-- Migration: 16+2 Agent System Schema with Tiered Stock Classification (PostgreSQL Fixed)
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_prescreen
CREATE INDEX IF NOT EXISTS idx_prescreen_symbol ON agent_prescreen (symbol);
CREATE INDEX IF NOT EXISTS idx_prescreen_date ON agent_prescreen (screening_date);
CREATE INDEX IF NOT EXISTS idx_prescreen_qualified ON agent_prescreen (qualified_for_analysis);
CREATE INDEX IF NOT EXISTS idx_prescreen_created ON agent_prescreen (created_at);

-- Core Prediction Agents Output (8 agents: 4 DeepSeek + 4 Qwen)
CREATE TABLE IF NOT EXISTS agent_predictions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL, -- 'deepseek-bull-1', 'qwen-bear-2', etc.
    agent_model VARCHAR(30) NOT NULL, -- 'deepseek-r1-8b', 'qwen3-8b', etc.
    prediction_type VARCHAR(20) NOT NULL, -- 'bullish', 'bearish'
    confidence_score DECIMAL(5,3),
    target_price DECIMAL(10,2),
    timeframe_days INTEGER,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_predictions
CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON agent_predictions (symbol);
CREATE INDEX IF NOT EXISTS idx_predictions_agent ON agent_predictions (agent_name);
CREATE INDEX IF NOT EXISTS idx_predictions_type ON agent_predictions (prediction_type);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON agent_predictions (created_at);

-- Vision Analysis Output (2 agents)
CREATE TABLE IF NOT EXISTS agent_vision_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL, -- 'vision-primary', 'vision-secondary'
    agent_model VARCHAR(30) NOT NULL, -- 'qwen3-vl-11b', 'llama3.2-vision-11b'
    chart_timeframe VARCHAR(20), -- '1D', '5D', '1M', '3M'
    support_level_1 DECIMAL(10,2), -- Bearish support levels
    support_level_2 DECIMAL(10,2),
    support_level_3 DECIMAL(10,2),
    pattern_detected VARCHAR(100),
    visual_sentiment VARCHAR(20), -- 'bullish', 'bearish', 'neutral'
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_vision_analysis
CREATE INDEX IF NOT EXISTS idx_vision_symbol ON agent_vision_analysis (symbol);
CREATE INDEX IF NOT EXISTS idx_vision_agent ON agent_vision_analysis (agent_name);
CREATE INDEX IF NOT EXISTS idx_vision_created ON agent_vision_analysis (created_at);

-- Risk Analysis Output (2 agents)
CREATE TABLE IF NOT EXISTS agent_risk_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL, -- 'risk-conservative', 'risk-aggressive'
    agent_model VARCHAR(30) NOT NULL,
    risk_profile VARCHAR(20), -- 'conservative', 'aggressive'
    position_size_recommendation DECIMAL(5,3), -- 0.01 to 1.00
    stop_loss_price DECIMAL(10,2), -- Only for bullish picks
    risk_reward_ratio DECIMAL(5,2),
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_risk_analysis
CREATE INDEX IF NOT EXISTS idx_risk_symbol ON agent_risk_analysis (symbol);
CREATE INDEX IF NOT EXISTS idx_risk_agent ON agent_risk_analysis (agent_name);
CREATE INDEX IF NOT EXISTS idx_risk_profile ON agent_risk_analysis (risk_profile);
CREATE INDEX IF NOT EXISTS idx_risk_created ON agent_risk_analysis (created_at);

-- Target Consensus Analysis Output (2 agents)
CREATE TABLE IF NOT EXISTS agent_target_consensus (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50) NOT NULL, -- 'target-technical', 'target-fundamental'
    agent_model VARCHAR(30) NOT NULL,
    analysis_type VARCHAR(20), -- 'technical', 'fundamental'
    low_target DECIMAL(10,2),
    medium_target DECIMAL(10,2),
    high_target DECIMAL(10,2),
    confidence_score DECIMAL(5,3),
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_target_consensus
CREATE INDEX IF NOT EXISTS idx_target_symbol ON agent_target_consensus (symbol);
CREATE INDEX IF NOT EXISTS idx_target_agent ON agent_target_consensus (agent_name);
CREATE INDEX IF NOT EXISTS idx_target_type ON agent_target_consensus (analysis_type);
CREATE INDEX IF NOT EXISTS idx_target_created ON agent_target_consensus (created_at);

