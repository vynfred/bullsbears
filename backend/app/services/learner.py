# services/learner.py
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from ..core.database import get_asyncpg_pool
from ..core.runpod_client import get_runpod_client

logger = logging.getLogger(__name__)

def build_learning_prompt(candidates: List[Dict]) -> str:
    examples = []
    for c in candidates[:8]:
        outcome = "MOON" if c["change_30d"] > 20 else "RUG" if c["change_30d"] < -20 else "neutral"
        examples.append(f"- {c['symbol']}: {c['change_30d']:+.1f}% → {outcome}")
    return f"""
You are the BullsBears Learner. Analyze yesterday's 75 candidates.

EXAMPLES:
{chr(10).join(examples)}

TASK:
1. Find missed moons and rugs
2. Suggest weight updates and prompt examples

OUTPUT JSON:
{{
  "vision_updates": {{"volume_shelf_breakout": 2.1}},
  "arbitrator_updates": {{"prescreen_score": 0.32}},
  "prompt_additions": ["- NVDA: +28% → missed"]
}}
"""

async def run_nightly_learning():
    logger.info("Starting nightly learning...")
    try:
        db = await get_asyncpg_pool()
        runpod_client = await get_runpod_client()

        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        candidates = await db.fetch("""
            SELECT symbol, prescreen_score, social_score, vision_flags,
                   final_pick, change_30d, confidence
            FROM short_list_price_tracking
            WHERE date = $1
        """, yesterday)

        if not candidates:
            logger.info("No data. Skipping.")
            return

        prompt = build_learning_prompt(candidates)
        response = await runpod_client.run_inference(
            prompt=prompt,
            model="qwen2.5:32b",
            temperature=0.0,
            max_tokens=2048,
            response_format="json"
        )

        # Parse response
        response_text = response.get('response') or response.get('output', '{}')
        updates = json.loads(response_text)

        # Apply updates to database
        for flag, w in updates.get("vision_updates", {}).items():
            await db.execute(
                "INSERT INTO model_weights (name, value) VALUES ($1, $2) ON CONFLICT (name) DO UPDATE SET value = $2",
                f"vision_{flag}", float(w)
            )

        for name, w in updates.get("arbitrator_updates", {}).items():
            await db.execute(
                "INSERT INTO model_weights (name, value) VALUES ($1, $2) ON CONFLICT (name) DO UPDATE SET value = $2",
                name, float(w)
            )

        for ex in updates.get("prompt_additions", []):
            await db.execute(
                "INSERT INTO prompt_examples (type, content) VALUES ($1, $2)",
                "missed_moon", ex
            )

        logger.info("Nightly learning complete.")
    except Exception as e:
        logger.error(f"Learner failed: {e}")