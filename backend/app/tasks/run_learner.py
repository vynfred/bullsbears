# app/tasks/run_learner.py
import asyncio
import logging
import json
from app.core.database import get_asyncpg_pool
from app.core.runpod_client import get_runpod_client
from datetime import datetime, timedelta
from pathlib import Path

from app.core.celery import celery_app
from app.services.runpod_agents.learner_agent import build_learning_prompt
from app.services.system_state import SystemState

logger = logging.getLogger(__name__)

# === CONFIG ===
INSIGHTS_DIR = Path(__file__).parent.parent.parent / "templates" / "insights"
INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)

# === OVERRIDE: Replace nightly with WEEKLY logic ===
async def run_weekly_learner_cycle(week_start: datetime, week_end: datetime):
    """
    This is the **real** weekly learner logic.
    We define it here because `learner_agent.py` still has `run_nightly_learning`.
    We'll **monkey-patch** it at import time.
    """
    logger.info(f"Weekly learner: {week_start.date()} to {week_end.date()}")

    db = await get_asyncpg_pool()
    client = await get_runpod_client()

    # === 1. Fetch data ===
    candidates = await db.fetch("""
        SELECT symbol, prescreen_score, social_score, vision_flags,
               was_picked, picked_direction, price_at_selection, price_30d
        FROM shortlist_candidates
        WHERE date >= $1 AND date <= $2
    """, week_start.date(), week_end.date())

    if not candidates:
        logger.info("No candidates this week")
        return {}

    # === 2. Enrich with % change ===
    enriched = []
    for c in candidates:
        change = 0.0
        if c['price_at_selection'] and c['price_30d']:
            change = ((c['price_30d'] - c['price_at_selection']) / c['price_at_selection']) * 100
        enriched.append({**dict(c), "change_30d": change})

    # === 3. Build prompt ===
    # Load few-shot examples
    from app.services.runpod_agents.learner_agent import _load_prompt_examples
    examples = _load_prompt_examples()
    prompt = build_learning_prompt(enriched, examples)

    # === 4. Call LLM ===
    resp = await client.generate(
        prompt=prompt,
        model="qwen2.5:32b",
        temperature=0.0,
        max_tokens=2048
    )

    # === 5. Parse JSON ===
    raw = resp.get('output', '{}')
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        logger.error("No JSON in response")
        return {}
    updates = json.loads(raw[start:end])

    # === 6. Apply updates to correct tables ===
    async with db.transaction():
        # Update feature_weights table
        for name, val in updates.get("feature_weight_updates", {}).items():
            await db.execute("""
                INSERT INTO feature_weights (name, value, last_updated)
                VALUES ($1, $2, now())
                ON CONFLICT (name) DO UPDATE SET value = $2, last_updated = now()
            """, name, float(val))

        # Update agent_weights table
        for name, val in updates.get("agent_trust_updates", {}).items():
            await db.execute("""
                INSERT INTO agent_weights (agent_name, weight, last_updated)
                VALUES ($1, $2, now())
                ON CONFLICT (agent_name) DO UPDATE SET weight = $2, last_updated = now()
            """, name, float(val))

    # === 7. Generate report ===
    report = {
        "cycle_start": week_start.isoformat(),
        "cycle_end": week_end.isoformat(),
        "arbitrator_model": "deepseek-v3",  # TODO: fetch from picks
        "total_candidates": len(enriched),
        "final_picks": len([c for c in enriched if c["was_picked"]]),
        "insights": updates.get("insights", []),
        "weight_changes": {
            **updates.get("feature_weight_updates", {}),
            **updates.get("agent_trust_updates", {})
        },
        "generated_at": datetime.now().isoformat()
    }

    report_path = INSIGHTS_DIR / f"learner_report_{week_start.date()}.json"
    report_path.write_text(json.dumps(report, indent=2))

    logger.info(f"Report saved: {report_path}")
    return report


# === CELERY TASK: Runs Saturday 4:00 AM ===
@celery_app.task(name="tasks.run_weekly_learner")
def run_weekly_learner():
    async def _run():
        if not await SystemState.is_system_on():
            logger.info("System OFF - skipping learner")
            return {"skipped": True}

        today = datetime.now().date()
        week_end = today - timedelta(days=1)      # Sunday
        week_start = week_end - timedelta(days=6) # Monday

        result = await run_weekly_learner_cycle(
            datetime.combine(week_start, datetime.min.time()),
            datetime.combine(week_end, datetime.min.time())
        )

        return {
            "success": True,
            "week": f"{week_start} to {week_end}",
            "report": f"/app/templates/insights/learner_report_{week_start}.json"
        }

    return asyncio.run(_run())