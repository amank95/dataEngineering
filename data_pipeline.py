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
    Column names match Supabase schema (lowercase with underscores).
    """
    rename_map = {
        # Keep lowercase to match Supabase schema
        'macd': 'macd',
        'daily_return': 'daily_return',
        'volatility': 'volatility',
    }
    
    # Dynamic SMA mapping (lowercase)
    sma_periods = CONFIG.get('features', {}).get('sma_periods', [20, 50])
    for period in sma_periods:
        rename_map[f'ma_{period}'] = f'sma_{period}'
        
    # Dynamic RSI mapping (lowercase)
    rsi_period = CONFIG.get('features', {}).get('rsi_period', 14)
    rename_map[f'rsi_{rsi_period}'] = f'rsi_{rsi_period}'

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
            # Read CSV with date as index (as saved by feature_engineering.py)
            df = pd.read_csv(final_path, index_col='date', parse_dates=True)
            
            # Reset index to make 'date' a regular column
            df.reset_index(inplace=True)
            
            # Use dynamic rename map
            rename_map = get_dynamic_rename_map()
            df.rename(columns=rename_map, inplace=True)
            
            # Ensure ticker column exists (lowercase to match Supabase schema)
            df['ticker'] = ticker
            
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
        
        # Optional: Auto-sync to Supabase
        if CONFIG.get('supabase', {}).get('auto_sync', False):
            logger.info("Auto-sync to Supabase is enabled. Starting sync...")
            try:
                from supabase_ingestion import SupabaseIngestion
                
                supabase_url = os.getenv('SUPABASE_URL')
                supabase_key = os.getenv('SUPABASE_KEY')
                
                if supabase_url and supabase_key:
                    batch_size = CONFIG.get('supabase', {}).get('batch_size', 1000)
                    ingestion = SupabaseIngestion(supabase_url, supabase_key, batch_size)
                    sync_summary = ingestion.sync_data(OUTPUT_FILE, dry_run=False)
                    
                    logger.info(f"Supabase sync completed: {sync_summary['success_count']} records synced")
                else:
                    logger.warning("Supabase credentials not found in environment. Skipping sync.")
                    logger.warning("Set SUPABASE_URL and SUPABASE_KEY in .env file to enable auto-sync.")
                    
            except ImportError:
                logger.error("supabase_ingestion module not found. Skipping sync.")
            except Exception as e:
                logger.error(f"Supabase sync failed: {e}")
                logger.warning("Pipeline data saved to Parquet, but Supabase sync failed.")
        
    else:
        logger.warning("No data to consolidate.")

    if failed_tickers:
        logger.warning(f"Failed to process tickers: {failed_tickers}")
    
    return {
        'success': len(all_data) > 0,
        'total_tickers': len(TICKERS),
        'processed_tickers': len(all_data),
        'failed_tickers': failed_tickers
    }


if __name__ == "__main__":
    start_time = time.time()
    
    # Load environment variables for Supabase
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv not installed. Environment variables must be set manually.")
    
    result = main()
    
    duration = time.time() - start_time
    logger.info(f"Total time taken: {duration:.2f} seconds")
    
    if result['success']:
        logger.info("=" * 60)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Status: SUCCESS")
        logger.info(f"Processed: {result['processed_tickers']}/{result['total_tickers']} tickers")
        if result['failed_tickers']:
            logger.info(f"Failed: {', '.join(result['failed_tickers'])}")
        logger.info("=" * 60)
    else:
        logger.error("Pipeline failed - no data was processed")
        sys.exit(1)

