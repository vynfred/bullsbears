-- Migration: Add Moon/Rug Alert Fields to AnalysisResult (SQLite Version)
-- Phase 2: Pattern Recognition System
-- Date: 2025-11-04

-- Add new columns to analysis_results table
ALTER TABLE analysis_results ADD COLUMN alert_type TEXT DEFAULT 'GENERAL' NOT NULL;
ALTER TABLE analysis_results ADD COLUMN features_json TEXT;
ALTER TABLE analysis_results ADD COLUMN pattern_confidence REAL;
ALTER TABLE analysis_results ADD COLUMN target_timeframe_days INTEGER DEFAULT 3;
ALTER TABLE analysis_results ADD COLUMN move_threshold_percent REAL;
ALTER TABLE analysis_results ADD COLUMN alert_outcome TEXT DEFAULT 'PENDING';
ALTER TABLE analysis_results ADD COLUMN actual_move_percent REAL;
ALTER TABLE analysis_results ADD COLUMN days_to_move INTEGER;
ALTER TABLE analysis_results ADD COLUMN outcome_timestamp DATETIME;
ALTER TABLE analysis_results ADD COLUMN outcome_notes TEXT;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_alert_type_timestamp ON analysis_results (alert_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_alert_outcome_timestamp ON analysis_results (alert_outcome, outcome_timestamp);
CREATE INDEX IF NOT EXISTS idx_symbol_alert_type ON analysis_results (symbol, alert_type);
CREATE INDEX IF NOT EXISTS idx_pattern_confidence ON analysis_results (pattern_confidence);
CREATE INDEX IF NOT EXISTS idx_alert_outcome_confidence ON analysis_results (alert_type, alert_outcome, pattern_confidence);
CREATE INDEX IF NOT EXISTS idx_symbol_outcome_time ON analysis_results (symbol, alert_outcome, outcome_timestamp);
