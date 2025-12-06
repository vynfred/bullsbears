# backend/app/services/cloud_agents/prescreen_agent.py
"""
Prescreen Agent - Fireworks.ai qwen2.5-72b-instruct
ACTIVE tier → SHORT_LIST (up to 75 bullish + bearish)

v6: Added catalyst detection (earnings this week, short interest >20%)
"""

import httpx
import json
import logging
from datetime import date, timedelta
from app.core.config import settings
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

PRESCREEN_PROMPT = """You are an expert stock screener. Analyze these stocks and identify CLEAR bullish or bearish setups for short-term trading (1-5 days).

STOCK DATA (includes catalyst flags):
{STOCK_DATA}

CATALYST FIELDS TO CONSIDER:
- catalyst_earnings: true = earnings report within 5 days (high volatility expected)
- short_interest_pct: % of float sold short (>20% = short squeeze candidate)
- catalyst_short_squeeze: true = high short interest >20% (BULLISH bias for squeeze plays)
- has_macro_event: true = major economic event within 3 days (CPI/FOMC/Jobs)

SELECTION RULES:
- Only select stocks with UNAMBIGUOUS signals. Mixed or weak = SKIP.
- Maximum 75 total picks (bullish + bearish combined). Can be fewer if signals are weak.
- PRIORITIZE stocks with catalyst flags - they have higher probability of large moves.

BULLISH CRITERIA (must meet ≥2):
1. 30-day price change ≥ +12% AND volume_ratio > 1.5 (momentum + volume confirmation)
2. Breaking recent highs on elevated volume (volume_ratio > 2.0)
3. Volatility expansion after consolidation (volatility_30d > 5% with positive price change)
4. SHORT SQUEEZE SETUP: short_interest_pct > 20% AND positive momentum (high priority!)

BEARISH CRITERIA (must meet ≥2):
1. 30-day price change ≤ -12% AND volume_ratio > 1.5 (breakdown + volume confirmation)
2. Support breakdown on elevated volume (volume_ratio > 2.0 with negative momentum)
3. Volatility spike after tight range (volatility_30d > 8% with negative price change)
4. LOW short interest + negative momentum = easier to fall (no squeeze risk)

Return ONLY valid JSON with this exact structure:
{
    "bullish": ["AAPL", "NVDA", ...],
    "bearish": ["XYZ", "ABC", ...],
    "summary": "Brief explanation of today's market conditions and selection rationale"
}"""


