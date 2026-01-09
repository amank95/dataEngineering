
import yfinance as yf
import pandas as pd
import os

tickers = ['HDFCBANK.NS', 'AXISBANK.NS', 'BAJFINANCE.NS', 'KOTAKBANK.NS']
print(f"Checking tickers: {tickers}")

for ticker in tickers:
    print(f"\n--- {ticker} ---")
    try:
        # Fetch daily
        print(f"Fetching daily (1mo)...")
        df = yf.download(ticker, period="1mo", progress=False)
        
        if df.empty:
            print(f"❌ Empty DataFrame returned for {ticker}")
        else:
            print(f"✅ Data found. Shape: {df.shape}")
            print(f"Columns: {df.columns}")
            if isinstance(df.columns, pd.MultiIndex):
                print(f"MultiIndex detected: {df.columns.levels}")
                # Try the fix
                df_fixed = df.copy()
                df_fixed.columns = df_fixed.columns.droplevel(1)
                print(f"Fixed Columns: {df_fixed.columns}")
                print(f"First row:\n{df_fixed.iloc[0]}")
            else:
                 print(f"First row:\n{df.iloc[0]}")

    except Exception as e:
        print(f"❌ Exception for {ticker}: {e}")
