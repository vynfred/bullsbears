#!/usr/bin/env python3
"""
BullsBears Services – FINAL v3.3 (November 14, 2025)
LEAN. AUTOMATIC. ONLY WHAT WE USE.
"""

# Data
from .fmp_data_ingestion import get_fmp_ingestion
from .stock_filter_service import get_stock_filter_service

# Core Services
from .cloud_agents.prescreen_agent import PrescreenAgent
from .kill_switch_service import KillSwitchService

# FIREWORKS.AI
from .cloud_agents.learner_agent import run_weekly_learner

# Output
from .push_picks_to_firebase import push_picks_to_firebase, FirebaseService

# System State
from .system_state import SystemState

# NOTE: ChartGenerator is defined inline in backend/app/tasks/generate_charts.py
# It's not a service - it's a task-specific class used only by the generate_charts task

__all__ = [
    "get_fmp_ingestion",
    "get_stock_filter_service",
    "PrescreenAgent",
    "KillSwitchService",
    "run_weekly_learner",
    "push_picks_to_firebase",
    "FirebaseService",
    "SystemState",
]
