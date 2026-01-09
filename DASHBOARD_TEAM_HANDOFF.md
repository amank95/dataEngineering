# Dashboard Team Handoff Documentation

## 📋 Overview

This document contains everything the Dashboard team needs to integrate with our Data Engineering Pipeline. The pipeline provides real-time stock market data with technical indicators through a RESTful API and Supabase database.

---

## 🔗 API Base URL

**Local Development:**
```
http://127.0.0.1:8000
```

**API Documentation (Interactive):**
```
http://127.0.0.1:8000/docs
```

---

## 🔑 Authentication & Access

### Supabase Credentials
You'll need these environment variables for direct database access:

```env
SUPABASE_URL=<provided_separately>
SUPABASE_KEY=<provided_separately>
```

> **Note:** Credentials will be shared securely via separate channel.

### API Access
- **No authentication required** for local development
- All endpoints support CORS for frontend integration
- For production, we'll implement API key authentication

---

## 📊 Available Data

### Stock Tickers
Currently tracking **Indian stocks** (NSE format):
- `INFY.NS` - Infosys
- `TCS.NS` - Tata Consultancy Services
- *(More tickers can be added on request)*

### Data Fields
Each record contains:

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Stock symbol (e.g., "RELIANCE.NS") |
| `date` | date | Trading date (YYYY-MM-DD) |
| `open` | decimal | Opening price |
| `high` | decimal | Highest price |
| `low` | decimal | Lowest price |
| `close` | decimal | Closing price |
| `volume` | integer | Trading volume |
| `daily_return` | decimal | Daily return percentage |
| `sma_20` | decimal | 20-day Simple Moving Average |
| `sma_50` | decimal | 50-day Simple Moving Average |
| `rsi_14` | decimal | 14-day Relative Strength Index (0-100) |
| `macd` | decimal | MACD indicator |
| `volatility` | decimal | 20-day rolling volatility |
| `created_at` | timestamp | Record creation time |
| `updated_at` | timestamp | Last update time |

---

## 🚀 API Endpoints

### 1. Health Check

**GET** `/health`

Check API and database connectivity.

**Response:**
```json
{
  "api": "healthy",
  "parquet_file_exists": true,
  "supabase_enabled": true,
  "supabase_connection": "healthy",
  "supabase_has_data": true
}
```

**Use Case:** Display system status in dashboard header.

---

### 2. Get Training Data (Date Range)

**GET** `/supabase/training-data`

Fetch data for specific date range and tickers.

**Parameters:**
- `start_date` (required): Start date (YYYY-MM-DD)
- `end_date` (required): End date (YYYY-MM-DD)
- `tickers` (optional): List of tickers (can repeat parameter)

**Example:**
```
GET /supabase/training-data?start_date=2024-01-01&end_date=2024-12-31&tickers=RELIANCE.NS&tickers=TCS.NS
```

**Response:**
```json
{
  "status": "success",
  "count": 500,
  "data": [
    {
      "ticker": "RELIANCE.NS",
      "date": "2024-01-01",
      "close": 2500.50,
      "daily_return": 0.015,
      "rsi_14": 65.5,
      ...
    }
  ]
}
```

**Use Case:** Fetch historical data for charts and analysis.

---

### 3. Get Ticker Time-Series

**GET** `/supabase/ticker/{ticker}`

Get all data for a specific ticker.

**Parameters:**
- `ticker` (path): Stock symbol (e.g., "RELIANCE.NS")
- `start_date` (optional): Filter from date
- `limit` (optional): Max records to return

**Example:**
```
GET /supabase/ticker/RELIANCE.NS?start_date=2024-01-01&limit=100
```

**Response:**
```json
{
  "status": "success",
  "ticker": "RELIANCE.NS",
  "count": 100,
  "data": [...]
}
```

**Use Case:** Display ticker-specific charts and metrics.

---

### 4. Get Recent Data

**GET** `/supabase/recent/{ticker}`

Get last N days of data for a ticker.

**Parameters:**
- `ticker` (path): Stock symbol
- `days` (optional): Number of recent days (default: 30)

**Example:**
```
GET /supabase/recent/RELIANCE.NS?days=60
```

**Response:**
```json
{
  "status": "success",
  "ticker": "RELIANCE.NS",
  "days": 60,
  "count": 60,
  "data": [
    {
      "date": "2024-12-01",
      "open": 2500.00,
      "close": 2520.00,
      "rsi_14": 68.5,
      "daily_return": 0.008
    }
  ]
}
```

