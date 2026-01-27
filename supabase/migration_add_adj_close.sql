-- ============================================
-- Migration: Add adj_close column
-- ============================================
-- This migration adds the missing 'adj_close' column to the stock_features table
-- Run this in your Supabase SQL Editor

-- Add the adj_close column
ALTER TABLE stock_features 
ADD COLUMN IF NOT EXISTS adj_close DECIMAL(12, 2);

-- Add comment for documentation
COMMENT ON COLUMN stock_features.adj_close IS 'Adjusted close price (accounts for dividends and stock splits)';

-- Verify the column was added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'stock_features' 
ORDER BY ordinal_position;
