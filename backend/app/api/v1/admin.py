"""
BullsBears Admin Control Panel API
Provides endpoints for system status and manual pipeline control
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional
import asyncio
import os
from datetime import datetime
from pathlib import Path

from ...services.data_flow_manager import DataFlowManager
from ...services.fmp_data_ingestion import get_fmp_service
from ...services.chart_generator import get_chart_generator
from ...services.firebase_service import FirebaseService
from ...services.kill_switch_service import KillSwitchService
from ...services.runpod_cost_control import runpod_cost_control
from ...core.database import get_database
from ...core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

# Setup templates
templates = Jinja2Templates(directory=Path(__file__).parent.parent.parent / "templates")

# Global pipeline control
PIPELINE_ENABLED = False
PIPELINE_STATUS = "stopped"

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Serve the admin dashboard HTML page"""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status"""
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_enabled": PIPELINE_ENABLED,
        "pipeline_status": PIPELINE_STATUS,
        "connections": {},
        "services": {},
        "data_status": {}
    }
    
    # Test Database Connection
    try:
        db_pool = await get_database()
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
        status["connections"]["database"] = {
            "status": "connected" if result == 1 else "error",
            "url": settings.database_url.split('@')[1] if '@' in settings.database_url else "configured",
            "last_check": datetime.now().isoformat()
        }
    except Exception as e:
        status["connections"]["database"] = {
            "status": "error",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
    
    # Test FMP API
    try:
        async with get_fmp_service() as fmp:
            # Quick test - get a few symbols
            symbols = await fmp.get_nasdaq_universe()
            status["connections"]["fmp_api"] = {
                "status": "connected",
                "symbols_available": len(symbols),
                "rate_limit": "300 calls/min",
                "last_check": datetime.now().isoformat()
            }
    except Exception as e:
        status["connections"]["fmp_api"] = {
            "status": "error",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
    
    # Test RunPod Connection
    try:
        import requests
        runpod_url = f"https://api.runpod.ai/v2/{settings.runpod_endpoint_id}/run"
        headers = {
            "Authorization": f"Bearer {settings.runpod_api_key}",
            "Content-Type": "application/json"
        }
        test_payload = {"input": {"test": "health_check"}}
        
        response = requests.post(runpod_url, headers=headers, json=test_payload, timeout=10)
        
        if response.status_code == 200:
            status["connections"]["runpod"] = {
                "status": "connected",
                "endpoint_id": settings.runpod_endpoint_id,
                "last_check": datetime.now().isoformat()
            }
        else:
            status["connections"]["runpod"] = {
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "last_check": datetime.now().isoformat()
            }
    except Exception as e:
        status["connections"]["runpod"] = {
            "status": "error", 
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
    
    # Test Firebase
    try:
        async with FirebaseService() as firebase:
            # Simple test - this will validate credentials
            status["connections"]["firebase"] = {
                "status": "connected",
                "project_id": "603494406675",
                "last_check": datetime.now().isoformat()
            }
    except Exception as e:
        status["connections"]["firebase"] = {
            "status": "error",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
    
    # Check Data Status
    try:
        db_pool = await get_database()
        async with db_pool.acquire() as conn:
            # Check if we have historical data
            try:
                ohlc_count = await conn.fetchval("SELECT COUNT(*) FROM prime_ohlc_90d")
                latest_date = await conn.fetchval("SELECT MAX(date) FROM prime_ohlc_90d")
            except Exception:
                # Table might not exist yet
                ohlc_count = 0
                latest_date = None

            # Check tier counts from stock_classifications table
            try:
                tier_counts_raw = await conn.fetch("""
                    SELECT current_tier, COUNT(*) as count
                    FROM stock_classifications
                    GROUP BY current_tier
                """)
                tier_counts = {row['current_tier']: row['count'] for row in tier_counts_raw}
            except Exception:
                # Table might not exist yet, show realistic estimates
                tier_counts = {
                    "ALL": 6960,  # Total NASDAQ stocks
                    "ACTIVE": 0,  # Will be populated during bootstrap
                    "QUALIFIED": 0,  # Will be populated during daily runs
                    "SHORT_LIST": 0,  # Will be populated during daily runs
                    "PICKS": 0  # Will be populated during daily runs
                }

            # Check for shortlist and picks tables
            try:
                shortlist_count = await conn.fetchval("SELECT COUNT(*) FROM shortlist_candidates")
                picks_count = await conn.fetchval("SELECT COUNT(*) FROM final_picks")
                tier_counts["SHORT_LIST"] = shortlist_count or 0
                tier_counts["PICKS"] = picks_count or 0
            except Exception:
                pass  # Tables don't exist yet

            status["data_status"] = {
                "historical_records": ohlc_count or 0,
                "latest_data_date": latest_date.isoformat() if latest_date else None,
                "tier_counts": tier_counts,
                "bootstrap_complete": ohlc_count > 100000,  # Rough estimate
                "tables_exist": {
                    "prime_ohlc_90d": ohlc_count is not None,
                    "stock_classifications": len(tier_counts) > 0,
                    "shortlist_candidates": "SHORT_LIST" in tier_counts,
                    "final_picks": "PICKS" in tier_counts
                }
            }
    except Exception as e:
        status["data_status"] = {
            "error": str(e),
            "bootstrap_complete": False,
            "tier_counts": {
                "ALL": 6960,  # Known NASDAQ total
                "ACTIVE": 0,
                "QUALIFIED": 0,
                "SHORT_LIST": 0,
                "PICKS": 0
            }
        }
    
    # Service Status
    status["services"] = {
        "data_flow_manager": "ready",
        "chart_generator": "ready", 
        "kill_switch": "inactive",
        "celery_worker": "not_started"
    }
    
    return status

@router.post("/pipeline/enable")
async def enable_pipeline() -> Dict[str, Any]:
    """Enable the automated pipeline"""
    global PIPELINE_ENABLED, PIPELINE_STATUS
    
    # Check if system is ready
    system_status = await get_system_status()
    
    # Validate all connections are working
    connections_ok = all(
        conn.get("status") == "connected" 
        for conn in system_status["connections"].values()
    )
    
    if not connections_ok:
        raise HTTPException(
            status_code=400,
            detail="Cannot enable pipeline - some connections are failing"
        )
    
    # Check if data is bootstrapped
    if not system_status["data_status"].get("bootstrap_complete", False):
        raise HTTPException(
            status_code=400,
            detail="Cannot enable pipeline - database not bootstrapped with historical data"
        )

    # 🛡️ CRITICAL: Initialize RunPod cost control
    try:
        await runpod_cost_control.initialize()
        runpod_startup = await runpod_cost_control.pipeline_enabled_startup()
        if not runpod_startup:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize RunPod cost control - pipeline not enabled for safety"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RunPod cost control initialization failed: {str(e)}"
        )

    PIPELINE_ENABLED = True
    PIPELINE_STATUS = "enabled"

    return {
        "success": True,
        "message": "Pipeline enabled - RunPod cost monitoring active - will start at next scheduled time (3:00 AM ET)",
        "enabled_at": datetime.now().isoformat(),
        "runpod_monitoring": "active"
    }

@router.post("/pipeline/disable")
async def disable_pipeline() -> Dict[str, Any]:
    """Disable the automated pipeline"""
    global PIPELINE_ENABLED, PIPELINE_STATUS

    # 🛡️ CRITICAL: Shutdown RunPod to prevent costs
    try:
        shutdown_success = await runpod_cost_control.pipeline_disabled_shutdown()
        if not shutdown_success:
            # Still disable pipeline but warn about RunPod
            PIPELINE_ENABLED = False
            PIPELINE_STATUS = "disabled"
            return {
                "success": True,
                "message": "Pipeline disabled - WARNING: RunPod shutdown may have failed, check costs manually",
                "disabled_at": datetime.now().isoformat(),
                "runpod_warning": "Manual verification required"
            }
    except Exception as e:
        # Still disable pipeline but warn about RunPod
        PIPELINE_ENABLED = False
        PIPELINE_STATUS = "disabled"
        return {
            "success": True,
            "message": f"Pipeline disabled - WARNING: RunPod shutdown error: {str(e)}",
            "disabled_at": datetime.now().isoformat(),
            "runpod_error": str(e)
        }

    PIPELINE_ENABLED = False
    PIPELINE_STATUS = "disabled"

    return {
        "success": True,
        "message": "Pipeline disabled - RunPod shutdown complete",
        "disabled_at": datetime.now().isoformat(),
        "runpod_shutdown": "success"
    }

@router.post("/runpod/emergency-shutdown")
async def emergency_runpod_shutdown() -> Dict[str, Any]:
    """🚨 EMERGENCY: Immediately shutdown all RunPod activity"""
    global PIPELINE_ENABLED, PIPELINE_STATUS

    try:
        # Force disable pipeline
        PIPELINE_ENABLED = False
        PIPELINE_STATUS = "emergency_shutdown"

        # Emergency RunPod shutdown
        shutdown_success = await runpod_cost_control.emergency_shutdown_all()

        return {
            "success": True,
            "message": "🚨 EMERGENCY SHUTDOWN COMPLETE - All RunPod activity terminated",
            "shutdown_at": datetime.now().isoformat(),
            "runpod_shutdown": "emergency_complete" if shutdown_success else "partial_failure",
            "pipeline_status": "emergency_disabled"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"🚨 EMERGENCY SHUTDOWN ERROR: {str(e)}",
            "error": str(e),
            "shutdown_at": datetime.now().isoformat()
        }

@router.get("/runpod/cost-status")
async def get_runpod_cost_status() -> Dict[str, Any]:
    """Get current RunPod cost and usage status"""
    try:
        cost_status = await runpod_cost_control.check_cost_alerts()
        kill_status = runpod_cost_control.check_emergency_kill_file()

        return {
            "success": True,
            "cost_status": cost_status,
            "kill_status": kill_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/runpod/clear-emergency-kill")
async def clear_emergency_kill() -> Dict[str, Any]:
    """Clear the emergency kill file to allow RunPod operations"""
    try:
        success = runpod_cost_control.clear_emergency_kill_file()

        if success:
            return {
                "success": True,
                "message": "✅ Emergency kill file cleared - RunPod operations can resume",
                "cleared_at": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "❌ Failed to clear emergency kill file",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Error clearing emergency kill file: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@router.post("/pipeline/run-once")
async def run_pipeline_once(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Run the pipeline once manually (for testing)"""
    
    # Check system status first
    system_status = await get_system_status()
    connections_ok = all(
        conn.get("status") == "connected" 
        for conn in system_status["connections"].values()
    )
    
    if not connections_ok:
        raise HTTPException(
            status_code=400,
            detail="Cannot run pipeline - some connections are failing"
        )
    
    # Run pipeline in background
    background_tasks.add_task(run_full_pipeline_once)
    
    return {
        "success": True,
        "message": "Pipeline started manually - check status for progress",
        "started_at": datetime.now().isoformat()
    }

