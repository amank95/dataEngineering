# Supabase Serving Layer

This directory contains the Supabase (Postgres) serving layer implementation for the stock market data pipeline.

## Quick Start

1. **Set up Supabase project** (see [SETUP_GUIDE.md](SETUP_GUIDE.md))
2. **Deploy schema:** Run `schema.sql` in Supabase SQL Editor
3. **Configure credentials:** Copy `../.env.example` to `../.env` and add your Supabase URL and key
4. **Install dependencies:** `pip install -r ../requirements.txt`
5. **Sync data:** `python ../supabase_ingestion.py`

## Files

- **`schema.sql`** - Database schema with optimized indexes
- **`SETUP_GUIDE.md`** - Comprehensive setup and usage guide
- **`query_examples.py`** - Example queries for ML and dashboards

## Architecture

```
Parquet (Source of Truth)
    ↓
supabase_ingestion.py (Batch Upsert)
    ↓
Supabase Postgres (Serving Layer)
    ↓
ML Models / Dashboards
```

## Key Features

- ✅ Optimized for time-series queries
- ✅ Composite primary key (ticker, date)
- ✅ Strategic indexes for ML and dashboard queries
- ✅ Batch upsert with conflict resolution
- ✅ Idempotent (safe to re-run)

## Usage

```bash
# Sync Parquet to Supabase
python ../supabase_ingestion.py

# Test without inserting
python ../supabase_ingestion.py --dry-run

# Custom batch size
python ../supabase_ingestion.py --batch-size 500
```

## Query Examples

```python
from supabase import create_client
import os

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get training data
response = supabase.table('stock_features')\
    .select('*')\
    .gte('date', '2024-01-01')\
    .execute()
```

See `query_examples.py` for more examples.

## Documentation

- **Setup Guide:** [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Schema Reference:** [schema.sql](schema.sql)
- **Query Examples:** [query_examples.py](query_examples.py)

## Support

For issues or questions, refer to:
- Supabase docs: https://supabase.com/docs
- Python client: https://github.com/supabase-community/supabase-py
