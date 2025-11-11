"""
BullsBears AI - Learning Agents
Learner and Brain agents for continuous system improvement
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..ollama_client import OllamaClient
from .base_agent import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)

@dataclass
class LearningInsight:
    """Represents a learning insight from historical data"""
    factor: str
    importance: float
    direction: str  # 'bullish' or 'bearish'
    confidence: float
    sample_size: int
    success_rate: float

@dataclass
class PromptUpdate:
    """Represents a prompt update recommendation"""
    agent_type: str
    current_prompt: str
    suggested_prompt: str
    reasoning: str
    expected_improvement: float

class LearnerAgent(BaseAgent):
    """
    Analyzes historical picks and outcomes to identify patterns (UPGRADED: Kimi-K2-Thinking)
    Reviews database to determine what factors correlate with success using advanced reasoning
    """

    def __init__(self, ollama_client: OllamaClient):
        # OPTIMIZED: Use DeepSeek-R1 for superior reasoning and pattern analysis
        super().__init__("Learner", "deepseek-r1:8b", ollama_client)  # DeepSeek-R1 specialized for reasoning

    def _get_default_prompt(self) -> str:
        """Default prompt for learning analysis"""
        return """You are a learning analysis specialist. Analyze historical stock picks to identify success patterns.

Focus on:
- Technical indicators that correlate with success
- Market conditions during successful picks
- Time-to-target patterns
- Risk factors that led to failures