**Use Case:** Display recent performance and trends.

---

### 5. Get Latest Data (All Tickers)

**GET** `/supabase/latest`

Get the most recent data point for each ticker.

**Parameters:**
- `limit` (optional): Number of tickers (default: 10)

**Example:**
```
GET /supabase/latest?limit=20
```

**Use Case:** Dashboard overview showing all stocks at a glance.

---

### 6. Get Top Performers

**GET** `/supabase/top-performers`

Get top performing stocks by daily return.

**Parameters:**
- `date` (optional): Specific date (defaults to latest)
- `top_n` (optional): Number of results (default: 10)

**Example:**
```
GET /supabase/top-performers?top_n=20
```

**Response:**
```json
{
  "status": "success",
  "count": 20,
  "data": [
    {
      "ticker": "TCS.NS",
      "date": "2024-12-31",
      "close": 3500.00,
      "daily_return": 0.025,
      "rsi_14": 72.3
    }
  ]
}
```

**Use Case:** "Top Gainers" widget in dashboard.

---

### 7. Search by RSI

**GET** `/supabase/rsi-search`

Find stocks within RSI range (for technical analysis).

**Parameters:**
- `min_rsi` (optional): Minimum RSI (default: 0)
- `max_rsi` (optional): Maximum RSI (default: 100)
- `date` (optional): Specific date

**Example (Oversold stocks):**
```
GET /supabase/rsi-search?min_rsi=0&max_rsi=30
```

**Example (Overbought stocks):**
```
GET /supabase/rsi-search?min_rsi=70&max_rsi=100
```

**Use Case:** "Oversold/Overbought Stocks" screener.

---

### 8. Get Ticker Statistics

**GET** `/supabase/stats/{ticker}`

Get statistical summary for a ticker over date range.

**Parameters:**
- `ticker` (path): Stock symbol
- `start_date` (required): Start date
- `end_date` (required): End date

**Example:**
```
GET /supabase/stats/RELIANCE.NS?start_date=2024-01-01&end_date=2024-12-31
```

**Response:**
```json
{
  "status": "success",
  "stats": {
    "ticker": "RELIANCE.NS",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "total_days": 250,
    "avg_return": 0.0012,
    "std_return": 0.018,
    "avg_rsi": 55.2,
    "avg_volume": 5000000,
    "price_change_pct": 15.5
  }
}
```

**Use Case:** Display performance metrics and statistics cards.

---

### 9. Trigger Pipeline Execution

**POST** `/run-pipeline`

Manually trigger data pipeline to fetch latest data.

**Example:**
```javascript
fetch('http://127.0.0.1:8000/run-pipeline', {
  method: 'POST'
})
```

**Response:**
```json
{
  "status": "success",
  "message": "Data pipeline executed successfully",
  "details": {
    "processed_tickers": 2,
    "total_tickers": 2,
    "success": true
  }
}
```

**Use Case:** "Refresh Data" button in dashboard.

---

### 10. Download Parquet File

**GET** `/fetch-parquet`

Download the complete dataset as Parquet file.

**Example:**
```
GET /fetch-parquet
```

**Response:** Binary file download

**Use Case:** Bulk data export for offline analysis.

---

## 🗄️ Direct Supabase Access

If you prefer direct database queries instead of API:

### JavaScript/TypeScript Example
```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_KEY
)

// Get recent data for a ticker
const { data, error } = await supabase
  .from('stock_features')
  .select('*')
  .eq('ticker', 'RELIANCE.NS')
  .gte('date', '2024-01-01')
  .order('date', { ascending: false })
  .limit(100)
```

### Python Example
```python
from supabase import create_client

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Get recent data
response = supabase.table('stock_features')\
    .select('*')\
    .eq('ticker', 'RELIANCE.NS')\
    .gte('date', '2024-01-01')\
    .order('date', desc=True)\
    .limit(100)\
    .execute()

data = response.data
```

### Available Views
- `latest_stock_data` - Latest data point per ticker
- `daily_market_summary` - Daily aggregated statistics

---

## 📈 Dashboard Integration Examples

### Example 1: Stock Price Chart
```javascript
// Fetch data
const response = await fetch(
  'http://127.0.0.1:8000/supabase/recent/RELIANCE.NS?days=90'
);
const result = await response.json();

// Use with Chart.js, Plotly, or any charting library
const chartData = {
  labels: result.data.map(d => d.date),
  datasets: [{
    label: 'Close Price',
    data: result.data.map(d => d.close)
  }]
};
```

