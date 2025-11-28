# backend/app/services/cloud_agents/__init__.py
"""
Cloud Agents – BullsBears v5
Function-based only. No classes.
"""

from .arbitrator_agent import get_final_picks
from .social_agent import run_social_analysis
from .vision_agent import run_vision_analysis

__all__ = [
    "get_final_picks",
    "run_social_analysis",
    "run_vision_analysis",
]