#!/usr/bin/env python3
"""
Social + Context Agent – Grok API (Phase 4)
75 parallel calls → social_score (-5 to +5) + news + events + Polymarket
No local models. Pure JSON.
"""

import asyncio
import logging
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import date

import httpx
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

# Grok API
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-beta"

# Hot-reloaded prompt (relative path)
PROMPT_PATH = Path(__file__).parent / "prompts" / "social_prompt.txt"

class SocialContextAgent:
    """One job: 75 symbols → social score + news + events + Polymarket"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=100))
        self.prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        try:
            return PROMPT_PATH.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"Social prompt load failed: {e}")
            return "Return ONLY a single integer from -5 to +5..."

    async def analyze_batch(self, symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Input: 75 symbols with symbol
        Output: 75 items with social_score, headlines, events, polymarket_prob
        """
        logger.info(f"SocialContextAgent: analyzing {len(symbols)} symbols via Grok...")

        tasks = [self._analyze_one(t["symbol"]) for t in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid = []
        for symbol, result in zip([t["symbol"] for t in symbols], results):
            if isinstance(result, Exception):
                logger.error(f"Social failed for {symbol}: {result}")
                valid.append({
                    "symbol": symbol,
                    "social_score": 0,
                    "headlines": [],
                    "events": [],
                    "polymarket_prob": None,
                    "mention_velocity": 0.0,
                    "platform_consensus": 0.0
                })
            else:
                valid.append({"symbol": symbol, **result})

        logger.info(f"SocialContextAgent: {len(valid)}/75 symbols processed")

        # Store social results in database
        await self._store_social_results(valid)

        return valid

    async def _analyze_one(self, symbol: str) -> Dict[str, Any]:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": self.prompt.replace("{SYMBOL}", symbol)}
            ],
            "temperature": 0.0,
            "max_tokens": 256
        }

        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }

        response = await self.client.post(GROK_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        raw = data["choices"][0]["message"]["content"]

        try:
            # Strict JSON parsing
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end])

            return {
                "social_score": int(parsed.get("social_score", 0)),
                "headlines": parsed.get("headlines", [])[:3],
                "events": parsed.get("events", []),
                "polymarket_prob": parsed.get("polymarket_prob"),
                "mention_velocity": parsed.get("mention_velocity", 0.0),
                "platform_consensus": parsed.get("platform_consensus", 0.0)
            }
        except Exception as e:
            logger.error(f"JSON parse failed for {symbol}: {e} | Raw: {raw[:200]}")
            raise

    async def _store_social_results(self, results: List[Dict[str, Any]]):
        """Store social sentiment results in shortlist_candidates table"""
        try:
            db = await get_asyncpg_pool()
            today = date.today()

            for result in results:
                symbol = result['symbol']
                social_score = result.get('social_score', 0)

                # Build social_data JSONB
                social_data = {
                    'headlines': result.get('headlines', []),
                    'events': result.get('events', []),
                    'polymarket_prob': result.get('polymarket_prob'),
                    'mention_velocity': result.get('mention_velocity', 0.0),
                    'platform_consensus': result.get('platform_consensus', 0.0)
                }

                # Update the shortlist_candidates record with social data
                await db.execute("""
                    UPDATE shortlist_candidates
                    SET social_score = $1,
                        social_data = $2,
                        polymarket_prob = $3,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = $4 AND symbol = $5
                """,
                    social_score,
                    json.dumps(social_data),
                    result.get('polymarket_prob'),
                    today,
                    symbol
                )

            logger.info(f"✅ Stored social results for {len(results)} candidates")
        except Exception as e:
            logger.error(f"❌ Failed to store social results: {e}", exc_info=True)

    async def close(self):
        await self.client.aclose()


# Global singleton
_social_agent = None

async def get_social_agent() -> SocialContextAgent:
    global _social_agent
    if _social_agent is None:
        _social_agent = SocialContextAgent()
    return _social_agent
