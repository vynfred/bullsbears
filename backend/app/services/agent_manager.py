#!/usr/bin/env python3
"""
BullsBears Agent Manager - Orchestrates all AI agents
Single entry point for running pipeline steps
"""

import logging
from datetime import date, timedelta
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)


class AgentManager:
    """Orchestrates all AI agents in the BullsBears pipeline"""
    
    def __init__(self):
        self.db = None
    
    async def initialize(self):
        """Initialize database connection"""
        self.db = await get_asyncpg_pool()
    
    async def run_prescreen_agent(self) -> dict:
        """Run prescreen: ACTIVE → SHORT_LIST (~75 stocks)"""
        from app.services.cloud_agents.prescreen_agent import PrescreenAgent
        
        agent = PrescreenAgent()
        await agent.initialize()
        result = await agent.run_prescreen()
        
        return result
    
    async def run_vision_agent(self) -> dict:
        """Run vision analysis on shortlist charts"""
        from app.services.cloud_agents.vision_agent import run_vision_analysis
        
        if not self.db:
            self.db = await get_asyncpg_pool()
        
        # Get charts from shortlist
        async with self.db.acquire() as conn:
            # Get latest shortlist date
            latest = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")
            if not latest or not latest['latest_date']:
                return {"status": "error", "message": "No shortlist found"}
            
            shortlist_date = latest['latest_date']
            
            # Get charts for analysis
            charts = await conn.fetch("""
                SELECT symbol, chart_url
                FROM shortlist_candidates
                WHERE date = $1 AND chart_url IS NOT NULL
            """, shortlist_date)
        
        if not charts:
            return {"status": "error", "message": "No charts found"}
        
        chart_list = [{"symbol": c["symbol"], "chart_url": c["chart_url"]} for c in charts]
        results = await run_vision_analysis(chart_list)
        
        success = sum(1 for r in results if any(v for k, v in r["vision_flags"].items() if isinstance(v, bool) and v))
        return {"status": "success", "analyzed": len(results), "with_flags": success}
    
    async def run_social_agent(self) -> dict:
        """Run social/sentiment analysis via Grok"""
        from app.services.cloud_agents.social_agent import run_social_analysis
        
        if not self.db:
            self.db = await get_asyncpg_pool()
        
        # Get shortlist symbols
        async with self.db.acquire() as conn:
            latest = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")
            if not latest or not latest['latest_date']:
                return {"status": "error", "message": "No shortlist found"}
            
            shortlist_date = latest['latest_date']
            
            symbols = await conn.fetch("""
                SELECT symbol FROM shortlist_candidates WHERE date = $1
            """, shortlist_date)
        
        if not symbols:
            return {"status": "error", "message": "No symbols found"}
        
        symbol_list = [{"symbol": s["symbol"]} for s in symbols]
        results = await run_social_analysis(symbol_list)
        
        with_scores = sum(1 for r in results if r.get("social_score", 0) != 0)
        return {"status": "success", "analyzed": len(results), "with_scores": with_scores}
    
    async def run_arbitrator_agent(self) -> dict:
        """Run final arbitrator with Fib targets"""
        from app.tasks.run_arbitrator import _run_arbitrator_async
        
        result = await _run_arbitrator_async()
        return result
    
    async def run_learner_agent(self) -> dict:
        """Run weekly learner to update weights"""
        from app.services.cloud_agents.learner_agent import run_weekly_learner
        
        today = date.today()
        week_end = today - timedelta(days=today.weekday() + 1)  # Last Sunday
        week_start = week_end - timedelta(days=6)
        
        result = await run_weekly_learner(week_start, week_end)
        return result


# Singleton
_agent_manager = None


async def get_agent_manager() -> AgentManager:
    """Get initialized AgentManager instance"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
        await _agent_manager.initialize()
    return _agent_manager

