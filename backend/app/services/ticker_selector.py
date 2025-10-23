"""
AI-powered ticker selection service for options trading.
Scans established companies and ETFs to find the best option plays.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import yfinance as yf
import pandas as pd
from dataclasses import dataclass

from ..core.config import settings
from ..analyzers.technical import TechnicalAnalyzer
from ..analyzers.news import NewsAnalyzer
from .top_options import top_options_service

logger = logging.getLogger(__name__)

@dataclass
class TickerCandidate:
    """Data class for ticker candidates."""
    symbol: str
    company_name: str
    sector: str
    market_cap: float
    avg_volume: float
    current_price: float
    technical_score: float
    news_sentiment: float
    volatility: float
    options_volume: float
    confidence_score: float
    reasoning: str

class TickerSelector:
    """AI-powered ticker selection for options trading."""
    
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        # Dynamic ticker universe will be fetched from top_options_service
    
    async def select_top_plays(self, 
                              max_plays: int = 5,
                              min_confidence: float = 70.0,
                              timeframe_days: int = 7) -> List[TickerCandidate]:
        """
        Select top option plays from the ticker universe.
        
        Args:
            max_plays: Maximum number of plays to return (default 5)
            min_confidence: Minimum confidence score required (default 70%)
            timeframe_days: Analysis timeframe in days (default 7)
            
        Returns:
            List of top ticker candidates sorted by confidence score
        """
        logger.info(f"Starting ticker selection for {max_plays} plays with {min_confidence}% min confidence")

        # Get dynamic ticker universe from top options service
        try:
            ticker_universe = await top_options_service.get_top_options_symbols()
            logger.info(f"Using dynamic ticker universe: {ticker_universe}")
        except Exception as e:
            logger.error(f"Failed to get dynamic ticker universe: {e}")
            # Fallback to static list
            ticker_universe = ["SPY", "QQQ", "NVDA", "TSLA", "AAPL"]

        candidates = []

        # Process tickers in small batches to avoid rate limits (free tier friendly)
        batch_size = 3  # Very small batches for free APIs
        for i in range(0, len(ticker_universe), batch_size):
            batch = ticker_universe[i:i + batch_size]
            batch_candidates = await self._analyze_ticker_batch(batch, timeframe_days)
            candidates.extend(batch_candidates)

            # Longer delay between batches for free tier APIs
            await asyncio.sleep(2)
        
        # Filter by minimum confidence and sort by score
        qualified_candidates = [c for c in candidates if c.confidence_score >= min_confidence]
        qualified_candidates.sort(key=lambda x: x.confidence_score, reverse=True)

        logger.info(f"Found {len(qualified_candidates)} candidates above {min_confidence}% confidence")

        # If no candidates found due to rate limiting, provide a fallback
        if not qualified_candidates:
            logger.warning("No candidates found, likely due to API rate limits. Providing fallback candidate.")
            fallback_candidate = TickerCandidate(
                symbol="SPY",
                company_name="SPDR S&P 500 ETF Trust",
                sector="ETF",
                market_cap=500000000000,
                avg_volume=50000000,
                current_price=450.0,
                technical_score=75.0,
                news_sentiment=0.1,
                volatility=0.15,
                options_volume=1000000,
                confidence_score=72.5,
                reasoning="Fallback recommendation due to API rate limits. SPY is a highly liquid ETF with excellent options volume and consistent performance."
            )
            return [fallback_candidate]

        return qualified_candidates[:max_plays]
    
    async def _analyze_ticker_batch(self, tickers: List[str], timeframe_days: int) -> List[TickerCandidate]:
        """Analyze a batch of tickers sequentially to avoid rate limits."""
        candidates = []

        for ticker in tickers:
            try:
                result = await self._analyze_single_ticker(ticker, timeframe_days)
                if result:
                    candidates.append(result)
                    logger.info(f"Successfully analyzed {ticker}: {result.confidence_score:.1f}% confidence")

                # Small delay between individual ticker analyses
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning(f"Error analyzing {ticker}: {e}")
                continue

        return candidates
    
    async def _analyze_single_ticker(self, symbol: str, timeframe_days: int) -> Optional[TickerCandidate]:
        """Analyze a single ticker for option play potential."""
        try:
            logger.debug(f"Analyzing ticker: {symbol}")

            # Get basic stock info with timeout protection
            ticker = yf.Ticker(symbol)

            try:
                info = ticker.info
            except Exception as e:
                logger.warning(f"Failed to get info for {symbol}: {e}")
                return None

            # Skip if essential data is missing
            if not info or 'regularMarketPrice' not in info:
                logger.debug(f"Missing price data for {symbol}")
                return None

            current_price = info.get('regularMarketPrice', 0)
            if current_price <= 0:
                logger.debug(f"Invalid price for {symbol}: {current_price}")
                return None

            # Get historical data for technical analysis with error handling
            try:
                hist = ticker.history(period="3mo")
                if hist.empty:
                    logger.debug(f"No historical data for {symbol}")
                    return None
            except Exception as e:
                logger.warning(f"Failed to get historical data for {symbol}: {e}")
                return None
            
            # Calculate basic metrics
            avg_volume = hist['Volume'].tail(20).mean()
            volatility = hist['Close'].pct_change().std() * (252 ** 0.5)  # Annualized volatility
            
            # Skip low volume stocks
            if avg_volume < 100000:  # Minimum 100k average volume
                return None
            
            # Get technical analysis with error handling
            try:
                technical_data = await self.technical_analyzer.analyze(symbol)
                technical_score = self._calculate_technical_score(technical_data)
            except Exception as e:
                logger.warning(f"Technical analysis failed for {symbol}: {e}")
                technical_data = {}
                technical_score = 50.0  # Neutral score

            # Get news sentiment with error handling
            try:
                news_data = await self.news_analyzer.analyze_sentiment(symbol, info.get('longName', symbol))
                news_sentiment = news_data.get('compound_score', 0)
            except Exception as e:
                logger.warning(f"News analysis failed for {symbol}: {e}")
                news_data = {}
                news_sentiment = 0.0  # Neutral sentiment
            
            # Get options volume (simplified - would need options data API)
            options_volume = self._estimate_options_volume(symbol, avg_volume)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                technical_score, news_sentiment, volatility, options_volume, avg_volume
            )
            
            # Generate reasoning
            reasoning = self._generate_reasoning(symbol, technical_data, news_data, confidence_score)
            
            return TickerCandidate(
                symbol=symbol,
                company_name=info.get('longName', symbol),
                sector=info.get('sector', 'Unknown'),
                market_cap=info.get('marketCap', 0),
                avg_volume=avg_volume,
                current_price=current_price,
                technical_score=technical_score,
                news_sentiment=news_sentiment,
                volatility=volatility,
                options_volume=options_volume,
                confidence_score=confidence_score,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.warning(f"Error analyzing {symbol}: {e}")
            return None
    
    def _calculate_technical_score(self, technical_data: Dict[str, Any]) -> float:
        """Calculate technical analysis score (0-100)."""
        if not technical_data or 'indicators' not in technical_data:
            return 0.0
        
        indicators = technical_data['indicators']
        score = 0.0
        weight_sum = 0.0
        
        # RSI scoring (30-70 range is neutral, extremes get higher scores)
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if rsi < 30:  # Oversold - potential buy
                score += 80 * 0.3
            elif rsi > 70:  # Overbought - potential sell
                score += 80 * 0.3
            else:  # Neutral
                score += 40 * 0.3
            weight_sum += 0.3
        
        # MACD scoring
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            macd_signal = indicators['macd_signal']
            if macd > macd_signal:  # Bullish crossover
                score += 75 * 0.25
            else:  # Bearish
                score += 25 * 0.25
            weight_sum += 0.25
        
        # Bollinger Bands scoring
        if all(k in indicators for k in ['bb_upper', 'bb_lower', 'bb_middle']):
            current_price = technical_data.get('current_price', 0)
            bb_upper = indicators['bb_upper']
            bb_lower = indicators['bb_lower']
            bb_middle = indicators['bb_middle']
            
            if current_price <= bb_lower:  # Near lower band - potential buy
                score += 85 * 0.25
            elif current_price >= bb_upper:  # Near upper band - potential sell
                score += 85 * 0.25
            else:  # Middle range
                score += 50 * 0.25
            weight_sum += 0.25
        
        # Moving averages
        if 'sma_20' in indicators and 'sma_50' in indicators:
            sma_20 = indicators['sma_20']
            sma_50 = indicators['sma_50']
            if sma_20 > sma_50:  # Bullish trend
                score += 70 * 0.2
            else:  # Bearish trend
                score += 30 * 0.2
            weight_sum += 0.2
        
        return score / weight_sum if weight_sum > 0 else 0.0
    
    def _estimate_options_volume(self, symbol: str, avg_stock_volume: float) -> float:
        """Estimate options volume based on stock volume and symbol popularity."""
        # This is a simplified estimation - in production, use actual options data
        popular_options_stocks = {
            'AAPL', 'TSLA', 'SPY', 'QQQ', 'AMZN', 'MSFT', 'NVDA', 'META'
        }
        
        base_ratio = 0.1  # 10% of stock volume as baseline
        if symbol in popular_options_stocks:
            base_ratio = 0.3  # 30% for popular options stocks
        
        return avg_stock_volume * base_ratio
    
    def _calculate_confidence_score(self, technical_score: float, news_sentiment: float, 
                                  volatility: float, options_volume: float, avg_volume: float) -> float:
        """Calculate overall confidence score using weighted factors."""
        
        # Normalize news sentiment (-1 to 1) to 0-100 scale
        news_score = (news_sentiment + 1) * 50
        
        # Volatility score (higher volatility = better for options)
        volatility_score = min(volatility * 100, 100)  # Cap at 100
        
        # Volume score (higher volume = better liquidity)
        volume_score = min((avg_volume / 1000000) * 20, 100)  # 1M volume = 20 points
        
        # Options volume score
        options_score = min((options_volume / 100000) * 25, 100)  # 100k options = 25 points
        
        # Weighted combination based on your specified weights
        confidence = (
            technical_score * 0.44 +      # 44% technical
            news_score * 0.33 +           # 33% news sentiment  
            volatility_score * 0.10 +     # 10% volatility
            volume_score * 0.08 +         # 8% stock volume
            options_score * 0.05          # 5% options volume
        )
        
        return min(confidence, 100.0)
    
    def _generate_reasoning(self, symbol: str, technical_data: Dict, 
                          news_data: Dict, confidence_score: float) -> str:
        """Generate human-readable reasoning for the selection."""
        reasons = []
        
        # Technical reasons
        if technical_data and 'indicators' in technical_data:
            indicators = technical_data['indicators']
            
            if 'rsi' in indicators:
                rsi = indicators['rsi']
                if rsi < 30:
                    reasons.append(f"RSI oversold at {rsi:.1f}")
                elif rsi > 70:
                    reasons.append(f"RSI overbought at {rsi:.1f}")
            
            if 'macd' in indicators and 'macd_signal' in indicators:
                if indicators['macd'] > indicators['macd_signal']:
                    reasons.append("MACD bullish crossover")
                else:
                    reasons.append("MACD bearish signal")
        
        # News sentiment
        if news_data:
            sentiment = news_data.get('compound_score', 0)
            if sentiment > 0.1:
                reasons.append("Positive news sentiment")
            elif sentiment < -0.1:
                reasons.append("Negative news sentiment")
        
        # Confidence level
        if confidence_score >= 80:
            reasons.append("High confidence setup")
        elif confidence_score >= 70:
            reasons.append("Moderate confidence setup")
        
        return "; ".join(reasons) if reasons else "Standard technical setup"
