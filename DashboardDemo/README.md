# Stock & ETF Signal Generation Platform - Dashboard Demo

A working Streamlit dashboard demo for the Stock & ETF Signal Generation Platform.

## Features

- **🏠 Home Page**: Overview and quick start guide
- **📈 Stock Explorer**: Interactive charts with technical indicators
- **🔔 Signal Generator**: Buy/Sell/Hold signals based on technical analysis
- **📊 Performance Analytics**: Compare multiple stocks with performance metrics
- **⚙️ Settings**: Configuration and platform information

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

## Running the Dashboard

1. Navigate to the DashboardDemo folder:
```bash
cd DashboardDemo
```

2. Run Streamlit:
```bash
streamlit run app.py
```

The dashboard will open in your default web browser at `http://localhost:8501`

## Usage

1. **Home**: View platform overview and available tickers
2. **Stock Explorer**: 
   - Select a stock/ETF from the dropdown
   - View price charts with moving averages and RSI
   - Analyze historical data
3. **Signal Generator**:
   - View current buy/sell/hold signals
   - See signal history
   - Compare signals across multiple stocks
4. **Performance Analytics**:
   - Compare multiple stocks side-by-side
   - View performance metrics (returns, Sharpe ratio, volatility, drawdown)
   - Interactive charts for comparison

## Data Requirements

The dashboard expects processed data files in `../data/processed/` with the format:
- `{TICKER}_final.csv` files containing:
  - date, close, open, high, low, volume
  - daily_return, ma_20, ma_50, rsi_14

## Signal Generation Logic

Signals are generated based on:
- **RSI**: Oversold (<30) = bullish, Overbought (>70) = bearish
- **Moving Averages**: MA 20 above MA 50 with price above MA 20 = bullish
- **Price Momentum**: Strong positive/negative daily returns
- **Combined Score**: Aggregated signal strength

## Notes

- This is a demo version using mock signal generation logic
- For production, integrate with actual ML models from Squad 2
- Real-time data updates require API integration
- Backtesting features will be added in Phase 3 integration


