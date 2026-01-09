# Streamlit Dashboard API Endpoints
Base URL: `http://127.0.0.1:8000`

## System Health
`GET /health`

## Pipeline Control
`POST /run-pipeline`

## Stock Data & Charts
`GET /supabase/recent/{ticker}?days=30`
`GET /supabase/ticker/{ticker}?start_date=2024-01-01&limit=100`

## Market Overview
`GET /supabase/latest?limit=10`
`GET /supabase/top-performers?top_n=10`

## Analysis & Filtering
`GET /supabase/stats/{ticker}?start_date=2024-01-01` (Auto-ends today)
`GET /supabase/rsi-search?min_rsi=0&max_rsi=30`
