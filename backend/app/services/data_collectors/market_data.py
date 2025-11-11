"""
Market Data Collector for Agent System
Collects all market data needed for the daily scan pipeline
"""

import asyncio
import logging
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from ...core.database import get_database
from ...core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


async def get_market_data() -> Dict[str, Any]:
    """
    Collect all market data needed for agent analysis
    Returns structured data for the agent pipeline
    """
    try:
        logger.info("📊 Collecting market data for agent pipeline...")
        
        # Collect data in parallel
        tasks = [
            get_stock_universe(),
            get_market_conditions(),
            get_news_data(),
            get_earnings_data(),
            get_chart_data(),
            get_news_sentiment()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        stocks = results[0] if not isinstance(results[0], Exception) else []
        conditions = results[1] if not isinstance(results[1], Exception) else {}
        news = results[2] if not isinstance(results[2], Exception) else {}
        earnings = results[3] if not isinstance(results[3], Exception) else {}
        charts = results[4] if not isinstance(results[4], Exception) else []
        news_sentiment = results[5] if not isinstance(results[5], Exception) else {}
        
        logger.info(f"✅ Market data collected: {len(stocks)} stocks, {len(charts)} charts")
        
        return {
            'stocks': stocks,
            'conditions': conditions,
            'news': news,
            'earnings': earnings,
            'charts': charts,
            'news_sentiment': news_sentiment
        }
        
    except Exception as e:
        logger.error(f"Failed to collect market data: {str(e)}")
        return {
            'stocks': [],
            'conditions': {},
            'news': {},
            'earnings': {},
            'charts': [],
            'news_sentiment': {}
        }


async def get_stock_universe() -> List[Dict[str, Any]]:
    """Get the current stock universe with technical indicators"""
    try:
        # For now, use a curated list of volatile stocks
        # In production, this would query from your prices_15m table
        
        volatile_tickers = [
            'TSLA', 'NVDA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX',
            'AMD', 'INTC', 'CRM', 'ADBE', 'PYPL', 'SHOP', 'SQ', 'ROKU',
            'PLTR', 'SNOW', 'COIN', 'RBLX', 'U', 'DKNG', 'PENN', 'FUBO',
            'GME', 'AMC', 'BB', 'NOK', 'SNDL', 'TLRY', 'ACB', 'CGC',
            'SPCE', 'LCID', 'RIVN', 'F', 'NIO', 'XPEV', 'LI', 'BABA',
            'JD', 'PDD', 'BILI', 'IQ', 'VIPS', 'WB', 'DIDI', 'GRAB'
        ]
        
        stocks_data = []
        
        # Get basic data for each ticker
        for ticker in volatile_tickers:
            try:
                stock_data = await get_ticker_data(ticker)
                if stock_data:
                    stocks_data.append(stock_data)
            except Exception as e:
                logger.warning(f"Failed to get data for {ticker}: {str(e)}")
                continue
        
        logger.info(f"📈 Collected data for {len(stocks_data)} stocks")
        return stocks_data
        
    except Exception as e:
        logger.error(f"Failed to get stock universe: {str(e)}")
        return []


async def get_ticker_data(ticker: str) -> Optional[Dict[str, Any]]:
    """Get technical data for a single ticker"""
    try:
        # Use yfinance to get recent data
        stock = yf.Ticker(ticker)
        
        # Get 30 days of data for technical calculations
        hist = stock.history(period="30d", interval="1d")
        
        if hist.empty:
            return None
        
        # Calculate technical indicators
        current_price = float(hist['Close'].iloc[-1])
        volume_avg = float(hist['Volume'].rolling(10).mean().iloc[-1])
        current_volume = float(hist['Volume'].iloc[-1])
        
        # Calculate ATR (Average True Range)
        high_low = hist['High'] - hist['Low']
        high_close = np.abs(hist['High'] - hist['Close'].shift())
        low_close = np.abs(hist['Low'] - hist['Close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_10d = float(true_range.rolling(10).mean().iloc[-1])
        atr_percent = (atr_10d / current_price) * 100
        
        # Calculate gap from previous close
        prev_close = float(hist['Close'].iloc[-2])
        gap_percent = ((current_price - prev_close) / prev_close) * 100
        
        # Volume ratio
        volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1.0
        
        return {
            'ticker': ticker,
            'price': current_price,
            'volume': current_volume,
            'volume_avg': volume_avg,
            'volume_ratio': volume_ratio,
            'atr_10d': atr_percent,
            'gap_percent': gap_percent,
            'high_52w': float(hist['High'].max()),
            'low_52w': float(hist['Low'].min()),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.warning(f"Failed to get ticker data for {ticker}: {str(e)}")
        return None


async def get_market_conditions() -> Dict[str, Any]:
    """Get overall market conditions for kill-switch logic"""
    try:
        # Get SPY and VIX data
        spy = yf.Ticker("SPY")
        vix = yf.Ticker("^VIX")
        
        # Get recent data
        spy_hist = spy.history(period="2d", interval="1d")
        vix_hist = vix.history(period="1d", interval="1d")
        
        conditions = {
            'spy_premarket_change': 0.0,  # Would need real-time pre-market data
            'vix_current': 20.0,  # Default
            'market_open': True,
            'timestamp': datetime.now().isoformat()
        }
        
        # Calculate SPY change if data available
        if not spy_hist.empty and len(spy_hist) >= 2:
            current_spy = float(spy_hist['Close'].iloc[-1])
            prev_spy = float(spy_hist['Close'].iloc[-2])
            spy_change = ((current_spy - prev_spy) / prev_spy) * 100
            conditions['spy_change'] = spy_change
        
        # Get VIX level if data available
        if not vix_hist.empty:
            conditions['vix_current'] = float(vix_hist['Close'].iloc[-1])
        
        return conditions
        
    except Exception as e:
        logger.error(f"Failed to get market conditions: {str(e)}")
        return {
            'spy_premarket_change': 0.0,
            'vix_current': 20.0,
            'market_open': True,
            'timestamp': datetime.now().isoformat()
        }


async def get_news_data() -> Dict[str, Any]:
    """Get news data for fundamental analysis"""
    try:
        # Placeholder for news integration
        # Would integrate with Alpha Vantage, Finnhub, or NewsAPI
        
        return {
            'market_news': [],
            'earnings_news': [],
            'sector_news': {},
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get news data: {str(e)}")
        return {}


async def get_earnings_data() -> Dict[str, Any]:
    """Get earnings calendar data"""
    try:
        # Placeholder for earnings integration
        # Would integrate with Finnhub or Alpha Vantage
        
        return {
            'today': [],
            'this_week': [],
            'next_week': [],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get earnings data: {str(e)}")
        return {}


async def get_chart_data() -> List[Dict[str, Any]]:
    """Get chart images for vision analysis"""
    try:
        # Placeholder for chart generation
        # Would generate chart images for top candidates
        
        return []
        
    except Exception as e:
        logger.error(f"Failed to get chart data: {str(e)}")
        return []


async def get_news_sentiment() -> Dict[str, Any]:
    """Get news sentiment analysis"""
    try:
        # Placeholder for sentiment analysis
        # Would analyze news sentiment for stocks
        
        return {
            'overall_sentiment': 0.0,
            'stock_sentiment': {},
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get news sentiment: {str(e)}")
        return {}
