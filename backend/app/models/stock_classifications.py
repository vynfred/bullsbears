# app/models/stock_classifications.py
from sqlalchemy import Column, Integer, String, DECIMAL, BigInteger, Date, DateTime, Boolean, JSON, Index
from sqlalchemy.sql import func
from datetime import datetime, date

from ..core.database import Base

class StockClassification(Base):
    __tablename__ = 'stock_classifications'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    exchange = Column(String(10), nullable=False, index=True)
    current_tier = Column(String(20), nullable=False, index=True)  # ALL, ACTIVE, SHORT_LIST, PICKS
    
    # Basic stock metrics for tier qualification
    price = Column(DECIMAL(10, 2))
    market_cap = Column(BigInteger)
    daily_volume = Column(BigInteger)
    
    # Add company info fields that filter service expects
    company_name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))
    
    last_qualified_date = Column(Date, index=True)
    qualified_days_count = Column(Integer, default=0)
    selection_fatigue_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_classifications_tier', 'current_tier'),
        Index('idx_classifications_symbol', 'symbol'),
        Index('idx_classifications_updated', 'updated_at'),
    )

    def __repr__(self):
        return f"<StockClassification(symbol='{self.symbol}', tier='{self.current_tier}')>"

class ShortListPriceTracking(Base):
    __tablename__ = "short_list_price_tracking"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    symbol = Column(String(10), nullable=False)
    prescreen_score = Column(DECIMAL(5, 4))
    social_score = Column(Integer)
    vision_flags = Column(JSON)
    final_pick = Column(Boolean)
    change_30d = Column(DECIMAL(6, 2))
    confidence = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_short_list_date', 'date'),
        Index('idx_short_list_symbol', 'symbol'),
    )
