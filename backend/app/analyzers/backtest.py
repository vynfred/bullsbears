"""
Backtesting Engine for "When Moon?" and "When Rug?" Pattern Recognition
Analyzes historical data to identify patterns preceding +20% and -20% stock moves
"""

import asyncio
import logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from ..services.ai_consensus import AIConsensusEngine
from ..analyzers.technical import TechnicalAnalyzer
from ..analyzers.confidence import ConfidenceScorer
from ..core.redis_client import get_redis_client
from ..core.config import settings

logger = logging.getLogger(__name__)


class MoveType(Enum):
    MOON = "MOON"  # +20% move
    RUG = "RUG"    # -20% move


@dataclass
class BacktestResult:
    """Results from backtesting analysis"""
    symbol: str
    move_type: MoveType
    move_date: datetime
    move_magnitude: float  # Percentage move
    pre_signal_features: Dict[str, Any]
    ai_consensus_score: float
    pattern_confidence: float
    days_to_move: int


@dataclass
class PatternFeatures:
    """Features extracted before a significant move"""
    # Technical indicators
    rsi: float
    macd_signal: str
    volume_ratio: float  # Current volume / 20-day average
    bollinger_position: str
    moving_average_trend: str
    
    # Sentiment features
    news_sentiment: float
    social_sentiment: float
    
    # Market context
    vix_level: float
    sector_performance: float
    
    # Time-based features
    days_to_earnings: Optional[int]
    is_earnings_week: bool


