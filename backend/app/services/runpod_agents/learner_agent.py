# services/learner_agent.py
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.core.database import get_asyncpg_pool
from app.core.runpod_client import get_runpod_client

logger = logging.getLogger(__name__)

# Paths (relative to services/)
PROMPT_EXAMPLES_PATH = Path(__file__).parent.parent / "prompts" / "learner_examples.json"
INSIGHTS_DIR = Path(__file__).parent.parent.parent / "templates" / "insights"
INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_prompt_examples() -> List[Dict]:
    """Load existing few-shot examples for the learner prompt."""
    try:
        return json.loads(PROMPT_EXAMPLES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def build_learning_prompt(candidates: List[Dict], examples: List[Dict]) -> str:
    base = (
        "You are the Learner Agent. Analyze the past 7 days of short-list candidates and final picks. "
        "Determine which features (prescreen_score, vision_flags, social_score, etc.) predicted wins vs losses. "
        "Return ONLY a JSON object with:\n"
        "  - feature_weight_updates: {feature_name: new_weight}\n"
        "  - agent_trust_updates: {agent_name: new_trust_score}\n"
        "  - new_prompt_examples: [{symbol, direction, reasoning, outcome, ...}]\n"
        "  - insights: [human-readable bullet points]\n\n"
    )

    # Sample candidates
    sample = "\n".join(
        f"- {c['symbol']}: {c.get('change_30d',0):+5.1f}% → "
        f"{'MOON' if c.get('change_30d',0)>20 else 'RUG' if c.get('change_30d',0)<-20 else 'NEUTRAL'}"
        for c in candidates[:12]
    )

    # Few-shot examples
    ex = "\n".join(json.dumps(e, ensure_ascii=False) for e in examples[-5:])  # last 5

    return f"{base}SAMPLE CANDIDATES:\n{sample}\n\nFEW-SHOT EXAMPLES:\n{ex}\n"


async def run_weekly_learner_cycle(week_start: datetime, week_end: datetime) -> Dict[str, Any]:
    """
    Full weekly learning cycle – called every Saturday 4:00 AM.
    """
    logger.info(f"Learner cycle for {week_start.date()} → {week_end.date()}")

    db = await get_asyncpg_pool()
    client = await get_runpod_client()

    # 1. Fetch shortlist + final picks for the week
    candidates = await db.fetch("""
        SELECT symbol, prescreen_score, social_score, vision_flags,
               was_picked, picked_direction, price_at_selection, price_30d
        FROM shortlist_candidates
        WHERE date >= $1 AND date <= $2
    """, week_start.date(), week_end.date())

    if not candidates:
        logger.info("No candidates this week – skipping.")
        return {}

    # 2. Enrich with 30-day change
    enriched = []
    for c in candidates:
        change = 0.0
        if c['price_at_selection'] and c['price_30d']:
            change = ((c['price_30d'] - c['price_at_selection']) / c['price_at_selection']) * 100
        enriched.append(dict(c, change_30d=change))

    # 3. Load few-shot examples
    examples = _load_prompt_examples()

    # 4. Build prompt + call LLM
    prompt = build_learning_prompt(enriched, examples)
    resp = await client.generate(
        prompt=prompt,
        model="qwen2.5:32b",
        temperature=0.0,
        max_tokens=2048
    )

    # 5. Parse JSON
    raw = resp.get('output', '{}')
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        logger.error("No JSON in learner response")
        return {}
    updates = json.loads(raw[start:end])

    # 6. Apply DB updates
    async with db.transaction():
        # Feature weights - use feature_weights table
        for name, val in updates.get("feature_weight_updates", {}).items():
            await db.execute("""
                INSERT INTO feature_weights (name, value, last_updated)
                VALUES ($1, $2, now())
                ON CONFLICT (name) DO UPDATE SET value = $2, last_updated = now()
            """, name, float(val))

        # Agent trust - use agent_weights table
        for name, val in updates.get("agent_trust_updates", {}).items():
            await db.execute("""
                INSERT INTO agent_weights (agent_name, weight, last_updated)
                VALUES ($1, $2, now())
                ON CONFLICT (agent_name) DO UPDATE SET weight = $2, last_updated = now()
            """, name, float(val))

        # Prompt examples - match database schema (type, content, source_pick_id, outcome, agent_name)
        new_ex = updates.get("new_prompt_examples", [])
        if new_ex:
            for ex in new_ex:
                await db.execute("""
                    INSERT INTO prompt_examples (type, content, outcome, agent_name)
                    VALUES ($1, $2, $3, $4)
                """,
                ex.get("direction", "bullish"),  # type
                ex.get("reasoning", ""),  # content
                ex.get("outcome", ""),  # outcome
                "ArbitratorAgent"  # agent_name
                )
            # Append to file for next cycle
            all_ex = examples + new_ex
            PROMPT_EXAMPLES_PATH.write_text(json.dumps(all_ex, indent=2, ensure_ascii=False))

    # 7. Generate human report
    report = {
        "cycle_start": week_start.isoformat(),
        "cycle_end": week_end.isoformat(),
        "arbitrator_model": (week_start - timedelta(days=7)).strftime("%A") + " model",  # placeholder
        "total_candidates": len(enriched),
        "final_picks": len([c for c in enriched if c["was_picked"]]),
        "insights": updates.get("insights", []),
        "weight_changes": {
            **updates.get("feature_weight_updates", {}),
            **updates.get("agent_trust_updates", {})
        },
        "generated_at": datetime.now().isoformat()
    }

    # 8. Save report
    report_path = INSIGHTS_DIR / f"learner_report_{week_start.date()}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    logger.info(f"Report saved: {report_path}")

    # 9. Log cycle
    await db.execute("""
        INSERT INTO learning_cycles (cycle_date, duration_seconds, insights_count, updates_applied, top_factors, cycle_data)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, week_start, 0.0, len(report["insights"]),
         len(updates.get("feature_weight_updates", {})) + len(updates.get("agent_trust_updates", {})),
         json.dumps(report["insights"]), json.dumps(report))

    logger.info("Weekly learner cycle complete")
    return report