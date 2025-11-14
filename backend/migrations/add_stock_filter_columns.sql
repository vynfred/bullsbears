-- Add stock filter columns migration
-- Run with: gcloud sql import sql INSTANCE_NAME gs://BUCKET/add_stock_filter_columns.sql

BEGIN;

-- Add missing columns to stock_classifications
ALTER TABLE stock_classifications 
ADD COLUMN IF NOT EXISTS exchange VARCHAR(10),
ADD COLUMN IF NOT EXISTS company_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS sector VARCHAR(100),
ADD COLUMN IF NOT EXISTS industry VARCHAR(100);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_classifications_exchange ON stock_classifications(exchange);

-- Set default exchange for existing records
UPDATE stock_classifications 
SET exchange = 'NASDAQ' 
WHERE exchange IS NULL;

-- Make exchange non-nullable after setting defaults
ALTER TABLE stock_classifications 
ALTER COLUMN exchange SET NOT NULL;

COMMIT;