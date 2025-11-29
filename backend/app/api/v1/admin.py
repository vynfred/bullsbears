# backend/app/api/v1/admin.py
"""
BullsBears Admin API - Secret admin endpoints
Only accessible via secret URL known to owner
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin credentials from environment
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "hellovynfred@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "bullsbears2025")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str | None = None


@router.post("/auth/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """Admin login - validates credentials"""
    if request.email == ADMIN_EMAIL and request.password == ADMIN_PASSWORD:
        # Simple token for now - in production use proper JWT
        return LoginResponse(
            success=True,
            message="Login successful",
            token="admin-session-token"
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/system/status")
async def get_system_status():
    """Get current system status"""
    from app.services.system_state import is_system_on
    
    system_on = await is_system_on()
    return {
        "system_on": system_on,
        "status": "ON" if system_on else "OFF"
    }


@router.post("/system/on")
async def turn_system_on():
    """Turn system ON"""
    from app.services.system_state import set_system_on
    
    await set_system_on(True)
    return {"success": True, "message": "System turned ON"}


@router.post("/system/off")
async def turn_system_off():
    """Turn system OFF"""
    from app.services.system_state import set_system_on
    
    await set_system_on(False)
    return {"success": True, "message": "System turned OFF"}

