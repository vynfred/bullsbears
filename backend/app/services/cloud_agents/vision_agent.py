# backend/app/services/cloud_agents/vision_agent.py
"""
Vision Agent – Fireworks.ai Qwen3-VL-30B-A3B (Phase 3)
Fetches chart images from Firebase Storage → sends to Fireworks Vision API
Returns 6 boolean pattern flags per chart
"""

import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import httpx
from app.core.config import settings
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

# Fireworks Vision API (Qwen3-VL-30B-A3B Thinking)
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
MODEL = "accounts/fireworks/models/qwen3-vl-30b-a3b-thinking"

# Hot-reloaded prompt
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "vision_prompt.txt"

# Default flags on failure - Advanced pattern flags
DEFAULT_FLAGS = {
    "volume_shelf_breakout": False,
    "wyckoff_phase_2": False,
    "spring_setup": False,
    "higher_high_higher_low": False,
    "vcp_tightness": False,
    "parabolic_curve": False,
    "stop_hunt_liquidity_grab": False,
    "dominant_pattern": "none",
    "trend_direction": "neutral",
}


async def run_vision_analysis(charts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Input: List of dicts with 'symbol' and 'chart_url' (Firebase Storage URL)
    Output: List with 'symbol' and 'vision_flags' (6 booleans)
    """
    logger.info(f"Vision agent: analyzing {len(charts)} charts via Fireworks Qwen3-VL-30B-A3B")

    # Reload prompt each run (hot-reload)
    prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()

    async with httpx.AsyncClient(timeout=60.0, limits=httpx.Limits(max_connections=20)) as client:
        tasks = [_analyze_one(client, item, prompt) for item in charts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    processed = []
    for item, result in zip(charts, results):
        symbol = item["symbol"]
        if isinstance(result, Exception):
            logger.error(f"Vision analysis failed for {symbol}: {result}")
            processed.append({"symbol": symbol, "vision_flags": DEFAULT_FLAGS.copy()})
        else:
            processed.append(result)

    # Store in DB
    await _store_vision_results(processed)

    success_count = sum(1 for p in processed if p["vision_flags"] != DEFAULT_FLAGS)
    logger.info(f"Vision analysis complete: {success_count}/{len(processed)} analyzed successfully")
    return processed


async def _analyze_one(client: httpx.AsyncClient, item: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    symbol = item["symbol"]
    chart_url = item["chart_url"]

    # Download chart image from Firebase Storage
    try:
        img_resp = await client.get(chart_url)
        img_resp.raise_for_status()
        base64_png = base64.b64encode(img_resp.content).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to download chart for {symbol}: {e}")
        raise

    # Send to Fireworks Vision API (Qwen3-VL-30B-A3B)
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Stock: {symbol}\n\n{prompt}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_png}"}
                    }
                ]
            }
        ],
        "temperature": 0.0,
        "max_tokens": 2048,  # Thinking model needs more tokens for reasoning + JSON output
    }

    try:
        resp = await client.post(
            FIREWORKS_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.FIREWORKS_API_KEY}",
                "Content-Type": "application/json"
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Parse JSON from response - for thinking models, look after </think> tag
        json_content = content
        if "</think>" in content:
            json_content = content.split("</think>")[-1].strip()

        # Strip markdown code blocks (```json ... ```)
        import re
        json_content = re.sub(r"^```json\s*|```$", "", json_content, flags=re.MULTILINE).strip()

        # Find the last JSON object (most reliable for thinking models)
        start = json_content.rfind("{")
        end = json_content.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON found in response: {content[:200]}")

        flags = json.loads(json_content[start:end])

        return {
            "symbol": symbol,
            "vision_flags": {
                "volume_shelf_breakout": bool(flags.get("volume_shelf_breakout", False)),
                "wyckoff_phase_2": bool(flags.get("wyckoff_phase_2", False)),
                "spring_setup": bool(flags.get("spring_setup", False)),
                "higher_high_higher_low": bool(flags.get("higher_high_higher_low", False)),
                "vcp_tightness": bool(flags.get("vcp_tightness", False)),
                "parabolic_curve": bool(flags.get("parabolic_curve", False)),
                "stop_hunt_liquidity_grab": bool(flags.get("stop_hunt_liquidity_grab", False)),
                "dominant_pattern": str(flags.get("dominant_pattern", "none")),
                "trend_direction": str(flags.get("trend_direction", "neutral")),
            }
        }
    except Exception as e:
        logger.error(f"Fireworks Vision failed for {symbol}: {e}")
        raise


async def _store_vision_results(results: List[Dict[str, Any]]):
    """Store vision flags in shortlist_candidates table"""
    try:
        db = await get_asyncpg_pool()

        # Get latest shortlist date
        async with db.acquire() as conn:
            latest = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")

        if not latest or not latest['latest_date']:
            logger.error("No shortlist found for storing vision results")
            return

        shortlist_date = latest['latest_date']

        async with db.acquire() as conn:
            for r in results:
                await conn.execute("""
                    UPDATE shortlist_candidates
                    SET vision_flags = $1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = $2 AND symbol = $3
                """, json.dumps(r["vision_flags"]), shortlist_date, r["symbol"])

        logger.info(f"Vision results stored for {len(results)} symbols (date: {shortlist_date})")
    except Exception as e:
        logger.error(f"Failed to store vision results: {e}")