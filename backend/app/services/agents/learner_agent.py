#!/usr/bin/env python3
"""
LearnerAgent v3.3 – November 10, 2025
Analyzes all 75 SHORT_LIST candidates → nightly hot-reloads 3 files
No Ollama. No parsing. Pure data-driven.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from ..candidate_tracking_service import get_candidate_tracking_service

logger = logging.getLogger(__name__)

class LearnerAgent:
    """One job: 4:01 AM → make tomorrow's bot smarter"""

    def __init__(self):
        self.tracking = None
        self.history_dir = Path("/workspace/bullsbears/backend/app/services/agents/learning_history")
        self.history_dir.mkdir(exist_ok=True)

    async def initialize(self):
        self.tracking = await get_candidate_tracking_service()

    async def generate_finma_prompt(self) -> str:
        """Generate new FinMA-7b prescreen prompt with RECENT LEARNER INSIGHTS"""
        insights = await self._get_recent_insights()
        return f"""You are FinMA-7b, elite explosive-move hunter for BullsBears.xyz.
MISSION: From ~1,700 ACTIVE tickers, select EXACTLY 75 SHORT_LIST candidates with highest ≥20% move probability in 5 days.

RECENT LEARNER INSIGHTS (updated nightly by BrainAgent):
{insights}

SELECTION CRITERIA:
- Prioritize MULTIPLE converging signals
- Boost tickers with RECENT LEARNER INSIGHTS matches
- Balance bullish/bearish (~50/50)
- Rank purely by estimated edge

RETURN VALID JSON ONLY:
{{
  "filtered_tickers": ["NVDA","TSLA",...],
  "summary": "75 selected. Dominant signals: ...",
  "top_10_with_scores": [...]
}}
"""

    async def generate_weights(self) -> Dict[str, Any]:
        """Generate new weights.json with vision + arbitrator bias"""
        retro = await self.tracking.get_30day_performance()
        vision_weights = await self._rank_vision_flags(retro)
        arbitrator_bias = await self._rank_arbitrators(retro)

        return {
            **await self._get_banner(),
            "feature_weights": await self._rank_features(retro),
            "vision_flag_weights": vision_weights,
            "pattern_multipliers": await self._mine_patterns(retro),
            "arbitrator_rotation_bias": arbitrator_bias,
            "learning_metadata": {
                "last_updated": datetime.now().isoformat(),
                "moon_capture_rate": retro.get("moon_capture_rate", 0.0),
                "rug_capture_rate": retro.get("rug_capture_rate", 0.0),
                "total_candidates": retro.get("total_candidates", 0)
            }
        }

    async def rank_arbitrators(self) -> Dict[str, float]:
        """Rank rotating arbitrators by hit rate"""
        retro = await self.tracking.get_30day_performance()
        bias = {}
        for model in ["DeepSeek-V3", "Gemini 2.5 Pro", "Grok 4", "Claude Sonnet 4", "GPT-5"]:
            hits = retro["arbitrator_hits"].get(model, 0)
            total = retro["arbitrator_total"].get(model, 1)
            bias[model] = max(0.8, min(1.3, hits / total * 1.2))  # 0.8–1.3 range
        return bias

    async def _get_recent_insights(self) -> str:
        retro = await self.tracking.get_30day_performance()
        lines = [
            f"• volume_shelf_breakout + social_score ≥ 6 → {retro['patterns']['volume_social']}% hit rate",
            f"• wyckoff_phase_2 + earnings_3d → {retro['patterns']['wyckoff_earn']}% hit rate",
            f"• Best arbitrator: {max(retro['arbitrator_hits'], key=retro['arbitrator_hits'].get)}"
        ]
        return "\n".join(lines) if lines else "• No insights yet – learning in progress"

    async def _rank_vision_flags(self, retro: Dict) -> Dict[str, float]:
        flags = retro["vision_stats"]
        total = sum(flags.values()) or 1
        return {k: round(v / total * 1.5, 3) for k, v in flags.items()}

    async def _rank_features(self, retro: Dict) -> Dict[str, float]:
        # Simplified – in real use: SHAP values or correlation
        return {
            "volume_surge": 0.92,
            "gap_magnitude": 0.88,
            "rsi_2": 0.85,
            "social_sentiment": 0.82,
            "options_flow": 0.80
        }

    async def _mine_patterns(self, retro: Dict) -> Dict[str, float]:
        return retro.get("top_patterns", {
            "volume_shelf_plus_social_ge_6": 1.42,
            "wyckoff_phase_2_plus_earn_3d": 1.35
        })

    async def _get_banner(self) -> Dict[str, Any]:
        return {
            "_BRAINAGENT_AUTO_GENERATED": True,
            "_DO_NOT_EDIT": "Overwritten nightly at 4:01 AM ET",
            "_LAST_UPDATED": datetime.now().isoformat(),
            "_NEXT_UPDATE": (datetime.now() + timedelta(days=1)).replace(hour=4, minute=1).isoformat()
        }


# Global singleton
_learner_agent = None

async def get_learner_agent() -> LearnerAgent:
    global _learner_agent
    if _learner_agent is None:
        _learner_agent = LearnerAgent()
        await _learner_agent.initialize()
    return _learner_agent