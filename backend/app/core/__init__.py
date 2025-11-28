# backend/app/core/__init__.py
"""
BullsBears v5 Core – Render + Fireworks Edition (November 2025)
Clean. Minimal. Bulletproof.
"""

from .config import settings
from .database import get_db, close_db
from .celery_app import celery_app
from .firebase import db as firebase_db  # Realtime Database reference
from .system_state import SystemState

__all__ = [
    "settings",
    "get_db",
    "close_db",
    "celery_app",
    "firebase_db",
    "SystemState",
]