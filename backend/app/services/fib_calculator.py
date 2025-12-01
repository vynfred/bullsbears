# backend/app/services/fib_calculator.py
"""
Fibonacci-based target calculator using swing detection.
Production-grade: zero subjectivity, based on actual OHLC data.
"""

import logging
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SwingPoint:
    """Represents a swing high or low"""
    index: int
    price: float
    is_high: bool


@dataclass
class FibTargets:
    """Fibonacci-based price targets"""
    direction: str  # 'bullish' or 'bearish'
    current_price: float
    swing_low: float
    swing_high: float
    target_1: float  # Primary target (1.0 ext for bull, -0.618 ext for bear)
    target_2: float  # Moonshot target (1.618 ext for bull, -1.0 ext for bear)
    stop_loss: float
    valid: bool  # Whether setup is valid (price above/below 0.618 retracement)
    invalidation_reason: Optional[str] = None


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
        swing_low = min(lows[-lookback:])
        swing_high = max(highs[-lookback:])

        # Ensure minimum swing size
        swing_range_pct = (swing_high - swing_low) / swing_low * 100
        if swing_range_pct < min_pct:
            return None, None

        return swing_low, swing_high

    # Get last two swings to form completed swing


def fib_extension(swing_low: float, swing_high: float, level: float) -> float:
    """Calculate Fibonacci extension level from swing"""
    swing_range = swing_high - swing_low
    return swing_high + swing_range * level


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
        if direction == 'bullish':
            return FibTargets(
                direction=direction,
                current_price=current_price,
                swing_low=current_price * 0.9,
                swing_high=current_price,
                target_1=current_price * 1.10,  # 10% upside
                target_2=current_price * 1.20,  # 20% upside
                stop_loss=current_price * 0.92,
                valid=True,
                invalidation_reason="No swing detected - using default 10-20% targets"
            )
        else:
            return FibTargets(
                direction=direction,
                current_price=current_price,
                swing_low=current_price,
                swing_high=current_price * 1.1,
                target_1=current_price * 0.90,  # 10% downside
                target_2=current_price * 0.80,  # 20% downside
                stop_loss=current_price * 1.08,
                valid=True,
                invalidation_reason="No swing detected - using default 10-20% targets"
            )

    swing_range = swing_high - swing_low
    fib_618_retracement = fib_retracement(swing_low, swing_high, 0.618)

    if direction == 'bullish':
        # Bullish: measure from swing_low to swing_high
        # Check if price is above 0.618 retracement (bullish structure)
        is_valid = current_price > fib_618_retracement

        # Extension targets from swing_high
        target_1 = swing_high + swing_range * 1.0    # 1.0 extension (~70-75% hit rate)
        target_2 = swing_high + swing_range * 1.618  # 1.618 extension (~40-50% hit rate)
        stop_loss = swing_low * 0.97  # Just below swing low

        return FibTargets(
            direction=direction,
            current_price=current_price,
            swing_low=swing_low,
            swing_high=swing_high,
            target_1=target_1,
            target_2=target_2,
            stop_loss=stop_loss,
            valid=is_valid,
            invalidation_reason=None if is_valid else f"Price ${current_price:.2f} below 0.618 retracement ${fib_618_retracement:.2f}"
        )

    else:  # bearish
        # Bearish: measure from swing_high to swing_low
        # Check if price is below 0.618 retracement (bearish structure)
        is_valid = current_price < fib_618_retracement

        # Extension targets below swing_low
        target_1 = swing_low - swing_range * 0.618  # -0.618 extension (primary, ~70-75% hit rate)
        target_2 = swing_low - swing_range * 1.0    # -1.0 extension (aggressive)
        stop_loss = swing_high * 1.03  # Just above swing high

        return FibTargets(
            direction=direction,
            current_price=current_price,
            swing_low=swing_low,
            swing_high=swing_high,
            target_1=target_1,
            target_2=target_2,
            stop_loss=stop_loss,
            valid=is_valid,
            invalidation_reason=None if is_valid else f"Price ${current_price:.2f} above 0.618 retracement ${fib_618_retracement:.2f}"
        )


async def get_fib_targets_for_symbol(
    symbol: str,
    current_price: float,
    direction: str,
    db_pool
) -> FibTargets:
    """
    Fetch OHLC data and calculate Fib targets for a symbol.

    Args:
        symbol: Stock ticker
        current_price: Current price
        direction: 'bullish' or 'bearish'
        db_pool: Database connection pool

    Returns:
        FibTargets with calculated levels
    """
    async with db_pool.acquire() as conn:
        # Get 90 days of OHLC data
        rows = await conn.fetch("""
            SELECT high, low
            FROM prime_ohlc_90d
            WHERE symbol = $1
            ORDER BY date ASC
        """, symbol)

        if not rows or len(rows) < 20:
            logger.warning(f"Insufficient OHLC data for {symbol}, using defaults")
            return calculate_fib_targets(
                current_price=current_price,
                highs=[current_price],
                lows=[current_price],
                direction=direction
            )

        highs = [float(r['high']) for r in rows]
        lows = [float(r['low']) for r in rows]

        return calculate_fib_targets(
            current_price=current_price,
            highs=highs,
            lows=lows,
            direction=direction,
            min_pct=8.0,
            min_bars=12
        )
    return end - (end - start) * level

