"""
BullsBears AI - Learning System Tasks
Celery tasks for automated learning and prompt optimization
"""

import asyncio
import logging
from datetime import datetime
from celery import Celery

from ..services.learning_manager import LearningManager

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery('bullsbears_learning')

@celery_app.task(name='weekly_learning_cycle')
def weekly_learning_cycle():
    """
    Weekly learning cycle task
    Runs every Sunday at 4:01 AM to analyze the past week's performance
    """
    
    logger.info("Starting weekly learning cycle...")
    
    try:
        # Run async learning cycle
        result = asyncio.run(_run_learning_cycle())
        
        if result["success"]:
            logger.info(f"Weekly learning cycle completed successfully: {result}")
            return {
                "status": "success",
                "insights_generated": result.get("insights_generated", 0),
                "updates_applied": result.get("updates_applied", 0),
                "duration": result.get("duration_seconds", 0)
            }
        else:
            logger.error(f"Weekly learning cycle failed: {result}")
            return {
                "status": "failed",
                "error": result.get("error", "Unknown error")
            }
            
    except Exception as e:
        logger.error(f"Weekly learning cycle task error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@celery_app.task(name='monthly_deep_learning')
def monthly_deep_learning():
    """
    Monthly deep learning cycle
    Runs first Sunday of each month at 4:02 AM for comprehensive analysis
    """
    
    logger.info("Starting monthly deep learning cycle...")
    
    try:
        # Run async deep learning cycle with more historical data
        result = asyncio.run(_run_learning_cycle(days_back=90))
        
        if result["success"]:
            logger.info(f"Monthly deep learning cycle completed: {result}")
            return {
                "status": "success",
                "insights_generated": result.get("insights_generated", 0),
                "updates_applied": result.get("updates_applied", 0),
                "duration": result.get("duration_seconds", 0),
                "type": "deep_learning"
            }
        else:
            logger.error(f"Monthly deep learning cycle failed: {result}")
            return {
                "status": "failed",
                "error": result.get("error", "Unknown error")
            }
            
    except Exception as e:
        logger.error(f"Monthly deep learning cycle task error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@celery_app.task(name='learning_health_check')
def learning_health_check():
    """
    Daily learning system health check
    Runs daily at 3:00 AM to verify learning system status
    """
    
    logger.info("Running learning system health check...")
    
    try:
        result = asyncio.run(_check_learning_health())
        
        logger.info(f"Learning health check completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Learning health check error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def _run_learning_cycle(days_back: int = 7) -> dict:
    """Run the learning cycle asynchronously"""
    
    manager = LearningManager()
    await manager.initialize()
    
    return await manager.run_learning_cycle(days_back=days_back)

async def _check_learning_health() -> dict:
    """Check learning system health"""
    
    try:
        manager = LearningManager()
        await manager.initialize()
        
        # Get recent learning progress
        progress = await manager.get_learning_progress(days_back=30)
        
        if "error" in progress:
            return {
                "status": "unhealthy",
                "error": progress["error"]
            }
        
        # Check if learning system is active
        recent_cycles = progress.get("total_learning_cycles", 0)
        recent_updates = progress.get("total_prompt_updates", 0)
        
        if recent_cycles == 0:
            return {
                "status": "warning",
                "message": "No learning cycles in the past 30 days"
            }
        
        return {
            "status": "healthy",
            "recent_cycles": recent_cycles,
            "recent_updates": recent_updates,
            "avg_insights": progress.get("avg_insights_per_cycle", 0),
            "most_improved_agents": progress.get("most_improved_agents", [])
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Celery beat schedule for automated learning
celery_app.conf.beat_schedule = {
    'weekly-learning-cycle': {
        'task': 'weekly_learning_cycle',
        'schedule': {
            'minute': 1,
            'hour': 4,
            'day_of_week': 0,  # Sunday
        },
    },
    'monthly-deep-learning': {
        'task': 'monthly_deep_learning', 
        'schedule': {
            'minute': 2,
            'hour': 4,
            'day_of_month': '1-7',  # First week of month
            'day_of_week': 0,       # Sunday
        },
    },
    'learning-health-check': {
        'task': 'learning_health_check',
        'schedule': {
            'minute': 0,
            'hour': 3,  # 3:00 AM daily
        },
    },
}

celery_app.conf.timezone = 'UTC'
