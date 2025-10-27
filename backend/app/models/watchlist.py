"""
Watchlist and performance tracking models.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

from ..core.database import Base


class WatchlistEntry(Base):
    """Track user's watchlist entries for performance analysis."""
    
    __tablename__ = "watchlist_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic trade information
    symbol = Column(String(10), nullable=False, index=True)
    company_name = Column(String(200))
    entry_type = Column(String(20), nullable=False)  # 'STOCK', 'OPTION_CALL', 'OPTION_PUT'
    
    # Entry details
    entry_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    stop_loss_price = Column(Float)
    entry_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Options-specific fields (null for stocks)
    strike_price = Column(Float)
    expiration_date = Column(DateTime(timezone=True))
    option_contract_symbol = Column(String(50))
    
    # AI recommendation data
    ai_confidence_score = Column(Float, nullable=False)  # 0-100
    ai_recommendation = Column(String(20))  # BUY, SELL, HOLD, STRONG_BUY, STRONG_SELL
    ai_reasoning = Column(Text)
    ai_key_factors = Column(JSON)  # List of key factors from AI analysis
    
    # Performance tracking
    current_price = Column(Float)
    current_return_percent = Column(Float)  # (current_price - entry_price) / entry_price * 100
    current_return_dollars = Column(Float)  # For position sizing
    unrealized_pnl = Column(Float)
    
    # Trade status
    status = Column(String(20), default='ACTIVE')  # ACTIVE, CLOSED, EXPIRED
    is_winner = Column(Boolean)  # True if target hit, False if stop loss hit, None if active
    days_held = Column(Integer, default=0)
    
    # Exit details (when trade is closed)
    exit_price = Column(Float)
    exit_date = Column(DateTime(timezone=True))
    exit_reason = Column(String(50))  # TARGET_HIT, STOP_LOSS, EXPIRED, MANUAL_CLOSE
    final_return_percent = Column(Float)
    final_return_dollars = Column(Float)
    
    # Performance metrics
    max_favorable_excursion = Column(Float)  # Best price reached during trade
    max_adverse_excursion = Column(Float)   # Worst price reached during trade
    volatility_during_hold = Column(Float)
    
    # Data quality and tracking
    last_price_update = Column(DateTime(timezone=True))
    price_update_count = Column(Integer, default=0)
    data_source = Column(String(50), default="alpha_vantage")
    
    # Position sizing (for portfolio-level analysis)
    position_size_dollars = Column(Float, default=1000.0)  # Paper trading amount
    position_size_shares = Column(Float)  # Calculated shares/contracts
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    price_history = relationship("WatchlistPriceHistory", back_populates="watchlist_entry", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_symbol_entry_date', 'symbol', 'entry_date'),
        Index('idx_status_entry_type', 'status', 'entry_type'),
        Index('idx_confidence_performance', 'ai_confidence_score', 'current_return_percent'),
        Index('idx_entry_date_status', 'entry_date', 'status'),
    )
    
    def __repr__(self):
        return f"<WatchlistEntry(symbol='{self.symbol}', type='{self.entry_type}', return={self.current_return_percent}%)>"


class WatchlistPriceHistory(Base):
    """Historical price data for watchlist entries."""
    
    __tablename__ = "watchlist_price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    watchlist_entry_id = Column(Integer, ForeignKey("watchlist_entries.id"), nullable=False, index=True)
    
    # Price data
    price = Column(Float, nullable=False)
    volume = Column(Integer)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Options-specific data (null for stocks)
    implied_volatility = Column(Float)
    delta = Column(Float)
    gamma = Column(Float)
    theta = Column(Float)
    vega = Column(Float)
    
    # Calculated metrics
    return_percent = Column(Float)  # vs entry price
    return_dollars = Column(Float)
    days_since_entry = Column(Integer)
    
    # Data source
    data_source = Column(String(50), default="alpha_vantage")
    is_real_time = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    watchlist_entry = relationship("WatchlistEntry", back_populates="price_history")
    
    # Indexes
    __table_args__ = (
        Index('idx_entry_timestamp', 'watchlist_entry_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<WatchlistPriceHistory(entry_id={self.watchlist_entry_id}, price={self.price}, return={self.return_percent}%)>"


class PerformanceSummary(Base):
    """Aggregated performance metrics for analysis."""
    
    __tablename__ = "performance_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), default='ALL_TIME')  # DAILY, WEEKLY, MONTHLY, ALL_TIME
    
    # Overall performance
    total_trades = Column(Integer, default=0)
    active_trades = Column(Integer, default=0)
    closed_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # Performance metrics
    win_rate = Column(Float, default=0.0)  # winning_trades / closed_trades
    average_return = Column(Float, default=0.0)
    median_return = Column(Float, default=0.0)
    total_return = Column(Float, default=0.0)
    best_trade_return = Column(Float, default=0.0)
    worst_trade_return = Column(Float, default=0.0)
    
    # Risk metrics
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    volatility = Column(Float)
    
    # AI accuracy metrics
    high_confidence_trades = Column(Integer, default=0)  # 80%+ confidence
    high_confidence_winners = Column(Integer, default=0)
    high_confidence_accuracy = Column(Float, default=0.0)
    
    medium_confidence_trades = Column(Integer, default=0)  # 60-80% confidence
    medium_confidence_winners = Column(Integer, default=0)
    medium_confidence_accuracy = Column(Float, default=0.0)
    
    low_confidence_trades = Column(Integer, default=0)  # <60% confidence
    low_confidence_winners = Column(Integer, default=0)
    low_confidence_accuracy = Column(Float, default=0.0)
    
    # Trade type breakdown
    stock_trades = Column(Integer, default=0)
    stock_win_rate = Column(Float, default=0.0)
    option_trades = Column(Integer, default=0)
    option_win_rate = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_period_type_end', 'period_type', 'period_end'),
    )
    
    def __repr__(self):
        return f"<PerformanceSummary(period='{self.period_type}', win_rate={self.win_rate}%, total_trades={self.total_trades})>"
