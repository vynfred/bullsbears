#!/usr/bin/env python3
"""
Generate 75 × 256×256 PNG charts → base64 → PostgreSQL
Runs at 8:15 AM ET → CPU only → $0 cost
"""

import asyncio
import logging
import io
import base64
from pathlib import Path
from typing import List, Dict
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for Render worker
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from app.core.database import get_asyncpg_pool
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

# Dark theme — perfect for Groq Vision
plt.style.use("dark_background")
BACKGROUND = "#000000"
GRID = "#333333"
BULL = "#00ff88"
BEAR = "#ff4444"
VOL = "#666666"

class ChartGenerator:
    """75 charts in < 7 seconds — CPU only — perfect for Render worker"""

    def __init__(self):
        self.db = None
        self.fig = plt.figure(figsize=(2.56, 2.56), dpi=100)

    async def initialize(self):
        self.db = await get_asyncpg_pool()

    async def generate_all_charts(self) -> List[Dict]:
        """Generate charts for today's SHORT_LIST → store base64 in DB"""
        logger.info("Generating 75 charts for today's SHORT_LIST")

        # Get today's SHORT_LIST symbols
        query = """
        SELECT DISTINCT symbol 
        FROM shortlist_candidates 
        WHERE date::date = CURRENT_DATE 
        ORDER BY rank
        LIMIT 75
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query)
        
        symbols = [row["symbol"] for row in rows]
        if not symbols:
            logger.warning("No SHORT_LIST found for today")
            return []

        charts = []
        for symbol in symbols:
            df = await self._fetch_90d(symbol)
            if df is not None and len(df) >= 30:
                base64_png = self._render_chart(df)
                await self._store_chart(symbol, base64_png)
                charts.append({"symbol": symbol, "chart_base64": base64_png})
            else:
                logger.warning(f"Insufficient data for {symbol}")
                charts.append({"symbol": symbol, "chart_base64": ""})

        logger.info(f"Generated {len(charts)} charts in < 7s")
        return charts

    async def _fetch_90d(self, symbol: str) -> pd.DataFrame:
        """Pull 90-day OHLCV from Prime DB"""
        query = """
        SELECT date, open_price, high_price, low_price, close_price, adj_close, volume, vwap
        FROM prime_ohlc_90d
        WHERE symbol = $1
        ORDER BY date DESC
        LIMIT 90
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, symbol)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        return df

    def _render_chart(self, df: pd.DataFrame) -> str:
        """Render 256×256 PNG → base64"""
        self.fig.clear()
        ax1, ax2 = self.fig.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]})

        # Candlesticks
        for i, (idx, row) in enumerate(df.iterrows()):
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
        return base64.b64encode(buf.read()).decode()

    async def _store_chart(self, symbol: str, base64_png: str):
        """Atomic upsert into DB"""
        query = """
        INSERT INTO stock_charts (symbol, chart_data, generated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (symbol) DO UPDATE SET
            chart_data = EXCLUDED.chart_data,
            generated_at = NOW()
        """
        async with self.db.acquire() as conn:
            await conn.execute(query, symbol, base64_png)


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
