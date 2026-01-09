
from src.fetch_data import fetch_intraday_data
from src.clean_data import clean_intraday_data
from src.feature_engineering import generate_intraday_features
import traceback

ticker = "ASHOKLEY.NS"
print(f"Testing Intraday for {ticker}...")

try:
    fetch_intraday_data(ticker, interval="5m")
    print("Fetch done.")
    clean_intraday_data(ticker, interval="5m")
    print("Clean done.")
    generate_intraday_features(ticker, interval="5m")
    print("Features done.")
except Exception as e:
    print(f"FAILED: {e}")
    traceback.print_exc()
