import pandas as pd
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add src to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fetch_data import fetch_data
from clean_data import clean_data
from feature_engineering import generate_features
from config_loader import get_tickers, get_start_date, get_end_date, get_processed_dir, get_output_file

# Load configuration
start = time.time()
TICKERS = get_tickers()
START_DATE = get_start_date()
END_DATE = get_end_date()
PROCESSED_DIR = get_processed_dir()
OUTPUT_FILE = get_output_file()


def process_ticker(ticker):
    """
    Process a single ticker: fetch, clean, feature engineer, and read final CSV
    Returns processed dataframe or None if failed.
    """
    print(f"\nProcessing {ticker}...")

    try:
        # 1. Fetch Data
        fetch_data(ticker=ticker, start_date=START_DATE, end_date=END_DATE)

        # 2. Clean Data
        clean_data(ticker=ticker)

        # 3. Feature Engineering
        generate_features(ticker=ticker)

        # 4. Read processed data
        final_path = f"data/processed/{ticker}_final.csv"
        if os.path.exists(final_path):
            df = pd.read_csv(final_path)
            
            # Rename columns as per requirement
            rename_map = {
                'ticker': 'Ticker',
                'macd': 'MACD',
                'daily_return': 'Return',
                'ma_20': 'SMA_20',
                'ma_50': 'SMA_50',
                'rsi_14': 'RSI_14',
                'volatility': 'Volatility'
            }
            df.rename(columns=rename_map, inplace=True)
            
            # Ensure Ticker column exists
            df['Ticker'] = ticker
            return df
        else:
            print(f"Warning: {final_path} not found for {ticker}")
            return None

    except Exception as e:
        print(f"Error processing {ticker}: {e}")
        return None


def main():
    print("Starting Data Pipeline...")

    # Ensure processed directory exists
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    all_data = []

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=min(8, len(TICKERS))) as executor:
        future_to_ticker = {executor.submit(process_ticker, ticker): ticker for ticker in TICKERS}

        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            result = future.result()
            if result is not None:
                all_data.append(result)

    # Consolidate
    if all_data:
        print("\nConsolidating data...")
        master_data = pd.concat(all_data, ignore_index=True)
        base_cols = {}
#changes done here  for 
        for col in master_data.columns:
            base = col.split('.')[0]
            base_cols.setdefault(base, []).append(col)
        
        for base, cols in base_cols.items():
            if len(cols) > 1:
                master_data[base] = master_data[cols].bfill(axis=1).iloc[:, 0]
                master_data.drop(columns=[c for c in cols if c != base], inplace=True)
#till here 
        print(f"Saving to {OUTPUT_FILE}...")
        master_data.to_csv(os.path.join(PROCESSED_DIR, "master_data.csv"), index=False)
        print("Pipeline completed successfully.")
    else:
        print("No data to consolidate.")


if __name__ == "__main__":
    main()
    print("time taken ", time.time()-start)
