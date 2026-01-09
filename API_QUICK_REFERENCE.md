# Quick Reference: Dashboard Team API

## � Base URL
```
http://127.0.0.1:8000
```

## � Most Used Endpoints

### 1. Health Check
```
GET /health
```

### 2. Get Recent Data (Last N Days)
```
GET /supabase/recent/{ticker}?days=30
```
Example: `/supabase/recent/RELIANCE.NS?days=60`

### 3. Get Ticker Data (Date Range)
```
GET /supabase/ticker/{ticker}?start_date=YYYY-MM-DD&limit=100
```

### 4. Get Top Performers
```
GET /supabase/top-performers?top_n=10
```

### 5. Get Latest Data (All Tickers)
```
GET /supabase/latest?limit=20
```

### 6. Search by RSI
```
GET /supabase/rsi-search?min_rsi=0&max_rsi=30
```
- Oversold: `min_rsi=0&max_rsi=30`
- Overbought: `min_rsi=70&max_rsi=100`

### 7. Get Statistics
```
GET /supabase/stats/{ticker}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

### 8. Refresh Data
```
POST /run-pipeline
```

---

## 📊 Data Fields

| Field | Description |
|-------|-------------|
| `ticker` | Stock symbol (e.g., "RELIANCE.NS") |
| `date` | Trading date |
| `open`, `high`, `low`, `close` | OHLC prices |
| `volume` | Trading volume |
| `daily_return` | Daily return % |
| `sma_20`, `sma_50` | Moving averages |
| `rsi_14` | RSI indicator (0-100) |
| `macd` | MACD indicator |
| `volatility` | 20-day volatility |

---

## � Quick Start

1. **Test API:**
   ```bash
   curl http://127.0.0.1:8000/health
   ```

2. **Get sample data:**
   ```bash
   curl "http://127.0.0.1:8000/supabase/recent/TCS.NS?days=30"
   ```

3. **View interactive docs:**
   ```
   http://127.0.0.1:8000/docs
   ```

---

## 🔑 Environment Variables

```env
SUPABASE_URL=<provided_by_data_team>
SUPABASE_KEY=<provided_by_data_team>
API_BASE_URL=http://127.0.0.1:8000
```

---

## 📞 Support

- Full documentation: `DASHBOARD_TEAM_HANDOFF.md`
- Contact: Data Engineering Team
