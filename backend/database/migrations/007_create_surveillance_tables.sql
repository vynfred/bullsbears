-- NASDAQ Surveillance System Database Schema
-- Comprehensive market intelligence tables for 6,960+ NASDAQ stocks

-- 1. NASDAQ Symbols Master Table
CREATE TABLE IF NOT EXISTS nasdaq_symbols (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    name TEXT NOT NULL,
    market_cap BIGINT,
    country VARCHAR(50),
    ipo_year INTEGER,
    sector VARCHAR(100),
    industry VARCHAR(200),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast symbol lookups
CREATE INDEX IF NOT EXISTS idx_nasdaq_symbols_symbol ON nasdaq_symbols(symbol);
CREATE INDEX IF NOT EXISTS idx_nasdaq_symbols_sector ON nasdaq_symbols(sector);
CREATE INDEX IF NOT EXISTS idx_nasdaq_symbols_market_cap ON nasdaq_symbols(market_cap DESC);

-- 2. Stock Surveillance Records (Main surveillance data)
CREATE TABLE IF NOT EXISTS stock_surveillance (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    scan_date TIMESTAMP WITH TIME ZONE NOT NULL,
    week_number INTEGER NOT NULL,
    
    -- Current market data
    current_price DECIMAL(12,4),
    volume BIGINT,
    market_cap BIGINT,
    avg_volume BIGINT,
    
    -- Technical indicators
    rsi DECIMAL(5,2),
    volume_ratio DECIMAL(8,4), -- Current volume vs average
    price_vs_resistance DECIMAL(8,4), -- Price vs resistance level
    day_high DECIMAL(12,4),
    day_low DECIMAL(12,4),
    fifty_day_ma DECIMAL(12,4),
    two_hundred_day_ma DECIMAL(12,4),
    
    -- Fundamental data
    pe_ratio DECIMAL(8,2),
    debt_to_equity DECIMAL(8,4),
    revenue_growth DECIMAL(8,4),
    profit_margin DECIMAL(8,4),
    roe DECIMAL(8,4), -- Return on Equity
    
    -- Institutional & insider data
    institutional_ownership DECIMAL(5,2), -- Percentage
    institutional_flow_change DECIMAL(8,4), -- Change from previous scan
    insider_buy_count INTEGER DEFAULT 0,
    insider_sell_count INTEGER DEFAULT 0,
    insider_net_value BIGINT DEFAULT 0, -- Net insider transaction value
    
    -- Sentiment & news
    sentiment_score DECIMAL(4,3), -- 0.0 to 1.0
    news_count INTEGER DEFAULT 0,
    analyst_rating VARCHAR(20), -- Strong Buy, Buy, Hold, Sell, Strong Sell
    analyst_target_price DECIMAL(12,4),
    
    -- Change detection flags (JSON array)
    change_flags JSONB DEFAULT '[]',
    significance_score DECIMAL(4,3) DEFAULT 0.0, -- ML-powered score 0-1
    
    -- Data quality
    data_completeness DECIMAL(4,3) DEFAULT 0.0, -- Percentage of data collected
    api_calls_used INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (symbol) REFERENCES nasdaq_symbols(symbol)
);

-- Indexes for surveillance queries
CREATE INDEX IF NOT EXISTS idx_surveillance_symbol_date ON stock_surveillance(symbol, scan_date DESC);
CREATE INDEX IF NOT EXISTS idx_surveillance_week ON stock_surveillance(week_number, scan_date DESC);
CREATE INDEX IF NOT EXISTS idx_surveillance_significance ON stock_surveillance(significance_score DESC);
CREATE INDEX IF NOT EXISTS idx_surveillance_change_flags ON stock_surveillance USING GIN(change_flags);

-- 3. Institutional Holdings Tracking
CREATE TABLE IF NOT EXISTS institutional_holdings (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    scan_date TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Institutional holder details
    holder_name TEXT NOT NULL,
    shares_held BIGINT,
    percentage_held DECIMAL(5,2),
    value_held BIGINT, -- Dollar value
    change_in_shares BIGINT, -- Change from previous quarter
    change_percentage DECIMAL(8,4),
    
    -- Metadata
    filing_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (symbol) REFERENCES nasdaq_symbols(symbol)
);

-- Index for institutional tracking
CREATE INDEX IF NOT EXISTS idx_institutional_symbol_date ON institutional_holdings(symbol, scan_date DESC);
CREATE INDEX IF NOT EXISTS idx_institutional_holder ON institutional_holdings(holder_name);

-- 4. Insider Trading Tracking
CREATE TABLE IF NOT EXISTS insider_trading (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    scan_date TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Insider details
    insider_name TEXT NOT NULL,
    insider_title TEXT,
    transaction_type VARCHAR(20), -- P-Purchase, S-Sale, etc.
    transaction_date DATE,
    filing_date DATE,
    
    -- Transaction details
    shares_traded BIGINT,
    price_per_share DECIMAL(12,4),
    total_value BIGINT,
    shares_owned_after BIGINT,
    
    -- Analysis flags
    is_significant BOOLEAN DEFAULT false, -- Large transaction
    is_clustered BOOLEAN DEFAULT false, -- Multiple insiders trading
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (symbol) REFERENCES nasdaq_symbols(symbol)
);

-- Index for insider tracking
CREATE INDEX IF NOT EXISTS idx_insider_symbol_date ON insider_trading(symbol, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_insider_type ON insider_trading(transaction_type);
CREATE INDEX IF NOT EXISTS idx_insider_significant ON insider_trading(is_significant, transaction_date DESC);

-- 5. Surveillance Alerts (Breakout/Breakdown alerts)
CREATE TABLE IF NOT EXISTS surveillance_alerts (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- breakout, breakdown, insider_accumulation, etc.
    confidence DECIMAL(4,3) NOT NULL, -- 0.0 to 1.0
    
    -- Alert details
    trigger_factors JSONB, -- Array of factors that triggered alert
    current_price DECIMAL(12,4),
    target_estimate DECIMAL(12,4),
    message TEXT,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'active', -- active, resolved, false_positive
    resolution_date TIMESTAMP WITH TIME ZONE,
    outcome TEXT, -- What happened after the alert
    
    -- Performance tracking
    max_price_reached DECIMAL(12,4),
    min_price_reached DECIMAL(12,4),
    days_to_resolution INTEGER,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (symbol) REFERENCES nasdaq_symbols(symbol)
);

-- Index for alerts
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON surveillance_alerts(symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON surveillance_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_confidence ON surveillance_alerts(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON surveillance_alerts(status, created_at DESC);

-- 6. Weekly Surveillance Batches (Track which stocks processed each week)
CREATE TABLE IF NOT EXISTS surveillance_batches (
    id SERIAL PRIMARY KEY,
    week_number INTEGER NOT NULL,
    batch_date DATE NOT NULL,
    
    -- Batch details
    total_symbols INTEGER,
    processed_symbols INTEGER,
    failed_symbols INTEGER,
    priority_symbols INTEGER, -- High significance stocks
    
    -- API usage tracking
    total_api_calls INTEGER,
    api_calls_per_symbol DECIMAL(6,2),
    processing_time_minutes INTEGER,
    
    -- Results summary
    alerts_generated INTEGER,
    new_flagged_stocks INTEGER,
    
    -- Status
    status VARCHAR(20) DEFAULT 'in_progress', -- in_progress, completed, failed
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Index for batch tracking
CREATE INDEX IF NOT EXISTS idx_batches_week ON surveillance_batches(week_number);
CREATE INDEX IF NOT EXISTS idx_batches_date ON surveillance_batches(batch_date DESC);

-- 7. Surveillance Performance Metrics
CREATE TABLE IF NOT EXISTS surveillance_performance (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    
    -- Alert performance
    total_alerts INTEGER DEFAULT 0,
    successful_alerts INTEGER DEFAULT 0, -- Alerts that led to significant moves
    false_positive_alerts INTEGER DEFAULT 0,
    alert_success_rate DECIMAL(5,2) DEFAULT 0.0,
    
    -- Detection performance
    breakouts_detected INTEGER DEFAULT 0,
    breakouts_missed INTEGER DEFAULT 0, -- Manual review
    detection_accuracy DECIMAL(5,2) DEFAULT 0.0,
    
    -- System performance
    avg_processing_time_per_stock DECIMAL(8,2), -- Seconds
    api_efficiency DECIMAL(6,2), -- Calls per successful data point
    data_completeness_avg DECIMAL(5,2), -- Average data completeness
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for performance tracking
CREATE INDEX IF NOT EXISTS idx_performance_date ON surveillance_performance(metric_date DESC);

-- 8. Economic Events Impact Tracking
CREATE TABLE IF NOT EXISTS economic_impact_tracking (
    id SERIAL PRIMARY KEY,
    event_date DATE NOT NULL,
    event_type VARCHAR(100) NOT NULL, -- CPI, Fed Rate, Earnings, etc.
    event_description TEXT,
    
    -- Market impact
    market_reaction VARCHAR(20), -- positive, negative, neutral
    affected_sectors JSONB, -- Array of sectors most affected
    
    -- Surveillance system response
    alerts_triggered INTEGER DEFAULT 0,
    new_patterns_detected INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for economic tracking
CREATE INDEX IF NOT EXISTS idx_economic_date ON economic_impact_tracking(event_date DESC);
CREATE INDEX IF NOT EXISTS idx_economic_type ON economic_impact_tracking(event_type);

-- Create views for common queries
CREATE OR REPLACE VIEW current_surveillance_summary AS
SELECT 
    s.symbol,
    s.current_price,
    s.volume_ratio,
    s.significance_score,
    s.change_flags,
    s.scan_date,
    ns.name,
    ns.sector,
    ns.market_cap
FROM stock_surveillance s
JOIN nasdaq_symbols ns ON s.symbol = ns.symbol
WHERE s.scan_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY s.significance_score DESC;

CREATE OR REPLACE VIEW high_priority_stocks AS
SELECT 
    symbol,
    significance_score,
    change_flags,
    current_price,
    volume_ratio,
    scan_date
FROM stock_surveillance
WHERE significance_score > 0.5
    AND scan_date >= CURRENT_DATE - INTERVAL '3 days'
ORDER BY significance_score DESC;

CREATE OR REPLACE VIEW insider_accumulation_alerts AS
SELECT 
    it.symbol,
    COUNT(*) as transaction_count,
    SUM(CASE WHEN it.transaction_type = 'P-Purchase' THEN it.total_value ELSE 0 END) as total_purchases,
    SUM(CASE WHEN it.transaction_type = 'S-Sale' THEN it.total_value ELSE 0 END) as total_sales,
    MAX(it.transaction_date) as latest_transaction
FROM insider_trading it
WHERE it.transaction_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY it.symbol
HAVING COUNT(CASE WHEN it.transaction_type = 'P-Purchase' THEN 1 END) >= 2
ORDER BY total_purchases DESC;

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO surveillance_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO surveillance_user;
