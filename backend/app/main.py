# backend/app/main.py
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Import app from __init__.py (which creates it and adds routers)
from . import app

# Optional: health check endpoint Render loves
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": "BullsBears v5",
        "version": "5.0.0",
        "environment": os.getenv("ENVIRONMENT", "dev")
    }

# Optional: root redirect to docs
@app.get("/")
async def root():
    return {"message": "BullsBears v5 API – go to /docs", "version": "5.0.0"}

# Graceful startup/shutdown if you ever need it
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown (e.g. close DB pools if you add them later)

app.router.lifespan_context = lifespan

# Export for Render
__all__ = ["app"]