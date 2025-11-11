-- Migration: 16+2 Agent System Schema with Tiered Stock Classification
-- Description: Database schema for Finma-7b prescreen + 16 local + 2 cloud agent architecture
-- Date: November 10, 2024

-- =====================================================
-- TIERED STOCK CLASSIFICATION SYSTEM
-- =====================================================

-- Stock Classification Tracking
CREATE TABLE IF NOT EXISTS stock_classifications (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    current_tier VARCHAR(20) NOT NULL, -- 'ALL', 'ACTIVE', 'QUALIFIED', 'SHORT_LIST', 'PICKS'
    price DECIMAL(10,2),
    market_cap BIGINT,
    daily_volume BIGINT,
    last_qualified_date DATE,
    qualified_days_count INTEGER DEFAULT 0,
    selection_fatigue_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for stock_classifications
CREATE INDEX IF NOT EXISTS idx_classifications_tier ON stock_classifications (current_tier);
CREATE INDEX IF NOT EXISTS idx_classifications_symbol ON stock_classifications (symbol);
CREATE INDEX IF NOT EXISTS idx_classifications_qualified_date ON stock_classifications (last_qualified_date);
CREATE INDEX IF NOT EXISTS idx_classifications_updated ON stock_classifications (updated_at);

-- Kill Switch Status Tracking
CREATE TABLE IF NOT EXISTS kill_switch_status (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    vix_level DECIMAL(5,2),
    spy_change DECIMAL(5,3),
    kill_switch_active BOOLEAN NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for kill_switch_status
CREATE INDEX IF NOT EXISTS idx_kill_switch_date ON kill_switch_status (date);
CREATE INDEX IF NOT EXISTS idx_kill_switch_active ON kill_switch_status (kill_switch_active);

-- =====================================================
-- AGENT OUTPUT TABLES (16 Local + 2 Cloud)
-- =====================================================

-- Prescreen Agent Output (Finma-7b)
CREATE TABLE IF NOT EXISTS agent_prescreen (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_model VARCHAR(30) NOT NULL DEFAULT 'finma-7b',
    screening_date DATE NOT NULL,
    qualified_for_analysis BOOLEAN NOT NULL,
    momentum_score DECIMAL(5,3),
    news_sentiment_score DECIMAL(5,3),
    prescreen_reasoning TEXT,
    market_context JSON, -- VIX, SPY, sector performance
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_prescreen_symbol (symbol),
    INDEX idx_prescreen_date (screening_date),
    INDEX idx_prescreen_qualified (qualified_for_analysis),
    INDEX idx_prescreen_created (created_at)
);

-- Core Prediction Agents Output (8 agents: 4 DeepSeek + 4 Qwen)
CREATE TABLE IF NOT EXISTS agent_predictions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    agent_model VARCHAR(30) NOT NULL, -- 'deepseek-r1:8b', 'qwen3:8b-instruct'
    prediction_type VARCHAR(20) NOT NULL, -- 'bullish', 'bearish'
    confidence_score DECIMAL(5,3) NOT NULL,
    reasoning TEXT NOT NULL,
    target_price DECIMAL(10,2),
    timeframe_days INTEGER,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_predictions_symbol (symbol),
    INDEX idx_predictions_agent (agent_name),
    INDEX idx_predictions_type (prediction_type),
    INDEX idx_predictions_created (created_at)
);

-- Vision Analysis Output (2 agents)
CREATE TABLE IF NOT EXISTS agent_vision_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL, -- 'VisionAgent-Primary' or 'VisionAgent-Secondary'
    agent_model VARCHAR(30) NOT NULL, -- 'qwen3-vl:8b-instruct' or 'llama3.2-vision:11b'
    chart_patterns JSON, -- Array of detected patterns
    support_levels JSON, -- Array of 3 support price levels for bearish picks
    resistance_levels JSON, -- Array of resistance price levels for bullish picks
    breakout_probability DECIMAL(5,3),
    pattern_confidence DECIMAL(5,3),
    visual_sentiment VARCHAR(20), -- 'bullish', 'bearish', 'neutral'
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_vision_symbol (symbol),
    INDEX idx_vision_agent (agent_name),
    INDEX idx_vision_created (created_at)
);

