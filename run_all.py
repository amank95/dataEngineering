"""
Master Orchestration Script
============================
Automates the complete stock market data pipeline workflow.

Workflow:
1. Run data pipeline (fetch, clean, engineer features)
2. Sync to Supabase (if enabled)
3. Start API server (optional)

Usage:
    python run_all.py                    # Run pipeline only
    python run_all.py --sync             # Run pipeline + manual sync
    python run_all.py --start-api        # Run pipeline + start API
    python run_all.py --sync --start-api # Complete workflow
"""

import argparse
import sys
import os
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_pipeline():
    """Execute the data pipeline."""
    logger.info("=" * 70)
    logger.info("STEP 1: Running Data Pipeline")
    logger.info("=" * 70)
    
    try:
        # Import and run pipeline
        from data_pipeline import main as pipeline_main
        from dotenv import load_dotenv
        
        load_dotenv()
        result = pipeline_main()
        
        if result['success']:
            logger.info(f"✓ Pipeline completed: {result['processed_tickers']}/{result['total_tickers']} tickers processed")
            return True
        else:
            logger.error("✗ Pipeline failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Pipeline execution failed: {e}")
        return False


def sync_to_supabase(force=False):
    """Sync data to Supabase."""
    logger.info("=" * 70)
    logger.info("STEP 2: Syncing to Supabase")
    logger.info("=" * 70)
    
    try:
        from supabase_ingestion import SupabaseIngestion
        from config_loader import get_output_file
        from dotenv import load_dotenv
        
        load_dotenv()
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("✗ Supabase credentials not found in .env")
            logger.warning("  Set SUPABASE_URL and SUPABASE_KEY to enable sync")
            return False
        
        ingestion = SupabaseIngestion(supabase_url, supabase_key)
        summary = ingestion.sync_data(get_output_file(), dry_run=False)
        
        if summary['error_count'] == 0:
            logger.info(f"✓ Supabase sync completed: {summary['success_count']} records synced")
            logger.info(f"  Duration: {summary['duration_seconds']:.2f}s")
            logger.info(f"  Throughput: {summary['records_per_second']:.2f} records/sec")
            return True
        else:
            logger.warning(f"⚠ Sync completed with errors: {summary['error_count']} failed")
            return False
            
    except ImportError as e:
        logger.error(f"✗ Required module not found: {e}")
        logger.error("  Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        logger.error(f"✗ Supabase sync failed: {e}")
        return False


def start_api_server():
    """Start the FastAPI server."""
    logger.info("=" * 70)
    logger.info("STEP 3: Starting API Server")
    logger.info("=" * 70)
    logger.info("API will be available at: http://127.0.0.1:8000")
    logger.info("Interactive docs at: http://127.0.0.1:8000/docs")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 70)
    
    try:
        # Start uvicorn server
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "api:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ])
        
    except KeyboardInterrupt:
        logger.info("\nAPI server stopped by user")
    except Exception as e:
        logger.error(f"✗ Failed to start API server: {e}")
        logger.error("  Make sure uvicorn is installed: pip install uvicorn")


def main():
    """Main orchestration function."""
    parser = argparse.ArgumentParser(
        description='Orchestrate the complete stock market data pipeline'
    )
    parser.add_argument(
        '--sync',
        action='store_true',
        help='Force sync to Supabase (even if auto_sync is disabled)'
    )
    parser.add_argument(
        '--start-api',
        action='store_true',
        help='Start the API server after pipeline execution'
    )
    parser.add_argument(
        '--skip-pipeline',
        action='store_true',
        help='Skip pipeline execution (useful for testing API/sync only)'
    )
    
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    logger.info("╔" + "═" * 68 + "╗")
    logger.info("║" + " " * 15 + "STOCK MARKET DATA PIPELINE" + " " * 27 + "║")
    logger.info("║" + " " * 20 + "Complete Workflow Automation" + " " * 20 + "║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info("")
    
    success = True
    
    # Step 1: Run Pipeline
    if not args.skip_pipeline:
        if not run_pipeline():
            logger.error("\n❌ Pipeline failed. Stopping workflow.")
            sys.exit(1)
        logger.info("")
    else:
        logger.info("Skipping pipeline execution (--skip-pipeline flag)")
        logger.info("")
    
    # Step 2: Sync to Supabase
    if args.sync:
        if not sync_to_supabase(force=True):
            logger.warning("\n⚠ Supabase sync failed, but continuing...")
        logger.info("")
    
    # Step 3: Start API Server
    if args.start_api:
        start_api_server()
    
    # Summary
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info("")
    logger.info("╔" + "═" * 68 + "╗")
    logger.info("║" + " " * 25 + "WORKFLOW COMPLETE" + " " * 26 + "║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info(f"Total execution time: {duration:.2f} seconds")
    logger.info("")
    
    if not args.start_api:
        logger.info("💡 Tip: Use --start-api to automatically start the API server")
        logger.info("   Example: python run_all.py --sync --start-api")
    
    logger.info("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nWorkflow interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\n❌ Workflow failed: {e}")
        sys.exit(1)
