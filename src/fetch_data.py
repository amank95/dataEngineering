import yfinance as yf
import os

def fetch_data(ticker="AAPL", start_date="2020-01-01", end_date="2023-01-01"):
    """
    Fetches daily OHLCV data for a given ticker and saves it to a CSV file.
    
    Parameters:
        ticker (str): The stock or ETF symbol (default: "AAPL").
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
    """
    
    # download data using yfinance
    print(f"Fetching data for {ticker} from {start_date} to {end_date}...")
    df = yf.download(ticker, start=start_date, end=end_date)
    
    # define output path
    output_dir = "data/raw"
    os.makedirs(output_dir, exist_ok=True)
    file_path = f"{output_dir}/{ticker}_raw.csv"
    
    # save to csv
    df.to_csv(file_path)
    print(f"Data saved to {file_path}")

if __name__ == "__main__":
    # execute function with default parameters
    fetch_data()
