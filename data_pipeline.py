import pandas as pd
import os
import sys
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fetch_data import fetch_data
from clean_data import clean_data
from feature_engineering import generate_features
from config_loader import get_config, get_tickers, get_start_date, get_end_date, get_processed_dir, get_output_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

# Load configuration from config.yaml (with defaults as fallback)
TICKERS = get_tickers()
START_DATE = get_start_date()
END_DATE = get_end_date()
PROCESSED_DIR = get_processed_dir()
OUTPUT_FILE = get_output_file()
CONFIG = get_config()


def get_dynamic_rename_map():
    """
    Generates a column rename map dynamically based on configuration.
    """
    rename_map = {
        'ticker': 'Ticker',
        'macd': 'MACD',
        'daily_return': 'Return',
        'volatility': 'Volatility',
    }
    
    # Dynamic SMA mapping
    sma_periods = CONFIG.get('features', {}).get('sma_periods', [20, 50])
    for period in sma_periods:
        rename_map[f'ma_{period}'] = f'SMA_{period}'
        
    # Dynamic RSI mapping
    rsi_period = CONFIG.get('features', {}).get('rsi_period', 14)
    rename_map[f'rsi_{rsi_period}'] = f'RSI_{rsi_period}'

    return rename_map


def process_ticker(ticker):
    """
    Process a single ticker: fetch, clean, feature engineer, and read final CSV.
    Returns processed dataframe or None if failed.
    """
    logger.info(f"Processing {ticker}...")
    
    try:
        # 1. Fetch Data
        fetch_data(ticker=ticker, start_date=START_DATE, end_date=END_DATE)
        
        # 2. Clean Data
        clean_data(ticker=ticker)
        
        # 3. Feature Engineering
        generate_features(ticker=ticker)
        
        # 4. Read back the processed data for consolidation
        final_path = f"data/processed/{ticker}_final.csv"
        if os.path.exists(final_path):
            df = pd.read_csv(final_path)
            
            # Use dynamic rename map
            rename_map = get_dynamic_rename_map()
            df.rename(columns=rename_map, inplace=True)
            
            # Ensure Ticker column exists
            df['Ticker'] = ticker
            
            return df
        else:
            logger.warning(f"{final_path} not found for {ticker}")
            return None
            
    except Exception as e:
        logger.error(f"Error processing {ticker}: {e}")
        return None


def main():
    logger.info("Starting Data Pipeline...")
    logger.info(f"Processing {len(TICKERS)} tickers from {START_DATE} to {END_DATE}")
    
    # Ensure processed directory exists
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    all_data = []
    failed_tickers = []

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=min(8, len(TICKERS))) as executor:
        future_to_ticker = {executor.submit(process_ticker, ticker): ticker for ticker in TICKERS}
        
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            result = future.result()
            if result is not None:
                all_data.append(result)
            else:
                failed_tickers.append(ticker)

    # Consolidate
    if all_data:
        logger.info("Consolidating data...")
        master_data = pd.concat(all_data, ignore_index=True)
        
        # Handle duplicate columns (from merge conflicts in data)
        base_cols = {}
        for col in master_data.columns:
            base = col.split('.')[0]
            base_cols.setdefault(base, []).append(col)
        
        for base, cols in base_cols.items():
            if len(cols) > 1:
                master_data[base] = master_data[cols].bfill(axis=1).iloc[:, 0]
                master_data.drop(columns=[c for c in cols if c != base], inplace=True)
        
        # Save to Parquet
        logger.info(f"Saving to {OUTPUT_FILE}...")
        master_data.to_parquet(OUTPUT_FILE, index=False)
        logger.info("Pipeline completed successfully.")
    else:
        logger.warning("No data to consolidate.")

    if failed_tickers:
        logger.warning(f"Failed to process tickers: {failed_tickers}")


if __name__ == "__main__":
    start_time = time.time()
    main()
    logger.info(f"Total time taken: {time.time() - start_time:.2f} seconds")
