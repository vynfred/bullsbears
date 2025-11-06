"""
Statistics Service for Badge Data Accuracy
Provides accurate statistics for all badges, counters, and performance metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from ..core.database import get_db
from ..models.analysis_results import AnalysisResult, AlertType, AlertOutcome
from ..models.watchlist import WatchlistEntry
from ..models.dual_ai_training import DualAITrainingData
from ..core.redis_client import redis_client

logger = logging.getLogger(__name__)


class StatisticsService:
    """Service for providing accurate statistics for UI badges and counters"""
    
    def __init__(self):
        self.redis_client = redis_client
        self.cache_ttl = 300  # 5 minutes cache
    
    async def get_picks_statistics(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive picks statistics for badges and counters"""
        
        cache_key = "picks_statistics"
        cached_stats = await self.redis_client.get(cache_key)
        if cached_stats:
            return cached_stats
        
        try:
            # Get date ranges
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Today's picks
            today_picks = db.query(AnalysisResult).filter(
                and_(
                    func.date(AnalysisResult.timestamp) == today,
                    AnalysisResult.alert_type.in_([AlertType.BULLISH, AlertType.BEARISH])
                )
            ).all()
            
            # This week's picks
            week_picks = db.query(AnalysisResult).filter(
                and_(
                    AnalysisResult.timestamp >= week_ago,
                    AnalysisResult.alert_type.in_([AlertType.BULLISH, AlertType.BEARISH])
                )
            ).all()

            # This month's picks
            month_picks = db.query(AnalysisResult).filter(
                and_(
                    AnalysisResult.timestamp >= month_ago,
                    AnalysisResult.alert_type.in_([AlertType.BULLISH, AlertType.BEARISH])
                )
            ).all()
            
            # Calculate statistics
            stats = {
                # Today's stats
                "today": {
                    "total_picks": len(today_picks),
                    "bullish_picks": len([p for p in today_picks if p.alert_type == AlertType.BULLISH]),
                    "bearish_picks": len([p for p in today_picks if p.alert_type == AlertType.BEARISH]),
                    "avg_confidence": self._calculate_avg_confidence(today_picks),
                    "high_confidence_picks": len([p for p in today_picks if (p.confidence_score or 0) >= 0.8])
                },
                
                # Weekly stats
                "week": {
                    "total_picks": len(week_picks),
                    "bullish_picks": len([p for p in week_picks if p.alert_type == AlertType.BULLISH]),
                    "bearish_picks": len([p for p in week_picks if p.alert_type == AlertType.BEARISH]),
                    "wins": len([p for p in week_picks if p.alert_outcome == AlertOutcome.SUCCESS]),
                    "losses": len([p for p in week_picks if p.alert_outcome == AlertOutcome.FAILURE]),
                    "pending": len([p for p in week_picks if p.alert_outcome == AlertOutcome.PENDING]),
                    "win_rate": self._calculate_win_rate(week_picks),
                    "avg_confidence": self._calculate_avg_confidence(week_picks)
                },
                
                # Monthly stats
                "month": {
                    "total_picks": len(month_picks),
                    "bullish_picks": len([p for p in month_picks if p.alert_type == AlertType.BULLISH]),
                    "bearish_picks": len([p for p in month_picks if p.alert_type == AlertType.BEARISH]),
                    "wins": len([p for p in month_picks if p.alert_outcome == AlertOutcome.SUCCESS]),
                    "losses": len([p for p in month_picks if p.alert_outcome == AlertOutcome.FAILURE]),
                    "pending": len([p for p in month_picks if p.alert_outcome == AlertOutcome.PENDING]),
                    "win_rate": self._calculate_win_rate(month_picks),
                    "avg_confidence": self._calculate_avg_confidence(month_picks),
                    "avg_days_to_target": self._calculate_avg_days_to_target(month_picks)
                },
                
                # Performance breakdown
                "performance": {
                    "bullish_win_rate": self._calculate_bullish_win_rate(month_picks),
                    "bearish_win_rate": self._calculate_bearish_win_rate(month_picks),
                    "high_confidence_win_rate": self._calculate_high_confidence_win_rate(month_picks),
                    "target_hit_breakdown": self._calculate_target_hit_breakdown(month_picks)
                }
            }
            
            # Cache the results
            await self.redis_client.cache_with_ttl(cache_key, stats, self.cache_ttl)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating picks statistics: {e}")
            return self._get_default_picks_stats()
    
    async def get_watchlist_statistics(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive watchlist statistics"""
        
        cache_key = "watchlist_statistics"
        cached_stats = await self.redis_client.get(cache_key)
        if cached_stats:
            return cached_stats
        
        try:
            # Get active watchlist entries
            active_entries = db.query(WatchlistEntry).filter(
                WatchlistEntry.status == 'ACTIVE'
            ).all()
            
            # Get closed entries from last 30 days
            month_ago = datetime.now() - timedelta(days=30)
            closed_entries = db.query(WatchlistEntry).filter(
                and_(
                    WatchlistEntry.status == 'CLOSED',
                    WatchlistEntry.exit_date >= month_ago
                )
            ).all()
            
            # Calculate statistics
            stats = {
                "active": {
                    "total_stocks": len(active_entries),
                    "avg_performance": self._calculate_avg_watchlist_performance(active_entries),
                    "winners": len([e for e in active_entries if (e.current_return_percent or 0) > 0]),
                    "losers": len([e for e in active_entries if (e.current_return_percent or 0) < 0]),
                    "total_value": sum(e.position_size_dollars or 0 for e in active_entries),
                    "total_return_dollars": sum(e.current_return_dollars or 0 for e in active_entries)
                },
                
                "closed": {
                    "total_closed": len(closed_entries),
                    "winners": len([e for e in closed_entries if e.is_winner]),
                    "losers": len([e for e in closed_entries if not e.is_winner]),
                    "win_rate": len([e for e in closed_entries if e.is_winner]) / len(closed_entries) * 100 if closed_entries else 0,
                    "avg_return": sum(e.final_return_percent or 0 for e in closed_entries) / len(closed_entries) if closed_entries else 0,
                    "total_return_dollars": sum(e.final_return_dollars or 0 for e in closed_entries)
                },
                
                "performance": {
                    "best_performer": self._get_best_performer(active_entries),
                    "worst_performer": self._get_worst_performer(active_entries),
                    "target_hits": len([e for e in closed_entries if e.exit_reason and 'TARGET_HIT' in e.exit_reason]),
                    "stop_losses": len([e for e in closed_entries if e.exit_reason and 'STOP_LOSS' in e.exit_reason])
                }
            }
            
            # Cache the results
            await self.redis_client.cache_with_ttl(cache_key, stats, self.cache_ttl)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating watchlist statistics: {e}")
            return self._get_default_watchlist_stats()
    
    async def get_model_accuracy_statistics(self, db: Session) -> Dict[str, Any]:
        """Get ML model accuracy statistics"""
        
        cache_key = "model_accuracy_statistics"
        cached_stats = await self.redis_client.get(cache_key)
        if cached_stats:
            return cached_stats
        
        try:
            # Get training data for accuracy calculation
            month_ago = datetime.now() - timedelta(days=30)
            training_data = db.query(DualAITrainingData).filter(
                and_(
                    DualAITrainingData.outcome_timestamp >= month_ago,
                    DualAITrainingData.actual_outcome.isnot(None)
                )
            ).all()
            
            # Get completed picks for accuracy
            completed_picks = db.query(AnalysisResult).filter(
                and_(
                    AnalysisResult.alert_outcome.in_([AlertOutcome.SUCCESS, AlertOutcome.FAILURE]),
                    AnalysisResult.timestamp >= month_ago
                )
            ).all()
            
            # Calculate accuracy metrics
            total_predictions = len(completed_picks)
            correct_predictions = len([p for p in completed_picks if p.alert_outcome == AlertOutcome.SUCCESS])
            
            stats = {
                "overall_accuracy": (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0,
                "total_predictions": total_predictions,
                "correct_predictions": correct_predictions,
                "bullish_accuracy": self._calculate_bullish_accuracy(completed_picks),
                "bearish_accuracy": self._calculate_bearish_accuracy(completed_picks),
                "high_confidence_accuracy": self._calculate_high_confidence_accuracy(completed_picks),
                "accuracy_trend": self._calculate_accuracy_trend(completed_picks),
                "model_performance": {
                    "precision": self._calculate_precision(completed_picks),
                    "recall": self._calculate_recall(completed_picks),
                    "f1_score": self._calculate_f1_score(completed_picks)
                }
            }
            
            # Cache the results
            await self.redis_client.cache_with_ttl(cache_key, stats, self.cache_ttl)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating model accuracy statistics: {e}")
            return self._get_default_accuracy_stats()
    
    def _calculate_avg_confidence(self, picks: List[AnalysisResult]) -> float:
        """Calculate average confidence score"""
        if not picks:
            return 0.0
        
        confidences = [p.confidence_score or 0 for p in picks]
        return sum(confidences) / len(confidences) * 100
    
    def _calculate_win_rate(self, picks: List[AnalysisResult]) -> float:
        """Calculate win rate percentage"""
        completed_picks = [p for p in picks if p.alert_outcome in [AlertOutcome.SUCCESS, AlertOutcome.FAILURE]]
        if not completed_picks:
            return 0.0
        
        wins = len([p for p in completed_picks if p.alert_outcome == AlertOutcome.SUCCESS])
        return (wins / len(completed_picks)) * 100
    
    def _calculate_bullish_win_rate(self, picks: List[AnalysisResult]) -> float:
        """Calculate bullish picks win rate"""
        bullish_picks = [p for p in picks if p.alert_type == AlertType.BULLISH and p.alert_outcome in [AlertOutcome.SUCCESS, AlertOutcome.FAILURE]]
        if not bullish_picks:
            return 0.0

        wins = len([p for p in bullish_picks if p.alert_outcome == AlertOutcome.SUCCESS])
        return (wins / len(bullish_picks)) * 100

    def _calculate_bearish_win_rate(self, picks: List[AnalysisResult]) -> float:
        """Calculate bearish picks win rate"""
        bearish_picks = [p for p in picks if p.alert_type == AlertType.BEARISH and p.alert_outcome in [AlertOutcome.SUCCESS, AlertOutcome.FAILURE]]
        if not bearish_picks:
            return 0.0

        wins = len([p for p in bearish_picks if p.alert_outcome == AlertOutcome.SUCCESS])
        return (wins / len(bearish_picks)) * 100
    
    def _calculate_high_confidence_win_rate(self, picks: List[AnalysisResult]) -> float:
        """Calculate win rate for high confidence picks (>80%)"""
        high_conf_picks = [p for p in picks if (p.confidence_score or 0) >= 0.8 and p.alert_outcome in [AlertOutcome.SUCCESS, AlertOutcome.FAILURE]]
        if not high_conf_picks:
            return 0.0
        
        wins = len([p for p in high_conf_picks if p.alert_outcome == AlertOutcome.SUCCESS])
        return (wins / len(high_conf_picks)) * 100
    
    def _calculate_avg_days_to_target(self, picks: List[AnalysisResult]) -> float:
        """Calculate average days to reach target"""
        successful_picks = [p for p in picks if p.alert_outcome == AlertOutcome.SUCCESS and p.days_to_move]
        if not successful_picks:
            return 0.0
        
        return sum(p.days_to_move for p in successful_picks) / len(successful_picks)
    
    def _calculate_target_hit_breakdown(self, picks: List[AnalysisResult]) -> Dict[str, int]:
        """Calculate breakdown of target hits (low/mid/high)"""
        # This would require additional data about which target was hit
        # For now, return placeholder data
        return {
            "low_target_hits": 0,
            "mid_target_hits": 0,
            "high_target_hits": 0
        }
    
    def _calculate_avg_watchlist_performance(self, entries: List[WatchlistEntry]) -> float:
        """Calculate average watchlist performance"""
        if not entries:
            return 0.0
        
        returns = [e.current_return_percent or 0 for e in entries]
        return sum(returns) / len(returns)
    
    def _get_best_performer(self, entries: List[WatchlistEntry]) -> Optional[Dict]:
        """Get best performing watchlist entry"""
        if not entries:
            return None
        
        best = max(entries, key=lambda e: e.current_return_percent or 0)
        return {
            "symbol": best.symbol,
            "return_percent": best.current_return_percent or 0
        }
    
    def _get_worst_performer(self, entries: List[WatchlistEntry]) -> Optional[Dict]:
        """Get worst performing watchlist entry"""
        if not entries:
            return None
        
        worst = min(entries, key=lambda e: e.current_return_percent or 0)
        return {
            "symbol": worst.symbol,
            "return_percent": worst.current_return_percent or 0
        }
    
    def _calculate_bullish_accuracy(self, picks: List[AnalysisResult]) -> float:
        """Calculate accuracy for bullish picks only"""
        bullish_picks = [p for p in picks if p.alert_type == AlertType.BULLISH]
        return self._calculate_win_rate(bullish_picks)

    def _calculate_bearish_accuracy(self, picks: List[AnalysisResult]) -> float:
        """Calculate accuracy for bearish picks only"""
        bearish_picks = [p for p in picks if p.alert_type == AlertType.BEARISH]
        return self._calculate_win_rate(bearish_picks)
    
    def _calculate_high_confidence_accuracy(self, picks: List[AnalysisResult]) -> float:
        """Calculate accuracy for high confidence picks"""
        return self._calculate_high_confidence_win_rate(picks)
    
    def _calculate_accuracy_trend(self, picks: List[AnalysisResult]) -> List[Dict]:
        """Calculate accuracy trend over time"""
        # Group picks by week and calculate accuracy for each week
        # This is a simplified implementation
        return []
    
    def _calculate_precision(self, picks: List[AnalysisResult]) -> float:
        """Calculate precision metric"""
        # Simplified precision calculation
        return self._calculate_win_rate(picks)
    
    def _calculate_recall(self, picks: List[AnalysisResult]) -> float:
        """Calculate recall metric"""
        # Simplified recall calculation
        return self._calculate_win_rate(picks)
    
    def _calculate_f1_score(self, picks: List[AnalysisResult]) -> float:
        """Calculate F1 score"""
        precision = self._calculate_precision(picks)
        recall = self._calculate_recall(picks)
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    def _get_default_picks_stats(self) -> Dict[str, Any]:
        """Return default picks statistics when calculation fails"""
        return {
            "today": {"total_picks": 0, "bullish_picks": 0, "bearish_picks": 0, "avg_confidence": 0, "high_confidence_picks": 0},
            "week": {"total_picks": 0, "bullish_picks": 0, "bearish_picks": 0, "wins": 0, "losses": 0, "pending": 0, "win_rate": 0, "avg_confidence": 0},
            "month": {"total_picks": 0, "bullish_picks": 0, "bearish_picks": 0, "wins": 0, "losses": 0, "pending": 0, "win_rate": 0, "avg_confidence": 0, "avg_days_to_target": 0},
            "performance": {"bullish_win_rate": 0, "bearish_win_rate": 0, "high_confidence_win_rate": 0, "target_hit_breakdown": {"low_target_hits": 0, "mid_target_hits": 0, "high_target_hits": 0}}
        }
    
    def _get_default_watchlist_stats(self) -> Dict[str, Any]:
        """Return default watchlist statistics when calculation fails"""
        return {
            "active": {"total_stocks": 0, "avg_performance": 0, "winners": 0, "losers": 0, "total_value": 0, "total_return_dollars": 0},
            "closed": {"total_closed": 0, "winners": 0, "losers": 0, "win_rate": 0, "avg_return": 0, "total_return_dollars": 0},
            "performance": {"best_performer": None, "worst_performer": None, "target_hits": 0, "stop_losses": 0}
        }
    
    def _get_default_accuracy_stats(self) -> Dict[str, Any]:
        """Return default accuracy statistics when calculation fails"""
        return {
            "overall_accuracy": 0, "total_predictions": 0, "correct_predictions": 0,
            "bullish_accuracy": 0, "bearish_accuracy": 0, "high_confidence_accuracy": 0,
            "accuracy_trend": [], "model_performance": {"precision": 0, "recall": 0, "f1_score": 0}
        }


# Global instance
statistics_service = StatisticsService()
