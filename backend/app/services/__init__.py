#!/usr/bin/env python3
"""
BullsBears Services – FINAL v3.3 (November 12, 2025)
LEAN. AUTOMATIC. ONLY WHAT WE USE.
"""

# Data
from .fmp_data_ingestion import get_fmp_ingestion
from .chart_generator import get_chart_generator

# Core Services
from .prescreen import PrescreenAgent
from .kill_switch_service import KillSwitchService

# Agents (API calls)
from .agents.arbitrator_agent import get_arbitrator_agent
from .learner import run_nightly_learning  # ← DB-based learner
from .agents.social_agent import get_social_agent
from .agents.vision_agent import get_vision_agent

# Output
from .push_picks_to_firebase import push_picks_to_firebase

__all__ = [
    "get_fmp_ingestion",
    "get_chart_generator",
    "PrescreenAgent",
    "KillSwitchService",
    "get_arbitrator_agent",
    "run_nightly_learning",        # ← NEW: DB learner
    "get_social_agent",
    "get_vision_agent",
    "push_picks_to_firebase",
]