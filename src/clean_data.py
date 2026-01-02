

import pandas as pd
import os
import yfinance as yf
import sys

# Add parent directory to path to import config_loader
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

try:
    from config_loader import get_config
    # Import data quality from same directory
    from data_quality import validate_ohlc, detect_outliers, check_data_freshness, validate_data_ranges, get_data_quality_report
    DATA_QUALITY_ENABLED = True
except ImportError as e:
    # Fallback if data_quality module not available
    DATA_QUALITY_ENABLED = False
    # Only print warning if module exists but import failed for other reasons
    if 'data_quality' in str(e):
        pass  # Module doesn't exist yet, that's okay

def clean_data(ticker="AAPL"):
    """
    Loads raw data, cleans it, and saves it to the processed folder.
    
    Parameters:
        ticker (str): The stock or ETF symbol (default: "AAPL").
    """
    
    # define paths
    raw_path = f"data/raw/{ticker}_raw.csv"
    processed_dir = "data/processed"
    os.makedirs(processed_dir, exist_ok=True)
    processed_path = f"{processed_dir}/{ticker}_cleaned.csv"
    
    print(f"Cleaning data for {ticker}...")
    
    # load raw data
    try:
        # yfinance CSVs usually have the date as the first column (index)
        df = pd.read_csv(raw_path, index_col=0, parse_dates=True)
    except FileNotFoundError:
        print(f"Error: File not found at {raw_path}")
        return

    # standardize column names to lowercase
    df.columns = [col.lower() for col in df.columns]
    
    # Ensure index is named 'date'
    df.index.name = 'date'
    
    # Ensure index is datetime (fix for potential string index)
    df.index = pd.to_datetime(df.index, errors='coerce')
    df = df[df.index.notna()]
    
    # If date was somehow read as a column (fallback), handled by set_index? 
    # With index_col=0, it's in the index.

    # drop missing values

    # Ensure all columns are numeric
    df = df.apply(pd.to_numeric, errors='coerce')

    # drop missing values
    df.dropna(inplace=True)
    
    # ============================================
    # DATA QUALITY VALIDATION
    # ============================================
    if DATA_QUALITY_ENABLED:
        try:
            config = get_config()
            validate_ohlc_flag = config.get('processing', {}).get('validate_ohlc', True)
            min_data_points = config.get('processing', {}).get('min_data_points', 50)
            
            # 1. Check minimum data points
            if len(df) < min_data_points:
                print(f"⚠️  Warning: Only {len(df)} data points (minimum: {min_data_points})")
            
            # 2. Validate OHLC relationships
            if validate_ohlc_flag and all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                is_valid, errors = validate_ohlc(df)
                if not is_valid:
                    print(f"⚠️  OHLC Validation Issues for {ticker}:")
                    for error in errors:
                        print(f"   - {error}")
                else:
                    print(f"✅ OHLC validation passed for {ticker}")
            
            # 3. Detect outliers
            outliers = detect_outliers(df, method='iqr', threshold=3.0)
            total_outliers = sum([outliers[col].sum() for col in outliers])
            if total_outliers > 0:
                print(f"⚠️  Detected {total_outliers} outliers in {ticker}")
                for col, outlier_mask in outliers.items():
                    count = outlier_mask.sum()
                    if count > 0:
                        print(f"   - {col}: {count} outliers")
            else:
                print(f"✅ No significant outliers detected for {ticker}")
            
            # 4. Validate data ranges
            is_valid, warnings = validate_data_ranges(df)
            if warnings:
                print(f"⚠️  Data Range Warnings for {ticker}:")
                for warning in warnings:
                    print(f"   - {warning}")
            
            # 5. Generate quality report (optional, can be verbose)
            # Uncomment if you want detailed report
            # report = get_data_quality_report(df, ticker)
            # print(f"📊 Quality Score: {report['quality_score']:.1f}/100")
            
        except Exception as e:
            print(f"⚠️  Data quality check failed: {e}")
            print("   Continuing with data processing...")

    # Convert USD to INR
    print("Fetching USD to INR exchange rates...")
    try:
        # 1. Fetch Currency Data
        tickers_currency = "USDINR=X"
        start_date = df.index.min()
        end_date = df.index.max() + pd.Timedelta(days=5) # Add buffer

        currency_df = yf.download(tickers_currency, start=start_date, end=end_date, progress=False)

        # Handle yfinance columns (multi-index or simple)
        if isinstance(currency_df.columns, pd.MultiIndex):
            currency_df.columns = currency_df.columns.get_level_values(0)
        
        currency_df.columns = [col.lower() for col in currency_df.columns]
        
        # 2. Align Data
        # We only need the close rate
        exchange_rate = currency_df['close']
        
        # Ensure timezone-naive for alignment
        if exchange_rate.index.tz is not None:
             exchange_rate.index = exchange_rate.index.tz_localize(None)
        
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Reindex to match stock data, ffill to handle weekends/holidays
        exchange_rate = exchange_rate.reindex(df.index, method='ffill')
        
        # Fill any remaining NaNs (e.g. at the start) with the first valid value
        exchange_rate = exchange_rate.bfill()

        # 3. Convert Columns
        cols_to_convert = ['open', 'high', 'low', 'close']
        for col in cols_to_convert:
            if col in df.columns:
                df[col] = df[col] * exchange_rate

        print("Converted prices from USD to INR.")
        
    except Exception as e:
        print(f"Warning: Could not convert to INR. Error: {e}")
        print("Saving in USD instead.")
    
    # Check data freshness before saving
    if DATA_QUALITY_ENABLED:
        try:
            is_fresh, freshness_msg = check_data_freshness(raw_path, max_age_hours=24)
            if not is_fresh:
                print(f"⚠️  {freshness_msg}")
        except Exception as e:
            print(f"⚠️  Could not check data freshness: {e}")
    
    # save to csv
    df.to_csv(processed_path)
    print(f"Cleaned data saved to {processed_path}")

if __name__ == "__main__":
    clean_data()
