-- Migration: Create Candidate Tracking System Tables
-- Description: Creates tables for storing all predictor agent candidates and tracking their performance
-- Date: 2024-11-09
-- Version: 1.0

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table 1: pick_candidates - Store all predictor agent candidates
CREATE TABLE IF NOT EXISTS pick_candidates (
    candidate_id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    prediction_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    prediction_cycle VARCHAR(20) NOT NULL DEFAULT 'morning', -- morning, afternoon, evening
    
    -- Predictor Agent Information
    predictor_agent VARCHAR(50) NOT NULL, -- BullPredictorTechnical-DeepSeek, etc.
    agent_model VARCHAR(50) NOT NULL, -- deepseek-r1:8b, qwen2.5:14b, etc.
    agent_confidence DECIMAL(5,3) NOT NULL CHECK (agent_confidence >= 0 AND agent_confidence <= 1),
    prediction_type VARCHAR(10) NOT NULL CHECK (prediction_type IN ('bullish', 'bearish')),
    
    -- Market Data at Prediction Time
    current_price DECIMAL(10,2) NOT NULL,
    volume_24h BIGINT,
    market_cap BIGINT,
    
    -- Technical Indicators (JSON for flexibility)
    technical_indicators JSONB,
    
    -- Market Conditions
    market_conditions JSONB,
    
    -- Sentiment Data
    sentiment_score DECIMAL(5,3) CHECK (sentiment_score >= 0 AND sentiment_score <= 1),
    news_sentiment JSONB,
    social_sentiment JSONB,
    
    -- Vision Agent Targets (from vision analysis)
    target_low DECIMAL(10,2), -- Conservative target
    target_medium DECIMAL(10,2), -- Expected target  
    target_high DECIMAL(10,2), -- Optimistic target
    target_timeframe_days INTEGER DEFAULT 30,
    
    -- Vision Analysis Data
    chart_pattern VARCHAR(100),
    support_levels DECIMAL(10,2)[],
    resistance_levels DECIMAL(10,2)[],
    vision_confidence DECIMAL(5,3) CHECK (vision_confidence >= 0 AND vision_confidence <= 1),
    
    -- Risk Analysis
    stop_loss DECIMAL(10,2),
    risk_reward_ratio DECIMAL(5,2),
    position_size_recommendation DECIMAL(5,3),
    
    -- Arbitrator Decision
    selected_by_arbitrator BOOLEAN DEFAULT FALSE,
    arbitrator_reasoning TEXT,
    final_pick_id INTEGER, -- Reference to final picks table if selected
    
    -- Performance Tracking
    outcome_analyzed BOOLEAN DEFAULT FALSE,
    max_price_reached DECIMAL(10,2),
    min_price_reached DECIMAL(10,2),
    max_gain_percent DECIMAL(8,3),
    max_loss_percent DECIMAL(8,3),
    target_low_hit BOOLEAN DEFAULT FALSE,
    target_medium_hit BOOLEAN DEFAULT FALSE,
    target_high_hit BOOLEAN DEFAULT FALSE,
    days_to_target_hit INTEGER,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Table 2: candidate_price_tracking - Daily price monitoring for all candidates
CREATE TABLE IF NOT EXISTS candidate_price_tracking (
    tracking_id SERIAL PRIMARY KEY,
    candidate_id INTEGER NOT NULL REFERENCES pick_candidates(candidate_id) ON DELETE CASCADE,
    
    -- Price Data
    tracking_date DATE NOT NULL,
    open_price DECIMAL(10,2) NOT NULL,
    high_price DECIMAL(10,2) NOT NULL,
    low_price DECIMAL(10,2) NOT NULL,
    close_price DECIMAL(10,2) NOT NULL,
    volume BIGINT,
    
    -- Performance Metrics
    daily_change_percent DECIMAL(8,3),
    cumulative_change_percent DECIMAL(8,3),
    days_since_prediction INTEGER,
    
    -- Target Progress
    distance_to_low_target DECIMAL(8,3),
    distance_to_medium_target DECIMAL(8,3),
    distance_to_high_target DECIMAL(8,3),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(candidate_id, tracking_date)
);

-- Table 3: candidate_retrospective_analysis - Weekly analysis results
CREATE TABLE IF NOT EXISTS candidate_retrospective_analysis (
    analysis_id SERIAL PRIMARY KEY,
    analysis_date DATE NOT NULL,
    analysis_period_start DATE NOT NULL,
    analysis_period_end DATE NOT NULL,
    
    -- Analysis Results
    total_candidates_analyzed INTEGER NOT NULL,
    selected_candidates_count INTEGER NOT NULL,
    rejected_candidates_count INTEGER NOT NULL,
    
    -- Performance Comparison
    selected_avg_performance DECIMAL(8,3),
    rejected_avg_performance DECIMAL(8,3),
    missed_opportunities_count INTEGER,
    
    -- Top Missed Opportunities (JSON array of candidate details)
    missed_opportunities JSONB,
    
    -- Analysis Insights
    key_findings TEXT,
    pattern_discoveries JSONB,
    
    -- Recommendations
    model_recommendations JSONB,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Table 4: candidate_model_learning - Track model adjustments and improvements
CREATE TABLE IF NOT EXISTS candidate_model_learning (
    learning_id SERIAL PRIMARY KEY,
    learning_date DATE NOT NULL,
    
    -- Learning Source
    source_analysis_id INTEGER REFERENCES candidate_retrospective_analysis(analysis_id),
    learning_type VARCHAR(50) NOT NULL, -- feature_importance, criteria_update, pattern_discovery
    
    -- Learning Data
    feature_name VARCHAR(100),
    old_weight DECIMAL(8,5),
    new_weight DECIMAL(8,5),
    confidence_improvement DECIMAL(8,5),
    
    -- Criteria Updates
    criteria_name VARCHAR(100),
    old_threshold DECIMAL(10,5),
    new_threshold DECIMAL(10,5),
    success_rate_improvement DECIMAL(8,5),
    
    -- Pattern Discovery
    pattern_name VARCHAR(100),
    pattern_description TEXT,
    pattern_conditions JSONB,
    pattern_success_rate DECIMAL(5,3),
    
    -- Implementation Status
    implemented BOOLEAN DEFAULT FALSE,
    implementation_date TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_pick_candidates_ticker_date ON pick_candidates(ticker, prediction_date);
CREATE INDEX IF NOT EXISTS idx_pick_candidates_predictor ON pick_candidates(predictor_agent);
CREATE INDEX IF NOT EXISTS idx_pick_candidates_selected ON pick_candidates(selected_by_arbitrator);
CREATE INDEX IF NOT EXISTS idx_pick_candidates_outcome ON pick_candidates(outcome_analyzed);
CREATE INDEX IF NOT EXISTS idx_pick_candidates_prediction_date ON pick_candidates(prediction_date);

CREATE INDEX IF NOT EXISTS idx_candidate_price_tracking_candidate ON candidate_price_tracking(candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidate_price_tracking_date ON candidate_price_tracking(tracking_date);

CREATE INDEX IF NOT EXISTS idx_retrospective_analysis_date ON candidate_retrospective_analysis(analysis_date);

CREATE INDEX IF NOT EXISTS idx_model_learning_date ON candidate_model_learning(learning_date);
CREATE INDEX IF NOT EXISTS idx_model_learning_type ON candidate_model_learning(learning_type);

-- Triggers for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_pick_candidates_updated_at 
    BEFORE UPDATE ON pick_candidates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE pick_candidates IS 'Stores all predictor agent candidates with vision targets and performance tracking';
COMMENT ON TABLE candidate_price_tracking IS 'Daily price monitoring for all candidates over 30-day tracking period';
COMMENT ON TABLE candidate_retrospective_analysis IS 'Weekly analysis results identifying missed opportunities';
COMMENT ON TABLE candidate_model_learning IS 'Tracks model adjustments and improvements based on retrospective findings';

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bullsbears_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bullsbears_user;
