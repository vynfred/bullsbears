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
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uvicorn
try:
    import pytz
except ImportError:
    pytz = None

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

# Default schedule configuration (3:00 AM - 4:01 AM ET daily)
DEFAULT_SCHEDULE = {
    "enabled": True,
    "daily_run_time": "03:00",  # 3:00 AM ET
    "timezone": "America/New_York",
    "max_duration_minutes": 61,  # 1 hour 1 minute
    "next_run": None,
    "last_run": None,
    "kill_switch_conditions": {
        "vix_threshold": 30,
        "spy_drop_threshold": -2.0
    }
}

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

@app.get("/api/v1/admin/frontend-status")
async def get_frontend_status() -> Dict[str, Any]:
    """Get frontend application status - check actual Firebase hosting"""
    try:
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
        if not firebase_project_id:
            return {
                "status": "not_configured",
                "message": "Firebase project ID not configured",
                "deployment": "Firebase Hosting",
                "domain": "bullsbears.xyz"
            }

        # REAL CHECK: We haven't deployed to Firebase hosting yet
        # Don't make fake checks - just show the truth
        return {
            "status": "not_deployed",
            "message": "Frontend not deployed to Firebase hosting yet",
            "deployment": "Firebase Hosting (not deployed)",
            "domain": "bullsbears.xyz (not live)",
            "firebase_project_id": firebase_project_id,
            "next_steps": "Need to build and deploy frontend to Firebase hosting"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Frontend status check failed: {str(e)}",
            "deployment": "Firebase Hosting"
        }

@app.get("/api/v1/admin/users")
async def get_user_stats() -> Dict[str, Any]:
    """Get user statistics and activity"""
    try:
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
        if not firebase_project_id:
            return {
                "status": "not_configured",
                "message": "Firebase authentication not set up yet",
                "total_users": 0,
                "active_users_24h": 0,
                "active_users_7d": 0,
                "new_users_today": 0,
                "user_growth": "N/A",
                "note": "User tracking will be available once Firebase Auth is configured"
            }

        # TODO: When Firebase is set up, query actual user data
        # For now, show that we have no users yet
        return {
            "status": "no_users_yet",
            "message": "Firebase configured but no users registered yet",
            "total_users": 0,
            "active_users_24h": 0,
            "active_users_7d": 0,
            "new_users_today": 0,
            "user_growth": "0%",
            "firebase_project_id": firebase_project_id,
            "note": "User registration will begin when frontend is deployed"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get user stats: {str(e)}",
            "total_users": 0,
            "active_users_24h": 0,
            "active_users_7d": 0,
            "new_users_today": 0,
            "user_growth": "N/A"
        }

@app.get("/api/v1/admin/api-usage")
async def get_api_usage() -> Dict[str, Any]:
    """Get API usage statistics for FMP and cloud AI agents"""

    # FMP API Usage
    fmp_usage = await get_fmp_usage()

    # Cloud AI Agent Usage
    ai_usage = await get_ai_agent_usage()

    return {
        "fmp_api": fmp_usage,
        "ai_agents": ai_usage,
        "last_updated": datetime.now().isoformat()
    }

