# services/learner.py
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from app.core.database import db
from app.services.qwen_client import qwen_client

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
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        candidates = await db.fetch("""
            SELECT symbol, prescreen_score, social_score, vision_flags, 
                   final_pick, change_30d, confidence
            FROM short_list_price_tracking 
            WHERE date = %s
        """, (yesterday,))

        if not candidates:
            logger.info("No data. Skipping.")
            return

        response = await qwen_client.chat.completions.create(
            model="qwen2.5:32b",
            messages=[{"role": "user", "content": build_learning_prompt(candidates)}],
            response_format={"type": "json_object"}
        )

        updates = json.loads(response.choices[0].message.content)

        # Apply updates
        for flag, w in updates.get("vision_updates", {}).items():
            await db.upsert("model_weights", {"name": f"vision_{flag}"}, {"value": float(w)})

        for name, w in updates.get("arbitrator_updates", {}).items():
            await db.upsert("model_weights", {"name": name}, {"value": float(w)})

        for ex in updates.get("prompt_additions", []):
            await db.insert("prompt_examples", {"type": "missed_moon", "content": ex})

        logger.info("Nightly learning complete.")
    except Exception as e:
        logger.error(f"Learner failed: {e}")