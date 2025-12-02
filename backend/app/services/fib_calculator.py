# backend/app/services/fib_calculator.py
"""
BullsBears v5 - Full Confluence Target System
100% deterministic mathematics | Zero LLM price output | Self-improving weekly

Confluence methods:
1. Fibonacci Extensions (primary driver)
2. Weekly + Daily Standard Pivot Points (R1/R2/S1/S2)
3. Gann 1×1 and 1×2 Angles (30-day time-price projection)
4. RSI Hidden / Regular Divergence detection (confirmation only)
"""

import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SwingPoint:
    """Represents a swing high or low with RSI value for divergence detection"""
    index: int
    price: float
    is_high: bool
    rsi: Optional[float] = None


@dataclass
class WeeklyPivots:
    """Standard pivot points from weekly OHLC"""
    pivot: float  # (H + L + C) / 3
    r1: float     # 2 * P - L
    r2: float     # P + (H - L)
    s1: float     # 2 * P - H
    s2: float     # P - (H - L)


@dataclass
class GannProjection:
    """Gann angle projection from swing point"""
    start_price: float
    start_index: int
    angle_1x1: float  # Price at 30 days (1:1 time/price)
    angle_1x2: float  # Price at 30 days (1:2 time/price, steeper)
    aligned: bool     # Price within ±2% of 1x1 line


@dataclass
class RSIDivergence:
    """RSI divergence detection result"""
    detected: bool
    divergence_type: Optional[str] = None  # 'regular_bullish', 'hidden_bullish', 'regular_bearish', 'hidden_bearish'
    price_swing_1: Optional[float] = None
    price_swing_2: Optional[float] = None
    rsi_swing_1: Optional[float] = None
    rsi_swing_2: Optional[float] = None


@dataclass
class ConfluenceTargets:
    """Full confluence-based price targets - PRODUCTION RETURN OBJECT"""
    direction: str  # 'bullish' or 'bearish'
    current_price: float
    swing_low: float
    swing_high: float

    # Targets
    primary_target: float   # Fib 1.0 extension (always shown)
    moonshot_target: Optional[float]  # Fib 1.618 extension (only when qualified)
    stop_loss: float

    # Confluence scoring (0-4)
    confluence_score: int
    confluence_methods: List[str]  # Which methods contributed

    # Technical data
    weekly_pivots: Optional[WeeklyPivots] = None
    gann: Optional[GannProjection] = None
    rsi_divergence: Optional[RSIDivergence] = None
    gann_alignment: bool = False

    # Validation
    valid: bool = True
    invalidation_reason: Optional[str] = None

    # ATR for moonshot qualification
    atr_pct: float = 0.0


# Legacy compatibility alias
FibTargets = ConfluenceTargets


def detect_swings(
    highs: List[float],
    lows: List[float],
    min_pct: float = 8.0,
    min_bars: int = 12
) -> List[SwingPoint]:
    """
    Detect swing highs and lows using ZigZag-style algorithm.

    Args:
        highs: List of high prices (oldest first)
        lows: List of low prices (oldest first)
        min_pct: Minimum percentage move to qualify as swing (default 8%)
        min_bars: Minimum bars between swings (default 12)

    Returns:
        List of SwingPoint objects
    """
    if len(highs) < min_bars * 2:
        return []

    swings = []
    last_swing_idx = 0
    last_swing_price = (highs[0] + lows[0]) / 2
    last_swing_is_high = True

    i = min_bars
    while i < len(highs):
        # Look for swing high
        window_high = max(highs[max(0, i - min_bars):i + 1])
        window_high_idx = highs[max(0, i - min_bars):i + 1].index(window_high) + max(0, i - min_bars)

        # Look for swing low
        window_low = min(lows[max(0, i - min_bars):i + 1])
        window_low_idx = lows[max(0, i - min_bars):i + 1].index(window_low) + max(0, i - min_bars)

        # Check if we have a valid swing from last point
        if last_swing_is_high:
            # Looking for swing low
            pct_move = (last_swing_price - window_low) / last_swing_price * 100
            if pct_move >= min_pct and (i - last_swing_idx) >= min_bars:
                swings.append(SwingPoint(window_low_idx, window_low, False))
                last_swing_idx = window_low_idx
                last_swing_price = window_low
                last_swing_is_high = False
        else:
            # Looking for swing high
            pct_move = (window_high - last_swing_price) / last_swing_price * 100
            if pct_move >= min_pct and (i - last_swing_idx) >= min_bars:
                swings.append(SwingPoint(window_high_idx, window_high, True))
                last_swing_idx = window_high_idx
                last_swing_price = window_high
                last_swing_is_high = True

        i += 1

    return swings


