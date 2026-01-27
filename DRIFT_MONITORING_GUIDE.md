# Drift Monitoring & Auto-Retraining Guide

## Overview
The enhanced drift monitoring system now includes:
1.  **Multi-Method Detection**: Uses both **KS-Test** (for distribution shape) and **PSI** (Population Stability Index) to robustly detect drift.
2.  **Severity Classification**: Drift is classified as `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
3.  **Unified Drift Score**: A single 0-1 score combining KS and PSI metrics.
4.  **Auto-Retraining**: Automatically triggers the ML team's API when significant drift occurs (configurable).
5.  **Safety Features**: Rate limiting (e.g., max 1 retrain per 6 hours), Circuit Breaker, and Manual Approval mode for critical tickers.
6.  **Slack Integration**: Real-time alerts for drift events, approval requests, and retraining confirmations.

## Configuration (`config.yaml`)

### Drift Detection
```yaml
drift_detection:
  enabled: true
  check_interval_hours: 6
  methods:
    - ks_test
    - psi
  default_alpha: 0.05
  default_psi_threshold: 0.2
  monitored_features: ["sma_20", "rsi_14", "volatility", "daily_return", "macd"]
```

### Auto-Retraining
```yaml
retraining:
  default_enabled: false
  min_interval_hours: 6
  critical_tickers: ["TCS.NS", "RELIANCE.NS"]
  min_severity_for_auto_retrain: "MEDIUM"
```

## API Endpoints (MLOps)

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/mlops/drift-alerts/{ticker}` | GET | Fetch recent drift alerts for a ticker |
| `/api/mlops/training-data/{ticker}` | GET | Get fresh training data (last N days) |
| `/api/mlops/trigger-retrain/{ticker}` | POST | Manually trigger retraining (bypasses drift check) |
| `/api/mlops/acknowledge-drift/{ticker}` | POST | Acknowledge alerts (stops repeating them) |
| `/api/mlops/retraining-history/{ticker}` | GET | History of retraining jobs and statuses |

## Operational Workflows

### 1. Handling a CRITICAL Drift Alert
1.  **Slack Alert Received**: "CRITICAL drift detected for TCS.NS. Manual approval required."
2.  **Investigate**: Check dashboard or `/api/mlops/drift-detection/TCS.NS` to see which features drifted.
3.  **Approve Retraining**:
    *   Call: `POST /api/mlops/trigger-retrain/TCS.NS?reason=approved_via_slack`
    *   The system checks the Circuit Breaker and triggers the ML job.
4.  **Confirmation**: Slack message confirms "Retraining job started (Job ID: ...)"

### 2. Auto-Retraining Flow (Non-Critical Tickers)
1.  **Drift Detected**: System detects MEDIUM drift for INFY.NS.
2.  **Auto-Trigger**: System checks:
    *   Is auto-retrain enabled? (Yes)
    *   Is rate limit passed? (Yes, > 6 hours since last job)
    *   Is Circuit Breaker closed? (Yes, ML API is healthy)
3.  **Action**: Calls ML API `/retrain/INFY.NS`.
4.  **Logging**: Records job in `retraining_jobs` table and sends Slack notification.

## Maintenance

### Updating Baseline
Periodically (e.g., monthly), the baseline should be updated to reflect the new "normal" data distribution.
```bash
python create_baseline.py
```

### Checking System Health
Run the verification script to ensure all components (Slack, DB, Config) are connected:
```bash
python verify_drift_setup.py
```

### Database Schema
Two new tables manage this system:
*   `ticker_config`: Per-ticker settings (drift thresholds, auto-retrain flags).
*   `retraining_jobs`: Log of all retraining attempts and their outcomes.
