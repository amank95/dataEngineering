"""
Supabase Query Examples
=======================
Demonstrates how to query stock features from Supabase for:
1. ML model training
2. Dashboard visualizations
3. Data analysis

Prerequisites:
- Supabase project set up
- Data synced using supabase_ingestion.py
- .env file with SUPABASE_URL and SUPABASE_KEY
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import Client, create_client


# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)


# ============================================
# ML Training Queries
# ============================================

def get_training_data(start_date: str, end_date: str, tickers: list = None) -> pd.DataFrame:
    """
    Get training data for ML models.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        tickers: Optional list of tickers to filter
        
    Returns:
        DataFrame with stock features
    """
    query = supabase.table('stock_features')\
        .select('*')\
        .gte('date', start_date)\
        .lte('date', end_date)
    
    if tickers:
        query = query.in_('ticker', tickers)
    
    response = query.execute()
    df = pd.DataFrame(response.data)
    
    print(f"Retrieved {len(df)} records for training")
    return df


def get_incremental_data(last_sync_timestamp: str) -> pd.DataFrame:
    """
    Get only new/updated records since last sync.
    Useful for incremental model updates.
    
    Args:
        last_sync_timestamp: ISO timestamp of last sync
        
    Returns:
        DataFrame with new/updated records
    """
    response = supabase.table('stock_features')\
        .select('*')\
        .gt('updated_at', last_sync_timestamp)\
        .execute()
    
    df = pd.DataFrame(response.data)
    print(f"Retrieved {len(df)} new/updated records")
    return df


def get_ticker_time_series(ticker: str, start_date: str = None, limit: int = None) -> pd.DataFrame:
    """
    Get complete time series for a specific ticker.
    
    Args:
        ticker: Stock ticker (e.g., 'RELIANCE.NS')
        start_date: Optional start date filter
        limit: Optional limit on number of records
        
    Returns:
        DataFrame sorted by date
    """
    query = supabase.table('stock_features')\
        .select('*')\
        .eq('ticker', ticker)\
        .order('date', desc=False)  # Ascending for time series
    
    if start_date:
        query = query.gte('date', start_date)
    
    if limit:
        query = query.limit(limit)
    
    response = query.execute()
    df = pd.DataFrame(response.data)
    
    print(f"Retrieved {len(df)} records for {ticker}")
    return df


# ============================================
# Dashboard Queries
# ============================================

def get_latest_data_per_ticker(limit: int = 10) -> pd.DataFrame:
    """
    Get the most recent data point for each ticker.
    Useful for dashboard overview.
    
    Args:
        limit: Number of tickers to return
        
    Returns:
        DataFrame with latest data per ticker
    """
    # Use the pre-built view
    response = supabase.table('latest_stock_data')\
        .select('*')\
        .limit(limit)\
        .execute()
    
    df = pd.DataFrame(response.data)
    return df


def get_recent_ticker_data(ticker: str, days: int = 30) -> pd.DataFrame:
    """
    Get recent N days of data for a ticker.
    Useful for dashboard charts.
    
    Args:
        ticker: Stock ticker
        days: Number of recent days
        
    Returns:
        DataFrame with recent data
    """
    response = supabase.table('stock_features')\
        .select('date, open, high, low, close, volume, rsi_14, daily_return')\
        .eq('ticker', ticker)\
        .order('date', desc=True)\
        .limit(days)\
        .execute()
    
    df = pd.DataFrame(response.data)
    # Reverse to get chronological order
    df = df.iloc[::-1].reset_index(drop=True)
    
    return df


def get_paginated_data(page: int = 0, page_size: int = 100, order_by: str = 'date') -> pd.DataFrame:
    """
    Get paginated data for dashboard tables.
    
    Args:
        page: Page number (0-indexed)
        page_size: Records per page
        order_by: Column to sort by
        
    Returns:
        DataFrame with paginated results
    """
    start = page * page_size
    end = start + page_size - 1
    
    response = supabase.table('stock_features')\
        .select('*')\
        .order(order_by, desc=True)\
        .range(start, end)\
        .execute()
    
    df = pd.DataFrame(response.data)
    print(f"Page {page + 1}: {len(df)} records")
    return df


# ============================================
# Analysis Queries
# ============================================

def get_top_performers(date: str = None, top_n: int = 10) -> pd.DataFrame:
    """
    Get top performing stocks by daily return.
    
    Args:
        date: Specific date (defaults to latest)
        top_n: Number of top performers
        
    Returns:
        DataFrame with top performers
    """
    query = supabase.table('stock_features')\
        .select('ticker, date, close, daily_return, rsi_14')
    
    if date:
        query = query.eq('date', date)
    else:
        # Get latest date's data
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
    
    df = pd.DataFrame(response.data)
    return df


def get_ticker_statistics(ticker: str, start_date: str, end_date: str) -> dict:
    """
    Calculate statistics for a ticker over a date range.
    
    Args:
        ticker: Stock ticker
        start_date: Start date
        end_date: End date
        
    Returns:
        Dictionary with statistics
    """
    df = get_ticker_time_series(ticker, start_date)
    df = df[df['date'] <= end_date]
    
    stats = {
        'ticker': ticker,
        'start_date': start_date,
        'end_date': end_date,
        'total_days': len(df),
        'avg_return': df['daily_return'].mean(),
        'std_return': df['daily_return'].std(),
        'avg_rsi': df['rsi_14'].mean(),
        'avg_volume': df['volume'].mean(),
        'price_change': ((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100) if len(df) > 0 else 0
    }
    
    return stats


def search_by_rsi_range(min_rsi: float, max_rsi: float, date: str = None) -> pd.DataFrame:
    """
    Find stocks within RSI range (useful for trading signals).
    
    Args:
        min_rsi: Minimum RSI value
        max_rsi: Maximum RSI value
        date: Specific date (defaults to latest)
        
    Returns:
        DataFrame with matching stocks
    """
    query = supabase.table('stock_features')\
        .select('ticker, date, close, rsi_14, daily_return')\
        .gte('rsi_14', min_rsi)\
        .lte('rsi_14', max_rsi)
    
    if date:
        query = query.eq('date', date)
    
    response = query.order('rsi_14', desc=False).execute()
    df = pd.DataFrame(response.data)
    
    print(f"Found {len(df)} stocks with RSI between {min_rsi} and {max_rsi}")
    return df


# ============================================
# Example Usage
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Supabase Query Examples")
    print("=" * 60)
    
    # Example 1: Get training data
    print("\n1. ML Training Data (Last 6 months)")
    start = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    end = datetime.now().strftime('%Y-%m-%d')
    training_df = get_training_data(start, end, tickers=['RELIANCE.NS', 'TCS.NS'])
    print(training_df.head())
    
    # Example 2: Latest data per ticker
    print("\n2. Latest Data Per Ticker")
    latest_df = get_latest_data_per_ticker(limit=5)
    print(latest_df)
    
    # Example 3: Recent ticker data for chart
    print("\n3. Recent 30 Days for RELIANCE.NS")
    recent_df = get_recent_ticker_data('RELIANCE.NS', days=30)
    print(recent_df.tail())
    
    # Example 4: Top performers
    print("\n4. Top 5 Performers (Latest Date)")
    top_df = get_top_performers(top_n=5)
    print(top_df)
    
    # Example 5: RSI-based search (oversold stocks)
    print("\n5. Oversold Stocks (RSI < 30)")
    oversold_df = search_by_rsi_range(0, 30)
    print(oversold_df)
    
    # Example 6: Ticker statistics
    print("\n6. Statistics for RELIANCE.NS")
    stats = get_ticker_statistics('RELIANCE.NS', start, end)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Examples completed successfully!")
    print("=" * 60)
