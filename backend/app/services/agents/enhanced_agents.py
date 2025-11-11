"""
BullsBears Enhanced Agents
NewsAgent, RiskAgent, and BearPredictorFundamental for the optimized 8-agent system
Enhanced with Economic Events Integration (Task #1)
"""

import json
import time
import logging
from typing import Dict, List, Any
from .base_agent import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class NewsAgent(BaseAgent):
    """
    Phase 3: Enhanced News Agent - News + Economic Events Analysis (qwen2.5:14b)
    Analyzes news articles, recent events, and cross-references with economic calendar
    Enhanced with Economic Events Integration (Task #1)
    """

    def __init__(self, ollama_client, economic_events_service=None):
        # OPTIMIZED: Use best available local model for complex economic events cross-referencing
        super().__init__("NewsAgent", "qwen2.5:32b", ollama_client)  # Qwen2.5:32b for enhanced reasoning
        self.economic_events_service = economic_events_service
    
    def _get_default_prompt(self) -> str:
        return """You are a financial news analysis specialist. Analyze recent news and events for stock picks to confirm or reject trading signals.

Focus on:
1. Earnings announcements and guidance
2. Product launches and partnerships
3. Regulatory news and legal issues
4. Analyst upgrades/downgrades
5. Management changes and insider activity
6. Sector trends and competitive dynamics

Return JSON with news sentiment analysis:
{
    "news_analysis": [
        {
            "ticker": "TSLA",
            "sentiment": "bullish",
            "confidence": 75,
            "key_events": ["Q4 earnings beat", "FSD beta expansion"],
            "impact_score": 8.2,
            "reasoning": "Strong earnings momentum with positive FSD developments"
        }
    ]
}"""
    
    async def analyze(self, data: Dict[str, Any]) -> AgentResponse:
        start_time = time.time()

        picks = data.get('picks', [])
        news_data = data.get('news_data', {})

        # NEW: Get economic events for the week (Task #1)
        economic_events = {}
        if self.economic_events_service:
            try:
                economic_events = await self.economic_events_service.get_weekly_economic_events()
                logger.info(f"Retrieved {economic_events.get('total_events', 0)} economic events for analysis")
            except Exception as e:
                logger.error(f"Failed to get economic events: {e}")
                economic_events = {}
        
        prompt = f"""
        Analyze recent news AND upcoming economic events for these stock picks:

        Picks to analyze: {json.dumps(picks, indent=2)}

        Recent News Data: {json.dumps(news_data, indent=2)}

        ECONOMIC EVENTS THIS WEEK: {json.dumps(economic_events, indent=2)}

        For each pick, determine:
        1. News sentiment (bullish/bearish/neutral)
        2. Impact confidence (0-100)
        3. Key catalysts or risks
        4. Economic event impact (how upcoming events may affect this stock)
        5. Overall combined impact score (news + economic events)

        CRITICAL: Cross-reference picks with upcoming economic events:
        - CPI data impact on inflation-sensitive stocks
        - Fed meetings impact on rate-sensitive sectors
        - Employment data impact on consumer stocks
        - Earnings calendar conflicts with macro events

        Weight bullish/bearish sentiment based on upcoming events that week.
        Focus on material events that could drive significant price movement.

        Respond with valid JSON only:
        """
        
        response = await self._call_model(prompt, max_tokens=3000)
        parsed = self._parse_json_response(response)
        
        news_analysis = parsed.get('news_analysis', [])
        
        avg_confidence = sum(item.get('confidence', 0) for item in news_analysis) / len(news_analysis) if news_analysis else 0
        
        execution_time = time.time() - start_time
        
        return AgentResponse(
            agent_name=self.name,
            picks=news_analysis,
            confidence=avg_confidence,
            reasoning=f"News analysis completed for {len(news_analysis)} picks",
            execution_time=execution_time,
            model_used=self.model,
            timestamp=time.time()
        )