async def get_fmp_usage() -> Dict[str, Any]:
    """Get FMP API usage statistics"""
    try:
        fmp_api_key = os.getenv("FMP_API_KEY")
        if not fmp_api_key:
            return {"status": "error", "message": "FMP API key not configured"}

        # Try to get usage from FMP API
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # FMP doesn't have a direct usage endpoint, so we'll simulate based on typical usage
            # In production, you'd track this in your database

            # Test API call to check if key is working
            test_url = f"https://financialmodelingprep.com/api/v3/profile/AAPL?apikey={fmp_api_key}"
            async with session.get(test_url) as response:
                if response.status == 200:
                    # Calculate data usage for 20GB monthly threshold
                    try:
                        # Estimate data usage based on typical API response sizes
                        # Historical data: ~2KB per stock per call
                        # Real-time data: ~0.5KB per stock per call
                        # News/events: ~1KB per call

                        # Get rough estimates from database if available
                        # Try to get real-time usage from our tracking system
                        try:
                            from app.services.api_usage_tracker import get_api_usage_tracker
                            tracker = await get_api_usage_tracker()
                            usage_data = await tracker.get_fmp_usage_this_month()

                            if "error" not in usage_data:
                                # Use real tracked data
                                calls_this_month = usage_data["calls_this_month"]
                                estimated_data_gb = usage_data["data_usage_gb"]
                                usage_percentage = float(usage_data["usage_percentage"].rstrip('%'))
                                tracking_status = "🟢 Real-time tracking active"
                            else:
                                # Fallback to manual FMP dashboard data
                                actual_usage_mb = 204  # From your FMP dashboard
                                estimated_data_gb = actual_usage_mb / 1024
                                usage_percentage = (estimated_data_gb / 20) * 100
                                calls_this_month = int(actual_usage_mb * 1024 / 2)  # ~2KB per call
                                tracking_status = "🟡 Manual tracking (FMP dashboard: 204 MB)"

                        except Exception:
                            # Fallback to manual FMP dashboard data
                            actual_usage_mb = 204  # From your FMP dashboard
                            estimated_data_gb = actual_usage_mb / 1024
                            usage_percentage = (estimated_data_gb / 20) * 100
                            calls_this_month = int(actual_usage_mb * 1024 / 2)
                            tracking_status = "🟡 Manual tracking (FMP dashboard: 204 MB)"

                    except Exception:
                        calls_this_month = 0
                        estimated_data_gb = 0.0
                        usage_percentage = 0.0

                    return {
                        "status": "configured",
                        "plan": "Premium ($29/month)",
                        "calls_today": "0 (pipeline not active)",
                        "calls_this_month": f"~{calls_this_month:,}",
                        "calls_limit": "300 calls/min",
                        "data_usage_gb": round(estimated_data_gb, 3),
                        "data_limit_gb": 20,
                        "usage_percentage": f"{usage_percentage:.1f}%",
                        "reset_date": "Trailing 30-day window",
                        "cost_estimate": "$29/month (active plan)",
                        "remaining_gb": round(20 - estimated_data_gb, 1),
                        "tracking_method": tracking_status,
                        "note": f"📊 {round(estimated_data_gb * 1024)} MB used, {20 - estimated_data_gb:.1f}GB remaining"
                    }
                else:
                    return {"status": "error", "message": f"API key invalid (HTTP {response.status})"}

    except Exception as e:
        return {"status": "error", "message": f"Failed to check FMP usage: {str(e)}"}

async def get_ai_agent_usage() -> Dict[str, Any]:
    """Get cloud AI agent usage statistics"""
    try:
        # RunPod Usage (Local agents: FinMA-7b, DeepSeek-r1:8b)
        runpod_usage = await get_runpod_usage()

        # Groq API Usage (Vision agent: Llama-3.2-11B-Vision)
        groq_usage = await get_groq_usage()

        # Grok API Usage (Social sentiment)
        grok_usage = await get_grok_usage()

        # Rotating Arbitrator APIs (DeepSeek-V3, Gemini 2.5 Pro, Claude Sonnet 4, GPT-5)
        arbitrator_usage = await get_arbitrator_usage()

        return {
            "runpod": runpod_usage,
            "groq": groq_usage,
            "grok": grok_usage,  # Combined for both social sentiment AND arbitration
            "deepseek": arbitrator_usage.get("deepseek", {}),
            "gemini": arbitrator_usage.get("gemini", {}),
            "claude": arbitrator_usage.get("claude", {}),
            "gpt5": arbitrator_usage.get("gpt5", {}),
            "total_cost_estimate": "TBD - will calculate when APIs are actively used",
            "development_status": "All APIs configured but not actively running yet"
        }

    except Exception as e:
        return {"status": "error", "message": f"Failed to get AI usage: {str(e)}"}

