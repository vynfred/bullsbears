# backend/app/services/cloud_agents/social_agent.py
"""
Social Context Agent – Grok-4 (Phase 4)
75 parallel calls → social_score (-5 to +5) + headlines + events + Polymarket
Pure async. No classes. No legacy.
"""

import asyncio
import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import List, Dict, Any

import httpx
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

# Grok API — locked in
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-beta"

# Hot-reloaded prompt
PROMPT = (Path(__file__).parent.parent / "prompts" / "social_prompt.txt").read_text(encoding="utf-8").strip()


async def run_social_analysis(symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Input: List of symbol dicts from SHORT_LIST
    Output: List with social_score, headlines, events, polymarket_prob
    """
    logger.info(f"Social agent: analyzing {len(symbols)} symbols via Grok-4")

    async with httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=100)) as client:
        tasks = [_analyze_one(client, symbol["symbol"]) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    processed = []
    for symbol, result in zip([s["symbol"] for s in symbols], results):
        if isinstance(result, Exception):
            logger.error(f"Social analysis failed for {symbol}: {result}")
            processed.append({
                "symbol": symbol,
                "social_score": 0,
                "headlines": [],
                "events": [],
                "polymarket_prob": None,
                "mention_velocity": 0.0,
                "platform_consensus": 0.0,
            })
        else:
            processed.append({"symbol": symbol, **result})

    # Store in DB
    await _store_social_results(processed)

    logger.info(f"Social analysis complete: {len(processed)} symbols")
    return processed


async def _analyze_one(client: httpx.AsyncClient, symbol: str) -> Dict[str, Any]:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": PROMPT.replace("{SYMBOL}", symbol)}
        ],
        "temperature": 0.0,
        "max_tokens": 256,
    }

    try:
        resp = await client.post(
            GROK_URL,
            json=payload,
            headers={"Authorization": f"Bearer {GROK_API_KEY}"},
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Strict JSON parse
        start = content.find("{")
        end = content.rfind("}") + 1
        data = json.loads(content[start:end])

        return {
            "social_score": int(data.get("social_score", 0)),
            "headlines": data.get("headlines", [])[:3],
            "events": data.get("events", []),
            "polymarket_prob": data.get("polymarket_prob"),
            "mention_velocity": float(data.get("mention_velocity", 0.0)),
            "platform_consensus": float(data.get("platform_consensus", 0.0)),
        }
    except Exception as e:
        logger.error(f"Grok failed for {symbol}: {e}")
        raise


async def _store_social_results(results: List[Dict[str, Any]]):
    """Store social data in shortlist_candidates table"""
    try:
        db = await get_asyncpg_pool()
        today = date.today()

        async with db.acquire() as conn:
            for r in results:
                social_data = {
                    "headlines": r.get("headlines", []),
                    "events": r.get("events", []),
                    "polymarket_prob": r.get("polymarket_prob"),
                    "mention_velocity": r.get("mention_velocity", 0.0),
                    "platform_consensus": r.get("platform_consensus", 0.0),
                }

                await conn.execute("""
                    UPDATE shortlist_candidates
                    SET social_score = $1,
                        social_data = $2,
                        polymarket_prob = $3,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = $4 AND symbol = $5
                """, r["social_score"], json.dumps(social_data), r.get("polymarket_prob"), today, r["symbol"])

        logger.info(f"Social results stored for {len(results)} symbols")
    except Exception as e:
        logger.error(f"Failed to store social results: {e}")