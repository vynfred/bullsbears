#!/usr/bin/env python3
"""
Generate beautiful shareable charts for final picks with:
- 90-day candlestick history
- Target zones (low, high, moon) shaded
- Stop loss level
- Entry price marker
- Annotated labels
- Timeframe in top-left, dates at bottom, prices on right

Runs right after arbitrator finalizes picks
"""

import asyncio
import logging
import io
from datetime import date, datetime
from typing import Dict, Optional
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.dates import DateFormatter, AutoDateLocator
import pandas as pd

from app.core.database import get_asyncpg_pool
from app.core.firebase import upload_chart_to_storage

logger = logging.getLogger(__name__)

# BullsBears color scheme
BACKGROUND = "#0F1419"
GRID = "#1E2A35"
BULL_CANDLE = "#77E4C8"  # Mint green
BEAR_CANDLE = "#FF8080"  # Red
BULL_TARGET_ZONE = "#22C55E"  # Green for bullish targets
BEAR_TARGET_ZONE = "#EF4444"  # Red for bearish targets
STOP_LOSS_BULL = "#EF4444"  # Red stop for bullish
STOP_LOSS_BEAR = "#22C55E"  # Green stop for bearish
ENTRY_COLOR = "#F59E0B"  # Amber for entry
TEXT_COLOR = "#E8EAED"
WATERMARK_COLOR = "#FFFFFF"