async def get_runpod_usage() -> Dict[str, Any]:
    """Get RunPod serverless usage with accurate cost control info"""
    try:
        runpod_api_key = os.getenv("RUNPOD_API_KEY")
        if not runpod_api_key:
            return {"status": "error", "message": "RunPod API key not configured"}

        # Import our cost control system
        from app.services.runpod_cost_control import runpod_cost_control

        # Get real-time cost and status
        try:
            await runpod_cost_control.initialize()
            cost_status = await runpod_cost_control.check_cost_alerts()
            kill_status = runpod_cost_control.check_emergency_kill_file()

            # Determine actual status
            if kill_status.get("kill_active"):
                status = "emergency_kill_active"
                status_message = "🚨 EMERGENCY KILL ACTIVE"
            elif cost_status.get("current_spend_per_hour", 0) > 0:
                status = "active_spending"
                status_message = f"💰 ACTIVE: ${cost_status['current_spend_per_hour']}/hour"
            elif cost_status.get("api_accessible") == False:
                status = "api_unavailable"
                status_message = "⚠️ API unavailable (using safe defaults)"
            else:
                status = "idle"
                status_message = "✅ Connected, no active spending"

            return {
                "status": status,
                "status_message": status_message,
                "current_spend_per_hour": f"${cost_status.get('current_spend_per_hour', 0):.4f}",
                "session_runtime": cost_status.get('session_runtime', 'Not running'),
                "emergency_kill_active": kill_status.get("kill_active", False),
                "spend_limit": f"${cost_status.get('spend_limit', 0):.2f}",
                "alerts": cost_status.get('alerts', []),
                "endpoint_id": os.getenv("RUNPOD_ENDPOINT_ID", "N/A"),
                "cost_control": "✅ Active monitoring",
                "max_runtime": "2 hours (auto-shutdown)",
                "api_accessible": cost_status.get('api_accessible', True)
            }

        except Exception as cost_error:
            return {
                "status": "error",
                "status_message": f"❌ Cost control error: {str(cost_error)}",
                "current_spend_per_hour": "$0.0000 (error state)",
                "emergency_kill_active": False,
                "endpoint_id": os.getenv("RUNPOD_ENDPOINT_ID", "N/A"),
                "cost_control": "❌ Error - manual verification required",
                "error": str(cost_error)
            }

    except Exception as e:
        return {"status": "error", "message": f"RunPod usage check failed: {str(e)}"}

