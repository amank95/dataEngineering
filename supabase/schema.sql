-- ============================================
-- Supabase Schema for Stock Market Features
-- ============================================
-- This schema is optimized for:
-- 1. ML model training (date-range queries)
-- 2. Dashboard queries (ticker-specific)
-- 3. Efficient upserts from Parquet source

-- Drop table if exists (for clean setup)
-- DROP TABLE IF EXISTS stock_features CASCADE;

-- ============================================
-- Main Table: stock_features
-- ============================================
CREATE TABLE IF NOT EXISTS stock_features (
    -- Primary Key Components
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    
    -- OHLCV Data
    open DECIMAL(12, 2),
    high DECIMAL(12, 2),
    low DECIMAL(12, 2),
    close DECIMAL(12, 2),
    volume BIGINT,
    
    -- Technical Indicators
    daily_return DECIMAL(10, 6),
    sma_20 DECIMAL(12, 2),
    sma_50 DECIMAL(12, 2),
    rsi_14 DECIMAL(6, 2),
    macd DECIMAL(12, 4),
    volatility DECIMAL(10, 6),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    PRIMARY KEY (ticker, date),
    
    -- Data validation constraints
    CONSTRAINT valid_ohlc CHECK (
        high >= low AND 
        high >= open AND 
        high >= close AND
        low <= open AND 
        low <= close
    ),
    CONSTRAINT valid_rsi CHECK (rsi_14 >= 0 AND rsi_14 <= 100),
    CONSTRAINT positive_volume CHECK (volume >= 0)
);

-- ============================================
-- Indexes for Performance
-- ============================================

-- Index 1: Date-range queries (ML training)
-- Use case: SELECT * WHERE date BETWEEN '2024-01-01' AND '2024-12-31'
CREATE INDEX IF NOT EXISTS idx_date_ticker 
ON stock_features(date DESC, ticker);

-- Index 2: Ticker time-series queries (Dashboards)
-- Use case: SELECT * WHERE ticker = 'RELIANCE.NS' ORDER BY date DESC
CREATE INDEX IF NOT EXISTS idx_ticker_date 
ON stock_features(ticker, date DESC);

-- Index 3: Recent data queries
-- Use case: SELECT * WHERE created_at > last_sync_time
CREATE INDEX IF NOT EXISTS idx_created_at 
ON stock_features(created_at DESC);

-- Index 4: Updated records tracking
CREATE INDEX IF NOT EXISTS idx_updated_at 
ON stock_features(updated_at DESC);

-- ============================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_stock_features_updated_at
    BEFORE UPDATE ON stock_features
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Optional: Row Level Security (RLS)
-- ============================================
-- Uncomment if you need multi-tenant access control

-- ALTER TABLE stock_features ENABLE ROW LEVEL SECURITY;

-- -- Policy: Allow public read access
-- CREATE POLICY "Allow public read access"
--     ON stock_features
--     FOR SELECT
--     USING (true);

-- -- Policy: Allow authenticated insert/update
-- CREATE POLICY "Allow authenticated insert/update"
--     ON stock_features
--     FOR ALL
--     USING (auth.role() = 'authenticated');

-- ============================================
-- Useful Views (Optional)
-- ============================================

-- View: Latest data per ticker
CREATE OR REPLACE VIEW latest_stock_data AS
SELECT DISTINCT ON (ticker)
    ticker,
    date,
    close,
    daily_return,
    rsi_14,
    updated_at
FROM stock_features
ORDER BY ticker, date DESC;

-- View: Daily summary statistics
CREATE OR REPLACE VIEW daily_market_summary AS
SELECT 
    date,
    COUNT(DISTINCT ticker) as ticker_count,
    AVG(daily_return) as avg_return,
    STDDEV(daily_return) as market_volatility,
    MAX(volume) as max_volume
FROM stock_features
GROUP BY date
ORDER BY date DESC;

-- ============================================
-- Utility Functions
-- ============================================

-- Function: Get ticker data for date range
CREATE OR REPLACE FUNCTION get_ticker_data(
    p_ticker VARCHAR(20),
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    date DATE,
    open DECIMAL,
    high DECIMAL,
    low DECIMAL,
    close DECIMAL,
    volume BIGINT,
    daily_return DECIMAL,
    sma_20 DECIMAL,
    sma_50 DECIMAL,
    rsi_14 DECIMAL,
    macd DECIMAL,
    volatility DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sf.date,
        sf.open,
        sf.high,
        sf.low,
        sf.close,
        sf.volume,
        sf.daily_return,
        sf.sma_20,
        sf.sma_50,
        sf.rsi_14,
        sf.macd,
        sf.volatility
    FROM stock_features sf
    WHERE sf.ticker = p_ticker
        AND sf.date >= p_start_date
        AND sf.date <= p_end_date
    ORDER BY sf.date DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Maintenance
-- ============================================

-- Analyze table for query optimization
ANALYZE stock_features;

-- Grant permissions (adjust as needed)
-- GRANT SELECT ON stock_features TO anon;
-- GRANT ALL ON stock_features TO authenticated;

-- ============================================
-- Model Health / Drift Monitoring
-- ============================================

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

-- ============================================
-- Verification Queries
-- ============================================

-- Check table structure
-- \d stock_features

-- Check indexes
-- \di stock_features*

-- Sample query to verify data
-- SELECT ticker, date, close, rsi_14 
-- FROM stock_features 
-- WHERE ticker = 'RELIANCE.NS' 
-- ORDER BY date DESC 
-- LIMIT 10;
