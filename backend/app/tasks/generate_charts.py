#!/usr/bin/env python3
"""
Generate charts for shortlist stocks → Firebase Storage → URL in PostgreSQL
Runs at 8:15 AM ET → CPU only → $0 cost
"""

import asyncio
import logging
import io
from datetime import date
from typing import Dict
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for Render worker
import matplotlib.pyplot as plt
import pandas as pd

from app.core.database import get_asyncpg_pool
from app.core.celery_app import celery_app
from app.core.firebase import upload_chart_to_storage

logger = logging.getLogger(__name__)

# Dark theme — perfect for Groq Vision
plt.style.use("dark_background")
BACKGROUND = "#000000"
GRID = "#333333"
BULL = "#00ff88"
BEAR = "#ff4444"
VOL = "#666666"


class ChartGenerator:
    """Generate charts and upload to Firebase Storage"""

    def __init__(self):
        self.db = None
        self.fig = plt.figure(figsize=(2.56, 2.56), dpi=100)

    async def initialize(self):
        self.db = await get_asyncpg_pool()

    async def generate_all_charts(self) -> Dict:
        """Generate charts for today's SHORT_LIST → Firebase Storage → URL in DB"""
        logger.info("📊 Starting chart generation for today's shortlist")

        today = date.today()
        date_str = today.strftime("%Y-%m-%d")

        # Get today's SHORT_LIST symbols
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT symbol, rank
                FROM shortlist_candidates
                WHERE date = $1
                ORDER BY rank
            """, today)

        symbols = [row["symbol"] for row in rows]
        if not symbols:
            logger.warning("No SHORT_LIST found for today")
            return {"success": False, "reason": "no_shortlist", "charts": 0}

        logger.info(f"Generating {len(symbols)} charts...")

        success_count = 0
        failed = []

        for symbol in symbols:
            df = await self._fetch_90d(symbol)
            if df is not None and len(df) >= 30:
                # Render chart to PNG bytes
                png_bytes = self._render_chart(df)

                # Upload to Firebase Storage
                chart_url = upload_chart_to_storage(symbol, date_str, png_bytes)

                if chart_url:
                    # Store URL in shortlist_candidates
                    await self._store_chart_url(symbol, today, chart_url)
                    success_count += 1
                else:
                    failed.append(symbol)
                    logger.warning(f"Failed to upload chart for {symbol}")
            else:
                failed.append(symbol)
                logger.warning(f"Insufficient data for {symbol}")

        logger.info(f"✅ Generated {success_count}/{len(symbols)} charts")

        return {
            "success": True,
            "charts_generated": success_count,
            "charts_failed": len(failed),
            "failed_symbols": failed[:10]  # First 10 failures
        }

    async def _fetch_90d(self, symbol: str) -> pd.DataFrame:
        """Pull 90-day OHLCV from Prime DB"""
        query = """
        SELECT date, open_price, high_price, low_price, close_price, volume
        FROM prime_ohlc_90d
        WHERE symbol = $1
        ORDER BY date DESC
        LIMIT 90
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, symbol)

        if not rows:
            return pd.DataFrame()

        # Convert asyncpg Records to dicts
        data = [dict(row) for row in rows]
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        return df

    def _render_chart(self, df: pd.DataFrame) -> bytes:
        """Render 256×256 PNG → bytes"""
        self.fig.clear()
        ax1, ax2 = self.fig.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]})

        # Candlesticks
        for i, (_, row) in enumerate(df.iterrows()):
            color = BULL if row["close_price"] >= row["open_price"] else BEAR
            ax1.plot([i, i], [row["low_price"], row["high_price"]], color=color, lw=0.8)
            rect = plt.Rectangle(
                (i - 0.35, min(row["open_price"], row["close_price"])),
                0.7, abs(row["close_price"] - row["open_price"]),
                facecolor=color, edgecolor=color, lw=0.5
            )
            ax1.add_patch(rect)

        # Volume
        ax2.bar(range(len(df)), df["volume"], color=VOL, width=0.8)

        # Clean styling
        for ax in (ax1, ax2):
            ax.set_facecolor(BACKGROUND)
            ax.grid(True, color=GRID, alpha=0.3, lw=0.4)
            ax.set_xticks([])
            ax.set_yticks([])

        plt.subplots_adjust(left=0, right=1, top=1, bottom=0, hspace=0)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
        buf.seek(0)
        return buf.read()

    async def _store_chart_url(self, symbol: str, today: date, chart_url: str):
        """Store chart URL in shortlist_candidates"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE shortlist_candidates
                SET chart_url = $1, updated_at = NOW()
                WHERE date = $2 AND symbol = $3
            """, chart_url, today, symbol)


# Global singleton
_generator = None


async def get_chart_generator() -> ChartGenerator:
    global _generator
    if _generator is None:
        _generator = ChartGenerator()
        await _generator.initialize()
    return _generator


# Celery task
@celery_app.task(name="tasks.generate_charts")
def generate_charts():
    """Celery task — runs at 8:15 AM ET"""
    async def _run():
        from app.services.system_state import is_system_on

        # Check if system is ON
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping chart generation")
            return {"skipped": True, "reason": "system_off"}

        gen = await get_chart_generator()
        return await gen.generate_all_charts()

    return asyncio.run(_run())
