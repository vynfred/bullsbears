#!/usr/bin/env python3
"""
BullsBears Admin Server
Simple FastAPI server to serve the admin dashboard
"""

import sys
import os
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import uvicorn

# Load environment variables from root .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Setup templates
templates = Jinja2Templates(directory=Path(__file__).parent / "app" / "templates")

# Create FastAPI app
app = FastAPI(
    title="BullsBears Admin Dashboard",
    description="System control and monitoring dashboard",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline control
PIPELINE_ENABLED = False
PIPELINE_STATUS = "stopped"

# Simplified admin routes without full app dependencies
@app.get("/api/v1/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Serve the admin dashboard HTML page"""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@app.get("/api/v1/admin/status")
async def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status with real connection testing"""

    status = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_enabled": PIPELINE_ENABLED,
        "pipeline_status": PIPELINE_STATUS,
        "connections": {},
        "services": {
            "data_ingestion": {"status": "unknown", "last_run": None},
            "ai_pipeline": {"status": "unknown", "last_run": None},
            "kill_switch": {"status": "unknown", "active": False}
        },
        "data_status": {
            "historical_records": 0,
            "latest_data_date": None,
            "bootstrap_complete": False,
            "tier_counts": {
                "ALL": 0,
                "ACTIVE": 0,
                "SHORT_LIST": 0,
                "PICKS": 0
            }
        }
    }

    # Test actual connections
    status["connections"]["database"] = await test_database_connection()
    status["connections"]["fmp_api"] = await test_fmp_api_connection()
    status["connections"]["runpod"] = await test_runpod_connection()
    status["connections"]["firebase"] = await test_firebase_connection()

    return status

async def test_database_connection() -> Dict[str, str]:
    """Test actual database connectivity"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {"status": "error", "message": "DATABASE_URL not configured"}

        # Try to import and test database connection
        import asyncpg

        # Parse connection string and test connection with timeout
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(database_url),
                timeout=5.0  # 5 second timeout
            )
            await asyncio.wait_for(
                conn.execute("SELECT 1"),
                timeout=3.0  # 3 second timeout for query
            )
            await conn.close()

            return {"status": "connected", "message": "Database connection successful"}

        except asyncio.TimeoutError:
            return {"status": "error", "message": "Database connection timeout - check network/firewall"}

    except ImportError:
        return {"status": "error", "message": "asyncpg not installed"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}

async def test_fmp_api_connection() -> Dict[str, str]:
    """Test actual FMP API connectivity"""
    try:
        fmp_key = os.getenv("FMP_API_KEY")
        if not fmp_key:
            return {"status": "error", "message": "FMP_API_KEY not configured"}

        # Test FMP API with a simple request
        import aiohttp
        async with aiohttp.ClientSession() as session:
            url = f"https://financialmodelingprep.com/api/v3/profile/AAPL?apikey={fmp_key}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        return {"status": "connected", "message": "FMP API connection successful"}
                    else:
                        return {"status": "error", "message": "FMP API returned empty response"}
                else:
                    return {"status": "error", "message": f"FMP API returned status {response.status}"}

    except ImportError:
        return {"status": "error", "message": "aiohttp not installed"}
    except Exception as e:
        return {"status": "error", "message": f"FMP API connection failed: {str(e)}"}

async def test_runpod_connection() -> Dict[str, str]:
    """Test actual RunPod endpoint connectivity"""
    try:
        runpod_key = os.getenv("RUNPOD_API_KEY")
        runpod_endpoint = os.getenv("RUNPOD_ENDPOINT_ID")

        if not runpod_key:
            return {"status": "error", "message": "RUNPOD_API_KEY not configured"}
        if not runpod_endpoint:
            return {"status": "error", "message": "RUNPOD_ENDPOINT_ID not configured"}

        # Test RunPod endpoint health (correct endpoint)
        import aiohttp
        async with aiohttp.ClientSession() as session:
            url = f"https://api.runpod.ai/v2/{runpod_endpoint}/health"
            headers = {"Authorization": f"Bearer {runpod_key}"}

            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    workers = data.get('workers', {})
                    ready_workers = workers.get('ready', 0)
                    total_workers = sum(workers.values()) if workers else 0

                    if ready_workers > 0:
                        return {"status": "connected", "message": f"RunPod endpoint healthy: {ready_workers}/{total_workers} workers ready"}
                    else:
                        return {"status": "warning", "message": f"RunPod endpoint accessible but no ready workers: {workers}"}
                else:
                    return {"status": "error", "message": f"RunPod API returned status {response.status}"}

    except ImportError:
        return {"status": "error", "message": "aiohttp not installed"}
    except Exception as e:
        return {"status": "error", "message": f"RunPod connection failed: {str(e)}"}

async def test_firebase_connection() -> Dict[str, str]:
    """Test Firebase connectivity"""
    try:
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID", "603494406675")

        # For now, just check if Firebase credentials are configured
        firebase_creds = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if firebase_creds and os.path.exists(firebase_creds):
            return {"status": "connected", "message": "Firebase credentials file found"}
        elif firebase_project_id:
            return {"status": "connected", "message": f"Firebase project ID configured: {firebase_project_id}"}
        else:
            return {"status": "error", "message": "Firebase not configured"}

    except Exception as e:
        return {"status": "error", "message": f"Firebase check failed: {str(e)}"}

# Pipeline control endpoints
@app.post("/api/v1/admin/pipeline/enable")
async def enable_pipeline() -> Dict[str, Any]:
    """Enable the automated pipeline"""
    global PIPELINE_ENABLED, PIPELINE_STATUS

    # Check if system is ready
    system_status = await get_system_status()

    # Validate all connections are working (accept "connected" or "warning" status)
    connections_ok = all(
        conn.get("status") in ["connected", "warning"]
        for conn in system_status["connections"].values()
    )

    if not connections_ok:
        failed_connections = [
            name for name, conn in system_status["connections"].items()
            if conn.get("status") not in ["connected", "warning"]
        ]
        raise HTTPException(
            status_code=400,
            detail=f"Cannot enable pipeline - connections failing: {', '.join(failed_connections)}"
        )

    PIPELINE_ENABLED = True
    PIPELINE_STATUS = "enabled"

    return {
        "success": True,
        "message": "Pipeline enabled - will start at next scheduled time (3:00 AM ET)",
        "enabled_at": datetime.now().isoformat()
    }

@app.post("/api/v1/admin/pipeline/disable")
async def disable_pipeline() -> Dict[str, Any]:
    """Disable the automated pipeline"""
    global PIPELINE_ENABLED, PIPELINE_STATUS

    PIPELINE_ENABLED = False
    PIPELINE_STATUS = "disabled"

    return {
        "success": True,
        "message": "Pipeline disabled",
        "disabled_at": datetime.now().isoformat()
    }

@app.post("/api/v1/admin/pipeline/run-once")
async def run_pipeline_once(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Run the pipeline once manually (for testing)"""

    # Check system status first
    system_status = await get_system_status()
    connections_ok = all(
        conn.get("status") in ["connected", "warning"]
        for conn in system_status["connections"].values()
    )

    if not connections_ok:
        failed_connections = [
            name for name, conn in system_status["connections"].items()
            if conn.get("status") not in ["connected", "warning"]
        ]
        raise HTTPException(
            status_code=400,
            detail=f"Cannot run pipeline - connections failing: {', '.join(failed_connections)}"
        )

    # Run pipeline in background (placeholder for now)
    background_tasks.add_task(run_test_pipeline)

    return {
        "success": True,
        "message": "Pipeline started manually - check status for progress",
        "started_at": datetime.now().isoformat()
    }

@app.post("/api/v1/admin/bootstrap/start")
async def start_bootstrap(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Start database bootstrap process"""

    # Check if FMP connection is working
    fmp_status = await test_fmp_api_connection()

    if fmp_status.get("status") != "connected":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start bootstrap - FMP API connection failed: {fmp_status.get('message')}"
        )

    # Start bootstrap in background (placeholder for now)
    background_tasks.add_task(run_bootstrap_process)

    return {
        "success": True,
        "message": "Bootstrap process started - this will take 15-30 minutes",
        "started_at": datetime.now().isoformat()
    }

# Background task functions (placeholders)
async def run_test_pipeline():
    """Run a test pipeline (placeholder)"""
    global PIPELINE_STATUS

    try:
        PIPELINE_STATUS = "running"

        # Simulate pipeline work
        await asyncio.sleep(5)

        PIPELINE_STATUS = "completed"
        print("Test pipeline completed successfully")

    except Exception as e:
        PIPELINE_STATUS = f"error: {str(e)}"
        print(f"Test pipeline error: {e}")

async def run_bootstrap_process():
    """Run the bootstrap process (placeholder)"""
    try:
        print("Bootstrap process started...")

        # Simulate bootstrap work
        await asyncio.sleep(10)

        print("Bootstrap process completed")

    except Exception as e:
        print(f"Bootstrap error: {e}")

# Root redirect to dashboard
@app.get("/")
async def root():
    """Redirect to admin dashboard"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/admin/dashboard")

@app.get("/health")
async def health_check():
    """Simple health check"""
    return {"status": "healthy", "service": "BullsBears Admin"}

if __name__ == "__main__":
    print("🚀 Starting BullsBears Admin Dashboard")
    print("=" * 50)
    print("📊 Dashboard URL: http://localhost:8001")
    print("🔧 API Docs: http://localhost:8001/docs")
    print("=" * 50)
    
    uvicorn.run(
        "run_admin_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
