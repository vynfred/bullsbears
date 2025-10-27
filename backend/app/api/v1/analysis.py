"""
Analysis API endpoints for stock analysis and recommendations
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ...core.database import get_db
from ...core.config import settings
from ...analyzers.confidence import ConfidenceScorer
from ...services.stock_data import StockDataService
from ...services.precompute_service import PrecomputeService
from ...models.stock import Stock
from ...models.analysis_results import AnalysisResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.get("/analyze/{symbol}")
async def analyze_stock(
    symbol: str,
    request: Request,
    company_name: Optional[str] = Query(None, description="Company name for better news search"),
    use_precompute: bool = Query(True, description="Use precomputed analysis when available"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Perform complete stock analysis with confidence scoring and smart fallback system.

    Returns comprehensive analysis including:
    - Technical analysis (RSI, MACD, Bollinger Bands, etc.)
    - News sentiment analysis
    - Social media sentiment
    - Risk assessment
    - Position sizing recommendations
    - Final buy/sell recommendation with confidence level

    Data Sources (in priority order):
    1. Redis cache (5-30 minutes fresh)
    2. Database precomputed (1+ hours fresh)
    3. Real-time API calls (rate limited to 5/day)
    4. Stale data with warnings (always available)
    """
    try:
        symbol = symbol.upper().strip()

        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol format")

        # Get client IP for rate limiting
        client_ip = request.client.host if request.client else None

        # Use precompute service for smart fallback
        precompute_service = PrecomputeService()
        result, data_source = await precompute_service.get_analysis(
            symbol=symbol,
            db=db,
            company_name=company_name,
            use_precompute=use_precompute and settings.precompute_enabled,
            client_ip=client_ip
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Add response metadata
        response_data = {
            "success": True,
            "data": result,
            "metadata": {
                "symbol": symbol,
                "data_source": data_source,
                "precompute_enabled": settings.precompute_enabled,
                "timestamp": datetime.now().isoformat()
            },
            "disclaimer": "This analysis is for educational purposes only. Not financial advice."
        }

        # Add rate limiting info for real-time requests
        if data_source == "real_time" and client_ip:
            from ...core.redis_client import redis_client
            today = datetime.now().strftime("%Y-%m-%d")
            rate_limit_key = f"realtime_requests:{client_ip}:{today}"
            current_count = await redis_client.get(rate_limit_key) or 0

            response_data["rate_limit_info"] = {
                "requests_used_today": int(current_count),
                "daily_limit": settings.realtime_requests_per_day,
                "requests_remaining": max(0, settings.realtime_requests_per_day - int(current_count))
            }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache performance statistics and system status.
    """
    try:
        precompute_service = PrecomputeService()
        stats = await precompute_service.get_cache_stats()

        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.post("/cache/invalidate/{symbol}")
async def invalidate_symbol_cache(symbol: str) -> Dict[str, Any]:
    """
    Manually invalidate cache for a specific symbol.
    """
    try:
        symbol = symbol.upper().strip()

        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol format")

        precompute_service = PrecomputeService()
        success = await precompute_service.invalidate_symbol_cache(symbol)

        return {
            "success": success,
            "message": f"Cache invalidated for {symbol}" if success else f"No cache found for {symbol}",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to invalidate cache for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate cache: {str(e)}")


@router.get("/precompute/status")
async def get_precompute_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get status of precompute system and recent job history.
    """
    try:
        from ...models.precomputed_analysis import PrecomputeJobStatus, PrecomputedAnalysis

        # Get recent job status
        recent_jobs = db.query(PrecomputeJobStatus).order_by(
            PrecomputeJobStatus.created_at.desc()
        ).limit(10).all()

        # Get precomputed analysis counts
        total_analyses = db.query(PrecomputedAnalysis).count()
        fresh_analyses = db.query(PrecomputedAnalysis).filter(
            PrecomputedAnalysis.expires_at > datetime.now()
        ).count()

        # Get top stocks status
        from ...tasks.precompute import TOP_STOCKS
        top_stocks_status = []

        for symbol in TOP_STOCKS:
            latest = db.query(PrecomputedAnalysis).filter(
                PrecomputedAnalysis.symbol == symbol
            ).order_by(PrecomputedAnalysis.computed_at.desc()).first()

            if latest:
                top_stocks_status.append({
                    "symbol": symbol,
                    "last_updated": latest.computed_at.isoformat(),
                    "expires_at": latest.expires_at.isoformat(),
                    "is_fresh": not latest.is_expired,
                    "confidence_score": latest.confidence_score,
                    "recommendation": latest.recommendation
                })
            else:
                top_stocks_status.append({
                    "symbol": symbol,
                    "last_updated": None,
                    "expires_at": None,
                    "is_fresh": False,
                    "confidence_score": None,
                    "recommendation": None
                })

        return {
            "success": True,
            "data": {
                "precompute_enabled": settings.precompute_enabled,
                "top_stocks": TOP_STOCKS,
                "system_status": {
                    "total_analyses": total_analyses,
                    "fresh_analyses": fresh_analyses,
                    "stale_analyses": total_analyses - fresh_analyses
                },
                "top_stocks_status": top_stocks_status,
                "recent_jobs": [
                    {
                        "job_id": job.job_id,
                        "job_type": job.job_type,
                        "status": job.status,
                        "symbols_processed": job.symbols_processed,
                        "symbols_failed": job.symbols_failed,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "total_time_seconds": job.total_time_seconds
                    }
                    for job in recent_jobs
                ],
                "configuration": {
                    "market_hours_interval": settings.precompute_market_hours_interval,
                    "after_hours_interval": settings.precompute_after_hours_interval,
                    "weekend_interval": settings.precompute_weekend_interval,
                    "realtime_requests_per_day": settings.realtime_requests_per_day
                }
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get precompute status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get precompute status: {str(e)}")


@router.post("/precompute/trigger/{symbol}")
async def trigger_precompute_update(symbol: str) -> Dict[str, Any]:
    """
    Manually trigger precompute update for a specific symbol.
    """
    try:
        symbol = symbol.upper().strip()

        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol format")

        from ...tasks.precompute import trigger_update_single_stock

        # Trigger background task
        task = trigger_update_single_stock(symbol)

        return {
            "success": True,
            "message": f"Precompute update triggered for {symbol}",
            "task_id": task.id,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to trigger precompute update for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger update: {str(e)}")


@router.get("/sentiment/{symbol}")
async def get_sentiment_breakdown(
    symbol: str,
    company_name: Optional[str] = Query(None, description="Company name for better news search"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed sentiment breakdown from news and social media sources.
    
    Returns:
    - News sentiment analysis with article breakdown
    - Social media sentiment from Twitter, StockTwits, Reddit
    - Platform-specific sentiment scores
    - Volume and engagement metrics
    """
    try:
        symbol = symbol.upper().strip()
        
        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol format")
        
        # Initialize analyzers
        from ...analyzers.news import NewsAnalyzer
        from ...analyzers.social import SocialMediaAnalyzer
        
        # Run sentiment analyses
        async with NewsAnalyzer() as news_analyzer:
            news_result = await news_analyzer.analyze(symbol, company_name)
        
        async with SocialMediaAnalyzer() as social_analyzer:
            social_result = await social_analyzer.analyze(symbol)
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "timestamp": news_result.get("timestamp"),
                "news_sentiment": {
                    "overall_sentiment": news_result.get("sentiment_analysis", {}).get("overall_sentiment"),
                    "sentiment_score": news_result.get("sentiment_analysis", {}).get("sentiment_score"),
                    "confidence": news_result.get("sentiment_analysis", {}).get("confidence"),
                    "article_breakdown": {
                        "total_articles": news_result.get("news_data", {}).get("total_articles", 0),
                        "positive_articles": news_result.get("sentiment_analysis", {}).get("positive_articles", 0),
                        "negative_articles": news_result.get("sentiment_analysis", {}).get("negative_articles", 0),
                        "neutral_articles": news_result.get("sentiment_analysis", {}).get("neutral_articles", 0)
                    },
                    "sources": news_result.get("news_data", {}).get("sources", [])
                },
                "social_sentiment": {
                    "overall_sentiment": social_result.get("sentiment_analysis", {}).get("overall_sentiment"),
                    "sentiment_score": social_result.get("sentiment_analysis", {}).get("sentiment_score"),
                    "confidence": social_result.get("sentiment_analysis", {}).get("confidence"),
                    "platform_breakdown": social_result.get("sentiment_analysis", {}).get("platform_breakdown", {}),
                    "total_posts": social_result.get("sentiment_analysis", {}).get("total_posts", 0)
                },
                "combined_sentiment": {
                    "news_weight": 25.0,
                    "social_weight": 20.0,
                    "weighted_score": (
                        news_result.get("weighted_score", 0) + 
                        social_result.get("weighted_score", 0)
                    )
                }
            },
            "disclaimer": "Sentiment analysis is for informational purposes only. Not financial advice."
        }
        
    except Exception as e:
        logger.error(f"Sentiment analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


@router.get("/options/{symbol}")
async def get_options_analysis(
    symbol: str,
    expiration_date: Optional[str] = Query(None, description="Specific expiration date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get options chain data with analysis and recommendations.
    
    Returns:
    - Options chain (calls and puts)
    - Greeks calculations (delta, gamma, theta, vega)
    - Unusual options activity
    - Options-specific recommendations
    """
    try:
        symbol = symbol.upper().strip()
        
        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol format")
        
        # Get options data
        async with StockDataService() as stock_service:
            options_data = await stock_service.get_options_chain(symbol, expiration_date)
            
            if not options_data:
                raise HTTPException(status_code=404, detail="Options data not available for this symbol")
        
        # Analyze options for unusual activity
        unusual_activity = _analyze_unusual_options_activity(options_data)
        
        # Get stock analysis for context
        confidence_scorer = ConfidenceScorer()
        stock_analysis = await confidence_scorer.analyze_stock(symbol, db)
        
        # Generate options recommendations
        options_recommendations = _generate_options_recommendations(
            options_data, stock_analysis, unusual_activity
        )
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "timestamp": options_data.get("timestamp"),
                "expiration_date": options_data.get("expiration_date"),
                "available_expirations": options_data.get("available_expirations", []),
                "options_chain": {
                    "calls": options_data.get("calls", []),
                    "puts": options_data.get("puts", [])
                },
                "unusual_activity": unusual_activity,
                "recommendations": options_recommendations,
                "stock_context": {
                    "current_price": stock_analysis.get("current_price"),
                    "recommendation": stock_analysis.get("recommendation"),
                    "confidence_level": stock_analysis.get("confidence_level")
                }
            },
            "disclaimer": "Options trading involves significant risk. This analysis is for educational purposes only."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Options analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Options analysis failed: {str(e)}")


@router.get("/recommendations")
async def get_daily_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations to return"),
    min_confidence: str = Query("MEDIUM", description="Minimum confidence level (LOW, MEDIUM, HIGH)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get daily top stock recommendations based on analysis results.
    
    Returns:
    - Top buy/sell recommendations
    - Confidence levels and scores
    - Risk assessments
    - Position sizing suggestions
    """
    try:
        # Map confidence levels to numeric values for filtering
        confidence_mapping = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        min_confidence_value = confidence_mapping.get(min_confidence.upper(), 2)
        
        # Query recent analysis results
        query = db.query(AnalysisResult).join(Stock)
        
        # Filter by confidence level
        if min_confidence_value == 3:  # HIGH
            query = query.filter(AnalysisResult.confidence_level == "HIGH")
        elif min_confidence_value == 2:  # MEDIUM or higher
            query = query.filter(AnalysisResult.confidence_level.in_(["MEDIUM", "HIGH"]))
        # LOW includes all levels
        
        # Get recent results, ordered by score
        recent_results = query.order_by(
            AnalysisResult.timestamp.desc(),
            AnalysisResult.overall_score.desc()
        ).limit(limit * 2).all()  # Get more to filter and rank
        
        # Process and rank recommendations
        recommendations = []
        for result in recent_results:
            if result.recommendation in ["STRONG_BUY", "BUY", "WEAK_BUY", "STRONG_SELL", "SELL", "WEAK_SELL"]:
                recommendations.append({
                    "symbol": result.stock.symbol,
                    "company_name": result.stock.name,
                    "recommendation": result.recommendation,
                    "confidence_level": result.confidence_level,
                    "overall_score": result.overall_score,
                    "technical_score": result.technical_score,
                    "news_score": result.news_score,
                    "social_score": result.social_score,
                    "risk_level": result.risk_level,
                    "max_position_size": result.max_position_size,
                    "stop_loss_price": result.stop_loss_price,
                    "take_profit_price": result.take_profit_price,
                    "analysis_timestamp": result.timestamp.isoformat(),
                    "summary": result.analysis_summary
                })
        
        # Sort by score and limit results
        recommendations.sort(key=lambda x: x["overall_score"], reverse=True)
        recommendations = recommendations[:limit]
        
        return {
            "success": True,
            "data": {
                "timestamp": logger.info("Generated daily recommendations"),
                "total_recommendations": len(recommendations),
                "filter_criteria": {
                    "min_confidence": min_confidence,
                    "limit": limit
                },
                "recommendations": recommendations
            },
            "disclaimer": "These recommendations are for educational purposes only. Not financial advice."
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


def _analyze_unusual_options_activity(options_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze options chain for unusual activity."""
    calls = options_data.get("calls", [])
    puts = options_data.get("puts", [])
    
    # Calculate average volume and open interest
    all_options = calls + puts
    if not all_options:
        return {"has_unusual_activity": False}
    
    volumes = [opt.get("volume", 0) for opt in all_options if opt.get("volume", 0) > 0]
    open_interests = [opt.get("open_interest", 0) for opt in all_options if opt.get("open_interest", 0) > 0]
    
    if not volumes:
        return {"has_unusual_activity": False}
    
    avg_volume = sum(volumes) / len(volumes)
    avg_oi = sum(open_interests) / len(open_interests) if open_interests else 0
    
    # Find unusual activity (volume > 3x average)
    unusual_options = []
    for option in all_options:
        volume = option.get("volume", 0)
        if volume > avg_volume * 3 and volume > 100:  # Significant volume threshold
            unusual_options.append({
                "strike": option.get("strike"),
                "option_type": option.get("option_type"),
                "volume": volume,
                "open_interest": option.get("open_interest", 0),
                "last_price": option.get("last_price", 0),
                "implied_volatility": option.get("implied_volatility", 0)
            })
    
    return {
        "has_unusual_activity": len(unusual_options) > 0,
        "unusual_options": unusual_options,
        "average_volume": round(avg_volume, 0),
        "average_open_interest": round(avg_oi, 0)
    }


def _generate_options_recommendations(options_data: Dict[str, Any], 
                                    stock_analysis: Dict[str, Any],
                                    unusual_activity: Dict[str, Any]) -> Dict[str, Any]:
    """Generate options trading recommendations based on analysis."""
    stock_recommendation = stock_analysis.get("recommendation", "HOLD")
    current_price = stock_analysis.get("current_price", 0)
    
    recommendations = []
    
    # Generate recommendations based on stock analysis
    if stock_recommendation in ["STRONG_BUY", "BUY"]:
        # Recommend call options
        calls = options_data.get("calls", [])
        atm_calls = [c for c in calls if abs(c.get("strike", 0) - current_price) < current_price * 0.05]
        
        if atm_calls:
            best_call = min(atm_calls, key=lambda x: abs(x.get("strike", 0) - current_price))
            recommendations.append({
                "strategy": "Long Call",
                "option_type": "CALL",
                "strike": best_call.get("strike"),
                "rationale": f"Bullish outlook based on {stock_recommendation} recommendation",
                "max_risk": best_call.get("last_price", 0),
                "breakeven": best_call.get("strike", 0) + best_call.get("last_price", 0)
            })
    
    elif stock_recommendation in ["STRONG_SELL", "SELL"]:
        # Recommend put options
        puts = options_data.get("puts", [])
        atm_puts = [p for p in puts if abs(p.get("strike", 0) - current_price) < current_price * 0.05]
        
        if atm_puts:
            best_put = min(atm_puts, key=lambda x: abs(x.get("strike", 0) - current_price))
            recommendations.append({
                "strategy": "Long Put",
                "option_type": "PUT",
                "strike": best_put.get("strike"),
                "rationale": f"Bearish outlook based on {stock_recommendation} recommendation",
                "max_risk": best_put.get("last_price", 0),
                "breakeven": best_put.get("strike", 0) - best_put.get("last_price", 0)
            })
    
    return {
        "strategies": recommendations,
        "risk_warning": "Options trading involves significant risk of loss. Only trade with risk capital.",
        "unusual_activity_note": "Consider unusual options activity when making trading decisions." if unusual_activity.get("has_unusual_activity") else None
    }


@router.get("/stock/{symbol}/ohlc")
async def get_stock_ohlc(
    symbol: str,
    period: str = Query("1y", description="Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"),
    interval: str = Query("1d", description="Data interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo")
) -> List[Dict[str, Any]]:
    """
    Get OHLC (Open, High, Low, Close) data for stock charts.

    Returns data in format compatible with TradingView Lightweight Charts:
    [
        {
            "time": "2023-01-01", // or timestamp
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 103.0,
            "volume": 1000000
        }
    ]
    """
    try:
        symbol = symbol.upper().strip()

        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol format")

        # Initialize stock data service
        stock_service = StockDataService()

        # Get historical data
        historical_data = await stock_service.get_historical_data(symbol, period=period, interval=interval)

        if not historical_data or historical_data.empty:
            raise HTTPException(status_code=404, detail=f"No OHLC data found for symbol {symbol}")

        # Convert to TradingView format
        ohlc_data = []
        for index, row in historical_data.iterrows():
            # Convert timestamp to string format for TradingView
            if hasattr(index, 'strftime'):
                time_str = index.strftime('%Y-%m-%d')
            else:
                time_str = str(index)

            ohlc_data.append({
                "time": time_str,
                "open": float(row.get('Open', 0)),
                "high": float(row.get('High', 0)),
                "low": float(row.get('Low', 0)),
                "close": float(row.get('Close', 0)),
                "volume": int(row.get('Volume', 0)) if row.get('Volume') else 0
            })

        # Sort by time to ensure proper order
        ohlc_data.sort(key=lambda x: x['time'])

        return ohlc_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching OHLC data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch OHLC data: {str(e)}")


@router.get("/unusual-options")
async def get_unusual_options_activity(
    limit: int = Query(50, ge=1, le=200, description="Number of unusual options to return"),
    min_volume_ratio: float = Query(2.0, ge=1.0, le=10.0, description="Minimum volume/OI ratio for unusual activity"),
    min_premium: float = Query(10000, ge=1000, description="Minimum premium value for large trades"),
    time_range: str = Query("1d", description="Time range: 1h, 4h, 1d"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get unusual options activity across all symbols with AI analysis.

    Returns:
    - Top unusual options by volume/OI ratio
    - Large premium trades
    - AI summary of market activity
    - Sector breakdown of unusual activity
    """
    try:
        from ...services.volume_analyzer import VolumeAnalyzer
        from ...services.grok_ai import GrokAIService

        volume_analyzer = VolumeAnalyzer()
        ai_service = GrokAIService()

        # Get popular symbols to analyze (you can expand this list)
        popular_symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX",
            "SPY", "QQQ", "IWM", "DIA", "AMD", "INTC", "CRM", "ORCL",
            "BABA", "UBER", "LYFT", "SNAP", "TWTR", "ROKU", "ZM", "SHOP"
        ]

        unusual_options = []
        large_trades = []
        sector_activity = {}

        # Analyze each symbol for unusual options activity
        for symbol in popular_symbols:
            try:
                stock_service = StockDataService()
                options_data = await stock_service.get_options_chain(symbol)

                if not options_data:
                    continue

                calls = options_data.get("calls", [])
                puts = options_data.get("puts", [])

                # Analyze unusual activity
                for contract in calls + puts:
                    volume = contract.get('volume', 0)
                    open_interest = contract.get('open_interest', 1)
                    last_price = contract.get('last_price', 0)

                    if volume > 0 and open_interest > 0:
                        volume_oi_ratio = volume / open_interest
                        premium_value = volume * last_price * 100

                        # Check for unusual volume/OI ratio
                        if volume_oi_ratio >= min_volume_ratio:
                            unusual_options.append({
                                "symbol": symbol,
                                "contract_symbol": contract.get('contract_symbol', ''),
                                "option_type": contract.get('option_type', ''),
                                "strike": contract.get('strike_price', 0),
                                "expiration": contract.get('expiration_date', ''),
                                "volume": volume,
                                "open_interest": open_interest,
                                "volume_oi_ratio": round(volume_oi_ratio, 2),
                                "last_price": last_price,
                                "premium_value": round(premium_value, 2),
                                "timestamp": datetime.now().isoformat()
                            })

                        # Check for large premium trades
                        if premium_value >= min_premium:
                            large_trades.append({
                                "symbol": symbol,
                                "contract_symbol": contract.get('contract_symbol', ''),
                                "option_type": contract.get('option_type', ''),
                                "strike": contract.get('strike_price', 0),
                                "premium_value": round(premium_value, 2),
                                "volume": volume,
                                "last_price": last_price,
                                "timestamp": datetime.now().isoformat()
                            })

                    # Track sector activity (simplified mapping)
                    sector = _get_sector_for_symbol(symbol)
                    if sector not in sector_activity:
                        sector_activity[sector] = {"call_volume": 0, "put_volume": 0, "total_premium": 0}

                    if contract.get('option_type') == 'call':
                        sector_activity[sector]["call_volume"] += volume
                    else:
                        sector_activity[sector]["put_volume"] += volume

                    sector_activity[sector]["total_premium"] += volume * last_price * 100

            except Exception as e:
                logger.warning(f"Error analyzing unusual options for {symbol}: {e}")
                continue

        # Sort by volume/OI ratio and premium value
        unusual_options.sort(key=lambda x: x["volume_oi_ratio"], reverse=True)
        large_trades.sort(key=lambda x: x["premium_value"], reverse=True)

        # Limit results
        unusual_options = unusual_options[:limit]
        large_trades = large_trades[:min(limit, 20)]

        # Generate AI summary
        ai_summary = await _generate_unusual_options_summary(
            unusual_options, large_trades, sector_activity, ai_service
        )

        return {
            "success": True,
            "data": {
                "timestamp": datetime.now().isoformat(),
                "time_range": time_range,
                "filter_criteria": {
                    "min_volume_ratio": min_volume_ratio,
                    "min_premium": min_premium,
                    "symbols_analyzed": len(popular_symbols)
                },
                "ai_summary": ai_summary,
                "unusual_options": unusual_options,
                "large_trades": large_trades,
                "sector_activity": sector_activity,
                "market_metrics": {
                    "total_unusual_contracts": len(unusual_options),
                    "total_large_trades": len(large_trades),
                    "total_premium_flow": sum(trade["premium_value"] for trade in large_trades),
                    "call_put_ratio": _calculate_overall_call_put_ratio(unusual_options)
                }
            },
            "disclaimer": "Unusual options activity analysis is for educational purposes only. Not financial advice."
        }

    except Exception as e:
        logger.error(f"Failed to get unusual options activity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get unusual options activity: {str(e)}")


def _get_sector_for_symbol(symbol: str) -> str:
    """Map symbol to sector (simplified mapping)."""
    tech_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", "INTC", "CRM", "ORCL"]
    finance_symbols = ["JPM", "BAC", "WFC", "GS", "MS", "C"]
    healthcare_symbols = ["JNJ", "PFE", "UNH", "ABBV", "MRK", "TMO"]
    energy_symbols = ["XOM", "CVX", "COP", "EOG", "SLB", "MPC"]
    etf_symbols = ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLV"]

    if symbol in tech_symbols:
        return "Technology"
    elif symbol in finance_symbols:
        return "Financial"
    elif symbol in healthcare_symbols:
        return "Healthcare"
    elif symbol in energy_symbols:
        return "Energy"
    elif symbol in etf_symbols:
        return "ETFs"
    else:
        return "Other"


def _calculate_overall_call_put_ratio(unusual_options: List[Dict]) -> float:
    """Calculate overall call/put ratio from unusual options."""
    call_volume = sum(opt["volume"] for opt in unusual_options if opt["option_type"] == "call")
    put_volume = sum(opt["volume"] for opt in unusual_options if opt["option_type"] == "put")

    if put_volume == 0:
        return float('inf') if call_volume > 0 else 0

    return round(call_volume / put_volume, 2)


async def _generate_unusual_options_summary(
    unusual_options: List[Dict],
    large_trades: List[Dict],
    sector_activity: Dict,
    ai_service
) -> Dict[str, Any]:
    """Generate AI summary of unusual options activity."""
    try:
        # Prepare data for AI analysis
        summary_data = {
            "total_unusual_contracts": len(unusual_options),
            "total_large_trades": len(large_trades),
            "top_symbols": list(set([opt["symbol"] for opt in unusual_options[:10]])),
            "top_sectors": sorted(sector_activity.items(), key=lambda x: x[1]["total_premium"], reverse=True)[:5],
            "call_put_ratio": _calculate_overall_call_put_ratio(unusual_options),
            "largest_premium_trade": large_trades[0] if large_trades else None,
            "highest_volume_ratio": unusual_options[0] if unusual_options else None
        }

        # Create prompt for AI analysis
        prompt = f"""
        Analyze the following unusual options activity data and provide a concise market summary:

        - Total unusual contracts: {summary_data['total_unusual_contracts']}
        - Total large trades: {summary_data['total_large_trades']}
        - Top active symbols: {', '.join(summary_data['top_symbols'])}
        - Call/Put ratio: {summary_data['call_put_ratio']}
        - Most active sectors: {[sector[0] for sector in summary_data['top_sectors'][:3]]}

        Provide a 2-3 sentence summary highlighting the most significant trends and what they might indicate about market sentiment.
        """

        # Generate basic analysis summary (simplified for now - can enhance with AI later)
        try:
            # Try to get AI analysis if available
            async with ai_service:
                ai_analysis = await ai_service.analyze_option_play(
                    symbol="MARKET",
                    technical_data={},
                    news_data={},
                    social_data={},
                    polymarket_data=[],
                    catalyst_data={},
                    unusual_volume_data=summary_data,
                    confidence_score=70.0
                )

                if ai_analysis:
                    ai_summary = ai_analysis.summary
                    ai_sentiment = ai_analysis.recommendation
                    ai_confidence = ai_analysis.confidence / 100.0
                else:
                    ai_summary = "Analyzing unusual options activity across multiple symbols and sectors."
                    ai_sentiment = "NEUTRAL"
                    ai_confidence = 0.7
        except Exception as e:
            logger.warning(f"AI analysis unavailable: {e}")
            ai_summary = "Analyzing unusual options activity across multiple symbols and sectors."
            ai_sentiment = "NEUTRAL"
            ai_confidence = 0.7

        return {
            "summary": ai_summary,
            "key_trends": [
                f"Tracking {summary_data['total_unusual_contracts']} unusual contracts",
                f"Call/Put ratio: {summary_data['call_put_ratio']}",
                f"Most active: {', '.join(summary_data['top_symbols'][:3])}"
            ],
            "market_sentiment": ai_sentiment,
            "confidence": ai_confidence,
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        logger.warning(f"Error generating AI summary: {e}")
        return {
            "summary": "Real-time unusual options activity monitoring across major symbols.",
            "key_trends": [
                f"Monitoring {len(unusual_options)} unusual contracts",
                f"Tracking {len(large_trades)} large premium trades",
                "AI analysis temporarily unavailable"
            ],
            "market_sentiment": "NEUTRAL",
            "confidence": 0.5,
            "last_updated": datetime.now().isoformat()
        }
