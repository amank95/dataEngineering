"""
ML Team Data Access Module
===========================
This module provides direct access to pandas DataFrames for the ML team.
Instead of reading saved files, ML engineers can call these functions to get
DataFrames directly in memory for model training.

This module REUSES the existing pipeline functions (fetch_data, clean_data, 
generate_features) to avoid code duplication.

Usage Example:
--------------
from ml_data_access import get_processed_dataframe, get_all_tickers_dataframe

# Get data for a single ticker
df = get_processed_dataframe('AAPL', start_date='2022-01-01', end_date='2026-01-01')

# Get consolidated data for all tickers
df_all = get_all_tickers_dataframe(
    tickers=['WMT', 'JNJ', 'JPM', 'MSFT'],
    start_date='2022-01-01',
    end_date='2026-01-01'
)
"""

import pandas as pd
import os
import sys

# Add src to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fetch_data import fetch_data
from clean_data import clean_data
from feature_engineering import generate_features


def get_processed_dataframe(ticker, start_date, end_date):
    """
    Returns fully processed DataFrame with all features for a single ticker.
    This is the main function ML teams should use for single ticker data.
    
    This function REUSES existing pipeline functions:
    - fetch_data() to get raw data
    - clean_data() to clean and convert to INR
    - generate_features() to add technical indicators
    
    Parameters:
        ticker (str): Stock or ETF symbol
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str): End date in 'YYYY-MM-DD' format
    
    Returns:
        pd.DataFrame: Fully processed data with features:
            - OHLCV data (in INR)
            - Return: Daily returns
            - SMA_20: 20-day Simple Moving Average
            - SMA_50: 50-day Simple Moving Average
            - RSI_14: 14-period Relative Strength Index
            - MACD: Moving Average Convergence Divergence
            - Volatility: 20-day rolling volatility
            - Ticker: Stock symbol
    """
    print(f"\n{'='*60}")
    print(f"Processing {ticker} ({start_date} to {end_date})")
    print(f"{'='*60}")
    
    # Step 1: Fetch raw data using existing function
    fetch_data(ticker=ticker, start_date=start_date, end_date=end_date)
    
    # Step 2: Clean data using existing function
    clean_data(ticker=ticker)
    
    # Step 3: Generate features using existing function
    generate_features(ticker=ticker)
    
    # Step 4: Read the processed data
    final_path = f"data/processed/{ticker}_final.csv"
    if not os.path.exists(final_path):
        raise FileNotFoundError(f"Processed file not found: {final_path}")
    
    df = pd.read_csv(final_path, index_col='date', parse_dates=True)
    
    # Step 5: Standardize column names for ML team
    rename_map = {
        'daily_return': 'Return',
        'ma_20': 'SMA_20',
        'ma_50': 'SMA_50',
        'rsi_14': 'RSI_14',
        'macd': 'MACD',
        'volatility': 'Volatility'
    }
    df.rename(columns=rename_map, inplace=True)
    
    # Step 6: Add Ticker column
    df['Ticker'] = ticker
    
    print(f"✅ Completed processing for {ticker}. Shape: {df.shape}")
    return df


def get_all_tickers_dataframe(tickers, start_date, end_date):
    """
    Returns consolidated DataFrame for multiple tickers.
    This is the main function ML teams should use for multi-ticker datasets.
    
    Parameters:
        tickers (list): List of stock/ETF symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str): End date in 'YYYY-MM-DD' format
    
    Returns:
        pd.DataFrame: Consolidated DataFrame with all tickers and features
    
    Example:
        >>> tickers = ['WMT', 'JNJ', 'JPM', 'MSFT', 'NVDA']
        >>> df = get_all_tickers_dataframe(tickers, '2022-01-01', '2026-01-01')
        >>> print(df.head())
        >>> print(df['Ticker'].unique())
    """
    print(f"\nProcessing {len(tickers)} tickers: {tickers}")
    all_data = []
    
    for ticker in tickers:
        try:
            df = get_processed_dataframe(ticker, start_date, end_date)
            all_data.append(df)
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue
    
    if all_data:
        print("\nConsolidating all ticker data...")
        master_df = pd.concat(all_data, ignore_index=True)
        print(f"Consolidated DataFrame shape: {master_df.shape}")
        print(f"Tickers included: {master_df['Ticker'].unique().tolist()}")
        return master_df
    else:
        print("No data to consolidate.")
        return pd.DataFrame()


# Example usage and testing
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ML Data Access Module - Example Usage")
    print("=" * 60)
    
    # Example 1: Get data for a single ticker
    print("\n--- Example 1: Single Ticker ---")
    df_single = get_processed_dataframe('AAPL', '2023-06-01', '2023-12-31')
    print(f"\n✅ DataFrame Info:")
    print(df_single.info())
    print(f"\n✅ First 5 rows:")
    print(df_single.head())
    print(f"\n✅ Column names: {df_single.columns.tolist()}")
    
    # Example 2: Get data for multiple tickers
    print("\n\n--- Example 2: Multiple Tickers ---")
    tickers = ['AAPL', 'MSFT']
    df_multi = get_all_tickers_dataframe(tickers, '2023-06-01', '2023-12-31')
    print(f"\n✅ DataFrame Info:")
    print(df_multi.info())
    print(f"\n✅ Sample data:")
    print(df_multi.head(10))
    print(f"\n✅ Data distribution by ticker:")
    print(df_multi['Ticker'].value_counts())
    
    print("\n" + "=" * 60)
    print("✅ Examples completed successfully!")
    print("=" * 60)
