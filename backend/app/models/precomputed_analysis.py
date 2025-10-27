"""
Precomputed Analysis model for storing complete analysis results.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta

from ..core.database import Base


class PrecomputedAnalysis(Base):
    """Precomputed complete analysis results for stocks."""
    
    __tablename__ = "precomputed_analysis"
    
    # Primary key and identifiers
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    
    # Analysis metadata
    analysis_version = Column(String(10), default="1.0")
    computed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_market_hours = Column(Boolean, default=True)
    
    # Complete analysis data (JSON fields)
    complete_analysis = Column(JSON, nullable=False)  # Full analysis result
    technical_data = Column(JSON)  # Technical analysis breakdown
    sentiment_data = Column(JSON)  # News and social sentiment
    ai_analysis = Column(JSON)  # Grok and DeepSeek analysis
    risk_assessment = Column(JSON)  # Risk metrics and warnings
    
    # Key metrics for quick access (denormalized for performance)
    confidence_score = Column(Float, nullable=False, index=True)
    recommendation = Column(String(10), nullable=False, index=True)  # BUY, SELL, HOLD
    risk_level = Column(String(10), nullable=False)  # LOW, MODERATE, HIGH
    
    # Technical scores
    technical_score = Column(Float, default=50.0)
    rsi = Column(Float)
    macd_signal = Column(String(10))  # BULLISH, BEARISH, NEUTRAL
    
    # Sentiment scores
    news_sentiment_score = Column(Float, default=50.0)
    social_sentiment_score = Column(Float, default=50.0)
    overall_sentiment = Column(String(10))  # POSITIVE, NEGATIVE, NEUTRAL
    
    # Data freshness tracking
    api_calls_used = Column(Integer, default=0)
    data_sources = Column(JSON)  # List of data sources used
    data_quality_score = Column(Float, default=100.0)

    # Dual AI Scoring (for ML training data collection)
    grok_confidence = Column(Float)  # Grok AI confidence score (0-100)
    deepseek_sentiment = Column(Float)  # DeepSeek sentiment analysis score (0-100)
    ai_agreement_level = Column(String(20))  # STRONG_AGREEMENT, PARTIAL_AGREEMENT, DISAGREEMENT
    consensus_confidence_boost = Column(Float)  # Confidence boost/penalty from consensus (-20 to +20)
    hybrid_validation_used = Column(Boolean, default=False)  # Whether hybrid validation was triggered
    dual_ai_reasoning = Column(Text)  # Combined reasoning from both AI systems
    ai_model_versions = Column(String(100))  # JSON string of AI model versions used

    # Performance tracking
    computation_time_ms = Column(Integer)  # Time taken to compute
    cache_hit_rate = Column(Float)  # Cache hit rate during computation
    
    # Status and flags
    is_stale = Column(Boolean, default=False)
    has_warnings = Column(Boolean, default=False)
    warning_messages = Column(JSON)  # List of warning messages
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    stock = relationship("Stock", back_populates="precomputed_analyses")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_symbol_computed_at', 'symbol', 'computed_at'),
        Index('idx_expires_at_symbol', 'expires_at', 'symbol'),
        Index('idx_confidence_recommendation', 'confidence_score', 'recommendation'),
        Index('idx_market_hours_computed', 'is_market_hours', 'computed_at'),
    )
    
    def __repr__(self):
        return f"<PrecomputedAnalysis(symbol='{self.symbol}', confidence={self.confidence_score}, computed_at='{self.computed_at}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the analysis has expired."""
        return datetime.now() > self.expires_at
    
    @property
    def freshness_minutes(self) -> int:
        """Get the age of the analysis in minutes."""
        return int((datetime.now() - self.computed_at).total_seconds() / 60)
    
    @property
    def time_until_expiry_minutes(self) -> int:
        """Get minutes until expiry."""
        if self.is_expired:
            return 0
        return int((self.expires_at - datetime.now()).total_seconds() / 60)
    
    @classmethod
    def get_fresh_analysis(cls, db_session, symbol: str, max_age_minutes: int = 60):
        """Get fresh analysis for a symbol."""
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        return db_session.query(cls).filter(
            cls.symbol == symbol.upper(),
            cls.computed_at >= cutoff_time,
            cls.expires_at > datetime.now()
        ).order_by(cls.computed_at.desc()).first()
    
    @classmethod
    def get_latest_analysis(cls, db_session, symbol: str):
        """Get the most recent analysis for a symbol, even if expired."""
        return db_session.query(cls).filter(
            cls.symbol == symbol.upper()
        ).order_by(cls.computed_at.desc()).first()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "confidence_score": self.confidence_score,
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
            "computed_at": self.computed_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "freshness_minutes": self.freshness_minutes,
            "is_expired": self.is_expired,
            "is_stale": self.is_stale,
            "data_quality_score": self.data_quality_score,
            "api_calls_used": self.api_calls_used,
            "computation_time_ms": self.computation_time_ms,
            "complete_analysis": self.complete_analysis,
            "metadata": {
                "analysis_version": self.analysis_version,
                "is_market_hours": self.is_market_hours,
                "data_sources": self.data_sources,
                "has_warnings": self.has_warnings,
                "warning_messages": self.warning_messages
            }
        }


class PrecomputeJobStatus(Base):
    """Track status of precompute background jobs."""
    
    __tablename__ = "precompute_job_status"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), unique=True, nullable=False, index=True)
    job_type = Column(String(50), nullable=False)  # 'update_top_stocks', 'update_single_stock'
    
    # Job parameters
    symbols = Column(JSON)  # List of symbols being processed
    market_hours = Column(Boolean, default=True)
    
    # Status tracking
    status = Column(String(20), default="PENDING", index=True)  # PENDING, RUNNING, SUCCESS, FAILED
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Results
    symbols_processed = Column(Integer, default=0)
    symbols_failed = Column(Integer, default=0)
    total_api_calls = Column(Integer, default=0)
    error_messages = Column(JSON)  # List of error messages
    
    # Performance metrics
    total_time_seconds = Column(Float)
    average_time_per_symbol = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<PrecomputeJobStatus(job_id='{self.job_id}', status='{self.status}', symbols={len(self.symbols or [])})>"
