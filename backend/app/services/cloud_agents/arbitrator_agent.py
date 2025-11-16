#!/usr/bin/env python3
"""
Final Arbitrator Agent - Single Cloud API Call (Phase 5)
7-day rotating frontier models with learned prompt enhancement
"""

import asyncio
import logging
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Hot-reloaded prompt and bias paths (relative to services/)
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "arbitrator_prompt.txt"
BIAS_PATH = Path(__file__).parent.parent / "prompts" / "arbitrator_bias.json"

class ArbitratorAgent:
    """
    Phase 5: Final Arbitrator - Rotating Cloud Models
    Weekly rotation: DeepSeek-V3, Gemini 2.5 Pro, Grok-4, Claude Sonnet 4, GPT-5
    Tracks which model performs best over time via Learner Agent
    """

    def __init__(self, cloud_model: str = "deepseek-v3"):
        self.agent_name = "ArbitratorAgent"
        self.cloud_model = cloud_model  # Rotates weekly (Mon-Sun)
        self.base_prompt = self._load_prompt()

        # Map model names to API providers
        self.model_providers = {
            "deepseek-v3": "runpod",      # DeepSeek on RunPod
            "gemini-2.5-pro": "google",   # Gemini via Google AI
            "grok-4": "xai",              # Grok via X.AI
            "claude-sonnet-4": "anthropic", # Claude via Anthropic
            "gpt-5-o3": "openai",         # GPT via OpenAI
            "qwen2.5:32b": "runpod"       # Fallback: Qwen on RunPod
        }

        self.provider = self.model_providers.get(cloud_model, "runpod")

        # Fallback chain: Try primary → try alternates → fallback to RunPod Qwen
        self.fallback_chain = self._build_fallback_chain(cloud_model)

    def _build_fallback_chain(self, primary_model: str) -> List[str]:
        """
        Build fallback chain for model failures
        Order: Primary → Other cloud models → RunPod Qwen (guaranteed)
        """
        all_models = ["deepseek-v3", "gemini-2.5-pro", "grok-4", "claude-sonnet-4", "gpt-5-o3"]

        # Start with primary model
        chain = [primary_model]

        # Add other cloud models (excluding primary)
        for model in all_models:
            if model != primary_model and model not in chain:
                chain.append(model)

        # Always end with RunPod Qwen as guaranteed fallback
        if "qwen2.5:32b" not in chain:
            chain.append("qwen2.5:32b")

        return chain
        
    def _load_prompt(self) -> str:
        """Load base arbitrator prompt from file"""
        try:
            return PROMPT_PATH.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"Arbitrator prompt load failed: {e}")
            return "Select best picks from agents. Return JSON only."

    async def initialize(self):
        """Initialize dependencies (currently none needed)"""
        pass
    
    async def make_final_selection(self, phase_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Single cloud API call for final arbitration
        
        Args:
            phase_data: {
                'short_list': [...],      # 75 symbols from Phase 1
                'vision_flags': {...},    # 6 boolean flags per symbol  
                'social_scores': {...},   # -5 to +5 per symbol
                'market_context': {...}   # Kill-switch data
            }
            
        Returns:
            {
                'final_picks': [...],     # 3-6 picks with targets
                'reasoning': '...',
                'confidence_intervals': {...}
            }
        """
        
        # Initialize if needed
        await self.initialize()
        
        # Get learned arbitrator bias (hot-reloaded nightly)
        arbitrator_bias = await self._load_arbitrator_bias()
        
        # Build enhanced prompt with learned insights
        enhanced_prompt = await self._build_enhanced_prompt(phase_data, arbitrator_bias)
        
        # Single cloud API call
        result = await self._call_cloud_arbitrator(enhanced_prompt)
        
        # Track decision for learning
        await self._track_arbitration_decision(phase_data, result)
        
        return result
    
    async def _load_arbitrator_bias(self) -> Dict[str, Any]:
        """Load learned arbitrator bias (updated nightly by Learner Agent)"""
        try:
            with open(BIAS_PATH, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Arbitrator bias file not found at {BIAS_PATH}, using defaults")
            # Default bias if file doesn't exist yet
            return {
                "social_score_multiplier": 1.2,
                "sector_preferences": {"tech": 1.1, "energy": 0.9},
                "confidence_calibration": 0.75,
                "arbitrator_rotation_bias": {"qwen2.5:32b": 1.0}
            }
    
    async def _build_enhanced_prompt(self, phase_data: Dict[str, Any], bias: Dict[str, Any]) -> str:
        """Build prompt enhanced with learned insights"""

        # Start with base prompt from file
        enhanced = f"{self.base_prompt}\n\n"

        # Add learned bias
        enhanced += f"""
LEARNED ARBITRATOR BIAS (updated nightly by Learner Agent):
Model: {self.cloud_model} (RunPod)
Social Score Multiplier: {bias.get('social_score_multiplier', 1.0)}
Sector Preferences: {json.dumps(bias.get('sector_preferences', {}), indent=2)}
Confidence Calibration: {bias.get('confidence_calibration', 0.75)}

PHASE DATA:
Short List: {len(phase_data.get('short_list', []))} candidates
Vision Flags: {len(phase_data.get('vision_flags', {}))} analyzed
Social Scores: {len(phase_data.get('social_scores', {}))} analyzed

TOP 10 CANDIDATES:
{json.dumps(phase_data.get('short_list', [])[:10], indent=2)}

SELECT 3-6 FINAL PICKS with:
- Direction: "bullish" or "bearish"
- Confidence: 0.0-1.0
- Target low and target high prices
- Reasoning: Brief explanation (under 100 chars)

RETURN JSON ONLY:
{{
  "final_picks": [
    {{
      "symbol": "NVDA",
      "direction": "bullish",
      "confidence": 0.82,
      "target_low": 145.0,
      "target_high": 165.0,
      "reasoning": "Strong vision flags + social score +4"
    }}
  ],
  "model_used": "{self.cloud_model}"
}}
"""
        return enhanced
    
    async def _call_cloud_arbitrator(self, prompt: str) -> Dict[str, Any]:
        """
        Call cloud provider with automatic fallback chain
        Tries: Primary → Alternates → RunPod Qwen (guaranteed)
        """
        logger.info(f"🎯 Arbitrator fallback chain: {' → '.join(self.fallback_chain)}")

        for attempt_num, model in enumerate(self.fallback_chain, 1):
            try:
                provider = self.model_providers.get(model, "runpod")
                logger.info(f"Attempt {attempt_num}/{len(self.fallback_chain)}: Trying {model} via {provider}")

                # Route to appropriate provider
                if provider == "runpod":
                    result = await self._call_runpod(prompt, model)
                elif provider == "google":
                    result = await self._call_google_gemini(prompt, model)
                elif provider == "xai":
                    result = await self._call_xai_grok(prompt, model)
                elif provider == "anthropic":
                    result = await self._call_anthropic_claude(prompt, model)
                elif provider == "openai":
                    result = await self._call_openai_gpt(prompt, model)
                else:
                    logger.error(f"Unknown provider: {provider}")
                    continue

                # Check if result is valid
                if result and result.get("final_picks"):
                    logger.info(f"✅ Success with {model}: {len(result['final_picks'])} picks")
                    result['attempted_models'] = self.fallback_chain[:attempt_num]
                    result['fallback_used'] = attempt_num > 1
                    return result
                else:
                    logger.warning(f"⚠️ {model} returned no picks, trying next fallback")

            except Exception as e:
                logger.error(f"❌ {model} failed: {e}")
                if attempt_num == len(self.fallback_chain):
                    # Last fallback failed - this is critical
                    logger.critical(f"🚨 ALL FALLBACKS FAILED including RunPod Qwen!")
                    raise
                else:
                    logger.warning(f"Falling back to next model...")
                    continue

        # Should never reach here due to raise above, but just in case
        return {
            "final_picks": [],
            "model_used": "FAILED",
            "attempted_models": self.fallback_chain,
            "error": "All fallback models failed"
        }

    async def _call_runpod(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call RunPod API (DeepSeek-V3 or Qwen2.5:32b)"""
        from app.core.runpod_client import get_runpod_client

        client = await get_runpod_client()
        response = await client.generate(
            prompt=prompt,
            model=model,
            temperature=0.3,
            max_tokens=2048
        )

        result = self._parse_json_response(response.get('output', ''))
        result['model_used'] = model
        result['provider'] = 'runpod'
        return result

    async def _call_google_gemini(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call Google Gemini 2.5 Pro API"""
        # TODO: Implement Google AI API call
        # For now, raise exception to trigger fallback
        raise NotImplementedError("Gemini API not yet implemented")

    async def _call_xai_grok(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call X.AI Grok-4 API"""
        # TODO: Implement X.AI API call
        # For now, raise exception to trigger fallback
        raise NotImplementedError("Grok API not yet implemented")

    async def _call_anthropic_claude(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call Anthropic Claude Sonnet 4 API"""
        # TODO: Implement Anthropic API call
        # For now, raise exception to trigger fallback
        raise NotImplementedError("Claude API not yet implemented")

    async def _call_openai_gpt(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call OpenAI GPT-5 API"""
        # TODO: Implement OpenAI API call
        # For now, raise exception to trigger fallback
        raise NotImplementedError("GPT API not yet implemented")

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        """Parse JSON from model response"""
        start = raw.find("{")
        end = raw.rfind("}") + 1

        if start == -1 or end == 0:
            logger.error(f"No JSON found in response: {raw[:200]}")
            return {"final_picks": [], "model_used": self.cloud_model}

        try:
            result = json.loads(raw[start:end])
            result['model_used'] = self.cloud_model
            result['provider'] = self.provider
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {"final_picks": [], "model_used": self.cloud_model}
    
    async def _track_arbitration_decision(self, phase_data: Dict[str, Any], result: Dict[str, Any]):
        """
        Track decision for nightly learning
        NOTE: Tracking is now handled by learner_agent which analyzes shortlist_candidates table
        """
        # Legacy method - learner agent now handles this via database analysis
        pass
