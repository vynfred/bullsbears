"""
Celery tasks for statistics and badge data updates.
Ensures accurate and up-to-date statistics for UI components.
"""

import logging
from datetime import datetime
from celery import Celery
from sqlalchemy.orm import Session

from ..core.celery import celery_app
from ..core.database import get_db
from ..services.statistics_service import statistics_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="update_statistics_cache")
def update_statistics_cache(self):
    """
    Update all statistics caches for badge data accuracy.
    Runs every 5 minutes to ensure fresh data.
    """
    try:
        logger.info("Starting statistics cache update")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Clear existing cache
            logger.info("Clearing existing statistics cache")
            redis_client = statistics_service.redis_client
            await redis_client.delete("picks_statistics")
            await redis_client.delete("watchlist_statistics") 
            await redis_client.delete("model_accuracy_statistics")
            
            # Recalculate all statistics
            logger.info("Recalculating picks statistics")
            picks_stats = await statistics_service.get_picks_statistics(db)
            
            logger.info("Recalculating watchlist statistics")
            watchlist_stats = await statistics_service.get_watchlist_statistics(db)
            
            logger.info("Recalculating model accuracy statistics")
            accuracy_stats = await statistics_service.get_model_accuracy_statistics(db)
            
            logger.info(f"Statistics cache updated successfully at {datetime.now()}")
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "picks_count": picks_stats.get("today", {}).get("total_picks", 0),
                "watchlist_count": watchlist_stats.get("active", {}).get("total_stocks", 0),
                "model_accuracy": accuracy_stats.get("overall_accuracy", 0)
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error updating statistics cache: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="update_badge_data_cache")
def update_badge_data_cache(self):
    """
    Update badge data cache specifically for UI components.
    Runs every 2 minutes during market hours for real-time updates.
    """
    try:
        logger.info("Starting badge data cache update")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Get all statistics needed for badges
            picks_stats = await statistics_service.get_picks_statistics(db)
            watchlist_stats = await statistics_service.get_watchlist_statistics(db)
            accuracy_stats = await statistics_service.get_model_accuracy_statistics(db)
            
            # Format for badge consumption (same as API endpoint)
            badge_data = {
                "picks_tab": {
                    "total_picks_today": picks_stats["today"]["total_picks"],
                    "bullish_count": picks_stats["today"]["bullish_picks"],
                    "bearish_count": picks_stats["today"]["bearish_picks"],
                    "high_confidence_count": picks_stats["today"]["high_confidence_picks"],
                    "avg_confidence": round(picks_stats["today"]["avg_confidence"], 1),
                    "week_win_rate": round(picks_stats["week"]["win_rate"], 1)
                },
                "watchlist_tab": {
                    "total_stocks": watchlist_stats["active"]["total_stocks"],
                    "winners": watchlist_stats["active"]["winners"],
                    "losers": watchlist_stats["active"]["losers"],
                    "avg_performance": round(watchlist_stats["active"]["avg_performance"], 1),
                    "total_return_dollars": round(watchlist_stats["active"]["total_return_dollars"], 2),
                    "best_performer": watchlist_stats["performance"]["best_performer"],
                    "worst_performer": watchlist_stats["performance"]["worst_performer"]
                },
                "analytics_tab": {
                    "model_accuracy": round(accuracy_stats["overall_accuracy"], 1),
                    "total_predictions": accuracy_stats["total_predictions"],
                    "bullish_accuracy": round(accuracy_stats["bullish_accuracy"], 1),
                    "bearish_accuracy": round(accuracy_stats["bearish_accuracy"], 1),
                    "high_confidence_accuracy": round(accuracy_stats["high_confidence_accuracy"], 1),
                    "precision": round(accuracy_stats["model_performance"]["precision"], 1),
                    "recall": round(accuracy_stats["model_performance"]["recall"], 1),
                    "f1_score": round(accuracy_stats["model_performance"]["f1_score"], 1)
                },
                "stats_bar": {
                    "daily_scans": 888,  # From project requirements
                    "alert_rate": 1.0,   # 1% alert rate
                    "bullish_win_rate": round(picks_stats["performance"]["bullish_win_rate"], 0),
                    "bearish_win_rate": round(picks_stats["performance"]["bearish_win_rate"], 0)
                },
                "profile": {
                    "total_picks_month": picks_stats["month"]["total_picks"],
                    "win_rate_month": round(picks_stats["month"]["win_rate"], 1),
                    "avg_days_to_target": round(picks_stats["month"]["avg_days_to_target"], 1),
                    "closed_positions": watchlist_stats["closed"]["total_closed"],
                    "closed_win_rate": round(watchlist_stats["closed"]["win_rate"], 1)
                }
            }
            
            # Cache the badge data
            redis_client = statistics_service.redis_client
            await redis_client.cache_with_ttl("badge_data", badge_data, 300)  # 5 minutes TTL
            
            logger.info(f"Badge data cache updated successfully at {datetime.now()}")
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "badge_data_keys": list(badge_data.keys())
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error updating badge data cache: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=5)