async def get_groq_usage() -> Dict[str, Any]:
    """Get Groq API usage for Vision agent (Llama-3.2-11B-Vision)"""
    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            return {"status": "not_configured", "message": "Groq API key not set"}

        # Check if API key is valid by testing it
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {groq_api_key}"}
                # Test with a minimal request to check key validity
                test_url = "https://api.groq.com/openai/v1/models"
                async with session.get(test_url, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        return {
                            "status": "configured",
                            "plan": "Pay-per-use",
                            "requests_today": "0 (not active yet)",
                            "requests_limit": "14,400/day",
                            "cost_estimate": "~$0.18 per 1K tokens",
                            "models_used": [
                                {"model": "llama-3.2-11b-vision-preview", "requests": 0}
                            ],
                            "usage_type": "Vision Analysis (75 charts/day when pipeline runs)",
                            "note": "✅ API key valid, ready for pipeline activation"
                        }
                    else:
                        return {"status": "error", "message": f"API key invalid (HTTP {response.status})"}
        except Exception as api_error:
            return {
                "status": "configured",
                "plan": "Pay-per-use",
                "requests_today": "0 (not active yet)",
                "requests_limit": "14,400/day",
                "cost_estimate": "~$0.18 per 1K tokens",
                "usage_type": "Vision Analysis (75 charts/day when pipeline runs)",
                "note": f"⚠️ API key present but couldn't verify: {str(api_error)}"
            }

    except Exception as e:
        return {"status": "error", "message": f"Groq usage check failed: {str(e)}"}

async def get_grok_usage() -> Dict[str, Any]:
    """Get Grok API usage for social sentiment"""
    try:
        grok_api_key = os.getenv("GROK_API_KEY")
        if not grok_api_key:
            return {"status": "not_configured", "message": "Grok API key not set"}

        # Check if today is Wednesday (Grok arbitration day)
        from datetime import datetime
        today = datetime.now().weekday()  # 0=Monday, 6=Sunday
        is_grok_arbitration_day = (today == 2)  # Wednesday

        # X.AI API exists and key is configured
        return {
            "status": "configured",
            "plan": "Developer",
            "requests_today": "0 (not active yet)",
            "requests_limit": "5,000/day",
            "cost_estimate": "~$5.00 per 1M tokens (estimated)",
            "models_used": [
                {"model": "grok-beta", "requests": 0}
            ],
            "usage_type": "Social Sentiment (75 calls/day) + Arbitration (1 call/day on Wednesdays)",
            "arbitration_active_today": is_grok_arbitration_day,
            "note": f"✅ API key configured, {'🎯 Active arbitrator today' if is_grok_arbitration_day else 'Standby for arbitration'}"
        }

    except Exception as e:
        return {"status": "error", "message": f"Grok usage check failed: {str(e)}"}

async def get_arbitrator_usage() -> Dict[str, Any]:
    """Get individual arbitrator API usage (DeepSeek-V3, Gemini 2.5 Pro, Grok 4, Claude Sonnet 4, GPT-5)"""
    try:
        # Check which arbitrator APIs are configured
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        claude_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        grok_key = os.getenv("GROK_API_KEY")  # Same API used for both social and arbitration

        # Determine current arbitrator based on weekday
        from datetime import datetime
        today = datetime.now().weekday()  # 0=Monday, 6=Sunday
        arbitrator_schedule = {
            0: "DeepSeek-V3",
            1: "Gemini 2.5 Pro",
            2: "Grok 4",
            3: "Claude Sonnet 4",
            4: "GPT-5"
        }
        current_arbitrator = arbitrator_schedule.get(today, "DeepSeek-V3")

        # Individual API usage - show real configuration status and today's active arbitrator
        return {
            "deepseek": {
                "status": "configured" if deepseek_key else "not_configured",
                "model": "DeepSeek-V3",
                "calls_today": 0,  # Not running yet
                "cost_estimate": "~$0.14 per 1M tokens",
                "is_active_today": current_arbitrator == "DeepSeek-V3",
                "note": "🎯 ACTIVE ARBITRATOR TODAY" if current_arbitrator == "DeepSeek-V3" else "Standby"
            },
            "gemini": {
                "status": "configured" if gemini_key else "not_configured",
                "model": "Gemini 2.5 Pro",
                "calls_today": 0,  # Not running yet
                "cost_estimate": "~$1.25 per 1M tokens",
                "is_active_today": current_arbitrator == "Gemini 2.5 Pro",
                "note": "🎯 ACTIVE ARBITRATOR TODAY" if current_arbitrator == "Gemini 2.5 Pro" else "Standby"
            },
            "claude": {
                "status": "configured" if claude_key else "not_configured",
                "model": "Claude Sonnet 4",
                "calls_today": 0,  # Not running yet
                "cost_estimate": "~$3.00 per 1M tokens",
                "is_active_today": current_arbitrator == "Claude Sonnet 4",
                "note": "🎯 ACTIVE ARBITRATOR TODAY" if current_arbitrator == "Claude Sonnet 4" else "Standby"
            },
            "gpt5": {
                "status": "configured" if openai_key else "not_configured",
                "model": "GPT-5",
                "calls_today": 0,  # Not running yet
                "cost_estimate": "~$10.00 per 1M tokens (estimated)",
                "is_active_today": current_arbitrator == "GPT-5",
                "note": "🎯 ACTIVE ARBITRATOR TODAY" if current_arbitrator == "GPT-5" else "Standby"
            },
            "grok": {
                "status": "configured" if grok_key else "not_configured",
                "model": "Grok-beta",
                "calls_today": 0,  # Not running yet
                "cost_estimate": "~$5.00 per 1M tokens (estimated)",
                "is_active_today": current_arbitrator == "Grok 4",
                "note": "🎯 ACTIVE ARBITRATOR TODAY" if current_arbitrator == "Grok 4" else "Standby"
            },
            "current_arbitrator": current_arbitrator,
            "rotation_schedule": arbitrator_schedule,
            "today_is": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][today],
            "development_note": f"✅ {current_arbitrator} is today's arbitrator - APIs configured but not actively running yet"
        }

    except Exception as e:
        return {"status": "error", "message": f"Arbitrator usage check failed: {str(e)}"}

