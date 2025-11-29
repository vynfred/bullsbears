# app/api/v1/internal.py
from fastapi import APIRouter, HTTPException
from app.services.system_state import is_system_on, set_system_on

router = APIRouter()


@router.get("/health")
async def internal_health():
    return {
        "status": "healthy",
        "app": "BullsBears v5 – Render Edition",
        "environment": "production",
        "database": "Render Postgres (internal)",
        "queue": "Render Redis (internal)",
        "llm": "Fireworks qwen2.5-72b-instruct",
        "vision": "Groq Llama-3.2-11B-Vision",
        "social": "Grok-4",
        "system_state": "ON" if await is_system_on() else "OFF",
    }


@router.post("/system/on")
async def turn_system_on():
    await set_system_on(True)
    return {"status": "System turned ON – daily pipeline will run at 8:00 AM ET"}


@router.post("/system/off")
async def turn_system_off():
    await set_system_on(False)
    return {"status": "System turned OFF – no pipeline until turned back on"}


@router.get("/system/status")
async def get_system_status():
    return {"system_on": await is_system_on()}