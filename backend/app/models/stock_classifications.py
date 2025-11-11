"""
Stock Classification Models for Tiered System

Models for the 5-tier stock classification system:
- ALL (6,960 NASDAQ stocks)
- ACTIVE (~3,000 stocks)
- QUALIFIED (~50-500 stocks)
- SHORT_LIST (max 80 stocks)
- PICKS (max 6 stocks)
"""

from sqlalchemy import Column, Integer, String, DECIMAL, BigInteger, Date, DateTime, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime, date
from typing import Optional

Base = declarative_base()

class StockClassification(Base):
    """
    Stock Classification Model for Tiered System
    
    Tracks which tier each stock belongs to and relevant metrics
    for tier qualification and movement tracking.
    """
    __tablename__ = 'stock_classifications'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    current_tier = Column(String(20), nullable=False, index=True)  # ALL, ACTIVE, QUALIFIED, SHORT_LIST, PICKS
    
    # Basic stock metrics for tier qualification
    price = Column(DECIMAL(10, 2))
    market_cap = Column(BigInteger)
    daily_volume = Column(BigInteger)
    
    # Tier management
    last_qualified_date = Column(Date, index=True)
    qualified_days_count = Column(Integer, default=0)
    selection_fatigue_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_classifications_tier', 'current_tier'),
        Index('idx_classifications_symbol', 'symbol'),
        Index('idx_classifications_qualified_date', 'last_qualified_date'),
        Index('idx_classifications_updated', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<StockClassification(symbol='{self.symbol}', tier='{self.current_tier}', price={self.price})>"
    
    @property
    def is_qualified_for_active(self) -> bool:
        """Check if stock meets ACTIVE tier criteria"""
        return (
            self.price and self.price > 1.25 and
            self.daily_volume and self.daily_volume > 100000
        )
    
    @property
    def qualified_days_remaining(self) -> int:
        """Days remaining in QUALIFIED tier (minimum 3 days)"""
        if self.current_tier != 'QUALIFIED' or not self.last_qualified_date:
            return 0
        
        days_since_qualified = (date.today() - self.last_qualified_date).days
        return max(0, 3 - days_since_qualified)
    
    def move_to_tier(self, new_tier: str) -> None:
        """Move stock to a new tier with proper tracking"""
        old_tier = self.current_tier
        self.current_tier = new_tier
        self.updated_at = datetime.utcnow()
        
        # Special handling for QUALIFIED tier
        if new_tier == 'QUALIFIED':
            if old_tier != 'QUALIFIED':
                self.last_qualified_date = date.today()
                self.qualified_days_count = 1
            else:
                self.qualified_days_count += 1
        
        # Track selection fatigue for SHORT_LIST
        if new_tier == 'SHORT_LIST':
            self.selection_fatigue_count += 1


class KillSwitchStatus(Base):
    """
    Kill Switch Status Tracking
    
    Tracks daily kill switch activations based on market conditions
    (VIX > 35 AND SPY < -2%)
    """
    __tablename__ = 'kill_switch_status'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    
    # Market condition data
    vix_level = Column(DECIMAL(5, 2))
    spy_change = Column(DECIMAL(5, 3))
    
    # Kill switch status
    kill_switch_active = Column(Boolean, nullable=False, index=True)
    reason = Column(String(500))
    
    # Timestamp
    created_at = Column(DateTime, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_kill_switch_date', 'date'),
        Index('idx_kill_switch_active', 'kill_switch_active'),
    )
    
    def __repr__(self):
        return f"<KillSwitchStatus(date='{self.date}', active={self.kill_switch_active}, vix={self.vix_level})>"
    
    @classmethod
    def should_activate_kill_switch(cls, vix_level: float, spy_change: float) -> bool:
        """Determine if kill switch should be activated"""
        return vix_level > 35.0 and spy_change < -2.0


class HistoricalData(Base):
    """
    Historical Price Data Storage
    
    Stores daily OHLCV data for all stocks with 12-month rolling retention.
    Used for ML model training and historical analysis.
    """
    __tablename__ = 'historical_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # OHLCV data
    open_price = Column(DECIMAL(10, 2), nullable=False)
    high_price = Column(DECIMAL(10, 2), nullable=False)
    low_price = Column(DECIMAL(10, 2), nullable=False)
    close_price = Column(DECIMAL(10, 2), nullable=False)
    volume = Column(BigInteger, nullable=False)
    adj_close = Column(DECIMAL(10, 2))
    
    # Timestamp
    created_at = Column(DateTime, default=func.now())
    
    # Composite indexes for performance
    __table_args__ = (
        Index('idx_historical_symbol_date', 'symbol', 'date'),
        Index('idx_historical_date', 'date'),
        Index('idx_historical_symbol', 'symbol'),
    )
    
    def __repr__(self):
        return f"<HistoricalData(symbol='{self.symbol}', date='{self.date}', close={self.close_price})>"
    
    @property
    def daily_return(self) -> Optional[float]:
        """Calculate daily return percentage"""
        if self.open_price and self.open_price > 0:
            return ((self.close_price - self.open_price) / self.open_price) * 100
        return None
    
    @property
    def daily_range(self) -> Optional[float]:
        """Calculate daily price range percentage"""
        if self.low_price and self.low_price > 0:
            return ((self.high_price - self.low_price) / self.low_price) * 100
        return None


class TierMovementLog(Base):
    """
    Tier Movement Tracking
    
    Logs all movements between tiers for analysis and debugging.
    Helps understand stock flow through the classification system.
    """
    __tablename__ = 'tier_movement_log'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    
    # Movement details
    from_tier = Column(String(20), nullable=False)
    to_tier = Column(String(20), nullable=False, index=True)
    reason = Column(String(500))
    
    # Context data
    price_at_movement = Column(DECIMAL(10, 2))
    volume_at_movement = Column(BigInteger)
    market_conditions = Column(String(1000))  # JSON string
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_tier_movement_symbol', 'symbol'),
        Index('idx_tier_movement_to_tier', 'to_tier'),
        Index('idx_tier_movement_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<TierMovementLog(symbol='{self.symbol}', {self.from_tier} -> {self.to_tier})>"


# Utility functions for tier management

def get_tier_criteria() -> dict:
    """Get criteria for each tier"""
    return {
        'ALL': {
            'description': 'All NASDAQ stocks',
            'criteria': 'Listed on NASDAQ',
            'count': 6960
        },
        'ACTIVE': {
            'description': 'Viable investment candidates',
            'criteria': 'Price > $1.25, Volume > 100K, No penny/IPO/delisting',
            'count': '~3,000'
        },
        'QUALIFIED': {
            'description': 'Showing momentum signs',
            'criteria': 'Prescreen agent identifies movement potential',
            'count': '~50-500'
        },
        'SHORT_LIST': {
            'description': 'Agent-selected candidates',
            'criteria': 'Predictor agents select from QUALIFIED',
            'count': 'max 80'
        },
        'PICKS': {
            'description': 'Final daily recommendations',
            'criteria': 'Arbitrator selects from SHORT_LIST',
            'count': 'max 6 (3 bullish, 3 bearish)'
        }
    }


def get_tier_hierarchy() -> list:
    """Get tier hierarchy in order"""
    return ['ALL', 'ACTIVE', 'QUALIFIED', 'SHORT_LIST', 'PICKS']


def is_tier_promotion(from_tier: str, to_tier: str) -> bool:
    """Check if movement is a promotion (toward PICKS)"""
    hierarchy = get_tier_hierarchy()
    try:
        from_idx = hierarchy.index(from_tier)
        to_idx = hierarchy.index(to_tier)
        return to_idx > from_idx
    except ValueError:
        return False


def is_tier_demotion(from_tier: str, to_tier: str) -> bool:
    """Check if movement is a demotion (away from PICKS)"""
    hierarchy = get_tier_hierarchy()
    try:
        from_idx = hierarchy.index(from_tier)
        to_idx = hierarchy.index(to_tier)
        return to_idx < from_idx
    except ValueError:
        return False
