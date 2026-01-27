-- Migration: Add Retraining Tables and Enhanced Drift Tracking
-- ============================================================
-- This migration adds support for:
-- 1. Retraining job tracking
-- 2. Per-ticker configuration
-- 3. Enhanced drift alert fields

-- ============================================================
-- Table 1: retraining_jobs
-- ============================================================
-- Tracks all retraining triggers (auto and manual)

CREATE TABLE IF NOT EXISTS retraining_jobs (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    triggered_by VARCHAR(50) DEFAULT 'auto_drift',
    drift_severity VARCHAR(20),
    ml_job_id VARCHAR(100),
    ml_api_status VARCHAR(50),
    ml_api_response JSONB,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    
    -- Indexes for common queries
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_retraining_jobs_ticker_triggered 
    ON retraining_jobs (ticker, triggered_at DESC);

CREATE INDEX idx_retraining_jobs_status 
    ON retraining_jobs (status, triggered_at DESC);

CREATE INDEX idx_retraining_jobs_ml_job_id 
    ON retraining_jobs (ml_job_id) WHERE ml_job_id IS NOT NULL;

COMMENT ON TABLE retraining_jobs IS 'Tracks all model retraining jobs triggered by drift detection or manual requests';
COMMENT ON COLUMN retraining_jobs.triggered_by IS 'Source of trigger: auto_drift, manual, scheduled, etc.';
COMMENT ON COLUMN retraining_jobs.ml_api_status IS 'Response status from ML team API: success, timeout, failed';
COMMENT ON COLUMN retraining_jobs.ml_api_response IS 'Full JSON response from ML API';

-- ============================================================
-- Table 2: ticker_config
-- ============================================================
-- Per-ticker drift detection and retraining configuration

CREATE TABLE IF NOT EXISTS ticker_config (
    ticker VARCHAR(20) PRIMARY KEY,
    auto_retrain_enabled BOOLEAN DEFAULT FALSE,
    requires_approval BOOLEAN DEFAULT FALSE,
    drift_threshold DECIMAL(4,3) DEFAULT 0.05,
    psi_threshold DECIMAL(4,3) DEFAULT 0.20,
    min_retrain_interval_hours INTEGER DEFAULT 6,
    last_retrain_at TIMESTAMPTZ,
    is_critical BOOLEAN DEFAULT FALSE,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_drift_threshold CHECK (drift_threshold > 0 AND drift_threshold < 1),
    CONSTRAINT valid_psi_threshold CHECK (psi_threshold >= 0),
    CONSTRAINT valid_interval CHECK (min_retrain_interval_hours >= 0)
);

CREATE INDEX idx_ticker_config_auto_retrain 
    ON ticker_config (auto_retrain_enabled) WHERE auto_retrain_enabled = TRUE;

CREATE INDEX idx_ticker_config_critical 
    ON ticker_config (is_critical) WHERE is_critical = TRUE;

COMMENT ON TABLE ticker_config IS 'Per-ticker configuration for drift detection and auto-retraining';
COMMENT ON COLUMN ticker_config.auto_retrain_enabled IS 'Whether to automatically trigger retraining on drift';
COMMENT ON COLUMN ticker_config.requires_approval IS 'Whether retraining requires manual approval (for critical tickers)';
COMMENT ON COLUMN ticker_config.is_critical IS 'Mark ticker as critical (requires approval, extra monitoring)';

-- ============================================================
-- Table 3: Enhance model_health_alerts
-- ============================================================
-- Add new columns to existing table

-- Check if columns exist before adding (idempotent)
DO $$ 
BEGIN
    -- Add drift_score column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'model_health_alerts' AND column_name = 'drift_score'
    ) THEN
        ALTER TABLE model_health_alerts ADD COLUMN drift_score DECIMAL(5,4);
    END IF;
    
    -- Add severity column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'model_health_alerts' AND column_name = 'severity'
    ) THEN
        ALTER TABLE model_health_alerts ADD COLUMN severity VARCHAR(20);
    END IF;
    
    -- Add psi column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'model_health_alerts' AND column_name = 'psi'
    ) THEN
        ALTER TABLE model_health_alerts ADD COLUMN psi DECIMAL(6,4);
    END IF;
    
    -- Add acknowledged column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'model_health_alerts' AND column_name = 'acknowledged'
    ) THEN
        ALTER TABLE model_health_alerts ADD COLUMN acknowledged BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- Add acknowledged_by column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'model_health_alerts' AND column_name = 'acknowledged_by'
    ) THEN
        ALTER TABLE model_health_alerts ADD COLUMN acknowledged_by VARCHAR(100);
    END IF;
    
    -- Add acknowledged_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'model_health_alerts' AND column_name = 'acknowledged_at'
    ) THEN
        ALTER TABLE model_health_alerts ADD COLUMN acknowledged_at TIMESTAMPTZ;
    END IF;
END $$;

-- Add index for acknowledged alerts
CREATE INDEX IF NOT EXISTS idx_model_health_alerts_acknowledged 
    ON model_health_alerts (acknowledged, detected_at DESC);

-- Add index for severity
CREATE INDEX IF NOT EXISTS idx_model_health_alerts_severity 
    ON model_health_alerts (severity, detected_at DESC);

-- ============================================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to ticker_config
DROP TRIGGER IF EXISTS update_ticker_config_updated_at ON ticker_config;
CREATE TRIGGER update_ticker_config_updated_at
    BEFORE UPDATE ON ticker_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Insert Default Configurations
-- ============================================================
-- Add default config for existing tickers (safe to run multiple times)

INSERT INTO ticker_config (ticker, auto_retrain_enabled, requires_approval, is_critical)
VALUES 
    -- Critical tickers (require approval)
    ('TCS.NS', FALSE, TRUE, TRUE),
    ('RELIANCE.NS', FALSE, TRUE, TRUE),
    ('HDFCBANK.NS', FALSE, TRUE, TRUE),
    
    -- Non-critical tickers (can auto-retrain)
    ('INFY.NS', FALSE, FALSE, FALSE),
    ('WIPRO.NS', FALSE, FALSE, FALSE)
ON CONFLICT (ticker) DO NOTHING;

-- ============================================================
-- Verification Queries
-- ============================================================
-- Run these to verify migration success

-- Check table exists
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' AND table_name IN ('retraining_jobs', 'ticker_config');

-- Check columns added to model_health_alerts
-- SELECT column_name, data_type FROM information_schema.columns 
-- WHERE table_name = 'model_health_alerts' AND column_name IN ('drift_score', 'severity', 'psi', 'acknowledged');

-- Check default ticker configs
-- SELECT * FROM ticker_config;
