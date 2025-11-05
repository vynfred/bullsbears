-- Migration: Add watchlist monitoring events
-- Description: Add WatchlistEvent table and WatchlistEventType enum for stock monitoring alerts
-- Date: 2025-11-04

-- Create enum type for watchlist event types
CREATE TYPE watchlist_event_type AS ENUM (
    'insider_activity',
    'institutional_change', 
    'macro_catalyst'
);

-- Create watchlist_events table
CREATE TABLE watchlist_events (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    event_type watchlist_event_type NOT NULL,
    event_title VARCHAR(255) NOT NULL,
    event_description TEXT,
    
    -- Monitoring window tracking
    day_offset INTEGER NOT NULL CHECK (day_offset >= 0 AND day_offset <= 6),
    pick_date TIMESTAMP NOT NULL,
    pick_type VARCHAR(20) NOT NULL, -- 'bullish' or 'bearish'
    pick_confidence FLOAT NOT NULL,
    
    -- Score tracking
    baseline_score FLOAT NOT NULL,
    current_score FLOAT NOT NULL,
    score_delta FLOAT NOT NULL,
    
    -- Notification tracking
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_sent_at TIMESTAMP NULL,
    notification_message TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_watchlist_events_user_id (user_id),
    INDEX idx_watchlist_events_symbol (symbol),
    INDEX idx_watchlist_events_event_type (event_type),
    INDEX idx_watchlist_events_day_offset (day_offset),
    INDEX idx_watchlist_events_pick_date (pick_date),
    INDEX idx_watchlist_events_notification_sent (notification_sent),
    INDEX idx_watchlist_events_created_at (created_at),
    
    -- Composite indexes for common queries
    INDEX idx_watchlist_events_user_symbol (user_id, symbol),
    INDEX idx_watchlist_events_user_day_offset (user_id, day_offset),
    INDEX idx_watchlist_events_symbol_day_offset (symbol, day_offset),
    INDEX idx_watchlist_events_pending_notifications (notification_sent, created_at)
);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_watchlist_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_watchlist_events_updated_at
    BEFORE UPDATE ON watchlist_events
    FOR EACH ROW
    EXECUTE FUNCTION update_watchlist_events_updated_at();

-- Add comments for documentation
COMMENT ON TABLE watchlist_events IS 'Stores monitoring events for watchlist stocks during 7-day window after AI picks';
COMMENT ON COLUMN watchlist_events.day_offset IS 'Days since pick (0-6) for 7-day monitoring window';
COMMENT ON COLUMN watchlist_events.score_delta IS 'Change in bullish indication score (%) that triggered the alert';
COMMENT ON COLUMN watchlist_events.baseline_score IS 'Original AI confidence score at pick time';
COMMENT ON COLUMN watchlist_events.current_score IS 'Current AI confidence score when event detected';
COMMENT ON COLUMN watchlist_events.event_type IS 'Type of monitoring event: insider_activity, institutional_change, or macro_catalyst';
COMMENT ON COLUMN watchlist_events.notification_message IS 'Formatted message for push notifications';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON watchlist_events TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE watchlist_events_id_seq TO your_app_user;
