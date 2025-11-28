#!/usr/bin/env python3
"""
BullsBears Celery Worker - Render Edition
Starts all background tasks for the trading pipeline
"""
from app.core.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()
