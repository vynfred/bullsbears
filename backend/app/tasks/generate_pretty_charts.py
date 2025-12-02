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
        """Render beautiful annotated chart with S/R lines, target boxes, and buy zone"""
        import numpy as np

        is_bullish = direction == "bullish"
        target_color = BULL_TARGET_ZONE if is_bullish else BEAR_TARGET_ZONE
        stop_color = STOP_LOSS_BULL if is_bullish else STOP_LOSS_BEAR

        dates = df.index.tolist()
        x_pos = range(len(dates))

        price_min = df["low_price"].min()
        price_max = df["high_price"].max()

        # Collect all price levels for dynamic scaling
        all_levels = [price_min, price_max]
        if target_low: all_levels.append(target_low)
        if target_high: all_levels.append(target_high)
        if moon_target: all_levels.append(moon_target)
        if stop_loss: all_levels.append(stop_loss)
        if entry_price: all_levels.append(entry_price)

        # Dynamic Y scaling with extra padding for annotations
        price_range = max(all_levels) - min(all_levels)
        y_min = min(all_levels) - price_range * 0.1
        y_max = max(all_levels) + price_range * 0.15  # Extra top space for labels

        # Dynamic figure height based on price range
        base_height = 8
        fig, (ax_price, ax_vol) = plt.subplots(
            2, 1, figsize=(14, base_height), dpi=150,
            gridspec_kw={'height_ratios': [4, 1], 'hspace': 0.05},
            facecolor=BACKGROUND
        )

        ax_price.set_facecolor(BACKGROUND)
        ax_vol.set_facecolor(BACKGROUND)

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

        # Zone box positions
        entry_x = len(df) - 1
        box_start_x = len(df) + 2
        box_end_x = len(df) + 25
        box_width = box_end_x - box_start_x
        label_x = box_end_x + 1

        # Calculate buy zone (around entry price)
        if entry_price:
            buy_zone_height = entry_price * 0.03  # 3% range around entry
            buy_zone_low = entry_price - buy_zone_height
            buy_zone_high = entry_price + buy_zone_height

            # Draw BUY ZONE box
            buy_box = Rectangle(
                (box_start_x, buy_zone_low), box_width, buy_zone_high - buy_zone_low,
                facecolor=ENTRY_COLOR, edgecolor=ENTRY_COLOR, alpha=0.15, lw=2, zorder=4
            )
            ax_price.add_patch(buy_box)

            # Buy Zone label inside box
            ax_price.text(
                box_start_x + box_width / 2, entry_price, 'Buy Zone',
                color=ENTRY_COLOR, fontsize=10, fontweight='bold',
                ha='center', va='center', zorder=10
            )

            # Entry price annotation on right
            ax_price.text(label_x, entry_price, f'Entry: ${entry_price:.2f}',
                         color=ENTRY_COLOR, fontsize=9, fontweight='bold', va='center', zorder=10)

            # Entry marker on chart
            ax_price.scatter([entry_x], [entry_price], color=ENTRY_COLOR,
                            s=120, zorder=6, marker='o', edgecolors='white', linewidths=1.5)

        # Draw BREAKOUT LINE if we have targets (the line where price needs to break)
        if entry_price and (target_low or target_high):
            breakout_level = entry_price
            if is_bullish and sr_levels["resistance"]:
                # For bullish, breakout is nearest resistance above entry
                above_entry = [r for r in sr_levels["resistance"] if r > entry_price]
                if above_entry:
                    breakout_level = min(above_entry)
            elif not is_bullish and sr_levels["support"]:
                # For bearish, breakout is nearest support below entry
                below_entry = [s for s in sr_levels["support"] if s < entry_price]
                if below_entry:
                    breakout_level = max(below_entry)

            # Draw breakout line
            ax_price.axhline(y=breakout_level, color='#FFD700', linestyle='-', lw=1.5, alpha=0.8, zorder=5)
            ax_price.text(2, breakout_level, 'Breakout', color='#FFD700', fontsize=8,
                         fontweight='bold', va='bottom', ha='left', zorder=10,
                         bbox=dict(boxstyle='round,pad=0.2', facecolor=BACKGROUND, edgecolor='none', alpha=0.8))

        # TARGET ZONE BOXES
        if target_low and target_high:
            # Target 1 box (lower target)
            t1_box = Rectangle(
                (box_start_x, target_low - price_range * 0.02), box_width, price_range * 0.04,
                facecolor=target_color, edgecolor=target_color, alpha=0.2, lw=2, zorder=4
            )
            ax_price.add_patch(t1_box)
            ax_price.text(label_x, target_low, f'Target 1: ${target_low:.2f}',
                         color=target_color, fontsize=9, fontweight='bold', va='center', zorder=10)

            # Target 2 box (higher target)
            t2_box = Rectangle(
                (box_start_x, target_high - price_range * 0.02), box_width, price_range * 0.04,
                facecolor=target_color, edgecolor=target_color, alpha=0.25, lw=2, zorder=4
            )
            ax_price.add_patch(t2_box)
            ax_price.text(label_x, target_high, f'Target 2: ${target_high:.2f}',
                         color=target_color, fontsize=9, fontweight='bold', va='center', zorder=10)

        # MOON TARGET box
        if moon_target:
            moon_box = Rectangle(
                (box_start_x, moon_target - price_range * 0.015), box_width, price_range * 0.03,
                facecolor=target_color, edgecolor=target_color, alpha=0.1, lw=1.5, ls='--', zorder=4
            )
            ax_price.add_patch(moon_box)
            ax_price.text(label_x, moon_target, f'🌙 Moon: ${moon_target:.2f}',
                         color=target_color, fontsize=8, va='center', alpha=0.9, zorder=10)

        # STOP LOSS line and annotation
        if stop_loss:
            ax_price.axhline(y=stop_loss, color=stop_color, lw=2, ls='-', alpha=0.8, zorder=5)
            # Position label above or below line to avoid overlap
            label_offset = price_range * 0.03
            label_y = stop_loss - label_offset if is_bullish else stop_loss + label_offset
            ax_price.text(label_x, label_y, f'⛔ Stop: ${stop_loss:.2f}',
                         color=stop_color, fontsize=9, fontweight='bold', va='center', zorder=10)

        # Volume bars
        colors = [BULL_CANDLE if df.iloc[i]["close_price"] >= df.iloc[i]["open_price"]
                  else BEAR_CANDLE for i in range(len(df))]
        ax_vol.bar(x_pos, df["volume"], color=colors, width=0.8, alpha=0.6)

        # Styling
        chart_right_edge = label_x + 15
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

        # Header with bull/bear icon
        direction_icon = "🐂" if is_bullish else "🐻"
        direction_text = "BULLISH" if is_bullish else "BEARISH"
        icon_color = BULL_TARGET_ZONE if is_bullish else BEAR_TARGET_ZONE

        ax_price.text(0.02, 0.98, f'{symbol} · 90D · {direction_icon} {direction_text}',
                     transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                     color=TEXT_COLOR, va='top', ha='left')

        # Watermark
        ax_price.text(0.4, 0.5, 'BullsBears.xyz', transform=ax_price.transAxes,
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

