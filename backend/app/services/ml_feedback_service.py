"""
ML Feedback Service for Target Hit Learning
Tracks when low/medium/high targets are hit and feeds this data back to ML models for continuous improvement.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.database import get_db
from ..models.analysis_results import AnalysisResult, AlertType, AlertOutcome
from ..models.watchlist import WatchlistEntry
from ..services.stock_data import StockDataService
from ..services.model_loader import ModelLoader

logger = logging.getLogger(__name__)


class TargetHitType:
    """Target hit classification for ML learning"""
    LOW_TARGET = "low_target"
    MID_TARGET = "mid_target" 
    HIGH_TARGET = "high_target"
    STOP_LOSS = "stop_loss"
    NO_TARGET = "no_target"


class MLFeedbackService:
    """Service for tracking target hits and feeding back to ML models"""
    
    def __init__(self):
        self.stock_data_service = StockDataService()
        self.model_loader = ModelLoader()
        
    async def track_target_hits(self, db: Session) -> Dict:
        """
        Track target hits for all active picks and watchlist items.
        Returns summary of target hits found.
        """
        logger.info("🎯 Starting target hit tracking for ML feedback")
        
        results = {
            "picks_checked": 0,
            "watchlist_checked": 0,
            "target_hits_found": 0,
            "new_training_samples": 0,
            "target_hit_breakdown": {
                "low": 0,
                "mid": 0, 
                "high": 0,
                "stop_loss": 0
            }
        }
        
        # Track target hits for picks (AnalysisResult)
        picks_results = await self._track_picks_target_hits(db)
        results.update(picks_results)
        
        # Track target hits for watchlist items
        watchlist_results = await self._track_watchlist_target_hits(db)
        results["watchlist_checked"] = watchlist_results["watchlist_checked"]
        results["target_hits_found"] += watchlist_results["target_hits_found"]
        results["new_training_samples"] += watchlist_results["new_training_samples"]
        
        # Update target hit breakdown
        for key in results["target_hit_breakdown"]:
            results["target_hit_breakdown"][key] += watchlist_results["target_hit_breakdown"].get(key, 0)
        
        logger.info(f"✅ Target hit tracking complete: {results}")
        return results
    
    async def _track_picks_target_hits(self, db: Session) -> Dict:
        """Track target hits for AI picks (AnalysisResult entries)"""
        
        # Get pending picks from last 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        pending_picks = db.query(AnalysisResult).filter(
            and_(
                AnalysisResult.alert_outcome == AlertOutcome.PENDING,
                AnalysisResult.timestamp >= cutoff_date,
                AnalysisResult.alert_type.in_([AlertType.BULLISH, AlertType.BEARISH])
            )
        ).all()
        
        results = {
            "picks_checked": len(pending_picks),
            "target_hits_found": 0,
            "new_training_samples": 0,
            "target_hit_breakdown": {"low": 0, "mid": 0, "high": 0, "stop_loss": 0}
        }
        
        for pick in pending_picks:
            try:
                target_hit = await self._check_pick_target_hit(pick)
                if target_hit:
                    # Update the pick with target hit information
                    await self._update_pick_with_target_hit(db, pick, target_hit)
                    
                    results["target_hits_found"] += 1
                    results["new_training_samples"] += 1
                    results["target_hit_breakdown"][target_hit["target_type"]] += 1
                    
                    logger.info(f"🎯 Target hit detected for {pick.symbol}: {target_hit}")
                    
            except Exception as e:
                logger.error(f"Error checking target hit for pick {pick.id} ({pick.symbol}): {e}")
                continue
        
        return results
    
    async def _track_watchlist_target_hits(self, db: Session) -> Dict:
        """Track target hits for watchlist items"""
        
        # Get active watchlist entries
        active_entries = db.query(WatchlistEntry).filter(
            WatchlistEntry.status == 'ACTIVE'
        ).all()
        
        results = {
            "watchlist_checked": len(active_entries),
            "target_hits_found": 0,
            "new_training_samples": 0,
            "target_hit_breakdown": {"low": 0, "mid": 0, "high": 0, "stop_loss": 0}
        }
        
        for entry in active_entries:
            try:
                target_hit = await self._check_watchlist_target_hit(entry)
                if target_hit:
                    # Update the watchlist entry
                    await self._update_watchlist_with_target_hit(db, entry, target_hit)
                    
                    # Create ML training sample
                    await self._create_ml_training_sample(db, entry, target_hit)
                    
                    results["target_hits_found"] += 1
                    results["new_training_samples"] += 1
                    results["target_hit_breakdown"][target_hit["target_type"]] += 1
                    
                    logger.info(f"🎯 Watchlist target hit: {entry.symbol} - {target_hit}")
                    
            except Exception as e:
                logger.error(f"Error checking watchlist target hit for {entry.id} ({entry.symbol}): {e}")
                continue
        
        return results
    
    async def _check_pick_target_hit(self, pick: AnalysisResult) -> Optional[Dict]:
        """Check if a pick has hit any target levels"""
        
        # Get current price
        current_price = await self.stock_data_service.get_current_price(pick.symbol)
        if not current_price:
            return None
        
        # Calculate expected targets based on confidence and alert type
        entry_price = pick.current_price or current_price
        confidence = pick.pattern_confidence or pick.confidence_score
        
        if pick.alert_type == AlertType.BULLISH:
            # Bullish targets
            low_target = entry_price * (1 + 0.10)   # 10% gain
            mid_target = entry_price * (1 + 0.20)   # 20% gain
            high_target = entry_price * (1 + 0.35)  # 35% gain
            stop_loss = entry_price * (1 - 0.08)    # 8% loss
        else:  # BEARISH
            # Bearish targets (inverted)
            low_target = entry_price * (1 - 0.10)   # 10% drop
            mid_target = entry_price * (1 - 0.20)   # 20% drop
            high_target = entry_price * (1 - 0.35)  # 35% drop
            stop_loss = entry_price * (1 + 0.08)    # 8% gain (stop loss for short)
        
        # Check which target was hit
        days_since_alert = (datetime.now() - pick.timestamp).days
        move_percent = ((current_price - entry_price) / entry_price) * 100
        
        if pick.alert_type == AlertType.BULLISH:
            if current_price >= high_target:
                return {
                    "target_type": "high",
                    "target_price": high_target,
                    "current_price": current_price,
                    "move_percent": move_percent,
                    "days_to_target": days_since_alert,
                    "confidence_at_alert": confidence,
                    "outcome": AlertOutcome.SUCCESS
                }
            elif current_price >= mid_target:
                return {
                    "target_type": "mid",
                    "target_price": mid_target,
                    "current_price": current_price,
                    "move_percent": move_percent,
                    "days_to_target": days_since_alert,
                    "confidence_at_alert": confidence,
                    "outcome": AlertOutcome.SUCCESS
                }
            elif current_price >= low_target:
                return {
                    "target_type": "low",
                    "target_price": low_target,
                    "current_price": current_price,
                    "move_percent": move_percent,
                    "days_to_target": days_since_alert,
                    "confidence_at_alert": confidence,
                    "outcome": AlertOutcome.PARTIAL
                }
            elif current_price <= stop_loss:
                return {
                    "target_type": "stop_loss",
                    "target_price": stop_loss,
                    "current_price": current_price,
                    "move_percent": move_percent,
                    "days_to_target": days_since_alert,
                    "confidence_at_alert": confidence,
                    "outcome": AlertOutcome.FAILURE
                }
        else:  # RUG
            if current_price <= high_target:
                return {
                    "target_type": "high",
                    "target_price": high_target,
                    "current_price": current_price,
                    "move_percent": abs(move_percent),
                    "days_to_target": days_since_alert,
                    "confidence_at_alert": confidence,
                    "outcome": AlertOutcome.SUCCESS
                }
            elif current_price <= mid_target:
                return {
                    "target_type": "mid",
                    "target_price": mid_target,
                    "current_price": current_price,
                    "move_percent": abs(move_percent),
                    "days_to_target": days_since_alert,
                    "confidence_at_alert": confidence,
                    "outcome": AlertOutcome.SUCCESS
                }
            elif current_price <= low_target:
                return {
                    "target_type": "low",
                    "target_price": low_target,
                    "current_price": current_price,
                    "move_percent": abs(move_percent),
                    "days_to_target": days_since_alert,
                    "confidence_at_alert": confidence,
                    "outcome": AlertOutcome.PARTIAL
                }
            elif current_price >= stop_loss:
                return {
                    "target_type": "stop_loss",
                    "target_price": stop_loss,
                    "current_price": current_price,
                    "move_percent": move_percent,
                    "days_to_target": days_since_alert,
                    "confidence_at_alert": confidence,
                    "outcome": AlertOutcome.FAILURE
                }
        
        return None
    
    async def _check_watchlist_target_hit(self, entry: WatchlistEntry) -> Optional[Dict]:
        """Check if a watchlist entry has hit target levels"""
        
        # Get current price
        current_price = await self.stock_data_service.get_current_price(entry.symbol)
        if not current_price:
            return None
        
        entry_price = entry.entry_price
        target_price = entry.target_price
        stop_loss = entry.stop_loss_price
        
        days_since_entry = (datetime.now() - entry.entry_date).days
        move_percent = ((current_price - entry_price) / entry_price) * 100
        
        # Check target hit
        if target_price and current_price >= target_price:
            return {
                "target_type": "target_hit",
                "target_price": target_price,
                "current_price": current_price,
                "move_percent": move_percent,
                "days_to_target": days_since_entry,
                "confidence_at_entry": entry.ai_confidence_score,
                "outcome": "SUCCESS"
            }
        
        # Check stop loss hit
        if stop_loss and current_price <= stop_loss:
            return {
                "target_type": "stop_loss",
                "target_price": stop_loss,
                "current_price": current_price,
                "move_percent": move_percent,
                "days_to_target": days_since_entry,
                "confidence_at_entry": entry.ai_confidence_score,
                "outcome": "FAILURE"
            }
        
        return None
    
    async def _update_pick_with_target_hit(self, db: Session, pick: AnalysisResult, target_hit: Dict):
        """Update pick with target hit information"""
        
        pick.alert_outcome = target_hit["outcome"]
        pick.actual_move_percent = target_hit["move_percent"]
        pick.days_to_move = target_hit["days_to_target"]
        pick.outcome_timestamp = datetime.now()
        pick.outcome_notes = f"Target hit: {target_hit['target_type']} at ${target_hit['current_price']:.2f}"
        
        db.commit()
    
    async def _update_watchlist_with_target_hit(self, db: Session, entry: WatchlistEntry, target_hit: Dict):
        """Update watchlist entry with target hit information"""
        
        entry.current_price = target_hit["current_price"]
        entry.current_return_percent = target_hit["move_percent"]
        entry.status = 'CLOSED'
        entry.is_winner = target_hit["outcome"] == "SUCCESS"
        entry.exit_price = target_hit["current_price"]
        entry.exit_date = datetime.now()
        entry.exit_reason = f"TARGET_HIT_{target_hit['target_type'].upper()}"
        entry.final_return_percent = target_hit["move_percent"]
        entry.last_price_update = datetime.now()
        
        db.commit()
    
    async def _create_ml_training_sample(self, db: Session, entry: WatchlistEntry, target_hit: Dict):
        """Create ML training sample from target hit data"""
        
        # This would create a training sample for the ML model
        # Implementation depends on your ML training pipeline
        logger.info(f"Creating ML training sample for {entry.symbol} target hit: {target_hit}")
        
        # TODO: Implement ML training sample creation
        # This should feed into your LightGBM/RandomForest retraining pipeline
        pass


# Global instance
ml_feedback_service = MLFeedbackService()
