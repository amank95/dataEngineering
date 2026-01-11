# API Endpoints for Dashboard Team

**Base URL**: `http://127.0.0.1:8000`

---

## System Health
```
GET /health
GET /
```

## Stock Data & Charts
```
GET /supabase/recent/{ticker}?days=30
GET /supabase/ticker/{ticker}?start_date=2024-01-01&limit=100
```

## Market Overview
```
GET /supabase/latest?limit=10
GET /supabase/top-performers?top_n=10
GET /supabase/top-performers?top_n=20&date=2024-12-31
```

## Analysis & Filtering
```
GET /supabase/stats/{ticker}?start_date=2024-01-01
GET /supabase/stats/{ticker}?start_date=2024-01-01&end_date=2024-12-31
GET /supabase/rsi-search?min_rsi=0&max_rsi=30
GET /supabase/rsi-search?min_rsi=70&max_rsi=100&date=2024-12-31
```

## Training Data
```
GET /supabase/training-data?start_date=2024-01-01&end_date=2024-12-31
GET /supabase/training-data?start_date=2024-01-01 (Auto-ends today)
```

## Model Health Monitoring
```
GET /supabase/model-health?window_hours=24
GET /supabase/model-health?window_hours=48&ticker=INFY.NS
GET /supabase/drift-alerts?limit=50
GET /supabase/drift-alerts?ticker=RELIANCE.NS
GET /supabase/drift-alerts?ticker=RELIANCE.NS&feature=sma_20
```

## File Download
```
GET /fetch-parquet
```

---

## Interactive Documentation
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## How to Start API Server
```bash
python run_all.py --start-api
```

**Notes**:
- All endpoints return JSON (except `/fetch-parquet`)
- No authentication required
- Replace `{ticker}` with actual stock symbols (e.g., `RELIANCE.NS`, `INFY.NS`)
