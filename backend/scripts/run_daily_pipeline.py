#!/usr/bin/env python3
"""
BullsBears Daily Pipeline Runner
Triggered by Render Cron Job at 8:00 AM ET on weekdays

Pipeline Steps:
1. Check if system is ON
2. FMP Delta Update (refresh OHLC data)
3. Prescreen (ACTIVE → SHORT_LIST ~75 stocks)
4. Generate Charts (create annotated charts → Firebase Storage)
5. Vision Analysis (Fireworks Qwen3-VL pattern detection)
6. Social Analysis (Grok sentiment scoring)
7. Arbitrator (select 3 bullish + 3 bearish picks with Fib targets)
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


async def run_pipeline():
    """Execute full daily pipeline"""
    from app.services.system_state import is_system_on
    
    # Step 0: Check system state
    if not await is_system_on():
        logger.warning("⏸️ System is OFF - skipping daily pipeline")
        return {"status": "skipped", "reason": "system_off"}
    
    logger.info("🚀 Starting BullsBears Daily Pipeline")
    results = {}
    
    try:
        # Step 1: FMP Delta Update
        logger.info("📊 Step 1/6: FMP Delta Update...")
        from app.services import get_fmp_ingestion
        ingestion = await get_fmp_ingestion()
        await ingestion.daily_delta_update()
        results["fmp_delta"] = "success"
        logger.info("✅ FMP Delta complete")
    except Exception as e:
        logger.error(f"❌ FMP Delta failed: {e}")
        results["fmp_delta"] = f"error: {e}"
        # Continue anyway - we might have recent enough data
    
    try:
        # Step 2: Prescreen
        logger.info("🔍 Step 2/6: Prescreen (ACTIVE → SHORT_LIST)...")
        from app.services.agent_manager import get_agent_manager
        agent_manager = await get_agent_manager()
        prescreen_result = await agent_manager.run_prescreen_agent()
        results["prescreen"] = prescreen_result
        logger.info(f"✅ Prescreen complete: {prescreen_result.get('shortlist_count', 0)} stocks")
    except Exception as e:
        logger.error(f"❌ Prescreen failed: {e}")
        results["prescreen"] = f"error: {e}"
        return {"status": "failed", "step": "prescreen", "results": results}
    
    try:
        # Step 3: Generate Charts
        logger.info("📈 Step 3/6: Generating charts...")
        from app.tasks.generate_charts import get_chart_generator
        chart_gen = await get_chart_generator()
        chart_result = await chart_gen.generate_all_charts()
        results["charts"] = chart_result
        logger.info(f"✅ Charts complete: {chart_result.get('success_count', 0)} generated")
    except Exception as e:
        logger.error(f"❌ Chart generation failed: {e}")
        results["charts"] = f"error: {e}"
        return {"status": "failed", "step": "charts", "results": results}
    
    try:
        # Step 4: Vision Analysis
        logger.info("👁️ Step 4/6: Vision analysis (Fireworks Qwen3-VL)...")
        vision_result = await agent_manager.run_vision_agent()
        results["vision"] = vision_result
        logger.info(f"✅ Vision complete")
    except Exception as e:
        logger.error(f"❌ Vision analysis failed: {e}")
        results["vision"] = f"error: {e}"
        # Continue - social might still work
    
    try:
        # Step 5: Social Analysis
        logger.info("📱 Step 5/6: Social analysis (Grok)...")
        social_result = await agent_manager.run_social_agent()
        results["social"] = social_result
        logger.info(f"✅ Social complete")
    except Exception as e:
        logger.error(f"❌ Social analysis failed: {e}")
        results["social"] = f"error: {e}"
        # Continue - arbitrator can work without social
    
    try:
        # Step 6: Arbitrator (with Fib targets)
        logger.info("🎯 Step 6/6: Arbitrator (final picks with Fib targets)...")
        arbitrator_result = await agent_manager.run_arbitrator_agent()
        results["arbitrator"] = arbitrator_result
        logger.info(f"✅ Arbitrator complete: {arbitrator_result.get('picks_count', 0)} picks")
    except Exception as e:
        logger.error(f"❌ Arbitrator failed: {e}")
        results["arbitrator"] = f"error: {e}"
        return {"status": "failed", "step": "arbitrator", "results": results}
    
    logger.info("🎉 Daily pipeline complete!")
    return {"status": "success", "results": results}


def main():
    """Entry point for Render cron job"""
    try:
        result = asyncio.run(run_pipeline())
        logger.info(f"Pipeline result: {result}")
        
        if result.get("status") == "success":
            sys.exit(0)
        elif result.get("status") == "skipped":
            sys.exit(0)  # Not an error
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Pipeline crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

