"""
BullsBears AI Agent Base Class
Provides common interface for all AI agents in the system
"""

import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Standardized response from AI agents"""
    agent_name: str
    picks: List[Dict[str, Any]]
    confidence: float
    reasoning: str
    execution_time: float
    model_used: str
    timestamp: float


class BaseAgent(ABC):
    """Base class for all BullsBears AI agents"""
    
    def __init__(self, name: str, model: str, client, client_type: str = "ollama"):
        self.name = name
        self.model = model
        self.client = client  # Can be ollama_client or vllm_client
        self.client_type = client_type  # "ollama" or "vllm"
        self.system_prompt = self._load_system_prompt()

        logger.info(f"🤖 Initialized {name} agent with {client_type.upper()} model {model}")
        
    def _load_system_prompt(self) -> str:
        """Load system prompt from file"""
        try:
            # Map agent names to prompt files
            prompt_mapping = {
                # Phase 1: Pre-filtering
                'PreFilter': 'prefilter.txt',

                # Phase 2: Predictors
                'Bull-Technical': 'bull_technical.txt',
                'Bull-Fundamental': 'bull_fundamental.txt',
                'Bear-Technical': 'bear_technical.txt',
                'Bear-Fundamental': 'bear_fundamental.txt',

                # Phase 3: News & Social
                'NewsAgent': 'newsagent.txt',

                # Phase 4: Vision & Risk
                'Vision': 'vision.txt',
                'RiskAgent': 'riskagent.txt',

                # Phase 5: Final Decision
                'Arbitrator': 'arbitrator.txt',

                # Phase 6: Learning System
                'Learner': 'learner.txt',
                'Brain': 'brain.txt'
            }

            prompt_filename = prompt_mapping.get(self.name)
            if prompt_filename:
                # Get absolute path to prompts directory
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                prompt_file = os.path.join(current_dir, "prompts", prompt_filename)

                if os.path.exists(prompt_file):
                    with open(prompt_file, 'r') as f:
                        logger.info(f"✅ Loaded optimized prompt for {self.name}")
                        return f.read().strip()

            logger.warning(f"System prompt file not found for {self.name}, using default")
            return self._get_default_prompt()
        except Exception as e:
            logger.error(f"Error loading system prompt for {self.name}: {str(e)}")
            return self._get_default_prompt()
    
    @abstractmethod
    def _get_default_prompt(self) -> str:
        """Get default system prompt for this agent"""
        pass
    
    @abstractmethod
    async def analyze(self, data: Dict[str, Any]) -> AgentResponse:
        """Main analysis method - must be implemented by each agent"""
        pass
    
    async def _call_model(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call the model (Ollama or vLLM) with error handling"""
        start_time = time.time()

        try:
            if self.client_type == "vllm":
                # Use vLLM client for Kimi-K2
                full_prompt = f"{self.system_prompt}\n\n{prompt}"
                response = await self.client.generate(
                    prompt=full_prompt,
                    max_tokens=max_tokens,
                    temperature=0.6  # Kimi-K2 recommended temperature
                )
                result = response.content.strip()

            else:
                # Use Ollama client (default)
                response = await self.client.generate(
                    model=self.model,
                    prompt=f"{self.system_prompt}\n\n{prompt}",
                    options={
                        "num_predict": max_tokens,
                        "temperature": 0.1,  # Low temperature for consistent results
                        "top_p": 0.9,
                        "stop": ["</analysis>", "\n\n---"]
                    }
                )
                result = response.get('response', '')

            execution_time = time.time() - start_time
            logger.info(f"{self.name} ({self.client_type.upper()}) completed in {execution_time:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Error calling {self.name} model: {str(e)}")
            raise
    
    def _parse_json_response(self, response) -> Dict[str, Any]:
        """Parse JSON response with error handling"""
        try:
            # Handle Ollama response format
            if isinstance(response, dict) and 'response' in response:
                response_text = response['response']
            else:
                response_text = str(response)

            # Look for JSON in markdown code blocks first (DeepSeek-R1 format)
            import re
            json_patterns = [
                r'```json\s*(\{.*?\})\s*```',
                r'```\s*(\{.*?\})\s*```',
                r'(\{.*?\})',
            ]

            for pattern in json_patterns:
                matches = re.findall(pattern, response_text, re.DOTALL)
                for match in matches:
                    try:
                        return json.loads(match.strip())
                    except json.JSONDecodeError:
                        continue

            # Fallback: try to extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                logger.warning(f"No JSON found in {self.name} response")
                logger.debug(f"Raw response: {response_text[:200]}...")
                return {}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in {self.name}: {str(e)}")
            return {}
    
    def _validate_picks(self, picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean pick data"""
        validated_picks = []
        
        for pick in picks:
            if not isinstance(pick, dict):
                continue
                
            # Required fields
            if 'ticker' not in pick or 'confidence' not in pick:
                continue
                
            # Clean and validate ticker
            ticker = str(pick['ticker']).upper().strip()
            if not ticker or len(ticker) > 10:
                continue
                
            # Validate confidence
            try:
                confidence = float(pick['confidence'])
                if not 0 <= confidence <= 100:
                    continue
            except (ValueError, TypeError):
                continue
            
            validated_pick = {
                'ticker': ticker,
                'confidence': confidence,
                'reasoning': pick.get('reasoning', ''),
                'direction': pick.get('direction', 'bullish'),
                'target_range': pick.get('target_range', {}),
                'timeframe': pick.get('timeframe', '1-3 days')
            }
            
            validated_picks.append(validated_pick)
        
        return validated_picks
    
    async def health_check(self) -> bool:
        """Check if agent is healthy and responsive"""
        try:
            test_response = await self._call_model("Health check", max_tokens=10)
            return len(test_response) > 0
        except Exception:
            return False


class PreFilterAgent(BaseAgent):
    """Pre-filter agent to reduce 2,963 stocks to ~200 volatile candidates"""
    
    def __init__(self, ollama_client):
        super().__init__("PreFilter", "llama3.2:3b", ollama_client)
    
    def _get_default_prompt(self) -> str:
        return """You are a stock pre-filter agent. You must respond with valid JSON only.

Filter criteria:
- 10-day ATR > 4% OR gap > 3%
- Volume above average
- Technical setup potential
- Exclude penny stocks (<$5)

You must respond in this exact JSON format:
{
    "filtered_tickers": ["TSLA", "NVDA"],
    "reasoning": "Brief explanation of filtering logic"
}

Respond with valid JSON only:"""
    
    async def analyze(self, data: Dict[str, Any]) -> AgentResponse:
        start_time = time.time()
        
        stocks_data = data.get('stocks', [])
        
        prompt = f"""
Analyze these {len(stocks_data)} stocks and filter to ~200 volatile candidates:

{json.dumps(stocks_data[:50], indent=2)}  # Truncate for prompt size

Return JSON format:
{{
    "filtered_tickers": ["TSLA", "NVDA", ...],
    "reasoning": "Brief explanation of filtering logic"
}}
"""
        
        response = await self._call_model(prompt, max_tokens=2000)
        parsed = self._parse_json_response(response)
        
        filtered_tickers = parsed.get('filtered_tickers', [])
        reasoning = parsed.get('reasoning', 'Pre-filter analysis completed')
        
        # Convert to standard pick format
        picks = [{'ticker': ticker, 'confidence': 75, 'reasoning': 'Pre-filtered candidate'} 
                for ticker in filtered_tickers[:200]]  # Limit to 200
        
        execution_time = time.time() - start_time
        
        return AgentResponse(
            agent_name=self.name,
            picks=picks,
            confidence=75.0,
            reasoning=reasoning,
            execution_time=execution_time,
            model_used=self.model,
            timestamp=time.time()
        )
