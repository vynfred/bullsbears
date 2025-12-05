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

STOCK DATA (symbol, price, volume_today, pct_change_30d, avg_volume_30d, volume_ratio, volatility_30d):
{STOCK_DATA}

SELECTION RULES:
- Only select stocks with UNAMBIGUOUS signals. Mixed or weak = SKIP.
- Maximum 75 total picks (bullish + bearish combined). Can be fewer if signals are weak.

BULLISH CRITERIA (must meet ≥2):
1. 30-day price change ≥ +12% AND volume_ratio > 1.5 (momentum + volume confirmation)
2. Breaking recent highs on elevated volume (volume_ratio > 2.0)
3. Volatility expansion after consolidation (volatility_30d > 5% with positive price change)

BEARISH CRITERIA (must meet ≥2):
1. 30-day price change ≤ -12% AND volume_ratio > 1.5 (breakdown + volume confirmation)
2. Support breakdown on elevated volume (volume_ratio > 2.0 with negative momentum)
3. Volatility spike after tight range (volatility_30d > 8% with negative price change)

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
        # v7 FINRA SHORT INTEREST (bi-weekly updates, use last available)
        # ═══════════════════════════════════════════════════════════════════
        short_interest = {}
        try:
            # FINRA publishes bi-weekly, use ~15 days ago to get latest available
            latest_si_date = (today_date - timedelta(days=15)).strftime("%Y-%m-%d")
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.finra.org/data/group/otcMarket/name/EquityShortInterest",
                    headers={"Content-Type": "application/json"},
                    json={"settlementDate": latest_si_date}
                )
                if resp.status_code == 200:
                    si_data = resp.json()
                    for row in si_data:
                        symbol = row.get("symbol", "").upper()
                        shares_short = float(row.get("sharesShort", 0))
                        float_shares = float(row.get("floatSharesOutstanding", 0))
                        if float_shares > 0:
                            pct = (shares_short / float_shares) * 100
                            short_interest[symbol] = round(pct, 2)
                    logger.info(f"📊 Fetched short interest for {len(short_interest)} symbols from FINRA")
                else:
                    logger.warning(f"FINRA API returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"FINRA short interest fetch failed: {e}")

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

        async with self.db.acquire() as conn:
            # Clear today's existing shortlist
            await conn.execute("DELETE FROM shortlist_candidates WHERE date = $1", today)

            # Insert bullish picks
            for rank, symbol in enumerate(bullish_picks, 1):
                s = stock_lookup.get(symbol, {})
                await conn.execute("""
                    INSERT INTO shortlist_candidates (
                        date, symbol, rank, direction, prescreen_score, prescreen_reasoning,
                        price_at_selection, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    ON CONFLICT (date, symbol) DO UPDATE SET
                        rank = EXCLUDED.rank,
                        direction = EXCLUDED.direction,
                        prescreen_score = EXCLUDED.prescreen_score,
                        updated_at = NOW()
                """, today, symbol, rank, "bull", s.get("volume_ratio", 0) * 10, summary, s.get("price", 0))

            # Insert bearish picks
            for rank, symbol in enumerate(bearish_picks, len(bullish_picks) + 1):
                s = stock_lookup.get(symbol, {})
                await conn.execute("""
                    INSERT INTO shortlist_candidates (
                        date, symbol, rank, direction, prescreen_score, prescreen_reasoning,
                        price_at_selection, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    ON CONFLICT (date, symbol) DO UPDATE SET
                        rank = EXCLUDED.rank,
                        direction = EXCLUDED.direction,
                        prescreen_score = EXCLUDED.prescreen_score,
                        updated_at = NOW()
                """, today, symbol, rank, "bear", s.get("volume_ratio", 0) * 10, summary, s.get("price", 0))

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