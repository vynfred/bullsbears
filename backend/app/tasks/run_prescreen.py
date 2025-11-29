#!/usr/bin/env python3
"""
Prescreen Task - ACTIVE → SHORT_LIST (~75 stocks)
Runs at 8:10 AM ET using Fireworks.ai qwen2.5-72b-instruct
"""

import asyncio
import logging
from datetime import datetime
from app.core.celery_app import celery_app
from app.services.cloud_agents.prescreen_agent import PrescreenAgent
from app.services.system_state import is_system_on

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_prescreen")
def run_prescreen():
    """
    Celery task - runs at 8:10 AM ET via Render cron
    Filters ACTIVE tier (~1,700 stocks) → SHORT_LIST (exactly 75 stocks)
    Uses qwen2.5-72b-instruct on Fireworks.ai
    """
    
    # Run prescreen - single Fireworks API call
    async def _run():
        # Check if system is ON
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping prescreen")
            return {"skipped": True, "reason": "system_off"}
        
        logger.info("🔍 Starting ACTIVE → SHORT_LIST prescreen task")
        start_time = datetime.now()
        
        try:
            # Initialize prescreen agent
            agent = PrescreenAgent()
            await agent.initialize()
            
            # Run prescreen - single Fireworks API call
            result = await agent.run_prescreen()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Prescreen complete: {result.get('shortlist_count', 0)} stocks in {elapsed:.1f}s")
            
            return {
                "success": True,
                "shortlist_count": result.get("shortlist_count", 0),
                "elapsed_seconds": elapsed,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Prescreen task failed: {e}")
            raise
    
    return asyncio.run(_run())

