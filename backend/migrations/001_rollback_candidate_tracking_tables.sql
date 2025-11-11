-- Rollback Migration: Drop Candidate Tracking System Tables
-- Description: Removes all candidate tracking tables and related objects
-- Date: 2024-11-09
-- Version: 1.0

-- Drop triggers first
DROP TRIGGER IF EXISTS update_pick_candidates_updated_at ON pick_candidates;

-- Drop function
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop indexes
DROP INDEX IF EXISTS idx_pick_candidates_ticker_date;
DROP INDEX IF EXISTS idx_pick_candidates_predictor;
DROP INDEX IF EXISTS idx_pick_candidates_selected;
DROP INDEX IF EXISTS idx_pick_candidates_outcome;
DROP INDEX IF EXISTS idx_pick_candidates_prediction_date;

DROP INDEX IF EXISTS idx_candidate_price_tracking_candidate;
DROP INDEX IF EXISTS idx_candidate_price_tracking_date;

DROP INDEX IF EXISTS idx_retrospective_analysis_date;

DROP INDEX IF EXISTS idx_model_learning_date;
DROP INDEX IF EXISTS idx_model_learning_type;

-- Drop tables in reverse order (due to foreign key constraints)
DROP TABLE IF EXISTS candidate_model_learning;
DROP TABLE IF EXISTS candidate_retrospective_analysis;
DROP TABLE IF EXISTS candidate_price_tracking;
DROP TABLE IF EXISTS pick_candidates;

-- Note: We don't drop the uuid-ossp extension as it might be used by other tables
