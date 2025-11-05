"""
Enhanced Economic Events Analyzer - Combines SEC, FRED, and BLS data sources.

This service integrates data from:
- SEC API: Insider trades, institutional holdings, material events
- FRED API: Federal Reserve economic data
- BLS API: Bureau of Labor Statistics data

Computes unified impact scores and features for the ML model.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json

from .sec_data_service import SECDataService
from .fred_data_service import FREDDataService
from .bls_data_service import BLSDataService
from ..core.redis_client import redis_client

logger = logging.getLogger(__name__)


@dataclass
class EconomicImpactAnalysis:
    """Comprehensive economic impact analysis for a stock."""
    ticker: str
    timestamp: datetime
    
    # Overall scores (-1.0 to 1.0)
    overall_economic_score: float
    insider_sentiment_score: float
    institutional_flow_score: float
    macro_economic_score: float
    
    # Confidence levels (0.0 to 1.0)
    overall_confidence: float
    
    # Supporting data
    insider_analysis: Dict[str, Any]
    institutional_analysis: Dict[str, Any]
    macro_analysis: Dict[str, Any]
    material_events: List[Dict[str, Any]]
    
    # Risk factors and catalysts
    risk_factors: List[str]
    bullish_catalysts: List[str]
    bearish_catalysts: List[str]


class EnhancedEconomicEventsAnalyzer:
    """Enhanced analyzer combining SEC, FRED, and BLS data sources."""
    
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache for combined analysis
        
        # Weighting factors for different data sources
        self.weights = {
            "insider_sentiment": 0.35,      # 35% - Direct company insider activity
            "institutional_flow": 0.25,     # 25% - Institutional money flow
            "macro_economic": 0.25,         # 25% - Broader economic conditions
            "material_events": 0.15         # 15% - Company-specific events
        }
    
    async def analyze_stock_economic_impact(
        self, 
        ticker: str,
        use_cache: bool = True
    ) -> EconomicImpactAnalysis:
        """
        Perform comprehensive economic impact analysis for a stock.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data
            
        Returns:
            EconomicImpactAnalysis object
        """
        cache_key = f"enhanced_economic_analysis:{ticker}"
        
        # Check cache first
        if use_cache:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                try:
                    data = json.loads(cached_data)
                    # Convert timestamp back to datetime
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    return EconomicImpactAnalysis(**data)
                except Exception as e:
                    logger.warning(f"Failed to parse cached economic analysis: {e}")
        
        # Perform analysis using all data sources
        async with SECDataService() as sec_service, \
                   FREDDataService() as fred_service, \
                   BLSDataService() as bls_service:
            
            # Fetch data in parallel
            tasks = [
                self._analyze_insider_sentiment(sec_service, ticker),
                self._analyze_institutional_flow(sec_service, ticker),
                self._analyze_macro_economic_conditions(fred_service, bls_service),
                self._analyze_material_events(sec_service, ticker)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            insider_analysis = results[0] if not isinstance(results[0], Exception) else {}
            institutional_analysis = results[1] if not isinstance(results[1], Exception) else {}
            macro_analysis = results[2] if not isinstance(results[2], Exception) else {}
            material_events = results[3] if not isinstance(results[3], Exception) else []
            
            # Calculate weighted overall score
            insider_score = insider_analysis.get("sentiment_score", 0.0)
            institutional_score = institutional_analysis.get("flow_score", 0.0)
            macro_score = macro_analysis.get("market_sentiment_score", 0.0)
            events_score = self._calculate_events_score(material_events)
            
            overall_score = (
                insider_score * self.weights["insider_sentiment"] +
                institutional_score * self.weights["institutional_flow"] +
                macro_score * self.weights["macro_economic"] +
                events_score * self.weights["material_events"]
            )
            
            # Calculate overall confidence
            confidences = [
                insider_analysis.get("confidence", 0.0),
                institutional_analysis.get("confidence", 0.0),
                macro_analysis.get("confidence", 0.0),
                0.8 if material_events else 0.0  # High confidence in SEC events data
            ]
            overall_confidence = sum(confidences) / len(confidences)
            
            # Generate risk factors and catalysts
            risk_factors, bullish_catalysts, bearish_catalysts = self._generate_catalysts_and_risks(
                insider_analysis, institutional_analysis, macro_analysis, material_events
            )
            
            # Create analysis result
            analysis = EconomicImpactAnalysis(
                ticker=ticker,
                timestamp=datetime.now(),
                overall_economic_score=round(overall_score, 3),
                insider_sentiment_score=round(insider_score, 3),
                institutional_flow_score=round(institutional_score, 3),
                macro_economic_score=round(macro_score, 3),
                overall_confidence=round(overall_confidence, 3),
                insider_analysis=insider_analysis,
                institutional_analysis=institutional_analysis,
                macro_analysis=macro_analysis,
                material_events=material_events,
                risk_factors=risk_factors,
                bullish_catalysts=bullish_catalysts,
                bearish_catalysts=bearish_catalysts
            )
            
            # Cache the result
            if use_cache:
                # Convert to dict for caching
                analysis_dict = analysis.__dict__.copy()
                analysis_dict["timestamp"] = analysis.timestamp.isoformat()
                
                await redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(analysis_dict)
                )
            
            return analysis
    
    async def _analyze_insider_sentiment(
        self, 
        sec_service: SECDataService, 
        ticker: str
    ) -> Dict[str, Any]:
        """Analyze insider trading sentiment."""
        try:
            return await sec_service.get_insider_sentiment_score(ticker, days_back=90)
        except Exception as e:
            logger.error(f"Failed to analyze insider sentiment for {ticker}: {e}")
            return {"sentiment_score": 0.0, "confidence": 0.0}
    
    async def _analyze_institutional_flow(
        self, 
        sec_service: SECDataService, 
        ticker: str
    ) -> Dict[str, Any]:
        """Analyze institutional money flow."""
        try:
            return await sec_service.get_institutional_flow_score(ticker)
        except Exception as e:
            logger.error(f"Failed to analyze institutional flow for {ticker}: {e}")
            return {"flow_score": 0.0, "confidence": 0.0}
    
    async def _analyze_macro_economic_conditions(
        self, 
        fred_service: FREDDataService, 
        bls_service: BLSDataService
    ) -> Dict[str, Any]:
        """Analyze macro economic conditions."""
        try:
            # Get economic snapshots
            fred_snapshot = await fred_service.get_economic_snapshot()
            bls_inflation = await bls_service.get_inflation_impact_score()
            
            # Combine FRED and BLS analysis
            fred_sentiment = fred_snapshot.get("market_sentiment", "Neutral")
            bls_impact = bls_inflation.get("impact_score", 0.0)
            
            # Convert sentiment to score
            sentiment_score = 0.0
            if fred_sentiment == "Bullish":
                sentiment_score = 0.3
            elif fred_sentiment == "Bearish":
                sentiment_score = -0.3
            
            # Combine with BLS impact
            combined_score = (sentiment_score + bls_impact) / 2
            
            return {
                "market_sentiment_score": combined_score,
                "confidence": 0.7,
                "fred_data": fred_snapshot,
                "bls_data": bls_inflation
            }
        except Exception as e:
            logger.error(f"Failed to analyze macro economic conditions: {e}")
            return {"market_sentiment_score": 0.0, "confidence": 0.0}
    
    async def _analyze_material_events(
        self, 
        sec_service: SECDataService, 
        ticker: str
    ) -> List[Dict[str, Any]]:
        """Analyze material events from SEC filings."""
        try:
            events = await sec_service.get_material_events(ticker, days_back=30)
            return [
                {
                    "event_type": event.event_type,
                    "description": event.event_description,
                    "impact_score": event.impact_score,
                    "date": event.event_date.isoformat()
                }
                for event in events
            ]
        except Exception as e:
            logger.error(f"Failed to analyze material events for {ticker}: {e}")
            return []
    
    def _calculate_events_score(self, events: List[Dict[str, Any]]) -> float:
        """Calculate overall score from material events."""
        if not events:
            return 0.0
        
        # Weight recent events more heavily
        total_score = 0.0
        total_weight = 0.0
        
        for event in events:
            try:
                event_date = datetime.fromisoformat(event["date"])
                days_ago = (datetime.now() - event_date).days
                
                # Weight decreases with age (max 30 days)
                weight = max(0.1, 1.0 - (days_ago / 30.0))
                
                impact_score = event.get("impact_score", 0.0)
                total_score += impact_score * weight
                total_weight += weight
            except Exception as e:
                logger.warning(f"Failed to process event: {e}")
                continue
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _generate_catalysts_and_risks(
        self,
        insider_analysis: Dict[str, Any],
        institutional_analysis: Dict[str, Any],
        macro_analysis: Dict[str, Any],
        material_events: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate risk factors and catalysts based on analysis."""
        risk_factors = []
        bullish_catalysts = []
        bearish_catalysts = []
        
        # Insider trading analysis
        insider_sentiment = insider_analysis.get("sentiment_score", 0.0)
        insider_activity = insider_analysis.get("insider_activity", "None")
        
        if insider_sentiment > 0.3:
            bullish_catalysts.append(f"Strong insider buying activity ({insider_activity})")
        elif insider_sentiment < -0.3:
            bearish_catalysts.append(f"Heavy insider selling activity ({insider_activity})")
        
        # Institutional flow analysis
        institutional_score = institutional_analysis.get("flow_score", 0.0)
        institutional_interest = institutional_analysis.get("institutional_interest", "None")
        
        if institutional_score > 0.2:
            bullish_catalysts.append(f"High institutional interest ({institutional_interest})")
        elif institutional_score < -0.2:
            bearish_catalysts.append(f"Low institutional interest ({institutional_interest})")
        
        # Macro economic analysis
        macro_score = macro_analysis.get("market_sentiment_score", 0.0)
        if "bls_data" in macro_analysis:
            inflation_impact = macro_analysis["bls_data"].get("market_impact", "Neutral")
            if inflation_impact == "Bearish":
                risk_factors.append("High inflation environment pressuring valuations")
            elif inflation_impact == "Bullish":
                bullish_catalysts.append("Favorable inflation environment")
        
        # Material events
        for event in material_events:
            impact_score = event.get("impact_score", 0.0)
            description = event.get("description", "")
            
            if impact_score > 0.3:
                bullish_catalysts.append(f"Recent positive event: {description}")
            elif impact_score < -0.3:
                bearish_catalysts.append(f"Recent negative event: {description}")
        
        # General risk factors
        if len(material_events) > 3:
            risk_factors.append("High frequency of material events indicating volatility")
        
        return risk_factors, bullish_catalysts, bearish_catalysts
    
    async def get_economic_features_for_ml(self, ticker: str) -> Dict[str, float]:
        """
        Get economic features formatted for ML model integration.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict of feature names to values for ML model
        """
        analysis = await self.analyze_stock_economic_impact(ticker)
        
        return {
            "economic_overall_score": analysis.overall_economic_score,
            "economic_insider_sentiment": analysis.insider_sentiment_score,
            "economic_institutional_flow": analysis.institutional_flow_score,
            "economic_macro_score": analysis.macro_economic_score,
            "economic_confidence": analysis.overall_confidence,
            "economic_risk_factor_count": len(analysis.risk_factors),
            "economic_bullish_catalyst_count": len(analysis.bullish_catalysts),
            "economic_bearish_catalyst_count": len(analysis.bearish_catalysts)
        }
