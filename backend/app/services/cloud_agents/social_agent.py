# backend/app/services/cloud_agents/social_agent.py
"""
Social Context Agent – Grok-4 (Phase 4)
75 parallel calls → social_score (-7 to +7) + headlines + events + Polymarket
Includes: bullish_ratio, mention_velocity, engagement_weight, platform_consensus, contrarian_flag
Pure async. No classes. No legacy.
"""

import asyncio
import json
import logging
import os
from datetime import date  # noqa: F401 - used for type hints
from pathlib import Path
from typing import List, Dict, Any

import httpx
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

# Grok API — locked in
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-4-fast-reasoning"

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
                "bullish_ratio": 0.5,
                "headlines": [],
                "events": [],
                "polymarket_prob": None,
                "mention_velocity": 1.0,
                "engagement_weight": 1.0,
                "platform_consensus": 0.0,
                "contrarian_flag": False,
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

        # ═══════════════════════════════════════════════════════════════════
        # v9 DYNAMIC SCORE ADJUSTMENTS (server-side enforcement)
        # Grok returns base score; we apply velocity scaling + contrarian flip
        # ═══════════════════════════════════════════════════════════════════

        # Extract raw base score from Grok
        base_score = int(data.get("social_score", 0))  # -5 to +5 (or already adjusted)

        # Extract dynamic factors
        velocity = float(data.get("mention_velocity", 1.0))
        consensus = float(data.get("platform_consensus", 0.5))

        # Scale: base * velocity if >1.5; divide by 1.2 if consensus <0.6
        adjusted_score = float(base_score)
        if velocity > 1.5:
            adjusted_score *= velocity
        if consensus < 0.6:
            adjusted_score /= 1.2

        # Cap to -7 to +7 range
        adjusted_score = max(-7.0, min(7.0, adjusted_score))

        # Contrarian flip: if |base| ≥4 and velocity >3x, flip sign by 20%
        # This catches overhyped stocks that may reverse
        contrarian = False
        if abs(base_score) >= 4 and velocity > 3.0:
            adjusted_score *= 0.8 * (-1 if base_score > 0 else 1)  # Flip direction, reduce 20%
            contrarian = True
            logger.info(f"🔄 {symbol}: Contrarian flip triggered (base={base_score}, velocity={velocity}x)")

        return {
            "social_score": int(round(adjusted_score)),  # No decimals per prompt
            "bullish_ratio": float(data.get("bullish_ratio", 0.5)),
            "headlines": data.get("headlines", [])[:3],
            "events": data.get("events", []),
            "polymarket_prob": data.get("polymarket_prob"),
            "mention_velocity": velocity,
            "engagement_weight": float(data.get("engagement_weight", 1.0)),
            "platform_consensus": consensus,
            "contrarian_flag": contrarian or bool(data.get("contrarian_flag", False)),
        }
    except Exception as e:
        logger.error(f"Grok failed for {symbol}: {e}")
        raise


async def _store_social_results(results: List[Dict[str, Any]]):
    """Store social data in shortlist_candidates table"""
    try:
        db = await get_asyncpg_pool()

        async with db.acquire() as conn:
            # Get the latest shortlist date (may not be today)
            row = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")
            if not row or not row['latest_date']:
                logger.error("No shortlist found to update")
                return
            shortlist_date = row['latest_date']
            logger.info(f"Storing social results for date: {shortlist_date} (type: {type(shortlist_date)})")

            updated_count = 0
            for r in results:
                social_data = {
                    "headlines": r.get("headlines", []),
                    "events": r.get("events", []),
                    "polymarket_prob": r.get("polymarket_prob"),
                    "bullish_ratio": r.get("bullish_ratio", 0.5),
                    "mention_velocity": r.get("mention_velocity", 1.0),
                    "engagement_weight": r.get("engagement_weight", 1.0),
                    "platform_consensus": r.get("platform_consensus", 0.0),
                    "contrarian_flag": r.get("contrarian_flag", False),
                }

                result = await conn.execute("""
                    UPDATE shortlist_candidates
                    SET social_score = $1,
                        social_data = $2,
                        polymarket_prob = $3,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = $4 AND symbol = $5
                """, r["social_score"], json.dumps(social_data), r.get("polymarket_prob"), shortlist_date, r["symbol"])

                # Check if row was actually updated
                if "UPDATE 1" in result:
                    updated_count += 1

        logger.info(f"Social results: {updated_count}/{len(results)} rows updated (date: {shortlist_date})")
    except Exception as e:
        logger.error(f"Failed to store social results: {e}")