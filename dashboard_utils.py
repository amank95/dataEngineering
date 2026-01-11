"""
Dashboard Utilities Module
===========================
Provides utility functions for fetching and processing data for the MLOps dashboard.
Uses the FastAPI endpoints from api.py
"""

import requests
from typing import Dict, Optional, Tuple
from datetime import datetime
import os

# Get API URL from environment or use default
BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')


def fetch_system_health() -> Dict:
    """
    Fetch system health metrics from API.
    
    Returns:
        dict: System health data including freshness, status, and scores
    """
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        health_data = response.json()
        
        # Transform API response to match dashboard expectations
        data_freshness = health_data.get('data_freshness', {})
        hours_since = data_freshness.get('hours_since_update', 999)
        
        if hours_since < 24:
            freshness_status = "fresh"
        elif hours_since < 72:
            freshness_status = "acceptable"
        else:
            freshness_status = "stale"
        
        return {
            "data_freshness": {
                "status": freshness_status,
                "hours_since_update": hours_since,
                "last_update": data_freshness.get('last_update')
            },
            "supabase_status": "connected" if health_data.get('supabase_enabled') else "not_configured",
            "overall_health_score": health_data.get('health_score', 0),
            "parquet_file_exists": health_data.get('parquet_file_exists', False),
            "supabase_enabled": health_data.get('supabase_enabled', False)
        }
    except Exception as e:
        return {
            "error": str(e),
            "data_freshness": {"status": "error"},
            "supabase_status": "error",
            "overall_health_score": 0
        }


def fetch_pipeline_metrics() -> Dict:
    """
    Fetch pipeline performance metrics from API.
    
    Returns:
        dict: Pipeline metrics including latency, throughput, and success rate
    """
    try:
        # Get health data which includes pipeline info
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        health_data = response.json()
        
        # Estimate metrics from health data
        # In production, you might want to add a dedicated /pipeline-metrics endpoint
        return {
            "latency_seconds": health_data.get('pipeline_latency_seconds', 0),
            "throughput_rows_per_second": health_data.get('throughput', 0),
            "total_rows_ingested": health_data.get('total_records', 0),
            "tickers_processed": health_data.get('tickers_processed', 0),
            "last_execution": health_data.get('last_update'),
            "success_rate_percent": 100 if health_data.get('parquet_file_exists') else 0
        }
    except Exception as e:
        return {
            "error": str(e),
            "latency_seconds": 0,
            "throughput_rows_per_second": 0,
            "total_rows_ingested": 0,
            "success_rate_percent": 0
        }