-- Risk Analysis Output (2 agents)
CREATE TABLE IF NOT EXISTS agent_risk_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    agent_model VARCHAR(30) NOT NULL,
    risk_profile VARCHAR(20) NOT NULL, -- 'conservative', 'aggressive'
    stop_loss DECIMAL(10,2), -- Only for bullish picks, NULL for bearish
    position_size_recommendation DECIMAL(5,3),
    risk_reward_ratio DECIMAL(5,2),
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_risk_symbol (symbol),
    INDEX idx_risk_agent (agent_name),
    INDEX idx_risk_profile (risk_profile),
    INDEX idx_risk_created (created_at)
);

-- Target Consensus Analysis Output (2 agents)
CREATE TABLE IF NOT EXISTS agent_target_consensus (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    agent_model VARCHAR(30) NOT NULL,
    analysis_type VARCHAR(20) NOT NULL, -- 'target_technical', 'target_fundamental'
    target_low DECIMAL(10,2),
    target_medium DECIMAL(10,2),
    target_high DECIMAL(10,2),
    confidence_score DECIMAL(5,3),
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_target_symbol (symbol),
    INDEX idx_target_agent (agent_name),
    INDEX idx_target_type (analysis_type),
    INDEX idx_target_created (created_at)
);

-- RSS News Analysis Output (1 local agent)
CREATE TABLE IF NOT EXISTS agent_rss_news (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL DEFAULT 'RSSNewsAgent',
    agent_model VARCHAR(30) NOT NULL, -- Local model for RSS processing
    sentiment_score DECIMAL(5,3) NOT NULL, -- -1.0 to 1.0
    confidence_score DECIMAL(5,3) NOT NULL,
    key_topics JSON, -- Array of key topics/themes
    news_articles JSON, -- Array of relevant RSS news articles
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_rss_news_symbol (symbol),
    INDEX idx_rss_news_created (created_at)
);

-- Social Analysis Output (1 cloud agent - Grok)
CREATE TABLE IF NOT EXISTS agent_social_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL DEFAULT 'GrokSocialAgent',
    agent_model VARCHAR(30) NOT NULL DEFAULT 'Grok-4',
    sentiment_score DECIMAL(5,3) NOT NULL, -- -1.0 to 1.0
    confidence_score DECIMAL(5,3) NOT NULL,
    social_mentions INTEGER,
    key_topics JSON, -- Array of trending topics/themes
    social_sources JSON, -- Array of social media sources analyzed
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_social_symbol (symbol),
    INDEX idx_social_created (created_at)
);

-- =====================================================
-- CONSENSUS AND ARBITRATION TABLES
-- =====================================================

-- Prediction Consensus (8 agents: 4 DeepSeek + 4 Qwen)
CREATE TABLE IF NOT EXISTS consensus_predictions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id UUID NOT NULL,
    analysis_date DATE NOT NULL,

    -- DeepSeek vs Qwen model validation
    deepseek_bull_confidence DECIMAL(5,3),
    deepseek_bear_confidence DECIMAL(5,3),
    qwen_bull_confidence DECIMAL(5,3),
    qwen_bear_confidence DECIMAL(5,3),

    -- Model agreement analysis
    model_consensus_score DECIMAL(5,3),
    prediction_alignment BOOLEAN,

    -- Final prediction consensus
    final_direction VARCHAR(10), -- 'bullish', 'bearish', 'neutral'
    final_confidence DECIMAL(5,3),
    consensus_strength VARCHAR(20), -- 'strong', 'moderate', 'weak'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_consensus_symbol (symbol),
    INDEX idx_consensus_round (consensus_round_id),
    INDEX idx_consensus_direction (final_direction),
    INDEX idx_consensus_date (analysis_date),
    INDEX idx_consensus_created (created_at)
);

