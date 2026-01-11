# API Endpoints for Dashboard (UI) Team

> **Base URL**: `http://127.0.0.1:8000`  
> **Interactive Docs**: `http://127.0.0.1:8000/docs` (Swagger UI for testing)

---

## 📊 Dashboard Overview Endpoints

### 1. Health & Status Monitoring

#### **GET** `/health`
Comprehensive health check with data freshness metrics.

**Response Example**:
```json
{
  "api": "healthy",
  "parquet_file_exists": true,
  "supabase_enabled": true,
  "health_score": 90,
  "data_freshness": {
    "last_update": "2026-01-11T20:00:00",
    "hours_since_update": 1.2
  },
  "total_records": 15000,
  "tickers_processed": 50
}
```

#### **GET** `/`
API information and available endpoints.

---

## 📈 Data Retrieval Endpoints

### 2. Latest Stock Data

#### **GET** `/supabase/latest?limit={n}`
Get latest data point for each ticker.

**Parameters**:
- `limit` (optional): Number of tickers (default: 20)

**Example**: `/supabase/latest?limit=10`

**Use Case**: Display current market snapshot on dashboard homepage.

---

### 3. Ticker-Specific Data

#### **GET** `/supabase/ticker/{ticker}?start_date={date}&limit={n}`
Get time-series data for a specific ticker.

**Parameters**:
- `ticker` (required): Stock symbol (e.g., `RELIANCE.NS`)
- `start_date` (optional): Start date in YYYY-MM-DD format
- `limit` (optional): Max number of records

**Example**: `/supabase/ticker/RELIANCE.NS?start_date=2024-01-01&limit=100`

**Use Case**: Show detailed stock charts and historical data.

---

#### **GET** `/supabase/recent/{ticker}?days={n}`
Get recent N days of data for a ticker.

**Parameters**:
- `ticker` (required): Stock symbol
- `days` (optional): Number of recent days (default: 30)

**Example**: `/supabase/recent/INFY.NS?days=60`

**Use Case**: Quick access to recent performance data.

---

### 4. Training Data (for ML team integration)

#### **GET** `/supabase/training-data?start_date={date}&end_date={date}&tickers={list}`
Get training data for ML models.

**Parameters**:
- `start_date` (required): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (defaults to today)
- `tickers` (optional): List of specific tickers

**Example**: `/supabase/training-data?start_date=2024-01-01&end_date=2024-12-31`

---

## 🔍 Analytics & Insights Endpoints

### 5. Market Analytics

#### **GET** `/supabase/top-performers?top_n={n}&date={date}`
Get top performing stocks by daily return.

**Parameters**:
- `top_n` (optional): Number of top performers (default: 20)
- `date` (optional): Specific date (defaults to latest)

**Example**: `/supabase/top-performers?top_n=10`

**Use Case**: Display top gainers on dashboard.

---

#### **GET** `/supabase/stats/{ticker}?start_date={date}&end_date={date}`
Get statistical summary for a ticker.

**Parameters**:
- `ticker` (required): Stock symbol
- `start_date` (required): Start date
- `end_date` (optional): End date (defaults to today)

**Example**: `/supabase/stats/RELIANCE.NS?start_date=2024-01-01`

**Response Example**:
```json
{
  "status": "success",
  "stats": {
    "ticker": "RELIANCE.NS",
    "total_days": 250,
    "avg_return": 0.0012,
    "std_return": 0.0234,
    "avg_rsi": 52.3,
    "avg_volume": 5000000,
    "price_change_pct": 15.6
  }
}
```

**Use Case**: Show comprehensive stock statistics.

---

#### **GET** `/supabase/rsi-search?min_rsi={n}&max_rsi={n}&date={date}`
Find stocks within RSI range.

**Parameters**:
- `min_rsi` (optional): Minimum RSI (default: 0)
- `max_rsi` (optional): Maximum RSI (default: 100)
- `date` (optional): Specific date

**Example**: `/supabase/rsi-search?min_rsi=0&max_rsi=30` (oversold stocks)

**Use Case**: Identify trading opportunities (oversold/overbought stocks).

---

## 🏥 Model Health Monitoring

### 6. Model Health Status

#### **GET** `/supabase/model-health?window_hours={n}&ticker={symbol}`
Get model health status from drift alerts.

**Parameters**:
- `window_hours` (optional): Hours to look back (default: 24)
- `ticker` (optional): Filter by specific ticker

**Example**: `/supabase/model-health?window_hours=48&ticker=INFY.NS`

**Response Example**:
```json
{
  "status": "success",
  "model_health": "stable",
  "has_drift": false,
  "alert_count": 0,
  "window_hours": 24,
  "alerts": []
}
```

**Use Case**: Monitor model health status on dashboard.

---

#### **GET** `/supabase/drift-alerts?ticker={symbol}&feature={name}&limit={n}`
Get detailed drift alerts.

**Parameters**:
- `ticker` (optional): Filter by ticker
- `feature` (optional): Filter by feature (e.g., `sma_20`)
- `limit` (optional): Max alerts (default: 50)

**Example**: `/supabase/drift-alerts?ticker=RELIANCE.NS&feature=sma_20`

**Use Case**: Display data drift warnings.

---

## 📥 File Download Endpoints

### 7. Data Export

#### **GET** `/fetch-parquet`
Download the processed Parquet file.

**Response**: Binary file download

**Use Case**: Allow users to download complete dataset.

---

## 🚀 How to Start the API Server

```bash
# Start API server only
python run_all.py --start-api

# Or run everything (pipeline + API)
python run_all.py
```

The API will be available at `http://127.0.0.1:8000`

---

## 📝 Important Notes

### General
- ✅ All endpoints return JSON responses (except file downloads)
- ✅ No authentication required (configure for production)
- ✅ CORS enabled for frontend access
- ✅ Built-in caching for performance (15-60 second TTL)

### Data Sources
- **Supabase**: Real-time database queries (preferred)
- **Parquet**: Fallback for `/supabase/latest` endpoint
- Some endpoints require Supabase to be configured

### Response Format
All successful responses follow this pattern:
```json
{
  "status": "success",
  "count": 10,
  "data": [...]
}
```

### Error Handling
- `404`: Data not found
- `500`: Server/query error
- `503`: Supabase not configured

---

## 🎯 Quick Reference by Use Case

| **Dashboard Feature** | **Recommended Endpoint** |
|----------------------|-------------------------|
| Homepage Market Overview | `/supabase/latest?limit=20` |
| Stock Detail Page | `/supabase/ticker/{ticker}` |
| Top Gainers Widget | `/supabase/top-performers?top_n=10` |
| Trading Signals | `/supabase/rsi-search?min_rsi=0&max_rsi=30` |
| Health Monitoring | `/health` |
| Model Health Status | `/supabase/model-health` |
| Drift Alerts | `/supabase/drift-alerts` |
| Historical Analysis | `/supabase/stats/{ticker}` |

---

## 🔗 Additional Resources

- **Swagger UI**: Visit `/docs` for interactive API testing
- **ReDoc**: Visit `/redoc` for alternative documentation view
- **Support**: Contact the Data Engineering team for issues

---

**Last Updated**: 2026-01-11  
**API Version**: 2.0
