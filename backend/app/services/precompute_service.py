"""
Precompute Service - Smart fallback system for analysis requests.

Multi-tier analysis system:
1. Redis cache (5-30 minutes fresh)
2. Database precomputed (1+ hours fresh)  
3. Real-time API calls (rate limited to 5/day)
4. Stale data with warnings (always available)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from ..core.redis_client import redis_client
from ..core.config import settings
from ..models.precomputed_analysis import PrecomputedAnalysis
from ..models.stock import Stock
from ..analyzers.confidence import ConfidenceScorer
from ..tasks.precompute import trigger_update_single_stock

logger = logging.getLogger(__name__)


class PrecomputeService:
    """Service for managing precomputed analysis with smart fallbacks."""
    
    def __init__(self):
        self.confidence_scorer = ConfidenceScorer()
    
    async def get_analysis(
        self, 
        symbol: str, 
        db: Session,
        company_name: Optional[str] = None,
        use_precompute: bool = True,
        client_ip: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Get analysis with smart fallback system.
        
        Returns:
            Tuple of (analysis_result, data_source)
            data_source can be: 'redis_cache', 'database_precomputed', 'real_time', 'stale_data'
        """
        symbol = symbol.upper()
        
        if not use_precompute or not settings.precompute_enabled:
            # Fallback to real-time analysis
            return await self._get_realtime_analysis(symbol, db, company_name, client_ip)
        
        # Tier 1: Check Redis cache
        cache_result = await self._check_redis_cache(symbol)
        if cache_result:
            await redis_client.track_cache_hit("analysis", hit=True)
            return cache_result, "redis_cache"
        
        await redis_client.track_cache_hit("analysis", hit=False)
        
        # Tier 2: Check database precomputed
        db_result = await self._check_database_precomputed(symbol, db)
        if db_result:
            # Cache the result in Redis for faster future access
            await self._cache_database_result(symbol, db_result)
            return db_result, "database_precomputed"
        
        # Tier 3: Real-time API calls (rate limited)
        if await self._can_make_realtime_request(client_ip):
            try:
                realtime_result, source = await self._get_realtime_analysis(
                    symbol, db, company_name, client_ip
                )
                
                # Trigger background update for future requests
                if settings.precompute_enabled:
                    trigger_update_single_stock(symbol)
                
                return realtime_result, source
                
            except Exception as e:
                logger.error(f"Real-time analysis failed for {symbol}: {e}")
                # Fall through to stale data
        
        # Tier 4: Stale data with warnings
        stale_result = await self._get_stale_data(symbol, db)
        if stale_result:
            return stale_result, "stale_data"
        
        # Last resort: return error
        return {
            "error": "No analysis data available",
            "symbol": symbol,
            "message": "Unable to retrieve analysis data from any source",
            "suggestions": [
                "Try again in a few minutes",
                "Check if the symbol is valid",
                "Contact support if the issue persists"
            ]
        }, "error"
    
    async def _check_redis_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Check Redis cache for fresh analysis."""
        try:
            cache_key = f"precomputed_analysis:{symbol}"
            data, metadata = await redis_client.get_with_metadata(cache_key)
            
            if data and metadata:
                # Check if data is still fresh
                cached_at = datetime.fromisoformat(metadata.get("cached_at", ""))
                max_age = timedelta(seconds=settings.cache_precomputed_analysis)
                
                if datetime.now() - cached_at < max_age:
                    # Add cache metadata to response
                    data["cache_info"] = {
                        "source": "redis_cache",
                        "cached_at": metadata.get("cached_at"),
                        "expires_at": metadata.get("expires_at"),
                        "freshness_minutes": int((datetime.now() - cached_at).total_seconds() / 60)
                    }
                    return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking Redis cache for {symbol}: {e}")
            return None
    
    async def _check_database_precomputed(self, symbol: str, db: Session) -> Optional[Dict[str, Any]]:
        """Check database for precomputed analysis."""
        try:
            # Look for fresh analysis (within 2 hours)
            fresh_analysis = PrecomputedAnalysis.get_fresh_analysis(
                db, symbol, max_age_minutes=120
            )
            
            if fresh_analysis and not fresh_analysis.is_expired:
                result = fresh_analysis.complete_analysis.copy()
                result["cache_info"] = {
                    "source": "database_precomputed",
                    "computed_at": fresh_analysis.computed_at.isoformat(),
                    "expires_at": fresh_analysis.expires_at.isoformat(),
                    "freshness_minutes": fresh_analysis.freshness_minutes,
                    "confidence_score": fresh_analysis.confidence_score,
                    "api_calls_used": fresh_analysis.api_calls_used
                }
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking database precomputed for {symbol}: {e}")
            return None
    
    async def _cache_database_result(self, symbol: str, result: Dict[str, Any]):
        """Cache database result in Redis for faster access."""
        try:
            cache_key = f"precomputed_analysis:{symbol}"
            cache_info = result.get("cache_info", {})
            
            await redis_client.set_with_metadata(
                cache_key,
                result,
                settings.cache_precomputed_analysis,
                metadata={
                    "cached_at": datetime.now().isoformat(),
                    "source": "database_cached",
                    "original_computed_at": cache_info.get("computed_at"),
                    "expires_at": cache_info.get("expires_at")
                }
            )
            
        except Exception as e:
            logger.error(f"Error caching database result for {symbol}: {e}")
    
    async def _can_make_realtime_request(self, client_ip: Optional[str]) -> bool:
        """Check if client can make real-time requests (rate limiting)."""
        if not client_ip:
            return True  # Allow if no IP provided (internal requests)
        
        try:
            # Check daily rate limit
            today = datetime.now().strftime("%Y-%m-%d")
            rate_limit_key = f"realtime_requests:{client_ip}:{today}"
            
            current_count = await redis_client.get(rate_limit_key) or 0
            current_count = int(current_count)
            
            return current_count < settings.realtime_requests_per_day
            
        except Exception as e:
            logger.error(f"Error checking rate limit for {client_ip}: {e}")
            return True  # Allow on error
    
    async def _increment_realtime_counter(self, client_ip: Optional[str]):
        """Increment real-time request counter."""
        if not client_ip:
            return
        
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            rate_limit_key = f"realtime_requests:{client_ip}:{today}"
            
            # Increment counter with 24-hour expiry
            await redis_client.client.incr(rate_limit_key)
            await redis_client.client.expire(rate_limit_key, 86400)
            
        except Exception as e:
            logger.error(f"Error incrementing rate limit counter for {client_ip}: {e}")
    
    async def _get_realtime_analysis(
        self, 
        symbol: str, 
        db: Session, 
        company_name: Optional[str],
        client_ip: Optional[str]
    ) -> Tuple[Dict[str, Any], str]:
        """Get real-time analysis with rate limiting."""
        try:
            # Increment rate limit counter
            await self._increment_realtime_counter(client_ip)
            
            # Perform real-time analysis
            result = await self.confidence_scorer.analyze_stock(symbol, db, company_name)
            
            if "error" in result:
                return result, "real_time_error"
            
            # Add real-time metadata
            result["cache_info"] = {
                "source": "real_time",
                "computed_at": datetime.now().isoformat(),
                "freshness_minutes": 0,
                "api_calls_used": result.get("api_calls_used", 0)
            }
            
            return result, "real_time"
            
        except Exception as e:
            logger.error(f"Real-time analysis failed for {symbol}: {e}")
            return {
                "error": "Real-time analysis failed",
                "symbol": symbol,
                "message": str(e)
            }, "real_time_error"
    
    async def _get_stale_data(self, symbol: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get stale data as last resort."""
        try:
            # Get the most recent analysis, even if expired
            latest_analysis = PrecomputedAnalysis.get_latest_analysis(db, symbol)
            
            if latest_analysis:
                result = latest_analysis.complete_analysis.copy()
                
                # Add stale data warnings
                result["cache_info"] = {
                    "source": "stale_data",
                    "computed_at": latest_analysis.computed_at.isoformat(),
                    "expires_at": latest_analysis.expires_at.isoformat(),
                    "freshness_minutes": latest_analysis.freshness_minutes,
                    "is_stale": True,
                    "stale_warning": f"This data is {latest_analysis.freshness_minutes} minutes old"
                }
                
                result["warnings"] = result.get("warnings", [])
                result["warnings"].append({
                    "type": "stale_data",
                    "message": f"Analysis data is {latest_analysis.freshness_minutes} minutes old",
                    "recommendation": "Data may not reflect current market conditions"
                })
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting stale data for {symbol}: {e}")
            return None
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        try:
            analysis_stats = await redis_client.get_cache_stats("analysis")
            
            return {
                "cache_performance": analysis_stats,
                "precompute_enabled": settings.precompute_enabled,
                "rate_limits": {
                    "realtime_requests_per_day": settings.realtime_requests_per_day,
                    "api_calls_per_request": settings.realtime_api_calls_per_request
                },
                "cache_ttl_settings": {
                    "precomputed_analysis": settings.cache_precomputed_analysis,
                    "precomputed_technical": settings.cache_precomputed_technical,
                    "precomputed_sentiment": settings.cache_precomputed_sentiment
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}
    
    async def invalidate_symbol_cache(self, symbol: str) -> bool:
        """Manually invalidate cache for a symbol."""
        try:
            pattern = f"*{symbol}*"
            deleted_count = await redis_client.invalidate_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} cache entries for {symbol}")
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache for {symbol}: {e}")
            return False
