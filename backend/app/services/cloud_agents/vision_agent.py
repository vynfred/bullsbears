#!/usr/bin/env python3
"""
Vision Agent – Groq Llama-3.2-11B-Vision (Phase 3)
75 parallel API calls → 6 boolean pattern flags per symbol
No local models. No parsing. Pure JSON.
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

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.2-11b-vision-preview"

# Hot-reloaded prompt (relative to services/)
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "vision_prompt.txt"

class VisionAgent:
    """One job: 75 charts → 6 boolean flags each. Nothing else."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=100))
        self.prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        try:
            return PROMPT_PATH.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"Vision prompt load failed: {e}")
            return "Detect ONLY these six patterns. Return VALID JSON only."

    async def analyze_batch(self, charts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Input: 75 items with:
          - symbol
          - chart_base64 (PNG string)
        Output: 75 items with:
          - symbol
          - vision_flags: 6 booleans
        """
        logger.info(f"VisionAgent: analyzing {len(charts)} charts via Groq...")

        tasks = [self._analyze_one(item) for item in charts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid = []
        for item, result in zip(charts, results):
            if isinstance(result, Exception):
                logger.error(f"Vision failed for {item['symbol']}: {result}")
                valid.append({
                    "symbol": item["symbol"],
                    "vision_flags": {
                        "wyckoff_phase_2": False,
                        "weekly_triangle_coil": False,
                        "volume_shelf_breakout": False,
                        "p_shape_profile": False,
                        "fakeout_wick_rejection": False,
                        "spring_setup": False
                    }
                })
            else:
                valid.append(result)

        logger.info(f"VisionAgent: {len(valid)}/75 charts processed successfully")

        # Store vision results in database
        await self._store_vision_results(valid)

        return valid

    async def _analyze_one(self, item: Dict[str, Any]) -> Dict[str, Any]:
        symbol = item["symbol"]
        base64_png = item["chart_base64"]

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_png}"}
                        }
                    ]
                }
            ],
            "temperature": 0.0,
            "max_tokens": 128
        }

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        response = await self.client.post(GROQ_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        raw = data["choices"][0]["message"]["content"]

        try:
            # Strict JSON parsing
            start = raw.find("{")
            end = raw.rfind("}") + 1
            flags = json.loads(raw[start:end])

            return {
                "symbol": symbol,
                "vision_flags": {
                    "wyckoff_phase_2": bool(flags.get("wyckoff_phase_2", False)),
                    "weekly_triangle_coil": bool(flags.get("weekly_triangle_coil", False)),
                    "volume_shelf_breakout": bool(flags.get("volume_shelf_breakout", False)),
                    "p_shape_profile": bool(flags.get("p_shape_profile", False)),
                    "fakeout_wick_rejection": bool(flags.get("fakeout_wick_rejection", False)),
                    "spring_setup": bool(flags.get("spring_setup", False))
                }
            }
        except Exception as e:
            logger.error(f"JSON parse failed for {symbol}: {e} | Raw: {raw[:200]}")
            raise

    async def _store_vision_results(self, results: List[Dict[str, Any]]):
        """Store vision analysis results in shortlist_candidates table"""
        try:
            db = await get_asyncpg_pool()
            today = date.today()

            for result in results:
                symbol = result['symbol']
                vision_flags = result['vision_flags']

                # Update the shortlist_candidates record with vision data
                await db.execute("""
                    UPDATE shortlist_candidates
                    SET vision_flags = $1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = $2 AND symbol = $3
                """, json.dumps(vision_flags), today, symbol)

            logger.info(f"✅ Stored vision results for {len(results)} candidates")
        except Exception as e:
            logger.error(f"❌ Failed to store vision results: {e}", exc_info=True)

    async def close(self):
        await self.client.aclose()


# Global singleton
_vision_agent = None

async def get_vision_agent() -> VisionAgent:
    global _vision_agent
    if _vision_agent is None:
        _vision_agent = VisionAgent()
    return _vision_agent