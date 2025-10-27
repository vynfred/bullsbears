"""
Chosen Option model for tracking user-selected option plays.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from datetime import datetime

from ..core.database import Base


class ChosenOption(Base):
    __tablename__ = "chosen_options"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    company_name = Column(String)
    option_type = Column(String)  # CALL or PUT
    strike = Column(Float)
    expiration = Column(String)
    entry_price = Column(Float)
    target_price = Column(Float)
    stop_loss = Column(Float)
    confidence_score = Column(Float)
    ai_recommendation = Column(String)
    chosen_at = Column(DateTime, default=datetime.utcnow)
    position_size = Column(Integer)
    max_profit = Column(Float)
    max_loss = Column(Float)
    risk_reward_ratio = Column(Float)
    summary = Column(Text)
    key_factors = Column(Text)  # JSON string
    is_expired = Column(Boolean, default=False)
    final_price = Column(Float, nullable=True)
    actual_profit_loss = Column(Float, nullable=True)

    # Dual AI Scoring (for ML training data collection)
    grok_technical_score = Column(Float)  # Grok AI technical analysis score (0-100)
    deepseek_sentiment_score = Column(Float)  # DeepSeek sentiment analysis score (0-100)
    ai_consensus_level = Column(String(20))  # STRONG_AGREEMENT, PARTIAL_AGREEMENT, DISAGREEMENT
    confidence_boost_applied = Column(Float)  # Confidence boost/penalty from consensus (-20 to +20)
    hybrid_validation_outcome = Column(Boolean)  # Whether hybrid validation was triggered
    dual_ai_recommendation_reasoning = Column(Text)  # Combined reasoning from both AI systems
    ai_analysis_timestamp = Column(DateTime)  # When AI analysis was performed

    def __repr__(self):
        return f"<ChosenOption(symbol={self.symbol}, type={self.option_type}, strike={self.strike}, expiration={self.expiration})>"


class OptionPriceHistory(Base):
    __tablename__ = "option_price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    chosen_option_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    option_type = Column(String)
    strike = Column(Float)
    expiration = Column(String)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    underlying_price = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    open_interest = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<OptionPriceHistory(symbol={self.symbol}, price={self.price}, timestamp={self.timestamp})>"
