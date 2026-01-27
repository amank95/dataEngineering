"""
Enhanced FastAPI for Stock Market Data Pipeline
================================================
Serves data from both Parquet files and Supabase database.

Features:
- Pipeline execution endpoint
- Parquet file download
- Direct Supabase queries
- ML training data endpoints
- Dashboard data endpoints
- Health checks

Usage:
    uvicorn api:app --reload
    Access docs: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Any
from datetime import datetime, timedelta
from time import time
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
def get_pipeline_runner():
    from data_pipeline import main
    return main


# from data_pipeline import main as run_pipeline
from config_loader import get_output_file

# Initialize Supabase client (optional)
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        SUPABASE_ENABLED = True
    else:
        SUPABASE_ENABLED = False
        supabase = None
except ImportError:
    SUPABASE_ENABLED = False
    supabase = None

# Import MLOps router
from mlops_api import router as mlops_router

# ============================================
# Simple In-Memory Cache
# ============================================
_CACHE = {}

def _make_cache_key(*args):
    """Create a cache key from arguments."""
    return ":".join(str(arg) for arg in args if arg is not None)

def _cache_get(key: str, ttl_seconds: int = 60):
    """Get value from cache if not expired."""
    if key in _CACHE:
        value, timestamp = _CACHE[key]
        if (time() - timestamp) < ttl_seconds:
            return value
        else:
            del _CACHE[key]
    return None

def _cache_set(key: str, value: Any):
    """Set value in cache with timestamp."""
    _CACHE[key] = (value, time())

# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="Stock Data Pipeline API",
    description="API for ML team to generate, fetch, and query stock market data",
    version="2.0"
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include MLOps router
app.include_router(mlops_router)

# ============================================
# Health Checks
# ============================================

@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "status": "API is running",
        "version": "2.0",
        "endpoints": {
            "pipeline": "/run-pipeline (POST)",
            "parquet": "/fetch-parquet (GET)",
            "supabase": "/supabase/* (GET)",
            "docs": "/docs"
        },
        "supabase_enabled": SUPABASE_ENABLED
    }

@app.get("/health")
def health_check():
    """Comprehensive health check."""
    health_status = {
        "api": "healthy",
        "parquet_file_exists": os.path.exists(get_output_file()),
        "supabase_enabled": SUPABASE_ENABLED
    }
    
    # Check Supabase connection
    if SUPABASE_ENABLED:
        try:
            # Simple query to test connection
            response = supabase.table('stock_features').select('ticker').limit(1).execute()
            health_status["supabase_connection"] = "healthy"
            health_status["supabase_has_data"] = len(response.data) > 0
        except Exception as e:
            health_status["supabase_connection"] = f"unhealthy: {str(e)}"
            health_status["supabase_has_data"] = False
    
    return health_status

# ============================================
# Pipeline Execution
# ============================================

# @app.post("/run-pipeline")
# def run_pipeline_endpoint():
#     """
#     Execute the complete data pipeline.
    
#     This will:
#     1. Fetch data from Yahoo Finance
#     2. Clean and validate data
#     3. Generate technical indicators
#     4. Save to Parquet
#     5. (Optional) Sync to Supabase if auto_sync is enabled
#     """
#     try:
#         result = run_pipeline()
        
#         return {
#             "status": "success",
#             "message": "Data pipeline executed successfully",
#             "details": result
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")

