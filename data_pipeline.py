import pandas as pd
import os
import sys
import logging
import time

# Add src to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fetch_data import fetch_data
from clean_data import clean_data
from feature_engineering import generate_features
from config_loader import get_config, get_tickers, get_start_date, get_end_date, get_processed_dir, get_output_file

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

# Load configuration
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
        # 'rsi_14' will be handled dynamically if period changes, 
        # but for now we map the config-based key to standard output
    }
    
    # Dynamic SMA mapping
    sma_periods = CONFIG.get('features', {}).get('sma_periods', [20, 50])
    for period in sma_periods:
        rename_map[f'ma_{period}'] = f'SMA_{period}'
        
    # Dynamic RSI mapping
    rsi_period = CONFIG.get('features', {}).get('rsi_period', 14)
    rename_map[f'rsi_{rsi_period}'] = f'RSI_{rsi_period}'

    return rename_map

def main():
    logger.info("Starting Data Pipeline...")
    logger.info(f"Processing {len(TICKERS)} tickers from {START_DATE} to {END_DATE}")
    
    # Ensure processed directory exists
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    all_data = []
    failed_tickers = []

    for ticker in TICKERS:
        logger.info(f"Processing {ticker}...")
        try:
            # 1. Fetch Data
            fetch_data(ticker=ticker, start_date=START_DATE, end_date=END_DATE)
            
            # 2. Clean Data
            clean_data(ticker=ticker)
            
            # 3. Feature Engineering
            generate_features(ticker=ticker)
            
            # 4. Read back and standardise
            final_path = os.path.join(PROCESSED_DIR, f"{ticker}_final.csv")
            
            if os.path.exists(final_path):
                df = pd.read_csv(final_path)
                
                # Apply Dynamic Renaming
                rename_map = get_dynamic_rename_map()
                df.rename(columns=rename_map, inplace=True)
                
                # Add Ticker column
                df['Ticker'] = ticker
                
                all_data.append(df)
            else:
                logger.warning(f"File not found: {final_path}")
                failed_tickers.append(ticker)

        except Exception as e:
            logger.error(f"Pipeline failed for {ticker}: {e}", exc_info=True)
            failed_tickers.append(ticker)

    # 5. Consolidate
    if all_data:
        logger.info("Consolidating data...")
        master_data = pd.concat(all_data, ignore_index=True)
        
        # Save to Parquet
        logger.info(f"Saving to {OUTPUT_FILE}...")
        
        # Ensure output directory exists'
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        master_data.to_parquet(OUTPUT_FILE, index=False)
        logger.info("Pipeline completed successfully.")
    else:
        logger.warning("No data to consolidate.")

    if failed_tickers:
        logger.warning(f"Failed to process tickers: {failed_tickers}")

if __name__ == "__main__":
    start_time = time.time()
    main()
    logger.info(f"Total execution time: {time.time() - start_time:.2f} seconds")
