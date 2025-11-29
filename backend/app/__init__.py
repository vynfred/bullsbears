# backend/app/__init__.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="BullsBears v5 API",
    version="5.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# Allow your Firebase-hosted frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production replace with your actual domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers after app creation to avoid circular imports
from .api.v1 import analytics, stocks, watchlist, internal, admin

app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["watchlist"])
app.include_router(internal.router, prefix="/api/v1/internal", tags=["internal"])
app.include_router(admin.router, prefix="/api/v1")