def get_last_completed_swing(
    highs: List[float],
    lows: List[float],
    min_pct: float = 8.0,
    min_bars: int = 12
) -> Tuple[Optional[float], Optional[float]]:
    """
    Get the most recent completed swing (low, high).
    A completed swing must have been retraced at least once.

    Returns:
        (swing_low, swing_high) or (None, None) if no valid swing
    """
    swings = detect_swings(highs, lows, min_pct, min_bars)

    if len(swings) < 2:
        # Fallback: use simple min/max of recent data
        lookback = min(30, len(highs))
        if lookback == 0:
            return None, None
        swing_low = min(lows[-lookback:])
        swing_high = max(highs[-lookback:])

        # Ensure minimum swing size (avoid divide by zero)
        if swing_low <= 0:
            return None, None
        swing_range_pct = (swing_high - swing_low) / swing_low * 100
        if swing_range_pct < min_pct:
            return None, None

        return swing_low, swing_high

    # Get last two swings to form completed swing
    # Find the most recent high and low from the swings
    recent_swings = swings[-4:] if len(swings) >= 4 else swings  # Last 4 swings max

    swing_highs = [s.price for s in recent_swings if s.is_high]
    swing_lows = [s.price for s in recent_swings if not s.is_high]

    if swing_highs and swing_lows:
        return min(swing_lows), max(swing_highs)

    # Fallback to simple min/max
    lookback = min(30, len(highs))
    return min(lows[-lookback:]), max(highs[-lookback:])


def fib_extension(swing_low: float, swing_high: float, level: float) -> float:
    """Calculate Fibonacci extension level from swing"""
    swing_range = swing_high - swing_low
    return swing_high + swing_range * level


def fib_retracement(start: float, end: float, level: float) -> float:
    """Calculate Fibonacci retracement level"""
    return end - (end - start) * level


# =============================================================================
# PIVOT POINT CALCULATIONS
# =============================================================================

def calculate_weekly_pivots(weekly_high: float, weekly_low: float, weekly_close: float) -> WeeklyPivots:
    """
    Calculate standard pivot points from weekly OHLC.
    Used for confluence scoring - if primary_target is within ±3% of any pivot level.
    """
    pivot = (weekly_high + weekly_low + weekly_close) / 3
    r1 = 2 * pivot - weekly_low
    r2 = pivot + (weekly_high - weekly_low)
    s1 = 2 * pivot - weekly_high
    s2 = pivot - (weekly_high - weekly_low)

    return WeeklyPivots(pivot=pivot, r1=r1, r2=r2, s1=s1, s2=s2)


def is_near_pivot(target: float, pivots: WeeklyPivots, threshold_pct: float = 3.0) -> bool:
    """Check if target is within threshold% of any weekly pivot level"""
    for level in [pivots.r1, pivots.r2, pivots.s1, pivots.s2]:
        if abs(target - level) / level * 100 <= threshold_pct:
            return True
    return False


# =============================================================================
# GANN ANGLE CALCULATIONS
# =============================================================================

