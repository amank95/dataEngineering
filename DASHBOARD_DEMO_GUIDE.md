# Data Engineering Pipeline Dashboard

## What to Display for Your Mentor Demo

### 1. **Pipeline Health & Infrastructure** (Tab 1: Overview)
**Why:** Proves your system is production-ready and reliable.

**Metrics to Show:**
- ✅ **API Status**: Real-time connection indicator (Green = Healthy)
- 📦 **Parquet File Status**: Shows data persistence layer is working
- 🗄️ **Supabase Connection**: Demonstrates cloud database integration
- 📊 **Data Availability**: Confirms the pipeline has populated data

**What This Proves:**
- Your pipeline has proper health monitoring
- You've implemented a complete data storage strategy (local + cloud)
- The system can self-diagnose issues

---

### 2. **Data Quality Metrics** (Tab 4: Data Quality)
**Why:** Shows you understand production data engineering principles.

**Metrics to Show:**
- 📈 **Completeness Score**: Percentage of non-null values per column
- ⏰ **Data Freshness**: How recent is the latest data update
- 📊 **Distribution Analysis**: Histograms showing feature distributions (RSI, Returns)

**What This Proves:**
- You validate data quality (no garbage in, garbage out)
- You track data staleness (critical for ML model accuracy)
- You understand feature engineering validation

---

### 3. **Feature Engineering Validation** (Tab 2: Data Explorer)
**Why:** Demonstrates technical depth in financial analytics.

**Visualizations to Show:**
- 📈 **Price Time Series**: Interactive line chart showing stock prices
- 📊 **RSI Indicator**: Technical indicator with overbought/oversold zones
- 📉 **Daily Returns**: Bar chart showing volatility and trends

**What This Proves:**
- Your pipeline correctly calculates technical indicators
- Features are ready for ML consumption
- You can provide visual proof of data correctness

---

### 4. **Statistical Analytics** (Tab 3: Analytics)
**Why:** Shows you can derive insights from the data.

**Metrics to Show:**
- 📊 **Total Trading Days**: Data coverage
- 📈 **Average Daily Return**: Performance metric
- 📉 **Volatility (Std Dev)**: Risk metric
- 💹 **Price Change %**: Overall trend
- 🎯 **Sharpe Ratio**: Risk-adjusted return approximation

**What This Proves:**
- You understand financial metrics
- Your pipeline enables quantitative analysis
- Data is ready for ML model training

---

### 5. **MLOps Integration** (Sidebar: Pipeline Control)
**Why:** Demonstrates the "feedback loop" you mentioned for data drift.

**Features to Show:**
- ▶️ **Run Pipeline Button**: On-demand data refresh
- 🔄 **Refresh Data**: Cache invalidation and reload
- 📡 **API Endpoint Display**: Shows integration architecture

**What This Proves:**
- Pipeline can be triggered programmatically (automation-ready)
- Fresh data can be pulled to combat model drift
- System is designed for continuous operation

---

## The Theory: Why This Dashboard Matters

### For Data Engineering:
1. **Observability**: You can't manage what you can't measure. This dashboard provides visibility into pipeline health.
2. **Data Quality**: Production systems need quality gates. Your completeness and freshness metrics act as automated validators.
3. **Debugging**: When something breaks, this dashboard helps identify if it's a data issue, API issue, or pipeline issue.

### For MLOps (Data Drift Solution):
1. **Fresh Data Ingestion**: The "Run Pipeline" button allows scheduled or on-demand data updates.
2. **Drift Detection**: By comparing "Data Freshness" and "Distribution Analysis", you can spot when market behavior changes.
3. **Retraining Trigger**: When drift is detected, the ML team can use your API endpoints to fetch new training data and retrain models.

---

## Demo Script for Your Mentor

**Opening (30 seconds):**
"This is a Data Engineering pipeline for stock market data. It fetches, cleans, and engineers features for ML models. The dashboard shows pipeline health, data quality, and analytics."

**Section 1: Health Check (1 minute):**
"In the Overview tab, you can see all systems are healthy. The API is connected, data is stored in both Parquet files and Supabase cloud database, and we have fresh data available."

**Section 2: Data Quality (1 minute):**
"In the Data Quality tab, we track completeness—all columns are 100% populated. Data freshness shows the last update was X hours ago, which is within acceptable limits for daily stock data."

**Section 3: Feature Engineering (1.5 minutes):**
"In the Data Explorer, I can query any ticker—let's look at RELIANCE.NS. You can see the price chart, RSI indicator showing overbought/oversold zones, and daily returns. These features are calculated by the pipeline and ready for ML models."

**Section 4: Analytics (1 minute):**
"The Analytics tab shows statistical summaries. For example, RELIANCE.NS had an average daily return of X%, volatility of Y%, and a Sharpe ratio of Z. This helps validate that our feature engineering is producing sensible values."

**Section 5: MLOps Integration (1 minute):**
"To solve data drift, I can click 'Run Pipeline' to fetch the latest market data. This updates the database, and the ML team can immediately pull fresh training data via the API endpoints. This creates a feedback loop to keep models accurate."

**Closing (30 seconds):**
"This pipeline is production-ready with health monitoring, quality validation, and API access for ML integration. It's designed to combat data drift by continuously ingesting fresh market data."

---

## Quick Start Commands

1. **Install dependencies:**
   ```bash
   pip install streamlit plotly
   ```

2. **Make sure API is running:**
   ```bash
   python run_all.py --start-api
   ```
   (In a separate terminal)

3. **Launch dashboard:**
   ```bash
   streamlit run dashboard.py
   ```

4. **Open in browser:**
   Navigate to `http://localhost:8501`

---

## Tips for the Demo

1. **Run the pipeline first** to ensure you have data to display
2. **Test all tabs** before the demo to ensure everything loads
3. **Prepare a specific ticker** (like RELIANCE.NS or TCS.NS) that you know has good data
4. **Have the API running** in the background before starting the dashboard
5. **Practice the 5-minute walkthrough** to stay within time limits

---

## Technical Architecture (For Questions)

```
┌─────────────────┐
│  Yahoo Finance  │  (Data Source)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Pipeline  │  (Fetch → Clean → Feature Engineering)
└────────┬────────┘
         │
         ├──────────────┬─────────────┐
         ▼              ▼             ▼
    ┌────────┐    ┌──────────┐  ┌──────────┐
    │ Parquet│    │ Supabase │  │   API    │
    │  File  │    │ Database │  │ (FastAPI)│
    └────────┘    └──────────┘  └─────┬────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │    Dashboard    │
                              │   (Streamlit)   │
                              └─────────────────┘
```

This shows:
- **Data Source**: Yahoo Finance (free, reliable)
- **Pipeline**: Automated ETL process
- **Storage**: Dual persistence (local + cloud)
- **API**: RESTful interface for ML team
- **Dashboard**: Monitoring and analytics UI
