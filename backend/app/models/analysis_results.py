"""
Analysis results and confidence scoring models.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base


class AnalysisResult(Base):
    """Complete analysis results for a stock/option."""
    
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    
    # Analysis metadata
    analysis_type = Column(String(20), nullable=False)  # 'stock', 'option_call', 'option_put'
    timeframe = Column(String(10), default="1D")  # Analysis timeframe
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Overall recommendation
    recommendation = Column(String(20), nullable=False)  # STRONG_BUY, MODERATE_BUY, WEAK_BUY, HOLD, WEAK_SELL, MODERATE_SELL, STRONG_SELL
    confidence_score = Column(Float, nullable=False)  # 0-100
    
    # Component scores (0-100 each)
    technical_score = Column(Float, nullable=False)
    news_sentiment_score = Column(Float, nullable=False)
    social_sentiment_score = Column(Float, nullable=False)
    earnings_score = Column(Float, nullable=False)
    market_trend_score = Column(Float, nullable=False)
    
    # Risk assessment
    risk_level = Column(String(20), default="moderate")  # low, moderate, high, extreme
    max_loss_potential = Column(Float)  # Maximum potential loss in dollars
    time_decay_risk = Column(Float)  # For options: theta impact
    volatility_risk = Column(Float)  # Volatility impact on position
    
    # Position sizing recommendations
    recommended_position_size = Column(Float)  # In dollars
    max_position_percentage = Column(Float)  # Percentage of portfolio
    
    # Detailed analysis data
    technical_indicators = Column(JSON)  # RSI, MACD, Bollinger Bands, etc.
    news_analysis = Column(JSON)  # News sentiment breakdown
    social_analysis = Column(JSON)  # Social media sentiment breakdown
    earnings_data = Column(JSON)  # Earnings and fundamental data
    market_data = Column(JSON)  # Market trend data
    
    # Options-specific data (if applicable)
    option_contract_symbol = Column(String(50))
    option_type = Column(String(4))  # CALL or PUT
    strike_price = Column(Float)
    expiration_date = Column(DateTime(timezone=True))
    implied_volatility = Column(Float)
    delta = Column(Float)
    gamma = Column(Float)
    theta = Column(Float)
    vega = Column(Float)
    
    # Analysis quality and metadata
    data_quality_score = Column(Float, default=100.0)  # Quality of underlying data
    analysis_version = Column(String(10), default="1.0")
    is_real_time = Column(Boolean, default=True)

    # Dual AI Scoring (for ML training data collection)
    grok_score = Column(Float)  # Grok AI confidence score (0-100)
    deepseek_score = Column(Float)  # DeepSeek AI sentiment score (0-100)
    agreement_level = Column(String(20))  # STRONG_AGREEMENT, PARTIAL_AGREEMENT, DISAGREEMENT
    confidence_adjustment = Column(Float)  # Confidence boost/penalty from consensus (-20 to +20)
    hybrid_validation_triggered = Column(Boolean, default=False)  # Whether hybrid validation was used
    consensus_reasoning = Column(Text)  # Combined reasoning from both AIs
    social_news_bridge = Column(Float)  # Correlation between social and news sentiment
    dual_ai_version = Column(String(10), default="1.0")  # Version of dual AI system used

    # ML Performance Tracking (B1.1 Extension)
    response_time_ms = Column(Integer)  # Total dual AI analysis response time in milliseconds
    cache_hit = Column(Boolean, default=False)  # Whether Redis cache was hit for this analysis
    ai_cost_cents = Column(Integer, default=0)  # Total API cost for this analysis in cents (Grok + DeepSeek)
    grok_analysis_time = Column(DateTime(timezone=True))  # Timestamp when Grok analysis completed
    deepseek_analysis_time = Column(DateTime(timezone=True))  # Timestamp when DeepSeek analysis completed
    consensus_time = Column(DateTime(timezone=True))  # Timestamp when consensus resolution completed
    handoff_delta = Column(Float)  # Time difference between Grok and DeepSeek analysis phases
    ml_features = Column(JSON, default=dict)  # Market context features for ML training (VIX, RSI weights, etc.)
    consensus_score = Column(Float)  # Final consensus confidence score after agreement adjustments
    api_calls_count = Column(Integer, default=0)  # Total number of API calls made for this analysis
    data_sources_used = Column(JSON, default=list)  # Array of data sources used (Alpha Vantage, NewsAPI, Reddit, etc.)
    performance_tier = Column(String(20), default="standard")  # Performance classification: fast, standard, slow

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))  # When this analysis expires
    
    # Relationships
    stock = relationship("Stock", back_populates="analysis_results")
    confidence_scores = relationship("ConfidenceScore", back_populates="analysis_result", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_recommendation_confidence', 'recommendation', 'confidence_score'),
        Index('idx_analysis_type_timestamp', 'analysis_type', 'timestamp'),
        # ML Performance Indexes (B1.1 Extension)
        Index('idx_analysis_agreement_level', 'agreement_level'),
        Index('idx_analysis_consensus_score', 'consensus_score'),
        Index('idx_analysis_response_time', 'response_time_ms'),
        Index('idx_analysis_ai_cost', 'ai_cost_cents'),
        Index('idx_analysis_performance_tier', 'performance_tier'),
        # Composite indexes for time-series ML analysis
        Index('idx_symbol_created_consensus', 'symbol', 'created_at', 'consensus_score'),
        Index('idx_agreement_confidence_time', 'agreement_level', 'confidence_score', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AnalysisResult(symbol='{self.symbol}', recommendation='{self.recommendation}', confidence={self.confidence_score})>"


class ConfidenceScore(Base):
    """Detailed confidence score breakdown."""
    
    __tablename__ = "confidence_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False, index=True)
    
    # Score component details
    component_name = Column(String(50), nullable=False)  # technical, news, social, earnings, market
    raw_score = Column(Float, nullable=False)  # Raw component score
    weighted_score = Column(Float, nullable=False)  # Score after applying weight
    weight = Column(Float, nullable=False)  # Weight used (0-100)
    
    # Component-specific data
    data_points_count = Column(Integer, default=0)  # Number of data points used
    data_quality = Column(Float, default=100.0)  # Quality of data for this component
    last_updated = Column(DateTime(timezone=True), nullable=False)
    
    # Detailed breakdown
    sub_scores = Column(JSON)  # Detailed sub-component scores
    contributing_factors = Column(JSON)  # Factors that influenced the score
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    analysis_result = relationship("AnalysisResult", back_populates="confidence_scores")
    
    def __repr__(self):
        return f"<ConfidenceScore(component='{self.component_name}', weighted_score={self.weighted_score})>"
