-- Migration: Add Moon/Rug Alert Fields to AnalysisResult
-- Phase 2: Pattern Recognition System
-- Date: 2025-11-02

-- Add alert_type enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE alerttype AS ENUM ('MOON', 'RUG', 'GENERAL');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add alert_outcome enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE alertoutcome AS ENUM ('PENDING', 'SUCCESS', 'FAILURE', 'PARTIAL', 'EXPIRED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add new columns to analysis_results table
ALTER TABLE analysis_results 
ADD COLUMN IF NOT EXISTS alert_type alerttype DEFAULT 'GENERAL' NOT NULL,
ADD COLUMN IF NOT EXISTS features_json JSONB,
ADD COLUMN IF NOT EXISTS pattern_confidence FLOAT,
ADD COLUMN IF NOT EXISTS target_timeframe_days INTEGER DEFAULT 3,
ADD COLUMN IF NOT EXISTS move_threshold_percent FLOAT,
ADD COLUMN IF NOT EXISTS alert_outcome alertoutcome DEFAULT 'PENDING',
ADD COLUMN IF NOT EXISTS actual_move_percent FLOAT,
ADD COLUMN IF NOT EXISTS days_to_move INTEGER,
ADD COLUMN IF NOT EXISTS outcome_timestamp TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS outcome_notes TEXT;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_alert_type_timestamp ON analysis_results (alert_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_alert_outcome_timestamp ON analysis_results (alert_outcome, outcome_timestamp);
CREATE INDEX IF NOT EXISTS idx_symbol_alert_type ON analysis_results (symbol, alert_type);
CREATE INDEX IF NOT EXISTS idx_pattern_confidence ON analysis_results (pattern_confidence);
CREATE INDEX IF NOT EXISTS idx_alert_outcome_confidence ON analysis_results (alert_type, alert_outcome, pattern_confidence);
CREATE INDEX IF NOT EXISTS idx_symbol_outcome_time ON analysis_results (symbol, alert_outcome, outcome_timestamp);

-- Update existing records to have GENERAL alert_type (already set as default)
-- No additional update needed since DEFAULT is set

COMMIT;
