-- Rollback script for ML Performance Tracking Migration
-- This script removes the ML performance columns and related objects

BEGIN;

-- Drop views
DROP VIEW IF EXISTS ml_training_data;
DROP VIEW IF EXISTS cost_monitoring_daily;

-- Drop indexes
DROP INDEX IF EXISTS idx_analysis_agreement_level;
DROP INDEX IF EXISTS idx_analysis_consensus_score;
DROP INDEX IF EXISTS idx_analysis_response_time;
DROP INDEX IF EXISTS idx_analysis_ai_cost;
DROP INDEX IF EXISTS idx_analysis_performance_tier;
DROP INDEX IF EXISTS idx_symbol_created_consensus;
DROP INDEX IF EXISTS idx_agreement_confidence_time;
DROP INDEX IF EXISTS idx_cost_analysis_daily;

-- Drop constraints
ALTER TABLE analysis_results DROP CONSTRAINT IF EXISTS check_performance_tier;
ALTER TABLE analysis_results DROP CONSTRAINT IF EXISTS check_ai_cost_positive;
ALTER TABLE analysis_results DROP CONSTRAINT IF EXISTS check_response_time_positive;

-- Drop columns
ALTER TABLE analysis_results 
DROP COLUMN IF EXISTS response_time_ms,
DROP COLUMN IF EXISTS cache_hit,
DROP COLUMN IF EXISTS ai_cost_cents,
DROP COLUMN IF EXISTS grok_analysis_time,
DROP COLUMN IF EXISTS deepseek_analysis_time,
DROP COLUMN IF EXISTS consensus_time,
DROP COLUMN IF EXISTS handoff_delta,
DROP COLUMN IF EXISTS ml_features,
DROP COLUMN IF EXISTS consensus_score,
DROP COLUMN IF EXISTS api_calls_count,
DROP COLUMN IF EXISTS data_sources_used,
DROP COLUMN IF EXISTS performance_tier;

COMMIT;