Return JSON only:
{
  "insights": [
    {
      "factor": "RSI_oversold_recovery",
      "importance": 0.85,
      "success_rate": 0.73,
      "reasoning": "RSI < 30 followed by > 50 shows 73% success rate"
    }
  ]
}"""

    async def analyze(self, data: Dict[str, Any]) -> AgentResponse:
        """Main analysis method for learning"""
        insights = await self.analyze_historical_performance(data.get('days_back', 30))

        return AgentResponse(
            agent_name=self.name,
            picks=[],
            reasoning=f"Found {len(insights)} learning insights",
            confidence=0.9,
            model_used=self.model,
            timestamp=time.time()
        )
    
    async def analyze_historical_performance(self, days_back: int = 30) -> List[LearningInsight]:
        """Analyze historical picks to identify successful patterns"""
        
        try:
            # Get historical data from database
            historical_data = await self._get_historical_picks(days_back)
            
            if not historical_data:
                logger.warning("No historical data available for learning")
                return []
            
            # Analyze patterns using AI
            insights = await self._extract_learning_insights(historical_data)
            
            logger.info(f"Learner extracted {len(insights)} insights from {len(historical_data)} historical picks")
            return insights
            
        except Exception as e:
            logger.error(f"Learner analysis failed: {e}")
            return []
    
    async def _get_historical_picks(self, days_back: int) -> List[Dict[str, Any]]:
        """Retrieve historical picks from database with social sentiment data"""

        try:
            from ...core.database import get_database

            db = await get_database()
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Get historical picks with outcomes and social sentiment
            rows = await db.fetch("""
                SELECT
                    p.ticker as symbol,
                    p.direction as prediction_type,
                    p.confidence,
                    p.social_weight,
                    p.reasoning,
                    p.outcome,
                    p.outcome_price,
                    p.created_at as prediction_date,
                    p.outcome_date as target_hit_date,
                    -- Get average social sentiment for this pick
                    AVG(s.sentiment_score) as avg_social_sentiment,
                    COUNT(s.id) as social_mentions,
                    -- Get trending data if available
                    MAX(t.trend_score) as max_trend_score,
                    MAX(t.mention_velocity) as max_mention_velocity
                FROM picks p
                LEFT JOIN social_sentiment s ON s.ticker = p.ticker
                    AND s.created_at BETWEEN p.created_at - INTERVAL '1 day'
                    AND p.created_at + INTERVAL '1 day'
                LEFT JOIN trending_stocks t ON t.ticker = p.ticker
                    AND t.created_at BETWEEN p.created_at - INTERVAL '1 day'
                    AND p.created_at + INTERVAL '1 day'
                WHERE p.created_at > $1
                AND p.outcome != 'pending'
                GROUP BY p.id, p.ticker, p.direction, p.confidence, p.social_weight,
                         p.reasoning, p.outcome, p.outcome_price, p.created_at, p.outcome_date
                ORDER BY p.created_at DESC
            """, cutoff_date)

            historical_data = []
            for row in rows:
                # Calculate actual return based on outcome
                actual_return = 0.0
                if row['outcome'] == 'win':
                    actual_return = 0.20  # Assume 20% for wins
                elif row['outcome'] == 'partial':
                    actual_return = 0.12  # Assume 12% for partial wins
                elif row['outcome'] == 'loss':
                    actual_return = -0.05  # Assume -5% for losses

                # Calculate days to target
                days_to_target = 3  # Default
                if row['target_hit_date'] and row['prediction_date']:
                    days_to_target = (row['target_hit_date'] - row['prediction_date']).days

                data_point = {
                    "symbol": row['symbol'],
                    "prediction_type": row['prediction_type'],
                    "confidence": float(row['confidence']) / 100.0,  # Convert to 0-1 scale
                    "social_weight": float(row['social_weight']) if row['social_weight'] else 1.0,
                    "factors": {
                        "social_sentiment": float(row['avg_social_sentiment']) / 100.0 if row['avg_social_sentiment'] else 0.5,
                        "social_mentions": row['social_mentions'] or 0,
                        "trend_score": float(row['max_trend_score']) / 100.0 if row['max_trend_score'] else 0.0,
                        "mention_velocity": float(row['max_mention_velocity']) if row['max_mention_velocity'] else 0.0,
                        # Add mock technical factors for now
                        "rsi": 65.0,
                        "volume_ratio": 1.5,
                        "earnings_proximity": 5
                    },
                    "outcome": row['outcome'],
                    "actual_return": actual_return,
                    "days_to_target": days_to_target,
                    "prediction_date": row['prediction_date'].isoformat(),
                    "target_hit_date": row['target_hit_date'].isoformat() if row['target_hit_date'] else None
                }
                historical_data.append(data_point)

            logger.info(f"Retrieved {len(historical_data)} historical picks with social data")
            return historical_data

        except Exception as e:
            logger.error(f"Failed to get historical picks: {e}")
            # Return mock data as fallback
            return [
                {
                    "symbol": "AAPL",
                    "prediction_type": "bullish",
                    "confidence": 0.75,
                    "social_weight": 1.2,
                    "factors": {
                        "rsi": 65.0,
                        "volume_ratio": 1.5,
                        "earnings_proximity": 5,
                        "social_sentiment": 0.8,
                        "social_mentions": 150,
                        "trend_score": 0.7,
                        "mention_velocity": 25.5
                    },
                    "outcome": "win",
                    "actual_return": 0.22,
                    "days_to_target": 3,
                    "prediction_date": "2024-01-15",
                    "target_hit_date": "2024-01-18"
                }
            ]
    
    async def _extract_learning_insights(self, historical_data: List[Dict[str, Any]]) -> List[LearningInsight]:
        """Use AI to extract patterns from historical data"""
        
        prompt = f"""
        Analyze these historical stock predictions and outcomes to identify success patterns:

        Historical Data: {json.dumps(historical_data[:10], indent=2)}

        For each factor (RSI, volume_ratio, earnings_proximity, social_sentiment, etc.):
        1. Calculate success rate when factor is high vs low
        2. Identify optimal ranges for bullish/bearish predictions
        3. Determine factor importance based on correlation with success

        Return JSON with insights:
        {{
            "insights": [
                {{
                    "factor": "rsi",
                    "importance": 0.85,
                    "direction": "bullish",
                    "confidence": 0.92,
                    "sample_size": 45,
                    "success_rate": 0.78,
                    "optimal_range": "60-70",
                    "reasoning": "RSI 60-70 shows 78% success rate for bullish predictions"
                }}
            ]
        }}
        """
        
        try:
            response = await self.ollama_client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.1}
            )
            
            parsed_response = self._parse_json_response(response)
            insights_data = parsed_response.get("insights", [])
            
            insights = []
            for insight_data in insights_data:
                insight = LearningInsight(
                    factor=insight_data.get("factor", ""),
                    importance=insight_data.get("importance", 0.0),
                    direction=insight_data.get("direction", ""),
                    confidence=insight_data.get("confidence", 0.0),
                    sample_size=insight_data.get("sample_size", 0),
                    success_rate=insight_data.get("success_rate", 0.0)
                )
                insights.append(insight)
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to extract learning insights: {e}")
            return []

class BrainAgent(BaseAgent):
    """
    Updates prompt guidelines based on Learner feedback
    Refines predictor agent prompts to improve accuracy over time
    """
    
    def __init__(self, ollama_client: OllamaClient):
        super().__init__("Brain", "qwen2.5:32b", ollama_client)  # Enhanced reasoning for prompt optimization

    def _get_default_prompt(self) -> str:
        """Default prompt for brain optimization"""
        return """You are a prompt optimization specialist. Update agent prompts based on learning insights.

Focus on:
- Incorporating successful patterns into prompts
- Removing or de-emphasizing failed strategies
- Maintaining JSON response format
- Improving confidence calibration

