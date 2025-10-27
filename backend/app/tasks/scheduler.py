"""
Background task scheduler for automated performance updates.
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional

from .performance_updater import run_daily_performance_update, run_hourly_performance_update

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Simple task scheduler for performance updates."""
    
    def __init__(self):
        self.running = False
        self.tasks = []
    
    async def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting task scheduler")
        
        # Start background tasks
        self.tasks = [
            asyncio.create_task(self._daily_update_loop()),
            asyncio.create_task(self._hourly_update_loop())
        ]
        
        logger.info("Task scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return
        
        logger.info("Stopping task scheduler")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        logger.info("Task scheduler stopped")
    
    async def _daily_update_loop(self):
        """Run daily performance updates at 6 AM ET."""
        target_hour = 11  # 6 AM ET = 11 AM UTC (approximate)
        
        while self.running:
            try:
                now = datetime.utcnow()
                
                # Check if it's time for daily update (6 AM ET)
                if now.hour == target_hour and now.minute < 5:
                    logger.info("Running scheduled daily performance update")
                    try:
                        result = await run_daily_performance_update()
                        logger.info(f"Daily update completed: {result}")
                    except Exception as e:
                        logger.error(f"Daily update failed: {str(e)}")
                    
                    # Sleep for 1 hour to avoid running multiple times
                    await asyncio.sleep(3600)
                else:
                    # Check every 5 minutes
                    await asyncio.sleep(300)
                    
            except asyncio.CancelledError:
                logger.info("Daily update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in daily update loop: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _hourly_update_loop(self):
        """Run hourly performance updates during market hours."""
        while self.running:
            try:
                now = datetime.utcnow()
                
                # Run hourly updates at the top of each hour during market hours
                if now.minute < 5:
                    logger.info("Running scheduled hourly performance update")
                    try:
                        result = await run_hourly_performance_update()
                        logger.info(f"Hourly update completed: {result}")
                    except Exception as e:
                        logger.error(f"Hourly update failed: {str(e)}")
                    
                    # Sleep for 1 hour
                    await asyncio.sleep(3600)
                else:
                    # Sleep until next hour
                    minutes_to_next_hour = 60 - now.minute
                    await asyncio.sleep(minutes_to_next_hour * 60)
                    
            except asyncio.CancelledError:
                logger.info("Hourly update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in hourly update loop: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying


# Global scheduler instance
scheduler = TaskScheduler()


async def start_scheduler():
    """Start the background task scheduler."""
    await scheduler.start()


async def stop_scheduler():
    """Stop the background task scheduler."""
    await scheduler.stop()