-- Vision Consensus (2 agents)
CREATE TABLE IF NOT EXISTS consensus_vision (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id UUID NOT NULL,

    primary_agent_confidence DECIMAL(5,3),
    secondary_agent_confidence DECIMAL(5,3),
    pattern_agreement BOOLEAN,
    breakout_consensus DECIMAL(5,3),

    -- Bearish: 3 support levels, Bullish: resistance levels
    combined_support_levels JSON, -- For bearish picks
    combined_resistance_levels JSON, -- For bullish picks
    combined_patterns JSON,
    conflict_flags JSON, -- Array of disagreements for review

    final_visual_sentiment VARCHAR(20), -- 'bullish', 'bearish', 'neutral'
    final_pattern_confidence DECIMAL(5,3),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_vision_consensus_symbol (symbol),
    INDEX idx_vision_consensus_round (consensus_round_id),
    INDEX idx_vision_consensus_created (created_at)
);

-- Risk Consensus (2 agents)
CREATE TABLE IF NOT EXISTS consensus_risk (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id UUID NOT NULL,

    -- Only for bullish picks (bearish picks have no stop loss)
    conservative_stop_loss DECIMAL(10,2),
    aggressive_stop_loss DECIMAL(10,2),
    final_stop_loss DECIMAL(10,2),

    risk_adjusted_position_size DECIMAL(5,3),
    consensus_risk_reward DECIMAL(5,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_risk_consensus_symbol (symbol),
    INDEX idx_risk_consensus_round (consensus_round_id),
    INDEX idx_risk_consensus_created (created_at)
);

-- Target Consensus (2 agents)
CREATE TABLE IF NOT EXISTS consensus_targets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id UUID NOT NULL,

    technical_targets JSON, -- Fibonacci, support/resistance, momentum
    fundamental_targets JSON, -- Earnings, valuation, catalyst-driven

    -- Final consensus targets
    final_target_low DECIMAL(10,2),
    final_target_medium DECIMAL(10,2),
    final_target_high DECIMAL(10,2),

    target_probabilities JSON, -- Confidence scores for each target level
    dual_validation_score DECIMAL(5,3),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_target_consensus_symbol (symbol),
    INDEX idx_target_consensus_round (consensus_round_id),
    INDEX idx_target_consensus_created (created_at)
);

-- =====================================================
-- FINAL ARBITRATION TABLE
-- =====================================================

-- Final Arbitration (DeepSeek-V3 Cloud API)
CREATE TABLE IF NOT EXISTS final_arbitration (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id UUID NOT NULL,
    analysis_date DATE NOT NULL,

    arbitrator_model VARCHAR(30) NOT NULL DEFAULT 'DeepSeek-V3',
    arbitrator_type VARCHAR(20) NOT NULL DEFAULT 'cloud_api',

    -- All consensus inputs
    prediction_consensus_score DECIMAL(5,3),
    vision_consensus_score DECIMAL(5,3),
    risk_consensus_score DECIMAL(5,3),
    target_consensus_score DECIMAL(5,3),
    rss_news_score DECIMAL(5,3),
    social_sentiment_score DECIMAL(5,3),

    -- Final decision (max 6 picks: 3 bullish, 3 bearish max)
    final_recommendation VARCHAR(20), -- 'bullish_pick', 'bearish_pick', 'rejected'
    final_confidence DECIMAL(5,3),
    comprehensive_reasoning TEXT,
    daily_prompt_used TEXT, -- Store the arbitrator prompt used

    -- Bearish pick support levels (3 levels with time tracking)
    support_level_1 DECIMAL(10,2),
    support_level_2 DECIMAL(10,2),
    support_level_3 DECIMAL(10,2),
    support_level_1_hit_date DATE,
    support_level_2_hit_date DATE,
    support_level_3_hit_date DATE,

    -- Model learning data
    candidate_stored BOOLEAN DEFAULT TRUE,
    retrospective_pending BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_arbitration_symbol (symbol),
    INDEX idx_arbitration_round (consensus_round_id),
    INDEX idx_arbitration_date (analysis_date),
    INDEX idx_arbitration_recommendation (final_recommendation),
    INDEX idx_arbitration_created (created_at)
);

-- =====================================================
-- CANDIDATE TRACKING (Enhanced for Model Learning)
-- =====================================================

