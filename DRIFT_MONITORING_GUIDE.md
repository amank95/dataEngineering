# Model-Aware Feature Store: Drift Detection Guide

## Overview

Your pipeline now includes **automatic data drift detection** that compares live data against a training baseline using statistical tests (Kolmogorov-Smirnov). When drift is detected, alerts are automatically written to Supabase.

## What Was Implemented

### 1. **Drift Monitor Module** (`drift_monitor.py`)
- Compares baseline vs current data using KS-2samp test
- Monitors key features: `sma_20`, `rsi_14`, `volatility`
- Detects drift when p-value < 0.05 (configurable)
- Writes alerts to `model_health_alerts` Supabase table

### 2. **Database Schema** (`supabase/schema.sql`)
- New table: `model_health_alerts`
- Stores: ticker, feature, p-value, statistic, sample sizes, timestamp
- Indexed for fast queries by ticker and detection time

### 3. **Pipeline Integration** (`supabase_ingestion.py`)
- Drift monitoring runs **automatically** after successful Supabase sync
- Non-blocking: failures don't stop the pipeline
- Logs drift detection results

### 4. **Dashboard Integration** (`dashboard.py`)
- **New "Model Health" metric** in Overview tab (5th column)
- Shows "Stable" (green) or "Drift Detected" (red)
- Queries `model_health_alerts` table for last 24 hours

### 5. **API Endpoints** (`api.py`)
- `GET /supabase/model-health` - Get overall health status
- `GET /supabase/drift-alerts` - Get detailed drift alerts

## Setup Instructions

### Step 1: Create Baseline Dataset

**IMPORTANT:** You need a baseline file before drift detection can work!

```bash
# Option 1: Use current processed data as baseline
python create_baseline.py

# Option 2: Specify custom source/output
python create_baseline.py --source data/processed/features_dataset.parquet --output data/processed/baseline_features.parquet
```

This creates `data/processed/baseline_features.parquet` which represents your "training phase" distribution.

### Step 2: Apply Database Schema

Run the updated schema in your Supabase project:

```sql
-- Run this in Supabase SQL Editor
CREATE TABLE IF NOT EXISTS model_health_alerts (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    feature VARCHAR(64) NOT NULL,
    p_value DOUBLE PRECISION NOT NULL,
    statistic DOUBLE PRECISION,
    alpha DOUBLE PRECISION DEFAULT 0.05,
    baseline_sample_size INTEGER,
    current_sample_size INTEGER,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_health_alerts_ticker_detected
    ON model_health_alerts (ticker, detected_at DESC);
```

Or use the full schema file:
```bash
# Copy and paste contents of supabase/schema.sql into Supabase SQL Editor
```

### Step 3: Install Dependencies

```bash
pip install scipy>=1.11.0
```

(Already added to `requirements.txt`)

### Step 4: Run Pipeline

The drift monitor runs automatically after Supabase sync:

```bash
python run_all.py --sync
```

Or just run the pipeline (if auto_sync is enabled in config.yaml):
```bash
python data_pipeline.py
```

## How It Works

1. **Baseline Phase**: You create a baseline from your training data
2. **Live Phase**: Pipeline runs and syncs to Supabase
3. **Drift Detection**: After sync, `drift_monitor.py` compares:
   - Baseline distribution (from `baseline_features.parquet`)
   - Current distribution (from latest `features_dataset.parquet`)
4. **Alert Generation**: If p-value < 0.05 for any feature, creates alert in Supabase
5. **Dashboard Display**: Dashboard queries alerts and shows health status

## Viewing Results

### Dashboard
1. Open Streamlit dashboard: `streamlit run dashboard.py`
2. Go to **📈 Overview** tab
3. Check the **5th metric card**: "Model Health"
   - **Green "Stable"** = No drift detected in last 24 hours
   - **Red "Drift Detected"** = Drift alerts found

### API
```bash
# Get overall health status
curl http://127.0.0.1:8000/supabase/model-health

# Get detailed alerts
curl http://127.0.0.1:8000/supabase/drift-alerts

# Filter by ticker
curl "http://127.0.0.1:8000/supabase/drift-alerts?ticker=RELIANCE.NS"
```

### Supabase
Query the table directly:
```sql
SELECT * FROM model_health_alerts 
ORDER BY detected_at DESC 
LIMIT 10;
```

## Configuration

### Environment Variables
```bash
# Optional: Custom baseline path
DRIFT_BASELINE_PATH=data/processed/baseline_features.parquet
```

### Code Configuration
Edit `drift_monitor.py`:
- `DEFAULT_FEATURES`: Features to monitor (default: `["sma_20", "rsi_14", "volatility"]`)
- `alpha`: Significance threshold (default: `0.05`)

## Troubleshooting

### "Baseline file not found"
**Solution**: Run `python create_baseline.py` first

### "Model Health shows Unknown"
**Solution**: 
- Check Supabase credentials in `.env`
- Verify `model_health_alerts` table exists
- Check dashboard logs for errors

### "No drift detected but should be"
**Solution**:
- Verify baseline file is from training phase (not current data)
- Check p-value threshold (default 0.05)
- Ensure sufficient sample sizes in both baseline and current data

### Performance Impact
- Drift detection adds ~1-3 seconds to pipeline (after sync)
- Uses efficient sampling (max 1000 rows per ticker)
- Non-blocking: failures don't stop pipeline

## Next Steps

1. **Create baseline** from your training data
2. **Run pipeline** to see drift detection in action
3. **Check dashboard** for Model Health status
4. **Query API** for detailed alerts
5. **Set up alerts** (email/Slack) based on `model_health_alerts` table

## Files Modified/Created

- ✅ `drift_monitor.py` - New drift detection module
- ✅ `supabase/schema.sql` - Added `model_health_alerts` table
- ✅ `supabase_ingestion.py` - Integrated drift monitor after sync
- ✅ `dashboard.py` - Added Model Health metric
- ✅ `api.py` - Added drift monitoring endpoints
- ✅ `create_baseline.py` - Helper script to create baseline
- ✅ `requirements.txt` - Added scipy dependency

## Summary

Your pipeline is now a **Model-Aware Feature Store** that:
- ✅ Automatically detects data drift
- ✅ Stores alerts in Supabase
- ✅ Displays health status in dashboard
- ✅ Provides API access to drift information
- ✅ Runs non-intrusively (doesn't slow down pipeline)

**Next**: Create your baseline and run the pipeline to see it in action!

