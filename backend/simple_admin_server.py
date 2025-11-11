#!/usr/bin/env python3
"""
Simple BullsBears Admin Dashboard
Minimal dependencies - just monitoring and controls
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI(title="BullsBears Admin Dashboard")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "app" / "templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("simple_admin.html", {"request": request})

@app.get("/api/status")
async def get_system_status():
    """Get system status without complex dependencies"""
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "system": "operational",
        "connections": {},
        "pipeline": {
            "enabled": False,
            "last_run": None,
            "status": "disabled"
        },
        "data": {
            "symbols_tracked": 0,
            "last_update": None
        }
    }
    
    # Test basic connections
    status["connections"]["database"] = await test_database_simple()
    status["connections"]["fmp_api"] = test_fmp_api()
    status["connections"]["runpod"] = test_runpod_simple()
    status["connections"]["firebase"] = test_firebase_simple()
    
    return status

async def test_database_simple():
    """Simple database connection test"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {"status": "error", "message": "DATABASE_URL not configured"}
        
        # Just check if we can import asyncpg and parse the URL
        import asyncpg
        return {"status": "configured", "message": "Database URL configured"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def test_fmp_api():
    """Test FMP API key"""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return {"status": "error", "message": "FMP_API_KEY not configured"}
    
    return {"status": "configured", "message": f"API key configured ({api_key[:8]}...)"}

def test_runpod_simple():
    """Test RunPod configuration"""
    api_key = os.getenv("RUNPOD_API_KEY")
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
    
    if not api_key or not endpoint_id:
        return {"status": "error", "message": "RunPod credentials not configured"}
    
    return {"status": "configured", "message": f"Endpoint: {endpoint_id[:8]}..."}

def test_firebase_simple():
    """Test Firebase configuration"""
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    if not project_id:
        return {"status": "error", "message": "Firebase not configured"}
    
    return {"status": "configured", "message": f"Project: {project_id}"}

@app.post("/api/pipeline/enable")
async def enable_pipeline():
    """Enable the data pipeline"""
    return {"status": "success", "message": "Pipeline enabled (placeholder)"}

@app.post("/api/pipeline/disable")
async def disable_pipeline():
    """Disable the data pipeline"""
    return {"status": "success", "message": "Pipeline disabled (placeholder)"}

@app.post("/api/bootstrap/start")
async def start_bootstrap():
    """Start database bootstrap"""
    return {"status": "success", "message": "Bootstrap started (placeholder)"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    print("🚀 Starting Simple BullsBears Admin Dashboard")
    print("📊 Dashboard: http://localhost:8001")
    print("🔧 API docs: http://localhost:8001/docs")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
