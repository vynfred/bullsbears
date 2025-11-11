"""
Pick Candidates Database Models
Track all predictor agent candidates with targets for retrospective analysis
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, List, Any, Optional

Base = declarative_base()


class PickCandidate(Base):
    """
    Store all predictor agent candidates before arbitrator selection
    Enables retrospective analysis of missed opportunities
    """
    __tablename__ = 'pick_candidates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Candidate identification
    ticker = Column(String(10), nullable=False, index=True)
    prediction_date = Column(DateTime, nullable=False, default=func.now(), index=True)
    prediction_cycle = Column(String(20), nullable=False, index=True)  # 'morning', 'afternoon', etc.
    
    # Predictor agent info
    predictor_agent = Column(String(50), nullable=False, index=True)  # 'BullPredictor', 'BearPredictor', etc.
    agent_model = Column(String(50), nullable=False)  # 'deepseek-r1:8b', 'qwen2.5:14b'
    agent_confidence = Column(Float, nullable=False)  # 0.0-1.0
    
    # Prediction details
    prediction_type = Column(String(10), nullable=False, index=True)  # 'bullish', 'bearish'
    reasoning = Column(Text, nullable=True)  # Agent's reasoning
    
    # Vision agent targets
    vision_targets = Column(JSON, nullable=True)  # Target prices and timeframes from vision agents
    target_low = Column(Float, nullable=True)  # Conservative target
    target_medium = Column(Float, nullable=True)  # Expected target
    target_high = Column(Float, nullable=True)  # Optimistic target
    target_timeframe_days = Column(Integer, nullable=True)  # Expected days to hit targets
    
    # Market context at prediction time
    current_price = Column(Float, nullable=False)
    market_conditions = Column(JSON, nullable=True)  # Market intelligence from news filter
    technical_indicators = Column(JSON, nullable=True)  # Technical analysis data
    sentiment_score = Column(Float, nullable=True)  # Overall sentiment score
    
    # Arbitrator decision
    selected_by_arbitrator = Column(Boolean, nullable=False, default=False, index=True)
    arbitrator_reasoning = Column(Text, nullable=True)  # Why selected/rejected
    final_pick_id = Column(Integer, ForeignKey('daily_picks.id'), nullable=True, index=True)
    
    # Retrospective analysis
    outcome_analyzed = Column(Boolean, nullable=False, default=False, index=True)
    analysis_date = Column(DateTime, nullable=True)
    
    # Performance tracking
    max_price_reached = Column(Float, nullable=True)  # Highest price during tracking period
    min_price_reached = Column(Float, nullable=True)  # Lowest price during tracking period
    price_at_analysis = Column(Float, nullable=True)  # Price when retrospective analysis was done
    
    # Target achievement
    target_low_hit = Column(Boolean, nullable=True)
    target_medium_hit = Column(Boolean, nullable=True)
    target_high_hit = Column(Boolean, nullable=True)
    days_to_target_hit = Column(Integer, nullable=True)  # Days to first target hit
    
    # Performance metrics
    max_gain_percent = Column(Float, nullable=True)  # Best performance during tracking
    final_performance_percent = Column(Float, nullable=True)  # Performance at analysis date
    outperformed_final_picks = Column(Boolean, nullable=True)  # Did better than selected picks
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    final_pick = relationship("DailyPick", back_populates="candidates")
    price_tracking = relationship("CandidatePriceTracking", back_populates="candidate")
    
    # Indexes for performance
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )


class CandidatePriceTracking(Base):
    """
    Track price movements for all candidates to enable retrospective analysis
    """
    __tablename__ = 'candidate_price_tracking'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    candidate_id = Column(Integer, ForeignKey('pick_candidates.id'), nullable=False, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    
    # Price data
    tracking_date = Column(DateTime, nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)
    
    # Performance metrics
    percent_change = Column(Float, nullable=False)  # From prediction price
    days_since_prediction = Column(Integer, nullable=False)
    
    # Target status
    target_low_achieved = Column(Boolean, nullable=False, default=False)
    target_medium_achieved = Column(Boolean, nullable=False, default=False)
    target_high_achieved = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Relationships
    candidate = relationship("PickCandidate", back_populates="price_tracking")
    
    # Indexes
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )


class CandidateRetrospectiveAnalysis(Base):
    """
    Store retrospective analysis results for model learning
    """
    __tablename__ = 'candidate_retrospective_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Analysis scope
    analysis_date = Column(DateTime, nullable=False, default=func.now(), index=True)
    analysis_period_days = Column(Integer, nullable=False)  # How many days back analyzed
    prediction_cycle = Column(String(20), nullable=False, index=True)
    
    # Performance comparison
    total_candidates = Column(Integer, nullable=False)
    selected_picks = Column(Integer, nullable=False)
    rejected_candidates = Column(Integer, nullable=False)
    
    # Outcome metrics
    selected_picks_avg_performance = Column(Float, nullable=True)
    rejected_candidates_avg_performance = Column(Float, nullable=True)
    missed_opportunities_count = Column(Integer, nullable=False, default=0)  # Rejected but outperformed
    
    # Target achievement rates
    selected_target_hit_rate = Column(Float, nullable=True)  # % of selected picks hitting targets
    rejected_target_hit_rate = Column(Float, nullable=True)  # % of rejected candidates hitting targets
    
    # Model insights
    top_missed_opportunities = Column(JSON, nullable=True)  # Best rejected candidates
    arbitrator_bias_analysis = Column(JSON, nullable=True)  # Patterns in arbitrator decisions
    predictor_performance_ranking = Column(JSON, nullable=True)  # Which predictors had best rejected candidates
    
    # Recommendations
    model_adjustment_recommendations = Column(JSON, nullable=True)  # Suggested model tweaks
    arbitrator_threshold_recommendations = Column(JSON, nullable=True)  # Suggested threshold changes
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Indexes
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )


class CandidateModelLearning(Base):
    """
    Track model learning adjustments based on candidate analysis
    """
    __tablename__ = 'candidate_model_learning'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Learning cycle
    learning_date = Column(DateTime, nullable=False, default=func.now(), index=True)
    retrospective_analysis_id = Column(Integer, ForeignKey('candidate_retrospective_analysis.id'), nullable=False)
    
    # Model adjustments
    predictor_weight_adjustments = Column(JSON, nullable=True)  # Adjust predictor agent weights
    arbitrator_threshold_adjustments = Column(JSON, nullable=True)  # Adjust selection thresholds
    confidence_calibration_adjustments = Column(JSON, nullable=True)  # Adjust confidence scoring
    
    # Implementation status
    adjustments_applied = Column(Boolean, nullable=False, default=False)
    application_date = Column(DateTime, nullable=True)
    
    # Performance tracking
    pre_adjustment_performance = Column(JSON, nullable=True)  # Performance before adjustments
    post_adjustment_performance = Column(JSON, nullable=True)  # Performance after adjustments
    improvement_metrics = Column(JSON, nullable=True)  # Measured improvements
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    retrospective_analysis = relationship("CandidateRetrospectiveAnalysis")
    
    # Indexes
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )
