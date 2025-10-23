"""
Technical Analysis Engine - 35% weight in confidence scoring
Implements RSI, MACD, Bollinger Bands, SMA/EMA with buy/sell signals
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from ..core.redis_client import redis_client
from ..core.config import settings

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """
    Technical analysis engine using pandas and numpy for calculations.
    Provides RSI, MACD, Bollinger Bands, and moving averages.
    """
    
    def __init__(self):
        self.weight = 35.0  # 35% of total confidence score
    
    async def analyze(self, symbol: str, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform complete technical analysis.
        
        Args:
            symbol: Stock symbol
            historical_data: List of historical price data
            
        Returns:
            Technical analysis results with signals and scores
        """
        cache_key = f"technical:{symbol}"
        
        # Check cache (5 minute TTL)
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for technical analysis {symbol}")
            return cached_result
        
        try:
            # Convert to DataFrame
            df = self._prepare_dataframe(historical_data)
            
            if len(df) < 50:  # Need minimum data for reliable analysis
                logger.warning(f"Insufficient data for technical analysis: {len(df)} days")
                return self._create_neutral_result(symbol, "insufficient_data")
            
            # Calculate all indicators
            indicators = {}
            indicators.update(self._calculate_rsi(df))
            indicators.update(self._calculate_macd(df))
            indicators.update(self._calculate_bollinger_bands(df))
            indicators.update(self._calculate_moving_averages(df))
            indicators.update(self._calculate_volume_analysis(df))
            indicators.update(self._identify_support_resistance(df))
            
            # Generate signals and score
            signals = self._generate_signals(indicators, df)
            technical_score = self._calculate_technical_score(signals, indicators)
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "indicators": indicators,
                "signals": signals,
                "technical_score": technical_score,
                "weight": self.weight,
                "weighted_score": technical_score * (self.weight / 100),
                "recommendation": self._get_recommendation(technical_score),
                "confidence_level": self._get_confidence_level(technical_score),
                "analysis_summary": self._generate_summary(signals, indicators)
            }
            
            # Cache result
            await redis_client.cache_with_ttl(cache_key, result, settings.cache_indicators)
            
            return result
            
        except Exception as e:
            logger.error(f"Technical analysis failed for {symbol}: {e}")
            return self._create_neutral_result(symbol, f"error: {str(e)}")
    
    def _prepare_dataframe(self, historical_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert historical data to pandas DataFrame."""
        df = pd.DataFrame(historical_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df.set_index('date', inplace=True)
        
        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
        """Calculate RSI (Relative Strength Index)."""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50
        
        return {
            "rsi": {
                "value": float(current_rsi),
                "period": period,
                "signal": "oversold" if current_rsi < 30 else "overbought" if current_rsi > 70 else "neutral",
                "trend": "bullish" if current_rsi > 50 else "bearish"
            }
        }
    
    def _calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Any]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        ema_fast = df['close'].ewm(span=fast).mean()
        ema_slow = df['close'].ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        current_macd = macd_line.iloc[-1] if not macd_line.empty else 0
        current_signal = signal_line.iloc[-1] if not signal_line.empty else 0
        current_histogram = histogram.iloc[-1] if not histogram.empty else 0
        
        # Determine signal
        macd_signal = "neutral"
        if current_macd > current_signal and current_histogram > 0:
            macd_signal = "bullish"
        elif current_macd < current_signal and current_histogram < 0:
            macd_signal = "bearish"
        
        return {
            "macd": {
                "macd_line": float(current_macd),
                "signal_line": float(current_signal),
                "histogram": float(current_histogram),
                "signal": macd_signal,
                "crossover": current_macd > current_signal
            }
        }
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, Any]:
        """Calculate Bollinger Bands."""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        current_price = df['close'].iloc[-1]
        current_upper = upper_band.iloc[-1] if not upper_band.empty else current_price
        current_lower = lower_band.iloc[-1] if not lower_band.empty else current_price
        current_sma = sma.iloc[-1] if not sma.empty else current_price
        
        # Calculate position within bands
        band_width = current_upper - current_lower
        position = (current_price - current_lower) / band_width if band_width > 0 else 0.5
        
        # Determine signal
        bb_signal = "neutral"
        if position < 0.2:
            bb_signal = "oversold"
        elif position > 0.8:
            bb_signal = "overbought"
        
        return {
            "bollinger_bands": {
                "upper_band": float(current_upper),
                "middle_band": float(current_sma),
                "lower_band": float(current_lower),
                "current_price": float(current_price),
                "position": float(position),
                "signal": bb_signal,
                "squeeze": band_width < (current_sma * 0.1)  # Tight bands indicate low volatility
            }
        }
    
    def _calculate_moving_averages(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate SMA and EMA for multiple periods."""
        periods = [20, 50, 200]
        current_price = df['close'].iloc[-1]
        
        sma_data = {}
        ema_data = {}
        
        for period in periods:
            if len(df) >= period:
                sma = df['close'].rolling(window=period).mean().iloc[-1]
                ema = df['close'].ewm(span=period).mean().iloc[-1]
                
                sma_data[f"sma_{period}"] = {
                    "value": float(sma),
                    "signal": "bullish" if current_price > sma else "bearish",
                    "distance": float((current_price - sma) / sma * 100)
                }
                
                ema_data[f"ema_{period}"] = {
                    "value": float(ema),
                    "signal": "bullish" if current_price > ema else "bearish",
                    "distance": float((current_price - ema) / ema * 100)
                }
        
        # Golden Cross / Death Cross detection
        golden_cross = False
        death_cross = False
        
        if len(df) >= 200:
            sma_50 = df['close'].rolling(window=50).mean()
            sma_200 = df['close'].rolling(window=200).mean()
            
            if len(sma_50) >= 2 and len(sma_200) >= 2:
                # Check for recent crossover
                current_50_above_200 = sma_50.iloc[-1] > sma_200.iloc[-1]
                previous_50_above_200 = sma_50.iloc[-2] > sma_200.iloc[-2]
                
                if current_50_above_200 and not previous_50_above_200:
                    golden_cross = True
                elif not current_50_above_200 and previous_50_above_200:
                    death_cross = True
        
        return {
            "moving_averages": {
                "sma": sma_data,
                "ema": ema_data,
                "golden_cross": golden_cross,
                "death_cross": death_cross
            }
        }

    def _calculate_volume_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume patterns and unusual activity."""
        if 'volume' not in df.columns or df['volume'].isna().all():
            return {"volume_analysis": {"signal": "neutral", "unusual_activity": False}}

        # Calculate volume moving averages
        volume_sma_20 = df['volume'].rolling(window=20).mean()
        current_volume = df['volume'].iloc[-1]
        avg_volume = volume_sma_20.iloc[-1] if not volume_sma_20.empty else current_volume

        # Detect unusual volume (2x average)
        unusual_activity = current_volume > (avg_volume * 2) if avg_volume > 0 else False

        # Volume trend
        recent_volume_avg = df['volume'].tail(5).mean()
        older_volume_avg = df['volume'].tail(20).head(15).mean()

        volume_trend = "increasing" if recent_volume_avg > older_volume_avg else "decreasing"

        return {
            "volume_analysis": {
                "current_volume": int(current_volume),
                "average_volume": int(avg_volume),
                "volume_ratio": float(current_volume / avg_volume) if avg_volume > 0 else 1.0,
                "unusual_activity": unusual_activity,
                "trend": volume_trend,
                "signal": "bullish" if unusual_activity and volume_trend == "increasing" else "neutral"
            }
        }

    def _identify_support_resistance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Identify support and resistance levels."""
        if len(df) < 20:
            return {"support_resistance": {"support": None, "resistance": None}}

        # Use recent highs and lows
        recent_data = df.tail(50)

        # Find local maxima and minima
        highs = recent_data['high'].rolling(window=5, center=True).max()
        lows = recent_data['low'].rolling(window=5, center=True).min()

        # Identify resistance (recent highs)
        resistance_levels = []
        for i in range(2, len(recent_data) - 2):
            if recent_data['high'].iloc[i] == highs.iloc[i]:
                resistance_levels.append(recent_data['high'].iloc[i])

        # Identify support (recent lows)
        support_levels = []
        for i in range(2, len(recent_data) - 2):
            if recent_data['low'].iloc[i] == lows.iloc[i]:
                support_levels.append(recent_data['low'].iloc[i])

        current_price = df['close'].iloc[-1]

        # Find nearest levels
        resistance = None
        support = None

        if resistance_levels:
            resistance_above = [r for r in resistance_levels if r > current_price]
            resistance = min(resistance_above) if resistance_above else max(resistance_levels)

        if support_levels:
            support_below = [s for s in support_levels if s < current_price]
            support = max(support_below) if support_below else min(support_levels)

        return {
            "support_resistance": {
                "support": float(support) if support else None,
                "resistance": float(resistance) if resistance else None,
                "current_price": float(current_price),
                "distance_to_support": float((current_price - support) / current_price * 100) if support else None,
                "distance_to_resistance": float((resistance - current_price) / current_price * 100) if resistance else None
            }
        }

    def _generate_signals(self, indicators: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
        """Generate buy/sell signals based on indicators."""
        signals = {
            "overall_signal": "neutral",
            "strength": 0,
            "bullish_signals": [],
            "bearish_signals": [],
            "neutral_signals": []
        }

        # RSI signals
        rsi_signal = indicators["rsi"]["signal"]
        if rsi_signal == "oversold":
            signals["bullish_signals"].append("RSI oversold (potential reversal)")
        elif rsi_signal == "overbought":
            signals["bearish_signals"].append("RSI overbought (potential reversal)")
        else:
            signals["neutral_signals"].append("RSI neutral")

        # MACD signals
        macd_signal = indicators["macd"]["signal"]
        if macd_signal == "bullish":
            signals["bullish_signals"].append("MACD bullish crossover")
        elif macd_signal == "bearish":
            signals["bearish_signals"].append("MACD bearish crossover")
        else:
            signals["neutral_signals"].append("MACD neutral")

        # Bollinger Bands signals
        bb_signal = indicators["bollinger_bands"]["signal"]
        if bb_signal == "oversold":
            signals["bullish_signals"].append("Price near lower Bollinger Band")
        elif bb_signal == "overbought":
            signals["bearish_signals"].append("Price near upper Bollinger Band")

        # Moving average signals
        ma_data = indicators["moving_averages"]
        if ma_data["golden_cross"]:
            signals["bullish_signals"].append("Golden Cross (50 SMA above 200 SMA)")
        elif ma_data["death_cross"]:
            signals["bearish_signals"].append("Death Cross (50 SMA below 200 SMA)")

        # Volume signals
        volume_signal = indicators["volume_analysis"]["signal"]
        if volume_signal == "bullish":
            signals["bullish_signals"].append("Unusual volume activity")

        # Calculate overall signal strength
        bullish_count = len(signals["bullish_signals"])
        bearish_count = len(signals["bearish_signals"])

        if bullish_count > bearish_count:
            signals["overall_signal"] = "bullish"
            signals["strength"] = min(bullish_count * 20, 100)
        elif bearish_count > bullish_count:
            signals["overall_signal"] = "bearish"
            signals["strength"] = min(bearish_count * 20, 100)
        else:
            signals["overall_signal"] = "neutral"
            signals["strength"] = 0

        return signals

    def _calculate_technical_score(self, signals: Dict[str, Any], indicators: Dict[str, Any]) -> float:
        """Calculate technical analysis score (0-100)."""
        score = 50  # Start neutral

        # RSI contribution (20 points)
        rsi_value = indicators["rsi"]["value"]
        if 30 <= rsi_value <= 70:
            score += 10  # Neutral RSI is good
        elif rsi_value < 30:
            score += 15  # Oversold can be bullish
        elif rsi_value > 70:
            score -= 15  # Overbought can be bearish

        # MACD contribution (20 points)
        if indicators["macd"]["signal"] == "bullish":
            score += 15
        elif indicators["macd"]["signal"] == "bearish":
            score -= 15

        # Moving averages contribution (15 points)
        ma_data = indicators["moving_averages"]
        if ma_data["golden_cross"]:
            score += 15
        elif ma_data["death_cross"]:
            score -= 15

        # Volume contribution (10 points)
        if indicators["volume_analysis"]["unusual_activity"]:
            score += 10

        # Bollinger Bands contribution (10 points)
        bb_position = indicators["bollinger_bands"]["position"]
        if bb_position < 0.2:
            score += 8  # Near lower band
        elif bb_position > 0.8:
            score -= 8  # Near upper band

        return max(0, min(100, score))

    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on technical score."""
        if score >= 70:
            return "BUY"
        elif score >= 55:
            return "WEAK_BUY"
        elif score <= 30:
            return "SELL"
        elif score <= 45:
            return "WEAK_SELL"
        else:
            return "HOLD"

    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level based on score."""
        if score >= 80 or score <= 20:
            return "HIGH"
        elif score >= 65 or score <= 35:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_summary(self, signals: Dict[str, Any], indicators: Dict[str, Any]) -> str:
        """Generate human-readable analysis summary."""
        summary_parts = []

        # Overall signal
        overall = signals["overall_signal"]
        strength = signals["strength"]
        summary_parts.append(f"Technical analysis shows {overall} sentiment with {strength}% strength.")

        # Key indicators
        rsi_value = indicators["rsi"]["value"]
        summary_parts.append(f"RSI at {rsi_value:.1f} indicates {indicators['rsi']['signal']} conditions.")

        macd_signal = indicators["macd"]["signal"]
        summary_parts.append(f"MACD shows {macd_signal} momentum.")

        # Volume
        if indicators["volume_analysis"]["unusual_activity"]:
            summary_parts.append("Unusual volume activity detected.")

        return " ".join(summary_parts)

    def _create_neutral_result(self, symbol: str, reason: str) -> Dict[str, Any]:
        """Create neutral result when analysis fails."""
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "technical_score": 50.0,
            "weight": self.weight,
            "weighted_score": 50.0 * (self.weight / 100),
            "recommendation": "HOLD",
            "confidence_level": "LOW",
            "error": reason,
            "signals": {"overall_signal": "neutral", "strength": 0},
            "analysis_summary": f"Technical analysis unavailable: {reason}"
        }
