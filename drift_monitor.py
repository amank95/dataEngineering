"""
Drift Monitor
==============
Compares a baseline (training) feature distribution with current live data
and writes drift alerts into Supabase (model_health_alerts table).
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import os
import logging
import requests
from datetime import datetime, timedelta

import pandas as pd
from scipy.stats import ks_2samp

logger = logging.getLogger(__name__)

DRIFT_BASELINE_PATH = os.getenv(
    "DRIFT_BASELINE_PATH",
    "data/processed/baseline_features.parquet",
)

DEFAULT_FEATURES = ["sma_20", "rsi_14", "volatility"]


def _load_baseline(path: Optional[str] = None) -> Optional[pd.DataFrame]:
    baseline_path = path or DRIFT_BASELINE_PATH
    if not os.path.exists(baseline_path):
        logger.warning(f"Drift baseline file not found at {baseline_path}. Skipping drift detection.")
        return None

    logger.info(f"Loading drift baseline from {baseline_path}...")
    if baseline_path.endswith(".parquet"):
        df = pd.read_parquet(baseline_path)
    elif baseline_path.endswith(".json"):
        df = pd.read_json(baseline_path)
    else:
        logger.warning(f"Unsupported baseline format for {baseline_path}. Expected .parquet or .json.")
        return None

    return df


def detect_feature_drift(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: Optional[List[str]] = None,
    alpha: float = 0.05,
    sample_size: int = 5000,
) -> Dict[str, Dict[str, Any]]:
    """
    Compare baseline vs current feature distributions using KS test.

    Returns a dict: {feature: {"statistic": ..., "p_value": ..., "drift": bool}}
    """
    features = features or DEFAULT_FEATURES
    results: Dict[str, Dict[str, Any]] = {}

    for feature in features:
        if feature not in baseline_df.columns or feature not in current_df.columns:
            continue

        base_vals = baseline_df[feature].dropna().to_numpy()
        curr_vals = current_df[feature].dropna().to_numpy()

        if len(base_vals) < 30 or len(curr_vals) < 30:
            # Not enough data to make a reliable judgment
            continue

        # Down-sample for speed
        if len(base_vals) > sample_size:
            base_vals = pd.Series(base_vals).sample(sample_size, random_state=42).to_numpy()
        if len(curr_vals) > sample_size:
            curr_vals = pd.Series(curr_vals).sample(sample_size, random_state=42).to_numpy()

        stat, p_value = ks_2samp(base_vals, curr_vals)
        results[feature] = {
            "statistic": float(stat),
            "p_value": float(p_value),
            "drift": bool(p_value < alpha),
            "baseline_sample_size": int(len(base_vals)),
            "current_sample_size": int(len(curr_vals)),
        }

    return results


def run_drift_monitor(
    parquet_path: str,
    supabase_client,
    baseline_path: Optional[str] = None,
    alpha: float = 0.05,
    features: Optional[List[str]] = None,
    lookback_days: int = 60,
    max_tickers: int = 50,
    sample_size: int = 5000,
) -> Dict[str, Any]:
    """
    Entry point: compare baseline vs current data and insert drift alerts.

    Args:
        parquet_path: Current pipeline Parquet file.
        supabase_client: Supabase client instance (already authenticated).
    """
    start = datetime.utcnow()

    baseline_df = _load_baseline(baseline_path)
    if baseline_df is None:
        return {"alerts_created": 0, "status": "baseline_missing"}

    if not os.path.exists(parquet_path):
        logger.warning(f"Current Parquet file not found: {parquet_path}. Skipping drift detection.")
        return {"alerts_created": 0, "status": "current_missing"}

    logger.info(f"Loading current features from {parquet_path} for drift detection...")
    current_df = pd.read_parquet(parquet_path)

    if "date" not in current_df.columns or "ticker" not in current_df.columns:
        logger.warning("Current data missing 'date' or 'ticker' columns. Skipping drift detection.")
        return {"alerts_created": 0, "status": "bad_schema"}

    # Restrict to recent window to keep things fast and relevant
    current_df["date"] = pd.to_datetime(current_df["date"])
    recent_cutoff = current_df["date"].max() - timedelta(days=lookback_days)
    current_recent = current_df[current_df["date"] >= recent_cutoff].copy()

    # Only consider tickers present in both baseline and current data
    common_tickers = sorted(
        set(baseline_df.get("ticker", [])).intersection(set(current_recent.get("ticker", [])))
    )
    if not common_tickers:
        logger.info("No common tickers between baseline and current data for drift detection.")
        return {"alerts_created": 0, "status": "no_common_tickers"}

    common_tickers = common_tickers[:max_tickers]

    alerts: List[Dict[str, Any]] = []

    for ticker in common_tickers:
        base_ticker_df = baseline_df[baseline_df.get("ticker") == ticker]
        curr_ticker_df = current_recent[current_recent["ticker"] == ticker]

        if base_ticker_df.empty or curr_ticker_df.empty:
            continue

        drift_results = detect_feature_drift(
            base_ticker_df,
            curr_ticker_df,
            features=features,
            alpha=alpha,
            sample_size=sample_size,
        )

        for feature, stats in drift_results.items():
            if stats.get("drift"):
                alerts.append(
                    {
                        "ticker": ticker,
                        "feature": feature,
                        "p_value": stats["p_value"],
                        "statistic": stats["statistic"],
                        "alpha": alpha,
                        "baseline_sample_size": stats["baseline_sample_size"],
                        "current_sample_size": stats["current_sample_size"],
                        "detected_at": datetime.utcnow().isoformat(),
                    }
                )

    alerts_created = 0
    if alerts:
        try:
            logger.info(f"Inserting {len(alerts)} drift alerts into model_health_alerts...")
            supabase_client.table("model_health_alerts").insert(alerts).execute()
            alerts_created = len(alerts)
        except Exception as e:
            logger.error(f"Failed to insert drift alerts into Supabase: {e}")

    duration = (datetime.utcnow() - start).total_seconds()
    logger.info(f"Drift monitor finished in {duration:.2f}s. Alerts created: {alerts_created}")

    # Active Notification: Trigger logic for ML Team
    if alerts_created > 0:
        trigger_retraining_webhook(alerts)

    return {
        "alerts_created": alerts_created,
        "status": "ok",
        "duration_seconds": duration,
    }


def trigger_retraining_webhook(alerts: List[Dict[str, Any]]):
    """
    Sends a webhook notification to the ML team's system (e.g., Jenkins, Airflow).
    """
    try:
        # Load config to get the webhook URL
        # We do this here to avoid circular imports if possible, or just use simple env vars/config loading
        from config_loader import get_config
        config = get_config()
        webhook_url = config.get('mlops', {}).get('retraining_webhook_url')
        
        if not webhook_url:
            logger.info("No 'retraining_webhook_url' configured. Skipping active notification.")
            return

        logger.info(f"Triggering ML retraining webhook at {webhook_url}...")
        
        payload = {
            "event": "drift_detected",
            "timestamp": datetime.utcnow().isoformat(),
            "alert_count": len(alerts),
            "alerts": alerts
        }
        
        response = requests.post(webhook_url, json=payload, timeout=5)
        
        if response.status_code == 200:
            logger.info("✅ Successfully triggered retraining webhook.")
        else:
            logger.error(f"❌ Failed to trigger webhook. Status: {response.status_code}, Response: {response.text}")
            
    except Exception as e:
        logger.error(f"Failed to send webhook notification: {e}")




