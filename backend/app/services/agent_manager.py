#!/usr/bin/env python3
"""
BullsBears Agent Manager – Lean & Lethal (v3.2 – November 10, 2025)
Phase 0 → 5: Kill Switch → Prescreen → Charts → Vision → Social → Arbitrator
"""

import asyncio
import logging
import time
from datetime import datetime, date
from typing import List, Dict, Any

from .kill_switch_service import KillSwitchService
from .stock_classification_service import get_active_tickers
from .agents.prescreen_agent import get_prescreen_agent
from .chart_generator import get_chart_generator
from .agents.vision_agent import get_vision_agent
from .agents.social_agent import get_social_agent
from .agents.arbitrator_agent import get_arbitrator_agent
from .candidate_tracking_service import get_candidate_tracking_service

logger = logging.getLogger(__name__)

class AgentManager:
    """One job: 3:00 AM → 3:25 AM → 3–6 picks in your inbox."""

    def __init__(self):
        self.kill_switch = KillSwitchService()
        self.tracking = None

    async def initialize(self):
        self.tracking = await get_candidate_tracking_service()

    async def run_daily_pipeline(self) -> Dict[str, Any]:
        start = time.time()
        today = date.today()
        logger.info(f"Daily pipeline START – {today}")

        # Phase 0: Kill Switch
        if await self.kill_switch.is_active():
            logger.warning("KILL SWITCH ACTIVE – no picks today")
            return {"picks": [], "reason": "kill_switch", "duration": time.time() - start}

        # Phase 1: Prescreen – ACTIVE (~1,700) → exactly 75
        logger.info("Phase 1: FinMA-7b prescreen")
        async with get_prescreen_agent() as prescreen:
            active = await get_active_tickers()  # ~1,700
            shortlist = await prescreen.screen_active_to_shortlist(active)
        logger.info(f"Phase 1 DONE – {len(shortlist)} in SHORT_LIST")

        # Phase 2: Charts
        logger.info("Phase 2: Generating 75 charts")
        charts = await self.chart_gen.generate_batch(shortlist)
        logger.info("Phase 2 DONE")

        # Phase 3: Vision
        logger.info("Phase 3: Groq Vision – 75 charts")
        async with get_vision_agent() as vision:
            vision_results = await vision.analyze_batch(charts)
        logger.info("Phase 3 DONE")

        # Phase 4: Social + Context
        logger.info("Phase 4: Grok Social + News + Polymarket")
        async with get_social_agent() as social:
            social_results = await social.analyze_batch(shortlist)
        logger.info("Phase 4 DONE")

        # Phase 5: Final Arbitrator (rotating)
        logger.info("Phase 5: Rotating Arbitrator")
        async with get_arbitrator_agent() as arb:
            final_picks = await arb.arbitrate(
                shortlist=shortlist,
                vision=vision_results,
                social=social_results
            )
        logger.info(f"Phase 5 DONE – {len(final_picks)} final picks")

        # Store full 75 for LearnerAgent
        await self.tracking.store_shortlist(shortlist, vision_results, social_results, final_picks)

        duration = time.time() - start
        logger.info(f"Pipeline COMPLETE – {duration:.1f}s")

        return {
            "date": today.isoformat(),
            "picks": final_picks,
            "shortlist_count": len(shortlist),
            "duration_seconds": round(duration, 1),
            "timestamp": datetime.now().isoformat()
        }


# Global singleton
_manager = None

async def get_agent_manager() -> AgentManager:
    global _manager
    if _manager is None:
        _manager = AgentManager()
        await _manager.initialize()
    return _manager


# Celery beat task
@celery_app.task
async def daily_pipeline_task():
    async with get_agent_manager() as manager:
        result = await manager.run_daily_pipeline()
        # Send to Discord/email/webhook here
        await send_alert(result)