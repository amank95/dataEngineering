"""
MLOps API Module
=================
Provides MLOps-specific endpoints for dashboard monitoring:
- System health metrics
- Pipeline performance metrics
- Data quality metrics
- Drift detection

Usage:
    This module is mounted in api.py as a router.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import os
import pandas as pd
import numpy as np
from scipy import stats

# Import existing modules
from config_loader import get_output_file, get_config
from src.data_quality import get_data_quality_report

# Initialize router
router = APIRouter(prefix="/api/mlops", tags=["MLOps"])

# Global variable to store pipeline metrics (updated by data_pipeline.py)
PIPELINE_METRICS = {
    "last_execution": None,
    "total_rows": 0,
    "execution_time_seconds": 0,
    "tickers_processed": 0,
    "tickers_failed": []
}


def update_pipeline_metrics(metrics: Dict):
    """Update global pipeline metrics (called by data_pipeline.py)"""
    global PIPELINE_METRICS
    PIPELINE_METRICS.update(metrics)


@router.get("/system-health")
def get_system_health():
    """
    Get comprehensive system health metrics.
    
    Returns:
        - data_freshness: Time since last pipeline execution
        - supabase_status: Connection status
        - api_status: API availability
        - overall_health_score: 0-100 score
    """
    health = {
        "timestamp": datetime.now().isoformat(),
        "data_freshness": {
            "status": "unknown",
            "last_update": None,
            "hours_since_update": None
        },
        "supabase_status": "unknown",
        "api_status": "healthy",
        "overall_health_score": 0
    }
    
    # Check data freshness
    output_file = get_output_file()
    if os.path.exists(output_file):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(output_file))
        hours_since = (datetime.now() - file_mod_time).total_seconds() / 3600
        
        health["data_freshness"]["last_update"] = file_mod_time.isoformat()
        health["data_freshness"]["hours_since_update"] = round(hours_since, 2)
        
        # Data is fresh if updated within 1 hour
        if hours_since < 1:
            health["data_freshness"]["status"] = "fresh"
        elif hours_since < 24:
            health["data_freshness"]["status"] = "acceptable"
        else:
            health["data_freshness"]["status"] = "stale"
    else:
        health["data_freshness"]["status"] = "no_data"
    
    # Check Supabase connection
    try:
        from supabase import create_client
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_KEY = os.getenv('SUPABASE_KEY')
        
        if SUPABASE_URL and SUPABASE_KEY:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            response = supabase.table('stock_features').select('ticker').limit(1).execute()
            health["supabase_status"] = "connected"
        else:
            health["supabase_status"] = "not_configured"
    except Exception as e:
        health["supabase_status"] = f"error: {str(e)}"
    
    # Calculate overall health score
    score = 100
    
    if health["data_freshness"]["status"] == "stale":
        score -= 40
    elif health["data_freshness"]["status"] == "acceptable":
        score -= 20
    elif health["data_freshness"]["status"] == "no_data":
        score -= 50
    
    if health["supabase_status"] not in ["connected", "not_configured"]:
        score -= 30
    
    health["overall_health_score"] = max(0, score)
    
    return health


@router.get("/pipeline-metrics")
def get_pipeline_metrics():
    """
    Get pipeline performance metrics.
    
    Returns:
        - latency: Average processing time per ticker
        - throughput: Rows processed per second
        - total_rows: Total rows ingested
        - success_rate: Percentage of successful ticker processing
        - last_execution: Timestamp of last pipeline run
    """
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "latency_seconds": 0,
        "throughput_rows_per_second": 0,
        "total_rows_ingested": PIPELINE_METRICS.get("total_rows", 0),
        "success_rate_percent": 0,
        "last_execution": PIPELINE_METRICS.get("last_execution"),
        "tickers_processed": PIPELINE_METRICS.get("tickers_processed", 0),
        "tickers_failed": PIPELINE_METRICS.get("tickers_failed", [])
    }
    
    # Calculate latency
    execution_time = PIPELINE_METRICS.get("execution_time_seconds", 0)
    tickers_processed = PIPELINE_METRICS.get("tickers_processed", 0)
    
    if tickers_processed > 0 and execution_time > 0:
        metrics["latency_seconds"] = round(execution_time / tickers_processed, 2)
        metrics["throughput_rows_per_second"] = round(
            PIPELINE_METRICS.get("total_rows", 0) / execution_time, 2
        )
    
    # Calculate success rate
    total_tickers = tickers_processed + len(PIPELINE_METRICS.get("tickers_failed", []))
    if total_tickers > 0:
        metrics["success_rate_percent"] = round((tickers_processed / total_tickers) * 100, 2)
    
    return metrics


@router.get("/data-quality/{ticker}")
def get_data_quality(ticker: str):
    """
    Get data quality metrics for a specific ticker.
    
    Parameters:
        ticker: Stock ticker symbol
    
    Returns:
        - null_percentage: Percentage of null values
        - quality_score: 0-100 quality score
        - ohlc_validation: OHLC validation status
        - outlier_count: Number of outliers detected
        - schema_validation: Schema validation status
    """
    try:
        # Check if Supabase is available
        from supabase import create_client
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_KEY = os.getenv('SUPABASE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Fetch recent data for the ticker
        response = supabase.table('stock_features')\
            .select('*')\
            .eq('ticker', ticker)\
            .order('date', desc=True)\
            .limit(100)\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"No data found for ticker {ticker}")
        
        # Convert to DataFrame
        df = pd.DataFrame(response.data)
        
        # Set date as index for quality report
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        
        # Get quality report
        quality_report = get_data_quality_report(df, ticker)
        
        # Calculate null percentage
        total_cells = len(df) * len(df.columns)
        total_nulls = sum(quality_report['missing_values'].values())
        null_percentage = round((total_nulls / total_cells) * 100, 2) if total_cells > 0 else 0
        
        # Format response
        result = {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker,
            "null_percentage": null_percentage,
            "quality_score": round(quality_report['quality_score'], 2),
            "ohlc_validation": quality_report['ohlc_validation'],
            "outlier_count": sum(quality_report['outliers'].values()),
            "schema_validation": "pass" if quality_report['quality_score'] > 80 else "fail",
            "total_rows_analyzed": len(df)
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality check failed: {str(e)}")


@router.get("/drift-detection/{ticker}")
def get_drift_detection(
    ticker: str,
    baseline_days: int = Query(30, description="Baseline window in days"),
    current_days: int = Query(7, description="Current window in days")
):
    """
    Detect statistical drift in market data.
    
    Parameters:
        ticker: Stock ticker symbol
        baseline_days: Number of days for baseline window (default: 30)
        current_days: Number of days for current window (default: 7)
    
    Returns:
        - drift_status: 'normal' or 'detected'
        - z_score: Statistical z-score
        - baseline_stats: Statistics for baseline window
        - current_stats: Statistics for current window
        - distribution_data: Data for visualization
    """
    try:
        # Check if Supabase is available
        from supabase import create_client
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_KEY = os.getenv('SUPABASE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Fetch recent data for the ticker
        total_days = baseline_days + current_days
        response = supabase.table('stock_features')\
            .select('date, close, daily_return, rsi_14')\
            .eq('ticker', ticker)\
            .order('date', desc=True)\
            .limit(total_days)\
            .execute()
        
        if not response.data or len(response.data) < total_days:
            raise HTTPException(
                status_code=404, 
                detail=f"Insufficient data for drift detection (need {total_days} days, got {len(response.data)})"
            )
        
        # Convert to DataFrame and sort chronologically
        df = pd.DataFrame(response.data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=True).reset_index(drop=True)
        
        # Split into baseline and current windows
        baseline_df = df.iloc[:baseline_days]
        current_df = df.iloc[baseline_days:]
        
        # Calculate statistics for daily returns
        baseline_return_mean = baseline_df['daily_return'].mean()
        baseline_return_std = baseline_df['daily_return'].std()
        current_return_mean = current_df['daily_return'].mean()
        
        # Calculate statistics for RSI
        baseline_rsi_mean = baseline_df['rsi_14'].mean()
        baseline_rsi_std = baseline_df['rsi_14'].std()
        current_rsi_mean = current_df['rsi_14'].mean()
        
        # Calculate z-scores
        z_score_return = abs((current_return_mean - baseline_return_mean) / baseline_return_std) if baseline_return_std > 0 else 0
        z_score_rsi = abs((current_rsi_mean - baseline_rsi_mean) / baseline_rsi_std) if baseline_rsi_std > 0 else 0
        
        # Overall z-score (max of the two)
        overall_z_score = max(z_score_return, z_score_rsi)
        
        # Determine drift status (threshold: 2.0)
        drift_detected = overall_z_score >= 2.0
        
        # Prepare distribution data for visualization
        distribution_data = {
            "baseline": {
                "returns": baseline_df['daily_return'].dropna().tolist(),
                "rsi": baseline_df['rsi_14'].dropna().tolist()
            },
            "current": {
                "returns": current_df['daily_return'].dropna().tolist(),
                "rsi": current_df['rsi_14'].dropna().tolist()
            }
        }
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker,
            "drift_status": "detected" if drift_detected else "normal",
            "z_score": round(overall_z_score, 3),
            "z_score_return": round(z_score_return, 3),
            "z_score_rsi": round(z_score_rsi, 3),
            "baseline_stats": {
                "window_days": baseline_days,
                "mean_return": round(baseline_return_mean, 4),
                "std_return": round(baseline_return_std, 4),
                "mean_rsi": round(baseline_rsi_mean, 2),
                "std_rsi": round(baseline_rsi_std, 2)
            },
            "current_stats": {
                "window_days": current_days,
                "mean_return": round(current_return_mean, 4),
                "mean_rsi": round(current_rsi_mean, 2)
            },
            "distribution_data": distribution_data,
            "confidence_level": "high" if overall_z_score > 3.0 else "medium" if overall_z_score > 2.0 else "low"
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drift detection failed: {str(e)}")


if __name__ == "__main__":
    print("MLOps API Module")
    print("=" * 50)
    print("This module provides MLOps endpoints for the dashboard.")
    print("Mount this router in api.py to use.")
