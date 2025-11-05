"""
Relative Confidence Scoring System
Converts raw ML scores to relative percentiles based on historical distribution
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.analysis_results import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceThresholds:
    """Dynamic confidence thresholds based on historical distribution"""
    high_threshold: float      # P90 - Top 10% of scores
    medium_threshold: float    # P70 - Top 30% of scores  
    speculative_threshold: float  # P40 - Top 60% of scores
    filter_threshold: float    # P40 - Bottom 40% filtered out
    last_updated: datetime
    sample_size: int


@dataclass
class RelativeConfidence:
    """Relative confidence with user-friendly display"""
    raw_score: float           # Original ML score (0.0-1.0)
    percentile: float          # Percentile rank (0-100)
    display_score: int         # User-facing score (50-100)
    level: str                 # HIGH, MEDIUM, SPECULATIVE
    emoji: str                 # Visual indicator
    description: str           # User-friendly description


class RelativeConfidenceScorer:
    """
    Converts raw ML confidence scores to relative percentiles
    Automatically recalibrates based on recent model performance
    """
    
    def __init__(self):
        self.bullish_thresholds: Optional[ConfidenceThresholds] = None
        self.bearish_thresholds: Optional[ConfidenceThresholds] = None
        self.recalibration_days = 30  # Recalibrate every 30 days
        self.min_sample_size = 100    # Minimum samples for reliable thresholds
        
    async def get_relative_confidence(self, raw_score: float, prediction_type: str = "bullish") -> RelativeConfidence:
        """
        Convert raw ML score to relative confidence
        
        Args:
            raw_score: Raw ML confidence (0.0-1.0)
            prediction_type: "bullish" or "bearish"
            
        Returns:
            RelativeConfidence with percentile-based scoring
        """
        # Get appropriate thresholds
        thresholds = await self._get_thresholds(prediction_type)
        
        # Calculate percentile rank
        percentile = self._calculate_percentile(raw_score, thresholds, prediction_type)
        
        # Convert to user-friendly display
        display_score, level, emoji, description = self._convert_to_display(percentile, raw_score)
        
        return RelativeConfidence(
            raw_score=raw_score,
            percentile=percentile,
            display_score=display_score,
            level=level,
            emoji=emoji,
            description=description
        )
    
    async def should_generate_alert(self, raw_score: float, prediction_type: str = "bullish") -> bool:
        """
        Determine if score is high enough to generate an alert
        Uses relative threshold (top 60% of historical scores)
        """
        thresholds = await self._get_thresholds(prediction_type)
        return raw_score >= thresholds.speculative_threshold
    
    async def _get_thresholds(self, prediction_type: str) -> ConfidenceThresholds:
        """Get or calculate confidence thresholds for prediction type"""
        
        if prediction_type == "bullish":
            if (self.bullish_thresholds is None or 
                self._needs_recalibration(self.bullish_thresholds)):
                self.bullish_thresholds = await self._calculate_thresholds("bullish")
            return self.bullish_thresholds
        else:
            if (self.bearish_thresholds is None or 
                self._needs_recalibration(self.bearish_thresholds)):
                self.bearish_thresholds = await self._calculate_thresholds("bearish")
            return self.bearish_thresholds
    
    def _needs_recalibration(self, thresholds: ConfidenceThresholds) -> bool:
        """Check if thresholds need recalibration"""
        days_since_update = (datetime.now() - thresholds.last_updated).days
        return days_since_update >= self.recalibration_days
    
    async def _calculate_thresholds(self, prediction_type: str) -> ConfidenceThresholds:
        """Calculate new confidence thresholds from recent historical data"""
        try:
            # Get recent predictions from database
            db = next(get_db())
            
            # Query last 90 days of predictions
            cutoff_date = datetime.now() - timedelta(days=90)
            
            query = db.query(AnalysisResult).filter(
                AnalysisResult.timestamp >= cutoff_date,
                AnalysisResult.confidence_score.isnot(None)
            )
            
            # Filter by prediction type if we have alert_type
            if prediction_type == "bullish":
                query = query.filter(AnalysisResult.alert_type == "BULLISH")
            else:
                query = query.filter(AnalysisResult.alert_type == "BEARISH")
            
            results = query.all()
            
            if len(results) < self.min_sample_size:
                logger.warning(f"Insufficient data for {prediction_type} thresholds ({len(results)} samples)")
                return self._get_default_thresholds()
            
            # Extract confidence scores (convert from percentage to 0-1 scale)
            scores = [r.confidence_score / 100.0 for r in results if r.confidence_score is not None]
            scores = np.array(scores)
            
            # Calculate percentile thresholds
            high_threshold = np.percentile(scores, 90)      # Top 10%
            medium_threshold = np.percentile(scores, 70)    # Top 30%
            speculative_threshold = np.percentile(scores, 40)  # Top 60%
            filter_threshold = speculative_threshold        # Same as speculative
            
            logger.info(f"📊 {prediction_type.title()} thresholds updated:")
            logger.info(f"   🔥 HIGH: {high_threshold:.3f} (P90)")
            logger.info(f"   📈 MEDIUM: {medium_threshold:.3f} (P70)")
            logger.info(f"   ⚡ SPECULATIVE: {speculative_threshold:.3f} (P40)")
            logger.info(f"   📊 Sample size: {len(scores)}")
            
            return ConfidenceThresholds(
                high_threshold=high_threshold,
                medium_threshold=medium_threshold,
                speculative_threshold=speculative_threshold,
                filter_threshold=filter_threshold,
                last_updated=datetime.now(),
                sample_size=len(scores)
            )
            
        except Exception as e:
            logger.error(f"Error calculating {prediction_type} thresholds: {e}")
            return self._get_default_thresholds()
    
    def _get_default_thresholds(self) -> ConfidenceThresholds:
        """Fallback default thresholds when insufficient data"""
        return ConfidenceThresholds(
            high_threshold=0.65,    # Reasonable defaults based on typical ML performance
            medium_threshold=0.58,
            speculative_threshold=0.52,
            filter_threshold=0.52,
            last_updated=datetime.now(),
            sample_size=0
        )
    
    def _calculate_percentile(self, raw_score: float, thresholds: ConfidenceThresholds, 
                            prediction_type: str) -> float:
        """Calculate percentile rank of raw score"""
        
        if raw_score >= thresholds.high_threshold:
            # Top 10% - scale from 90-100
            if thresholds.high_threshold < 1.0:
                percentile = 90 + 10 * (raw_score - thresholds.high_threshold) / (1.0 - thresholds.high_threshold)
            else:
                percentile = 95  # If threshold is at max, give high percentile
        elif raw_score >= thresholds.medium_threshold:
            # 70-90th percentile
            range_size = thresholds.high_threshold - thresholds.medium_threshold
            if range_size > 0:
                percentile = 70 + 20 * (raw_score - thresholds.medium_threshold) / range_size
            else:
                percentile = 80
        elif raw_score >= thresholds.speculative_threshold:
            # 40-70th percentile  
            range_size = thresholds.medium_threshold - thresholds.speculative_threshold
            if range_size > 0:
                percentile = 40 + 30 * (raw_score - thresholds.speculative_threshold) / range_size
            else:
                percentile = 55
        else:
            # Below 40th percentile - scale 0-40
            if thresholds.speculative_threshold > 0:
                percentile = 40 * (raw_score / thresholds.speculative_threshold)
            else:
                percentile = 20
        
        return min(100, max(0, percentile))
    
    def _convert_to_display(self, percentile: float, raw_score: float) -> Tuple[int, str, str, str]:
        """Convert percentile to user-friendly display format"""
        
        if percentile >= 90:
            display_score = int(90 + (percentile - 90))  # 90-100
            level = "HIGH"
            emoji = "🔥"
            description = "Strong conviction - multiple signals aligned"
        elif percentile >= 70:
            display_score = int(70 + (percentile - 70))  # 70-89
            level = "MEDIUM" 
            emoji = "📈"
            description = "Solid setup - favorable conditions detected"
        elif percentile >= 40:
            display_score = int(50 + (percentile - 40) * 0.67)  # 50-69
            level = "SPECULATIVE"
            emoji = "⚡"
            description = "Worth watching - early signals present"
        else:
            display_score = int(50)  # Minimum display score
            level = "LOW"
            emoji = "🔍"
            description = "Weak signals - monitor for changes"
        
        return display_score, level, emoji, description


# Global instance
_relative_scorer = None

async def get_relative_confidence_scorer() -> RelativeConfidenceScorer:
    """Get global relative confidence scorer instance"""
    global _relative_scorer
    if _relative_scorer is None:
        _relative_scorer = RelativeConfidenceScorer()
    return _relative_scorer
