"""
Alert models for bullish and bearish predictions
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from datetime import datetime

from ..core.database import Base


class BullishAlert(Base):
    """Bullish alert model for +20% upward movement predictions"""
    
    __tablename__ = "bullish_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    prediction = Column(String(20), default="BULLISH", nullable=False)
    confidence = Column(Float, nullable=False)  # 0-100 percentage
    reasoning = Column(Text, nullable=True)
    
    # Price targets
    current_price = Column(Float, nullable=False)
    target_price_low = Column(Float, nullable=False)   # Conservative target
    target_price_high = Column(Float, nullable=False)  # Optimistic target
    
    # Market data
    volume = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Outcome tracking
    outcome = Column(String(20), default="PENDING", nullable=False)  # PENDING, SUCCESS, FAILURE, PARTIAL
    actual_high_price = Column(Float, nullable=True)
    outcome_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<BullishAlert(symbol='{self.symbol}', confidence={self.confidence}%, target=${self.target_price_high})>"


class BearishAlert(Base):
    """Bearish alert model for -20% downward movement predictions"""
    
    __tablename__ = "bearish_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    prediction = Column(String(20), default="BEARISH", nullable=False)
    confidence = Column(Float, nullable=False)  # 0-100 percentage
    reasoning = Column(Text, nullable=True)
    
    # Price targets
    current_price = Column(Float, nullable=False)
    target_price_low = Column(Float, nullable=False)   # Conservative target (more negative)
    target_price_high = Column(Float, nullable=False)  # Optimistic target (less negative)
    
    # Market data
    volume = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Outcome tracking
    outcome = Column(String(20), default="PENDING", nullable=False)  # PENDING, SUCCESS, FAILURE, PARTIAL
    actual_low_price = Column(Float, nullable=True)
    outcome_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<BearishAlert(symbol='{self.symbol}', confidence={self.confidence}%, target=${self.target_price_low})>"
