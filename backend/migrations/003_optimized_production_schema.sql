-- BullsBears Optimized Production Schema (v3.3 - November 10, 2025)
-- Designed for 90-day data + 4-tier classification + agent pipeline

-- =====================================================================
-- CORE DATA TABLES
-- =====================================================================

-- Prime 90-day OHLCV storage (main data source)
CREATE TABLE IF NOT EXISTS prime_ohlc_90d (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(12,4) NOT NULL,
    high_price DECIMAL(12,4) NOT NULL,
    low_price DECIMAL(12,4) NOT NULL,
    close_price DECIMAL(12,4) NOT NULL,
    volume BIGINT NOT NULL,
    adj_close DECIMAL(12,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(symbol, date)
);

-- Stock classifications for 4-tier system
CREATE TABLE IF NOT EXISTS stock_classifications (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    current_tier VARCHAR(20) NOT NULL DEFAULT 'ALL', -- ALL, ACTIVE, SHORT_LIST, PICKS
    
    -- Tier qualification metrics
    price DECIMAL(10,2),
    market_cap BIGINT,
    daily_volume BIGINT,
    volatility_score DECIMAL(8,4),
    
    -- Tier management
    last_qualified_date DATE,
    qualified_days_count INTEGER DEFAULT 0,
    selection_fatigue_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chart storage for vision agents
CREATE TABLE IF NOT EXISTS stock_charts (
    symbol VARCHAR(10) PRIMARY KEY,
    chart_data TEXT NOT NULL, -- base64 encoded PNG
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chart_type VARCHAR(20) DEFAULT 'ohlcv_90d'
);

-- =====================================================================
-- AGENT PIPELINE TABLES
-- =====================================================================

-- Pick candidates (all 75 SHORT_LIST candidates tracked)
CREATE TABLE IF NOT EXISTS pick_candidates (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    analysis_date DATE NOT NULL,
    
    -- Agent outputs
    prescreen_score DECIMAL(8,4),
    vision_flags JSONB, -- 6 boolean flags from vision agent
    social_score INTEGER, -- -5 to +5 from social agent
    arbitrator_confidence DECIMAL(8,4),
    
    -- Targets and predictions
    direction VARCHAR(10), -- 'bullish' or 'bearish'
    target_low DECIMAL(10,2),
    target_high DECIMAL(10,2),
    support_level DECIMAL(10,2),
    timeframe_days INTEGER,
    
    -- Market context
    current_price DECIMAL(10,2) NOT NULL,
    market_conditions JSONB,
    
    -- Final selection
    selected_as_pick BOOLEAN DEFAULT FALSE,
    arbitrator_reasoning TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(symbol, analysis_date)
);

-- 30-day price tracking for learning system
CREATE TABLE IF NOT EXISTS candidate_price_tracking (
    id SERIAL PRIMARY KEY,
    candidate_id INTEGER REFERENCES pick_candidates(id),
    symbol VARCHAR(10) NOT NULL,
    tracking_date DATE NOT NULL,
    
    -- Price data
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    volume BIGINT,
    
    -- Performance metrics
    price_change_pct DECIMAL(8,4),
    max_gain_pct DECIMAL(8,4),
    max_loss_pct DECIMAL(8,4),
    target_hit_low BOOLEAN DEFAULT FALSE,
    target_hit_high BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(candidate_id, tracking_date)
);

-- Learning system weights and patterns
CREATE TABLE IF NOT EXISTS learning_weights (
    id SERIAL PRIMARY KEY,
    weight_type VARCHAR(50) NOT NULL, -- 'vision_flags', 'social_thresholds', 'arbitrator_bias'
    weight_data JSONB NOT NULL,
    performance_score DECIMAL(8,4),
    
    -- Metadata
    generated_by VARCHAR(50), -- 'brain_agent', 'learner_agent'
    effective_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- PERFORMANCE INDEXES
-- =====================================================================

-- Prime data indexes
CREATE INDEX IF NOT EXISTS idx_prime_symbol_date ON prime_ohlc_90d(symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_prime_date ON prime_ohlc_90d(date DESC);
CREATE INDEX IF NOT EXISTS idx_prime_symbol ON prime_ohlc_90d(symbol);

-- Classification indexes
CREATE INDEX IF NOT EXISTS idx_classifications_tier ON stock_classifications(current_tier);
CREATE INDEX IF NOT EXISTS idx_classifications_updated ON stock_classifications(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_classifications_qualified ON stock_classifications(last_qualified_date DESC);

-- Candidate tracking indexes
CREATE INDEX IF NOT EXISTS idx_candidates_date ON pick_candidates(analysis_date DESC);
CREATE INDEX IF NOT EXISTS idx_candidates_symbol ON pick_candidates(symbol);
CREATE INDEX IF NOT EXISTS idx_candidates_selected ON pick_candidates(selected_as_pick, analysis_date DESC);

-- Price tracking indexes
CREATE INDEX IF NOT EXISTS idx_tracking_symbol_date ON candidate_price_tracking(symbol, tracking_date DESC);
CREATE INDEX IF NOT EXISTS idx_tracking_candidate ON candidate_price_tracking(candidate_id);

-- Learning weights indexes
CREATE INDEX IF NOT EXISTS idx_weights_type_date ON learning_weights(weight_type, effective_date DESC);

-- =====================================================================
-- UTILITY FUNCTIONS
-- =====================================================================

-- Function to get tier counts
CREATE OR REPLACE FUNCTION get_tier_counts()
RETURNS TABLE(tier VARCHAR(20), count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT current_tier, COUNT(*)
    FROM stock_classifications
    GROUP BY current_tier
    ORDER BY 
        CASE current_tier
            WHEN 'PICKS' THEN 1
            WHEN 'SHORT_LIST' THEN 2
            WHEN 'ACTIVE' THEN 3
            WHEN 'ALL' THEN 4
            ELSE 5
        END;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old data (keep 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    cutoff_date DATE := CURRENT_DATE - INTERVAL '90 days';
BEGIN
    -- Clean old OHLC data
    DELETE FROM prime_ohlc_90d WHERE date < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Clean old candidate tracking
    DELETE FROM candidate_price_tracking WHERE tracking_date < cutoff_date;
    
    -- Clean old learning weights (keep last 30 days)
    DELETE FROM learning_weights WHERE created_at < CURRENT_DATE - INTERVAL '30 days';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- INITIAL DATA SETUP
-- =====================================================================

-- Create default learning weights
INSERT INTO learning_weights (weight_type, weight_data, performance_score, generated_by, effective_date)
VALUES 
    ('vision_flags', '{"wyckoff_phase_2": 1.2, "weekly_triangle_coil": 1.1, "volume_shelf_breakout": 1.3, "p_shape_profile": 1.0, "fakeout_wick_rejection": 0.9, "spring_setup": 1.4}', 0.0, 'initial_setup', CURRENT_DATE),
    ('social_thresholds', '{"bullish_min": 3, "bearish_max": -3, "neutral_range": [-2, 2]}', 0.0, 'initial_setup', CURRENT_DATE),
    ('arbitrator_bias', '{"confidence_threshold": 0.48, "risk_adjustment": 0.85, "target_scaling": 1.0}', 0.0, 'initial_setup', CURRENT_DATE)
ON CONFLICT DO NOTHING;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bullsbears_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bullsbears_user;

COMMIT;