class RiskAgent(BaseAgent):
    """
    Phase 4B: Risk Agent - Risk Management Specialist (qwen2.5:32b)
    Sets stop-loss and targets based on fibonacci levels and predictor recommendations
    """
    
    def __init__(self, ollama_client):
        super().__init__("RiskAgent", "qwen2.5:32b", ollama_client)  # Production model
    
    def _get_default_prompt(self) -> str:
        return """You are a risk management specialist. Set precise stop-loss and target levels using fibonacci retracements, support/resistance, and volatility analysis.

Focus on:
1. Fibonacci support/resistance levels (23.6%, 38.2%, 50%, 61.8%)
2. Technical support and resistance zones
3. Average True Range (ATR) for volatility adjustment
4. Risk/reward ratios (minimum 1:2)
5. Predictor agent recommendations

Return JSON with risk management levels:
{
    "risk_analysis": [
        {
            "ticker": "TSLA",
            "entry_price": 250.00,
            "stop_loss": 240.00,
            "targets": {
                "target_1": 265.00,
                "target_2": 280.00,
                "target_3": 295.00
            },
            "fibonacci_levels": {
                "support": 245.50,
                "resistance": 285.00
            },
            "risk_reward_ratio": 2.5,
            "position_size": "2%",
            "reasoning": "Fibonacci 38.2% support at 245, resistance at 285"
        }
    ]
}"""
    
    async def analyze(self, data: Dict[str, Any]) -> AgentResponse:
        start_time = time.time()
        
        picks = data.get('picks', [])
        chart_data = data.get('chart_data', {})
        predictor_recommendations = data.get('predictor_recommendations', {})
        
        prompt = f"""
        Set risk management levels for these picks:
        
        Picks: {json.dumps(picks, indent=2)}
        
        Chart Data: {json.dumps(chart_data, indent=2)}
        
        Predictor Recommendations: {json.dumps(predictor_recommendations, indent=2)}
        
        For each pick, calculate:
        1. Optimal entry price range
        2. Stop-loss level (fibonacci/technical support)
        3. Multiple target levels (fibonacci extensions)
        4. Risk/reward ratio validation
        5. Suggested position size
        
        Use fibonacci retracements and extensions for precise levels.
        Ensure minimum 1:2 risk/reward ratio.
        """
        
        response = await self._call_model(prompt, max_tokens=3000)
        parsed = self._parse_json_response(response)
        
        risk_analysis = parsed.get('risk_analysis', [])
        
        avg_risk_reward = sum(item.get('risk_reward_ratio', 0) for item in risk_analysis) / len(risk_analysis) if risk_analysis else 0
        
        execution_time = time.time() - start_time
        
        return AgentResponse(
            agent_name=self.name,
            picks=risk_analysis,
            confidence=min(avg_risk_reward * 20, 100),  # Convert risk/reward to confidence
            reasoning=f"Risk analysis completed for {len(risk_analysis)} picks, avg R:R {avg_risk_reward:.1f}",
            execution_time=execution_time,
            model_used=self.model,
            timestamp=time.time()
        )


class BearPredictorFundamental(BaseAgent):
    """
    Phase 2: Bear Predictor Fundamental - Bearish Fundamental Analysis (deepseek-r1:8b)
    Analyzes fundamental risks: earnings misses, regulatory risks, competitive threats
    """
    
    def __init__(self, ollama_client):
        super().__init__("Bear-Fundamental", "deepseek-r1:8b", ollama_client)  # Production model
    
    def _get_default_prompt(self) -> str:
        return """You are a bearish fundamental analysis specialist. Identify stocks vulnerable to significant downward moves based on fundamental risks.

Focus on:
1. Earnings misses and guidance cuts
2. Revenue decline and margin compression
3. Regulatory risks and legal issues
4. Competitive threats and market share loss
5. Management issues and insider selling
6. Sector headwinds and macro risks
7. High valuation with deteriorating fundamentals

Return JSON with bearish fundamental picks:
{
    "picks": [
        {
            "ticker": "NFLX",
            "confidence": 78,
            "reasoning": "Subscriber growth slowing, increased competition, high valuation",
            "target_range": {"low": 180, "high": 200},
            "timeframe": "2-4 weeks",
            "key_risks": ["competition", "valuation", "growth_slowdown"],
            "catalyst": "Q4 subscriber miss likely"
        }
    ]
}"""
    
    async def analyze(self, data: Dict[str, Any]) -> AgentResponse:
        start_time = time.time()
        
        candidates = data.get('candidates', [])
        earnings_data = data.get('earnings', {})
        news_data = data.get('news', {})
        
        prompt = f"""
        Analyze these stocks for BEARISH fundamental risks:
        
        Candidates: {json.dumps(candidates[:20], indent=2)}
        
        Earnings Data: {json.dumps(earnings_data, indent=2)}
        
        News Data: {json.dumps(news_data, indent=2)}
        
        Look for:
        1. Earnings disappointments and guidance cuts
        2. Regulatory pressures and legal risks
        3. Competitive threats and market disruption
        4. Management issues and corporate governance
        5. Sector headwinds and macro pressures
        6. Overvaluation with deteriorating metrics
        
        Only recommend picks with >70% confidence based on fundamental risks.
        """
        
        response = await self._call_model(prompt, max_tokens=2000)
        parsed = self._parse_json_response(response)
        
        picks = self._validate_picks(parsed.get('picks', []))
        high_confidence_picks = [p for p in picks if p['confidence'] >= 70]
        
        avg_confidence = sum(p['confidence'] for p in high_confidence_picks) / len(high_confidence_picks) if high_confidence_picks else 0
        
        execution_time = time.time() - start_time
        
        return AgentResponse(
            agent_name=self.name,
            picks=high_confidence_picks,
            confidence=avg_confidence,
            reasoning=f"Fundamental analysis identified {len(high_confidence_picks)} bearish risks",
            execution_time=execution_time,
            model_used=self.model,
            timestamp=time.time()
        )
