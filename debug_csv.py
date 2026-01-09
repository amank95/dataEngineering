
import yfinance as yf
import pandas as pd
import os

ticker = "ASHOKLEY.NS"
print(f"Fetching {ticker}...")
df = yf.download(ticker, period="1mo", progress=False)

print("\nDataframe columns:")
print(df.columns)

output_path = "debug_ashokley.csv"
df.to_csv(output_path)

print(f"\nSaved to {output_path}. Reading back...")
df_read = pd.read_csv(output_path, index_col=0, parse_dates=True)
print("Read columns:")
print(df_read.columns)
print("\nFirst few rows raw:")
with open(output_path, 'r') as f:
    print(f.read(300))
