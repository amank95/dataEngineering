"""
Data Quality Validation Module
==============================
Provides data validation, outlier detection, and data freshness checks.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


def validate_ohlc(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validates OHLC (Open, High, Low, Close) data relationships.
    
    Rules:
    - High >= Low (always)
    - High >= Open (usually)
    - High >= Close (usually)
    - Low <= Open (usually)
    - Low <= Close (usually)
    - Close > 0 (must be positive)
    
    Parameters:
        df (pd.DataFrame): DataFrame with OHLC columns
    
    Returns:
        tuple: (is_valid, list of error messages)
    """
    errors = []
    
    required_cols = ['open', 'high', 'low', 'close']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return False, [f"Missing required columns: {missing_cols}"]
    
    # Check for negative or zero prices
    if (df['close'] <= 0).any():
        errors.append("Found zero or negative close prices")
    
    if (df['open'] <= 0).any():
        errors.append("Found zero or negative open prices")
    
    # Validate High >= Low (must always be true)
    invalid_hl = df['high'] < df['low']
    if invalid_hl.any():
        count = invalid_hl.sum()
        errors.append(f"High < Low violation: {count} rows")
    
    # Validate High >= Open (should be true, but allow small tolerance for data issues)
    invalid_ho = df['high'] < df['open']
    if invalid_ho.any():
        count = invalid_ho.sum()
        errors.append(f"High < Open violation: {count} rows (tolerance allowed)")
    
    # Validate High >= Close
    invalid_hc = df['high'] < df['close']
    if invalid_hc.any():
        count = invalid_hc.sum()
        errors.append(f"High < Close violation: {count} rows (tolerance allowed)")
    
    # Validate Low <= Open
    invalid_lo = df['low'] > df['open']
    if invalid_lo.any():
        count = invalid_lo.sum()
        errors.append(f"Low > Open violation: {count} rows (tolerance allowed)")
    
    # Validate Low <= Close
    invalid_lc = df['low'] > df['close']
    if invalid_lc.any():
        count = invalid_lc.sum()
        errors.append(f"Low > Close violation: {count} rows (tolerance allowed)")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def detect_outliers(df: pd.DataFrame, method: str = 'iqr', threshold: float = 3.0) -> Dict[str, pd.Series]:
    """
    Detects outliers in price and volume data.
    
    Parameters:
        df (pd.DataFrame): DataFrame with price/volume columns
        method (str): 'iqr' (Interquartile Range) or 'zscore' (Z-score)
        threshold (float): Threshold for outlier detection
    
    Returns:
        dict: Dictionary with column names as keys and boolean Series as values
              (True = outlier, False = normal)
    """
    outliers = {}
    
    # Columns to check for outliers
    price_cols = ['open', 'high', 'low', 'close']
    volume_col = 'volume'
    
    for col in price_cols:
        if col not in df.columns:
            continue
            
        if method == 'iqr':
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            outliers[col] = (df[col] < lower_bound) | (df[col] > upper_bound)
        
        elif method == 'zscore':
            z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
            outliers[col] = z_scores > threshold
    
    # Check volume outliers
    if volume_col in df.columns:
        if method == 'iqr':
            Q1 = df[volume_col].quantile(0.25)
            Q3 = df[volume_col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            outliers[volume_col] = (df[volume_col] < lower_bound) | (df[volume_col] > upper_bound)
        elif method == 'zscore':
            z_scores = np.abs((df[volume_col] - df[volume_col].mean()) / df[volume_col].std())
            outliers[volume_col] = z_scores > threshold
    
    return outliers


def check_data_freshness(file_path: str, max_age_hours: int = 24) -> Tuple[bool, str]:
    """
    Checks if data file is fresh (recently updated).
    
    Parameters:
        file_path (str): Path to data file
        max_age_hours (int): Maximum age in hours before data is considered stale
    
    Returns:
        tuple: (is_fresh, message)
    """
    import os
    
    if not os.path.exists(file_path):
        return False, f"File does not exist: {file_path}"
    
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    age_hours = (datetime.now() - file_mod_time).total_seconds() / 3600
    
    if age_hours > max_age_hours:
        return False, f"Data is stale: {age_hours:.1f} hours old (max: {max_age_hours} hours)"
    
    return True, f"Data is fresh: {age_hours:.1f} hours old"


def validate_data_ranges(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validates that data values are within reasonable ranges.
    
    Parameters:
        df (pd.DataFrame): DataFrame to validate
    
    Returns:
        tuple: (is_valid, list of warnings)
    """
    warnings = []
    
    # Check price ranges (should be positive and reasonable)
    price_cols = ['open', 'high', 'low', 'close']
    for col in price_cols:
        if col not in df.columns:
            continue
        
        if (df[col] <= 0).any():
            warnings.append(f"{col}: Contains zero or negative values")
        
        # Check for extremely high values (potential data errors)
        if df[col].max() > 1e6:  # More than 1 million
            warnings.append(f"{col}: Contains very high values (max: {df[col].max():.2f})")
    
    # Check volume (should be non-negative)
    if 'volume' in df.columns:
        if (df['volume'] < 0).any():
            warnings.append("volume: Contains negative values")
    
    # Check for missing trading days (gaps in date index)
    if isinstance(df.index, pd.DatetimeIndex):
        date_diff = df.index.to_series().diff()
        # Check for gaps larger than 5 days (weekends + holidays are normal)
        large_gaps = date_diff > pd.Timedelta(days=5)
        if large_gaps.any():
            gap_count = large_gaps.sum()
            warnings.append(f"Found {gap_count} large date gaps (>5 days) - may indicate missing data")
    
    is_valid = len(warnings) == 0
    return is_valid, warnings


def get_data_quality_report(df: pd.DataFrame, ticker: str = "") -> Dict:
    """
    Generates a comprehensive data quality report.
    
    Parameters:
        df (pd.DataFrame): DataFrame to analyze
        ticker (str): Ticker symbol for reporting
    
    Returns:
        dict: Quality report with statistics and issues
    """
    report = {
        'ticker': ticker,
        'total_rows': len(df),
        'date_range': {
            'start': str(df.index.min()) if isinstance(df.index, pd.DatetimeIndex) else None,
            'end': str(df.index.max()) if isinstance(df.index, pd.DatetimeIndex) else None
        },
        'missing_values': df.isnull().sum().to_dict(),
        'ohlc_validation': {},
        'outliers': {},
        'range_validation': {},
        'quality_score': 0.0
    }
    
    # OHLC Validation
    if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        is_valid, errors = validate_ohlc(df)
        report['ohlc_validation'] = {
            'is_valid': is_valid,
            'errors': errors
        }
    
    # Outlier Detection
    outliers = detect_outliers(df, method='iqr', threshold=3.0)
    outlier_counts = {col: outliers[col].sum() for col in outliers}
    report['outliers'] = outlier_counts
    
    # Range Validation
    is_valid, warnings = validate_data_ranges(df)
    report['range_validation'] = {
        'is_valid': is_valid,
        'warnings': warnings
    }
    
    # Calculate quality score (0-100)
    score = 100.0
    
    # Deduct for missing values
    total_missing = sum(report['missing_values'].values())
    if total_missing > 0:
        score -= min(20, (total_missing / len(df)) * 100)
    
    # Deduct for OHLC errors
    if not report['ohlc_validation'].get('is_valid', True):
        score -= 30
    
    # Deduct for outliers
    total_outliers = sum(outlier_counts.values())
    if total_outliers > 0:
        score -= min(20, (total_outliers / len(df)) * 100)
    
    # Deduct for range warnings
    if not report['range_validation'].get('is_valid', True):
        score -= 20
    
    report['quality_score'] = max(0, score)
    
    return report


if __name__ == "__main__":
    # Test the validation functions
    print("Data Quality Validation Module")
    print("=" * 50)
    
    # Create sample data
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    sample_df = pd.DataFrame({
        'open': np.random.uniform(100, 200, 100),
        'high': np.random.uniform(150, 250, 100),
        'low': np.random.uniform(50, 150, 100),
        'close': np.random.uniform(100, 200, 100),
        'volume': np.random.uniform(1000000, 5000000, 100)
    }, index=dates)
    
    # Test validation
    is_valid, errors = validate_ohlc(sample_df)
    print(f"OHLC Validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
    if errors:
        print(f"Errors: {errors}")
    
    # Test outliers
    outliers = detect_outliers(sample_df)
    print(f"\nOutliers detected: {sum(sum(outliers.values()))} total")
    
    # Test quality report
    report = get_data_quality_report(sample_df, "TEST")
    print(f"\nQuality Score: {report['quality_score']:.1f}/100")