class BacktestEngine:
    """
    Core backtesting engine for pattern recognition.
    Identifies historical patterns that preceded major stock moves.
    """
    
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.confidence_scorer = ConfidenceScorer()
        self.ai_consensus = AIConsensusEngine()
        self.redis_client = None
        
        # Backtesting parameters
        self.lookback_months = 3  # Analyze past 3 months
        self.move_threshold_moon = 20.0  # +20% for moon
        self.move_threshold_rug = -20.0  # -20% for rug
        self.max_days_to_move = 3  # Move must occur within 3 trading days
        self.pre_signal_days = 10  # Extract features from 10 days before move
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.redis_client = await get_redis_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.redis_client:
            await self.redis_client.close()

    async def backtest_moon(self, symbols: List[str] = None) -> List[BacktestResult]:
        """
        Backtest for "When Moon?" patterns - identify +20% jump patterns.
        
        Args:
            symbols: List of symbols to analyze (None for default set)
            
        Returns:
            List of BacktestResult objects for moon patterns
        """
        if symbols is None:
            symbols = self._get_default_symbols()
            
        logger.info(f"Starting moon backtesting for {len(symbols)} symbols")
        
        results = []
        for symbol in symbols:
            try:
                symbol_results = await self._analyze_symbol_for_moves(
                    symbol, MoveType.MOON
                )
                results.extend(symbol_results)
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error backtesting {symbol} for moon patterns: {e}")
                continue
                
        logger.info(f"Found {len(results)} moon patterns across {len(symbols)} symbols")
        return results

    async def backtest_rug(self, symbols: List[str] = None) -> List[BacktestResult]:
        """
        Backtest for "When Rug?" patterns - identify -20% drop patterns.
        
        Args:
            symbols: List of symbols to analyze (None for default set)
            
        Returns:
            List of BacktestResult objects for rug patterns
        """
        if symbols is None:
            symbols = self._get_default_symbols()
            
        logger.info(f"Starting rug backtesting for {len(symbols)} symbols")
        
        results = []
        for symbol in symbols:
            try:
                symbol_results = await self._analyze_symbol_for_moves(
                    symbol, MoveType.RUG
                )
                results.extend(symbol_results)
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error backtesting {symbol} for rug patterns: {e}")
                continue
                
        logger.info(f"Found {len(results)} rug patterns across {len(symbols)} symbols")
        return results

    async def _analyze_symbol_for_moves(self, symbol: str, move_type: MoveType) -> List[BacktestResult]:
        """Analyze a single symbol for significant moves"""
        try:
            # Get historical data
            historical_data = await self._get_historical_data(symbol)
            if historical_data is None or len(historical_data) < 30:
                logger.warning(f"Insufficient data for {symbol}")
                return []
            
            # Identify significant moves
            moves = self._identify_significant_moves(historical_data, move_type)
            if not moves:
                return []
                
            logger.info(f"Found {len(moves)} {move_type.value} moves for {symbol}")
            
            # Analyze each move
            results = []
            for move_date, move_magnitude, days_to_move in moves:
                try:
                    # Extract pre-signal features
                    features = await self._extract_pre_signal_features(
                        symbol, historical_data, move_date
                    )
                    
                    if features:
                        # Get AI consensus score for this pattern
                        ai_score = await self._get_ai_consensus_score(
                            symbol, features, move_type
                        )
                        
                        # Calculate pattern confidence
                        pattern_confidence = self._calculate_pattern_confidence(
                            features, move_type
                        )
                        
                        result = BacktestResult(
                            symbol=symbol,
                            move_type=move_type,
                            move_date=move_date,
                            move_magnitude=move_magnitude,
                            pre_signal_features=features.__dict__,
                            ai_consensus_score=ai_score,
                            pattern_confidence=pattern_confidence,
                            days_to_move=days_to_move
                        )
                        results.append(result)
                        
                except Exception as e:
                    logger.error(f"Error analyzing move for {symbol} on {move_date}: {e}")
                    continue
                    
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return []

    async def _get_historical_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get historical price data using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_months * 30)
            
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                logger.warning(f"No historical data for {symbol}")
                return None
                
            return hist
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def _identify_significant_moves(self, data: pd.DataFrame, move_type: MoveType) -> List[Tuple[datetime, float, int]]:
        """Identify dates with significant price moves"""
        moves = []
        
        for i in range(len(data) - self.max_days_to_move):
            base_price = data['Close'].iloc[i]
            
            # Check for moves within max_days_to_move
            for days_ahead in range(1, self.max_days_to_move + 1):
                if i + days_ahead >= len(data):
                    break
                    
                future_price = data['Close'].iloc[i + days_ahead]
                move_pct = ((future_price - base_price) / base_price) * 100
                
                # Check if move meets threshold
                if move_type == MoveType.MOON and move_pct >= self.move_threshold_moon:
                    move_date = data.index[i]
                    moves.append((move_date, move_pct, days_ahead))
                    break  # Found move, don't check further days
                    
                elif move_type == MoveType.RUG and move_pct <= self.move_threshold_rug:
                    move_date = data.index[i]
                    moves.append((move_date, move_pct, days_ahead))
                    break  # Found move, don't check further days
                    
        return moves

    def _get_default_symbols(self) -> List[str]:
        """Get default set of symbols for backtesting"""
        return [
            # Large cap tech
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA",
            # Meme stocks and volatile names
            "GME", "AMC", "PLTR", "COIN", "HOOD", "RIVN", "LCID",
            # ETFs for market context
            "SPY", "QQQ", "IWM", "VIX",
            # Other volatile stocks
            "NFLX", "ZOOM", "PELOTON", "ROKU", "SQ", "PYPL"
        ]

    async def _extract_pre_signal_features(self, symbol: str, data: pd.DataFrame,
                                         move_date: datetime) -> Optional[PatternFeatures]:
        """Extract features from the period before a significant move"""
        try:
            # Find the index of the move date
            move_idx = data.index.get_loc(move_date)

            # Need enough historical data for feature extraction
            if move_idx < self.pre_signal_days:
                return None

            # Extract data for the pre-signal period
            pre_signal_data = data.iloc[move_idx - self.pre_signal_days:move_idx]

            # Calculate technical indicators
            technical_features = await self._extract_technical_features(pre_signal_data)

            # Get sentiment features (simplified for backtesting)
            sentiment_features = await self._extract_sentiment_features(symbol, move_date)

            # Get market context features
            market_features = await self._extract_market_features(move_date)

            # Combine all features
            features = PatternFeatures(
                # Technical
                rsi=technical_features.get('rsi', 50.0),
                macd_signal=technical_features.get('macd_signal', 'neutral'),
                volume_ratio=technical_features.get('volume_ratio', 1.0),
                bollinger_position=technical_features.get('bollinger_position', 'middle'),
                moving_average_trend=technical_features.get('ma_trend', 'neutral'),

                # Sentiment (simplified for backtesting)
                news_sentiment=sentiment_features.get('news_sentiment', 0.0),
                social_sentiment=sentiment_features.get('social_sentiment', 0.0),

                # Market context
                vix_level=market_features.get('vix_level', 20.0),
                sector_performance=market_features.get('sector_performance', 0.0),

                # Time-based
                days_to_earnings=market_features.get('days_to_earnings'),
                is_earnings_week=market_features.get('is_earnings_week', False)
            )

            return features

        except Exception as e:
            logger.error(f"Error extracting features for {symbol}: {e}")
            return None

    async def _extract_technical_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Extract technical indicator features"""
        try:
            # Use the existing technical analyzer
            # Get the last row of data for current values
            latest_data = data.iloc[-1]

            # Calculate RSI
            rsi = self._calculate_rsi(data['Close'])

            # Calculate MACD
            macd_signal = self._calculate_macd_signal(data['Close'])

            # Calculate volume ratio
            volume_ratio = data['Volume'].iloc[-1] / data['Volume'].mean()

            # Calculate Bollinger Bands position
            bollinger_position = self._calculate_bollinger_position(data['Close'])

            # Calculate moving average trend
            ma_trend = self._calculate_ma_trend(data['Close'])

            return {
                'rsi': rsi,
                'macd_signal': macd_signal,
                'volume_ratio': volume_ratio,
                'bollinger_position': bollinger_position,
                'ma_trend': ma_trend
            }

        except Exception as e:
            logger.error(f"Error calculating technical features: {e}")
            return {}

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
        except:
            return 50.0

    def _calculate_macd_signal(self, prices: pd.Series) -> str:
        """Calculate MACD signal"""
        try:
            ema12 = prices.ewm(span=12).mean()
            ema26 = prices.ewm(span=26).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9).mean()

            if macd.iloc[-1] > signal.iloc[-1]:
                return 'bullish'
            elif macd.iloc[-1] < signal.iloc[-1]:
                return 'bearish'
            else:
                return 'neutral'
        except:
            return 'neutral'

    def _calculate_bollinger_position(self, prices: pd.Series, period: int = 20) -> str:
        """Calculate position relative to Bollinger Bands"""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)

            current_price = prices.iloc[-1]
            current_sma = sma.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]

            if current_price > current_upper:
                return 'above_upper'
            elif current_price < current_lower:
                return 'below_lower'
            elif current_price > current_sma:
                return 'upper_half'
            else:
                return 'lower_half'
        except:
            return 'middle'

    def _calculate_ma_trend(self, prices: pd.Series) -> str:
        """Calculate moving average trend"""
        try:
            sma20 = prices.rolling(window=20).mean()
            sma50 = prices.rolling(window=50).mean()

            if len(sma20) < 2 or len(sma50) < 2:
                return 'neutral'

            # Check if short MA is above long MA and trending up
            if sma20.iloc[-1] > sma50.iloc[-1] and sma20.iloc[-1] > sma20.iloc[-2]:
                return 'bullish'
            elif sma20.iloc[-1] < sma50.iloc[-1] and sma20.iloc[-1] < sma20.iloc[-2]:
                return 'bearish'
            else:
                return 'neutral'
        except:
            return 'neutral'

    async def _extract_sentiment_features(self, symbol: str, move_date: datetime) -> Dict[str, Any]:
        """Extract sentiment features (simplified for backtesting)"""
        try:
            # For backtesting, we'll use simplified sentiment analysis
            # In a full implementation, this would analyze historical news and social media

            # Generate synthetic sentiment based on symbol characteristics
            # This is a placeholder - real implementation would use historical sentiment data
            base_sentiment = 0.0

            # Adjust based on symbol type
            if symbol in ['TSLA', 'GME', 'AMC', 'COIN']:
                # High volatility stocks tend to have more extreme sentiment
                base_sentiment = np.random.normal(0, 0.3)
            else:
                # More stable stocks have moderate sentiment
                base_sentiment = np.random.normal(0, 0.1)

            return {
                'news_sentiment': np.clip(base_sentiment, -1.0, 1.0),
                'social_sentiment': np.clip(base_sentiment + np.random.normal(0, 0.1), -1.0, 1.0)
            }

        except Exception as e:
            logger.error(f"Error extracting sentiment features: {e}")
            return {'news_sentiment': 0.0, 'social_sentiment': 0.0}

    async def _extract_market_features(self, move_date: datetime) -> Dict[str, Any]:
        """Extract market context features"""
        try:
            # For backtesting, use simplified market features
            # In production, this would fetch actual VIX, sector data, earnings calendar

            # Simulate VIX level (typically 10-40)
            vix_level = np.random.uniform(12, 35)

            # Simulate sector performance
            sector_performance = np.random.normal(0, 0.02)  # +/- 2% typical

            # Simulate earnings proximity (simplified)
            days_to_earnings = np.random.choice([None, 1, 2, 3, 7, 14], p=[0.7, 0.05, 0.05, 0.05, 0.1, 0.05])
            is_earnings_week = days_to_earnings is not None and days_to_earnings <= 7

            return {
                'vix_level': vix_level,
                'sector_performance': sector_performance,
                'days_to_earnings': days_to_earnings,
                'is_earnings_week': is_earnings_week
            }

        except Exception as e:
            logger.error(f"Error extracting market features: {e}")
            return {
                'vix_level': 20.0,
                'sector_performance': 0.0,
                'days_to_earnings': None,
                'is_earnings_week': False
            }

    async def _get_ai_consensus_score(self, symbol: str, features: PatternFeatures,
                                    move_type: MoveType) -> float:
        """Get AI consensus score for the pattern (simplified for backtesting)"""
        try:
            # For backtesting, we'll simulate AI consensus scores
            # In production, this would use the actual Grok + DeepSeek system

            # Create a mock analysis data structure
            mock_data = {
                'technical': {
                    'rsi': features.rsi,
                    'macd_signal': features.macd_signal,
                    'volume_ratio': features.volume_ratio,
                    'bollinger_position': features.bollinger_position
                },
                'sentiment': {
                    'news_sentiment': features.news_sentiment,
                    'social_sentiment': features.social_sentiment
                },
                'market': {
                    'vix_level': features.vix_level,
                    'sector_performance': features.sector_performance
                }
            }

            # Calculate a synthetic consensus score based on features
            score = 0.5  # Start neutral

            # Technical contribution
            if move_type == MoveType.MOON:
                if features.rsi < 30:  # Oversold
                    score += 0.15
                if features.macd_signal == 'bullish':
                    score += 0.1
                if features.volume_ratio > 1.5:  # High volume
                    score += 0.1
            else:  # RUG
                if features.rsi > 70:  # Overbought
                    score += 0.15
                if features.macd_signal == 'bearish':
                    score += 0.1
                if features.volume_ratio > 1.5:  # High volume
                    score += 0.1

            # Sentiment contribution
            if move_type == MoveType.MOON and features.social_sentiment > 0.2:
                score += 0.1
            elif move_type == MoveType.RUG and features.social_sentiment < -0.2:
                score += 0.1

            # Add some randomness to simulate AI uncertainty
            score += np.random.normal(0, 0.05)

            return np.clip(score, 0.0, 1.0)

        except Exception as e:
            logger.error(f"Error calculating AI consensus score: {e}")
            return 0.5

    def _calculate_pattern_confidence(self, features: PatternFeatures, move_type: MoveType) -> float:
        """Calculate pattern confidence based on feature alignment"""
        try:
            confidence = 0.5  # Start neutral

            # Technical alignment
            if move_type == MoveType.MOON:
                # Bullish technical signals
                if features.rsi < 35:  # Oversold
                    confidence += 0.1
                if features.macd_signal == 'bullish':
                    confidence += 0.1
                if features.volume_ratio > 1.3:
                    confidence += 0.1
                if features.bollinger_position in ['below_lower', 'lower_half']:
                    confidence += 0.05
                if features.moving_average_trend == 'bullish':
                    confidence += 0.1
            else:  # RUG
                # Bearish technical signals
                if features.rsi > 65:  # Overbought
                    confidence += 0.1
                if features.macd_signal == 'bearish':
                    confidence += 0.1
                if features.volume_ratio > 1.3:
                    confidence += 0.1
                if features.bollinger_position in ['above_upper', 'upper_half']:
                    confidence += 0.05
                if features.moving_average_trend == 'bearish':
                    confidence += 0.1

            # Sentiment alignment
            if move_type == MoveType.MOON and features.social_sentiment > 0.1:
                confidence += 0.05
            elif move_type == MoveType.RUG and features.social_sentiment < -0.1:
                confidence += 0.05

            # Market context
            if features.vix_level > 25:  # High volatility environment
                confidence += 0.05

            return np.clip(confidence, 0.0, 1.0)

        except Exception as e:
            logger.error(f"Error calculating pattern confidence: {e}")
            return 0.5


# Utility functions for easy usage
async def backtest_moon_patterns(symbols: List[str] = None) -> List[BacktestResult]:
    """Convenience function to backtest moon patterns"""
    async with BacktestEngine() as engine:
        return await engine.backtest_moon(symbols)


async def backtest_rug_patterns(symbols: List[str] = None) -> List[BacktestResult]:
    """Convenience function to backtest rug patterns"""
    async with BacktestEngine() as engine:
        return await engine.backtest_rug(symbols)
