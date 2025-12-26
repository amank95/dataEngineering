

import pandas as pd
import os

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
    
    # If date was somehow read as a column (fallback), handled by set_index? 
    # With index_col=0, it's in the index.

    # drop missing values

    # Ensure all columns are numeric
    df = df.apply(pd.to_numeric, errors='coerce')

    # drop missing values
    df.dropna(inplace=True)
    
    # save to csv
    df.to_csv(processed_path)
    print(f"Cleaned data saved to {processed_path}")

if __name__ == "__main__":
    clean_data()
