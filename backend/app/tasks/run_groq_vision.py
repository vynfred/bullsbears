#!/usr/bin/env python3
"""
Vision Analysis Task - Chart pattern detection
Runs at 8:16 AM ET using Groq Llama-3.2-11B-Vision
"""

import asyncio
import logging
from datetime import datetime
from app.core.celery import celery_app
from app.services.cloud_agents.vision_agent import VisionAgent
from app.core.database import get_asyncpg_pool
from app.services.system_state import SystemState

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_groq_vision")
def run_groq_vision():
    """
    Celery task - runs at 8:16 AM ET
    Analyzes 75 SHORT_LIST charts for 6 pattern flags
    Uses Groq Llama-3.2-11B-Vision API (75 parallel calls)
    """
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping vision analysis")
            return {"skipped": True, "reason": "system_off"}
        
        logger.info("👁️ Starting vision analysis task")
        start_time = datetime.now()
        
        try:
            db = await get_asyncpg_pool()
            
            # Get today's SHORT_LIST charts
            async with db.acquire() as conn:
                charts = await conn.fetch("""
                    SELECT sc.symbol, sc.chart_data as chart_base64
                    FROM stock_charts sc
                    JOIN shortlist_candidates sl ON sc.symbol = sl.symbol
                    WHERE sl.date::date = CURRENT_DATE
                    ORDER BY sl.rank
                    LIMIT 75
                """)
            
            if not charts:
                logger.warning("No charts found for today's SHORT_LIST")
                return {"success": False, "reason": "no_charts"}
            
            charts_list = [dict(c) for c in charts]
            logger.info(f"Analyzing {len(charts_list)} charts via Groq Vision API")
            
            # Run vision analysis
            agent = VisionAgent()
            results = await agent.analyze_batch(charts_list)
            
            # Store results in database
            async with db.acquire() as conn:
                for result in results:
                    await conn.execute("""
                        UPDATE shortlist_candidates
                        SET vision_flags = $1, vision_analyzed_at = NOW()
                        WHERE symbol = $2 AND date::date = CURRENT_DATE
                    """, result.get("vision_flags"), result.get("symbol"))
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Vision analysis complete: {len(results)} stocks in {elapsed:.1f}s")
            
            return {
                "success": True,
                "analyzed_count": len(results),
                "elapsed_seconds": elapsed,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Vision analysis task failed: {e}")
            raise
    
    return asyncio.run(_run())

