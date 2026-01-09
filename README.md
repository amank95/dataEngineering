# Data Engineering Pipeline - Complete Project Structure

## 📁 Project Overview

This is a production-ready **Stock Market Data Engineering Pipeline** designed to:
1. Fetch real-time stock data from Yahoo Finance
2. Clean and validate data
3. Engineer technical indicators (SMA, RSI, MACD, etc.)
4. Store data in Parquet files and Supabase cloud database
5. Serve data via FastAPI for ML team consumption
6. Monitor pipeline health via Streamlit dashboard

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file with your Supabase credentials (optional):
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 3. Run the Complete Pipeline
```bash
# Option 1: Run pipeline only
python run_all.py

# Option 2: Run pipeline + sync to Supabase
python run_all.py --sync

# Option 3: Run pipeline + start API server
python run_all.py --start-api

# Option 4: Complete workflow
python run_all.py --sync --start-api
```

### 4. Launch Dashboard (for demos)
```bash
# Make sure API is running first (in another terminal):
python run_all.py --start-api

# Then launch dashboard:
streamlit run dashboard.py
# OR
run_dashboard.bat
```

---

## 📂 Project Structure

```
squad1-data-engineering/
│
├── src/                          # Core pipeline modules
│   ├── fetch_data.py            # Yahoo Finance data fetcher
│   ├── clean_data.py            # Data cleaning & validation
│   └── feature_engineering.py   # Technical indicators calculation
│
├── data/                         # Data storage
│   ├── raw/                     # Raw fetched data
│   ├── cleaned/                 # Cleaned data
│   └── processed/               # Final data with features
│
├── supabase/                     # Database setup
│   ├── schema.sql               # Database schema
│   ├── query_examples.py        # Example queries
│   └── SETUP_GUIDE.md          # Supabase setup instructions
│
├── config.yaml                   # Pipeline configuration
├── config_loader.py             # Configuration management
├── data_pipeline.py             # Main pipeline orchestrator
├── supabase_ingestion.py        # Cloud database sync
├── api.py                       # FastAPI server
├── dashboard.py                 # Streamlit monitoring dashboard
├── run_all.py                   # Master orchestration script
│
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (create this)
│
└── Documentation/
    ├── README.md                # This file
    ├── DASHBOARD_DEMO_GUIDE.md  # Dashboard demo instructions
    ├── ML_TEAM_GUIDE.md         # Guide for ML team
    ├── EMAIL_TO_ML_TEAM.md      # Handoff email template
    └── HANDOFF_CHECKLIST.md     # Project handoff checklist
```

---

## 🔧 Core Components

### 1. Data Pipeline (`data_pipeline.py`)
**Purpose:** Orchestrates the complete ETL process

**Process:**
1. Fetches data for configured tickers from Yahoo Finance
2. Cleans data (handles nulls, duplicates, outliers)
3. Engineers features (SMA, RSI, MACD, volatility, returns)
4. Consolidates all ticker data into single Parquet file
5. Optionally syncs to Supabase (if `auto_sync: true` in config)

**Configuration:** Edit `config.yaml` to:
- Add/remove tickers
- Change date ranges
- Adjust technical indicator periods
- Enable/disable Supabase auto-sync

### 2. API Server (`api.py`)
**Purpose:** RESTful API for ML team to access data

**Key Endpoints:**
- `POST /run-pipeline` - Trigger pipeline execution
- `GET /fetch-parquet` - Download Parquet file
- `GET /supabase/training-data` - Get training data by date range
- `GET /supabase/ticker/{ticker}` - Get specific ticker data
- `GET /supabase/recent/{ticker}` - Get recent N days of data
- `GET /health` - System health check

**Documentation:** Visit `http://127.0.0.1:8000/docs` when API is running

### 3. Supabase Integration (`supabase_ingestion.py`)
**Purpose:** Cloud database persistence for scalability

**Features:**
- Batch upsert (configurable batch size)
- Automatic conflict resolution (ticker + date primary key)
- Progress tracking and error handling
- Dry-run mode for testing

**Setup:** See `supabase/SETUP_GUIDE.md`

### 4. Monitoring Dashboard (`dashboard.py`)
**Purpose:** Visual monitoring and analytics interface

**Tabs:**
1. **Overview** - Pipeline health, API status, data availability
2. **Data Explorer** - Interactive charts for any ticker
3. **Analytics** - Statistical summaries and metrics
4. **Data Quality** - Completeness, freshness, distributions

**Access:** `http://localhost:8501` when running

---

## 📊 What This Pipeline Provides

### For Data Engineers:
✅ **Automated ETL** - Scheduled or on-demand data refresh  
✅ **Data Quality** - Validation and completeness checks  
✅ **Dual Storage** - Local (Parquet) + Cloud (Supabase)  
✅ **Monitoring** - Health checks and observability  
✅ **Scalability** - Parallel processing, batch operations  

### For ML Engineers:
✅ **Clean Features** - Ready-to-use technical indicators  
✅ **API Access** - Programmatic data retrieval  
✅ **Flexible Queries** - Date ranges, ticker filters, recent data  
✅ **Fresh Data** - Combat model drift with latest market data  
✅ **Historical Data** - Full time-series for training  

