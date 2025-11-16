#!/usr/bin/env python3
"""
Social Sentiment Task - Social media + news + events analysis
Runs at 8:17 AM ET using Grok API
"""

import asyncio
import logging
from datetime import datetime
from app.core.celery import celery_app
from app.services.cloud_agents.social_agent import SocialContextAgent
from app.core.database import get_asyncpg_pool
from app.services.system_state import SystemState

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_grok_social")
def run_grok_social():
    """
    Celery task - runs at 8:17 AM ET
    Analyzes 75 SHORT_LIST stocks for social sentiment, news, events
    Uses Grok API (75 parallel calls)
    """
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping social analysis")
            return {"skipped": True, "reason": "system_off"}
        
        logger.info("🌐 Starting social sentiment analysis task")
        start_time = datetime.now()
        
        try:
            db = await get_asyncpg_pool()
            
            # Get today's SHORT_LIST symbols
            async with db.acquire() as conn:
                symbols = await conn.fetch("""
                    SELECT symbol
                    FROM shortlist_candidates
                    WHERE date::date = CURRENT_DATE
                    ORDER BY rank
                    LIMIT 75
                """)
            
            if not symbols:
                logger.warning("No SHORT_LIST found for today")
                return {"success": False, "reason": "no_shortlist"}
            
            symbols_list = [{"symbol": s["symbol"]} for s in symbols]
            logger.info(f"Analyzing {len(symbols_list)} stocks via Grok API")
            
            # Run social analysis
            agent = SocialContextAgent()
            results = await agent.analyze_batch(symbols_list)
            
            # Store results in database
            async with db.acquire() as conn:
                for result in results:
                    await conn.execute("""
                        UPDATE shortlist_candidates
                        SET 
                            social_score = $1,
                            social_headlines = $2,
                            social_events = $3,
                            polymarket_prob = $4,
                            social_analyzed_at = NOW()
                        WHERE symbol = $5 AND date::date = CURRENT_DATE
                    """, 
                        result.get("social_score", 0),
                        result.get("headlines", []),
                        result.get("events", []),
                        result.get("polymarket_prob"),
                        result.get("symbol")
                    )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Social analysis complete: {len(results)} stocks in {elapsed:.1f}s")
            
            return {
                "success": True,
                "analyzed_count": len(results),
                "elapsed_seconds": elapsed,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Social analysis task failed: {e}")
            raise
    
    return asyncio.run(_run())

