# backend/app/services/db_migration.py
"""
Centralized, versioned, idempotent database migrations
Run once at deploy time or via /admin/init-db (protected)
"""

import logging
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

async def run_all_migrations() -> dict:
    """
    Apply all migrations in order.
    Fully idempotent – safe to run every deploy.
    """
    db = await get_asyncpg_pool()
    async with db.acquire() as conn:
        async with conn.transaction():
            # === v1: Core pipeline tables (Nov 2024) ===
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_classifications (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL UNIQUE,
                    exchange VARCHAR(10) DEFAULT 'NASDAQ',
                    current_tier VARCHAR(20) NOT NULL,
                    last_price DECIMAL(10, 2),
                    avg_volume_20d BIGINT,
                    market_cap BIGINT,
                    company_name VARCHAR(255),
                    sector VARCHAR(100),
                    industry VARCHAR(100),
                    last_qualified_date DATE,
                    qualified_days_count INTEGER DEFAULT 0,
                    selection_fatigue_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_classifications_tier ON stock_classifications(current_tier);
                CREATE INDEX IF NOT EXISTS idx_classifications_symbol ON stock_classifications(symbol);
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS prime_ohlc_90d (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    open_price DECIMAL(10, 2),
                    high_price DECIMAL(10, 2),
                    low_price DECIMAL(10, 2),
                    close_price DECIMAL(10, 2),
                    volume BIGINT,
                    adj_close DECIMAL(10, 2),
                    vwap DECIMAL(10, 2),
                    UNIQUE(symbol, date)
                );
                
                CREATE INDEX IF NOT EXISTS idx_ohlc_symbol ON prime_ohlc_90d(symbol);
                CREATE INDEX IF NOT EXISTS idx_ohlc_date ON prime_ohlc_90d(date);
            """)

            # === v2: Picks + Shortlist (Dec 2024) ===
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS picks (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    direction VARCHAR(10) NOT NULL CHECK (direction IN ('bullish', 'bearish')),
                    confidence DECIMAL(5, 4) NOT NULL,
                    reasoning TEXT,
                    target_primary DECIMAL(10, 2),
                    target_medium DECIMAL(10, 2),
                    target_moonshot DECIMAL(10, 2),
                    confluence_score INTEGER DEFAULT 0,
                    confluence_methods TEXT[] DEFAULT '{}',
                    rsi_divergence BOOLEAN DEFAULT FALSE,
                    gann_alignment BOOLEAN DEFAULT FALSE,
                    weekly_pivots JSONB,
                    -- Catalyst flags
                    has_earnings_catalyst BOOLEAN DEFAULT FALSE,
                    has_news_catalyst BOOLEAN DEFAULT FALSE,
                    short_interest_pct DECIMAL(5, 2),
                    -- Extended catalyst tracking (v5.1)
                    has_insider_catalyst BOOLEAN DEFAULT FALSE,
                    insider_data JSONB,  -- {net_shares, net_value, buy_count, sell_count, last_filing_date}
                    has_economic_catalyst BOOLEAN DEFAULT FALSE,
                    economic_events JSONB,  -- [{event, date, impact}] from FRED
                    has_political_catalyst BOOLEAN DEFAULT FALSE,
                    political_trades JSONB,  -- Congress/Senate trades from QuiverQuant or similar
                    catalyst_summary TEXT,  -- AI-generated summary of all catalysts
                    -- Context
                    pick_context JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '30 days')
                );

                CREATE INDEX IF NOT EXISTS idx_picks_symbol ON picks(symbol);
                CREATE INDEX IF NOT EXISTS idx_picks_direction ON picks(direction);
                CREATE INDEX IF NOT EXISTS idx_picks_created ON picks(created_at);
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS shortlist_candidates (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    rank INTEGER,
                    direction VARCHAR(10),
                    price_at_selection DECIMAL(10, 2),
                    prescreen_score DECIMAL(5, 2),
                    prescreen_reasoning TEXT,
                    technical_snapshot JSONB,
                    fundamental_snapshot JSONB,
                    vision_flags JSONB,
                    social_score DECIMAL(5, 2),
                    social_data JSONB,
                    polymarket_prob DECIMAL(5, 4),
                    -- Catalyst data (collected during pipeline, v5.1)
                    insider_data JSONB,  -- FMP insider trading
                    economic_events JSONB,  -- FRED events
                    political_trades JSONB,  -- Congress trades
                    short_interest_pct DECIMAL(5, 2),
                    -- Pick tracking
                    was_picked BOOLEAN DEFAULT FALSE,
                    picked_direction VARCHAR(10),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(date, symbol)
                );

                CREATE INDEX IF NOT EXISTS idx_shortlist_date ON shortlist_candidates(date);
                CREATE INDEX IF NOT EXISTS idx_shortlist_symbol ON shortlist_candidates(symbol);
                CREATE INDEX IF NOT EXISTS idx_shortlist_picked ON shortlist_candidates(was_picked);
            """)

            # === v3: Outcome tracking (Jan 2025) ===
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pick_outcomes_detailed (
                    id SERIAL PRIMARY KEY,
                    pick_id INTEGER UNIQUE REFERENCES picks(id) ON DELETE CASCADE,
                    symbol VARCHAR(10) NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    price_when_picked DECIMAL(10, 2),
                    target_primary DECIMAL(10, 2),
                    target_medium DECIMAL(10, 2),
                    target_moonshot DECIMAL(10, 2),
                    hit_primary_target BOOLEAN DEFAULT FALSE,
                    hit_medium_target BOOLEAN DEFAULT FALSE,
                    hit_moonshot_target BOOLEAN DEFAULT FALSE,
                    price_at_hit DECIMAL(10, 2),
                    hit_at TIMESTAMP,
                    outcome VARCHAR(20) DEFAULT 'active',
                    max_gain_pct DECIMAL(6, 2),
                    days_to_peak INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    resolved_at TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_outcomes_symbol ON pick_outcomes_detailed(symbol);
                CREATE INDEX IF NOT EXISTS idx_outcomes_outcome ON pick_outcomes_detailed(outcome);
            """)

            # === v4: Activity log (Feb 2025) ===
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_activity (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    step VARCHAR(50) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    details JSONB,
                    tier_counts JSONB,
                    duration_seconds DECIMAL(10, 2),
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON pipeline_activity(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_activity_step ON pipeline_activity(step);
            """)

            # === v5: Extended catalyst tracking (Dec 2024) ===
            # Add new columns to existing tables (idempotent - IF NOT EXISTS not available, use DO block)
            await conn.execute("""
                DO $$ BEGIN
                    -- picks table catalyst columns
                    ALTER TABLE picks ADD COLUMN IF NOT EXISTS has_insider_catalyst BOOLEAN DEFAULT FALSE;
                    ALTER TABLE picks ADD COLUMN IF NOT EXISTS insider_data JSONB;
                    ALTER TABLE picks ADD COLUMN IF NOT EXISTS has_economic_catalyst BOOLEAN DEFAULT FALSE;
                    ALTER TABLE picks ADD COLUMN IF NOT EXISTS economic_events JSONB;
                    ALTER TABLE picks ADD COLUMN IF NOT EXISTS has_political_catalyst BOOLEAN DEFAULT FALSE;
                    ALTER TABLE picks ADD COLUMN IF NOT EXISTS political_trades JSONB;
                    ALTER TABLE picks ADD COLUMN IF NOT EXISTS catalyst_summary TEXT;

                    -- shortlist_candidates catalyst columns
                    ALTER TABLE shortlist_candidates ADD COLUMN IF NOT EXISTS insider_data JSONB;
                    ALTER TABLE shortlist_candidates ADD COLUMN IF NOT EXISTS economic_events JSONB;
                    ALTER TABLE shortlist_candidates ADD COLUMN IF NOT EXISTS political_trades JSONB;
                    ALTER TABLE shortlist_candidates ADD COLUMN IF NOT EXISTS short_interest_pct DECIMAL(5, 2);
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$;
            """)

    logger.info("All database migrations completed successfully")
    return {"success": True, "migrations_applied": 5}


async def reset_all_pipeline_tables() -> dict:
    """
    DANGER: Drops and recreates ONLY pipeline tables.
    Used for clean slate in staging or after schema bugs.
    """
    db = await get_asyncpg_pool()
    async with db.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DROP TABLE IF EXISTS pick_outcomes_detailed CASCADE")
            await conn.execute("DROP TABLE IF EXISTS picks CASCADE")
            await conn.execute("DROP TABLE IF EXISTS shortlist_candidates CASCADE")
            await conn.execute("DROP TABLE IF EXISTS pipeline_activity CASCADE")
            
        await run_all_migrations()  # recreate fresh
        
    logger.warning("Pipeline tables RESET and re-migrated")
    return {"success": True, "message": "Pipeline tables wiped and recreated"}