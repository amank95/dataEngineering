"""
Configuration Loader
===================
Loads configuration from YAML file with fallback to defaults.
Ensures backward compatibility if config file doesn't exist.
"""

import os
import yaml
from typing import Dict, List, Any
from datetime import datetime, timedelta

# Default configuration (fallback if config.yaml doesn't exist)
# Indian tickers with .NS suffix for NSE (National Stock Exchange)
DEFAULT_CONFIG = {
    'tickers': [
        # Indian IT Companies
        'INFY.NS', 'TCS.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS',
        # Indian Government Companies
        'ONGC.NS', 'IOC.NS', 'NTPC.NS', 'COALINDIA.NS', 'SAIL.NS'
    ],
    'dates': {
        'start_date': '2022-01-01',
        'end_date': 'today'  # Will use current system date
    },
    'paths': {
        'raw_data_dir': 'data/raw',
        'processed_data_dir': 'data/processed',
        'output_file': 'data/processed/features_dataset.parquet'
    },
    'features': {
        'sma_periods': [20, 50],
        'rsi_period': 14,
        'volatility_window': 20,
        'macd_fast': 12,
        'macd_slow': 26
    },
    'currency': {
        'source_currency': 'USD',
        'target_currency': 'INR',
        'exchange_rate_ticker': 'USDINR=X'
    },
    'processing': {
        'drop_na': True,
        'validate_ohlc': True,
        'min_data_points': 50
    }
}


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Parameters:
        config_path (str): Path to config file (default: 'config.yaml')
    
    Returns:
        dict: Configuration dictionary with defaults merged
    """
    # Start with defaults
    config = DEFAULT_CONFIG.copy()
    
    # Try to load from file if it exists
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    # Deep merge: update nested dicts properly
                    config = _deep_merge(config, file_config)
                    print(f"✅ Loaded configuration from {config_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not load config from {config_path}: {e}")
            print(f"   Using default configuration.")
    else:
        print(f"ℹ️  Config file not found at {config_path}, using defaults.")
    
    return config


def _deep_merge(base: Dict, update: Dict) -> Dict:
    """Recursively merge two dictionaries."""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_config() -> Dict[str, Any]:
    """
    Get the current configuration.
    This is a convenience function that loads config on first call.
    """
    if not hasattr(get_config, '_config'):
        get_config._config = load_config()
    return get_config._config


# Convenience functions for common config values
def get_tickers() -> List[str]:
    """Get list of tickers from config."""
    return get_config()['tickers']


def get_start_date() -> str:
    """Get start date from config."""
    return get_config()['dates']['start_date']


def get_end_date() -> str:
    """
    Get end date from config.
    If end_date is 'today', 'now', or None, returns current system date.
    Works on any device (phone, laptop, etc.) using system date.
    """
    end_date = get_config()['dates']['end_date']
    
    # If end_date is 'today', 'now', None, or empty, use current system date
    if end_date is None or end_date == '' or str(end_date).lower() in ['today', 'now', 'current']:
        # Get current system date in YYYY-MM-DD format
        # Get current system date + 1 day (because yfinance end_date is exclusive)
        # We want to include "today", so we must set end_date to "tomorrow"
        tomorrow = datetime.now() + timedelta(days=1)
        return tomorrow.strftime('%Y-%m-%d')
    
    return end_date


def get_processed_dir() -> str:
    """Get processed data directory from config."""
    return get_config()['paths']['processed_data_dir']


def get_output_file() -> str:
    """Get output file path from config."""
    return get_config()['paths']['output_file']


if __name__ == "__main__":
    # Test config loading
    config = load_config()
    print("\nCurrent Configuration:")
    print(f"Tickers: {config['tickers']}")
    print(f"Date Range: {config['dates']['start_date']} to {get_end_date()}")
    print(f"Output File: {config['paths']['output_file']}")
    print(f"\n💡 End date uses system date: {get_end_date()}")