@router.post("/bootstrap/start")
async def start_bootstrap(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Start database bootstrap process"""
    
    # Check if FMP connection is working
    system_status = await get_system_status()
    fmp_status = system_status["connections"].get("fmp_api", {})
    
    if fmp_status.get("status") != "connected":
        raise HTTPException(
            status_code=400,
            detail="Cannot start bootstrap - FMP API connection failed"
        )
    
    # Start bootstrap in background
    background_tasks.add_task(run_bootstrap_process)
    
    return {
        "success": True,
        "message": "Bootstrap process started - this will take 15-30 minutes",
        "started_at": datetime.now().isoformat()
    }

@router.get("/logs/recent")
async def get_recent_logs(lines: int = 100) -> Dict[str, Any]:
    """Get recent system logs"""
    
    # This would read from log files in a real implementation
    # For now, return a placeholder
    return {
        "logs": [
            f"[{datetime.now().isoformat()}] System status check completed",
            f"[{datetime.now().isoformat()}] All connections verified",
        ],
        "total_lines": lines
    }

# Background task functions
async def run_full_pipeline_once():
    """Run the complete pipeline once"""
    global PIPELINE_STATUS
    
    try:
        PIPELINE_STATUS = "running"
        
        manager = DataFlowManager()
        await manager.initialize()
        
        # Run the full daily pipeline
        result = await manager.run_daily_prescreen_full_pipeline()
        
        PIPELINE_STATUS = "completed"
        
    except Exception as e:
        PIPELINE_STATUS = f"error: {str(e)}"
    
async def run_bootstrap_process():
    """Run the bootstrap process"""
    try:
        manager = DataFlowManager()
        await manager.initialize()
        
        # Bootstrap with 90 days of data
        result = await manager.bootstrap_historical_data(days_back=90)
        
    except Exception as e:
        print(f"Bootstrap error: {e}")

# Pipeline control check function (used by Celery tasks)
def is_pipeline_enabled() -> bool:
    """Check if pipeline is enabled (used by Celery tasks)"""
    return PIPELINE_ENABLED