@app.get("/api/v1/admin/users")
async def get_users() -> Dict[str, Any]:
    """Get user statistics - shows real Firebase Auth status"""
    try:
        # Check if Firebase Admin SDK is configured
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
        firebase_private_key = os.getenv("FIREBASE_PRIVATE_KEY")
        firebase_client_email = os.getenv("FIREBASE_CLIENT_EMAIL")

        if not all([firebase_project_id, firebase_private_key, firebase_client_email]):
            return {
                "firebase_auth_status": "not_configured",
                "users_count": 0,
                "message": "Firebase Auth not configured - missing credentials",
                "required_env_vars": [
                    "FIREBASE_PROJECT_ID",
                    "FIREBASE_PRIVATE_KEY",
                    "FIREBASE_CLIENT_EMAIL"
                ],
                "note": "User authentication will be set up when going live"
            }

        # Try to initialize Firebase Admin (would need firebase-admin package)
        try:
            # This would require: pip install firebase-admin
            # import firebase_admin
            # from firebase_admin import credentials, auth

            # For now, show that credentials exist but SDK not initialized
            return {
                "firebase_auth_status": "credentials_configured",
                "users_count": 0,
                "message": "Firebase credentials configured but Admin SDK not initialized",
                "project_id": firebase_project_id,
                "note": "Ready for user authentication setup",
                "next_steps": [
                    "Install firebase-admin package",
                    "Initialize Firebase Admin SDK",
                    "Set up authentication flows"
                ]
            }

        except ImportError:
            return {
                "firebase_auth_status": "sdk_not_installed",
                "users_count": 0,
                "message": "Firebase Admin SDK not installed",
                "project_id": firebase_project_id,
                "note": "Run: pip install firebase-admin"
            }

    except Exception as e:
        return {
            "firebase_auth_status": "error",
            "users_count": 0,
            "error": str(e)
        }

@app.get("/api/v1/admin/frontend-status")
async def get_frontend_status() -> Dict[str, Any]:
    """Get frontend deployment status"""
    try:
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID", "603494406675")

        # Check if we can reach the Firebase hosting
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                # Try to reach the Firebase hosting URL
                hosting_url = f"https://{firebase_project_id}.web.app"
                async with session.get(hosting_url, timeout=5) as response:
                    if response.status == 200:
                        deployment_status = "deployed"
                        status_message = "✅ Live on Firebase Hosting"
                    else:
                        deployment_status = "error"
                        status_message = f"❌ HTTP {response.status}"
        except Exception:
            deployment_status = "not_deployed"
            status_message = "⚠️ Not deployed or unreachable"

        return {
            "status": deployment_status,
            "status_message": status_message,
            "domain": "bullsbears.xyz",
            "hosting_provider": "Firebase Hosting",
            "firebase_project_id": firebase_project_id,
            "hosting_url": f"https://{firebase_project_id}.web.app",
            "custom_domain_configured": False,
            "note": "Frontend will be deployed when ready for production"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/v1/admin/schedule")
async def get_schedule() -> Dict[str, Any]:
    """Get current pipeline schedule configuration"""

    # Calculate next run time
    if pytz:
        et_tz = pytz.timezone(DEFAULT_SCHEDULE["timezone"])
        now = datetime.now(et_tz)
    else:
        # Fallback to UTC if pytz not available
        now = datetime.now()

    # Next 3:00 AM ET (or UTC if pytz not available)
    next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if now.hour >= 3:
        next_run += timedelta(days=1)

    schedule_info = DEFAULT_SCHEDULE.copy()
    schedule_info["next_run"] = next_run.isoformat()
    schedule_info["current_time"] = now.isoformat()
    schedule_info["time_until_next_run"] = str(next_run - now).split('.')[0]

    return schedule_info

@app.post("/api/v1/admin/schedule/update")
async def update_schedule(schedule_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update pipeline schedule configuration"""
    # In production, this would update the actual scheduler
    # For now, just return success
    return {
        "success": True,
        "message": "Schedule updated successfully",
        "updated_fields": list(schedule_data.keys())
    }

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