def calculate_gann_projection(
    swing_price: float,
    swing_index: int,
    current_index: int,
    swing_range: float,
    direction: str,
    projection_days: int = 30
) -> Tuple[GannProjection, float]:
    """
    Calculate Gann 1×1 and 1×2 angle projections from swing point.

    True Gann 1×1 = 1 unit price per 1 unit time, scaled to actual swing.
    Example: $20 swing in 30 days → 1×1 = $0.666/day → +$20 in next 30 days

    Args:
        swing_price: Starting price (swing_low for bullish, swing_high for bearish)
        swing_index: Index of swing point in data
        current_index: Current bar index
        swing_range: Actual swing height in $ (swing_high - swing_low)
        direction: 'bullish' or 'bearish'
        projection_days: Days to project forward (default 30)

    Returns:
        Tuple of (GannProjection, current_1x1_price)
    """
    days_elapsed = max(1, current_index - swing_index)

    # Price per day based on actual swing geometry
    # 1×1 = full swing replicated in 30 days
    # 1×2 = twice as steep (full swing in 15 days, or 2x swing in 30 days)
    price_per_day_1x1 = swing_range / 30.0
    price_per_day_1x2 = price_per_day_1x1 * 2

    if direction == 'bullish':
        # Bullish: project upward from swing_low
        angle_1x1 = swing_price + price_per_day_1x1 * projection_days
        angle_1x2 = swing_price + price_per_day_1x2 * projection_days
        current_1x1 = swing_price + price_per_day_1x1 * days_elapsed
    else:
        # Bearish: project downward from swing_high
        angle_1x1 = swing_price - price_per_day_1x1 * projection_days
        angle_1x2 = swing_price - price_per_day_1x2 * projection_days
        current_1x1 = swing_price - price_per_day_1x1 * days_elapsed

    gann = GannProjection(
        start_price=swing_price,
        start_index=swing_index,
        angle_1x1=angle_1x1,
        angle_1x2=angle_1x2,
        aligned=False  # Will be set after checking current price
    )

    return gann, current_1x1


def check_gann_alignment(current_price: float, current_1x1: float, threshold_pct: float = 2.0) -> bool:
    """Check if current price is within threshold% of current Gann 1×1 line position"""
    if current_1x1 <= 0:
        return False
    return abs(current_price - current_1x1) / current_1x1 * 100 <= threshold_pct


# =============================================================================
# RSI DIVERGENCE DETECTION
# =============================================================================

def calculate_rsi(closes: List[float], period: int = 14) -> List[float]:
    """Calculate RSI for a list of closing prices"""
    if len(closes) < period + 1:
        return [50.0] * len(closes)  # Neutral fallback

    rsi_values = [50.0] * period  # Fill initial values with neutral

    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        gains.append(max(0, change))
        losses.append(max(0, -change))

    # Initial average
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        rsi_values.append(rsi)

    return rsi_values


def detect_rsi_divergence(
    swings: List[SwingPoint],
    closes: List[float],
    direction: str
) -> RSIDivergence:
    """
    Detect RSI divergence on last 3 swing points.

    Regular Bullish: price lower low + RSI higher low
    Hidden Bullish: price higher low + RSI lower low (continuation)
    Regular Bearish: price higher high + RSI lower high
    Hidden Bearish: price lower high + RSI higher high
    """
    if len(swings) < 2:
        return RSIDivergence(detected=False)

    rsi_values = calculate_rsi(closes)

    # Get last 3 swings of the appropriate type
    if direction == 'bullish':
        # Look for lows
        lows = [s for s in swings if not s.is_high][-3:]
        if len(lows) < 2:
            return RSIDivergence(detected=False)

        # Add RSI values to swings
        for swing in lows:
            if swing.index < len(rsi_values):
                swing.rsi = rsi_values[swing.index]

        sw1, sw2 = lows[-2], lows[-1]
        if sw1.rsi is None or sw2.rsi is None:
            return RSIDivergence(detected=False)

        # Regular Bullish: price LL, RSI HL
        if sw2.price < sw1.price and sw2.rsi > sw1.rsi:
            return RSIDivergence(
                detected=True,
                divergence_type='regular_bullish',
                price_swing_1=sw1.price, price_swing_2=sw2.price,
                rsi_swing_1=sw1.rsi, rsi_swing_2=sw2.rsi
            )

        # Hidden Bullish: price HL, RSI LL
        if sw2.price > sw1.price and sw2.rsi < sw1.rsi:
            return RSIDivergence(
                detected=True,
                divergence_type='hidden_bullish',
                price_swing_1=sw1.price, price_swing_2=sw2.price,
                rsi_swing_1=sw1.rsi, rsi_swing_2=sw2.rsi
            )

    else:  # bearish
        # Look for highs
        highs = [s for s in swings if s.is_high][-3:]
        if len(highs) < 2:
            return RSIDivergence(detected=False)

        for swing in highs:
            if swing.index < len(rsi_values):
                swing.rsi = rsi_values[swing.index]

        sw1, sw2 = highs[-2], highs[-1]
        if sw1.rsi is None or sw2.rsi is None:
            return RSIDivergence(detected=False)

        # Regular Bearish: price HH, RSI LH
        if sw2.price > sw1.price and sw2.rsi < sw1.rsi:
            return RSIDivergence(
                detected=True,
                divergence_type='regular_bearish',
                price_swing_1=sw1.price, price_swing_2=sw2.price,
                rsi_swing_1=sw1.rsi, rsi_swing_2=sw2.rsi
            )

        # Hidden Bearish: price LH, RSI HH
        if sw2.price < sw1.price and sw2.rsi > sw1.rsi:
            return RSIDivergence(
                detected=True,
                divergence_type='hidden_bearish',
                price_swing_1=sw1.price, price_swing_2=sw2.price,
                rsi_swing_1=sw1.rsi, rsi_swing_2=sw2.rsi
            )

    return RSIDivergence(detected=False)


