-- Migration: Add watchlist monitoring events (SQLite version)
-- Description: Add WatchlistEvent table for stock monitoring alerts
-- Date: 2025-11-04

-- Create watchlist_events table (SQLite doesn't support enums, use CHECK constraints)
CREATE TABLE watchlist_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Core identifiers
    watchlist_entry_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    user_id TEXT NOT NULL,

    -- Event details
    event_type TEXT NOT NULL CHECK (event_type IN ('insider_activity', 'institutional_change', 'macro_catalyst')),
    day_offset INTEGER NOT NULL CHECK (day_offset >= 0 AND day_offset <= 6),

    -- Impact scoring
    score_delta REAL NOT NULL,
    baseline_score REAL NOT NULL,
    current_score REAL NOT NULL,

    -- Event metadata
    event_title TEXT NOT NULL,
    event_description TEXT,
    event_data TEXT,  -- JSON stored as TEXT in SQLite

    -- Notification tracking
    notification_sent BOOLEAN DEFAULT 0,
    notification_sent_at TIMESTAMP NULL,
    push_notification_id TEXT,

    -- Pick reference data
    pick_date TIMESTAMP NOT NULL,
    pick_type TEXT NOT NULL CHECK (pick_type IN ('bullish', 'bearish')),
    pick_confidence REAL NOT NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_watchlist_events_user_id ON watchlist_events(user_id);
CREATE INDEX idx_watchlist_events_symbol ON watchlist_events(symbol);
CREATE INDEX idx_watchlist_events_event_type ON watchlist_events(event_type);
CREATE INDEX idx_watchlist_events_day_offset ON watchlist_events(day_offset);
CREATE INDEX idx_watchlist_events_pick_date ON watchlist_events(pick_date);
CREATE INDEX idx_watchlist_events_notification_sent ON watchlist_events(notification_sent);
CREATE INDEX idx_watchlist_events_created_at ON watchlist_events(created_at);

-- Composite indexes for common queries
CREATE INDEX idx_watchlist_events_user_symbol ON watchlist_events(user_id, symbol);
CREATE INDEX idx_watchlist_events_user_day_offset ON watchlist_events(user_id, day_offset);
CREATE INDEX idx_watchlist_events_symbol_day_offset ON watchlist_events(symbol, day_offset);
CREATE INDEX idx_watchlist_events_pending_notifications ON watchlist_events(notification_sent, created_at);

-- Create trigger to update updated_at timestamp (SQLite version)
CREATE TRIGGER trigger_update_watchlist_events_updated_at
    AFTER UPDATE ON watchlist_events
    FOR EACH ROW
    BEGIN
        UPDATE watchlist_events 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = NEW.id;
    END;
