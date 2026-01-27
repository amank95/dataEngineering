"""
Drift Monitor (Enhanced)
=========================
Production-ready drift detection with:
- KS-test + PSI (Population Stability Index)
- Drift severity classification
- Slack alerts
- Auto-retraining triggers
- Rate limiting and safety features
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import os
import logging
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from scipy.stats import ks_2samp

# Import new modules
try:
    from src.slack_notifier import get_slack_notifier
    from src.retraining_trigger import get_retraining_trigger
    INTEGRATIONS_AVAILABLE = True
except ImportError:
    INTEGRATIONS_AVAILABLE = False
    logger.warning("Slack/Retraining integrations not available")

logger = logging.getLogger(__name__)

DRIFT_BASELINE_PATH = os.getenv(
    "DRIFT_BASELINE_PATH",
    "data/processed/baseline_features.parquet",
)

DEFAULT_FEATURES = ["sma_20", "rsi_14", "volatility", "daily_return", "macd"]


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


def calculate_psi(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """
    Calculate Population Stability Index (PSI).
    
    PSI measures distribution shift:
    - PSI < 0.1: No significant change
    - 0.1 <= PSI < 0.2: Moderate change
    - PSI >= 0.2: Significant change (drift)
    
    Args:
        baseline: Baseline distribution
        current: Current distribution
        bins: Number of bins for discretization
        
    Returns:
        PSI value
    """
    # Create bins based on baseline distribution
    breakpoints = np.percentile(baseline, np.linspace(0, 100, bins + 1))
    breakpoints = np.unique(breakpoints)  # Remove duplicates
    
    if len(breakpoints) < 3:
        # Not enough unique values
        return 0.0
    
    # Calculate frequencies
    baseline_freq, _ = np.histogram(baseline, bins=breakpoints)
    current_freq, _ = np.histogram(current, bins=breakpoints)
    
    # Normalize to percentages
    baseline_pct = baseline_freq / len(baseline)
    current_pct = current_freq / len(current)
    
    # Avoid division by zero
    baseline_pct = np.where(baseline_pct == 0, 0.0001, baseline_pct)
    current_pct = np.where(current_pct == 0, 0.0001, current_pct)
    
    # Calculate PSI
    psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
    
    return float(psi)


def calculate_drift_score(ks_pvalue: float, psi_value: float) -> float:
    """
    Calculate normalized drift score (0-1) from KS p-value and PSI.
    
    Args:
        ks_pvalue: KS-test p-value (0-1)
        psi_value: PSI value (typically 0-1, but can be higher)
        
    Returns:
        Drift score (0 = no drift, 1 = maximum drift)
    """
    # Convert p-value to drift indicator (inverse)
    ks_score = 1 - ks_pvalue
    
    # Normalize PSI (cap at 1.0)
    psi_score = min(psi_value / 0.3, 1.0)
    
    # Weighted average (KS-test weighted more heavily)
    drift_score = 0.7 * ks_score + 0.3 * psi_score
    
    return float(drift_score)


def classify_drift_severity(drift_score: float) -> str:
    """
    Classify drift severity based on drift score.
    
    Args:
        drift_score: Normalized drift score (0-1)
        
    Returns:
        Severity level: LOW, MEDIUM, HIGH, or CRITICAL
    """
    if drift_score < 0.3:
        return "LOW"
    elif drift_score < 0.6:
        return "MEDIUM"
    elif drift_score < 0.85:
        return "HIGH"
    else:
        return "CRITICAL"


def detect_feature_drift(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: Optional[List[str]] = None,
    alpha: float = 0.05,
    psi_threshold: float = 0.2,
    sample_size: int = 5000,
) -> Dict[str, Dict[str, Any]]:
    """
    Compare baseline vs current feature distributions using KS test + PSI.

    Returns a dict: {feature: {"statistic": ..., "p_value": ..., "drift": bool, "psi": ..., "drift_score": ...}}
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

        # KS-test
        stat, p_value = ks_2samp(base_vals, curr_vals)
        
        # PSI calculation
        psi = calculate_psi(base_vals, curr_vals)
        
        # Drift score
        drift_score = calculate_drift_score(p_value, psi)
        
        # Drift detection (either KS or PSI triggers)
        drift_detected = (p_value < alpha) or (psi >= psi_threshold)
        
        results[feature] = {
            "statistic": float(stat),
            "p_value": float(p_value),
            "psi": float(psi),
            "drift_score": float(drift_score),
            "drift": bool(drift_detected),
            "baseline_sample_size": int(len(base_vals)),
            "current_sample_size": int(len(curr_vals)),
        }

    return results


