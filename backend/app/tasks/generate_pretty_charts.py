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
BULL_TEXT_COLOR = "#77E4C8"  # Mint green for bullish text
BEAR_TEXT_COLOR = "#FF8080"  # Red for bearish text
BULL_TARGET_ZONE = "#22C55E"  # Green for bullish targets
BEAR_TARGET_ZONE = "#EF4444"  # Red for bearish targets
STOP_LOSS_BULL = "#EF4444"  # Red stop for bullish
STOP_LOSS_BEAR = "#22C55E"  # Green stop for bearish
IDENTIFIED_COLOR = "#00FFFF"  # Cyan for identified price
RSI_COLOR = "#00FFFF"  # Cyan for RSI line
TEXT_COLOR = "#E8EAED"
SYMBOL_COLOR = "#FCF9EA"  # Cream color for symbol
# Gradient colors from logo
GRADIENT_START = "#77E4C8"  # Mint
GRADIENT_END = "#22C55E"  # Green

# Icon paths - use pre-colored icons from assets folder
BULL_ICON_PATH = os.path.join(os.path.dirname(__file__), "../../../assets/green-bull-icon.png")
BEAR_ICON_PATH = os.path.join(os.path.dirname(__file__), "../../../assets/red-bear-icon.png")


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
            # Get today's picks with confluence data
            picks = await conn.fetch("""
                SELECT p.id, p.symbol, p.direction, p.confidence,
                       p.target_low, p.target_high,
                       p.primary_target, p.moonshot_target,
                       p.confluence_score, p.confluence_methods,
                       p.rsi_divergence, p.gann_alignment,
                       p.weekly_pivots,
                       p.pick_context,
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

            # Get pick_context for confluence_analysis
            pick_context = pick["pick_context"]
            if isinstance(pick_context, str):
                import json
                try:
                    pick_context = json.loads(pick_context)
                except (json.JSONDecodeError, TypeError):
                    pick_context = {}
            elif pick_context is None:
                pick_context = {}

            # v5 Confluence data - directly from picks table
            primary_target = float(pick["primary_target"]) if pick["primary_target"] else None
            moonshot_target = float(pick["moonshot_target"]) if pick["moonshot_target"] else None
            confluence_score = int(pick["confluence_score"] or 0)
            confluence_methods = pick["confluence_methods"] or []
            rsi_divergence = bool(pick["rsi_divergence"])
            gann_alignment = bool(pick["gann_alignment"])

            # Parse weekly pivots
            weekly_pivots = pick["weekly_pivots"]
            if isinstance(weekly_pivots, str):
                try:
                    weekly_pivots = json.loads(weekly_pivots)
                except:
                    weekly_pivots = None

            # Get confluence_analysis from pick_context for stop_loss and swing data
            conf_analysis = pick_context.get("confluence_analysis", {})
            stop_loss = conf_analysis.get("stop_loss")
            swing_low = conf_analysis.get("swing_low")
            swing_high = conf_analysis.get("swing_high")

            # Fallback to old field names or estimates
            if primary_target is None:
                primary_target = float(pick["target_low"]) if pick["target_low"] else None
            if moonshot_target is None and pick["target_high"]:
                moonshot_target = float(pick["target_high"])

            if stop_loss is None:
                if direction == "bullish":
                    stop_loss = swing_low or (entry_price * 0.92 if entry_price else None)
                else:
                    stop_loss = swing_high or (entry_price * 1.08 if entry_price else None)

            # Fetch OHLC data
            df = await self._fetch_90d(symbol)
            if df is None or len(df) < 30:
                failed.append(symbol)
                logger.warning(f"Insufficient data for {symbol}")
                continue

            # Generate pretty chart with confluence data
            png_bytes = self._render_pretty_chart(
                df=df,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                primary_target=primary_target,
                moonshot_target=moonshot_target,
                stop_loss=stop_loss,
                confluence_score=confluence_score,
                confluence_methods=confluence_methods,
                weekly_pivots=weekly_pivots,
                rsi_divergence=rsi_divergence,
                gann_alignment=gann_alignment,
                swing_low=swing_low,
                swing_high=swing_high
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
        """Load pre-colored bull/bear icon from assets"""
        try:
            icon_path = BULL_ICON_PATH if is_bullish else BEAR_ICON_PATH
            logger.info(f"Loading icon from: {icon_path}")
            if os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA")
                img = img.resize((28, 28), Image.Resampling.LANCZOS)
                return np.array(img)
            else:
                logger.warning(f"Icon file not found: {icon_path}")
        except Exception as e:
            logger.warning(f"Could not load icon: {e}")
        return None

    def _render_pretty_chart(
        self,
        df: pd.DataFrame,
        symbol: str,
        direction: str,
        entry_price: Optional[float],
        primary_target: Optional[float],
        moonshot_target: Optional[float],  # None if confluence conditions not met
        stop_loss: Optional[float],
        confluence_score: int = 0,
        confluence_methods: list = None,
        weekly_pivots: dict = None,
        rsi_divergence: bool = False,
        gann_alignment: bool = False,
        swing_low: Optional[float] = None,
        swing_high: Optional[float] = None
    ) -> bytes:
        """
        Render chart with v5 confluence system elements:
        - Primary target (solid line, always shown)
        - Moonshot target (dashed line, only when confluence ≥3)
        - Weekly pivot lines (faint gray R1/R2/S1/S2)
        - Gann diagonal (if aligned)
        - RSI divergence indicator
        - Confluence X/4 badge
        """
        from matplotlib.gridspec import GridSpec

        if confluence_methods is None:
            confluence_methods = []

        is_bullish = direction == "bullish"
        target_color = BULL_TARGET_ZONE if is_bullish else BEAR_TARGET_ZONE
        stop_color = STOP_LOSS_BULL if is_bullish else STOP_LOSS_BEAR

        dates = df.index.tolist()
        x_pos = list(range(len(dates)))

        price_min = df["low_price"].min()
        price_max = df["high_price"].max()

        # Collect all price levels for dynamic scaling
        all_levels = [price_min, price_max]
        if primary_target: all_levels.append(primary_target)
        if moonshot_target: all_levels.append(moonshot_target)
        if stop_loss: all_levels.append(stop_loss)
        if entry_price: all_levels.append(entry_price)
        # Include pivot levels in scaling
        if weekly_pivots:
            for val in weekly_pivots.values():
                if val: all_levels.append(float(val))

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

        # ═══════════════════════════════════════════════════════════════════
        # v5 CONFLUENCE SYSTEM - Weekly Pivot Lines (faint gray)
        # ═══════════════════════════════════════════════════════════════════
        PIVOT_COLOR = '#4A5568'  # Faint gray
        if weekly_pivots:
            pivot_labels = {'r2': 'R2', 'r1': 'R1', 's1': 'S1', 's2': 'S2'}
            for key, label in pivot_labels.items():
                level = weekly_pivots.get(key)
                if level and float(level) > 0:
                    ax_price.axhline(y=float(level), color=PIVOT_COLOR, linestyle=':',
                                    lw=1, alpha=0.4, zorder=2)
                    ax_price.text(len(df) - 5, float(level), label,
                                 color=PIVOT_COLOR, fontsize=8, alpha=0.6, va='center')

        # ═══════════════════════════════════════════════════════════════════
        # v5 CONFLUENCE SYSTEM - Gann 1×1 Diagonal Line (orange)
        # ═══════════════════════════════════════════════════════════════════
        GANN_COLOR = '#FFA500'  # Orange
        if gann_alignment and (swing_low or swing_high):
            swing_price = swing_low if is_bullish else swing_high
            if swing_price and primary_target:
                # Draw Gann line from swing to 30-day projection
                gann_x = [len(df) - 30, len(df) + 30]  # From 30 days ago to 30 days future
                if is_bullish:
                    gann_y = [swing_price, primary_target * 1.1]  # Upward slope
                else:
                    gann_y = [swing_price, primary_target * 0.9]  # Downward slope
                ax_price.plot(gann_x, gann_y, color=GANN_COLOR, linestyle='-',
                             lw=2, alpha=0.7, zorder=3)
                ax_price.text(len(df) + 5, gann_y[1], 'Gann 1×1',
                             color=GANN_COLOR, fontsize=8, alpha=0.8, va='center')

        # ═══════════════════════════════════════════════════════════════════
        # v5 CONFLUENCE SYSTEM - RSI Divergence Indicator
        # ═══════════════════════════════════════════════════════════════════
        if rsi_divergence:
            div_color = '#22C55E' if is_bullish else '#EF4444'
            # Place divergence arrow near recent price action
            div_x = len(df) - 10
            div_y = df["close_price"].iloc[-10] if len(df) >= 10 else df["close_price"].iloc[-1]
            ax_price.annotate('', xy=(div_x + 3, div_y), xytext=(div_x, div_y),
                             arrowprops=dict(arrowstyle='->', color=div_color, lw=2))
            ax_price.text(div_x - 2, div_y, 'DIV', color=div_color, fontsize=8,
                         fontweight='bold', va='center', ha='right')

        # ═══════════════════════════════════════════════════════════════════
        # v5 CONFLUENCE SYSTEM - Target Lines (solid primary, dashed moonshot)
        # ═══════════════════════════════════════════════════════════════════
        valid_primary = primary_target if (primary_target and primary_target > 0.01) else None
        valid_moonshot = moonshot_target if (moonshot_target and moonshot_target > 0.01) else None

        if valid_primary:
            # Primary target - SOLID line with box (always shown)
            t1_height = price_range * 0.05
            t1_box = Rectangle((box_start_x, valid_primary - t1_height/2), box_width, t1_height,
                               facecolor=target_color, edgecolor=target_color, alpha=0.4, lw=3, zorder=4)
            ax_price.add_patch(t1_box)
            ax_price.axhline(y=valid_primary, color=target_color, lw=2.5, ls='-', alpha=0.8, zorder=5)
            ax_price.text(label_x, valid_primary, f'Primary: ${valid_primary:.2f}',
                         color=target_color, fontsize=10, fontweight='bold', va='center', zorder=10)

        if valid_moonshot:
            # Moonshot target - DASHED line (only when confluence ≥3)
            t2_height = price_range * 0.04
            t2_box = Rectangle((box_start_x, valid_moonshot - t2_height/2), box_width, t2_height,
                               facecolor=target_color, edgecolor=target_color, alpha=0.25, lw=2, zorder=4)
            ax_price.add_patch(t2_box)
            ax_price.axhline(y=valid_moonshot, color=target_color, lw=2, ls='--', alpha=0.7, zorder=5)
            ax_price.text(label_x, valid_moonshot, f'Moonshot: ${valid_moonshot:.2f}',
                         color=target_color, fontsize=9, fontweight='bold', va='center', alpha=0.8, zorder=10)

        # ═══════════════════════════════════════════════════════════════════
        # v5 CONFLUENCE SYSTEM - Confluence Badge (top-right)
        # ═══════════════════════════════════════════════════════════════════
        badge_color = '#77E4C8' if confluence_score >= 3 else '#FFA500' if confluence_score >= 2 else '#FF8080'
        badge_text = f'Confluence {confluence_score}/4'
        ax_price.text(0.98, 0.96, badge_text, transform=ax_price.transAxes,
                     fontsize=11, fontweight='bold', color=badge_color,
                     bbox=dict(boxstyle='round,pad=0.5', facecolor='#1E2A35',
                              edgecolor=badge_color, lw=2),
                     ha='right', va='top', zorder=15)

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

        # Header format: SYMBOL (cream) · 90D · [icon] BEARISH/BULLISH (colored)
        direction_text = "BULLISH" if is_bullish else "BEARISH"
        direction_color = BULL_TEXT_COLOR if is_bullish else BEAR_TEXT_COLOR

        # Symbol in cream color
        ax_price.text(0.02, 0.96, f'{symbol}',
                     transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                     color=SYMBOL_COLOR, va='top', ha='left')

        # " · 90D · " separator
        ax_price.text(0.08, 0.96, ' · 90D ·',
                     transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                     color=TEXT_COLOR, va='top', ha='left')

        # Try to load and place icon inline, then direction text
        icon_arr = self._load_icon(is_bullish)
        icon_x = 0.185  # Position after "90D ·"
        text_x = 0.215  # Position after icon

        if icon_arr is not None:
            try:
                imagebox = OffsetImage(icon_arr, zoom=0.8)
                # Position icon inline with text
                ab = AnnotationBbox(imagebox, (icon_x, 0.955), frameon=False,
                                   xycoords='axes fraction', box_alignment=(0.5, 0.5))
                ax_price.add_artist(ab)
                # Direction text right after icon
                ax_price.text(text_x, 0.96, direction_text,
                             transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                             color=direction_color, va='top', ha='left')
            except Exception as e:
                logger.warning(f"Icon placement failed: {e}")
                ax_price.text(icon_x, 0.96, direction_text,
                             transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                             color=direction_color, va='top', ha='left')
        else:
            ax_price.text(icon_x, 0.96, direction_text,
                         transform=ax_price.transAxes, fontsize=14, fontweight='bold',
                         color=direction_color, va='top', ha='left')

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

