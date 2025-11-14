#!/usr/bin/env python3
"""
BullsBears Tasks - All Celery scheduled tasks
"""

from .fmp_delta_update import fmp_delta_update
from .build_active_symbols import build_active_symbols
from .run_prescreen import run_prescreen
from .generate_charts import generate_charts
from .run_groq_vision import run_groq_vision
from .run_grok_social import run_grok_social
from .run_arbitrator import run_arbitrator
from .publish_to_firebase import publish_to_firebase
from .run_learner import trigger_learner
from .statistics_tasks import (
    update_statistics_cache,
    update_badge_data_cache,
    validate_statistics_accuracy,
    generate_statistics_report
)

__all__ = [
    # Daily pipeline (8:00 AM - 8:25 AM)
    "fmp_delta_update",           # 8:00 AM - Update stock data from FMP
    "build_active_symbols",        # 8:05 AM - Filter NASDAQ → ACTIVE tier
    "run_prescreen",               # 8:10 AM - ACTIVE → SHORT_LIST (75 stocks)
    "generate_charts",             # 8:15 AM - Generate 75 charts
    "run_groq_vision",             # 8:16 AM - Vision analysis (Groq)
    "run_grok_social",             # 8:17 AM - Social sentiment (Grok)
    "run_arbitrator",              # 8:20 AM - Final pick selection (RunPod)
    "publish_to_firebase",         # 8:25 AM - Publish picks to Firebase

    # Nightly learning (4:00 AM)
    "trigger_learner",             # 4:01 AM & 4:15 AM - Review outcomes & update weights

    # Continuous tasks
    "update_statistics_cache",     # Every 5 min
    "update_badge_data_cache",     # Every 2 min
    "validate_statistics_accuracy", # Every hour
    "generate_statistics_report",  # Daily report
]