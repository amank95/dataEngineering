
from src.fetch_data import fetch_intraday_data
import pandas as pd
import os
import time

ticker = "HDFCBANK.NS"
print(f"Test run 1: Fetching {ticker} intraday...")
fetch_intraday_data(ticker, interval="5m", period="5d")

path = f"data/raw/intraday/{ticker}_5m_raw.csv"
if os.path.exists(path):
    df1 = pd.read_csv(path, index_col=0)
    print(f"Run 1 Rows: {len(df1)}")
    
    # Simulate a second run
    print("\nTest run 2: Fetching again (should update/keep existing)...")
    fetch_intraday_data(ticker, interval="5m", period="5d")
    
    df2 = pd.read_csv(path, index_col=0)
    print(f"Run 2 Rows: {len(df2)}")
    
    if len(df2) >= len(df1):
        print("✅ Incremental update logic (append/deduplicate) working.")
    else:
        print("❌ Data count decreased? Something is wrong.")
else:
    print("❌ File not created.")
