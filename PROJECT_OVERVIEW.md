# Project Overview: Squad1 Data Engineering

## 1. Executive Summary
**Purpose**: An end-to-end MLOps pipeline for stock market data, automating the extraction, transformation, loading (ETL), and monitoring of financial data for Machine Learning applications.

**Key Components**:
*   **ETL Pipeline**: Automates data fetching (Yahoo Finance), cleaning, and feature engineering.
*   **Integration**: Syncs processed data to **Supabase** (PostgreSQL) for cloud access.
*   **API**: A **FastAPI** server that serves data, metrics, and pipeline controls to external tools.
*   **Dashboard**: A **Streamlit** dashboard for real-time monitoring of pipeline health, data quality, and drift.

---

## 2. Automation & Data Flow
The system is designed to be fully automated via the master orchestration script: **`run_all.py`**.

### Workflow:
1.  **Data Extraction** (`fetch_data.py`):
    *   Downloads incremental OHLCV data from Yahoo Finance.
    *   Checks existing files to fetch *only* missing dates (optimization).
    *   Stores raw CSVs in `data/raw/`.

2.  **Data Cleaning** (`clean_data.py`):
    *   Validates data integrity (OHLC rules, outliers).
    *   **Currency Conversion**: Fetches `USDINR=X` rates to convert US stock prices to INR.
    *   Stores cleaned CSVs in `data/processed/`.

3.  **Feature Engineering** (`feature_engineering.py`):
    *   Calculates technical indicators for ML models.
    *   **Math Implemented**:
        *   **SMA (20, 50)**: Simple Moving Average (Rolling mean).
        *   **RSI (14)**: Relative Strength Index (Exponential Weighted Moving Average). formula: `100 - (100 / (1 + RS))`.
        *   **MACD**: Difference between 12-day and 26-day EMA.
        *   **Volatility**: 20-day rolling standard deviation of daily returns.

4.  **Consolidation** (`data_pipeline.py`):
    *   Merges all individual ticker files into a single master dataset: `data/processed/features_dataset.parquet`.

5.  **Drift Detection** (`drift_monitor.py`):
    *   Compares the new dataset against a baseline (`baseline_features.parquet`).
    *   Uses **Kolmogorov-Smirnov (KS) Test** to detect statistical drift in features.
    *   Alerts are logged to Supabase.

6.  **Cloud Sync** (`supabase_ingestion.py`):
    *   Batch upserts the final dataset to **Supabase**.

---

## 3. File Inventory & Analysis

### Core Orchestration
| File | Role | Details |
| :--- | :--- | :--- |
| `run_all.py` | **Entry Point** | Runs the full pipeline: Pipeline -> Drift Check -> Sync -> API. |
| `data_pipeline.py` | **Pipeline Logic** | Manages the parallel execution of the ETL steps using `ThreadPoolExecutor`. |

### Source Modules (`src/`)
| File | Role | Details |
| :--- | :--- | :--- |
| `src/fetch_data.py` | **Extraction** | Fetches `yfinance` data. Handles retries and incremental logic. |
| `src/clean_data.py` | **Processing** | Cleaning logic + USD-to-INR conversion. |
| `src/feature_engineering.py` | **Math** | Implements the financial formulas (RSI, MACD, SMA). |
| `src/data_quality.py` | **Validation** | Library of checks: `validate_ohlc`, `detect_outliers`, `check_data_freshness`. |

### API & Backend
| File | Role | Details |
| :--- | :--- | :--- |
| `api.py` | **Server** | FastAPI app. Endpoints: `/run-pipeline`, `/supabase/latest`. |
| `mlops_api.py` | **Monitoring** | specialized router for dashboard metrics (health, drift, quality). |
| `supabase_ingestion.py` | **Loader** | Handles reliable data upload to Supabase DB. |
| `ml_data_access.py` | **SDK** | Python helper for ML teams to load processed data easily in notebooks. |

### Dashboard
| File | Role | Details |
| :--- | :--- | :--- |
| `dashboard.py` | **UI** | Streamlit application main file. Visualizes everything. |
| `dashboard_utils.py` | **Helper** | Client-side functions to fetch data from the FastAPI server. |

### Utilities
| File | Role | Details |
| :--- | :--- | :--- |
| `drift_monitor.py` | **MLOps** | Runs the KS-Test for drift. usage: `scipy.stats.ks_2samp`. |
| `create_baseline.py` | **Setup** | Utility to creating the baseline reference file. |
| `config_loader.py` | **Config** | Safe loader for `config.yaml`. |

---

## 4. Automation & Storage
*   **Automation**: The entire process is automated by `python run_all.py`. It can be scheduled via Cron or Windows Task Scheduler.
*   **Storage**:
    *   **Local**: Intermediate CSVs in `data/processed/` and final `features_dataset.parquet`.
    *   **Cloud**: Supabase (PostgreSQL) table `stock_features`.
