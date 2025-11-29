#!/usr/bin/env python3
"""
Internal Task Endpoints for Cloud Scheduler
These endpoints are triggered by Cloud Scheduler instead of Celery
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from datetime import datetime

from app.services.system_state import is_system_on

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


async def verify_scheduler_auth(authorization: Optional[str] = Header(None)):
    """Verify request is from Cloud Scheduler (has valid Bearer token)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized - Cloud Scheduler only")
    return True


@router.get("/check-schema")
async def check_database_schema(authorized: bool = Depends(verify_scheduler_auth)):
    """Check if all required database tables exist with correct columns"""
    from app.core.database import get_asyncpg_pool

    try:
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Check critical tables
            tables_to_check = [
                "stock_classifications",
                "prime_ohlc_90d",
                "picks",
                "shortlist_candidates"
            ]

            results = {}
            for table in tables_to_check:
                # Check if table exists and get column info
                query = """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = $1
                    ORDER BY ordinal_position
                """
                columns = await conn.fetch(query, table)

                if columns:
                    results[table] = {
                        "exists": True,
                        "columns": [{"name": c["column_name"], "type": c["data_type"]} for c in columns]
                    }

                    # Get row count
                    count_query = f"SELECT COUNT(*) as count FROM {table}"
                    count_result = await conn.fetchval(count_query)
                    results[table]["row_count"] = count_result
                else:
                    results[table] = {"exists": False}

            return {
                "status": "success",
                "tables": results,
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error(f"Schema check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix-schema")
async def fix_database_schema(authorized: bool = Depends(verify_scheduler_auth)):
    """Add missing columns to prime_ohlc_90d table"""
    from app.core.database import get_asyncpg_pool

    try:
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Add missing columns
            await conn.execute("""
                ALTER TABLE prime_ohlc_90d
                ADD COLUMN IF NOT EXISTS adj_close NUMERIC(10,2),
                ADD COLUMN IF NOT EXISTS vwap NUMERIC(10,2)
            """)

            # Add unique constraint if not exists
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'prime_ohlc_90d_symbol_date_key'
                    ) THEN
                        ALTER TABLE prime_ohlc_90d
                        ADD CONSTRAINT prime_ohlc_90d_symbol_date_key
                        UNIQUE (symbol, date);
                    END IF;
                END $$;
            """)

            logger.info("✅ Schema fixed: added adj_close, vwap columns and unique constraint")

            return {
                "status": "success",
                "message": "Schema fixed successfully",
                "changes": [
                    "Added adj_close column to prime_ohlc_90d",
                    "Added vwap column to prime_ohlc_90d",
                    "Added unique constraint on (symbol, date)"
                ]
            }

    except Exception as e:
        logger.error(f"Schema fix failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fmp-delta")
async def trigger_fmp_delta(authorized: bool = Depends(verify_scheduler_auth)):
    """8:00 AM - FMP Daily Delta Update"""
    try:
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping FMP delta update")
            return {"status": "skipped", "reason": "system_off"}

        logger.info("🚀 Starting FMP delta update via Cloud Scheduler")
        
        from app.services import get_fmp_ingestion
        ingestion = await get_fmp_ingestion()
        await ingestion.daily_delta_update()
        
        logger.info("✅ FMP delta update complete")
        return {"status": "success", "timestamp": datetime.utcnow().isoformat()}
    
    except Exception as e:
        logger.error(f"❌ FMP delta update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build-active")
async def trigger_build_active(authorized: bool = Depends(verify_scheduler_auth)):
    """8:05 AM - Build ACTIVE tier from NASDAQ ALL"""
    try:
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping ACTIVE tier build")
            return {"status": "skipped", "reason": "system_off"}

        logger.info("🚀 Starting ACTIVE tier build via Cloud Scheduler")
        
        from app.services.stock_filter_service import get_stock_filter_service
        filter_service = await get_stock_filter_service()
        active_stocks = await filter_service.filter_nasdaq_to_active()
        
        logger.info(f"✅ ACTIVE tier build complete: {len(active_stocks)} stocks")
        return {
            "status": "success",
            "active_count": len(active_stocks),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ ACTIVE tier build failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prescreen")
async def trigger_prescreen(authorized: bool = Depends(verify_scheduler_auth)):
    """8:10 AM - Run Prescreen Agent (ACTIVE → SHORT_LIST)"""
    try:
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping prescreen")
            return {"status": "skipped", "reason": "system_off"}

        logger.info("🚀 Starting prescreen via Cloud Scheduler")
        
        from app.services.agent_manager import get_agent_manager
        agent_manager = await get_agent_manager()
        result = await agent_manager.run_prescreen_agent()
        
        logger.info(f"✅ Prescreen complete: {result.get('shortlist_count', 0)} stocks")
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Prescreen failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-charts")
async def trigger_generate_charts(authorized: bool = Depends(verify_scheduler_auth)):
    """8:15 AM - Generate charts for SHORT_LIST stocks"""
    try:
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping chart generation")
            return {"status": "skipped", "reason": "system_off"}

        logger.info("🚀 Starting chart generation via Cloud Scheduler")
        
        from app.services.chart_generator import get_chart_generator
        chart_gen = await get_chart_generator()
        result = await chart_gen.generate_shortlist_charts()
        
        logger.info(f"✅ Chart generation complete: {result.get('charts_generated', 0)} charts")
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Chart generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vision-analysis")
async def trigger_vision_analysis(authorized: bool = Depends(verify_scheduler_auth)):
    """8:16 AM - Run Groq Vision Analysis"""
    try:
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping vision analysis")
            return {"status": "skipped", "reason": "system_off"}

        logger.info("🚀 Starting vision analysis via Cloud Scheduler")
        
        from app.services.agent_manager import get_agent_manager
        agent_manager = await get_agent_manager()
        result = await agent_manager.run_vision_agent()
        
        logger.info(f"✅ Vision analysis complete")
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Vision analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/social-analysis")
async def trigger_social_analysis(authorized: bool = Depends(verify_scheduler_auth)):
    """8:17 AM - Run Grok Social Analysis"""
    try:
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping social analysis")
            return {"status": "skipped", "reason": "system_off"}

        logger.info("🚀 Starting social analysis via Cloud Scheduler")

        from app.services.agent_manager import get_agent_manager
        agent_manager = await get_agent_manager()
        result = await agent_manager.run_social_agent()

        logger.info(f"✅ Social analysis complete")
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Social analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/arbitrator")
async def trigger_arbitrator(authorized: bool = Depends(verify_scheduler_auth)):
    """8:20 AM - Run Final Arbitrator (select 3-6 picks)"""
    try:
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping arbitrator")
            return {"status": "skipped", "reason": "system_off"}

        logger.info("🚀 Starting arbitrator via Cloud Scheduler")

        from app.services.agent_manager import get_agent_manager
        agent_manager = await get_agent_manager()
        result = await agent_manager.run_arbitrator_agent()

        logger.info(f"✅ Arbitrator complete: {result.get('picks_count', 0)} picks selected")
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Arbitrator failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/publish-picks")
async def trigger_publish_picks(authorized: bool = Depends(verify_scheduler_auth)):
    """8:25 AM - Publish picks to Firebase"""
    try:
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping publish")
            return {"status": "skipped", "reason": "system_off"}

        logger.info("🚀 Starting publish to Firebase via Cloud Scheduler")

        from app.services.firebase_publisher import get_firebase_publisher
        publisher = await get_firebase_publisher()
        result = await publisher.publish_daily_picks()

        logger.info(f"✅ Publish complete")
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Publish failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/weekly-learner")
async def trigger_weekly_learner(authorized: bool = Depends(verify_scheduler_auth)):
    """Saturday 4:00 AM - Run Weekly Learner"""
    try:
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping weekly learner")
            return {"status": "skipped", "reason": "system_off"}

        logger.info("🚀 Starting weekly learner via Cloud Scheduler")

        from app.services.agent_manager import get_agent_manager
        agent_manager = await get_agent_manager()
        result = await agent_manager.run_learner_agent()

        logger.info(f"✅ Weekly learner complete")
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Weekly learner failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-statistics")
async def trigger_update_statistics(authorized: bool = Depends(verify_scheduler_auth)):
    """Every 5 minutes - Update statistics cache"""
    try:
        if not await is_system_on():
            return {"status": "skipped", "reason": "system_off"}

        from app.services.statistics_service import get_statistics_service
        stats_service = await get_statistics_service()
        await stats_service.update_cache()

        return {"status": "success", "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"❌ Statistics update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-badges")
async def trigger_update_badges(authorized: bool = Depends(verify_scheduler_auth)):
    """Every 2 minutes (market hours) - Update badge data"""
    try:
        if not await is_system_on():
            return {"status": "skipped", "reason": "system_off"}

        from app.services.badge_service import get_badge_service
        badge_service = await get_badge_service()
        await badge_service.update_badge_data()

        return {"status": "success", "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"❌ Badge update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def internal_health():
    """Health check for internal endpoints"""
    return {
        "status": "healthy",
        "service": "internal-tasks",
        "timestamp": datetime.utcnow().isoformat()
    }

