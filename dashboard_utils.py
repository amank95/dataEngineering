"""
Dashboard Utilities Module
===========================
Provides utility functions for fetching and processing data for the MLOps dashboard.
"""

import requests
from typing import Dict, Optional, Tuple
from datetime import datetime


BASE_URL = "http://127.0.0.1:8000"


def fetch_system_health() -> Dict:
    """
    Fetch system health metrics from API.
    
    Returns:
        dict: System health data including freshness, status, and scores
    """
    try:
        response = requests.get(f"{BASE_URL}/api/mlops/system-health", timeout=5)
        response.raise_for_status()
        return response.json()
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
        response = requests.get(f"{BASE_URL}/api/mlops/pipeline-metrics", timeout=5)
        response.raise_for_status()
        return response.json()
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
        response = requests.get(f"{BASE_URL}/api/mlops/data-quality/{ticker}", timeout=5)
        response.raise_for_status()
        return response.json()
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
        response = requests.get(
            f"{BASE_URL}/api/mlops/drift-detection/{ticker}",
            params={"baseline_days": baseline_days, "current_days": current_days},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
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


if __name__ == "__main__":
    print("Dashboard Utilities Module")
    print("=" * 50)
    print("Testing API connections...")
    
    # Test system health
    health = fetch_system_health()
    print(f"\nSystem Health: {health.get('overall_health_score', 0)}/100")
    
    # Test pipeline metrics
    metrics = fetch_pipeline_metrics()
    print(f"Pipeline Latency: {metrics.get('latency_seconds', 0)}s")
    
    print("\nUtilities module loaded successfully!")
