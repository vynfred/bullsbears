#!/usr/bin/env python3
"""
Generate annotated charts for shortlist stocks → Firebase Storage → URL in PostgreSQL
Pretty charts with S/R lines + volume profile for frontend display
Runs at 8:15 AM ET → CPU only → $0 cost
"""

import asyncio
import logging
import io
from datetime import date
from typing import Dict
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for Render worker
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import pandas as pd

from app.core.database import get_asyncpg_pool
from app.core.celery_app import celery_app
from app.core.firebase import upload_chart_to_storage

logger = logging.getLogger(__name__)

# BullsBears color scheme (from globals.css)
BACKGROUND = "#0F1419"  # Dark background
GRID = "#1E2A35"  # Subtle grid
BULL = "#77E4C8"  # Mint green for bulls/up
BEAR = "#FF8080"  # Red for bears/down
NEUTRAL = "#BADFDB"  # Light mint
SUPPORT = "#77E4C8"  # Support lines (mint)
RESISTANCE = "#FF8080"  # Resistance lines (red)
VOLUME_BULL = "rgba(119, 228, 200, 0.6)"
VOLUME_BEAR = "rgba(255, 128, 128, 0.6)"
TEXT_COLOR = "#E8EAED"  # Light text


class ChartGenerator:
    """Generate pretty annotated charts and upload to Firebase Storage"""

    def __init__(self):
        self.db = None

    async def initialize(self):
        self.db = await get_asyncpg_pool()

    async def generate_all_charts(self) -> Dict:
        """Generate charts for latest SHORT_LIST → Firebase Storage → URL in DB"""
        logger.info("📊 Starting chart generation for shortlist")

        # Get the most recent shortlist date (handles timezone differences)
        async with self.db.acquire() as conn:
            latest = await conn.fetchrow("""
                SELECT MAX(date) as latest_date FROM shortlist_candidates
            """)

        if not latest or not latest['latest_date']:
            logger.warning("No shortlist found in database")
            return {"success": False, "reason": "no_shortlist", "charts": 0}

        shortlist_date = latest['latest_date']
        date_str = shortlist_date.strftime("%Y-%m-%d")
        logger.info(f"Using shortlist date: {date_str}")

        # Get SHORT_LIST symbols for that date
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT symbol, rank
                FROM shortlist_candidates
                WHERE date = $1
                ORDER BY rank
            """, shortlist_date)

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
                # Render pretty annotated chart to PNG bytes
                png_bytes = self._render_chart(df, symbol)

                # Upload to Firebase Storage
                chart_url = upload_chart_to_storage(symbol, date_str, png_bytes)

                if chart_url:
                    # Store URL in shortlist_candidates
                    await self._store_chart_url(symbol, shortlist_date, chart_url)
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
        # Convert Decimal to float for matplotlib compatibility
        for col in ["open_price", "high_price", "low_price", "close_price"]:
            df[col] = df[col].astype(float)
        df["volume"] = df["volume"].astype(float)
        df = df.sort_values("date").set_index("date")
        return df

    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict:
        """Calculate support and resistance levels using pivot points"""
        highs = df["high_price"].values
        lows = df["low_price"].values

        # Use recent 30 days for S/R calculation
        recent_highs = highs[-30:]
        recent_lows = lows[-30:]

        # Find local maxima/minima for S/R levels
        resistance_levels = []
        support_levels = []

        # Simple pivot point method
        for i in range(2, len(recent_highs) - 2):
            # Local high (resistance)
            if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i-2] and \
               recent_highs[i] > recent_highs[i+1] and recent_highs[i] > recent_highs[i+2]:
                resistance_levels.append(recent_highs[i])
            # Local low (support)
            if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i-2] and \
               recent_lows[i] < recent_lows[i+1] and recent_lows[i] < recent_lows[i+2]:
                support_levels.append(recent_lows[i])

        # If not enough levels found, use percentile method
        if len(resistance_levels) < 2:
            resistance_levels = [np.percentile(recent_highs, 80), np.percentile(recent_highs, 95)]
        if len(support_levels) < 2:
            support_levels = [np.percentile(recent_lows, 5), np.percentile(recent_lows, 20)]

        # Sort and dedupe (keep top 2 of each)
        resistance_levels = sorted(set(resistance_levels), reverse=True)[:2]
        support_levels = sorted(set(support_levels))[:2]

        return {"resistance": resistance_levels, "support": support_levels}

    def _render_chart(self, df: pd.DataFrame, symbol: str = "") -> bytes:
        """Render pretty annotated chart with S/R lines and volume profile"""
        # Create figure with GridSpec for price chart + volume profile on right
        fig = plt.figure(figsize=(4, 3), dpi=100, facecolor=BACKGROUND)
        gs = GridSpec(3, 4, figure=fig, height_ratios=[3, 1, 0.1], width_ratios=[3, 0.5, 0.02, 0.3])

        ax_price = fig.add_subplot(gs[0, 0])  # Main price chart
        ax_vol = fig.add_subplot(gs[1, 0], sharex=ax_price)  # Volume bars
        ax_profile = fig.add_subplot(gs[0, 3])  # Volume profile (right side)

        # Set backgrounds
        for ax in [ax_price, ax_vol, ax_profile]:
            ax.set_facecolor(BACKGROUND)

        # Calculate S/R levels
        sr_levels = self._calculate_support_resistance(df)

        # Draw candlesticks
        for i, (_, row) in enumerate(df.iterrows()):
            is_bull = row["close_price"] >= row["open_price"]
            color = BULL if is_bull else BEAR

            # Wick
            ax_price.plot([i, i], [row["low_price"], row["high_price"]],
                         color=color, lw=1, solid_capstyle='round')
            # Body
            body_bottom = min(row["open_price"], row["close_price"])
            body_height = abs(row["close_price"] - row["open_price"])
            rect = plt.Rectangle((i - 0.35, body_bottom), 0.7, max(body_height, 0.01),
                                 facecolor=color, edgecolor=color, lw=0.5)
            ax_price.add_patch(rect)

        # Draw S/R lines
        for level in sr_levels["resistance"]:
            ax_price.axhline(y=level, color=RESISTANCE, linestyle='--',
                            lw=1, alpha=0.7, label='R')
        for level in sr_levels["support"]:
            ax_price.axhline(y=level, color=SUPPORT, linestyle='--',
                            lw=1, alpha=0.7, label='S')

        # Volume bars with color
        colors = [BULL if df.iloc[i]["close_price"] >= df.iloc[i]["open_price"] else BEAR
                  for i in range(len(df))]
        ax_vol.bar(range(len(df)), df["volume"], color=colors, width=0.8, alpha=0.7)

        # Volume profile (horizontal bars on right)
        price_range = np.linspace(df["low_price"].min(), df["high_price"].max(), 20)
        vol_profile = np.zeros(len(price_range) - 1)
        for i, (_, row) in enumerate(df.iterrows()):
            for j in range(len(price_range) - 1):
                if price_range[j] <= row["close_price"] <= price_range[j + 1]:
                    vol_profile[j] += row["volume"]

        # Normalize and plot volume profile
        if vol_profile.max() > 0:
            vol_profile = vol_profile / vol_profile.max()
        price_mids = (price_range[:-1] + price_range[1:]) / 2
        ax_profile.barh(price_mids, vol_profile, height=(price_range[1] - price_range[0]) * 0.9,
                       color=NEUTRAL, alpha=0.5)
        ax_profile.set_ylim(ax_price.get_ylim())

        # Styling
        ax_price.grid(True, color=GRID, alpha=0.3, lw=0.5)
        ax_vol.grid(True, color=GRID, alpha=0.2, lw=0.5)
        ax_price.set_xlim(-1, len(df))

        # Remove ticks for cleaner look
        ax_price.set_xticks([])
        ax_vol.set_xticks([])
        ax_profile.set_xticks([])
        ax_profile.set_yticks([])

        # Price labels on right side of price chart
        ax_price.yaxis.set_label_position("right")
        ax_price.yaxis.tick_right()
        ax_price.tick_params(axis='y', colors=TEXT_COLOR, labelsize=6)
        ax_vol.set_yticks([])

        # Add symbol label
        if symbol:
            ax_price.text(0.02, 0.98, symbol, transform=ax_price.transAxes,
                         fontsize=8, fontweight='bold', color=TEXT_COLOR,
                         verticalalignment='top')

        plt.subplots_adjust(left=0.02, right=0.88, top=0.98, bottom=0.02, hspace=0.05, wspace=0.1)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", facecolor=BACKGROUND, edgecolor='none')
        plt.close(fig)
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
