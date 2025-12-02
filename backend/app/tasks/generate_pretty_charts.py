#!/usr/bin/env python3
"""
Generate beautiful shareable charts for final picks with:
- 90-day candlestick history
- Target zones with gradient shading
- RSI(14) indicator with 30/70 bands
- Stop loss level
- Entry price marker ("IDENTIFIED AT")
- Bull/Bear icons from assets
- Gradient watermark

Runs right after arbitrator finalizes picks
"""

import asyncio
import logging
import io
import os
from datetime import date, datetime
from typing import Dict, Optional
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.dates import DateFormatter, AutoDateLocator
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
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
IDENTIFIED_COLOR = "#00FFFF"  # Cyan for identified price
RSI_COLOR = "#00FFFF"  # Cyan for RSI line
TEXT_COLOR = "#E8EAED"
# Gradient colors from logo
GRADIENT_START = "#77E4C8"  # Mint
GRADIENT_END = "#22C55E"  # Green

# Icon paths (relative to backend directory)
BULL_ICON_PATH = os.path.join(os.path.dirname(__file__), "../../../frontend/public/assets/bull-icon.png")
BEAR_ICON_PATH = os.path.join(os.path.dirname(__file__), "../../../assets/bear-icon.png")


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

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI(14) indicator"""
        delta = df["close_price"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _load_icon(self, is_bullish: bool) -> Optional[np.ndarray]:
        """Load and tint bull/bear icon with matching color"""
        try:
            icon_path = BULL_ICON_PATH if is_bullish else BEAR_ICON_PATH
            if os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA")
                img = img.resize((32, 32), Image.Resampling.LANCZOS)

                # Apply color tint (green for bull, red for bear)
                data = np.array(img)
                # Get RGB channels
                r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]

                if is_bullish:
                    # Tint green (#22C55E -> RGB: 34, 197, 94)
                    data[:,:,0] = np.clip(r * 0.13, 0, 255).astype(np.uint8)  # R
                    data[:,:,1] = np.clip(g * 0.77 + 50, 0, 255).astype(np.uint8)  # G
                    data[:,:,2] = np.clip(b * 0.37, 0, 255).astype(np.uint8)  # B
                else:
                    # Tint red (#EF4444 -> RGB: 239, 68, 68)
                    data[:,:,0] = np.clip(r * 0.94 + 50, 0, 255).astype(np.uint8)  # R
                    data[:,:,1] = np.clip(g * 0.27, 0, 255).astype(np.uint8)  # G
                    data[:,:,2] = np.clip(b * 0.27, 0, 255).astype(np.uint8)  # B

                return data
        except Exception as e:
            logger.warning(f"Could not load icon: {e}")
        return None

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
        """Render chart with gradient target zones, RSI, and bull/bear icons"""
        from matplotlib.gridspec import GridSpec

        is_bullish = direction == "bullish"
        target_color = BULL_TARGET_ZONE if is_bullish else BEAR_TARGET_ZONE
        stop_color = STOP_LOSS_BULL if is_bullish else STOP_LOSS_BEAR

        dates = df.index.tolist()
        x_pos = list(range(len(dates)))

        price_min = df["low_price"].min()
        price_max = df["high_price"].max()

        # Collect all price levels for dynamic scaling
        all_levels = [price_min, price_max]
        if target_low: all_levels.append(target_low)
        if target_high: all_levels.append(target_high)
        if moon_target: all_levels.append(moon_target)
        if stop_loss: all_levels.append(stop_loss)
        if entry_price: all_levels.append(entry_price)

        price_range = max(all_levels) - min(all_levels)
        y_min = min(all_levels) - price_range * 0.12
        y_max = max(all_levels) + price_range * 0.18

        # Calculate RSI
        rsi = self._calculate_rsi(df)

        # Create figure with 3 subplots: price, RSI, volume
        fig = plt.figure(figsize=(14, 10), dpi=150, facecolor=BACKGROUND)
        gs = GridSpec(3, 1, figure=fig, height_ratios=[5, 1.2, 0.8], hspace=0.08)

        ax_price = fig.add_subplot(gs[0])
        ax_rsi = fig.add_subplot(gs[1], sharex=ax_price)
        ax_vol = fig.add_subplot(gs[2], sharex=ax_price)

        for ax in [ax_price, ax_rsi, ax_vol]:
            ax.set_facecolor(BACKGROUND)

        # Calculate S/R levels
        sr_levels = self._calculate_support_resistance(df)

        # Draw S/R lines
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
        box_start_x = len(df) + 2
        box_end_x = len(df) + 28
        box_width = box_end_x - box_start_x
        label_x = box_end_x + 1

        # IDENTIFIED AT line (thick dashed cyan)
        if entry_price:
            ax_price.axhline(y=entry_price, color=IDENTIFIED_COLOR, linestyle='--', lw=3, alpha=0.9, zorder=5)
            ax_price.text(2, entry_price, f'IDENTIFIED AT ${entry_price:.2f}', color=IDENTIFIED_COLOR,
                         fontsize=9, fontweight='bold', va='bottom', ha='left', zorder=10,
                         bbox=dict(boxstyle='round,pad=0.3', facecolor=BACKGROUND, edgecolor=IDENTIFIED_COLOR, alpha=0.9, lw=1.5))

        # TARGET ZONE BOXES with gradient fill
        if target_low and target_high:
            # Create gradient colormap
            if is_bullish:
                colors_grad = [(0.13, 0.77, 0.37, 0.1), (0.13, 0.77, 0.37, 0.5)]  # Green gradient
            else:
                colors_grad = [(0.94, 0.27, 0.27, 0.1), (0.94, 0.27, 0.27, 0.5)]  # Red gradient

            # Target 1 box (thick gradient)
            t1_height = price_range * 0.06
            t1_box = Rectangle((box_start_x, target_low - t1_height/2), box_width, t1_height,
                               facecolor=target_color, edgecolor=target_color, alpha=0.4, lw=3, zorder=4)
            ax_price.add_patch(t1_box)
            ax_price.text(label_x, target_low, f'Target 1: ${target_low:.2f}',
                         color=target_color, fontsize=10, fontweight='bold', va='center', zorder=10)

            # Target 2 box (thick gradient)
            t2_height = price_range * 0.06
            t2_box = Rectangle((box_start_x, target_high - t2_height/2), box_width, t2_height,
                               facecolor=target_color, edgecolor=target_color, alpha=0.5, lw=3, zorder=4)
            ax_price.add_patch(t2_box)
            ax_price.text(label_x, target_high, f'Target 2: ${target_high:.2f}',
                         color=target_color, fontsize=10, fontweight='bold', va='center', zorder=10)

        # Moon target removed - rarely useful and causes overlap

        # STOP LOSS line and annotation
        if stop_loss:
            ax_price.axhline(y=stop_loss, color=stop_color, lw=2.5, ls='-', alpha=0.9, zorder=5)
            label_offset = price_range * 0.04
            label_y = stop_loss - label_offset if is_bullish else stop_loss + label_offset
            ax_price.text(label_x, label_y, f'Stop Loss: ${stop_loss:.2f}',
                         color=stop_color, fontsize=10, fontweight='bold', va='center', zorder=10)

        # RSI subplot
        ax_rsi.plot(x_pos, rsi.values, color=RSI_COLOR, lw=1.2, zorder=3)
        ax_rsi.axhline(y=70, color='#FF8080', linestyle='--', lw=1, alpha=0.6)
        ax_rsi.axhline(y=30, color='#77E4C8', linestyle='--', lw=1, alpha=0.6)
        ax_rsi.fill_between(x_pos, 30, 70, color=GRID, alpha=0.3)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_ylabel('RSI(14)', color=TEXT_COLOR, fontsize=9)
        ax_rsi.tick_params(axis='y', colors=TEXT_COLOR, labelsize=8)
        ax_rsi.yaxis.tick_right()
        ax_rsi.grid(True, color=GRID, alpha=0.3, lw=0.5)

        # Volume bars
        vol_colors = [BULL_CANDLE if df.iloc[i]["close_price"] >= df.iloc[i]["open_price"]
                      else BEAR_CANDLE for i in range(len(df))]
        ax_vol.bar(x_pos, df["volume"], color=vol_colors, width=0.8, alpha=0.6)
        ax_vol.set_ylabel('Vol', color=TEXT_COLOR, fontsize=9)

        # Styling
        chart_right_edge = label_x + 18
        ax_price.set_xlim(-1, chart_right_edge)
        ax_price.set_ylim(y_min, y_max)
        ax_price.grid(True, color=GRID, alpha=0.3, lw=0.5)
        ax_vol.grid(True, color=GRID, alpha=0.2, lw=0.5)

        ax_price.yaxis.tick_right()
        ax_price.tick_params(axis='y', colors=TEXT_COLOR, labelsize=10)

        # Date axis
        n_ticks = 6
        tick_positions = np.linspace(0, len(df) - 1, n_ticks, dtype=int)
        tick_labels = [dates[i].strftime('%b %d') for i in tick_positions]
        ax_vol.set_xticks(tick_positions)
        ax_vol.set_xticklabels(tick_labels, fontsize=9, color=TEXT_COLOR)
        ax_vol.set_xlim(-1, chart_right_edge)

        ax_price.set_xticks([])
        ax_rsi.set_xticks([])
        ax_vol.set_yticks([])

        # Header: symbol + direction with icon NEXT to text
        direction_text = "BULLISH" if is_bullish else "BEARISH"
        header_color = BULL_TARGET_ZONE if is_bullish else BEAR_TARGET_ZONE

        # First add the text
        ax_price.text(0.02, 0.96, f'{symbol} · 90D ·',
                     transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                     color=TEXT_COLOR, va='top', ha='left')

        # Try to load and place icon next to direction text
        icon_arr = self._load_icon(is_bullish)
        if icon_arr is not None:
            try:
                imagebox = OffsetImage(icon_arr, zoom=0.6)
                # Position icon right after "SYMBOL · 90D · " text
                ab = AnnotationBbox(imagebox, (0.22, 0.955), frameon=False,
                                   xycoords='axes fraction', box_alignment=(0.5, 0.5))
                ax_price.add_artist(ab)
                # Direction text after icon
                ax_price.text(0.26, 0.96, direction_text,
                             transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                             color=header_color, va='top', ha='left')
            except Exception as e:
                logger.warning(f"Icon placement failed: {e}")
                ax_price.text(0.22, 0.96, direction_text,
                             transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                             color=header_color, va='top', ha='left')
        else:
            ax_price.text(0.22, 0.96, direction_text,
                         transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                         color=header_color, va='top', ha='left')

        # Gradient watermark - DEAD CENTER of entire figure
        # Use figure coordinates for true center
        fig.text(0.45, 0.55, 'BullsBears.xyz',
                fontsize=36, fontweight='bold', color=GRADIENT_START,
                alpha=0.08, ha='center', va='center', style='italic')

        # Bottom attribution
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

