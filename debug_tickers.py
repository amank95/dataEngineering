
import yfinance as yf
import pandas as pd
from datetime import datetime

tickers = ["ASHOKLEY.NS", "AXISBANK.NS", "BHARTIARTL.NS", "RELIANCE.NS"] # Added RELIANCE as a control
start_date = "2024-01-01"
end_date = datetime.now().strftime('%Y-%m-%d')

print(f"Fetching data from {start_date} to {end_date}...")

for ticker in tickers:
    print(f"\n--- Checking {ticker} ---")
    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df.empty:
            print(f"❌ {ticker}: Dataframe is empty!")
            # Try fetching with period='max' to see if it's a date range issue
            print(f"   Retrying {ticker} with period='1mo'...")
            df_retry = yf.download(ticker, period="1mo", progress=False)
            if df_retry.empty:
                 print(f"   ❌ {ticker}: Dataframe is STILL empty with period='1mo'!")
            else:
                 print(f"   ✅ {ticker}: Data found with period='1mo'. (Date range issue?)")
                 print(df_retry.head(2))
        else:
            print(f"✅ {ticker}: Data found. Shape: {df.shape}")
            print(df.head(2))
    except Exception as e:
        print(f"❌ {ticker}: Exception occurred: {e}")