@app.post("/run-pipeline")
def run_pipeline_endpoint():
    """
    Execute the complete data pipeline.
    """
    try:
        run_pipeline = get_pipeline_runner()
        result = run_pipeline()

        return {
            "status": "success",
            "message": "Data pipeline executed successfully",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Parquet File Access
# ============================================

@app.get("/fetch-parquet")
def fetch_parquet_file():
    """Download the processed Parquet file."""
    output_file = get_output_file()

    if not os.path.exists(output_file):
        raise HTTPException(
            status_code=404,
            detail="Processed data not found. Run /run-pipeline first."
        )

    return FileResponse(
        path=output_file,
        filename=os.path.basename(output_file),
        media_type="application/octet-stream"
    )

# ============================================
# Supabase Query Endpoints
# ============================================

@app.get("/supabase/training-data")
def get_training_data(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
    tickers: Optional[List[str]] = Query(None, description="Optional list of tickers")
):
    """
    Get training data for ML models from Supabase.
    
    If end_date is not provided, defaults to today.
    
    Example: /supabase/training-data?start_date=2024-01-01
    """
    if not SUPABASE_ENABLED:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    cache_key = _make_cache_key(
        "training-data",
        start_date,
        end_date or "AUTO",
        tuple(sorted(tickers)) if tickers else None,
    )
    cached = _cache_get(cache_key, ttl_seconds=60)
    if cached is not None:
        return cached
    
    try:
        # Default end_date to today if not provided
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        query = supabase.table('stock_features')\
            .select('*')\
            .gte('date', start_date)\
            .lte('date', end_date)
        
        if tickers:
            query = query.in_('ticker', tickers)
        
        response = query.execute()
        
        result = {
            "status": "success",
            "count": len(response.data),
            "data": response.data
        }
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/supabase/ticker/{ticker}")
def get_ticker_data(
    ticker: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(None, description="Max number of records")
):
    """
    Get time-series data for a specific ticker.
    
    Example: /supabase/ticker/RELIANCE.NS?start_date=2024-01-01&limit=100
    """
    if not SUPABASE_ENABLED:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    cache_key = _make_cache_key("ticker-data", ticker, start_date or "NONE", limit or -1)
    cached = _cache_get(cache_key, ttl_seconds=30)
    if cached is not None:
        return cached
    
    try:
        query = supabase.table('stock_features')\
            .select('*')\
            .eq('ticker', ticker)\
            .order('date', desc=False)
        
        if start_date:
            query = query.gte('date', start_date)
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        
        result = {
            "status": "success",
            "ticker": ticker,
            "count": len(response.data),
            "data": response.data
        }
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/supabase/latest")
def get_latest_data(limit: int = Query(10, description="Number of tickers")):
    """
    Get latest data point for each ticker.
    
    Example: /supabase/latest?limit=20
    """
    cache_key = _make_cache_key("latest", limit)
    cached = _cache_get(cache_key, ttl_seconds=15)
    if cached is not None:
        return cached

    # Prefer Supabase if configured; otherwise or if empty, fall back to local Parquet.
    supabase_data = []
    if SUPABASE_ENABLED:
        try:
            response = supabase.table('latest_stock_data')\
                .select('*')\
                .limit(limit)\
                .execute()
            supabase_data = response.data or []
        except Exception as e:
            # Log and continue to parquet fallback
            print(f"[supabase/latest] Supabase query failed, falling back to Parquet: {e}")
    
    if supabase_data:
        result = {
            "status": "success",
            "count": len(supabase_data),
            "data": supabase_data
        }
        _cache_set(cache_key, result)
        return result

    # Fallback: derive latest rows from Parquet output
    try:
        import pandas as pd
        output_file = get_output_file()
        if not os.path.exists(output_file):
            raise HTTPException(status_code=404, detail="Processed data not found. Run /run-pipeline first.")

        df = pd.read_parquet(output_file)
        if 'ticker' not in df.columns or 'date' not in df.columns:
            raise HTTPException(status_code=500, detail="Parquet file missing required columns (ticker/date).")

        df['date'] = pd.to_datetime(df['date'])
        latest_per_ticker = df.sort_values('date').groupby('ticker').tail(1)
        latest_per_ticker = latest_per_ticker.sort_values('date', ascending=False).head(limit)

        result = {
            "status": "success",
            "count": len(latest_per_ticker),
            "data": latest_per_ticker.to_dict(orient='records')
        }
        _cache_set(cache_key, result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallback to Parquet failed: {str(e)}")

@app.get("/supabase/recent/{ticker}")
def get_recent_ticker_data(
    ticker: str,
    days: int = Query(30, description="Number of recent days")
):
    """
    Get recent N days of data for a ticker.
    
    Example: /supabase/recent/RELIANCE.NS?days=60
    """
    if not SUPABASE_ENABLED:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    cache_key = _make_cache_key("recent", ticker, days)
    cached = _cache_get(cache_key, ttl_seconds=15)
    if cached is not None:
        return cached
    
    try:
        response = supabase.table('stock_features')\
            .select('date, open, high, low, close, volume, rsi_14, daily_return')\
            .eq('ticker', ticker)\
            .order('date', desc=True)\
            .limit(days)\
            .execute()
        
        # Reverse to chronological order
        data = list(reversed(response.data))
        
        result = {
            "status": "success",
            "ticker": ticker,
            "days": days,
            "count": len(data),
            "data": data
        }
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/supabase/top-performers")
def get_top_performers(
    date: Optional[str] = Query(None, description="Specific date (YYYY-MM-DD), defaults to latest"),
    top_n: int = Query(10, description="Number of top performers")
):
    """
    Get top performing stocks by daily return.
    
    Example: /supabase/top-performers?top_n=20
    """
    if not SUPABASE_ENABLED:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    
    try:
        query = supabase.table('stock_features')\
            .select('ticker, date, close, daily_return, rsi_14')
        
        if date:
            query = query.eq('date', date)
        else:
            # Get latest date
            latest_response = supabase.table('stock_features')\
                .select('date')\
                .order('date', desc=True)\
                .limit(1)\
                .execute()
            
            if latest_response.data:
                latest_date = latest_response.data[0]['date']
                query = query.eq('date', latest_date)
        
        response = query.order('daily_return', desc=True)\
            .limit(top_n)\
            .execute()
        
        return {
            "status": "success",
            "count": len(response.data),
            "data": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/supabase/rsi-search")
def search_by_rsi(
    min_rsi: float = Query(0, description="Minimum RSI"),
    max_rsi: float = Query(100, description="Maximum RSI"),
    date: Optional[str] = Query(None, description="Specific date (YYYY-MM-DD)")
):
    """
    Find stocks within RSI range.
    
    Example: /supabase/rsi-search?min_rsi=0&max_rsi=30 (oversold stocks)
    """
    if not SUPABASE_ENABLED:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    
    try:
        query = supabase.table('stock_features')\
            .select('ticker, date, close, rsi_14, daily_return')\
            .gte('rsi_14', min_rsi)\
            .lte('rsi_14', max_rsi)
        
        if date:
            query = query.eq('date', date)
        
        response = query.order('rsi_14', desc=False).execute()
        
        return {
            "status": "success",
            "min_rsi": min_rsi,
            "max_rsi": max_rsi,
            "count": len(response.data),
            "data": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# ============================================
# Utility Endpoints
# ============================================

@app.get("/supabase/stats/{ticker}")
def get_ticker_stats(
    ticker: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD), defaults to today")
):
    """
    Get statistical summary for a ticker.
    
    If end_date is not provided, defaults to today.
    
    Example: /supabase/stats/RELIANCE.NS?start_date=2024-01-01
    """
    if not SUPABASE_ENABLED:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    
    try:
        # Default end_date to today if not provided
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        response = supabase.table('stock_features')\
            .select('*')\
            .eq('ticker', ticker)\
            .gte('date', start_date)\
            .lte('date', end_date)\
            .order('date', desc=False)\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        
        import pandas as pd
        df = pd.DataFrame(response.data)
        
        stats = {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "total_days": len(df),
            "avg_return": float(df['daily_return'].mean()) if 'daily_return' in df else None,
            "std_return": float(df['daily_return'].std()) if 'daily_return' in df else None,
            "avg_rsi": float(df['rsi_14'].mean()) if 'rsi_14' in df else None,
            "avg_volume": int(df['volume'].mean()) if 'volume' in df else None,
            "price_change_pct": float(((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100)) if len(df) > 0 else 0
        }
        
        return {
            "status": "success",
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats calculation failed: {str(e)}")

# ============================================
# Model Health / Drift Monitoring Endpoints
# ============================================

@app.get("/supabase/model-health")
def get_model_health(
    window_hours: int = Query(24, description="Hours to look back for alerts"),
    ticker: Optional[str] = Query(None, description="Filter by specific ticker")
):
    """
    Get model health status from drift alerts.
    
    Example: /supabase/model-health?window_hours=48&ticker=RELIANCE.NS
    """
    if not SUPABASE_ENABLED:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    
    try:
        from datetime import timedelta
        since = (datetime.utcnow() - timedelta(hours=window_hours)).isoformat()
        
        query = supabase.table('model_health_alerts')\
            .select('*')\
            .gte('detected_at', since)\
            .order('detected_at', desc=True)
        
        if ticker:
            query = query.eq('ticker', ticker)
        
        response = query.limit(100).execute()
        
        alerts = response.data or []
        has_drift = len(alerts) > 0
        
        return {
            "status": "success",
            "model_health": "drifted" if has_drift else "stable",
            "has_drift": has_drift,
            "alert_count": len(alerts),
            "window_hours": window_hours,
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/supabase/drift-alerts")
def get_drift_alerts(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    feature: Optional[str] = Query(None, description="Filter by feature"),
    limit: int = Query(50, description="Max number of alerts")
):
    """
    Get detailed drift alerts.
    
    Example: /supabase/drift-alerts?ticker=RELIANCE.NS&feature=sma_20
    """
    if not SUPABASE_ENABLED:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    
    try:
        query = supabase.table('model_health_alerts')\
            .select('*')\
            .order('detected_at', desc=True)
        
        if ticker:
            query = query.eq('ticker', ticker)
        if feature:
            query = query.eq('feature', feature)
        
        response = query.limit(limit).execute()
        
        return {
            "status": "success",
            "count": len(response.data),
            "alerts": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
