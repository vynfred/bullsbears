# backend/app/models/__init__.py
"""
SQLAlchemy models – BullsBears v5
Absolute imports only — REQUIRED for Render workers
"""

from app.core.database import Base
from .stock_classifications import (
    StockClassification,
    ShortlistCandidate,
)

__all__ = [
    "Base",
    "StockClassification",
    "ShortlistCandidate",
]