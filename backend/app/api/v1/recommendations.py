"""
Recommendations API endpoints for daily stock recommendations and watchlists
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ...core.database import get_db
from ...models.stock import Stock
from ...models.analysis_results import AnalysisResult
from ...analyzers.confidence import ConfidenceScorer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


@router.get("/recommendations/daily")
async def get_daily_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations to return"),
    min_confidence: str = Query("MEDIUM", description="Minimum confidence level (LOW, MEDIUM, HIGH)"),
    recommendation_type: str = Query("ALL", description="Filter by type (BUY, SELL, ALL)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get daily top stock recommendations based on recent analysis results.
    
    Returns the highest-scoring recommendations from the last 24 hours,
    filtered by confidence level and recommendation type.
    """
    try:
        # Map confidence levels to numeric values for filtering
        confidence_mapping = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        min_confidence_value = confidence_mapping.get(min_confidence.upper(), 2)
        
        # Get cutoff time (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Build query
        query = db.query(AnalysisResult).join(Stock).filter(
            AnalysisResult.timestamp >= cutoff_time
        )
        
        # Filter by confidence level
        if min_confidence_value == 3:  # HIGH only
            query = query.filter(AnalysisResult.confidence_level == "HIGH")
        elif min_confidence_value == 2:  # MEDIUM or HIGH
            query = query.filter(AnalysisResult.confidence_level.in_(["MEDIUM", "HIGH"]))
        # LOW includes all levels
        
        # Filter by recommendation type
        if recommendation_type.upper() == "BUY":
            query = query.filter(AnalysisResult.recommendation.in_(["STRONG_BUY", "BUY", "WEAK_BUY"]))
        elif recommendation_type.upper() == "SELL":
            query = query.filter(AnalysisResult.recommendation.in_(["STRONG_SELL", "SELL", "WEAK_SELL"]))
        else:  # ALL - exclude HOLD recommendations
            query = query.filter(AnalysisResult.recommendation != "HOLD")
        
        # Get results ordered by score
        results = query.order_by(
            AnalysisResult.overall_score.desc(),
            AnalysisResult.timestamp.desc()
        ).limit(limit).all()
        
        # Format recommendations
        recommendations = []
        for result in results:
            recommendations.append({
                "symbol": result.stock.symbol,
                "company_name": result.stock.name,
                "sector": result.stock.sector,
                "recommendation": result.recommendation,
                "confidence_level": result.confidence_level,
                "overall_score": round(result.overall_score, 2),
                "component_scores": {
                    "technical": round(result.technical_score, 2),
                    "news": round(result.news_score, 2),
                    "social": round(result.social_score, 2)
                },
                "risk_assessment": {
                    "risk_level": result.risk_level,
                    "max_position_size_percent": result.max_position_size,
                    "stop_loss_price": result.stop_loss_price,
                    "take_profit_price": result.take_profit_price
                },
                "analysis_timestamp": result.timestamp.isoformat(),
                "summary": result.analysis_summary,
                "priority": _calculate_priority(result)
            })
        
        # Sort by priority (combines score and confidence)
        recommendations.sort(key=lambda x: x["priority"], reverse=True)
        
        return {
            "success": True,
            "data": {
                "timestamp": datetime.now().isoformat(),
                "total_recommendations": len(recommendations),
                "filter_criteria": {
                    "min_confidence": min_confidence,
                    "recommendation_type": recommendation_type,
                    "time_range": "24 hours",
                    "limit": limit
                },
                "recommendations": recommendations,
                "market_summary": await _get_market_summary(db)
            },
            "disclaimer": "These recommendations are for educational purposes only. Not financial advice. Past performance does not guarantee future results."
        }
        
    except Exception as e:
        logger.error(f"Failed to get daily recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.get("/recommendations/trending")
async def get_trending_stocks(
    limit: int = Query(20, ge=1, le=100, description="Number of trending stocks to return"),
    time_range: str = Query("24h", description="Time range (1h, 6h, 24h, 7d)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get trending stocks based on analysis frequency and sentiment changes.
    
    Returns stocks that are being analyzed frequently or showing
    significant sentiment shifts.
    """
    try:
        # Map time range to hours
        time_mapping = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
        hours = time_mapping.get(time_range, 24)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Query for stocks with multiple recent analyses
        trending_query = db.query(
            Stock.symbol,
            Stock.name,
            Stock.sector,
            func.count(AnalysisResult.id).label('analysis_count'),
            func.avg(AnalysisResult.confidence_score).label('avg_score'),
            func.max(AnalysisResult.timestamp).label('latest_analysis')
        ).join(AnalysisResult).filter(
            AnalysisResult.timestamp >= cutoff_time
        ).group_by(
            Stock.id, Stock.symbol, Stock.name, Stock.sector
        ).having(
            func.count(AnalysisResult.id) >= 2  # At least 2 analyses
        ).order_by(
            func.count(AnalysisResult.id).desc(),
            func.avg(AnalysisResult.confidence_score).desc()
        ).limit(limit).all()
        
        trending_stocks = []
        for stock_data in trending_query:
            # Get latest analysis for this stock
            latest_analysis = db.query(AnalysisResult).join(Stock).filter(
                Stock.symbol == stock_data.symbol
            ).order_by(AnalysisResult.timestamp.desc()).first()

            if latest_analysis:
                trending_stocks.append({
                    "symbol": stock_data.symbol,
                    "company_name": stock_data.name,
                    "sector": stock_data.sector,
                    "analysis_count": stock_data.analysis_count,
                    "average_score": round(stock_data.avg_score, 2),
                    "latest_recommendation": latest_analysis.recommendation,
                    "latest_confidence": latest_analysis.confidence_level,
                    "latest_analysis": stock_data.latest_analysis.isoformat(),
                    "trend_indicator": _calculate_trend_indicator(stock_data.analysis_count, stock_data.avg_score)
                })

        # If no trending stocks found, provide mock data for development
        if not trending_stocks:
            trending_stocks = _get_mock_trending_stocks()
        
        return {
            "success": True,
            "data": {
                "timestamp": datetime.now().isoformat(),
                "time_range": time_range,
                "total_trending": len(trending_stocks),
                "trending_stocks": trending_stocks
            },
            "disclaimer": "Trending analysis is based on analysis frequency and does not constitute investment advice."
        }
        
    except Exception as e:
        logger.error(f"Failed to get trending stocks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trending stocks: {str(e)}")


@router.get("/recommendations/watchlist")
async def get_watchlist_recommendations(
    symbols: str = Query(..., description="Comma-separated list of symbols to analyze"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get analysis and recommendations for a custom watchlist of stocks.
    
    Analyzes each symbol in the watchlist and returns current recommendations
    with comparative scoring.
    """
    try:
        # Parse symbols
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        
        if not symbol_list:
            raise HTTPException(status_code=400, detail="No valid symbols provided")
        
        if len(symbol_list) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 symbols allowed")
        
        # Analyze each symbol
        confidence_scorer = ConfidenceScorer()
        watchlist_results = []
        
        for symbol in symbol_list:
            try:
                # Get latest analysis or perform new analysis
                latest_analysis = db.query(AnalysisResult).join(Stock).filter(
                    Stock.symbol == symbol
                ).order_by(AnalysisResult.timestamp.desc()).first()
                
                # If analysis is older than 1 hour, perform new analysis
                if not latest_analysis or (datetime.now() - latest_analysis.timestamp).seconds > 3600:
                    analysis_result = await confidence_scorer.analyze_stock(symbol, db)
                    
                    if "error" not in analysis_result:
                        watchlist_results.append({
                            "symbol": symbol,
                            "status": "analyzed",
                            "data": analysis_result
                        })
                    else:
                        watchlist_results.append({
                            "symbol": symbol,
                            "status": "error",
                            "error": analysis_result["error"]
                        })
                else:
                    # Use existing analysis
                    watchlist_results.append({
                        "symbol": symbol,
                        "status": "cached",
                        "data": {
                            "symbol": symbol,
                            "recommendation": latest_analysis.recommendation,
                            "confidence_level": latest_analysis.confidence_level,
                            "confidence_score": latest_analysis.overall_score,
                            "risk_level": latest_analysis.risk_level,
                            "analysis_timestamp": latest_analysis.timestamp.isoformat(),
                            "summary": latest_analysis.analysis_summary
                        }
                    })
                    
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
                watchlist_results.append({
                    "symbol": symbol,
                    "status": "error",
                    "error": str(e)
                })
        
        # Generate comparative analysis
        successful_analyses = [r for r in watchlist_results if r["status"] in ["analyzed", "cached"]]
        comparative_analysis = _generate_comparative_analysis(successful_analyses)
        
        return {
            "success": True,
            "data": {
                "timestamp": datetime.now().isoformat(),
                "watchlist_size": len(symbol_list),
                "successful_analyses": len(successful_analyses),
                "results": watchlist_results,
                "comparative_analysis": comparative_analysis
            },
            "disclaimer": "Watchlist analysis is for educational purposes only. Not financial advice."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Watchlist analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Watchlist analysis failed: {str(e)}")


def _calculate_priority(analysis_result: AnalysisResult) -> float:
    """Calculate priority score for ranking recommendations."""
    # Base priority on overall score
    priority = analysis_result.overall_score
    
    # Boost for high confidence
    if analysis_result.confidence_level == "HIGH":
        priority += 10
    elif analysis_result.confidence_level == "MEDIUM":
        priority += 5
    
    # Boost for strong recommendations
    if analysis_result.recommendation in ["STRONG_BUY", "STRONG_SELL"]:
        priority += 15
    elif analysis_result.recommendation in ["BUY", "SELL"]:
        priority += 10
    
    # Reduce for high risk
    if analysis_result.risk_level == "high":
        priority -= 5
    
    return priority


def _calculate_trend_indicator(analysis_count: int, avg_score: float) -> str:
    """Calculate trend indicator based on analysis frequency and score."""
    if analysis_count >= 5 and avg_score >= 70:
        return "🔥 HOT"
    elif analysis_count >= 3 and avg_score >= 60:
        return "📈 RISING"
    elif analysis_count >= 3 and avg_score <= 40:
        return "📉 FALLING"
    else:
        return "👀 WATCHING"


async def _get_market_summary(db: Session) -> Dict[str, Any]:
    """Get overall market summary based on recent analyses."""
    try:
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Get recent analysis statistics
        recent_analyses = db.query(AnalysisResult).filter(
            AnalysisResult.timestamp >= cutoff_time
        ).all()
        
        if not recent_analyses:
            return {"status": "no_data"}
        
        # Calculate market sentiment
        buy_recommendations = len([a for a in recent_analyses if a.recommendation in ["STRONG_BUY", "BUY", "WEAK_BUY"]])
        sell_recommendations = len([a for a in recent_analyses if a.recommendation in ["STRONG_SELL", "SELL", "WEAK_SELL"]])
        hold_recommendations = len([a for a in recent_analyses if a.recommendation == "HOLD"])
        
        total_analyses = len(recent_analyses)
        avg_score = sum(a.confidence_score for a in recent_analyses) / total_analyses
        
        # Determine market sentiment
        if buy_recommendations > sell_recommendations * 1.5:
            market_sentiment = "bullish"
        elif sell_recommendations > buy_recommendations * 1.5:
            market_sentiment = "bearish"
        else:
            market_sentiment = "neutral"
        
        return {
            "status": "active",
            "market_sentiment": market_sentiment,
            "total_analyses": total_analyses,
            "average_score": round(avg_score, 2),
            "recommendation_breakdown": {
                "buy": buy_recommendations,
                "sell": sell_recommendations,
                "hold": hold_recommendations
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get market summary: {e}")
        return {"status": "error", "error": str(e)}


def _generate_comparative_analysis(successful_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate comparative analysis for watchlist stocks."""
    if not successful_analyses:
        return {"status": "no_data"}
    
    # Extract scores and recommendations
    scores = []
    recommendations = {"buy": 0, "sell": 0, "hold": 0}
    
    for analysis in successful_analyses:
        data = analysis["data"]
        score = data.get("confidence_score", 50)
        scores.append(score)
        
        rec = data.get("recommendation", "HOLD")
        if rec in ["STRONG_BUY", "BUY", "WEAK_BUY"]:
            recommendations["buy"] += 1
        elif rec in ["STRONG_SELL", "SELL", "WEAK_SELL"]:
            recommendations["sell"] += 1
        else:
            recommendations["hold"] += 1
    
    # Find best and worst performers
    best_performer = max(successful_analyses, key=lambda x: x["data"].get("confidence_score", 0))
    worst_performer = min(successful_analyses, key=lambda x: x["data"].get("confidence_score", 100))
    
    return {
        "status": "complete",
        "average_score": round(sum(scores) / len(scores), 2),
        "score_range": {
            "min": min(scores),
            "max": max(scores)
        },
        "recommendation_distribution": recommendations,
        "best_performer": {
            "symbol": best_performer["symbol"],
            "score": best_performer["data"].get("confidence_score"),
            "recommendation": best_performer["data"].get("recommendation")
        },
        "worst_performer": {
            "symbol": worst_performer["symbol"],
            "score": worst_performer["data"].get("confidence_score"),
            "recommendation": worst_performer["data"].get("recommendation")
        }
    }


def _get_mock_trending_stocks() -> List[Dict[str, Any]]:
    """Provide mock trending stocks data for development/demo purposes."""
    import random

    mock_stocks = [
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "base_price": 175.50},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "base_price": 378.85},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", "base_price": 875.30},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "base_price": 138.75},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary", "base_price": 145.20},
        {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary", "base_price": 248.50},
        {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "base_price": 485.75},
        {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Communication Services", "base_price": 485.30},
        {"symbol": "AMD", "name": "Advanced Micro Devices", "sector": "Technology", "base_price": 142.85},
        {"symbol": "CRM", "name": "Salesforce Inc.", "sector": "Technology", "base_price": 285.40},
        {"symbol": "ORCL", "name": "Oracle Corporation", "sector": "Technology", "base_price": 115.60},
        {"symbol": "ADBE", "name": "Adobe Inc.", "sector": "Technology", "base_price": 485.90},
        {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "sector": "Financial Services", "base_price": 78.25},
        {"symbol": "INTC", "name": "Intel Corporation", "sector": "Technology", "base_price": 24.85},
        {"symbol": "UBER", "name": "Uber Technologies Inc.", "sector": "Technology", "base_price": 68.40},
        {"symbol": "SPOT", "name": "Spotify Technology S.A.", "sector": "Communication Services", "base_price": 285.75},
        {"symbol": "SHOP", "name": "Shopify Inc.", "sector": "Technology", "base_price": 78.90},
        {"symbol": "SQ", "name": "Block Inc.", "sector": "Financial Services", "base_price": 68.25},
        {"symbol": "ROKU", "name": "Roku Inc.", "sector": "Communication Services", "base_price": 58.40},
        {"symbol": "ZM", "name": "Zoom Video Communications", "sector": "Technology", "base_price": 68.75}
    ]

    trending_stocks = []
    selected_stocks = random.sample(mock_stocks, min(15, len(mock_stocks)))

    for i, stock in enumerate(selected_stocks):
        # Generate realistic mock data
        analysis_count = random.randint(3, 12)
        avg_score = random.uniform(45, 85)
        price_change = random.uniform(-5.0, 8.0)
        price_change_percent = (price_change / stock["base_price"]) * 100
        volume = random.randint(1000000, 50000000)
        sentiment_score = random.uniform(0.3, 0.9)

        recommendations = ["BUY", "STRONG_BUY", "HOLD", "SELL"]
        recommendation = random.choice(recommendations)

        trending_stocks.append({
            "symbol": stock["symbol"],
            "company_name": stock["name"],
            "sector": stock["sector"],
            "current_price": round(stock["base_price"] + price_change, 2),
            "price_change": round(price_change, 2),
            "price_change_percent": round(price_change_percent, 2),
            "volume": volume,
            "analysis_count": analysis_count,
            "sentiment_score": round(sentiment_score, 2),
            "recommendation": recommendation,
            "average_score": round(avg_score, 2),
            "latest_recommendation": recommendation,
            "latest_confidence": "HIGH" if avg_score > 70 else "MEDIUM" if avg_score > 50 else "LOW",
            "latest_analysis": datetime.now().isoformat(),
            "trend_indicator": _calculate_trend_indicator(analysis_count, avg_score)
        })

    # Sort by analysis count and score
    trending_stocks.sort(key=lambda x: (x["analysis_count"], x["average_score"]), reverse=True)

    return trending_stocks
