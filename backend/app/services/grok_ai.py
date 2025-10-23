"""
Grok AI integration for final recommendation validation and analysis.
Uses xAI's Grok API to provide intelligent analysis and risk warnings.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp
import json
from dataclasses import dataclass

from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class GrokAnalysis:
    """Data class for Grok AI analysis results."""
    recommendation: str  # BUY, SELL, HOLD
    confidence: float    # 0-100
    reasoning: str
    risk_warning: Optional[str]
    summary: str
    key_factors: List[str]
    contrarian_view: Optional[str]

class GrokAIService:
    """Service for Grok AI analysis and validation."""
    
    def __init__(self):
        self.api_key = settings.grok_api_key
        self.base_url = "https://api.x.ai/v1"
        self.session = None
        
        if not self.api_key:
            logger.warning("Grok API key not configured")
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.api_key:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def analyze_option_play(self, 
                                symbol: str,
                                technical_data: Dict[str, Any],
                                news_data: Dict[str, Any],
                                polymarket_data: List[Dict[str, Any]],
                                catalyst_data: Dict[str, Any],
                                unusual_volume_data: Dict[str, Any],
                                confidence_score: float) -> Optional[GrokAnalysis]:
        """
        Get Grok AI analysis of the complete option play data.
        
        Args:
            symbol: Stock symbol
            technical_data: Technical analysis results
            news_data: News sentiment analysis
            polymarket_data: Prediction market data
            catalyst_data: Upcoming catalysts
            unusual_volume_data: Unusual volume analysis
            confidence_score: Current confidence score
            
        Returns:
            GrokAnalysis object with AI recommendations
        """
        if not self.api_key:
            logger.warning("Grok API key not available")
            return None
        
        try:
            if not self.session:
                async with self:
                    return await self._perform_analysis(
                        symbol, technical_data, news_data, polymarket_data,
                        catalyst_data, unusual_volume_data, confidence_score
                    )
            else:
                return await self._perform_analysis(
                    symbol, technical_data, news_data, polymarket_data,
                    catalyst_data, unusual_volume_data, confidence_score
                )
                
        except Exception as e:
            logger.error(f"Error in Grok AI analysis: {e}")
            return None
    
    async def _perform_analysis(self, symbol: str, technical_data: Dict, news_data: Dict,
                              polymarket_data: List[Dict], catalyst_data: Dict,
                              unusual_volume_data: Dict, confidence_score: float) -> Optional[GrokAnalysis]:
        """Perform the actual AI analysis."""
        
        # Prepare the analysis prompt
        prompt = self._build_analysis_prompt(
            symbol, technical_data, news_data, polymarket_data,
            catalyst_data, unusual_volume_data, confidence_score
        )
        
        try:
            # Make API call to Grok
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert options trading analyst with deep knowledge of technical analysis, market sentiment, and risk management. Provide concise, actionable analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "model": "grok-beta",
                "stream": False,
                "temperature": 0.3  # Lower temperature for more consistent analysis
            }
            
            async with self.session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return self._parse_grok_response(result)
                else:
                    error_text = await response.text()
                    logger.error(f"Grok API error {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error calling Grok API: {e}")
            return None
    
    def _build_analysis_prompt(self, symbol: str, technical_data: Dict, news_data: Dict,
                             polymarket_data: List[Dict], catalyst_data: Dict,
                             unusual_volume_data: Dict, confidence_score: float) -> str:
        """Build the analysis prompt for Grok AI."""
        
        prompt = f"""
Analyze this options trading opportunity for {symbol} and provide your expert assessment:

CURRENT CONFIDENCE SCORE: {confidence_score:.1f}%

TECHNICAL ANALYSIS:
{self._format_technical_data(technical_data)}

NEWS SENTIMENT:
{self._format_news_data(news_data)}

PREDICTION MARKETS (High Probability Events):
{self._format_polymarket_data(polymarket_data)}

UPCOMING CATALYSTS:
{self._format_catalyst_data(catalyst_data)}

UNUSUAL VOLUME ACTIVITY:
{self._format_volume_data(unusual_volume_data)}

Please provide your analysis in this exact JSON format:
{{
    "recommendation": "BUY|SELL|HOLD",
    "confidence": 0-100,
    "reasoning": "Brief explanation of your recommendation",
    "risk_warning": "Any significant risks to highlight (null if none)",
    "summary": "2-3 sentence summary for quick decision making",
    "key_factors": ["factor1", "factor2", "factor3"],
    "contrarian_view": "What could go wrong with this trade (null if low risk)"
}}