def run_drift_monitor(
    parquet_path: str,
    supabase_client,
    baseline_path: Optional[str] = None,
    alpha: float = 0.05,
    psi_threshold: float = 0.2,
    features: Optional[List[str]] = None,
    lookback_days: int = 60,
    max_tickers: int = 50,
    sample_size: int = 5000,
    enable_slack: bool = True,
    enable_auto_retrain: bool = False,
    min_retrain_interval_hours: int = 6,
) -> Dict[str, Any]:
    """
    Entry point: compare baseline vs current data, send alerts, and trigger retraining.

    Args:
        parquet_path: Current pipeline Parquet file.
        supabase_client: Supabase client instance (already authenticated).
        baseline_path: Path to baseline features file
        alpha: KS-test significance level
        psi_threshold: PSI threshold for drift detection
        features: List of features to monitor
        lookback_days: Days of recent data to analyze
        max_tickers: Maximum tickers to process
        sample_size: Sample size for drift tests
        enable_slack: Whether to send Slack alerts
        enable_auto_retrain: Whether to trigger auto-retraining
        min_retrain_interval_hours: Minimum hours between retraining
    """
    start = datetime.utcnow()
    
    # Initialize integrations
    slack_notifier = None
    retraining_trigger = None
    
    if INTEGRATIONS_AVAILABLE:
        if enable_slack:
            slack_notifier = get_slack_notifier()
        if enable_auto_retrain:
            retraining_trigger = get_retraining_trigger()

    baseline_df = _load_baseline(baseline_path)
    if baseline_df is None:
        return {"alerts_created": 0, "retraining_triggered": 0, "status": "baseline_missing"}

    if not os.path.exists(parquet_path):
        logger.warning(f"Current Parquet file not found: {parquet_path}. Skipping drift detection.")
        return {"alerts_created": 0, "retraining_triggered": 0, "status": "current_missing"}

    logger.info(f"Loading current features from {parquet_path} for drift detection...")
    current_df = pd.read_parquet(parquet_path)

    if "date" not in current_df.columns or "ticker" not in current_df.columns:
        logger.warning("Current data missing 'date' or 'ticker' columns. Skipping drift detection.")
        return {"alerts_created": 0, "retraining_triggered": 0, "status": "bad_schema"}

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
        return {"alerts_created": 0, "retraining_triggered": 0, "status": "no_common_tickers"}

    common_tickers = common_tickers[:max_tickers]

    alerts: List[Dict[str, Any]] = []
    retraining_count = 0
    ticker_drift_summary: Dict[str, Dict[str, Any]] = {}

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
            psi_threshold=psi_threshold,
            sample_size=sample_size,
        )

        # Calculate overall ticker drift
        drifted_features = [f for f, stats in drift_results.items() if stats.get("drift")]
        
        if not drifted_features:
            continue
        
        # Calculate average drift score across drifted features
        avg_drift_score = np.mean([
            drift_results[f]["drift_score"] for f in drifted_features
        ])
        
        # Classify severity
        drift_severity = classify_drift_severity(avg_drift_score)
        
        # Store ticker summary
        ticker_drift_summary[ticker] = {
            "drifted_features": drifted_features,
            "avg_drift_score": float(avg_drift_score),
            "severity": drift_severity,
            "drift_results": drift_results
        }
        
        logger.info(
            f"Drift detected for {ticker}: {len(drifted_features)} features, "
            f"severity={drift_severity}, score={avg_drift_score:.3f}"
        )

        # Create alerts for database
        for feature in drifted_features:
            stats = drift_results[feature]
            alerts.append(
                {
                    "ticker": ticker,
                    "feature": feature,
                    "p_value": stats["p_value"],
                    "statistic": stats["statistic"],
                    "psi": stats.get("psi", 0.0),
                    "drift_score": stats.get("drift_score", 0.0),
                    "severity": drift_severity,
                    "alpha": alpha,
                    "baseline_sample_size": stats["baseline_sample_size"],
                    "current_sample_size": stats["current_sample_size"],
                    "detected_at": datetime.utcnow().isoformat(),
                }
            )
        
        # Send Slack alert
        if slack_notifier:
            try:
                slack_notifier.send_drift_alert(
                    ticker=ticker,
                    drift_results=drift_results,
                    severity=drift_severity,
                    affected_features=drifted_features
                )
            except Exception as e:
                logger.error(f"Failed to send Slack alert for {ticker}: {e}")
        
        # Auto-retraining logic
        if retraining_trigger and enable_auto_retrain:
            try:
                # Check if ticker requires approval
                requires_approval = retraining_trigger.requires_approval(ticker, supabase_client)
                
                if requires_approval:
                    logger.info(f"Ticker {ticker} requires manual approval for retraining")
                    if slack_notifier:
                        slack_notifier.send_approval_request(
                            ticker=ticker,
                            drift_severity=drift_severity,
                            affected_features=drifted_features
                        )
                    continue
                
                # Check rate limit
                rate_limit_check = retraining_trigger.check_rate_limit(
                    ticker=ticker,
                    supabase_client=supabase_client,
                    min_interval_hours=min_retrain_interval_hours
                )
                
                if not rate_limit_check["allowed"]:
                    logger.info(
                        f"Retraining skipped for {ticker} due to rate limiting "
                        f"(last retrain: {rate_limit_check.get('hours_since_last', 0):.1f}h ago)"
                    )
                    if slack_notifier:
                        slack_notifier.send_rate_limit_notification(
                            ticker=ticker,
                            last_retrain_time=rate_limit_check["last_retrain_time"],
                            cooldown_hours=min_retrain_interval_hours
                        )
                    continue
                
                # Trigger retraining
                logger.info(f"Triggering auto-retraining for {ticker}")
                retrain_result = retraining_trigger.trigger_retraining(
                    ticker=ticker,
                    drift_severity=drift_severity,
                    drift_results=drift_results,
                    supabase_client=supabase_client
                )
                
                if retrain_result["success"]:
                    retraining_count += 1
                    logger.info(
                        f"Retraining triggered successfully for {ticker}, "
                        f"job_id={retrain_result['job_id']}"
                    )
                    
                    # Send confirmation
                    if slack_notifier:
                        slack_notifier.send_retraining_confirmation(
                            ticker=ticker,
                            job_id=retrain_result["job_id"],
                            drift_severity=drift_severity
                        )
                else:
                    logger.error(
                        f"Failed to trigger retraining for {ticker}: "
                        f"{retrain_result.get('error')}"
                    )
                    
                    # Send error alert
                    if slack_notifier:
                        slack_notifier.send_error_alert(
                            ticker=ticker,
                            error_type="RETRAINING_TRIGGER_FAILED",
                            error_message=retrain_result.get("error", "Unknown error"),
                            context={"drift_severity": drift_severity}
                        )
                        
            except Exception as e:
                logger.error(f"Error in auto-retraining logic for {ticker}: {e}")
                if slack_notifier:
                    slack_notifier.send_error_alert(
                        ticker=ticker,
                        error_type="RETRAINING_EXCEPTION",
                        error_message=str(e)
                    )

    # Insert alerts into database
    alerts_created = 0
    if alerts:
        try:
            logger.info(f"Inserting {len(alerts)} drift alerts into model_health_alerts...")
            supabase_client.table("model_health_alerts").insert(alerts).execute()
            alerts_created = len(alerts)
        except Exception as e:
            logger.error(f"Failed to insert drift alerts into Supabase: {e}")

    duration = (datetime.utcnow() - start).total_seconds()
    logger.info(
        f"Drift monitor finished in {duration:.2f}s. "
        f"Alerts created: {alerts_created}, Retraining triggered: {retraining_count}"
    )

    return {
        "alerts_created": alerts_created,
        "retraining_triggered": retraining_count,
        "tickers_with_drift": len(ticker_drift_summary),
        "ticker_summary": ticker_drift_summary,
        "status": "ok",
        "duration_seconds": duration,
    }





