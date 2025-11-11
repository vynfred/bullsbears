#!/usr/bin/env python3
"""
Final Arbitrator Agent - Single Cloud API Call (Phase 5)
7-day rotating frontier models with learned prompt enhancement
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any

from .brain_agent import get_brain_agent
from ..candidate_tracking_service import get_candidate_tracking_service

logger = logging.getLogger(__name__)

class ArbitratorAgent:
    """
    Phase 5: Final Arbitrator - Single cloud API call
    Uses learned insights from BrainAgent for enhanced selection
    """
    
    def __init__(self, cloud_model: str = "deepseek-v3"):
        self.agent_name = "ArbitratorAgent"
        self.cloud_model = cloud_model  # Rotates weekly
        self.brain_agent = None
        self.candidate_tracking = None
        
    async def initialize(self):
        """Initialize dependencies"""
        self.brain_agent = await get_brain_agent()
        self.candidate_tracking = await get_candidate_tracking_service()
    
    async def make_final_selection(self, phase_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Single cloud API call for final arbitration
        
        Args:
            phase_data: {
                'short_list': [...],      # 75 tickers from Phase 1
                'vision_flags': {...},    # 6 boolean flags per ticker  
                'social_scores': {...},   # -5 to +5 per ticker
                'market_context': {...}   # Kill-switch data
            }
            
        Returns:
            {
                'final_picks': [...],     # 3-6 picks with targets
                'reasoning': '...',
                'confidence_intervals': {...}
            }
        """
        
        if not self.brain_agent:
            await self.initialize()
        
        # Get learned arbitrator bias (hot-reloaded nightly)
        arbitrator_bias = await self._load_arbitrator_bias()
        
        # Build enhanced prompt with learned insights
        enhanced_prompt = await self._build_enhanced_prompt(phase_data, arbitrator_bias)
        
        # Single cloud API call
        result = await self._call_cloud_arbitrator(enhanced_prompt)
        
        # Track decision for learning
        await self._track_arbitration_decision(phase_data, result)
        
        return result
    
    async def _load_arbitrator_bias(self) -> Dict[str, Any]:
        """Load learned arbitrator bias (updated nightly by BrainAgent)"""
        try:
            bias_path = "/workspace/bullsbears/backend/app/services/agents/prompts/arbitrator_bias.json"
            with open(bias_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default bias if file doesn't exist yet
            return {
                "vision_flag_weights": [0.85, 0.78, 0.82, 0.71, 0.69, 0.74],
                "social_score_multiplier": 1.2,
                "sector_preferences": {"tech": 1.1, "energy": 0.9},
                "confidence_calibration": 0.75
            }
    
    async def _build_enhanced_prompt(self, phase_data: Dict[str, Any], bias: Dict[str, Any]) -> str:
        """Build prompt enhanced with learned insights"""
        
        return f"""
        You are the final arbitrator using {self.cloud_model}.
        
        LEARNED ARBITRATOR BIAS (updated nightly):
        Vision Flag Weights: {bias.get('vision_flag_weights', [])}
        Social Score Multiplier: {bias.get('social_score_multiplier', 1.0)}
        Sector Preferences: {json.dumps(bias.get('sector_preferences', {}), indent=2)}
        
        PHASE DATA:
        Short List (75): {json.dumps(phase_data.get('short_list', [])[:10], indent=2)}...
        Vision Flags: {json.dumps(phase_data.get('vision_flags', {}), indent=2)}
        Social Scores: {json.dumps(phase_data.get('social_scores', {}), indent=2)}
        
        SELECT 3-6 FINAL PICKS with:
        - Conservative/Expected/Optimistic targets
        - Support/Resistance levels  
        - Confidence intervals (0.0-1.0)
        - Time horizons (5-14 days)
        
        RETURN JSON ONLY:
        {{
          "final_picks": [
            {{
              "symbol": "NVDA",
              "targets": {{"conservative": 145, "expected": 155, "optimistic": 165}},
              "support_resistance": {{"support": 140, "resistance": 170}},
              "confidence": 0.82,
              "time_horizon_days": 7,
              "reasoning": "Strong vision flags + social score +4"
            }}
          ]
        }}
        """
    
    async def _call_cloud_arbitrator(self, prompt: str) -> Dict[str, Any]:
        """Make single cloud API call"""
        # Implementation depends on cloud provider
        # DeepSeek-V3, Gemini 2.5 Pro, Grok-4, etc.
        pass
    
    async def _track_arbitration_decision(self, phase_data: Dict[str, Any], result: Dict[str, Any]):
        """Track decision for nightly learning"""
        await self.candidate_tracking.track_arbitration_decision(
            short_list=phase_data.get('short_list', []),
            final_picks=result.get('final_picks', []),
            arbitrator_model=self.cloud_model,
            decision_timestamp=datetime.now()
        )
