# Stock Data Engineering Pipeline

A production-ready Python data pipeline for stock and ETF data ingestion, cleaning, and feature engineering.

## 🎯 Overview

This project provides **two ways** to access processed stock data:

1. **File-based Pipeline** (`data_pipeline.py`) - Saves datasets to files
2. **Direct DataFrame Access** (`ml_data_access.py`) - Returns DataFrames directly for ML training

## 📁 Project Structure

```
squad1-data-engineering/
├── src/
│   ├── fetch_data.py           # Fetch raw OHLCV data from Yahoo Finance
│   ├── clean_data.py            # Clean data and convert USD to INR
│   └── feature_engineering.py   # Generate technical indicators
├── data/
│   ├── raw/                     # Raw downloaded data
│   └── processed/               # Cleaned and feature-engineered data
├── data_pipeline.py             # Main pipeline (saves to files)
├── ml_data_access.py            # Direct DataFrame access for ML team
├── example_ml_usage.py          # Usage examples
├── ML_TEAM_GUIDE.md            # Comprehensive guide for ML team
└── requirements.txt             # Python dependencies
```

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Option 1: File-Based Pipeline (Original)

```bash
# Run the full pipeline - saves to data/processed/features_dataset.parquet
python data_pipeline.py
```

### Option 2: Direct DataFrame Access (New - For ML Team)

```python
from ml_data_access import get_all_tickers_dataframe

# Get processed data directly
df = get_all_tickers_dataframe(
    tickers=['AAPL', 'MSFT', 'GOOGL'],
    start_date='2022-01-01',
    end_date='2026-01-01'
)

# Ready to use for model training!
print(df.head())
```

## 📊 Features Generated

The pipeline generates the following technical indicators:

- **Return**: Daily percentage returns
- **SMA_20**: 20-day Simple Moving Average
- **SMA_50**: 50-day Simple Moving Average
- **RSI_14**: 14-period Relative Strength Index
- **MACD**: Moving Average Convergence Divergence
- **Volatility**: 20-day rolling volatility

All prices are automatically converted from USD to INR.

## 🎓 For ML Team

### What Changed?

**Before:** You had to read saved Parquet/CSV files  
**Now:** You can get DataFrames directly from the pipeline code

### Quick Example

```python
from ml_data_access import get_processed_dataframe

# Get data for a single ticker
df = get_processed_dataframe('AAPL', '2023-01-01', '2024-01-01')

# Use directly in your model
from sklearn.ensemble import RandomForestRegressor
X = df[['SMA_20', 'SMA_50', 'RSI_14', 'MACD', 'Volatility']]
y = df['Return']
model = RandomForestRegressor()
model.fit(X, y)
```

### Available Functions

| Function | Purpose |
|----------|---------|
| `get_raw_dataframe()` | Raw OHLCV data |
| `get_cleaned_dataframe()` | Cleaned data with INR conversion |
| `get_processed_dataframe()` | Single ticker with all features ⭐ |
| `get_all_tickers_dataframe()` | Multiple tickers consolidated ⭐ |

**📖 See [ML_TEAM_GUIDE.md](ML_TEAM_GUIDE.md) for detailed documentation**

**💡 See [example_ml_usage.py](example_ml_usage.py) for practical examples**

## 🔧 Configuration

Edit `data_pipeline.py` to customize:

```python
TICKERS = ['WMT', 'JNJ', 'JPM', 'MSFT', 'NVDA', 'GOOGL', 'TSLA', 'AMZN', 'BAC', 'BK']
START_DATE = '2022-01-01'
END_DATE = '2026-01-01'
```

## 📝 Data Flow

```
1. Fetch Data (Yahoo Finance)
   ↓
2. Clean Data (Handle missing values, convert to INR)
   ↓
3. Feature Engineering (Technical indicators)
   ↓
4. Output:
   - File-based: Save to Parquet/CSV
   - Direct access: Return DataFrame
```

## 🧪 Testing

Run the example script to verify everything works:

```bash
python example_ml_usage.py
```

## 📦 Dependencies

- pandas
- yfinance
- pandas_ta (optional, for advanced indicators)

## 🤝 Contributing

This is a data engineering module for the Stock & ETF Signal Generation Platform.  
For questions or issues, contact the Data Engineering team.

## 📄 License

Internal use only.