class PrettyChartGenerator:
    """Generate beautiful annotated charts for final picks"""

    def __init__(self):
        self.db = None

    async def initialize(self):
        self.db = await get_asyncpg_pool()

    async def generate_charts_for_picks(self) -> Dict:
        """Generate pretty charts for all current picks"""
        logger.info("🎨 Generating pretty charts for final picks...")

        async with self.db.acquire() as conn:
            # Get today's picks with targets
            picks = await conn.fetch("""
                SELECT p.id, p.symbol, p.direction, p.confidence,
                       p.target_low, p.target_high, p.pick_context,
                       sc.price_at_selection as entry_price
                FROM picks p
                LEFT JOIN shortlist_candidates sc 
                    ON sc.symbol = p.symbol AND sc.date = p.created_at::date
                WHERE p.created_at::date = CURRENT_DATE
                ORDER BY p.confidence DESC
            """)

        if not picks:
            logger.warning("No picks found for today")
            return {"success": False, "reason": "no_picks", "charts": 0}

        success_count = 0
        failed = []
        date_str = datetime.now().strftime("%Y-%m-%d")

        for pick in picks:
            symbol = pick["symbol"]
            direction = pick["direction"]

            # Get entry price
            entry_price = float(pick["entry_price"]) if pick["entry_price"] else None

            # Get targets from pick_context (includes moon target and stop loss)
            # Handle both JSONB (dict) and JSON string formats
            pick_context = pick["pick_context"]
            if isinstance(pick_context, str):
                import json
                try:
                    pick_context = json.loads(pick_context)
                except (json.JSONDecodeError, TypeError):
                    pick_context = {}
            elif pick_context is None:
                pick_context = {}
            fib_data = pick_context.get("fib", {})

            target_low = float(pick["target_low"]) if pick["target_low"] else None
            target_high = float(pick["target_high"]) if pick["target_high"] else None

            # Extract moon target and stop loss from fib calculation
            # fib_data contains: target_1 (primary), target_2 (moon), stop_loss
            moon_target = fib_data.get("target_2")
            stop_loss = fib_data.get("stop_loss")

            # Ensure numeric types
            if moon_target is not None:
                moon_target = float(moon_target)
            if stop_loss is not None:
                stop_loss = float(stop_loss)

            # Fallback to estimation if fib data missing
            if moon_target is None:
                if direction == "bullish" and target_high:
                    moon_target = target_high * 1.15
                elif direction == "bearish" and target_low:
                    moon_target = target_low * 0.85

            if stop_loss is None:
                if direction == "bullish":
                    stop_loss = fib_data.get("swing_low") or (entry_price * 0.92 if entry_price else None)
                else:
                    stop_loss = fib_data.get("swing_high") or (entry_price * 1.08 if entry_price else None)

            # Fetch OHLC data
            df = await self._fetch_90d(symbol)
            if df is None or len(df) < 30:
                failed.append(symbol)
                logger.warning(f"Insufficient data for {symbol}")
                continue

            # Generate pretty chart
            png_bytes = self._render_pretty_chart(
                df=df,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                target_low=target_low,
                target_high=target_high,
                moon_target=moon_target,
                stop_loss=stop_loss
            )

            # Upload to Firebase Storage (different folder for pretty charts)
            chart_url = upload_chart_to_storage(
                symbol, 
                date_str, 
                png_bytes, 
                folder="pretty"
            )

            if chart_url:
                # Store pretty chart URL in picks table
                await self._store_pretty_chart_url(pick["id"], chart_url)
                success_count += 1
                logger.info(f"✅ Pretty chart generated for {symbol}")
            else:
                failed.append(symbol)

        logger.info(f"🎨 Generated {success_count}/{len(picks)} pretty charts")
        return {
            "success": True,
            "charts_generated": success_count,
            "charts_failed": len(failed),
            "failed_symbols": failed
        }

    async def _fetch_90d(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch 90-day OHLCV data"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM prime_ohlc_90d
                WHERE symbol = $1
                ORDER BY date ASC
            """, symbol)

        if not rows:
            return None

        df = pd.DataFrame([dict(r) for r in rows])
        df["date"] = pd.to_datetime(df["date"])
        for col in ["open_price", "high_price", "low_price", "close_price"]:
            df[col] = df[col].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df.set_index("date")

    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict:
        """Calculate support and resistance levels using pivot points"""
        import numpy as np
        highs = df["high_price"].values
        lows = df["low_price"].values

        # Use recent 30 days for S/R calculation
        recent_highs = highs[-30:]
        recent_lows = lows[-30:]

        resistance_levels = []
        support_levels = []

        # Simple pivot point method
        for i in range(2, len(recent_highs) - 2):
            if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i-2] and \
               recent_highs[i] > recent_highs[i+1] and recent_highs[i] > recent_highs[i+2]:
                resistance_levels.append(recent_highs[i])
            if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i-2] and \
               recent_lows[i] < recent_lows[i+1] and recent_lows[i] < recent_lows[i+2]:
                support_levels.append(recent_lows[i])

        # Fallback to percentile method
        if len(resistance_levels) < 2:
            resistance_levels = [np.percentile(recent_highs, 80), np.percentile(recent_highs, 95)]
        if len(support_levels) < 2:
            support_levels = [np.percentile(recent_lows, 5), np.percentile(recent_lows, 20)]

        resistance_levels = sorted(set(resistance_levels), reverse=True)[:2]
        support_levels = sorted(set(support_levels))[:2]

        return {"resistance": resistance_levels, "support": support_levels}

    def _render_pretty_chart(
        self,
        df: pd.DataFrame,
        symbol: str,
        direction: str,
        entry_price: Optional[float],
        target_low: Optional[float],
        target_high: Optional[float],
        moon_target: Optional[float],
        stop_loss: Optional[float]
    ) -> bytes:
        """Render beautiful annotated chart with S/R lines and target triangle"""
        from matplotlib.patches import Polygon
        import numpy as np

        fig, (ax_price, ax_vol) = plt.subplots(
            2, 1, figsize=(12, 8), dpi=150,
            gridspec_kw={'height_ratios': [4, 1], 'hspace': 0.05},
            facecolor=BACKGROUND
        )

        ax_price.set_facecolor(BACKGROUND)
        ax_vol.set_facecolor(BACKGROUND)

        is_bullish = direction == "bullish"
        target_color = BULL_TARGET_ZONE if is_bullish else BEAR_TARGET_ZONE
        stop_color = STOP_LOSS_BULL if is_bullish else STOP_LOSS_BEAR

        dates = df.index.tolist()
        x_pos = range(len(dates))

        price_min = df["low_price"].min()
        price_max = df["high_price"].max()

        # Extend range to include targets and stop loss
        all_levels = [price_min, price_max]
        if target_low: all_levels.append(target_low)
        if target_high: all_levels.append(target_high)
        if moon_target: all_levels.append(moon_target)
        if stop_loss: all_levels.append(stop_loss)

        y_min = min(all_levels) * 0.95
        y_max = max(all_levels) * 1.05

        # Calculate S/R levels
        sr_levels = self._calculate_support_resistance(df)

        # Draw S/R lines FIRST (behind everything)
        for level in sr_levels["resistance"]:
            ax_price.axhline(y=level, color='#FF8080', linestyle='--', lw=1.2, alpha=0.5, zorder=1)
        for level in sr_levels["support"]:
            ax_price.axhline(y=level, color='#77E4C8', linestyle='--', lw=1.2, alpha=0.5, zorder=1)

        # Draw candlesticks
        for i, (idx, row) in enumerate(df.iterrows()):
            is_bull = row["close_price"] >= row["open_price"]
            color = BULL_CANDLE if is_bull else BEAR_CANDLE

            ax_price.plot([i, i], [row["low_price"], row["high_price"]], color=color, lw=1.5, zorder=2)
            body_bottom = min(row["open_price"], row["close_price"])
            body_height = abs(row["close_price"] - row["open_price"])
            rect = Rectangle((i - 0.35, body_bottom), 0.7, max(body_height, 0.01),
                             facecolor=color, edgecolor=color, zorder=3)
            ax_price.add_patch(rect)

        # Draw TARGET TRIANGLE from entry point
        entry_x = len(df) - 1  # Entry at last candle
        triangle_end_x = len(df) + 12  # Triangle extends into future

        if entry_price and (target_low or target_high or moon_target):
            # Determine triangle vertices based on direction
            if is_bullish:
                # Bullish: triangle points upward from entry
                top_target = moon_target if moon_target else (target_high if target_high else target_low)
                bottom_target = stop_loss if stop_loss else entry_price * 0.92

                # Main target zone triangle (entry → target range)
                if target_low and target_high:
                    tri_points = [
                        (entry_x, entry_price),  # Start at entry
                        (triangle_end_x, target_high),  # Upper target
                        (triangle_end_x, target_low),  # Lower target
                    ]
                    triangle = Polygon(tri_points, closed=True, facecolor=target_color,
                                      alpha=0.2, edgecolor=target_color, lw=1.5, zorder=4)
                    ax_price.add_patch(triangle)

                # Moon extension (lighter triangle above)
                if moon_target and target_high:
                    moon_tri = [
                        (entry_x, entry_price),
                        (triangle_end_x, moon_target),
                        (triangle_end_x, target_high),
                    ]
                    moon_triangle = Polygon(moon_tri, closed=True, facecolor=target_color,
                                           alpha=0.08, edgecolor=target_color, lw=1, ls=':', zorder=4)
                    ax_price.add_patch(moon_triangle)

            else:
                # Bearish: triangle points downward from entry
                if target_low and target_high:
                    tri_points = [
                        (entry_x, entry_price),
                        (triangle_end_x, target_low),  # Lower target (deeper drop)
                        (triangle_end_x, target_high),  # Upper target (smaller drop)
                    ]
                    triangle = Polygon(tri_points, closed=True, facecolor=target_color,
                                      alpha=0.2, edgecolor=target_color, lw=1.5, zorder=4)
                    ax_price.add_patch(triangle)

                # Moon extension (deeper drop)
                if moon_target and target_low:
                    moon_tri = [
                        (entry_x, entry_price),
                        (triangle_end_x, moon_target),
                        (triangle_end_x, target_low),
                    ]
                    moon_triangle = Polygon(moon_tri, closed=True, facecolor=target_color,
                                           alpha=0.08, edgecolor=target_color, lw=1, ls=':', zorder=4)
                    ax_price.add_patch(moon_triangle)

        # Annotations on right side (outside triangle)
        annotation_x = triangle_end_x + 1

        if target_low:
            ax_price.text(annotation_x, target_low, f'Target 1: ${target_low:.2f}',
                         color=target_color, fontsize=9, fontweight='bold', va='center', zorder=10)
        if target_high:
            ax_price.text(annotation_x, target_high, f'Target 2: ${target_high:.2f}',
                         color=target_color, fontsize=9, fontweight='bold', va='center', zorder=10)
        if moon_target:
            ax_price.text(annotation_x, moon_target, f'🌙 Moon: ${moon_target:.2f}',
                         color=target_color, fontsize=8, va='center', alpha=0.8, zorder=10)

        if stop_loss:
            ax_price.axhline(y=stop_loss, color=stop_color, lw=2, ls='-', alpha=0.7, zorder=5)
            ax_price.text(annotation_x, stop_loss, f'⛔ Stop: ${stop_loss:.2f}',
                         color=stop_color, fontsize=9, fontweight='bold', va='center', zorder=10)

        if entry_price:
            ax_price.scatter([entry_x], [entry_price], color=ENTRY_COLOR,
                            s=120, zorder=6, marker='o', edgecolors='white', linewidths=1.5)
            ax_price.text(annotation_x, entry_price, f'Entry: ${entry_price:.2f}',
                         color=ENTRY_COLOR, fontsize=9, fontweight='bold', va='center', zorder=10)

        # Volume bars
        colors = [BULL_CANDLE if df.iloc[i]["close_price"] >= df.iloc[i]["open_price"]
                  else BEAR_CANDLE for i in range(len(df))]
        ax_vol.bar(x_pos, df["volume"], color=colors, width=0.8, alpha=0.6)

        # Styling - extend x to fit triangle + annotations
        chart_right_edge = triangle_end_x + 12  # Room for labels
        ax_price.set_xlim(-1, chart_right_edge)
        ax_price.set_ylim(y_min, y_max)
        ax_price.grid(True, color=GRID, alpha=0.3, lw=0.5)
        ax_vol.grid(True, color=GRID, alpha=0.2, lw=0.5)

        # Price axis on right
        ax_price.yaxis.tick_right()
        ax_price.yaxis.set_label_position("right")
        ax_price.tick_params(axis='y', colors=TEXT_COLOR, labelsize=10)

        # Date axis at bottom
        n_ticks = 6
        tick_positions = np.linspace(0, len(df) - 1, n_ticks, dtype=int)
        tick_labels = [dates[i].strftime('%b %d') for i in tick_positions]
        ax_vol.set_xticks(tick_positions)
        ax_vol.set_xticklabels(tick_labels, fontsize=9, color=TEXT_COLOR)
        ax_vol.set_xlim(-1, chart_right_edge)

        ax_price.set_xticks([])
        ax_vol.set_yticks([])

        # Labels
        direction_emoji = "🐂" if is_bullish else "🐻"
        direction_text = "BULLISH" if is_bullish else "BEARISH"

        # Top-left: Timeframe and symbol
        ax_price.text(0.02, 0.98, f'{symbol} · 90D · {direction_emoji} {direction_text}',
                     transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                     color=TEXT_COLOR, va='top', ha='left')

        # Watermark
        ax_price.text(0.5, 0.5, 'BullsBears.xyz', transform=ax_price.transAxes,
                     fontsize=28, fontweight='bold', color=WATERMARK_COLOR,
                     alpha=0.06, ha='center', va='center', style='italic')

        # Bottom-right attribution
        ax_vol.text(0.99, 0.02, 'BullsBears.xyz · 3-30 day swing',
                   transform=ax_vol.transAxes, fontsize=8, color=TEXT_COLOR,
                   alpha=0.5, ha='right', va='bottom')

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", facecolor=BACKGROUND, edgecolor='none',
                   bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    async def _store_pretty_chart_url(self, pick_id: int, chart_url: str):
        """Store pretty chart URL in picks table"""
        async with self.db.acquire() as conn:
            # First check if pretty_chart_url column exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'picks' AND column_name = 'pretty_chart_url'
                )
            """)

            if not exists:
                await conn.execute("""
                    ALTER TABLE picks ADD COLUMN pretty_chart_url TEXT
                """)

            await conn.execute("""
                UPDATE picks SET pretty_chart_url = $1 WHERE id = $2
            """, chart_url, pick_id)


# Singleton
_pretty_generator = None


async def get_pretty_chart_generator() -> PrettyChartGenerator:
    global _pretty_generator
    if _pretty_generator is None:
        _pretty_generator = PrettyChartGenerator()
        await _pretty_generator.initialize()
    return _pretty_generator


async def generate_pretty_charts_for_picks() -> Dict:
    """Entry point to generate pretty charts for all current picks"""
    gen = await get_pretty_chart_generator()
    return await gen.generate_charts_for_picks()