Focus on:
1. Whether the {confidence_score:.1f}% confidence score is justified
2. Key risks that might not be captured in the data
3. Timing considerations for options (1-30 day timeframe)
4. Any red flags or exceptional opportunities
"""
        return prompt
    
    def _format_technical_data(self, data: Dict) -> str:
        """Format technical analysis data for the prompt."""
        if not data or 'indicators' not in data:
            return "No technical data available"
        
        indicators = data['indicators']
        lines = []
        
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            lines.append(f"RSI: {rsi:.1f} ({'Oversold' if rsi < 30 else 'Overbought' if rsi > 70 else 'Neutral'})")
        
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            signal = indicators['macd_signal']
            trend = "Bullish" if macd > signal else "Bearish"
            lines.append(f"MACD: {trend} (MACD: {macd:.3f}, Signal: {signal:.3f})")
        
        if 'sma_20' in indicators and 'sma_50' in indicators:
            sma20 = indicators['sma_20']
            sma50 = indicators['sma_50']
            trend = "Bullish" if sma20 > sma50 else "Bearish"
            lines.append(f"Moving Averages: {trend} (20-day: ${sma20:.2f}, 50-day: ${sma50:.2f})")
        
        return "\n".join(lines) if lines else "Limited technical indicators available"
    
    def _format_news_data(self, data: Dict) -> str:
        """Format news sentiment data for the prompt."""
        if not data:
            return "No news data available"
        
        sentiment = data.get('compound_score', 0)
        article_count = data.get('article_count', 0)
        
        sentiment_label = "Positive" if sentiment > 0.1 else "Negative" if sentiment < -0.1 else "Neutral"
        
        return f"Sentiment: {sentiment_label} (Score: {sentiment:.2f}, Articles: {article_count})"
    
    def _format_polymarket_data(self, data: List[Dict]) -> str:
        """Format Polymarket prediction data for the prompt."""
        if not data:
            return "No high-probability prediction market events found"
        
        lines = []
        for event in data[:3]:  # Top 3 events
            prob = event.get('probability', 0) * 100
            question = event.get('question', 'Unknown')
            impact = event.get('impact_level', 'UNKNOWN')
            lines.append(f"• {question} ({prob:.0f}% probability, {impact} impact)")
        
        return "\n".join(lines)
    
    def _format_catalyst_data(self, data: Dict) -> str:
        """Format catalyst data for the prompt."""
        if not data or 'catalysts' not in data:
            return "No major catalysts identified in next 7 days"
        
        catalysts = data['catalysts']
        if not catalysts:
            return "No major catalysts identified in next 7 days"
        
        lines = []
        for catalyst in catalysts[:3]:  # Top 3 catalysts
            date = catalyst.get('date', 'Unknown')
            event_type = catalyst.get('type', 'Unknown')
            description = catalyst.get('description', 'No description')
            impact = catalyst.get('impact_score', 0)
            lines.append(f"• {date}: {event_type} - {description} (Impact: {impact:.1f})")
        
        return "\n".join(lines)
    
    def _format_volume_data(self, data: Dict) -> str:
        """Format unusual volume data for the prompt."""
        if not data:
            return "No unusual volume activity detected"
        
        lines = []
        
        if 'options_volume_ratio' in data:
            ratio = data['options_volume_ratio']
            if ratio >= 5.0:
                lines.append(f"Options volume {ratio:.1f}x above average")
        
        if 'dark_pool_activity' in data:
            dark_pool = data['dark_pool_activity']
            if dark_pool.get('unusual', False):
                lines.append(f"Unusual dark pool activity detected")
        
        if 'block_trades' in data:
            blocks = data['block_trades']
            if blocks:
                lines.append(f"{len(blocks)} large block trades detected")
        
        return "\n".join(lines) if lines else "Normal volume patterns"
    
    def _parse_grok_response(self, response: Dict) -> Optional[GrokAnalysis]:
        """Parse Grok AI response into structured data."""
        try:
            content = response['choices'][0]['message']['content']
            
            # Try to extract JSON from the response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.error("No JSON found in Grok response")
                return None
            
            json_str = content[start_idx:end_idx]
            analysis_data = json.loads(json_str)
            
            return GrokAnalysis(
                recommendation=analysis_data.get('recommendation', 'HOLD'),
                confidence=float(analysis_data.get('confidence', 0)),
                reasoning=analysis_data.get('reasoning', ''),
                risk_warning=analysis_data.get('risk_warning'),
                summary=analysis_data.get('summary', ''),
                key_factors=analysis_data.get('key_factors', []),
                contrarian_view=analysis_data.get('contrarian_view')
            )
            
        except Exception as e:
            logger.error(f"Error parsing Grok response: {e}")
            return None

# Utility function for easy usage
async def get_ai_analysis(symbol: str, all_data: Dict) -> Optional[GrokAnalysis]:
    """Convenience function to get AI analysis."""
    async with GrokAIService() as service:
        return await service.analyze_option_play(
            symbol=symbol,
            technical_data=all_data.get('technical', {}),
            news_data=all_data.get('news', {}),
            polymarket_data=all_data.get('polymarket', []),
            catalyst_data=all_data.get('catalysts', {}),
            unusual_volume_data=all_data.get('volume', {}),
            confidence_score=all_data.get('confidence_score', 0)
        )
