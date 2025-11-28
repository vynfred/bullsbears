# backend/app/services/cloud_agents/vision_agent.py
"""
Vision Agent – Groq Llama-3.2-11B-Vision (Phase 3)
75 parallel calls → 6 boolean pattern flags per chart
Pure async. No classes. No legacy.
"""

import asyncio
import json
import logging
from datetime import date
from pathlib import Path
from typing import List, Dict, Any

import httpx
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

# Groq API — locked in
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.2-11b-vision-preview"

# Hot-reloaded prompt (loaded once)
PROMPT = (Path(__file__).parent.parent / "prompts" / "vision_prompt.txt").read_text(encoding="utf-8").strip()


async def run_vision_analysis(charts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Input: List of dicts with 'symbol' and 'chart_base64' (PNG string)
    Output: List with 'symbol' and 'vision_flags' (6 booleans)
    """
    logger.info(f"Vision agent: analyzing {len(charts)} charts via Groq")

    async with httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=100)) as client:
        tasks = [_analyze_one(client, item) for item in charts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    processed = []
    for item, result in zip(charts, results):
        symbol = item["symbol"]
        if isinstance(result, Exception):
            logger.error(f"Vision analysis failed for {symbol}: {result}")
            processed.append({
                "symbol": symbol,
                "vision_flags": {
                    "wyckoff_phase_2": False,
                    "weekly_triangle_coil": False,
                    "volume_shelf_breakout": False,
                    "p_shape_profile": False,
                    "fakeout_wick_rejection": False,
                    "spring_setup": False,
                }
            })
        else:
            processed.append(result)

    # Store in DB
    await _store_vision_results(processed)

    logger.info(f"Vision analysis complete: {len(processed)} charts")
    return processed


async def _analyze_one(client: httpx.AsyncClient, item: Dict[str, Any]) -> Dict[str, Any]:
    symbol = item["symbol"]
    base64_png = item["chart_base64"]

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_png}"}
                    }
                ]
            }
        ],
        "temperature": 0.0,
        "max_tokens": 128,
    }

    try:
        resp = await client.post(
            GROQ_URL,
            json=payload,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Strict JSON parse
        start = content.find("{")
        end = content.rfind("}") + 1
        flags = json.loads(content[start:end])

        return {
            "symbol": symbol,
            "vision_flags": {
                "wyckoff_phase_2": bool(flags.get("wyckoff_phase_2", False)),
                "weekly_triangle_coil": bool(flags.get("weekly_triangle_coil", False)),
                "volume_shelf_breakout": bool(flags.get("volume_shelf_breakout", False)),
                "p_shape_profile": bool(flags.get("p_shape_profile", False)),
                "fakeout_wick_rejection": bool(flags.get("fakeout_wick_rejection", False)),
                "spring_setup": bool(flags.get("spring_setup", False)),
            }
        }
    except Exception as e:
        logger.error(f"Groq Vision failed for {symbol}: {e}")
        raise


async def _store_vision_results(results: List[Dict[str, Any]]):
    """Store vision flags in shortlist_candidates table"""
    try:
        db = await get_asyncpg_pool()
        today = date.today()

        async with db.acquire() as conn:
            for r in results:
                await conn.execute("""
                    UPDATE shortlist_candidates
                    SET vision_flags = $1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = $2 AND symbol = $3
                """, json.dumps(r["vision_flags"]), today, r["symbol"])

        logger.info(f"Vision results stored for {len(results)} symbols")
    except Exception as e:
        logger.error(f"Failed to store vision results: {e}")