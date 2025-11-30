# backend/app/services/cloud_agents/prescreen_agent.py
"""
Prescreen Agent - Fireworks.ai qwen2.5-72b-instruct
ACTIVE tier (~4,400 stocks) → SHORT_LIST (exactly 75)
"""

import httpx
import json
import logging
from datetime import date
from pathlib import Path
from app.core.config import settings
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

class PrescreenAgent:
    def __init__(self):
        self.model = "accounts/fireworks/models/qwen2.5-72b-instruct"
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "screen_prompt.txt"
        self.db = None

    async def initialize(self):
        """Initialize agent and DB connection"""
        self.db = await get_asyncpg_pool()

    async def run_prescreen(self) -> dict:
        """Run prescreen via Fireworks.ai"""
        logger.info("🔍 Running prescreen with qwen2.5-72b-instruct")

        if not self.db:
            self.db = await get_asyncpg_pool()

        # Get active stocks with recent price data from prime_ohlc_90d
        async with self.db.acquire() as conn:
            stocks = await conn.fetch("""
                WITH latest_prices AS (
                    SELECT DISTINCT ON (symbol)
                        symbol,
                        close_price as price,
                        volume,
                        date
                    FROM prime_ohlc_90d
                    ORDER BY symbol, date DESC
                )
                SELECT symbol, price, volume
                FROM latest_prices
                WHERE volume > 100000  -- Filter low volume
                AND price > 1.0        -- No penny stocks
                ORDER BY volume DESC
                LIMIT 500              -- Top 500 by volume for AI to analyze
            """)

        if not stocks:
            logger.warning("No stocks found in prime_ohlc_90d")
            return {"shortlist_count": 0, "tickers": [], "error": "no_stocks"}

        logger.info(f"Found {len(stocks)} active stocks to screen")

        # Build stock list for prompt
        stock_list = [{"symbol": s["symbol"], "price": float(s["price"]), "volume": int(s["volume"])} for s in stocks]

        # Load and format prompt
        try:
            prompt_template = self.prompt_path.read_text(encoding="utf-8")
            prompt = prompt_template.replace("{STOCK_DATA}", json.dumps(stock_list[:200]))  # Send top 200 to API
        except FileNotFoundError:
            # Default prompt if file doesn't exist
            prompt = f"""You are a stock screening AI. Analyze these stocks and select the top 75 most promising for short-term trading (1-5 days).

STOCKS TO ANALYZE:
{json.dumps(stock_list[:200], indent=2)}

Return a JSON object with this exact structure:
{{
    "filtered_tickers": ["AAPL", "NVDA", ...],  // exactly 75 symbols
    "summary": "Brief explanation of selection criteria"
}}

Focus on: high volume, price momentum, volatility potential. Return ONLY valid JSON."""

        # Call Fireworks API
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
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
                        "max_tokens": 4096
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
            tickers = result.get("filtered_tickers", [])[:75]  # Cap at 75

        except Exception as e:
            logger.error(f"Fireworks API error: {e}")
            # Fallback: select top 75 by volume
            tickers = [s["symbol"] for s in stock_list[:75]]
            result = {"summary": f"Fallback selection due to API error: {e}"}

        # Save to shortlist_candidates table
        today = date.today()
        async with self.db.acquire() as conn:
            # Clear today's existing shortlist
            await conn.execute("DELETE FROM shortlist_candidates WHERE date = $1", today)

            # Insert new shortlist
            for rank, symbol in enumerate(tickers, 1):
                # Get price for this symbol
                price_row = await conn.fetchrow("""
                    SELECT close_price FROM prime_ohlc_90d
                    WHERE symbol = $1 ORDER BY date DESC LIMIT 1
                """, symbol)
                price = float(price_row["close_price"]) if price_row else 0.0

                await conn.execute("""
                    INSERT INTO shortlist_candidates (
                        date, symbol, rank, prescreen_score, prescreen_reasoning,
                        price_at_selection, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (date, symbol) DO UPDATE SET
                        rank = EXCLUDED.rank,
                        prescreen_score = EXCLUDED.prescreen_score,
                        updated_at = NOW()
                """, today, symbol, rank, 75 - rank + 1, result.get("summary", ""), price)

        logger.info(f"✅ Saved {len(tickers)} stocks to shortlist_candidates")

        return {
            "shortlist_count": len(tickers),
            "tickers": tickers,
            "summary": result.get("summary", "")
        }