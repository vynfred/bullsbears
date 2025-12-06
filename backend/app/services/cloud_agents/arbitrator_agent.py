# backend/app/services/cloud_agents/arbitrator_agent.py
"""
Final Arbitrator Agent – BullsBears v5.1 (Dec 2025)
Primary: Grok 4.1-fast (xAI)
Failover: gpt-oss-120b (Fireworks)
Robust JSON parsing + no hard candidate limit
"""

import httpx
import json
import logging
import re
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "arbitrator_prompt.txt"
BIAS_PATH   = Path(__file__).parent.parent / "prompts" / "arbitrator_bias.json"

PROVIDERS = [
    {
        "name": "grok-4.1-fast",
        "model": "grok-4.1-fast",
        "base_url": "https://api.x.ai/v1",
        "api_key": settings.GROK_API_KEY,
    },
    {
        "name": "gpt-oss-120b",
        "model": "accounts/fireworks/models/gpt-oss-120b",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key": settings.FIREWORKS_API_KEY,
    },
]

def extract_json(text: str) -> str:
    """Extract JSON from LLM output, even if wrapped in markdown."""
    text = text.strip()
    text = re.sub(r"^```json\s*|```$", "", text, flags=re.MULTILINE)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found")
    return text[start:end]

async def call_provider(provider: dict, payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            f"{provider['base_url']}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

async def get_final_picks(phase_data: dict) -> dict:
    base_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    
    try:
        bias = json.loads(BIAS_PATH.read_text(encoding="utf-8"))
    except Exception:
        bias = {"social_score_multiplier": 1.2, "confidence_calibration": 0.75}

    short_list = phase_data.get("short_list", [])
    bullish_candidates = [s for s in short_list if s.get("direction") == "bull"]
    bearish_candidates = [s for s in short_list if s.get("direction") == "bear"]

    # Top 30 per direction (safe token limit)
    top_n = 30
    bullish_candidates = bullish_candidates[:top_n]
    bearish_candidates = bearish_candidates[:top_n]

    enhanced_prompt = f"""{base_prompt}

LEARNED ARBITRATOR BIAS (updated nightly):
Social Score ×{bias.get("social_score_multiplier", 1.2)}
Confidence Calibration: {bias.get("confidence_calibration", 0.75)}

=== BULLISH CANDIDATES ({len(bullish_candidates)}) ===
{json.dumps(bullish_candidates, indent=2, default=str)}

=== BEARISH CANDIDATES ({len(bearish_candidates)}) ===
{json.dumps(bearish_candidates, indent=2, default=str)}

Select TOP 3 from each. Return valid JSON with "final_picks" array.
"""

    payload_base = {
        "messages": [
            {"role": "system", "content": "You are the final BullsBears v5 arbitrator. Output ONLY valid JSON with a 'final_picks' array."},
            {"role": "user", "content": enhanced_prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 4096,
    }

    last_error = None
    for provider in PROVIDERS:
        if not provider["api_key"]:
            logger.info(f"Skipping {provider['name']} - no API key")
            continue
            
        payload = payload_base.copy()
        payload["model"] = provider["model"]

        try:
            logger.info(f"Arbitrator calling {provider['name']}...")
            response = await call_provider(provider, payload)
            content = response["choices"][0]["message"]["content"]

            clean_json = extract_json(content)
            result = json.loads(clean_json)

            result.setdefault("model_used", provider["model"])
            result.setdefault("provider", provider["name"])
            picks_count = len(result.get("final_picks", []))
            logger.info(f"Arbitrator success with {provider['name']}: {picks_count} picks")
            return result

        except Exception as e:
            last_error = e
            logger.warning(f"Arbitrator failed on {provider['name']}: {e}")
            continue

    logger.error(f"All providers failed. Last error: {last_error}")
    return {
        "final_picks": [],
        "model_used": "none",
        "provider": "failed",
        "error": str(last_error),
        "fallback_used": True
    }