"""
Analysis API endpoints for stock analysis and recommendations
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...analyzers.confidence import ConfidenceScorer
from ...services.stock_data import StockDataService
from ...models.stock import Stock
from ...models.analysis_results import AnalysisResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.get("/analyze/{symbol}")
async def analyze_stock(
    symbol: str,
    company_name: Optional[str] = Query(None, description="Company name for better news search"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Perform complete stock analysis with confidence scoring.
    
    Returns comprehensive analysis including:
    - Technical analysis (RSI, MACD, Bollinger Bands, etc.)
    - News sentiment analysis
    - Social media sentiment
    - Risk assessment
    - Position sizing recommendations
    - Final buy/sell recommendation with confidence level
    """
    try:
        symbol = symbol.upper().strip()
        
        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol format")
        
        # Initialize confidence scorer
        confidence_scorer = ConfidenceScorer()
        
        # Perform complete analysis
        result = await confidence_scorer.analyze_stock(symbol, db, company_name)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "data": result,
            "disclaimer": "This analysis is for educational purposes only. Not financial advice."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


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
