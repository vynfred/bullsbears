#!/usr/bin/env python3
"""
BullsBears Celery Beat – FINAL v3.3 (November 11, 2025)
FULLY AUTOMATIC – ZERO manual runs – $0 RunPod idle cost
"""

from celery.schedules import crontab
from .celery import celery_app  # ← imports your existing app

# =============================================================================
# DAILY PIPELINE – Atlanta, GA (EST/EDT) – 100% AUTOMATIC
# =============================================================================

celery_app.conf.beat_schedule = {
    "fmp-daily-delta": {
        "task": "tasks.fmp_delta_update",
        "schedule": crontab(hour=8, minute=0, day_of_week="*"),
        "options": {"queue": "data"},
    },
    "build-active-tickers": {
        "task": "tasks.build_active_tickers",
        "schedule": crontab(hour=8, minute=5, day_of_week="*"),
        "options": {"queue": "data"},
    },
    "finma-prescreen-and-learn": {
        "task": "tasks.run_finma_and_brain",
        "schedule": crontab(hour=8, minute=10, day_of_week="*"),  # 3:10 AM ET
        "options": {"queue": "runpod"},
    },
    "generate-charts": {
        "task": "tasks.generate_charts",
        "schedule": crontab(hour=8, minute=15, day_of_week="*"),
        "options": {"queue": "vision"},
    },
    "groq-vision": {
        "task": "tasks.run_groq_vision",
        "schedule": crontab(hour=8, minute=16, day_of_week="*"),
        "options": {"queue": "vision"},
    },
    "grok-social-context": {
        "task": "tasks.run_grok_social",
        "schedule": crontab(hour=8, minute=17, day_of_week="*"),
        "options": {"queue": "social"},
    },
    "final-arbitration": {
        "task": "tasks.run_arbitrator",
        "schedule": crontab(hour=8, minute=20, day_of_week="*"),
        "options": {"queue": "arbitrator"},
    },
    "publish-picks": {
        "task": "tasks.publish_to_firebase",
        "schedule": crontab(hour=8, minute=25, day_of_week="*"),
        "options": {"queue": "publish"},
    },
    # Every 5 minutes
"update-statistics-cache": {
    "task": "tasks.update_statistics_cache",
    "schedule": 300.0,
    "options": {"queue": "data"},
},

# Every 2 minutes (market hours only)
"update-badge-data-cache": {
    "task": "tasks.update_badge_data_cache",
    "schedule": crontab(minute="*/2", hour="14-20", day_of_week="1-5"),
    "options": {"queue": "data"},
},

# Every hour
"validate-statistics-accuracy": {
    "task": "tasks.validate_statistics_accuracy",
    "schedule": 3600.0,
    "options": {"queue": "data"},
},

# Daily at 12 PM ET
"generate-statistics-report": {
    "task": "tasks.generate_statistics_report",
    "schedule": crontab(hour=17, minute=0, day_of_week="*"),  # 12 PM ET
    "options": {"queue": "data"},
},
}

# =============================================================================
# UPDATE YOUR EXISTING ROUTES
# =============================================================================
celery_app.conf.task_routes.update({
    "tasks.fmp_delta_update": {"queue": "data"},
    "tasks.build_active_tickers": {"queue": "data"},
    "tasks.run_finma_and_brain": {"queue": "runpod"},
    "tasks.generate_charts": {"queue": "vision"},
    "tasks.run_groq_vision": {"queue": "vision"},
    "tasks.run_grok_social": {"queue": "social"},
    "tasks.run_arbitrator": {"queue": "arbitrator"},
    "tasks.publish_to_firebase": {"queue": "publish"},
})

# =============================================================================
# COST CONTROL
# =============================================================================
celery_app.conf.task_time_limit = {
    "tasks.run_finma_and_brain": 900,  # 15 min max
}
from app.tasks.run_learner import run_learner

# app/core/celery_scheduler.py
from celery.schedules import crontab
from app.tasks.run_learner import trigger_learner

beat_schedule = {
    "nightly-learner": {
        "task": "app.tasks.run_learner.trigger_learner",
        "schedule": crontab(hour=4, minute=1),
    },
}