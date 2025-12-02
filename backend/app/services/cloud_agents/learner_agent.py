# backend/app/services/cloud_agents/learner_agent.py
import httpx
import json
import logging
from datetime import date
from pathlib import Path
from app.core.config import settings
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

# Paths — these must exist and be writable on Render
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
WEIGHTS_PATH = PROMPTS_DIR / "weights.json"
BIAS_PATH = PROMPTS_DIR / "bias.json"
LEARNER_PROMPT_PATH = PROMPTS_DIR / "learner_prompt.txt"


async def run_weekly_learner(week_start: date, week_end: date):
    """
    Weekly learner - analyzes 30-day matured outcomes to improve weights/bias.
    Now includes confluence tracking for v5 target system.
    """
    logger.info(f"Weekly learner running: {week_start} → {week_end}")

    # 1. Pull real data from Render PostgreSQL with confluence + outcome data
    pool = await get_asyncpg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                sc.symbol,
                sc.prescreen_score,
                sc.social_score,
                sc.vision_flags,
                sc.polymarket_prob,
                sc.selected,
                fp.direction,
                sc.price_at_selection AS price_at_pick,
                hd_30.close_price AS price_30d_later,
                -- Confluence data from picks table
                p.confluence_score,
                p.confluence_methods,
                p.rsi_divergence,
                p.gann_alignment,
                p.primary_target,
                p.moonshot_target,
                -- Outcome tracking
                pod.hit_primary_target,
                pod.hit_moonshot_target,
                pod.max_gain_pct
            FROM shortlist_candidates sc
            LEFT JOIN final_picks fp
                ON fp.shortlist_id = sc.id
            LEFT JOIN picks p
                ON p.symbol = sc.symbol
                AND p.created_at::date = sc.date::date
            LEFT JOIN pick_outcomes_detailed pod
                ON pod.pick_id = p.id
            LEFT JOIN historical_data hd_30
                ON hd_30.symbol = sc.symbol
                AND hd_30.date = sc.date::date + INTERVAL '30 days'
            WHERE sc.date >= $1 AND sc.date <= $2
            ORDER BY sc.date DESC
        """, week_start, week_end)

    # 2. Build candidate list with 30-day moves + confluence metrics
    candidates = []
    for r in rows:
        if r["price_at_pick"] and r["price_30d_later"] and r["price_at_pick"] > 0:
            pct_30d = round((r["price_30d_later"] - r["price_at_pick"]) / r["price_at_pick"] * 100, 2)
        else:
            pct_30d = None

        # Parse confluence methods (stored as TEXT[])
        confluence_methods = r["confluence_methods"] or []
        if isinstance(confluence_methods, str):
            confluence_methods = json.loads(confluence_methods) if confluence_methods else []

        candidates.append({
            "symbol": r["symbol"],
            "prescreen": round(float(r["prescreen_score"] or 0), 3),
            "social": int(r["social_score"] or 0),
            "vision": r["vision_flags"] or {},
            "polymarket": round(float(r["polymarket_prob"] or 0), 3),
            "picked": bool(r["selected"]),
            "direction": r["direction"],
            "pct_30d": pct_30d,
            # Confluence tracking (v5)
            "confluence_score": int(r["confluence_score"] or 0),
            "confluence_methods": confluence_methods,
            "rsi_divergence": bool(r["rsi_divergence"]),
            "gann_alignment": bool(r["gann_alignment"]),
            "hit_primary": bool(r["hit_primary_target"]),
            "hit_moonshot": bool(r["hit_moonshot_target"]),
            "max_gain_pct": float(r["max_gain_pct"]) if r["max_gain_pct"] else None
        })

    if not candidates:
        logger.warning("No candidates with 30d price data")
        return {"status": "no_data"}

    # 3. Inject real data into prompt
    template = LEARNER_PROMPT_PATH.read_text()
    prompt = template.replace("{{CANDIDATE_SAMPLES}}", json.dumps(candidates, indent=2))

    # 4. Call Fireworks qwen2.5-72b
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            "https://api.fireworks.ai/inference/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.FIREWORKS_API_KEY}"},
            json={
                "model": "accounts/fireworks/models/qwen2.5-72b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 8192,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    # 5. Extract JSON safely
    json_str = content
    if "```json" in content:
        json_str = content.split("```json", 1)[1].split("```", 1)[0]

    try:
        data = json.loads(json_str.strip())
    except Exception as e:
        logger.error(f"Invalid JSON from LLM: {e}\nRaw:\n{content}")
        raise

    # 6. Write files — instantly used by prescreen/arbitrator next morning
    WEIGHTS_PATH.write_text(json.dumps(data.get("weights", {}), indent=2))
    BIAS_PATH.write_text(json.dumps(data.get("bias", {}), indent=2))

    logger.info(f"Learner success — updated weights/bias with {len(candidates)} candidates")
    return {"status": "success", "candidates": len(candidates)}