import pandas as pd
import os
import sys

# Add src to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fetch_data import fetch_data
from clean_data import clean_data
from feature_engineering import generate_features
from config_loader import get_tickers, get_start_date, get_end_date, get_processed_dir, get_output_file

# Load configuration from config.yaml (with defaults as fallback)
TICKERS = get_tickers()
START_DATE = get_start_date()
END_DATE = get_end_date()
PROCESSED_DIR = get_processed_dir()
OUTPUT_FILE = get_output_file()

def main():
    print("Starting Data Pipeline...")
    
    # Ensure processed directory exists
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    all_data = []

    for ticker in TICKERS:
        print(f"\nProcessing {ticker}...")
        
        # 1. Fetch Data
        # fetch_data saves to data/raw/{ticker}_raw.csv
        fetch_data(ticker=ticker, start_date=START_DATE, end_date=END_DATE)
        
        # 2. Clean Data
        # clean_data reads raw, saves to data/processed/{ticker}_cleaned.csv
        clean_data(ticker=ticker)
        
        # 3. Feature Engineering
        # generate_features reads cleaned, saves to data/processed/{ticker}_final.csv
        # We modified it to include RSI_14
        generate_features(ticker=ticker)
        
        # 4. Read back the processed data for consolidation
        final_path = f"data/processed/{ticker}_final.csv"
        if os.path.exists(final_path):
            df = pd.read_csv(final_path)
            # Standardize column names as per strict requirements
            # Current columns in feature_engineering.py: 'daily_return', 'ma_20', 'ma_50', 'rsi_14'
            # We need: 'Return', 'SMA_20', 'SMA_50', 'RSI_14'
            
            rename_map = {
                'ticker': 'Ticker',
                'macd': 'MACD',
                'daily_return': 'Return',
                'ma_20': 'SMA_20',
                'ma_50': 'SMA_50',
                'rsi_14': 'RSI_14', # Capitalize if needed, though we set it as rsi_14 in script
                'volatility': 'Volatility'

    # 'rsi_14': 'RSI',

    # 'daily_return': 'Daily_Return',
    # 'ema_20': 'EMA_20',
    # 'ema_50': 'EMA_50',
    # 'sma_20': 'SMA_20',
    # 'sma_50': 'SMA_50'
            
            }
            df.rename(columns=rename_map, inplace=True)
            
            # Add Ticker column for consolidation
            df['Ticker'] = ticker
            
            all_data.append(df)
        else:
            print(f"Warning: {final_path} not found for {ticker}")

    # 5. Consolidate
    if all_data:
        print("\nConsolidating data...")
        master_data = pd.concat(all_data, ignore_index=True)
        
        # Ensure correct column order/presence if needed, or just save
        # User asked for 'Return', 'SMA_20', 'SMA_50', 'RSI_14' columns to exist
        
        # Save to Parquet
        print(f"Saving to {OUTPUT_FILE}...")
        master_data.to_parquet(OUTPUT_FILE, index=False)
        print("Pipeline completed successfully.")
    else:
        print("No data to consolidate.")

if __name__ == "__main__":
    main()
