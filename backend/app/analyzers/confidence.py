"""
Confidence Scoring Engine - Combines all analyzers with weighted scoring
Technical(35%) + News(25%) + Social(20%) + Earnings(15%) + Market(5%)
"""
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from ..services.stock_data import StockDataService
from .technical import TechnicalAnalyzer
from .news import NewsAnalyzer
from .social import SocialMediaAnalyzer
from ..core.redis_client import redis_client
from ..core.config import settings
from ..models.analysis_results import AnalysisResult, ConfidenceScore

logger = logging.getLogger(__name__)


def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


class ConfidenceScorer:
    """
    Master confidence scoring engine that combines all analysis components.
    Provides final buy/sell recommendations with confidence levels and risk assessment.
    """
    
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        self.social_analyzer = SocialMediaAnalyzer()
        
        # Weights must sum to 100%
        self.weights = {
            "technical": 35.0,
            "news": 25.0,
            "social": 20.0,
            "earnings": 15.0,
            "market": 5.0
        }
    
    async def analyze_stock(self, symbol: str, db: Session, 
                          company_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform complete stock analysis with confidence scoring.
        
        Args:
            symbol: Stock symbol
            db: Database session
            company_name: Company name for better news search
            
        Returns:
            Complete analysis with confidence score and recommendation
        """
        cache_key = f"complete_analysis:{symbol}"
        
        # Check cache (10 minute TTL for complete analysis)
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for complete analysis {symbol}")
            return cached_result
        
        try:
            # Get stock data first
            async with StockDataService() as stock_service:
                # Get real-time quote
                quote_data = await stock_service.get_real_time_quote(symbol)
                if not quote_data:
                    return self._create_error_result(symbol, "Unable to fetch stock data")
                
                # Get historical data for technical analysis
                historical_data = await stock_service.get_historical_data(symbol, "1y")
                if not historical_data:
                    return self._create_error_result(symbol, "Unable to fetch historical data")
                
                # Store stock data in database
                stock = await stock_service.store_stock_data(db, symbol, quote_data)
            
            # Run all analyzers concurrently
            analysis_tasks = []
            
            # Technical analysis
            analysis_tasks.append(self.technical_analyzer.analyze(symbol, historical_data))
            
            # News analysis
            async with self.news_analyzer as news_analyzer:
                analysis_tasks.append(news_analyzer.analyze(symbol, company_name))
            
            # Social media analysis
            async with self.social_analyzer as social_analyzer:
                analysis_tasks.append(social_analyzer.analyze(symbol))
            
            # Execute all analyses
            import asyncio
            technical_result, news_result, social_result = await asyncio.gather(
                *analysis_tasks, return_exceptions=True
            )
            
            # Handle any exceptions
            if isinstance(technical_result, Exception):
                logger.error(f"Technical analysis failed: {technical_result}")
                technical_result = self._create_neutral_component("technical", str(technical_result))
            
            if isinstance(news_result, Exception):
                logger.error(f"News analysis failed: {news_result}")
                news_result = self._create_neutral_component("news", str(news_result))
            
            if isinstance(social_result, Exception):
                logger.error(f"Social analysis failed: {social_result}")
                social_result = self._create_neutral_component("social", str(social_result))
            
            # Add earnings and market analysis (simplified for now)
            earnings_result = await self._analyze_earnings_impact(symbol, quote_data)
            market_result = await self._analyze_market_conditions(symbol, quote_data)
            
            # Calculate final confidence score
            confidence_data = self._calculate_confidence_score({
                "technical": technical_result,
                "news": news_result,
                "social": social_result,
                "earnings": earnings_result,
                "market": market_result
            })
            
            # Generate risk assessment
            risk_assessment = self._assess_risk(quote_data, confidence_data, technical_result)
            
            # Create final result
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "current_price": quote_data["price"],
                "price_change": quote_data["change"],
                "price_change_percent": quote_data["change_percent"],
                "volume": quote_data["volume"],
                "data_source": quote_data["source"],
                
                # Individual analysis results
                "technical_analysis": technical_result,
                "news_analysis": news_result,
                "social_analysis": social_result,
                "earnings_analysis": earnings_result,
                "market_analysis": market_result,
                
                # Combined results
                "confidence_score": confidence_data["final_score"],
                "confidence_level": confidence_data["confidence_level"],
                "recommendation": confidence_data["recommendation"],
                "recommendation_strength": confidence_data["strength"],
                
                # Risk assessment
                "risk_assessment": risk_assessment,
                
                # Summary
                "analysis_summary": self._generate_comprehensive_summary(
                    confidence_data, technical_result, news_result, social_result
                ),
                
                # Metadata
                "weights_used": self.weights,
                "component_scores": confidence_data["component_scores"]
            }

            # Convert numpy types to Python native types for JSON serialization and database storage
            result = convert_numpy_types(result)

            # Store in database
            await self._store_analysis_result(db, stock.id, result)

            # Cache result
            await redis_client.cache_with_ttl(cache_key, result, settings.cache_complete_analysis)

            return result
            
        except Exception as e:
            logger.error(f"Complete analysis failed for {symbol}: {e}")
            return self._create_error_result(symbol, f"Analysis error: {str(e)}")
    
    def _calculate_confidence_score(self, analysis_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate weighted confidence score from all components."""
        component_scores = {}
        weighted_scores = {}
        total_weighted_score = 0
        
        for component, weight in self.weights.items():
            if component in analysis_results:
                result = analysis_results[component]
                
                # Extract score based on component type
                if component == "technical":
                    score = result.get("technical_score", 50)
                elif component == "news":
                    score = result.get("news_score", 50)
                elif component == "social":
                    score = result.get("social_score", 50)
                else:
                    score = result.get("score", 50)
                
                component_scores[component] = {
                    "raw_score": score,
                    "weighted_score": score * (weight / 100),
                    "details": result.get("details", {}),
                    "factors": result.get("factors", [])
                }
                weighted_score = score * (weight / 100)
                weighted_scores[component] = weighted_score
                total_weighted_score += weighted_score
        
        # Determine recommendation and confidence level
        recommendation = self._get_final_recommendation(total_weighted_score)
        confidence_level = self._get_final_confidence_level(total_weighted_score, component_scores)
        strength = self._calculate_recommendation_strength(total_weighted_score, component_scores)
        
        return {
            "final_score": round(total_weighted_score, 2),
            "component_scores": component_scores,
            "weighted_scores": weighted_scores,
            "recommendation": recommendation,
            "confidence_level": confidence_level,
            "strength": strength
        }
    
    def _get_final_recommendation(self, score: float) -> str:
        """Get final recommendation based on weighted score."""
        if score >= 75:
            return "STRONG_BUY"
        elif score >= 60:
            return "BUY"
        elif score >= 55:
            return "WEAK_BUY"
        elif score <= 25:
            return "STRONG_SELL"
        elif score <= 40:
            return "SELL"
        elif score <= 45:
            return "WEAK_SELL"
        else:
            return "HOLD"
    
    def _get_final_confidence_level(self, score: float, component_scores: Dict[str, Dict]) -> str:
        """Get confidence level based on score and component agreement."""
        # Check component agreement
        scores = [comp_data["raw_score"] for comp_data in component_scores.values()]
        if len(scores) < 2:
            return "LOW"
        
        # Calculate standard deviation of component scores
        import statistics
        score_std = statistics.stdev(scores) if len(scores) > 1 else 0
        
        # High confidence if extreme score and low deviation
        if (score >= 80 or score <= 20) and score_std < 15:
            return "HIGH"
        elif (score >= 70 or score <= 30) and score_std < 20:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_recommendation_strength(self, score: float, component_scores: Dict[str, Dict]) -> int:
        """Calculate recommendation strength (0-100)."""
        # Base strength on distance from neutral (50)
        distance_from_neutral = abs(score - 50)
        base_strength = min(distance_from_neutral * 2, 100)

        # Adjust for component agreement
        scores = [comp_data["raw_score"] for comp_data in component_scores.values()]
        if len(scores) > 1:
            import statistics
            score_std = statistics.stdev(scores)
            agreement_factor = max(0, 1 - (score_std / 25))  # Reduce strength if high deviation
            base_strength *= agreement_factor
        
        return int(base_strength)
    
    async def _analyze_earnings_impact(self, symbol: str, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze earnings impact (simplified implementation)."""
        # This would typically check earnings calendar and estimate impact
        # For now, return neutral impact
        return {
            "score": 50.0,
            "has_upcoming_earnings": False,
            "earnings_date": None,
            "estimated_impact": "neutral",
            "weight": self.weights["earnings"],
            "weighted_score": 50.0 * (self.weights["earnings"] / 100)
        }
    
    async def _analyze_market_conditions(self, symbol: str, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall market conditions (simplified implementation)."""
        # This would typically check market indices, VIX, etc.
        # For now, return neutral market conditions
        return {
            "score": 50.0,
            "market_trend": "neutral",
            "volatility": "normal",
            "sector_performance": "neutral",
            "weight": self.weights["market"],
            "weighted_score": 50.0 * (self.weights["market"] / 100)
        }

    def _assess_risk(self, quote_data: Dict[str, Any], confidence_data: Dict[str, Any],
                    technical_result: Dict[str, Any]) -> Dict[str, Any]:
        """Assess trading risk and provide position sizing recommendations."""
        current_price = quote_data["price"]
        recommendation = confidence_data["recommendation"]
        confidence_level = confidence_data["confidence_level"]

        # Calculate maximum loss potential
        if "support_resistance" in technical_result.get("indicators", {}):
            support = technical_result["indicators"]["support_resistance"].get("support")
            resistance = technical_result["indicators"]["support_resistance"].get("resistance")
        else:
            support = current_price * 0.9  # 10% below current price
            resistance = current_price * 1.1  # 10% above current price

        # Risk calculations
        downside_risk = ((current_price - support) / current_price * 100) if support else 10
        upside_potential = ((resistance - current_price) / current_price * 100) if resistance else 10
        risk_reward_ratio = upside_potential / downside_risk if downside_risk > 0 else 1

        # Position sizing based on confidence and risk
        if confidence_level == "HIGH":
            max_position_size = 5.0  # 5% of portfolio
        elif confidence_level == "MEDIUM":
            max_position_size = 3.0  # 3% of portfolio
        else:
            max_position_size = 1.0  # 1% of portfolio

        # Adjust for risk level
        if downside_risk > 15:  # High risk
            max_position_size *= 0.5
        elif downside_risk < 5:  # Low risk
            max_position_size *= 1.5

        # Stop loss and take profit levels
        stop_loss = support if support else current_price * 0.95
        take_profit = resistance if resistance else current_price * 1.1

        return {
            "risk_level": "high" if downside_risk > 15 else "medium" if downside_risk > 8 else "low",
            "downside_risk_percent": round(downside_risk, 2),
            "upside_potential_percent": round(upside_potential, 2),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "max_position_size_percent": round(max_position_size, 2),
            "stop_loss_price": round(stop_loss, 2),
            "take_profit_price": round(take_profit, 2),
            "volatility_assessment": self._assess_volatility(quote_data),
            "time_horizon": self._recommend_time_horizon(recommendation, confidence_level)
        }

    def _assess_volatility(self, quote_data: Dict[str, Any]) -> str:
        """Assess stock volatility based on price data."""
        # This would typically use historical volatility calculations
        # For now, use a simple heuristic based on daily change
        change_percent = abs(float(quote_data.get("change_percent", "0").replace("%", "")))

        if change_percent > 5:
            return "high"
        elif change_percent > 2:
            return "medium"
        else:
            return "low"

    def _recommend_time_horizon(self, recommendation: str, confidence_level: str) -> str:
        """Recommend holding time horizon."""
        if recommendation in ["STRONG_BUY", "STRONG_SELL"]:
            if confidence_level == "HIGH":
                return "medium_term"  # 3-6 months
            else:
                return "short_term"   # 1-3 months
        elif recommendation in ["BUY", "SELL"]:
            return "short_term"       # 1-3 months
        else:
            return "very_short_term"  # Days to weeks

    def _generate_comprehensive_summary(self, confidence_data: Dict[str, Any],
                                      technical_result: Dict[str, Any],
                                      news_result: Dict[str, Any],
                                      social_result: Dict[str, Any]) -> str:
        """Generate comprehensive analysis summary."""
        summary_parts = []

        # Overall recommendation
        recommendation = confidence_data["recommendation"]
        score = confidence_data["final_score"]
        confidence_level = confidence_data["confidence_level"]

        summary_parts.append(f"Overall recommendation: {recommendation} with {confidence_level} confidence (score: {score}/100).")

        # Component contributions
        component_scores = confidence_data["component_scores"]

        # Technical analysis summary
        if "technical" in component_scores:
            tech_score = component_scores["technical"]["raw_score"]
            tech_signal = technical_result.get("signals", {}).get("overall_signal", "neutral")
            summary_parts.append(f"Technical analysis shows {tech_signal} signals (score: {tech_score}/100).")

        # News sentiment summary
        if "news" in component_scores:
            news_score = component_scores["news"]["raw_score"]
            news_sentiment = news_result.get("sentiment_analysis", {}).get("overall_sentiment", "neutral")
            summary_parts.append(f"News sentiment is {news_sentiment} (score: {news_score}/100).")

        # Social media summary
        if "social" in component_scores:
            social_score = component_scores["social"]["raw_score"]
            social_sentiment = social_result.get("sentiment_analysis", {}).get("overall_sentiment", "neutral")
            summary_parts.append(f"Social media sentiment is {social_sentiment} (score: {social_score}/100).")

        return " ".join(summary_parts)

    async def _store_analysis_result(self, db: Session, stock_id: int, result: Dict[str, Any]):
        """Store analysis result in database."""
        try:
            # Create analysis result record
            analysis_result = AnalysisResult(
                stock_id=stock_id,
                symbol=result["symbol"],
                analysis_type="stock",
                timestamp=datetime.now(),
                recommendation=result["recommendation"],
                confidence_score=result["confidence_score"],
                technical_score=result.get("technical_analysis", {}).get("technical_score", 50),
                news_sentiment_score=result.get("news_analysis", {}).get("news_score", 50),
                social_sentiment_score=result.get("social_analysis", {}).get("social_score", 50),
                earnings_score=50,  # Default value for now
                market_trend_score=50,  # Default value for now
                risk_level=result["risk_assessment"]["risk_level"]
            )

            db.add(analysis_result)
            db.commit()
            db.refresh(analysis_result)

            # Create confidence score records for each component
            components = result.get("component_scores", {})
            for component_name, score_data in components.items():
                if component_name in self.weights:
                    confidence_score = ConfidenceScore(
                        analysis_result_id=analysis_result.id,
                        component_name=component_name,
                        raw_score=score_data["raw_score"],
                        weighted_score=score_data["weighted_score"],
                        weight=self.weights[component_name],
                        last_updated=datetime.now(),
                        sub_scores=score_data.get("details", {}),
                        contributing_factors=score_data.get("factors", [])
                    )
                    db.add(confidence_score)

            db.commit()

        except Exception as e:
            logger.error(f"Failed to store analysis result: {e}")
            db.rollback()

    def _create_neutral_component(self, component_type: str, error_message: str) -> Dict[str, Any]:
        """Create neutral component result when analysis fails."""
        weight = self.weights.get(component_type, 0)
        return {
            f"{component_type}_score": 50.0,
            "weight": weight,
            "weighted_score": 50.0 * (weight / 100),
            "recommendation": "HOLD",
            "confidence_level": "LOW",
            "error": error_message
        }

    def _create_error_result(self, symbol: str, error_message: str) -> Dict[str, Any]:
        """Create error result when complete analysis fails."""
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "confidence_score": 50.0,
            "confidence_level": "LOW",
            "recommendation": "HOLD",
            "recommendation_strength": 0,
            "analysis_summary": f"Analysis failed: {error_message}",
            "risk_assessment": {
                "risk_level": "unknown",
                "max_position_size_percent": 0.0
            }
        }
