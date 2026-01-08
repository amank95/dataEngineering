# Supabase Serving Layer - Setup Guide

## Overview
This guide explains how to set up and use the Supabase serving layer for the stock market data pipeline.

## Prerequisites
- Supabase account (free tier is sufficient)
- Python 3.8+
- Existing Parquet file from the data pipeline

---

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Sign up or log in
3. Click "New Project"
4. Fill in:
   - **Name:** stock-market-pipeline
   - **Database Password:** (save this securely)
   - **Region:** Choose closest to your location
5. Wait for project to be created (~2 minutes)

---

## Step 2: Set Up Database Schema

### Option A: Using Supabase SQL Editor (Recommended)

1. In your Supabase dashboard, go to **SQL Editor**
2. Click **New Query**
3. Copy the contents of `supabase/schema.sql`
4. Paste into the editor
5. Click **Run** (or press Ctrl+Enter)
6. Verify success: You should see "Success. No rows returned"

### Option B: Using psql (Advanced)

```bash
# Get connection string from Supabase Dashboard > Settings > Database
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres" < supabase/schema.sql
```

---

## Step 3: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Get your Supabase credentials:
   - Go to **Settings > API** in Supabase dashboard
   - Copy **Project URL** → paste as `SUPABASE_URL`
   - Copy **service_role key** → paste as `SUPABASE_KEY`
   
   ⚠️ **Important:** Use the `service_role` key, not the `anon` key (service_role has write permissions)

3. Edit `.env`:
   ```bash
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-service-role-key-here
   ```

4. **Security:** Add `.env` to `.gitignore` (already done)

---

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `supabase==2.10.0` - Supabase Python client
- `python-dotenv==1.0.1` - Environment variable management

---

## Step 5: Run Initial Data Sync

### Test with Dry Run (Recommended First)

```bash
python supabase_ingestion.py --dry-run
```

This will:
- ✅ Load the Parquet file
- ✅ Prepare records
- ✅ Show what would be inserted
- ❌ NOT actually insert data

### Run Actual Sync

```bash
python supabase_ingestion.py
```

**Expected Output:**
```
2026-01-08 12:00:00 - INFO - Loading data from: data/processed/features_dataset.parquet
2026-01-08 12:00:01 - INFO - Loaded 25000 records from Parquet
2026-01-08 12:00:01 - INFO - Processing 25000 records in 25 batches
2026-01-08 12:00:02 - INFO - Processing batch 1/25 (1000 records)...
2026-01-08 12:00:03 - INFO - ✓ Batch 1 completed successfully
...
2026-01-08 12:00:45 - INFO - Sync completed successfully
```

### Custom Options

```bash
# Use different Parquet file
python supabase_ingestion.py --parquet-file /path/to/custom.parquet

# Adjust batch size (for slower networks)
python supabase_ingestion.py --batch-size 500

# Combine options
python supabase_ingestion.py --parquet-file custom.parquet --batch-size 2000 --dry-run
```

---

## Step 6: Verify Data in Supabase

### Option A: Table Editor (Visual)

1. Go to **Table Editor** in Supabase dashboard
2. Select `stock_features` table
3. You should see your data!

### Option B: SQL Editor (Query)

```sql
-- Check total records
SELECT COUNT(*) FROM stock_features;

-- View sample data
SELECT * FROM stock_features 
ORDER BY date DESC 
LIMIT 10;

-- Check tickers
SELECT DISTINCT ticker FROM stock_features;

-- Latest data per ticker
SELECT * FROM latest_stock_data LIMIT 10;
```

---

## Step 7: Query from Python

### Example: ML Training Query

```python
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Get training data for specific date range
response = supabase.table('stock_features')\
    .select('*')\
    .gte('date', '2024-01-01')\
    .lte('date', '2024-12-31')\
    .execute()

data = response.data
print(f"Retrieved {len(data)} records")
```

### Example: Dashboard Query

```python
# Get latest 30 days for a ticker
response = supabase.table('stock_features')\
    .select('date, close, rsi_14, daily_return')\
    .eq('ticker', 'RELIANCE.NS')\
    .order('date', desc=True)\
    .limit(30)\
    .execute()

data = response.data
```

---

## Automation

### Option 1: Manual Sync After Pipeline

```bash
# Run pipeline
python data_pipeline.py

# Sync to Supabase
python supabase_ingestion.py
```

### Option 2: Auto-Sync (Integrated)

1. Edit `config.yaml`:
   ```yaml
   supabase:
     auto_sync: true  # Change from false to true
   ```

2. Run pipeline (will auto-sync):
   ```bash
   python data_pipeline.py
   ```

### Option 3: Scheduled Sync (Cron/Task Scheduler)

**Linux/Mac (cron):**
```bash
# Edit crontab
crontab -e

# Add daily sync at 6 AM
0 6 * * * cd /path/to/project && python supabase_ingestion.py >> sync.log 2>&1
```

**Windows (Task Scheduler):**
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 6:00 AM
4. Action: Start a program
5. Program: `python`
6. Arguments: `supabase_ingestion.py`
7. Start in: `C:\path\to\project`

---

## Troubleshooting

### Error: "SUPABASE_URL and SUPABASE_KEY must be set"

**Solution:** Check that `.env` file exists and has correct values

```bash
# Verify .env exists
ls -la .env

# Check contents (be careful not to expose keys!)
cat .env
```

### Error: "relation 'stock_features' does not exist"

**Solution:** Schema not created. Run `supabase/schema.sql` in SQL Editor

### Error: "Batch X failed: 413 Request Entity Too Large"

**Solution:** Reduce batch size

```bash
python supabase_ingestion.py --batch-size 500
```

### Slow Performance

**Solutions:**
1. Check indexes are created:
   ```sql
   \di stock_features*
   ```

2. Run ANALYZE:
   ```sql
   ANALYZE stock_features;
   ```

3. Reduce batch size for slower networks

---

## Best Practices

1. **Always test with --dry-run first**
2. **Keep `.env` secure** - never commit to git
3. **Monitor Supabase dashboard** for usage limits
4. **Run ANALYZE** after large data loads
5. **Use batch size 1000** for most cases (default)
6. **Schedule syncs** during off-peak hours

---

## Performance Tips

### For Large Datasets (100K+ records)

1. **Increase batch size:**
   ```bash
   python supabase_ingestion.py --batch-size 5000
   ```

2. **Use connection pooling** (automatic with Supabase)

3. **Consider partitioning** (for 1M+ records):
   ```sql
   -- Partition by year (advanced)
   CREATE TABLE stock_features_2024 
   PARTITION OF stock_features 
   FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
   ```

---

## Next Steps

- ✅ Set up Supabase project
- ✅ Create schema
- ✅ Configure environment
- ✅ Run initial sync
- ✅ Verify data
- 🔄 Integrate with ML workflows
- 🔄 Connect to dashboards
- 🔄 Set up automated syncs

---

## Support

- **Supabase Docs:** https://supabase.com/docs
- **Supabase Python Client:** https://github.com/supabase-community/supabase-py
- **Project Issues:** Check `supabase_ingestion.log` for detailed errors
