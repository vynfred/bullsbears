# backend/app/services/cloud_agents/arbitrator_agent.py
"""
Final Arbitrator Agent – BullsBears v5 (December 2025)
One model to rule them all: OpenAI gpt-oss-120b on Fireworks
No rotation. No fallback. Maximum win rate + nightly learner compounding.
"""

import httpx
import json
import logging
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

# Hot-reloaded files (updated nightly by learner)
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "arbitrator_prompt.txt"
BIAS_PATH   = Path(__file__).parent.parent / "prompts" / "arbitrator_bias.json"

# Permanent winner – locked in forever
MODEL = "accounts/fireworks/models/gpt-oss-120b"


async def get_final_picks(phase_data: dict) -> dict:
    """
    Single call to the best model in 2025.
    Returns 3–6 final picks with targets, confidence, reasoning.
    """
    # Load fresh prompt + learned bias (hot-reloaded nightly)
    base_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    
    try:
        bias = json.loads(BIAS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        bias = {"social_score_multiplier": 1.2, "confidence_calibration": 0.75}

    # Separate bullish and bearish candidates
    short_list = phase_data.get("short_list", [])
    bullish_candidates = [s for s in short_list if s.get("direction") == "bull"]
    bearish_candidates = [s for s in short_list if s.get("direction") == "bear"]

    # Build enhanced prompt with learned insights
    enhanced_prompt = f"""{base_prompt}

LEARNED ARBITRATOR BIAS (updated nightly):
Social Score ×{bias.get("social_score_multiplier", 1.2)}
Confidence Calibration: {bias.get("confidence_calibration", 0.75)}

=== BULLISH CANDIDATES ({len(bullish_candidates)} stocks with direction="bull") ===
{json.dumps(bullish_candidates[:20], indent=2, default=str)}

=== BEARISH CANDIDATES ({len(bearish_candidates)} stocks with direction="bear") ===
{json.dumps(bearish_candidates[:20], indent=2, default=str)}

Select TOP 3 from each category. Return valid JSON only.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are the final BullsBears v5 arbitrator. Output ONLY valid JSON."},
            {"role": "user", "content": enhanced_prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {settings.FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.fireworks.ai/inference/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

        # Parse JSON safely
        result = json.loads(content)
        result.setdefault("model_used", MODEL)
        result.setdefault("provider", "fireworks")
        logger.info(f"Arbitrator success: {len(result.get('final_picks', []))} picks using gpt-oss-120b")
        return result

    except Exception as e:
        logger.error(f"Arbitrator failed: {e}")
        # Critical safety net – never let pipeline die
        return {
            "final_picks": [],
            "model_used": MODEL,
            "provider": "fireworks",
            "error": str(e),
            "fallback_used": True
        }