"""
Options-related database models.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Date, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base


class OptionsChain(Base):
    """Options chain metadata."""
    
    __tablename__ = "options_chains"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    expiration_date = Column(Date, nullable=False, index=True)
    days_to_expiration = Column(Integer, nullable=False)
    is_weekly = Column(Boolean, default=False)
    is_monthly = Column(Boolean, default=True)
    is_quarterly = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    stock = relationship("Stock", back_populates="options_chains")
    options_data = relationship("OptionsData", back_populates="options_chain", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_stock_expiration', 'stock_id', 'expiration_date'),
    )
    
    def __repr__(self):
        return f"<OptionsChain(stock_id={self.stock_id}, expiration='{self.expiration_date}')>"


class OptionsData(Base):
    """Individual options contract data with Greeks."""
    
    __tablename__ = "options_data"
    
    id = Column(Integer, primary_key=True, index=True)
    options_chain_id = Column(Integer, ForeignKey("options_chains.id"), nullable=False, index=True)
    contract_symbol = Column(String(50), nullable=False, unique=True, index=True)
    
    # Contract details
    option_type = Column(String(4), nullable=False)  # 'CALL' or 'PUT'
    strike_price = Column(Float, nullable=False, index=True)
    expiration_date = Column(Date, nullable=False)
    
    # Pricing data
    last_price = Column(Float)
    bid = Column(Float)
    ask = Column(Float)
    mark = Column(Float)  # Mid-point between bid and ask
    
    # Volume and interest
    volume = Column(Integer, default=0)
    open_interest = Column(Integer, default=0)
    
    # Greeks
    delta = Column(Float)
    gamma = Column(Float)
    theta = Column(Float)
    vega = Column(Float)
    rho = Column(Float)
    
    # Implied volatility
    implied_volatility = Column(Float)
    
    # Additional metrics
    intrinsic_value = Column(Float)
    time_value = Column(Float)
    moneyness = Column(Float)  # Strike / Underlying price
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Data quality
    data_source = Column(String(50), default="alpha_vantage")
    is_real_time = Column(Boolean, default=True)
    
    # Relationships
    options_chain = relationship("OptionsChain", back_populates="options_data")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_chain_strike_type', 'options_chain_id', 'strike_price', 'option_type'),
        Index('idx_contract_timestamp', 'contract_symbol', 'timestamp'),
        Index('idx_expiration_strike', 'expiration_date', 'strike_price'),
    )
    
    def __repr__(self):
        return f"<OptionsData(symbol='{self.contract_symbol}', type='{self.option_type}', strike={self.strike_price})>"
