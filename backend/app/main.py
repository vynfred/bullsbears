#!/usr/bin/env python3
"""
BullsBears Backend – FINAL v3.3 (November 12, 2025)
Minimal FastAPI for health + Firebase + badges
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .core.config import settings
from .core.database import init_db, close_db
from .core.redis_client import redis_client
from .services.statistics_service import StatisticsService

# Structured logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="BullsBears v3.3",
    version="3.3.0",
    docs_url="/docs" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()
    await redis_client.connect()
    logger.info("BullsBears v3.3 API ready")

@app.on_event("shutdown")
async def shutdown():
    await close_db()
    await redis_client.disconnect()

@app.get("/")
async def root():
    return {"message": "BullsBears v3.3 API", "version": "3.3.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.3.0"}

@app.get("/api/v1/badge-data")
async def get_badge_data():
    stats = StatisticsService()
    return await stats.refresh_badge_data()

@app.get("/api/v1/picks/latest")
async def get_latest_picks():
    from .services.firebase_service import FirebaseService
    async with FirebaseService() as fb:
        data = await fb.get_latest_picks()
        return data or {"picks": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)