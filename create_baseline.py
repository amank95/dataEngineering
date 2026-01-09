"""
Create Baseline for Drift Detection
====================================
Generates a baseline Parquet file from the current processed dataset.
This baseline represents the "training phase" distribution that will be
compared against future live data.

Usage:
    python create_baseline.py
    python create_baseline.py --source data/processed/features_dataset.parquet
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import pandas as pd
from config_loader import get_output_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_BASELINE_PATH = "data/processed/baseline_features.parquet"


def create_baseline(source_path: str, output_path: str):
    """
    Create a baseline dataset from the current processed data.
    
    Args:
        source_path: Path to the current features dataset (Parquet)
        output_path: Path where baseline will be saved
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    logger.info(f"Loading data from {source_path}...")
    df = pd.read_parquet(source_path)
    
    logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
    logger.info(f"Columns: {list(df.columns)}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save as baseline
    df.to_parquet(output_path, index=False)
    logger.info(f"✓ Baseline saved to {output_path}")
    
    # Print summary statistics for key features
    key_features = ['sma_20', 'rsi_14', 'volatility']
    available_features = [f for f in key_features if f in df.columns]
    
    if available_features:
        logger.info("\nBaseline Summary Statistics:")
        logger.info("=" * 60)
        for feature in available_features:
            stats = df[feature].describe()
            logger.info(f"{feature}:")
            logger.info(f"  Mean: {stats['mean']:.4f}")
            logger.info(f"  Std:  {stats['std']:.4f}")
            logger.info(f"  Min:  {stats['min']:.4f}")
            logger.info(f"  Max:  {stats['max']:.4f}")
            logger.info(f"  Count: {stats['count']:.0f}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Baseline creation complete!")
    logger.info(f"Next pipeline run will compare live data against this baseline.")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Create baseline dataset for drift detection'
    )
    parser.add_argument(
        '--source',
        type=str,
        default=None,
        help=f'Source Parquet file (default: uses config_loader.get_output_file())'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=DEFAULT_BASELINE_PATH,
        help=f'Output baseline path (default: {DEFAULT_BASELINE_PATH})'
    )
    
    args = parser.parse_args()
    
    # Use config loader if source not specified
    source_path = args.source or get_output_file()
    
    try:
        create_baseline(source_path, args.output)
        logger.info("\n✓ Success! Baseline is ready for drift detection.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n✗ Failed to create baseline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