-- Store ALL predictor candidates for 30-day tracking
CREATE TABLE IF NOT EXISTS all_predictor_candidates (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id UUID NOT NULL,
    analysis_date DATE NOT NULL,

    -- Predictor agent details
    predictor_agent VARCHAR(50) NOT NULL,
    predictor_model VARCHAR(30) NOT NULL,
    prediction_type VARCHAR(20) NOT NULL, -- 'bullish', 'bearish'
    prediction_confidence DECIMAL(5,3),
    prediction_reasoning TEXT,

    -- Vision agent targets
    vision_target_low DECIMAL(10,2),
    vision_target_medium DECIMAL(10,2),
    vision_target_high DECIMAL(10,2),
    vision_confidence DECIMAL(5,3),

    -- Selection status and fatigue tracking
    selected_for_final BOOLEAN DEFAULT FALSE,
    selection_fatigue_count INTEGER DEFAULT 0,
    arbitrator_reasoning TEXT,

    -- Performance tracking (30-day window)
    entry_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    max_gain DECIMAL(5,3),
    min_loss DECIMAL(5,3),
    target_hit_status VARCHAR(20), -- 'none', 'low', 'medium', 'high'
    days_to_target_hit INTEGER,
    tracking_end_date DATE, -- 30 days from analysis_date

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_candidates_symbol (symbol),
    INDEX idx_candidates_round (consensus_round_id),
    INDEX idx_candidates_agent (predictor_agent),
    INDEX idx_candidates_selected (selected_for_final),
    INDEX idx_candidates_date (analysis_date),
    INDEX idx_candidates_tracking_end (tracking_end_date),
    INDEX idx_candidates_created (created_at)
);

-- Weekly retrospective analysis results
CREATE TABLE IF NOT EXISTS retrospective_analysis (
    id SERIAL PRIMARY KEY,
    analysis_week DATE NOT NULL,
    
    total_candidates INTEGER,
    selected_candidates INTEGER,
    missed_opportunities INTEGER,
    
    -- Performance comparison
    selected_avg_performance DECIMAL(5,3),
    missed_avg_performance DECIMAL(5,3),
    opportunity_cost DECIMAL(5,3),
    
    -- Model learning insights
    best_performing_models JSON,
    underperforming_models JSON,
    pattern_insights JSON,
    
    -- Recommendations
    model_adjustments JSON,
    selection_criteria_updates JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_retrospective_week (analysis_week),
    INDEX idx_retrospective_created (created_at)
);

-- =====================================================
-- PERFORMANCE OPTIMIZATION INDEXES
-- =====================================================

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_symbol_round_created 
ON agent_predictions_optimized (symbol, created_at);

CREATE INDEX IF NOT EXISTS idx_consensus_symbol_created 
ON consensus_predictions (symbol, created_at);

CREATE INDEX IF NOT EXISTS idx_arbitration_tier_created 
ON final_arbitration (tier_classification, created_at);

-- =====================================================
-- VIEWS FOR EASY QUERYING
-- =====================================================

-- Complete consensus view for a symbol
CREATE OR REPLACE VIEW v_complete_consensus AS
SELECT 
    cp.symbol,
    cp.consensus_round_id,
    cp.final_direction,
    cp.final_confidence,
    cv.final_visual_sentiment,
    cv.final_pattern_confidence,
    cr.balanced_stop_loss,
    cr.balanced_targets,
    ct.final_target_low,
    ct.final_target_medium,
    ct.final_target_high,
    fa.final_recommendation,
    fa.final_confidence as arbitrator_confidence,
    fa.tier_classification,
    cp.created_at
FROM consensus_predictions cp
LEFT JOIN consensus_vision cv ON cp.consensus_round_id = cv.consensus_round_id
LEFT JOIN consensus_risk cr ON cp.consensus_round_id = cr.consensus_round_id  
LEFT JOIN consensus_targets ct ON cp.consensus_round_id = ct.consensus_round_id
LEFT JOIN final_arbitration fa ON cp.consensus_round_id = fa.consensus_round_id;

-- Agent performance summary view
CREATE OR REPLACE VIEW v_agent_performance AS
SELECT 
    agent_name,
    agent_model,
    COUNT(*) as total_predictions,
    AVG(confidence_score) as avg_confidence,
    COUNT(CASE WHEN confidence_score > 0.7 THEN 1 END) as high_confidence_predictions,
    DATE(created_at) as prediction_date
FROM agent_predictions_optimized
GROUP BY agent_name, agent_model, DATE(created_at)
ORDER BY prediction_date DESC, avg_confidence DESC;