# =============================================================================
# ATR CALCULATION
# =============================================================================

def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Calculate Average True Range (ATR)"""
    if len(highs) < period + 1:
        return sum(h - l for h, l in zip(highs[-period:], lows[-period:])) / min(len(highs), period)

    true_ranges = []
    for i in range(1, len(highs)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i-1])
        low_close = abs(lows[i] - closes[i-1])
        true_ranges.append(max(high_low, high_close, low_close))

    return sum(true_ranges[-period:]) / period if len(true_ranges) >= period else sum(true_ranges) / len(true_ranges)


# =============================================================================
# MOONSHOT QUALIFICATION
# =============================================================================

def should_show_moonshot(
    confluence_score: int,
    primary_pct: float,
    moonshot_pct: float,
    atr_pct: float,
    gann_aligned: bool
) -> bool:
    """
    Determine if moonshot target should be displayed.

    All conditions must be true:
    1. confluence_score >= 3
    2. primary_target move >= 12%
    3. moonshot_target move <= +45% (bull) or >= -50% (bear)
    4. Gann 1×1 angle is active and aligned
    5. ATR(14) <= 8% of price
    """
    return (
        confluence_score >= 3 and
        abs(primary_pct) >= 12.0 and
        abs(moonshot_pct) <= 50.0 and
        atr_pct <= 8.0 and
        gann_aligned
    )


# =============================================================================
# LEGACY FUNCTION - SIMPLIFIED (for backward compatibility)
# =============================================================================

def calculate_fib_targets(
    current_price: float,
    highs: List[float],
    lows: List[float],
    direction: str,
    min_pct: float = 8.0,
    min_bars: int = 12
) -> FibTargets:
    """
    Calculate Fibonacci-based price targets.

    Production rules:
    - Bullish: price must be above 0.618 retracement to activate extension targets
    - Bearish: price must be below 0.618 retracement to activate extension targets
    - Uses 1.0 and 1.618 extensions for bullish
    - Uses -0.618 and -1.0 extensions for bearish

    Args:
        current_price: Current stock price
        highs: List of high prices (oldest first)
        lows: List of low prices (oldest first)
        direction: 'bullish' or 'bearish'
        min_pct: Minimum swing percentage
        min_bars: Minimum bars between swings

    Returns:
        FibTargets with calculated levels
    """
    swing_low, swing_high = get_last_completed_swing(highs, lows, min_pct, min_bars)

    # Fallback if no valid swing detected
    if swing_low is None or swing_high is None:
        logger.warning(f"No valid swing detected, using percentage-based targets")
        return _create_default_targets(current_price, direction)

    swing_range = swing_high - swing_low
    fib_618_ret = fib_retracement(swing_low, swing_high, 0.618)

    if direction == 'bullish':
        is_valid = current_price > fib_618_ret
        primary_target = swing_high + swing_range * 1.0
        moonshot_raw = swing_high + swing_range * 1.618
        stop_loss = swing_low * 0.97
    else:
        is_valid = current_price < fib_618_ret
        ext_1 = 0.382 if current_price < 1.0 else 0.618
        ext_2 = 0.5 if current_price < 1.0 else 1.0
        primary_target = max(0.01, swing_low - swing_range * ext_1)
        moonshot_raw = max(0.01, swing_low - swing_range * ext_2)
        stop_loss = swing_high * 1.03

        # Validation for bearish
        if primary_target >= current_price:
            primary_target = current_price * 0.90
        if moonshot_raw >= primary_target:
            moonshot_raw = primary_target * 0.85

    return ConfluenceTargets(
        direction=direction,
        current_price=current_price,
        swing_low=swing_low,
        swing_high=swing_high,
        primary_target=primary_target,
        moonshot_target=None,  # No moonshot in legacy mode (no confluence calc)
        stop_loss=stop_loss,
        confluence_score=1 if is_valid else 0,
        confluence_methods=['fib'] if is_valid else [],
        valid=is_valid,
        invalidation_reason=None if is_valid else "Price outside 0.618 retracement"
    )


# =============================================================================
# MAIN CONFLUENCE TARGET FUNCTION (PRODUCTION USE)
# =============================================================================

async def calculate_confluence_targets(
    symbol: str,
    current_price: float,
    direction: str,
    db_pool,
    weekly_high: Optional[float] = None,
    weekly_low: Optional[float] = None,
    weekly_close: Optional[float] = None
) -> ConfluenceTargets:
    """
    BullsBears v5 - Full Confluence Target Calculation

    Calculates targets using 4-method confluence scoring:
    1. Fibonacci Extensions (1.0 = primary, 1.618 = moonshot)
    2. Weekly Pivot Points (R1/R2/S1/S2)
    3. Gann 1×1 Angles (30-day projection from swing)
    4. RSI Divergence (regular + hidden)

    Args:
        symbol: Stock ticker
        current_price: Current price
        direction: 'bullish' or 'bearish'
        db_pool: Database connection pool
        weekly_high/low/close: Optional weekly OHLC for pivots

    Returns:
        ConfluenceTargets with primary_target, moonshot_target (conditional),
        confluence_score (0-4), and all technical data for charting
    """
    async with db_pool.acquire() as conn:
        # Get 90 days of OHLC data
        rows = await conn.fetch("""
            SELECT date, high_price, low_price, close_price
            FROM prime_ohlc_90d
            WHERE symbol = $1
            ORDER BY date ASC
        """, symbol)

        if not rows or len(rows) < 20:
            logger.warning(f"Insufficient OHLC data for {symbol}, using defaults")
            return _create_default_targets(current_price, direction)

        highs = [float(r['high_price']) for r in rows]
        lows = [float(r['low_price']) for r in rows]
        closes = [float(r['close_price']) for r in rows]

        # =================================================================
        # STEP 1: Detect swings and calculate Fibonacci extensions
        # =================================================================
        swings = detect_swings(highs, lows, min_pct=8.0, min_bars=12)
        swing_low, swing_high = get_last_completed_swing(highs, lows, min_pct=8.0, min_bars=12)

        if swing_low is None or swing_high is None:
            return _create_default_targets(current_price, direction)

        swing_range = swing_high - swing_low
        fib_618_ret = fib_retracement(swing_low, swing_high, 0.618)

        # Calculate targets
        if direction == 'bullish':
            primary_target = swing_high + swing_range * 1.0     # Fib 1.0 extension
            moonshot_raw = swing_high + swing_range * 1.618     # Fib 1.618 extension
            stop_loss = swing_low * 0.97
            fib_valid = current_price > fib_618_ret
            swing_for_gann = swing_low
            swing_idx = next((s.index for s in swings if not s.is_high), 0)
        else:
            # Dynamic extensions for penny stocks
            ext_1 = 0.382 if current_price < 1.0 else 0.618
            ext_2 = 0.5 if current_price < 1.0 else 1.0
            primary_target = max(0.01, swing_low - swing_range * ext_1)
            moonshot_raw = max(0.01, swing_low - swing_range * ext_2)
            stop_loss = swing_high * 1.03
            fib_valid = current_price < fib_618_ret
            swing_for_gann = swing_high
            swing_idx = next((s.index for s in swings if s.is_high), 0)

        # =================================================================
        # STEP 2: Calculate weekly pivots
        # =================================================================
        weekly_pivots = None
        pivot_aligned = False

        if weekly_high and weekly_low and weekly_close:
            weekly_pivots = calculate_weekly_pivots(weekly_high, weekly_low, weekly_close)
            pivot_aligned = is_near_pivot(primary_target, weekly_pivots, threshold_pct=3.0)
        else:
            # Use last 5 days as pseudo-weekly
            if len(highs) >= 5:
                weekly_pivots = calculate_weekly_pivots(
                    max(highs[-5:]), min(lows[-5:]), closes[-1]
                )
                pivot_aligned = is_near_pivot(primary_target, weekly_pivots, threshold_pct=3.0)

        # =================================================================
        # STEP 3: Calculate Gann projection (using actual swing geometry)
        # =================================================================
        current_idx = len(closes) - 1
        gann, current_1x1 = calculate_gann_projection(
            swing_price=swing_for_gann,
            swing_index=swing_idx,
            current_index=current_idx,
            swing_range=swing_range,  # Actual $ height of swing
            direction=direction,
            projection_days=30
        )
        gann.aligned = check_gann_alignment(current_price, current_1x1, threshold_pct=2.0)

        # =================================================================
        # STEP 4: Detect RSI divergence
        # =================================================================
        rsi_divergence = detect_rsi_divergence(swings, closes, direction)

        # =================================================================
        # STEP 5: Calculate ATR for moonshot qualification
        # =================================================================
        atr = calculate_atr(highs, lows, closes, period=14)
        atr_pct = (atr / current_price * 100) if current_price > 0 else 0

        # =================================================================
        # STEP 6: Calculate confluence score (0-4)
        # =================================================================
        confluence_score = 0
        confluence_methods = []

        # +1 for valid Fib setup
        if fib_valid:
            confluence_score += 1
            confluence_methods.append('fib')

        # +1 for pivot alignment (within 3%)
        if pivot_aligned:
            confluence_score += 1
            confluence_methods.append('pivot')

        # +1 for Gann alignment (within 2%)
        if gann.aligned:
            confluence_score += 1
            confluence_methods.append('gann')

        # +1 for RSI divergence
        if rsi_divergence.detected:
            confluence_score += 1
            confluence_methods.append('rsi')

        # =================================================================
        # STEP 7: Determine moonshot display
        # =================================================================
        primary_pct = (primary_target - current_price) / current_price * 100
        moonshot_pct = (moonshot_raw - current_price) / current_price * 100

        show_moonshot = should_show_moonshot(
            confluence_score=confluence_score,
            primary_pct=primary_pct,
            moonshot_pct=moonshot_pct,
            atr_pct=atr_pct,
            gann_aligned=gann.aligned
        )

        moonshot_target = moonshot_raw if show_moonshot else None

        # =================================================================
        # STEP 8: Final validation
        # =================================================================
        # Ensure bearish targets are below current price
        if direction == 'bearish':
            if primary_target >= current_price:
                primary_target = current_price * 0.90
            if moonshot_target and moonshot_target >= primary_target:
                moonshot_target = primary_target * 0.85

        return ConfluenceTargets(
            direction=direction,
            current_price=current_price,
            swing_low=swing_low,
            swing_high=swing_high,
            primary_target=primary_target,
            moonshot_target=moonshot_target,
            stop_loss=stop_loss,
            confluence_score=confluence_score,
            confluence_methods=confluence_methods,
            weekly_pivots=weekly_pivots,
            gann=gann,
            rsi_divergence=rsi_divergence,
            gann_alignment=gann.aligned,
            valid=fib_valid,
            invalidation_reason=None if fib_valid else f"Price outside 0.618 retracement",
            atr_pct=atr_pct
        )


def _create_default_targets(current_price: float, direction: str) -> ConfluenceTargets:
    """Create default targets when insufficient data"""
    if direction == 'bullish':
        return ConfluenceTargets(
            direction=direction,
            current_price=current_price,
            swing_low=current_price * 0.9,
            swing_high=current_price,
            primary_target=current_price * 1.10,
            moonshot_target=None,  # No moonshot without confluence
            stop_loss=current_price * 0.92,
            confluence_score=0,
            confluence_methods=[],
            valid=True,
            invalidation_reason="No swing detected - using defaults"
        )
    else:
        return ConfluenceTargets(
            direction=direction,
            current_price=current_price,
            swing_low=current_price,
            swing_high=current_price * 1.1,
            primary_target=current_price * 0.90,
            moonshot_target=None,
            stop_loss=current_price * 1.08,
            confluence_score=0,
            confluence_methods=[],
            valid=True,
            invalidation_reason="No swing detected - using defaults"
        )


# Legacy async function alias for backward compatibility
async def get_fib_targets_for_symbol(
    symbol: str,
    current_price: float,
    direction: str,
    db_pool
) -> ConfluenceTargets:
    """
    Legacy function - now calls calculate_confluence_targets.
    Maintained for backward compatibility with existing code.
    """
    return await calculate_confluence_targets(
        symbol=symbol,
        current_price=current_price,
        direction=direction,
        db_pool=db_pool
    )

