#!/usr/bin/env python3
"""
Stock Filter Service - NASDAQ ALL → ACTIVE Tier (Production Grade)
Filters ~3,800 NASDAQ stocks down to ~1,700 ACTIVE candidates with caching, monitoring, and resilience
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import redis.asyncio as redis
from ..core.database import get_asyncpg_pool
from ..core.config import settings
from ..core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class FilterCriteria(Enum):
    """Filter failure reasons for monitoring"""
    PRICE_TOO_LOW = "price_below_minimum"
    VOLUME_TOO_LOW = "volume_below_minimum" 
    MARKET_CAP_TOO_LOW = "market_cap_below_minimum"
    STALE_DATA = "data_too_old"
    MISSING_DATA = "missing_required_data"
    PENNY_STOCK = "penny_stock_excluded"

@dataclass
class FilterMetrics:
    """Filtering operation metrics"""
    total_stocks: int = 0
    active_stocks: int = 0
    filtered_out: Dict[str, int] = None
    processing_time_ms: int = 0
    cache_hit_rate: float = 0.0
    data_freshness_hours: float = 0.0
    
    def __post_init__(self):
        if self.filtered_out is None:
            self.filtered_out = {}

class StockFilterService:
    """
    Production-grade stock filtering service
    - Redis caching for performance
    - Comprehensive monitoring and metrics
    - Resilient error handling
    - Configurable filter criteria
    """
    
    def __init__(self):
        self.db = None
        self.redis = None
        self.initialized = False
        
        # Filter criteria from config
        self.min_price = settings.min_price
        self.min_volume = settings.min_volume
        self.min_market_cap = settings.min_market_cap
        self.max_data_age_hours = 24  # Reject stale data
        
        # Cache settings
        self.cache_key = "stock_filter:active_tier"
        self.cache_ttl = settings.cache_indicators  # 5 minutes
        self.metrics_key = "stock_filter:metrics"
        
        # Performance monitoring
        self.last_metrics: Optional[FilterMetrics] = None
    
    async def initialize(self):
        """Initialize database and Redis connections"""
        if not self.initialized:
            self.db = await get_asyncpg_pool()
            self.redis = await get_redis_client()
            self.initialized = True
            logger.info("StockFilterService initialized with caching and monitoring")
    
    async def get_active_stocks(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get ACTIVE tier stocks with intelligent caching
        Args:
            force_refresh: Skip cache and force database query
        Returns:
            List of ACTIVE tier stocks with metrics
        """
        if not self.initialized:
            await self.initialize()
        
        # Try cache first unless forced refresh
        if not force_refresh:
            cached_result = await self._get_cached_active_stocks()
            if cached_result:
                logger.info(f"✅ Cache hit: {len(cached_result)} ACTIVE stocks")
                return cached_result
        
        # Cache miss or forced refresh - filter from database
        return await self.filter_nasdaq_to_active()
    
    async def filter_nasdaq_to_active(self) -> List[Dict[str, Any]]:
        """
        Filter ALL NASDAQ stocks to ACTIVE tier with comprehensive monitoring
        """
        start_time = datetime.now()
        metrics = FilterMetrics()
        
        logger.info("🔍 Starting NASDAQ ALL → ACTIVE tier filtering")
        
        try:
            # Fetch all NASDAQ stocks with latest data
            all_stocks = await self._fetch_all_nasdaq_stocks()
            metrics.total_stocks = len(all_stocks)
            
            if not all_stocks:
                logger.warning("⚠️ No NASDAQ stocks found in database")
                return []
            
            # Apply filtering criteria with detailed tracking
            active_stocks = []
            filter_reasons = {reason.value: 0 for reason in FilterCriteria}
            
            for stock in all_stocks:
                filter_result = self._evaluate_stock_criteria(stock)
                
                if filter_result is None:
                    # Stock passes all criteria
                    active_stocks.append(self._format_active_stock(stock))
                else:
                    # Track why stock was filtered out
                    filter_reasons[filter_result.value] += 1
            
            metrics.active_stocks = len(active_stocks)
            metrics.filtered_out = filter_reasons
            metrics.processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Update database tier classifications
            await self._update_tier_classifications(active_stocks)
            
            # Cache results for performance
            await self._cache_active_stocks(active_stocks)
            
            # Store metrics for monitoring
            await self._store_metrics(metrics)
            self.last_metrics = metrics
            
            # Log comprehensive results
            self._log_filtering_results(metrics)
            
            return active_stocks
            
        except Exception as e:
            logger.error(f"❌ Critical error in stock filtering: {e}")
            # Try to return cached data as fallback
            cached_result = await self._get_cached_active_stocks()
            if cached_result:
                logger.warning("🔄 Returning cached ACTIVE stocks due to filtering error")
                return cached_result
            raise
    
    async def _fetch_all_nasdaq_stocks(self) -> List[Dict[str, Any]]:
        """Fetch all NASDAQ stocks with latest market data"""
        query = """
        SELECT 
            sc.symbol,
            sc.company_name,
            sc.sector,
            sc.industry,
            sc.price,
            sc.daily_volume,
            sc.market_cap,
            sc.updated_at as classification_updated,
            hd.close_price,
            hd.volume,
            hd.high_price,
            hd.low_price,
            hd.date as price_date,
            hd.updated_at as price_updated
        FROM stock_classifications sc
        LEFT JOIN historical_data hd ON sc.symbol = hd.symbol 
            AND hd.date = (
                SELECT MAX(date) 
                FROM historical_data hd2 
                WHERE hd2.symbol = sc.symbol
                AND hd2.date >= CURRENT_DATE - INTERVAL '7 days'
            )
        WHERE sc.exchange = 'NASDAQ'
        ORDER BY sc.market_cap DESC NULLS LAST
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query)
        
        return [dict(row) for row in rows]
    
    def _evaluate_stock_criteria(self, stock: Dict[str, Any]) -> Optional[FilterCriteria]:
        """
        Evaluate if stock meets ACTIVE tier criteria
        Returns None if passes, FilterCriteria enum if fails
        """
        # Get best available price data
        price = stock.get('price') or stock.get('close_price')
        volume = stock.get('daily_volume') or stock.get('volume')
        market_cap = stock.get('market_cap')
        
        # Check for missing critical data
        if not price or not volume or not market_cap:
            return FilterCriteria.MISSING_DATA
        
        # Check data freshness
        price_date = stock.get('price_date')
        if price_date:
            data_age = (datetime.now().date() - price_date).days
            if data_age > 1:  # More than 1 day old
                return FilterCriteria.STALE_DATA
        
        # Apply numerical filters
        if float(price) < self.min_price:
            return FilterCriteria.PRICE_TOO_LOW
            
        if int(volume) < self.min_volume:
            return FilterCriteria.VOLUME_TOO_LOW
            
        if int(market_cap) < self.min_market_cap:
            return FilterCriteria.MARKET_CAP_TOO_LOW
        
        # Additional quality filters
        if float(price) < 1.0:  # Penny stock exclusion
            return FilterCriteria.PENNY_STOCK
        
        return None  # Stock passes all criteria
    
    def _format_active_stock(self, stock: Dict[str, Any]) -> Dict[str, Any]:
        """Format stock data for ACTIVE tier"""
        return {
            'symbol': stock['symbol'],
            'company_name': stock.get('company_name'),
            'sector': stock.get('sector'),
            'industry': stock.get('industry'),
            'price': float(stock.get('price') or stock.get('close_price')),
            'volume': int(stock.get('daily_volume') or stock.get('volume')),
            'market_cap': int(stock.get('market_cap')),
            'high_price': float(stock.get('high_price') or 0),
            'low_price': float(stock.get('low_price') or 0),
            'last_updated': stock.get('price_updated') or stock.get('classification_updated'),
            'tier': 'ACTIVE',
            'filtered_at': datetime.now().isoformat()
        }
    
    async def _update_tier_classifications(self, active_stocks: List[Dict[str, Any]]):
        """Update database tier classifications efficiently"""
        try:
            active_symbols = [s['symbol'] for s in active_stocks]
            
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    # Reset all NASDAQ stocks to ALL tier
                    await conn.execute("""
                        UPDATE stock_classifications 
                        SET current_tier = 'ALL', updated_at = CURRENT_TIMESTAMP
                        WHERE exchange = 'NASDAQ' AND current_tier != 'ALL'
                    """)
                    
                    # Promote qualifying stocks to ACTIVE tier
                    if active_symbols:
                        await conn.executemany("""
                            UPDATE stock_classifications 
                            SET current_tier = 'ACTIVE', updated_at = CURRENT_TIMESTAMP
                            WHERE symbol = $1
                        """, [(symbol,) for symbol in active_symbols])
                
            logger.info(f"📊 Updated {len(active_symbols)} stocks to ACTIVE tier")
            
        except Exception as e:
            logger.error(f"❌ Failed to update tier classifications: {e}")
            raise
    
    async def _cache_active_stocks(self, active_stocks: List[Dict[str, Any]]):
        """Cache ACTIVE stocks for performance"""
        try:
            cache_data = {
                'stocks': active_stocks,
                'cached_at': datetime.now().isoformat(),
                'count': len(active_stocks)
            }
            
            await self.redis.setex(
                self.cache_key,
                self.cache_ttl,
                json.dumps(cache_data, default=str)
            )
            
            logger.debug(f"💾 Cached {len(active_stocks)} ACTIVE stocks for {self.cache_ttl}s")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache ACTIVE stocks: {e}")
    
    async def _get_cached_active_stocks(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached ACTIVE stocks"""
        try:
            cached_data = await self.redis.get(self.cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return data.get('stocks', [])
        except Exception as e:
            logger.warning(f"⚠️ Cache retrieval failed: {e}")
        
        return None
    
    async def _store_metrics(self, metrics: FilterMetrics):
        """Store filtering metrics for monitoring"""
        try:
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'total_stocks': metrics.total_stocks,
                'active_stocks': metrics.active_stocks,
                'filter_rate': round((metrics.total_stocks - metrics.active_stocks) / max(metrics.total_stocks, 1) * 100, 2),
                'processing_time_ms': metrics.processing_time_ms,
                'filtered_reasons': metrics.filtered_out
            }
            
            # Store latest metrics
            await self.redis.setex(
                self.metrics_key,
                3600,  # 1 hour
                json.dumps(metrics_data)
            )
            
            # Also store in time series for trending
            ts_key = f"{self.metrics_key}:history"
            await self.redis.lpush(ts_key, json.dumps(metrics_data))
            await self.redis.ltrim(ts_key, 0, 99)  # Keep last 100 entries
            await self.redis.expire(ts_key, 86400)  # 24 hours
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to store metrics: {e}")
    
    def _log_filtering_results(self, metrics: FilterMetrics):
        """Log comprehensive filtering results"""
        filter_rate = round((metrics.total_stocks - metrics.active_stocks) / max(metrics.total_stocks, 1) * 100, 1)
        
        logger.info(f"✅ NASDAQ Filtering Complete:")
        logger.info(f"   📊 Total: {metrics.total_stocks} → Active: {metrics.active_stocks} ({filter_rate}% filtered)")
        logger.info(f"   ⏱️  Processing: {metrics.processing_time_ms}ms")
        
        # Log top filter reasons
        if metrics.filtered_out:
            top_reasons = sorted(metrics.filtered_out.items(), key=lambda x: x[1], reverse=True)[:3]
            for reason, count in top_reasons:
                if count > 0:
                    logger.info(f"   🚫 {reason}: {count} stocks")
    
    async def get_filter_metrics(self) -> Optional[Dict[str, Any]]:
        """Get latest filtering metrics for monitoring"""
        try:
            cached_metrics = await self.redis.get(self.metrics_key)
            if cached_metrics:
                return json.loads(cached_metrics)
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve metrics: {e}")
        
        return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for monitoring systems"""
        try:
            if not self.initialized:
                await self.initialize()
            
            # Test database connection
            async with self.db.acquire() as conn:
                db_count = await conn.fetchval("SELECT COUNT(*) FROM stock_classifications WHERE exchange = 'NASDAQ'")
            
            # Test Redis connection
            await self.redis.ping()
            
            # Get cache status
            cached_data = await self.redis.get(self.cache_key)
            cache_status = "HIT" if cached_data else "MISS"
            
            return {
                'status': 'healthy',
                'database_stocks': db_count,
                'cache_status': cache_status,
                'last_metrics': self.last_metrics.__dict__ if self.last_metrics else None,
                'initialized': self.initialized
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'initialized': self.initialized
            }


# Singleton instance
_stock_filter_service = None

async def get_stock_filter_service() -> StockFilterService:
    """Get initialized StockFilterService instance"""
    global _stock_filter_service
    if _stock_filter_service is None:
        _stock_filter_service = StockFilterService()
        await _stock_filter_service.initialize()
    return _stock_filter_service