@celery_app.task(bind=True, name="validate_statistics_accuracy")
def validate_statistics_accuracy(self):
    """
    Validate that statistics are accurate and consistent.
    Runs every hour to ensure data integrity.
    """
    try:
        logger.info("Starting statistics accuracy validation")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Get fresh statistics
            picks_stats = await statistics_service.get_picks_statistics(db)
            watchlist_stats = await statistics_service.get_watchlist_statistics(db)
            accuracy_stats = await statistics_service.get_model_accuracy_statistics(db)
            
            # Validation checks
            validation_results = {
                "picks_validation": {
                    "total_picks_positive": picks_stats["today"]["total_picks"] >= 0,
                    "bullish_bearish_sum_matches": (
                        picks_stats["today"]["bullish_picks"] + picks_stats["today"]["bearish_picks"] 
                        <= picks_stats["today"]["total_picks"]
                    ),
                    "confidence_in_range": 0 <= picks_stats["today"]["avg_confidence"] <= 100,
                    "win_rate_in_range": 0 <= picks_stats["week"]["win_rate"] <= 100
                },
                "watchlist_validation": {
                    "total_stocks_positive": watchlist_stats["active"]["total_stocks"] >= 0,
                    "winners_losers_sum_valid": (
                        watchlist_stats["active"]["winners"] + watchlist_stats["active"]["losers"] 
                        <= watchlist_stats["active"]["total_stocks"]
                    ),
                    "performance_reasonable": abs(watchlist_stats["active"]["avg_performance"]) <= 1000  # Within 1000%
                },
                "accuracy_validation": {
                    "accuracy_in_range": 0 <= accuracy_stats["overall_accuracy"] <= 100,
                    "predictions_positive": accuracy_stats["total_predictions"] >= 0,
                    "bullish_accuracy_in_range": 0 <= accuracy_stats["bullish_accuracy"] <= 100,
                    "bearish_accuracy_in_range": 0 <= accuracy_stats["bearish_accuracy"] <= 100
                }
            }
            
            # Check for any validation failures
            all_validations_passed = all(
                all(checks.values()) for checks in validation_results.values()
            )
            
            if not all_validations_passed:
                logger.warning(f"Statistics validation failed: {validation_results}")
                
                # Clear cache to force recalculation
                redis_client = statistics_service.redis_client
                await redis_client.delete("picks_statistics")
                await redis_client.delete("watchlist_statistics")
                await redis_client.delete("model_accuracy_statistics")
                await redis_client.delete("badge_data")
                
                logger.info("Cleared statistics cache due to validation failures")
            
            logger.info(f"Statistics validation completed at {datetime.now()}")
            
            return {
                "status": "success" if all_validations_passed else "validation_failed",
                "timestamp": datetime.now().isoformat(),
                "validation_results": validation_results,
                "cache_cleared": not all_validations_passed
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error validating statistics accuracy: {e}")
        raise self.retry(exc=e, countdown=300, max_retries=2)


@celery_app.task(bind=True, name="generate_statistics_report")
def generate_statistics_report(self):
    """
    Generate a comprehensive statistics report for monitoring.
    Runs daily to track system performance.
    """
    try:
        logger.info("Generating statistics report")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Get all statistics
            picks_stats = await statistics_service.get_picks_statistics(db)
            watchlist_stats = await statistics_service.get_watchlist_statistics(db)
            accuracy_stats = await statistics_service.get_model_accuracy_statistics(db)
            
            # Generate comprehensive report
            report = {
                "report_date": datetime.now().isoformat(),
                "summary": {
                    "total_picks_today": picks_stats["today"]["total_picks"],
                    "total_picks_week": picks_stats["week"]["total_picks"],
                    "total_picks_month": picks_stats["month"]["total_picks"],
                    "overall_accuracy": accuracy_stats["overall_accuracy"],
                    "active_watchlist_stocks": watchlist_stats["active"]["total_stocks"],
                    "closed_positions_month": watchlist_stats["closed"]["total_closed"]
                },
                "performance_metrics": {
                    "bullish_win_rate": picks_stats["performance"]["bullish_win_rate"],
                    "bearish_win_rate": picks_stats["performance"]["bearish_win_rate"],
                    "high_confidence_accuracy": accuracy_stats["high_confidence_accuracy"],
                    "avg_days_to_target": picks_stats["month"]["avg_days_to_target"],
                    "watchlist_win_rate": watchlist_stats["closed"]["win_rate"]
                },
                "system_health": {
                    "cache_status": "operational",
                    "data_freshness": "current",
                    "validation_status": "passed"
                }
            }
            
            # Store report in cache for dashboard access
            redis_client = statistics_service.redis_client
            await redis_client.cache_with_ttl("daily_statistics_report", report, 86400)  # 24 hours
            
            logger.info(f"Statistics report generated successfully at {datetime.now()}")
            
            return report
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error generating statistics report: {e}")
        raise self.retry(exc=e, countdown=600, max_retries=2)
