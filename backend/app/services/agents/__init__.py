"""
BullsBears AI Agents Package
Optimized 8-agent system for stock analysis and prediction
"""

from .base_agent import BaseAgent, AgentResponse
from .predictor_agents import (
    BullPredictorTechnical,
    BullPredictorFundamental,
    BearPredictorTechnical,
    BearPredictorSentiment
)
from .specialized_agents import VisionAgent, ArbitratorAgent, KillSwitchAgent, PreFilterAgent
from .enhanced_agents import NewsAgent, RiskAgent, BearPredictorFundamental

__all__ = [
    'BaseAgent',
    'AgentResponse',
    'PreFilterAgent',
    'BullPredictorTechnical',
    'BullPredictorFundamental',
    'BearPredictorTechnical',
    'BearPredictorSentiment',
    'BearPredictorFundamental',
    'NewsAgent',
    'VisionAgent',
    'RiskAgent',
    'ArbitratorAgent',
    'KillSwitchAgent'
]
