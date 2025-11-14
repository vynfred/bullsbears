-- BullsBears Agent System Database Schema
-- Run this script to set up the required tables for the agent system

-- === EXISTING TABLES (UNCHANGED) ===
CREATE TABLE IF NOT EXISTS picks (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('bullish', 'bearish')),
    confidence DECIMAL(5,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    social_weight DECIMAL(3,2) DEFAULT 1.0,
    reasoning TEXT,
    target_low DECIMAL(10,2),
    target_high DECIMAL(10,2),
    scan_tier VARCHAR(20) DEFAULT 'daily' CHECK (scan_tier IN ('daily', 'weekly', 'monthly')),
    outcome VARCHAR(20) DEFAULT 'pending' CHECK (outcome IN ('pending', 'win', 'partial', 'loss')),
    outcome_price DECIMAL(10,2),
    outcome_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '3 days'),
    agent_version VARCHAR(20) DEFAULT '1.0'
);

CREATE TABLE IF NOT EXISTS scan_errors (
    id SERIAL PRIMARY KEY,
    error_type VARCHAR(50) NOT NULL,
    error_message TEXT NOT NULL,
    ticker VARCHAR(10),
    agent_name VARCHAR(50),
    stack_trace TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_performance (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL UNIQUE,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    accuracy DECIMAL(5,2) DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_conditions (
    id SERIAL PRIMARY KEY,
    spy_premarket_change DECIMAL(5,2) DEFAULT 0.0,
    vix_current DECIMAL(5,2) DEFAULT 20.0,
    market_open BOOLEAN DEFAULT true,
    kill_switch_active BOOLEAN DEFAULT false,
    kill_switch_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS social_sentiment (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    sentiment_score DECIMAL(5,2) NOT NULL CHECK (sentiment_score >= 0 AND sentiment_score <= 100),
    mention_count INTEGER DEFAULT 0,
    source VARCHAR(20) NOT NULL,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_cycles (
    id SERIAL PRIMARY KEY,
    cycle_date TIMESTAMP NOT NULL,
    duration_seconds FLOAT NOT NULL,
    insights_count INTEGER NOT NULL,
    updates_applied INTEGER NOT NULL,
    top_factors JSONB,
    cycle_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_updates (
    id SERIAL PRIMARY KEY,
    update_date TIMESTAMP NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    expected_improvement FLOAT NOT NULL,
    reasoning TEXT,
    old_prompt_hash BIGINT,
    new_prompt_hash BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trending_stocks (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    trend_score DECIMAL(5,2) NOT NULL,
    mention_velocity DECIMAL(10,2) NOT NULL,
    sentiment_shift DECIMAL(5,2) NOT NULL,
    social_volume INTEGER NOT NULL,
    key_catalysts JSONB,
    confidence DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- === NEW TABLES FOR LEARNER (DB-BASED) ===
CREATE TABLE IF NOT EXISTS model_weights (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    value FLOAT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_examples (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- === KILL SWITCH LOG (FOR kill_switch_service.py) ===
CREATE TABLE IF NOT EXISTS kill_switch_log (
    id SERIAL PRIMARY KEY,
    vix_level DECIMAL(5,2),
    spy_change_percent DECIMAL(5,3),
    activated_at TIMESTAMP DEFAULT NOW(),
    reason TEXT
);

-- === SEED INITIAL WEIGHTS ===
INSERT INTO model_weights (name, value) VALUES
('prescreen_score', 0.35),
('vision_flags', 0.25),
('social_score', 0.20),
('polymarket_edge', 0.15),
('lightgbm_prob', 0.05)
ON CONFLICT (name) DO NOTHING;

-- === INDEXES ===
CREATE INDEX IF NOT EXISTS idx_picks_ticker ON picks(ticker);
CREATE INDEX IF NOT EXISTS idx_picks_created_at ON picks(created_at);
CREATE INDEX IF NOT EXISTS idx_picks_outcome ON picks(outcome);
CREATE INDEX IF NOT EXISTS idx_picks_direction ON picks(direction);
CREATE INDEX IF NOT EXISTS idx_scan_errors_created_at ON scan_errors(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_performance_agent_name ON agent_performance(agent_name);
CREATE INDEX IF NOT EXISTS idx_market_conditions_created_at ON market_conditions(created_at);
CREATE INDEX IF NOT EXISTS idx_social_sentiment_ticker ON social_sentiment(ticker);
CREATE INDEX IF NOT EXISTS idx_social_sentiment_created_at ON social_sentiment(created_at);
CREATE INDEX IF NOT EXISTS idx_learning_cycles_date ON learning_cycles(cycle_date);
CREATE INDEX IF NOT EXISTS idx_prompt_updates_date ON prompt_updates(update_date);
CREATE INDEX IF NOT EXISTS idx_prompt_updates_agent ON prompt_updates(agent_type);
CREATE INDEX IF NOT EXISTS idx_trending_stocks_ticker ON trending_stocks(ticker);
CREATE INDEX IF NOT EXISTS idx_trending_stocks_created_at ON trending_stocks(created_at);
CREATE INDEX IF NOT EXISTS idx_trending_stocks_trend_score ON trending_stocks(trend_score);

-- === INITIAL DATA ===
INSERT INTO agent_performance (agent_name, accuracy) VALUES
    ('BullPredictorTechnical', 0.0),
    ('BullPredictorFundamental', 0.0),
    ('BearPredictorTechnical', 0.0),
    ('BearPredictorSentiment', 0.0),
    ('VisionAgent', 0.0),
    ('ArbitratorAgent', 0.0),
    ('LearnerAgent', 0.0),
ON CONFLICT (agent_name) DO NOTHING;

INSERT INTO market_conditions (spy_premarket_change, vix_current, market_open) VALUES 
    (0.0, 20.0, true)
ON CONFLICT DO NOTHING;

COMMIT;