class PrescreenAgent:
    def __init__(self):
        self.model = "accounts/fireworks/models/qwen2.5-72b-instruct"
        self.db = None

    async def initialize(self):
        """Initialize agent and DB connection"""
        self.db = await get_asyncpg_pool()

    async def run_prescreen(self) -> dict:
        """Run prescreen via Fireworks.ai"""
        logger.info("🔍 Running prescreen with qwen2.5-72b-instruct")

        if not self.db:
            self.db = await get_asyncpg_pool()

        # Get active stocks with calculated metrics
        async with self.db.acquire() as conn:
            stocks = await conn.fetch("""
                WITH latest_date AS (
                    SELECT MAX(date) as max_date FROM prime_ohlc_90d
                ),
                metrics AS (
                    SELECT
                        p.symbol,
                        p.close_price as price,
                        p.volume as volume_today,
                        -- 30-day price change %
                        ROUND(((p.close_price - p30.close_price) / NULLIF(p30.close_price, 0) * 100)::numeric, 2) as pct_change_30d,
                        -- 30-day average volume
                        ROUND(avg_vol.avg_volume::numeric, 0) as avg_volume_30d,
                        -- Volume ratio (today vs 30d avg)
                        ROUND((p.volume / NULLIF(avg_vol.avg_volume, 0))::numeric, 2) as volume_ratio,
                        -- 30-day volatility (stdev of daily returns)
                        ROUND(vol.volatility::numeric, 2) as volatility_30d
                    FROM prime_ohlc_90d p
                    CROSS JOIN latest_date ld
                    -- 30-day ago price
                    LEFT JOIN LATERAL (
                        SELECT close_price
                        FROM prime_ohlc_90d
                        WHERE symbol = p.symbol AND date <= ld.max_date - INTERVAL '30 days'
                        ORDER BY date DESC LIMIT 1
                    ) p30 ON true
                    -- 30-day average volume
                    LEFT JOIN LATERAL (
                        SELECT AVG(volume) as avg_volume
                        FROM prime_ohlc_90d
                        WHERE symbol = p.symbol AND date > ld.max_date - INTERVAL '30 days'
                    ) avg_vol ON true
                    -- 30-day volatility
                    LEFT JOIN LATERAL (
                        SELECT STDDEV((close_price - open_price) / NULLIF(open_price, 0) * 100) as volatility
                        FROM prime_ohlc_90d
                        WHERE symbol = p.symbol AND date > ld.max_date - INTERVAL '30 days'
                    ) vol ON true
                    WHERE p.date = ld.max_date
                )
                SELECT * FROM metrics
                WHERE volume_today > 100000  -- Filter low volume
                AND price > 1.25             -- No penny stocks (>$1.25)
                AND pct_change_30d IS NOT NULL
                ORDER BY volume_today DESC
                LIMIT 500
            """)

        if not stocks:
            logger.warning("No stocks found in prime_ohlc_90d")
            return {"shortlist_count": 0, "bullish": [], "bearish": [], "error": "no_stocks"}

        logger.info(f"Found {len(stocks)} active stocks to screen")

        # ═══════════════════════════════════════════════════════════════════
        # v6 CATALYST DETECTION - Earnings this week + Short Interest
        # ═══════════════════════════════════════════════════════════════════
        today_date = date.today()
        next_week = today_date + timedelta(days=7)

        # Fetch earnings calendar this week (FMP API)
        earnings_this_week = set()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"https://financialmodelingprep.com/api/v3/earning_calendar",
                    params={
                        "from": today_date.isoformat(),
                        "to": next_week.isoformat(),
                        "apikey": settings.FMP_API_KEY
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    earnings_this_week = {e.get('symbol') for e in data if e.get('symbol')}
                    logger.info(f"📅 Found {len(earnings_this_week)} stocks with earnings this week")
        except Exception as e:
            logger.warning(f"Could not fetch earnings calendar: {e}")

        # ═══════════════════════════════════════════════════════════════════
        # v8 SHORT INTEREST from Finnhub (stored daily in short_interest table)
        # ═══════════════════════════════════════════════════════════════════
        short_interest = {}
        try:
            async with self.db.acquire() as conn:
                # Check if table exists and has data
                si_rows = await conn.fetch("""
                    SELECT symbol, short_interest, avg_vol_30d, days_to_cover
                    FROM short_interest
                    WHERE updated_at > CURRENT_DATE - INTERVAL '7 days'
                """)
                for row in si_rows:
                    symbol = row['symbol']
                    shares_short = float(row['short_interest'] or 0)
                    avg_vol = float(row['avg_vol_30d'] or 0)
                    # Calculate short interest as % of avg volume (days to cover proxy)
                    if avg_vol > 0:
                        # days_to_cover = short_interest / avg_daily_volume
                        # If > 5 days to cover, that's ~20%+ of float typically
                        pct = min((row['days_to_cover'] or 0) * 4, 100)  # Rough estimate: 5 days = 20%
                        short_interest[symbol] = round(pct, 2)
                logger.info(f"📊 Loaded short interest for {len(short_interest)} symbols from Finnhub cache")
        except Exception as e:
            logger.warning(f"Short interest DB read failed (table may not exist yet): {e}")

        # Build stock data for prompt with catalyst flags
        stock_data = []
        for s in stocks:
            symbol = s["symbol"]
            vol_ratio = float(s["volume_ratio"] or 0)

            # Hard filter: skip low volume ratio stocks
            if vol_ratio < 1.5:
                continue

            # Get short interest for this symbol (default 0 if not found)
            short_pct = short_interest.get(symbol, 0)

            stock_entry = {
                "symbol": symbol,
                "price": float(s["price"]),
                "volume_today": int(s["volume_today"]),
                "pct_change_30d": float(s["pct_change_30d"] or 0),
                "avg_volume_30d": int(s["avg_volume_30d"] or 0),
                "volume_ratio": vol_ratio,
                "volatility_30d": float(s["volatility_30d"] or 0),
                # v6 Catalyst flags
                "catalyst_earnings": symbol in earnings_this_week,
                # v7 Short interest from FINRA
                "short_interest_pct": short_pct,
                "catalyst_short_squeeze": short_pct > 20  # High short = potential squeeze
            }
            stock_data.append(stock_entry)

        logger.info(f"Filtered to {len(stock_data)} stocks after vol_ratio >= 1.5 filter")

        # Format prompt
        prompt = PRESCREEN_PROMPT.replace("{STOCK_DATA}", json.dumps(stock_data, indent=2))

        # Call Fireworks API
        bullish_picks = []
        bearish_picks = []
        summary = ""

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    "https://api.fireworks.ai/inference/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.FIREWORKS_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.0,
                        "max_tokens": 8192
                    }
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]

            logger.info(f"Fireworks response received ({len(content)} chars)")

            # Parse JSON response - handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())
            bullish_picks = result.get("bullish", [])[:50]  # Cap bullish at 50
            bearish_picks = result.get("bearish", [])[:25]  # Cap bearish at 25
            summary = result.get("summary", "")

            # Ensure total doesn't exceed 75
            total = len(bullish_picks) + len(bearish_picks)
            if total > 75:
                # Trim proportionally
                bullish_picks = bullish_picks[:50]
                bearish_picks = bearish_picks[:25]

        except Exception as e:
            logger.error(f"Fireworks API error: {e}")
            # Fallback: select top stocks by volume ratio
            sorted_stocks = sorted(stock_data, key=lambda x: x["volume_ratio"], reverse=True)
            for s in sorted_stocks[:75]:
                if s["pct_change_30d"] > 5:
                    bullish_picks.append(s["symbol"])
                elif s["pct_change_30d"] < -5:
                    bearish_picks.append(s["symbol"])
            summary = f"Fallback selection due to API error: {e}"

        # Save to shortlist_candidates table
        today = date.today()
        stock_lookup = {s["symbol"]: s for s in stock_data}

        # Fetch upcoming economic events (next 7 days) to add to all candidates
        economic_events = []
        async with self.db.acquire() as conn:
            econ_rows = await conn.fetch("""
                SELECT release_name, release_date, impact_level
                FROM economic_calendar
                WHERE release_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
                ORDER BY release_date
            """)
            economic_events = [{"event": r["release_name"], "date": str(r["release_date"]), "impact": r["impact_level"]} for r in econ_rows]

        async with self.db.acquire() as conn:
            # Clear today's existing shortlist
            await conn.execute("DELETE FROM shortlist_candidates WHERE date = $1", today)

            # Insert bullish picks
            for rank, symbol in enumerate(bullish_picks, 1):
                s = stock_lookup.get(symbol, {})
                short_interest = s.get("short_interest_pct", 0) or 0
                # Store technical snapshot with short interest for arbitrator to read
                tech_snapshot = json.dumps({
                    "short_interest_pct": short_interest,
                    "catalyst_earnings": s.get("catalyst_earnings", False),
                    "catalyst_short_squeeze": s.get("catalyst_short_squeeze", False),
                    "volume_ratio": s.get("volume_ratio", 0),
                    "volatility_30d": s.get("volatility_30d", 0)
                })
                await conn.execute("""
                    INSERT INTO shortlist_candidates (
                        date, symbol, rank, direction, prescreen_score, prescreen_reasoning,
                        price_at_selection, technical_snapshot, short_interest_pct, economic_events, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                    ON CONFLICT (date, symbol) DO UPDATE SET
                        rank = EXCLUDED.rank,
                        direction = EXCLUDED.direction,
                        prescreen_score = EXCLUDED.prescreen_score,
                        technical_snapshot = EXCLUDED.technical_snapshot,
                        short_interest_pct = EXCLUDED.short_interest_pct,
                        economic_events = EXCLUDED.economic_events,
                        updated_at = NOW()
                """, today, symbol, rank, "bull", s.get("volume_ratio", 0) * 10, summary, s.get("price", 0), tech_snapshot, short_interest, json.dumps(economic_events))

            # Insert bearish picks
            for rank, symbol in enumerate(bearish_picks, len(bullish_picks) + 1):
                s = stock_lookup.get(symbol, {})
                short_interest = s.get("short_interest_pct", 0) or 0
                tech_snapshot = json.dumps({
                    "short_interest_pct": short_interest,
                    "catalyst_earnings": s.get("catalyst_earnings", False),
                    "catalyst_short_squeeze": s.get("catalyst_short_squeeze", False),
                    "volume_ratio": s.get("volume_ratio", 0),
                    "volatility_30d": s.get("volatility_30d", 0)
                })
                await conn.execute("""
                    INSERT INTO shortlist_candidates (
                        date, symbol, rank, direction, prescreen_score, prescreen_reasoning,
                        price_at_selection, technical_snapshot, short_interest_pct, economic_events, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                    ON CONFLICT (date, symbol) DO UPDATE SET
                        rank = EXCLUDED.rank,
                        direction = EXCLUDED.direction,
                        prescreen_score = EXCLUDED.prescreen_score,
                        technical_snapshot = EXCLUDED.technical_snapshot,
                        short_interest_pct = EXCLUDED.short_interest_pct,
                        economic_events = EXCLUDED.economic_events,
                        updated_at = NOW()
                """, today, symbol, rank, "bear", s.get("volume_ratio", 0) * 10, summary, s.get("price", 0), tech_snapshot, short_interest, json.dumps(economic_events))

        total_picks = len(bullish_picks) + len(bearish_picks)
        earnings_count = sum(1 for s in stock_data if s.get("catalyst_earnings"))
        logger.info(f"✅ Saved {total_picks} stocks ({len(bullish_picks)} bull, {len(bearish_picks)} bear)")
        logger.info(f"📅 {earnings_count} stocks have earnings this week (catalyst)")

        # Return catalyst data for downstream use (arbitrator/fib_calculator)
        catalyst_data = {
            symbol: {
                "catalyst_earnings": s.get("catalyst_earnings", False),
                "short_interest_pct": s.get("short_interest_pct", 0)
            }
            for s in stock_data
            for symbol in [s["symbol"]]
        }

        return {
            "shortlist_count": total_picks,
            "bullish": bullish_picks,
            "bearish": bearish_picks,
            "summary": summary,
            "catalyst_data": catalyst_data  # v6: Pass to arbitrator for fib_calculator
        }