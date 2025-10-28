-- Migration: Add ML Performance Tracking Columns to analysis_results table
-- Purpose: Extend database schema for dual AI performance tracking and cost monitoring
-- Date: October 27, 2024
-- Version: B1.1
-- Database: SQLite Compatible

-- Begin transaction for atomic migration
BEGIN;

-- Add ML performance tracking columns to analysis_results table (SQLite syntax)
ALTER TABLE analysis_results ADD COLUMN response_time_ms INTEGER DEFAULT NULL;
ALTER TABLE analysis_results ADD COLUMN cache_hit BOOLEAN DEFAULT 0;
ALTER TABLE analysis_results ADD COLUMN ai_cost_cents INTEGER DEFAULT 0;
ALTER TABLE analysis_results ADD COLUMN grok_analysis_time DATETIME DEFAULT NULL;
ALTER TABLE analysis_results ADD COLUMN deepseek_analysis_time DATETIME DEFAULT NULL;
ALTER TABLE analysis_results ADD COLUMN consensus_time DATETIME DEFAULT NULL;
ALTER TABLE analysis_results ADD COLUMN handoff_delta REAL DEFAULT NULL;
ALTER TABLE analysis_results ADD COLUMN ml_features TEXT DEFAULT '{}';
ALTER TABLE analysis_results ADD COLUMN consensus_score REAL DEFAULT NULL;
ALTER TABLE analysis_results ADD COLUMN api_calls_count INTEGER DEFAULT 0;
ALTER TABLE analysis_results ADD COLUMN data_sources_used TEXT DEFAULT '[]';
ALTER TABLE analysis_results ADD COLUMN performance_tier TEXT DEFAULT 'standard';

-- SQLite doesn't support column comments, but we'll document in code

-- Create performance indexes for ML queries (SQLite compatible)
CREATE INDEX IF NOT EXISTS idx_analysis_agreement_level ON analysis_results(agreement_level);
CREATE INDEX IF NOT EXISTS idx_analysis_consensus_score ON analysis_results(consensus_score);
CREATE INDEX IF NOT EXISTS idx_analysis_response_time ON analysis_results(response_time_ms);
CREATE INDEX IF NOT EXISTS idx_analysis_ai_cost ON analysis_results(ai_cost_cents);
CREATE INDEX IF NOT EXISTS idx_analysis_performance_tier ON analysis_results(performance_tier);

-- Composite indexes for time-series ML analysis
CREATE INDEX IF NOT EXISTS idx_symbol_created_consensus ON analysis_results(symbol, created_at, consensus_score);
CREATE INDEX IF NOT EXISTS idx_agreement_confidence_time ON analysis_results(agreement_level, confidence_score, created_at);

-- Index for cost analysis queries
CREATE INDEX IF NOT EXISTS idx_cost_analysis_daily ON analysis_results(date(created_at), ai_cost_cents);

-- Update existing records with default values for new columns
UPDATE analysis_results
SET
    cache_hit = 0,
    ai_cost_cents = 0,
    api_calls_count = 1,
    data_sources_used = '["demo"]',
    performance_tier = 'standard'
WHERE response_time_ms IS NULL;

-- Create a view for ML training data (SQLite compatible)
CREATE VIEW IF NOT EXISTS ml_training_data AS
SELECT
    id,
    symbol,
    created_at,
    recommendation,
    confidence_score,
    grok_score,
    deepseek_score,
    consensus_score,
    agreement_level,
    confidence_adjustment,
    response_time_ms,
    cache_hit,
    ai_cost_cents,
    handoff_delta,
    ml_features,
    technical_score,
    news_sentiment_score,
    social_sentiment_score,
    risk_level,
    performance_tier,
    strftime('%H', created_at) as analysis_hour,
    strftime('%w', created_at) as analysis_day_of_week,
    CASE
        WHEN response_time_ms < 200 THEN 'fast'
        WHEN response_time_ms < 500 THEN 'standard'
        ELSE 'slow'
    END as response_category
FROM analysis_results
WHERE grok_score IS NOT NULL
  AND deepseek_score IS NOT NULL
  AND agreement_level IS NOT NULL;

-- Create a view for cost monitoring (SQLite compatible)
CREATE VIEW IF NOT EXISTS cost_monitoring_daily AS
SELECT
    date(created_at) as analysis_date,
    COUNT(*) as total_analyses,
    SUM(ai_cost_cents) as total_cost_cents,
    AVG(ai_cost_cents) as avg_cost_per_analysis,
    SUM(api_calls_count) as total_api_calls,
    COUNT(CASE WHEN cache_hit = 1 THEN 1 END) as cache_hits,
    COUNT(CASE WHEN cache_hit = 0 THEN 1 END) as cache_misses,
    ROUND(COUNT(CASE WHEN cache_hit = 1 THEN 1 END) * 100.0 / COUNT(*), 2) as cache_hit_rate,
    AVG(response_time_ms) as avg_response_time_ms,
    COUNT(CASE WHEN agreement_level = 'strong_agreement' THEN 1 END) as strong_agreements,
    COUNT(CASE WHEN agreement_level = 'partial_agreement' THEN 1 END) as partial_agreements,
    COUNT(CASE WHEN agreement_level = 'strong_disagreement' THEN 1 END) as strong_disagreements
FROM analysis_results
WHERE created_at >= date('now', '-30 days')
  AND ai_cost_cents IS NOT NULL
GROUP BY date(created_at)
ORDER BY analysis_date DESC;

-- SQLite doesn't support ALTER TABLE ADD CONSTRAINT, so we'll skip constraints for now
-- Constraints will be enforced at the application level

-- Commit the transaction
COMMIT;