-- RSS News Analysis Output (1 local agent)
CREATE TABLE IF NOT EXISTS agent_rss_news (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_model VARCHAR(30) NOT NULL DEFAULT 'llama3.1-8b',
    news_sentiment VARCHAR(20), -- 'bullish', 'bearish', 'neutral'
    sentiment_score DECIMAL(5,3),
    key_events JSON, -- Array of key news events
    news_articles JSON, -- Array of relevant RSS news articles
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_rss_news
CREATE INDEX IF NOT EXISTS idx_rss_news_symbol ON agent_rss_news (symbol);
CREATE INDEX IF NOT EXISTS idx_rss_news_created ON agent_rss_news (created_at);

-- Social Analysis Output (1 cloud agent - Grok)
CREATE TABLE IF NOT EXISTS agent_social_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    agent_model VARCHAR(30) NOT NULL DEFAULT 'grok-2',
    social_sentiment VARCHAR(20), -- 'bullish', 'bearish', 'neutral'
    sentiment_score DECIMAL(5,3),
    mention_volume INTEGER,
    key_influencers JSON, -- Array of key social media influencers
    social_sources JSON, -- Array of social media sources analyzed
    reasoning TEXT,
    daily_prompt_used TEXT, -- Store the prompt used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_social_analysis
CREATE INDEX IF NOT EXISTS idx_social_symbol ON agent_social_analysis (symbol);
CREATE INDEX IF NOT EXISTS idx_social_created ON agent_social_analysis (created_at);

-- =====================================================
-- CONSENSUS AND ARBITRATION TABLES
-- =====================================================

-- Prediction Consensus (8 agents)
CREATE TABLE IF NOT EXISTS consensus_predictions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id VARCHAR(50) NOT NULL, -- Daily round identifier
    analysis_date DATE NOT NULL,
    
    -- Agent vote counts
    bullish_votes INTEGER DEFAULT 0,
    bearish_votes INTEGER DEFAULT 0,
    
    -- Weighted consensus (by confidence)
    weighted_bullish_score DECIMAL(8,3),
    weighted_bearish_score DECIMAL(8,3),
    
    -- Final consensus direction
    final_direction VARCHAR(20), -- 'bullish', 'bearish', 'neutral'
    final_confidence DECIMAL(5,3),
    consensus_strength VARCHAR(20), -- 'strong', 'moderate', 'weak'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for consensus_predictions
CREATE INDEX IF NOT EXISTS idx_consensus_symbol ON consensus_predictions (symbol);
CREATE INDEX IF NOT EXISTS idx_consensus_round ON consensus_predictions (consensus_round_id);
CREATE INDEX IF NOT EXISTS idx_consensus_direction ON consensus_predictions (final_direction);
CREATE INDEX IF NOT EXISTS idx_consensus_date ON consensus_predictions (analysis_date);
CREATE INDEX IF NOT EXISTS idx_consensus_created ON consensus_predictions (created_at);

-- Vision Consensus (2 agents)
CREATE TABLE IF NOT EXISTS consensus_vision (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id VARCHAR(50) NOT NULL,
    
    -- Support level consensus (for bearish picks)
    consensus_support_1 DECIMAL(10,2),
    consensus_support_2 DECIMAL(10,2),
    consensus_support_3 DECIMAL(10,2),
    
    -- Pattern consensus
    primary_pattern VARCHAR(100),
    secondary_pattern VARCHAR(100),
    pattern_strength VARCHAR(20), -- 'strong', 'moderate', 'weak'
    
    -- Final visual analysis
    final_visual_sentiment VARCHAR(20), -- 'bullish', 'bearish', 'neutral'
    final_pattern_confidence DECIMAL(5,3),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for consensus_vision
CREATE INDEX IF NOT EXISTS idx_vision_consensus_symbol ON consensus_vision (symbol);
CREATE INDEX IF NOT EXISTS idx_vision_consensus_round ON consensus_vision (consensus_round_id);
CREATE INDEX IF NOT EXISTS idx_vision_consensus_created ON consensus_vision (created_at);

-- Risk Consensus (2 agents)
CREATE TABLE IF NOT EXISTS consensus_risk (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id VARCHAR(50) NOT NULL,
    
    -- Position sizing consensus
    conservative_position_size DECIMAL(5,3),
    aggressive_position_size DECIMAL(5,3),
    final_position_size DECIMAL(5,3),
    
    risk_adjusted_position_size DECIMAL(5,3),
    consensus_risk_reward DECIMAL(5,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for consensus_risk
CREATE INDEX IF NOT EXISTS idx_risk_consensus_symbol ON consensus_risk (symbol);
CREATE INDEX IF NOT EXISTS idx_risk_consensus_round ON consensus_risk (consensus_round_id);
CREATE INDEX IF NOT EXISTS idx_risk_consensus_created ON consensus_risk (created_at);

-- Target Consensus (2 agents)
CREATE TABLE IF NOT EXISTS consensus_targets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id VARCHAR(50) NOT NULL,

    -- Target price consensus
    technical_low_target DECIMAL(10,2),
    technical_medium_target DECIMAL(10,2),
    technical_high_target DECIMAL(10,2),
    fundamental_low_target DECIMAL(10,2),
    fundamental_medium_target DECIMAL(10,2),
    fundamental_high_target DECIMAL(10,2),

    -- Final consensus targets
    final_low_target DECIMAL(10,2),
    final_medium_target DECIMAL(10,2),
    final_high_target DECIMAL(10,2),
    target_probabilities JSON, -- Confidence scores for each target level
    dual_validation_score DECIMAL(5,3),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for consensus_targets
CREATE INDEX IF NOT EXISTS idx_target_consensus_symbol ON consensus_targets (symbol);
CREATE INDEX IF NOT EXISTS idx_target_consensus_round ON consensus_targets (consensus_round_id);
CREATE INDEX IF NOT EXISTS idx_target_consensus_created ON consensus_targets (created_at);

-- =====================================================
-- FINAL ARBITRATION TABLE
-- =====================================================

-- Final Arbitration Output (1 cloud agent - DeepSeek-V3)
CREATE TABLE IF NOT EXISTS final_arbitration (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id VARCHAR(50) NOT NULL,
    analysis_date DATE NOT NULL,

    -- Input data summary
    prediction_consensus_summary JSON,
    vision_consensus_summary JSON,
    risk_consensus_summary JSON,
    target_consensus_summary JSON,
    news_sentiment_summary JSON,
    social_sentiment_summary JSON,

    -- Arbitration decision
    final_recommendation VARCHAR(20), -- 'bullish', 'bearish', 'pass'
    arbitration_confidence DECIMAL(5,3),
    reasoning TEXT,

    -- Target information
    selected_target_low DECIMAL(10,2),
    selected_target_medium DECIMAL(10,2),
    selected_target_high DECIMAL(10,2),
    estimated_days_to_target INTEGER,

    -- Risk management
    position_size DECIMAL(5,3),
    stop_loss_price DECIMAL(10,2), -- Only for bullish picks

    -- Bearish-specific (support levels for alerts)
    bearish_support_1 DECIMAL(10,2),
    bearish_support_2 DECIMAL(10,2),
    bearish_support_3 DECIMAL(10,2),

    -- Tier classification for next round
    tier_classification VARCHAR(20), -- Recommendation for next tier

    -- Tracking flags
    candidate_stored BOOLEAN DEFAULT TRUE,
    retrospective_pending BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for final_arbitration
CREATE INDEX IF NOT EXISTS idx_arbitration_symbol ON final_arbitration (symbol);
CREATE INDEX IF NOT EXISTS idx_arbitration_round ON final_arbitration (consensus_round_id);
CREATE INDEX IF NOT EXISTS idx_arbitration_date ON final_arbitration (analysis_date);
CREATE INDEX IF NOT EXISTS idx_arbitration_recommendation ON final_arbitration (final_recommendation);
CREATE INDEX IF NOT EXISTS idx_arbitration_created ON final_arbitration (created_at);

-- =====================================================
-- CANDIDATE TRACKING (Enhanced for Model Learning)
-- =====================================================

-- Enhanced candidate tracking for 30-day performance monitoring
CREATE TABLE IF NOT EXISTS agent_candidates_optimized (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    consensus_round_id VARCHAR(50) NOT NULL,
    analysis_date DATE NOT NULL,

    -- Agent information
    predictor_agent VARCHAR(50) NOT NULL,
    agent_model VARCHAR(30) NOT NULL,
    agent_confidence DECIMAL(5,3),
    prediction_type VARCHAR(20), -- 'bullish', 'bearish'

    -- Selection status
    selected_for_final BOOLEAN DEFAULT FALSE,
    arbitrator_reasoning TEXT,

    -- Price tracking
    price_at_analysis DECIMAL(10,2),
    target_low DECIMAL(10,2),
    target_medium DECIMAL(10,2),
    target_high DECIMAL(10,2),

    -- Performance tracking (updated daily)
    current_price DECIMAL(10,2),
    max_price_reached DECIMAL(10,2),
    min_price_reached DECIMAL(10,2),
    days_tracked INTEGER DEFAULT 0,

    -- Outcome tracking
    target_hit_status VARCHAR(20), -- 'none', 'low', 'medium', 'high'
    days_to_target_hit INTEGER,
    tracking_end_date DATE, -- 30 days from analysis_date

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_candidates_optimized
CREATE INDEX IF NOT EXISTS idx_candidates_symbol ON agent_candidates_optimized (symbol);
CREATE INDEX IF NOT EXISTS idx_candidates_round ON agent_candidates_optimized (consensus_round_id);
CREATE INDEX IF NOT EXISTS idx_candidates_agent ON agent_candidates_optimized (predictor_agent);
CREATE INDEX IF NOT EXISTS idx_candidates_selected ON agent_candidates_optimized (selected_for_final);
CREATE INDEX IF NOT EXISTS idx_candidates_date ON agent_candidates_optimized (analysis_date);
CREATE INDEX IF NOT EXISTS idx_candidates_tracking_end ON agent_candidates_optimized (tracking_end_date);
CREATE INDEX IF NOT EXISTS idx_candidates_created ON agent_candidates_optimized (created_at);

-- Weekly retrospective analysis results
CREATE TABLE IF NOT EXISTS retrospective_analysis (
    id SERIAL PRIMARY KEY,
    analysis_week DATE NOT NULL, -- Monday of the analysis week

    -- Performance metrics
    total_candidates_tracked INTEGER,
    selected_candidates_count INTEGER,
    non_selected_candidates_count INTEGER,

    -- Outcome analysis
    selected_hit_rate DECIMAL(5,3), -- Percentage of selected that hit targets
    non_selected_hit_rate DECIMAL(5,3), -- Percentage of non-selected that hit targets

    -- Agent performance
    best_performing_agents JSON, -- Array of top agents by hit rate
    worst_performing_agents JSON, -- Array of bottom agents by hit rate
    agent_accuracy_scores JSON, -- Detailed accuracy by agent

    -- Learning insights
    pattern_discoveries JSON, -- New patterns discovered
    model_adjustments JSON,
    selection_criteria_updates JSON,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for retrospective_analysis
CREATE INDEX IF NOT EXISTS idx_retrospective_week ON retrospective_analysis (analysis_week);
CREATE INDEX IF NOT EXISTS idx_retrospective_created ON retrospective_analysis (created_at);

-- =====================================================
-- PERFORMANCE OPTIMIZATION INDEXES
-- =====================================================

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_symbol_round_created
ON agent_predictions (symbol, created_at);

CREATE INDEX IF NOT EXISTS idx_consensus_symbol_created
ON consensus_predictions (symbol, created_at);

CREATE INDEX IF NOT EXISTS idx_arbitration_tier_created
ON final_arbitration (tier_classification, created_at);

-- =====================================================
-- VIEWS FOR EASY QUERYING
-- =====================================================

-- Daily agent performance summary
CREATE OR REPLACE VIEW daily_agent_performance AS
SELECT
    DATE(created_at) as analysis_date,
    agent_name,
    agent_model,
    prediction_type,
    COUNT(*) as total_predictions,
    AVG(confidence_score) as avg_confidence,
    COUNT(CASE WHEN confidence_score > 0.6 THEN 1 END) as high_confidence_count
FROM agent_predictions
GROUP BY DATE(created_at), agent_name, agent_model, prediction_type
ORDER BY analysis_date DESC, avg_confidence DESC;

-- Current tier distribution
CREATE OR REPLACE VIEW tier_distribution AS
SELECT
    current_tier,
    COUNT(*) as stock_count,
    AVG(price) as avg_price,
    AVG(daily_volume) as avg_volume
FROM stock_classifications
GROUP BY current_tier
ORDER BY
    CASE current_tier
        WHEN 'PICKS' THEN 5
        WHEN 'SHORT_LIST' THEN 4
        WHEN 'QUALIFIED' THEN 3
        WHEN 'ACTIVE' THEN 2
        WHEN 'ALL' THEN 1
    END DESC;

-- Recent arbitration decisions
CREATE OR REPLACE VIEW recent_arbitration_decisions AS
SELECT
    fa.symbol,
    fa.analysis_date,
    fa.final_recommendation,
    fa.arbitration_confidence,
    fa.selected_target_medium,
    fa.estimated_days_to_target,
    sc.current_tier,
    sc.price as current_price
FROM final_arbitration fa
LEFT JOIN stock_classifications sc ON fa.symbol = sc.symbol
WHERE fa.analysis_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY fa.analysis_date DESC, fa.arbitration_confidence DESC;