def fetch_data_quality(ticker: str) -> Dict:
    """
    Fetch data quality metrics for a specific ticker.
    
    Parameters:
        ticker: Stock ticker symbol
    
    Returns:
        dict: Data quality metrics including null percentage and quality score
    """
    try:
        # Get recent data for the ticker and calculate quality metrics
        response = requests.get(
            f"{BASE_URL}/supabase/recent/{ticker}",
            params={"days": 30},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'success' and data.get('data'):
            import pandas as pd
            df = pd.DataFrame(data['data'])
            
            # Calculate quality metrics
            total_rows = len(df)
            null_counts = df.isnull().sum()
            null_pct = (null_counts.sum() / (total_rows * len(df.columns))) * 100
            
            # Quality score (0-100): lower null % = higher score
            quality_score = max(0, 100 - null_pct * 2)
            
            # Schema validation: check if OHLC columns exist and are valid
            required_cols = ['open', 'high', 'low', 'close']
            has_schema = all(col in df.columns for col in required_cols)
            
            if has_schema and total_rows > 0:
                # Validate OHLC logic
                ohlc_valid = (df['high'] >= df['low']).all() and \
                            (df['high'] >= df['open']).all() and \
                            (df['high'] >= df['close']).all()
                schema_status = "pass" if ohlc_valid else "fail"
            else:
                schema_status = "unknown"
            
            return {
                "null_percentage": round(null_pct, 2),
                "quality_score": round(quality_score, 1),
                "schema_validation": schema_status,
                "total_rows": total_rows
            }
        else:
            return {
                "null_percentage": 0,
                "quality_score": 0,
                "schema_validation": "unknown"
            }
    except Exception as e:
        return {
            "error": str(e),
            "null_percentage": 0,
            "quality_score": 0,
            "schema_validation": "unknown"
        }


def fetch_drift_detection(ticker: str, baseline_days: int = 30, current_days: int = 7) -> Dict:
    """
    Fetch drift detection analysis for a specific ticker.
    
    Parameters:
        ticker: Stock ticker symbol
        baseline_days: Number of days for baseline window
        current_days: Number of days for current window
    
    Returns:
        dict: Drift detection results including status, z-score, and distribution data
    """
    try:
        # Get model health alerts for this ticker
        response = requests.get(
            f"{BASE_URL}/supabase/drift-alerts",
            params={"ticker": ticker, "limit": 10},
            timeout=10
        )
        response.raise_for_status()
        alerts_data = response.json()
        
        # Get recent data for statistical comparison
        recent_response = requests.get(
            f"{BASE_URL}/supabase/recent/{ticker}",
            params={"days": max(baseline_days, current_days)},
            timeout=10
        )
        recent_response.raise_for_status()
        stock_data = recent_response.json()
        
        if stock_data.get('status') == 'success' and stock_data.get('data'):
            import pandas as pd
            import numpy as np
            df = pd.DataFrame(stock_data['data'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Split into baseline and current windows
            if len(df) >= baseline_days:
                baseline_df = df.tail(baseline_days)
                current_df = df.tail(current_days) if len(df) >= current_days else df.tail(len(df))
                
                # Calculate statistics
                baseline_returns = baseline_df['daily_return'].dropna().values if 'daily_return' in baseline_df.columns else []
                current_returns = current_df['daily_return'].dropna().values if 'daily_return' in current_df.columns else []
                
                baseline_rsi = baseline_df['rsi_14'].dropna().values if 'rsi_14' in baseline_df.columns else []
                current_rsi = current_df['rsi_14'].dropna().values if 'rsi_14' in current_df.columns else []
                
                if len(baseline_returns) > 0 and len(current_returns) > 0:
                    # Calculate z-scores
                    baseline_mean = np.mean(baseline_returns)
                    baseline_std = np.std(baseline_returns)
                    current_mean = np.mean(current_returns)
                    
                    z_score_return = (current_mean - baseline_mean) / baseline_std if baseline_std > 0 else 0
                    
                    if len(baseline_rsi) > 0 and len(current_rsi) > 0:
                        baseline_rsi_mean = np.mean(baseline_rsi)
                        baseline_rsi_std = np.std(baseline_rsi)
                        current_rsi_mean = np.mean(current_rsi)
                        z_score_rsi = (current_rsi_mean - baseline_rsi_mean) / baseline_rsi_std if baseline_rsi_std > 0 else 0
                    else:
                        z_score_rsi = 0
                    
                    # Overall z-score (max of the two)
                    z_score = max(abs(z_score_return), abs(z_score_rsi))
                    
                    # Determine drift status
                    drift_threshold = 2.0
                    drift_status = "detected" if z_score > drift_threshold else "normal"
                    
                    # Check if there are recent alerts
                    alerts = alerts_data.get('alerts', [])
                    has_recent_alerts = len(alerts) > 0
                    
                    if has_recent_alerts:
                        drift_status = "detected"
                    
                    return {
                        "drift_status": drift_status,
                        "z_score": round(z_score, 3),
                        "z_score_return": round(z_score_return, 3),
                        "z_score_rsi": round(z_score_rsi, 3),
                        "baseline_stats": {
                            "mean_return": round(baseline_mean, 4),
                            "std_return": round(baseline_std, 4),
                            "mean_rsi": round(np.mean(baseline_rsi), 2) if len(baseline_rsi) > 0 else 0,
                            "std_rsi": round(np.std(baseline_rsi), 2) if len(baseline_rsi) > 0 else 0
                        },
                        "current_stats": {
                            "mean_return": round(current_mean, 4),
                            "mean_rsi": round(current_rsi_mean, 2) if len(current_rsi) > 0 else 0
                        },
                        "distribution_data": {
                            "baseline": {"returns": baseline_returns.tolist()},
                            "current": {"returns": current_returns.tolist()}
                        },
                        "confidence_level": "high" if z_score > 3 else "medium" if z_score > 2 else "low",
                        "recent_alerts": len(alerts)
                    }
        
        # Fallback if no data
        return {
            "drift_status": "unknown",
            "z_score": 0,
            "baseline_stats": {},
            "current_stats": {}
        }
    except Exception as e:
        return {
            "error": str(e),
            "drift_status": "unknown",
            "z_score": 0,
            "baseline_stats": {},
            "current_stats": {}
        }


def fetch_stock_data(ticker: str, start_date: str, end_date: str) -> Dict:
    """
    Fetch stock data from Supabase API.
    
    Parameters:
        ticker: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        dict: Stock data with OHLCV and technical indicators
    """
    try:
        # Calculate days difference
        from datetime import datetime as dt
        start = dt.strptime(start_date, "%Y-%m-%d")
        end = dt.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days
        
        response = requests.get(
            f"{BASE_URL}/supabase/recent/{ticker}",
            params={"days": days},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "error": str(e),
            "data": []
        }


def calculate_health_color(score: float, threshold_good: float = 80, threshold_warn: float = 50) -> str:
    """
    Calculate color based on health score.
    
    Parameters:
        score: Health score (0-100)
        threshold_good: Minimum score for green (default: 80)
        threshold_warn: Minimum score for yellow (default: 50)
    
    Returns:
        str: Color name ('green', 'yellow', or 'red')
    """
    if score >= threshold_good:
        return "green"
    elif score >= threshold_warn:
        return "yellow"
    else:
        return "red"


def format_timestamp(timestamp_str: Optional[str]) -> str:
    """
    Format ISO timestamp to human-readable format.
    
    Parameters:
        timestamp_str: ISO format timestamp string
    
    Returns:
        str: Formatted timestamp or 'Unknown'
    """
    if not timestamp_str:
        return "Unknown"
    
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str


def get_status_emoji(status: str) -> str:
    """
    Get emoji for status indicator.
    
    Parameters:
        status: Status string
    
    Returns:
        str: Emoji character
    """
    status_map = {
        "fresh": "✅",
        "acceptable": "⚠️",
        "stale": "🚨",
        "no_data": "❌",
        "error": "❌",
        "connected": "✅",
        "not_configured": "⚠️",
        "normal": "✅",
        "detected": "🚨",
        "pass": "✅",
        "fail": "🚨",
        "unknown": "❓"
    }
    return status_map.get(status.lower(), "❓")


def format_metric_value(value: float, unit: str = "", decimals: int = 2) -> str:
    """
    Format metric value with unit.
    
    Parameters:
        value: Numeric value
        unit: Unit string (e.g., 's', '%', 'rows/s')
        decimals: Number of decimal places
    
    Returns:
        str: Formatted value with unit
    """
    if isinstance(value, (int, float)):
        formatted = f"{value:.{decimals}f}"
        return f"{formatted} {unit}".strip()
    return str(value)
