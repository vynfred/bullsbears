"""
Stock-related database models.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base


class Stock(Base):
    """Stock information model."""
    
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    exchange = Column(String(50), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    prices = relationship("StockPrice", back_populates="stock", cascade="all, delete-orphan")
    options_chains = relationship("OptionsChain", back_populates="stock", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="stock", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Stock(symbol='{self.symbol}', name='{self.name}')>"


class StockPrice(Base):
    """Real-time and historical stock price data."""
    
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Price data
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    
    # Additional metrics
    vwap = Column(Float)  # Volume Weighted Average Price
    pre_market_price = Column(Float)
    after_hours_price = Column(Float)
    
    # Technical indicators (calculated and cached)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    bb_upper = Column(Float)  # Bollinger Band Upper
    bb_middle = Column(Float)  # Bollinger Band Middle
    bb_lower = Column(Float)  # Bollinger Band Lower
    sma_20 = Column(Float)  # Simple Moving Average 20
    sma_50 = Column(Float)  # Simple Moving Average 50
    ema_12 = Column(Float)  # Exponential Moving Average 12
    ema_26 = Column(Float)  # Exponential Moving Average 26
    
    # Data source and quality
    data_source = Column(String(50), default="alpha_vantage")
    is_real_time = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Foreign key relationship
    stock = relationship("Stock", back_populates="prices")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_stock_timestamp', 'stock_id', 'timestamp'),
        Index('idx_timestamp_desc', 'timestamp', postgresql_using='btree'),
    )
    
    def __repr__(self):
        return f"<StockPrice(stock_id={self.stock_id}, timestamp='{self.timestamp}', close={self.close_price})>"
