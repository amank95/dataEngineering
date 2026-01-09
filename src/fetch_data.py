import yfinance as yf
import pandas as pd
import os
import sys
import time

# Add parent directory to path to import config_loader
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from config_loader import get_config
from datetime import datetime, timedelta

def fetch_data(ticker="AAPL", start_date="2020-01-01", end_date="2023-01-01"):
    """
    Fetches daily OHLCV data for a given ticker and saves it to a CSV file.
    
    Parameters:
        ticker (str): The stock or ETF symbol (default: "AAPL").
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
    """
    
    # define output path
    config = get_config()
    output_dir = config['paths']['raw_data_dir']
    os.makedirs(output_dir, exist_ok=True)
    file_path = f"{output_dir}/{ticker}_raw.csv"

    # Incremental update: if a raw file already exists, only fetch missing dates
    incremental_start = start_date
    if os.path.exists(file_path):
        try:
            existing = pd.read_csv(file_path, index_col=0, parse_dates=True)
            if not existing.empty:
                last_date = existing.index.max()
                # yfinance end date is exclusive, so start from last_date + 1 day
                incremental_start = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception as e:
            print(f"Warning: could not read existing raw file for {ticker}: {e}. Refetching from {start_date}.")

    if incremental_start >= end_date:
        print(f"No new data needed for {ticker}. Latest date in cache covers up to {end_date}.")
        return

    print(f"Fetching data for {ticker} from {incremental_start} to {end_date}...")

    max_retries = 3
    retry_delay = 5  # seconds
    df = pd.DataFrame()  # Initialize empty DataFrame

    for attempt in range(max_retries):
        try:
            df = yf.download(ticker, start=incremental_start, end=end_date, progress=False)
            if not df.empty:
                break  # Data fetched successfully
            else:
                print(f"Attempt {attempt + 1}: No data returned for {ticker}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error fetching data for {ticker}: {e}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    # Check if empty after all retries
    if df.empty:
        print(f"Warning: No new data found for {ticker} after {max_retries} attempts.")
        return

    # Fix for yfinance returning MultiIndex columns (Price, Ticker)
    if isinstance(df.columns, pd.MultiIndex):
        # Drop the ticker level (level 1) if it exists
        df.columns = df.columns.droplevel(1)

    # If we have existing data, append and drop duplicates; otherwise, create new file
    if os.path.exists(file_path):
        try:
            existing = pd.read_csv(file_path, index_col=0, parse_dates=True)
            combined = pd.concat([existing, df])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined.sort_index(inplace=True)
            combined.to_csv(file_path)
            print(f"Data updated at {file_path} (rows: {len(combined)})")
            return
        except Exception as e:
            print(f"Warning: could not merge with existing raw file for {ticker}: {e}. Overwriting.")

    # save to csv (fresh write)
    df.to_csv(file_path)
    print(f"Data saved to {file_path}")

def fetch_intraday_data(ticker="AAPL", interval="5m", period="5d"):
    """
    Fetches intraday data and UPDATES existing file if present (Separate Schema/Folder).
    
    Parameters:
        ticker (str): The stock symbol.
        interval (str): Intraday interval.
        period (str): Period to fetch (e.g. '5d').
    """
    print(f"Fetching intraday data for {ticker} (Interval: {interval})...")
    
    try:
        new_df = yf.download(ticker, interval=interval, period=period, progress=False)
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return

    if new_df.empty:
        print(f"Warning: No intraday data found for {ticker}")
        return

    # Fix MultiIndex
    if isinstance(new_df.columns, pd.MultiIndex):
        new_df.columns = new_df.columns.droplevel(1)

    # Ensure index is timezone-naive to mix with potential existing data easily or consistent
    if new_df.index.tz is not None:
        new_df.index = new_df.index.tz_localize(None)

    config = get_config()
    # Separate schema/folder for intraday
    output_dir = os.path.join(config['paths']['raw_data_dir'], "intraday")
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = f"{output_dir}/{ticker}_{interval}_raw.csv"
    
    # Incremental Update Logic
    if os.path.exists(file_path):
        try:
            old_df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            if old_df.index.tz is not None:
                old_df.index = old_df.index.tz_localize(None)
                
            # Combine and drop duplicates based on index (Date/Time)
            combined_df = pd.concat([old_df, new_df])
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            combined_df.sort_index(inplace=True)
            
            print(f"Updated {ticker} intraday data. Total rows: {len(combined_df)}")
            combined_df.to_csv(file_path)
        except Exception as e:
            print(f"Error updating existing file {file_path}: {e}")
            print("Overwriting with new data instead.")
            new_df.to_csv(file_path)
    else:
        print(f"Creating new intraday file for {ticker}. Rows: {len(new_df)}")
        new_df.to_csv(file_path)

if __name__ == "__main__":
    # execute function with default parameters
    fetch_data()
