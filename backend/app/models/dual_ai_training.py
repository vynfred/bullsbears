"""
Dual AI Training Data model for ML training data collection.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from ..core.database import Base


class DualAITrainingData(Base):
    """Detailed dual AI training data for machine learning."""
    
    __tablename__ = "dual_ai_training_data"
    
    # Primary key and relationships
    id = Column(Integer, primary_key=True, index=True)
    analysis_result_id = Column(Integer, ForeignKey("analysis_results.id"), index=True)
    symbol = Column(String(10), nullable=False, index=True)
    
    # Grok AI Analysis Data
    grok_recommendation = Column(String(10))  # BUY, SELL, HOLD
    grok_confidence = Column(Float)  # 0-100
    grok_reasoning = Column(Text)  # Detailed reasoning from Grok
    grok_risk_warning = Column(Text)  # Risk warnings from Grok
    grok_key_factors = Column(Text)  # JSON string of key factors
    grok_response_time_ms = Column(Integer)  # Response time in milliseconds
    
    # DeepSeek AI Analysis Data
    deepseek_sentiment_score = Column(Float)  # 0-100
    deepseek_confidence = Column(Float)  # 0-100
    deepseek_narrative = Column(Text)  # Narrative synthesis from DeepSeek
    deepseek_key_themes = Column(Text)  # JSON string of key themes
    deepseek_crowd_psychology = Column(String(20))  # BULLISH, BEARISH, NEUTRAL, MIXED
    deepseek_sarcasm_detected = Column(Boolean, default=False)  # Whether sarcasm was detected
    deepseek_social_news_bridge = Column(Float)  # Correlation between social and news sentiment
    deepseek_response_time_ms = Column(Integer)  # Response time in milliseconds
    
    # Consensus Engine Data
    consensus_recommendation = Column(String(10))  # Final recommendation after consensus
    consensus_confidence = Column(Float)  # Final confidence score after consensus
    agreement_level = Column(String(20))  # STRONG_AGREEMENT, PARTIAL_AGREEMENT, DISAGREEMENT
    confidence_adjustment = Column(Float)  # Confidence boost/penalty applied (-20 to +20)
    hybrid_validation_triggered = Column(Boolean, default=False)  # Whether hybrid validation was used
    consensus_reasoning = Column(Text)  # Combined reasoning from consensus engine
    
    # ML Training Metadata
    training_label = Column(String(20))  # For supervised learning (CORRECT, INCORRECT, PARTIAL)
    actual_outcome = Column(Float)  # Actual stock/option performance (% change)
    outcome_timestamp = Column(DateTime)  # When the outcome was measured
    data_quality_score = Column(Float, default=100.0)  # Quality score for this training sample
    
    # Technical Context for ML Features (stored as JSON strings)
    market_conditions = Column(Text)  # VIX, market trend, sector performance
    technical_indicators = Column(Text)  # RSI, MACD, Bollinger Bands, etc.
    news_context = Column(Text)  # News sentiment, volume, key events
    social_context = Column(Text)  # Social sentiment, mention volume, trending topics
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    analysis_result = relationship("AnalysisResult", backref="dual_ai_training_data")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_dual_ai_training_symbol', 'symbol'),
        Index('idx_dual_ai_training_agreement', 'agreement_level'),
        Index('idx_dual_ai_training_label', 'training_label'),
        Index('idx_dual_ai_training_created', 'created_at'),
        Index('idx_dual_ai_training_outcome', 'actual_outcome'),
    )
    
    def __repr__(self):
        return f"<DualAITrainingData(symbol='{self.symbol}', agreement='{self.agreement_level}', label='{self.training_label}')>"
    
    @property
    def is_labeled(self) -> bool:
        """Check if this training sample has been labeled."""
        return self.training_label is not None
    
    @property
    def has_outcome(self) -> bool:
        """Check if this training sample has an actual outcome."""
        return self.actual_outcome is not None
    
    @property
    def is_complete_training_sample(self) -> bool:
        """Check if this is a complete training sample with label and outcome."""
        return self.is_labeled and self.has_outcome
    
    @property
    def consensus_accuracy(self) -> float:
        """Calculate accuracy of consensus vs actual outcome (if available)."""
        if not self.has_outcome or not self.consensus_recommendation:
            return None
        
        # Simple accuracy calculation based on direction
        if self.consensus_recommendation == "BUY" and self.actual_outcome > 0:
            return 1.0
        elif self.consensus_recommendation == "SELL" and self.actual_outcome < 0:
            return 1.0
        elif self.consensus_recommendation == "HOLD" and abs(self.actual_outcome) < 2.0:
            return 1.0
        else:
            return 0.0
    
    @classmethod
    def get_training_samples(cls, db_session, labeled_only: bool = False, min_quality_score: float = 80.0):
        """Get training samples for ML model training."""
        query = db_session.query(cls).filter(
            cls.data_quality_score >= min_quality_score
        )
        
        if labeled_only:
            query = query.filter(cls.training_label.isnot(None))
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_unlabeled_samples(cls, db_session, limit: int = 100):
        """Get unlabeled samples for manual labeling."""
        return db_session.query(cls).filter(
            cls.training_label.is_(None),
            cls.data_quality_score >= 80.0
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_accuracy_stats(cls, db_session, days_back: int = 30):
        """Get accuracy statistics for the dual AI system."""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        samples = db_session.query(cls).filter(
            cls.created_at >= cutoff_date,
            cls.actual_outcome.isnot(None),
            cls.consensus_recommendation.isnot(None)
        ).all()
        
        if not samples:
            return None
        
        total_samples = len(samples)
        correct_predictions = sum(1 for sample in samples if sample.consensus_accuracy == 1.0)
        
        return {
            "total_samples": total_samples,
            "correct_predictions": correct_predictions,
            "accuracy_rate": correct_predictions / total_samples if total_samples > 0 else 0.0,
            "strong_agreement_accuracy": cls._get_agreement_accuracy(samples, "STRONG_AGREEMENT"),
            "partial_agreement_accuracy": cls._get_agreement_accuracy(samples, "PARTIAL_AGREEMENT"),
            "disagreement_accuracy": cls._get_agreement_accuracy(samples, "DISAGREEMENT"),
        }
    
    @classmethod
    def _get_agreement_accuracy(cls, samples, agreement_level: str):
        """Helper method to calculate accuracy for specific agreement level."""
        filtered_samples = [s for s in samples if s.agreement_level == agreement_level]
        if not filtered_samples:
            return 0.0
        
        correct = sum(1 for sample in filtered_samples if sample.consensus_accuracy == 1.0)
        return correct / len(filtered_samples)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "grok_recommendation": self.grok_recommendation,
            "grok_confidence": self.grok_confidence,
            "deepseek_sentiment_score": self.deepseek_sentiment_score,
            "deepseek_confidence": self.deepseek_confidence,
            "consensus_recommendation": self.consensus_recommendation,
            "consensus_confidence": self.consensus_confidence,
            "agreement_level": self.agreement_level,
            "confidence_adjustment": self.confidence_adjustment,
            "hybrid_validation_triggered": self.hybrid_validation_triggered,
            "training_label": self.training_label,
            "actual_outcome": self.actual_outcome,
            "data_quality_score": self.data_quality_score,
            "is_complete_training_sample": self.is_complete_training_sample,
            "consensus_accuracy": self.consensus_accuracy,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "outcome_timestamp": self.outcome_timestamp.isoformat() if self.outcome_timestamp else None,
        }
