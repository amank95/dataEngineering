"""
Supabase Ingestion Module
==========================
Loads stock market features from Parquet file into Supabase (Postgres).

Features:
- Batch upsert with conflict resolution
- Progress tracking and logging
- Error handling and retry logic
- Dry-run mode for testing
- Configurable batch size

Usage:
    python supabase_ingestion.py
    python supabase_ingestion.py --dry-run
    python supabase_ingestion.py --batch-size 500
"""

import os
import sys
import logging
import argparse
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

from drift_monitor import run_drift_monitor

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('supabase_ingestion.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
TABLE_NAME = 'stock_features'
DEFAULT_BATCH_SIZE = 1000


class SupabaseIngestion:
    """Handles ingestion of stock features into Supabase."""
    
    def __init__(self, supabase_url: str, supabase_key: str, batch_size: int = DEFAULT_BATCH_SIZE):
        """
        Initialize Supabase client.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key (service role for write access)
            batch_size: Number of records per batch
        """
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        self.batch_size = batch_size
        logger.info(f"Initialized Supabase client with batch size: {batch_size}")
    
    def load_parquet_data(self, parquet_path: str) -> pd.DataFrame:
        """
        Load data from Parquet file.
        
        Args:
            parquet_path: Path to Parquet file
            
        Returns:
            DataFrame with stock features
        """
        logger.info(f"Loading data from: {parquet_path}")
        
        if not os.path.exists(parquet_path):
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")
        
        df = pd.read_parquet(parquet_path)
        logger.info(f"Loaded {len(df)} records from Parquet")
        logger.info(f"Columns: {list(df.columns)}")
        
        return df
    
    def prepare_records(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Transform DataFrame to list of dictionaries for Supabase.
        
        Args:
            df: DataFrame with stock features
            
        Returns:
            List of record dictionaries
        """
        logger.info("Preparing records for Supabase...")
        
        # Ensure required columns exist
        required_cols = ['Ticker', 'Date'] if 'Ticker' in df.columns else ['ticker', 'date']
        
        # Standardize column names to lowercase
        df_copy = df.copy()
        df_copy.columns = [col.lower() for col in df_copy.columns]
        
        # Handle date column - ensure it's in YYYY-MM-DD format
        if 'date' in df_copy.columns:
            df_copy['date'] = pd.to_datetime(df_copy['date']).dt.strftime('%Y-%m-%d')

        # Ensure integer columns match Supabase schema (e.g., volume is BIGINT)
        # Convert float-like values such as 1286852.0 -> 1286852
        int_like_cols = ['volume']
        for col in int_like_cols:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(
                    lambda v: int(v) if v is not None and pd.notna(v) else None
                )
        
        # Replace NaN with None for proper NULL handling in Postgres
        df_copy = df_copy.where(pd.notnull(df_copy), None)
        
        # Convert to list of dictionaries
        records = df_copy.to_dict('records')
        
        logger.info(f"Prepared {len(records)} records")
        return records
    
    def upsert_batch(self, records: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
        """
        Upsert a batch of records to Supabase.
        
        Args:
            records: List of record dictionaries
            dry_run: If True, don't actually insert data
            
        Returns:
            Response from Supabase
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would upsert {len(records)} records")
            logger.debug(f"Sample record: {records[0] if records else 'No records'}")
            return {"status": "dry_run", "count": len(records)}
        
        try:
            # Supabase upsert - will insert or update based on primary key (ticker, date)
            response = self.client.table(TABLE_NAME).upsert(
                records,
                on_conflict='ticker,date'  # Composite primary key
            ).execute()
            
            return response
            
        except Exception as e:
            logger.error(f"Error upserting batch: {e}")
            raise
    
    def sync_data(self, parquet_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Main sync function: Load from Parquet and upsert to Supabase.
        
        Args:
            parquet_path: Path to Parquet file
            dry_run: If True, don't actually insert data
            
        Returns:
            Summary statistics
        """
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Starting Supabase sync")
        logger.info("=" * 60)
        
        # Load data
        df = self.load_parquet_data(parquet_path)
        total_records = len(df)
        
        # Prepare records
        records = self.prepare_records(df)
        
        # Batch upsert
        batches = [records[i:i + self.batch_size] for i in range(0, len(records), self.batch_size)]
        total_batches = len(batches)
        
        logger.info(f"Processing {total_records} records in {total_batches} batches")
        
        success_count = 0
        error_count = 0
        
        for i, batch in enumerate(batches, 1):
            try:
                logger.info(f"Processing batch {i}/{total_batches} ({len(batch)} records)...")
                response = self.upsert_batch(batch, dry_run=dry_run)
                success_count += len(batch)
                
                if not dry_run:
                    logger.info(f"✓ Batch {i} completed successfully")
                
            except Exception as e:
                logger.error(f"✗ Batch {i} failed: {e}")
                error_count += len(batch)
                # Continue with next batch instead of failing completely
                continue
        
        # Summary
        duration = (datetime.now() - start_time).total_seconds()
        
        summary = {
            "total_records": total_records,
            "success_count": success_count,
            "error_count": error_count,
            "batches_processed": total_batches,
            "duration_seconds": duration,
            "records_per_second": success_count / duration if duration > 0 else 0,
            "dry_run": dry_run
        }
        
        logger.info("=" * 60)
        logger.info("Sync Summary")
        logger.info("=" * 60)
        logger.info(f"Total Records: {summary['total_records']}")
        logger.info(f"Success: {summary['success_count']}")
        logger.info(f"Errors: {summary['error_count']}")
        logger.info(f"Duration: {summary['duration_seconds']:.2f}s")
        logger.info(f"Throughput: {summary['records_per_second']:.2f} records/sec")
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        logger.info("=" * 60)

        # Run model-aware drift monitoring after successful live sync
        if not dry_run and summary["success_count"] > 0:
            try:
                logger.info("Starting model-aware feature drift detection...")
                drift_summary = run_drift_monitor(
                    parquet_path=parquet_path,
                    supabase_client=self.client,
                )
                logger.info(
                    f"Drift monitor completed: {drift_summary.get('alerts_created', 0)} alerts, "
                    f"duration={drift_summary.get('duration_seconds', 0):.2f}s, "
                    f"status={drift_summary.get('status')}"
                )
            except Exception as e:
                logger.error(f"Drift monitor failed (non-fatal): {e}")

        return summary


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(description='Sync Parquet data to Supabase')
    parser.add_argument(
        '--parquet-file',
        type=str,
        default='data/processed/features_dataset.parquet',
        help='Path to Parquet file (default: data/processed/features_dataset.parquet)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f'Batch size for upserts (default: {DEFAULT_BATCH_SIZE})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without actually inserting data'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize ingestion
        ingestion = SupabaseIngestion(
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_KEY,
            batch_size=args.batch_size
        )
        
        # Sync data
        summary = ingestion.sync_data(
            parquet_path=args.parquet_file,
            dry_run=args.dry_run
        )
        
        # Exit with appropriate code
        if summary['error_count'] > 0:
            logger.warning("Sync completed with errors")
            sys.exit(1)
        else:
            logger.info("Sync completed successfully")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
