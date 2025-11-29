# app/api/v1/__init__.py
from .analytics import router as analytics_router
from .stocks import router as stocks_router
from .watchlist import router as watchlist_router
from .internal import router as internal_router
from .admin import router as admin_router

__all__ = [
    "analytics_router",
    "stocks_router",
    "watchlist_router",
    "internal_router",
    "admin_router",
]