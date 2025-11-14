#!/usr/bin/env python3
"""
BullsBears Celery Beat – FINAL v3.3 (November 14, 2025)
FULLY AUTOMATIC – ZERO manual runs – $0 RunPod idle cost
"""

from celery.schedules import crontab
from .celery import celery_app

# =============================================================================
# NIGHTLY LEARNING – 4:00 AM (BEFORE DAILY PIPELINE)
# =============================================================================
# Learner reviews yesterday's outcomes and updates weights/prompts
# This runs BEFORE the daily pipeline so updated weights are used at 8:10 AM

celery_app.conf.beat_schedule = {
    # Nightly learning - Part 1: Review outcomes
    "nightly-learner-review": {
        "task": "tasks.trigger_learner",
        "schedule": crontab(hour=4, minute=1, day_of_week="*"),  # 4:01 AM
        "options": {"queue": "runpod"},
    },
    # Nightly learning - Part 2: Update weights/prompts
    "nightly-learner-update": {
        "task": "tasks.trigger_learner",
        "schedule": crontab(hour=4, minute=15, day_of_week="*"),  # 4:15 AM
        "options": {"queue": "runpod"},
    },

    # =============================================================================
    # DAILY PIPELINE – 8:00 AM - 8:25 AM (EST/EDT) – 100% AUTOMATIC
    # =============================================================================

    # 8:00 AM - Update all stock data from FMP
    "fmp-daily-delta": {
        "task": "tasks.fmp_delta_update",
        "schedule": crontab(hour=8, minute=0, day_of_week="*"),
        "options": {"queue": "data"},
    },

    # 8:05 AM - Filter NASDAQ → ACTIVE tier (~1,700 stocks)
    "build-active-symbols": {
        "task": "tasks.build_active_symbols",
        "schedule": crontab(hour=8, minute=5, day_of_week="*"),
        "options": {"queue": "data"},
    },

    # 8:10 AM - Prescreen: ACTIVE → SHORT_LIST (75 stocks) using RunPod
    "prescreen-shortlist": {
        "task": "tasks.run_prescreen",
        "schedule": crontab(hour=8, minute=10, day_of_week="*"),
        "options": {"queue": "runpod"},
    },

    # 8:15 AM - Generate 75 charts for SHORT_LIST
    "generate-charts": {
        "task": "tasks.generate_charts",
        "schedule": crontab(hour=8, minute=15, day_of_week="*"),
        "options": {"queue": "vision"},
    },

    # 8:16 AM - Vision analysis using Groq API
    "groq-vision": {
        "task": "tasks.run_groq_vision",
        "schedule": crontab(hour=8, minute=16, day_of_week="*"),
        "options": {"queue": "vision"},
    },

    # 8:17 AM - Social sentiment using Grok API
    "grok-social-context": {
        "task": "tasks.run_grok_social",
        "schedule": crontab(hour=8, minute=17, day_of_week="*"),
        "options": {"queue": "social"},
    },

    # 8:20 AM - Final arbitrator: Select 3-6 picks using RunPod
    "final-arbitration": {
        "task": "tasks.run_arbitrator",
        "schedule": crontab(hour=8, minute=20, day_of_week="*"),
        "options": {"queue": "arbitrator"},
    },

    # 8:25 AM - Publish final picks to Firebase
    "publish-picks": {
        "task": "tasks.publish_to_firebase",
        "schedule": crontab(hour=8, minute=25, day_of_week="*"),
        "options": {"queue": "publish"},
    },

    # =============================================================================
    # CONTINUOUS TASKS
    # =============================================================================

    # Every 5 minutes - Full stats refresh
    "update-statistics-cache": {
        "task": "tasks.update_statistics_cache",
        "schedule": 300.0,
        "options": {"queue": "data"},
    },

    # Every 2 minutes (market hours only) - Badge data for UI
    "update-badge-data-cache": {
        "task": "tasks.update_badge_data_cache",
        "schedule": crontab(minute="*/2", hour="14-20", day_of_week="1-5"),
        "options": {"queue": "data"},
    },

    # Every hour - Data integrity validation
    "validate-statistics-accuracy": {
        "task": "tasks.validate_statistics_accuracy",
        "schedule": 3600.0,
        "options": {"queue": "data"},
    },

    # Daily at 12 PM ET - Monitoring report
    "generate-statistics-report": {
        "task": "tasks.generate_statistics_report",
        "schedule": crontab(hour=17, minute=0, day_of_week="*"),
        "options": {"queue": "data"},
    },
}

# =============================================================================
# TASK ROUTES
# =============================================================================
celery_app.conf.task_routes.update({
    "tasks.fmp_delta_update": {"queue": "data"},
    "tasks.build_active_symbols": {"queue": "data"},
    "tasks.run_prescreen": {"queue": "runpod"},
    "tasks.generate_charts": {"queue": "vision"},
    "tasks.run_groq_vision": {"queue": "vision"},
    "tasks.run_grok_social": {"queue": "social"},
    "tasks.run_arbitrator": {"queue": "arbitrator"},
    "tasks.publish_to_firebase": {"queue": "publish"},
    "tasks.trigger_learner": {"queue": "runpod"},
})

# =============================================================================
# COST CONTROL - Maximum task execution times
# =============================================================================
celery_app.conf.task_time_limit = {
    "tasks.run_prescreen": 900,        # 15 min max - RunPod prescreen
    "tasks.run_arbitrator": 600,       # 10 min max - RunPod arbitrator
    "tasks.trigger_learner": 900,      # 15 min max - RunPod learning
    "tasks.run_groq_vision": 300,      # 5 min max - Groq API (75 parallel calls)
    "tasks.run_grok_social": 300,      # 5 min max - Grok API (75 parallel calls)
}