### For Stakeholders:
✅ **Visual Dashboard** - Real-time pipeline monitoring  
✅ **Quality Metrics** - Data completeness and freshness  
✅ **Analytics** - Statistical insights and trends  
✅ **Production-Ready** - Error handling, logging, documentation  

---

## 🎯 MLOps Integration (Data Drift Solution)

### The Problem:
Stock market data changes rapidly. ML models trained on old data become inaccurate (data drift).

### The Solution:
This pipeline acts as a **feedback loop**:

1. **Detect Drift:** Monitor model performance metrics
2. **Trigger Pipeline:** `POST /run-pipeline` to fetch latest data
3. **Fetch Training Data:** `GET /supabase/training-data` with recent date range
4. **Retrain Model:** Use fresh features to update model
5. **Deploy:** Replace old model with retrained version

### Automation:
Schedule the pipeline to run daily/weekly:
```bash
# Example: Windows Task Scheduler or cron job
python run_all.py --sync
```

---

## 🔍 Configuration Guide

### `config.yaml` Structure:
```yaml
data_sources:
  tickers: [RELIANCE.NS, TCS.NS, INFY.NS, ...]  # Stock symbols
  start_date: "2020-01-01"                       # Historical start
  end_date: "2024-12-31"                         # End date

features:
  sma_periods: [20, 50]                          # Moving average windows
  rsi_period: 14                                 # RSI calculation period

storage:
  processed_dir: "data/processed"                # Output directory
  output_file: "data/processed/stock_features.parquet"

supabase:
  auto_sync: false                               # Auto-sync after pipeline
  batch_size: 1000                               # Records per batch
```

### Environment Variables (`.env`):
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
API_BASE_URL=http://127.0.0.1:8000  # For dashboard
```

---

## 📈 Technical Indicators Calculated

| Indicator | Description | Use Case |
|-----------|-------------|----------|
| **SMA (20, 50)** | Simple Moving Average | Trend identification |
| **RSI (14)** | Relative Strength Index | Overbought/oversold signals |
| **MACD** | Moving Average Convergence Divergence | Momentum indicator |
| **Daily Return** | Percentage price change | Performance metric |
| **Volatility** | Rolling standard deviation | Risk assessment |

---

## 🧪 Testing & Validation

### 1. Test Pipeline Execution
```bash
python data_pipeline.py
```
Check `data/processed/` for output files.

### 2. Test API Endpoints
```bash
# Start API
python run_all.py --start-api

# In another terminal, test endpoints
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/
```

### 3. Test Supabase Sync (Dry Run)
```python
from supabase_ingestion import SupabaseIngestion
from config_loader import get_output_file

ingestion = SupabaseIngestion(supabase_url, supabase_key)
summary = ingestion.sync_data(get_output_file(), dry_run=True)
print(summary)
```

### 4. Test Dashboard
```bash
streamlit run dashboard.py
```
Navigate to `http://localhost:8501` and verify all tabs load.

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError"
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "API not connecting" in dashboard
**Solution:** Make sure API is running
```bash
python run_all.py --start-api
```

### Issue: "Supabase sync failed"
**Solution:** Check `.env` credentials and network connection
```bash
# Verify credentials
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('SUPABASE_URL'))"
```

### Issue: "No data in dashboard"
**Solution:** Run pipeline first to populate data
```bash
python run_all.py --sync
```

---

## 📝 Maintenance & Updates

### Adding New Tickers:
1. Edit `config.yaml` → `data_sources.tickers`
2. Run pipeline: `python run_all.py --sync`

### Changing Date Range:
1. Edit `config.yaml` → `data_sources.start_date` / `end_date`
2. Run pipeline: `python run_all.py --sync`

### Adding New Features:
1. Edit `src/feature_engineering.py`
2. Update `data_pipeline.py` rename map if needed
3. Update `supabase/schema.sql` to add new columns
4. Run pipeline: `python run_all.py --sync`

---

## 🎓 Learning Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Streamlit Docs:** https://docs.streamlit.io/
- **Supabase Docs:** https://supabase.com/docs
- **Pandas TA:** https://github.com/twopirllc/pandas-ta
- **yfinance:** https://github.com/ranaroussi/yfinance

---

## 👥 Team Handoff

For ML team integration, see:
- `ML_TEAM_GUIDE.md` - Technical integration guide
- `EMAIL_TO_ML_TEAM.md` - Handoff email template
- `HANDOFF_CHECKLIST.md` - Verification checklist

---

## 📄 License & Credits

This project is built for educational/demonstration purposes.

**Data Source:** Yahoo Finance (via yfinance library)  
**Tech Stack:** Python, FastAPI, Streamlit, Supabase, Plotly  
**Author:** Data Engineering Team  

---

## 🚀 Next Steps

1. ✅ Run the pipeline to generate initial data
2. ✅ Set up Supabase (optional but recommended)
3. ✅ Test the API endpoints
4. ✅ Launch the dashboard for monitoring
5. ✅ Share API documentation with ML team
6. ✅ Schedule automated pipeline runs

**For Demo:** Follow `DASHBOARD_DEMO_GUIDE.md` for presentation script.

---

**Questions?** Check the documentation files or review the inline code comments.
