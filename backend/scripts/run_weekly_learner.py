#!/usr/bin/env python3
"""
BullsBears Weekly Learner
Triggered by Render Cron Job at 4:10 AM ET on Mondays

Analyzes the past week's picks and outcomes to:
1. Update feature weights in weights.json
2. Adjust model biases
3. Log learning insights
"""

import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def run_learner():
    """Execute weekly learner"""
    from app.services.system_state import is_system_on
    
    # Check system state
    if not await is_system_on():
        logger.warning("⏸️ System is OFF - skipping weekly learner")
        return {"status": "skipped", "reason": "system_off"}
    
    logger.info("🧠 Starting BullsBears Weekly Learner")
    
    try:
        from app.services.agent_manager import get_agent_manager
        agent_manager = await get_agent_manager()
        result = await agent_manager.run_learner_agent()
        
        logger.info(f"✅ Weekly learner complete")
        logger.info(f"Result: {result}")
        
        return {"status": "success", "result": result}
        
    except Exception as e:
        logger.error(f"❌ Weekly learner failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}


def main():
    """Entry point for Render cron job"""
    try:
        result = asyncio.run(run_learner())
        logger.info(f"Learner result: {result}")
        
        if result.get("status") in ["success", "skipped"]:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Learner crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

