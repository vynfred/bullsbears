#!/usr/bin/env python3
"""
BullsBears Agents – FINAL v3.3 (November 12, 2025)
LEAN. AUTOMATIC. ONLY WHAT WE USE.
"""

from .arbitrator_agent import get_arbitrator_agent
from .social_agent import get_social_agent
from .vision_agent import get_vision_agent

__all__ = [
    "get_arbitrator_agent",
    "get_social_agent",
    "get_vision_agent",
]