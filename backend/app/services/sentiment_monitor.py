"""
Sentiment Monitoring Service
Monitors social media, news, and market sentiment for watchlist stocks and triggers notifications.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..core.database import get_db
from ..models.watchlist import WatchlistEntry
from ..services.stock_data import StockDataService
from ..services.watchlist_notifications import watchlist_notification_service
from ..analyzers.news import NewsAnalyzer
from ..core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class SentimentMonitor:
    """Monitor sentiment changes for watchlist stocks"""
    
    def __init__(self):
        self.stock_data_service = StockDataService()
        self.news_analyzer = NewsAnalyzer()
        self.redis_client = get_redis_client()
        
        # Sentiment thresholds for notifications
        self.bullish_threshold = 75.0  # 75% confidence
        self.bearish_threshold = 75.0  # 75% confidence
        self.sentiment_change_threshold = 20.0  # 20% change in sentiment
        
    async def monitor_watchlist_sentiment(self, db: Session) -> Dict:
        """Monitor sentiment for all watchlist entries"""
        
        logger.info("🔍 Starting watchlist sentiment monitoring")
        
        results = {
            "stocks_monitored": 0,
            "sentiment_alerts": 0,
            "volume_alerts": 0,
            "momentum_alerts": 0,
            "errors": 0
        }
        
        # Get active watchlist entries
        active_entries = db.query(WatchlistEntry).filter(
            WatchlistEntry.status == 'ACTIVE'
        ).all()
        
        if not active_entries:
            logger.info("No active watchlist entries to monitor")
            return results
        
        # Monitor each entry
        for entry in active_entries:
            try:
                entry_results = await self._monitor_entry_sentiment(db, entry)
                
                results["stocks_monitored"] += 1
                results["sentiment_alerts"] += entry_results.get("sentiment_alerts", 0)
                results["volume_alerts"] += entry_results.get("volume_alerts", 0)
                results["momentum_alerts"] += entry_results.get("momentum_alerts", 0)
                
                # Small delay to respect API rate limits
                await asyncio.sleep(1)
                
            except Exception as e:
                results["errors"] += 1
                logger.error(f"Error monitoring sentiment for {entry.symbol}: {e}")
        
        logger.info(f"✅ Sentiment monitoring complete: {results}")
        return results
    
    async def _monitor_entry_sentiment(self, db: Session, entry: WatchlistEntry) -> Dict:
        """Monitor sentiment for a single watchlist entry"""
        
        results = {
            "sentiment_alerts": 0,
            "volume_alerts": 0,
            "momentum_alerts": 0
        }
        
        symbol = entry.symbol
        
        # Get current price
        current_price = await self.stock_data_service.get_current_price(symbol)
        if not current_price:
            return results
        
        # Get sentiment data
        sentiment_data = await self._get_comprehensive_sentiment(symbol)
        if not sentiment_data:
            return results
        
        # Check for sentiment alerts
        if await self._check_sentiment_alerts(entry, current_price, sentiment_data):
            results["sentiment_alerts"] += 1
        
        # Check for volume alerts
        if await self._check_volume_alerts(entry, current_price, sentiment_data):
            results["volume_alerts"] += 1
        
        # Check for momentum shifts
        if await self._check_momentum_shifts(entry, current_price, sentiment_data):
            results["momentum_alerts"] += 1
        
        return results
    
    async def _get_comprehensive_sentiment(self, symbol: str) -> Optional[Dict]:
        """Get comprehensive sentiment data from multiple sources"""
        
        try:
            # Get cached sentiment first
            cache_key = f"sentiment:{symbol}"
            cached_sentiment = await self.redis_client.get(cache_key)
            if cached_sentiment:
                return cached_sentiment
            
            sentiment_data = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "overall_sentiment": "neutral",
                "confidence": 50.0,
                "sources": {},
                "reasons": [],
                "volume_data": {},
                "momentum_indicators": {}
            }
            
            # Get news sentiment
            try:
                async with self.news_analyzer as analyzer:
                    news_sentiment = await analyzer.analyze(symbol)
                    if news_sentiment:
                        sentiment_data["sources"]["news"] = news_sentiment
                        sentiment_data["reasons"].extend(news_sentiment.get("analysis_summary", {}).get("key_points", []))
            except Exception as e:
                logger.error(f"Error getting news sentiment for {symbol}: {e}")

            # Social media sentiment - placeholder for future implementation
            # TODO: Implement social media sentiment analysis
            try:
                # For now, use a neutral social sentiment
                social_sentiment = {
                    "sentiment": "neutral",
                    "confidence": 50.0,
                    "sources": ["twitter", "reddit"],
                    "reasons": ["No social sentiment data available"]
                }
                sentiment_data["sources"]["social"] = social_sentiment
                sentiment_data["reasons"].extend(social_sentiment.get("reasons", []))
            except Exception as e:
                logger.error(f"Error getting social sentiment for {symbol}: {e}")
            
            # Get volume and momentum data
            try:
                market_data = await self.stock_data_service.get_real_time_quote(symbol)
                if market_data:
                    sentiment_data["volume_data"] = {
                        "current_volume": market_data.get("volume", 0),
                        "average_volume": market_data.get("average_volume", 0),
                        "volume_ratio": market_data.get("volume_ratio", 1.0)
                    }
                    
                    # Simple momentum indicators
                    sentiment_data["momentum_indicators"] = {
                        "price_change": market_data.get("change", 0),
                        "price_change_percent": market_data.get("change_percent", 0),
                        "trend": "bullish" if market_data.get("change", 0) > 0 else "bearish"
                    }
            except Exception as e:
                logger.error(f"Error getting market data for {symbol}: {e}")
            
            # Calculate overall sentiment
            sentiment_data = self._calculate_overall_sentiment(sentiment_data)
            
            # Cache for 5 minutes
            await self.redis_client.cache_with_ttl(cache_key, sentiment_data, 300)
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive sentiment for {symbol}: {e}")
            return None
    
    def _calculate_overall_sentiment(self, sentiment_data: Dict) -> Dict:
        """Calculate overall sentiment from multiple sources"""
        
        sources = sentiment_data.get("sources", {})
        total_weight = 0
        weighted_sentiment = 0
        
        # Weight different sources
        source_weights = {
            "news": 0.4,
            "social": 0.3,
            "technical": 0.3
        }
        
        for source, weight in source_weights.items():
            if source in sources:
                source_data = sources[source]
                sentiment_score = source_data.get("sentiment_score", 50)
                confidence = source_data.get("confidence", 50)
                
                # Weight by confidence
                effective_weight = weight * (confidence / 100)
                weighted_sentiment += sentiment_score * effective_weight
                total_weight += effective_weight
        
        if total_weight > 0:
            overall_score = weighted_sentiment / total_weight
            sentiment_data["confidence"] = min(total_weight * 100, 100)
        else:
            overall_score = 50
            sentiment_data["confidence"] = 25
        
        # Determine sentiment category
        if overall_score >= 65:
            sentiment_data["overall_sentiment"] = "bullish"
        elif overall_score <= 35:
            sentiment_data["overall_sentiment"] = "bearish"
        else:
            sentiment_data["overall_sentiment"] = "neutral"
        
        sentiment_data["overall_score"] = overall_score
        
        return sentiment_data
    
    async def _check_sentiment_alerts(self, entry: WatchlistEntry, current_price: float, 
                                    sentiment_data: Dict) -> bool:
        """Check if sentiment alerts should be triggered"""
        
        overall_sentiment = sentiment_data.get("overall_sentiment", "neutral")
        confidence = sentiment_data.get("confidence", 0)
        
        # Check for strong bullish sentiment
        if overall_sentiment == "bullish" and confidence >= self.bullish_threshold:
            # Check if we haven't sent this alert recently
            alert_key = f"sentiment_alert:{entry.symbol}:bullish"
            if not await self.redis_client.get(alert_key):
                await watchlist_notification_service.send_sentiment_alert(
                    entry.symbol, "bullish", confidence, current_price, entry.entry_price, 
                    {**sentiment_data, "entry_id": entry.id}
                )
                # Set cooldown (1 hour)
                await self.redis_client.cache_with_ttl(alert_key, True, 3600)
                return True
        
        # Check for strong bearish sentiment
        elif overall_sentiment == "bearish" and confidence >= self.bearish_threshold:
            alert_key = f"sentiment_alert:{entry.symbol}:bearish"
            if not await self.redis_client.get(alert_key):
                await watchlist_notification_service.send_sentiment_alert(
                    entry.symbol, "bearish", confidence, current_price, entry.entry_price,
                    {**sentiment_data, "entry_id": entry.id}
                )
                # Set cooldown (1 hour)
                await self.redis_client.cache_with_ttl(alert_key, True, 3600)
                return True
        
        return False
    
    async def _check_volume_alerts(self, entry: WatchlistEntry, current_price: float,
                                 sentiment_data: Dict) -> bool:
        """Check for unusual volume alerts"""
        
        volume_data = sentiment_data.get("volume_data", {})
        volume_ratio = volume_data.get("volume_ratio", 1.0)
        
        # Alert on volume spikes > 3x average
        if volume_ratio >= 3.0:
            alert_key = f"volume_alert:{entry.symbol}"
            if not await self.redis_client.get(alert_key):
                await watchlist_notification_service.send_volume_spike_alert(
                    entry.symbol,
                    volume_data.get("current_volume", 0),
                    volume_data.get("average_volume", 0),
                    volume_ratio,
                    current_price,
                    entry.entry_price
                )
                # Set cooldown (30 minutes)
                await self.redis_client.cache_with_ttl(alert_key, True, 1800)
                return True
        
        return False
    
    async def _check_momentum_shifts(self, entry: WatchlistEntry, current_price: float,
                                   sentiment_data: Dict) -> bool:
        """Check for momentum shifts"""
        
        momentum = sentiment_data.get("momentum_indicators", {})
        price_change_percent = momentum.get("price_change_percent", 0)
        
        # Alert on significant momentum shifts (>5% moves)
        if abs(price_change_percent) >= 5.0:
            shift_type = "bullish" if price_change_percent > 0 else "bearish"
            alert_key = f"momentum_alert:{entry.symbol}:{shift_type}"
            
            if not await self.redis_client.get(alert_key):
                await watchlist_notification_service.send_momentum_shift_alert(
                    entry.symbol, shift_type, current_price, entry.entry_price,
                    {**momentum, "entry_id": entry.id}
                )
                # Set cooldown (2 hours)
                await self.redis_client.cache_with_ttl(alert_key, True, 7200)
                return True
        
        return False


# Global instance
sentiment_monitor = SentimentMonitor()
