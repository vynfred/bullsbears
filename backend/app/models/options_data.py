"""
Options Data Models for BullsBears System
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..core.database import Base


class OptionsData(Base):
    """Options data model"""
    __tablename__ = "options_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True, nullable=False)
    option_type = Column(String(4), nullable=False)  # CALL or PUT
    strike_price = Column(Float, nullable=False)
    expiration_date = Column(DateTime, nullable=False)
    bid = Column(Float)
    ask = Column(Float)
    last_price = Column(Float)
    volume = Column(Integer)
    open_interest = Column(Integer)
    implied_volatility = Column(Float)
    delta = Column(Float)
    gamma = Column(Float)
    theta = Column(Float)
    vega = Column(Float)
    rho = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OptionsChain(Base):
    """Options chain model"""
    __tablename__ = "options_chains"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True, nullable=False)
    expiration_date = Column(DateTime, nullable=False)
    chain_data = Column(Text)  # JSON string of full chain
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