### Example 2: RSI Indicator Widget
```javascript
const response = await fetch(
  'http://127.0.0.1:8000/supabase/ticker/TCS.NS?limit=1'
);
const result = await response.json();
const currentRSI = result.data[0].rsi_14;

// Display with color coding
const rsiStatus = currentRSI > 70 ? 'Overbought' : 
                  currentRSI < 30 ? 'Oversold' : 'Neutral';
```

### Example 3: Top Performers Table
```javascript
const response = await fetch(
  'http://127.0.0.1:8000/supabase/top-performers?top_n=10'
);
const result = await response.json();

// Render as table
result.data.forEach(stock => {
  console.log(`${stock.ticker}: ${stock.daily_return}%`);
});
```

### Example 4: Health Status Indicator
```javascript
const response = await fetch('http://127.0.0.1:8000/health');
const health = await response.json();

// Display status badge
const isHealthy = health.api === 'healthy' && 
                  health.supabase_connection === 'healthy';
```

---

## 🔄 Data Refresh Schedule

- **Pipeline runs:** On-demand via `/run-pipeline` endpoint
- **Data source:** Yahoo Finance (real-time during market hours)
- **Historical data:** Available from 2024-01-01
- **Update frequency:** Configurable (currently manual trigger)

**Recommendation:** Add a "Last Updated" timestamp in your dashboard using the `updated_at` field.

---

## ⚠️ Important Notes

### Data Validation
All data is validated before storage:
- OHLC validation (High ≥ Low, etc.)
- RSI range check (0-100)
- Positive volume constraint

### Error Handling
API returns standard HTTP status codes:
- `200` - Success
- `404` - Data not found
- `500` - Server error
- `503` - Service unavailable (e.g., Supabase not configured)

**Always check the `status` field in responses.**

### Rate Limiting
- No rate limits for local development
- For production deployment, we'll implement rate limiting

### CORS
CORS is enabled for all origins in development. For production, we'll restrict to your dashboard domain.

---

## 🛠️ Testing the API

### Using cURL
```bash
# Health check
curl http://127.0.0.1:8000/health

# Get recent data
curl "http://127.0.0.1:8000/supabase/recent/RELIANCE.NS?days=30"

# Trigger pipeline
curl -X POST http://127.0.0.1:8000/run-pipeline
```

### Using Postman
Import the API documentation from: `http://127.0.0.1:8000/docs`

### Using Browser
Navigate to `http://127.0.0.1:8000/docs` for interactive API testing.

---

## 📞 Support & Communication

### Questions?
- **Technical issues:** Contact Data Engineering team
- **New features:** Submit requirements via project tracker
- **Data requests:** Email with ticker symbols and date ranges

### Adding New Tickers
Send us a list of ticker symbols (NSE format: `TICKER.NS`) and we'll add them to the pipeline.

### Custom Indicators
If you need additional technical indicators, let us know:
- Bollinger Bands
- VWAP
- Fibonacci levels
- Custom calculations

---

## 🚀 Getting Started Checklist

- [ ] Receive Supabase credentials
- [ ] Test API health endpoint
- [ ] Fetch sample data for one ticker
- [ ] Integrate with your charting library
- [ ] Implement error handling
- [ ] Add "Refresh Data" functionality
- [ ] Test with multiple tickers
- [ ] Implement caching (recommended)

---

## 📚 Additional Resources

- **API Documentation:** http://127.0.0.1:8000/docs
- **Supabase Docs:** https://supabase.com/docs
- **Project README:** See `README.md` in project root
- **Schema Reference:** See `supabase/schema.sql`

---

## 🎯 Recommended Dashboard Features

Based on our data, here are suggested dashboard components:

1. **Overview Tab**
   - Market summary (total tickers, avg return)
   - Top gainers/losers
   - System health status

2. **Stock Explorer**
   - Search by ticker
   - Price charts with SMA overlays
   - RSI indicator
   - Volume bars

3. **Technical Analysis**
   - RSI screener (oversold/overbought)
   - MACD signals
   - Volatility rankings

4. **Performance Metrics**
   - Daily returns distribution
   - Correlation matrix
   - Risk-return scatter plot

5. **Data Quality**
   - Last update timestamp
   - Data completeness indicators
   - Refresh data button

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-08  
**Contact:** Data Engineering Team