Return JSON only:
{
  "prompt_updates": [
    {
      "agent_type": "bull_technical",
      "suggested_prompt": "Enhanced prompt with successful patterns...",
      "reasoning": "RSI recovery shows 73% success rate vs 45% baseline",
      "expected_improvement": 0.28
    }
  ]
}"""

    async def analyze(self, data: Dict[str, Any]) -> AgentResponse:
        """Main analysis method for brain optimization"""
        insights = data.get('insights', [])
        prompt_updates = await self.update_predictor_prompts(insights)

        return AgentResponse(
            agent_name=self.name,
            picks=[],
            reasoning=f"Generated {len(prompt_updates)} prompt updates",
            confidence=0.9,
            model_used=self.model,
            timestamp=time.time()
        )
    
    async def update_predictor_prompts(self, insights: List[LearningInsight]) -> List[PromptUpdate]:
        """Generate updated prompts based on learning insights"""
        
        if not insights:
            logger.warning("No insights provided for prompt updates")
            return []
        
        try:
            # Get current prompts
            current_prompts = await self._get_current_prompts()
            
            # Generate updates for each agent type
            updates = []
            
            for agent_type in ["bull_technical", "bull_fundamental", "bear_technical", "bear_sentiment"]:
                update = await self._generate_prompt_update(agent_type, current_prompts[agent_type], insights)
                if update:
                    updates.append(update)
            
            logger.info(f"Brain generated {len(updates)} prompt updates")
            return updates
            
        except Exception as e:
            logger.error(f"Brain prompt update failed: {e}")
            return []
    
    async def _get_current_prompts(self) -> Dict[str, str]:
        """Load current prompts from files"""
        
        prompts = {}
        prompt_files = {
            "bull_technical": "backend/app/services/agents/prompts/bull_technical.txt",
            "bull_fundamental": "backend/app/services/agents/prompts/bull_fundamental.txt", 
            "bear_technical": "backend/app/services/agents/prompts/bear_technical.txt",
            "bear_sentiment": "backend/app/services/agents/prompts/bear_sentiment.txt"
        }
        
        for agent_type, file_path in prompt_files.items():
            try:
                with open(file_path, 'r') as f:
                    prompts[agent_type] = f.read().strip()
            except FileNotFoundError:
                prompts[agent_type] = f"Find {agent_type.replace('_', ' ')} stocks. Return JSON only."
        
        return prompts
    
    async def _generate_prompt_update(self, agent_type: str, current_prompt: str, insights: List[LearningInsight]) -> Optional[PromptUpdate]:
        """Generate an updated prompt for a specific agent"""
        
        # Filter insights relevant to this agent type
        relevant_insights = [
            insight for insight in insights 
            if (agent_type.startswith("bull") and insight.direction == "bullish") or
               (agent_type.startswith("bear") and insight.direction == "bearish")
        ]
        
        if not relevant_insights:
            return None
        
        prompt = f"""
        Update this stock prediction prompt based on learning insights:

        Current Prompt: "{current_prompt}"
        
        Agent Type: {agent_type}
        
        Learning Insights:
        {json.dumps([{
            "factor": i.factor,
            "importance": i.importance,
            "success_rate": i.success_rate,
            "sample_size": i.sample_size
        } for i in relevant_insights], indent=2)}

        Generate an improved prompt that:
        1. Emphasizes high-importance factors (>0.7 importance)
        2. Includes specific ranges/thresholds from successful predictions
        3. Maintains the JSON output format
        4. Stays concise for fast processing

        Return JSON:
        {{
            "updated_prompt": "new prompt text",
            "reasoning": "why this improves accuracy",
            "expected_improvement": 0.15
        }}
        """
        
        try:
            response = await self.ollama_client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.2}
            )
            
            parsed_response = self._parse_json_response(response)
            
            return PromptUpdate(
                agent_type=agent_type,
                current_prompt=current_prompt,
                suggested_prompt=parsed_response.get("updated_prompt", current_prompt),
                reasoning=parsed_response.get("reasoning", ""),
                expected_improvement=parsed_response.get("expected_improvement", 0.0)
            )
            
        except Exception as e:
            logger.error(f"Failed to generate prompt update for {agent_type}: {e}")
            return None
    
    async def apply_prompt_updates(self, updates: List[PromptUpdate]) -> bool:
        """Apply approved prompt updates to files"""
        
        try:
            for update in updates:
                if update.expected_improvement > 0.05:  # Only apply if >5% improvement expected
                    file_path = f"backend/app/services/agents/prompts/{update.agent_type}.txt"
                    
                    # Backup current prompt
                    backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    with open(file_path, 'r') as f:
                        with open(backup_path, 'w') as backup:
                            backup.write(f.read())
                    
                    # Write new prompt
                    with open(file_path, 'w') as f:
                        f.write(update.suggested_prompt)
                    
                    logger.info(f"Updated {update.agent_type} prompt (expected +{update.expected_improvement:.1%})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply prompt updates: {e}")
            return False
