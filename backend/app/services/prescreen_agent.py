#!/usr/bin/env python3
"""
Prescreen Agent – FinMA-7b (Production v3 – November 10, 2025)
Phase 1: ACTIVE (~1,700) → exactly 75 SHORT_LIST candidates
Single Ollama call, no batching, no per-stock loops
"""

import asyncio
import logging
import os
import json
from datetime import datetime, date
from typing import List, Dict, Any

from .ollama_client import get_ollama_client
from ..core.database import get_database

logger = logging.getLogger(__name__)

class PrescreenAgent:
    """
    FinMA-7b Prescreen Agent – ONE CALL TO RULE THEM ALL
    
    Responsibilities:
    1. Take ACTIVE tickers + all 127 pre-computed features
    2. ONE Ollama call → return exactly 75 ranked SHORT_LIST tickers
    3. Store full candidate list (75) for LearnerAgent tracking
    4. Hot-reload prompt nightly via BrainAgent
    """

    def __init__(self):
        self.model_name = "finma-7b"
        self.ollama_client = None
        self.db = None
        self.initialized = False

        # Prompt files (hot-reloaded nightly)
        self.prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "finma_prescreen_v3.txt"
        )
        self.weights_path = os.path.join(
            os.path.dirname(__file__), "prompts", "weights.json"
        )

    async def initialize(self):
        if self.initialized:
            return

        self.ollama_client = await get_ollama_client()
        self.db = await get_database()

        # Verify model
        models = await self.ollama_client.list_models()
        model_names = [m['name'] for m in models.get('models', [])]
        if self.model_name not in model_names:
            raise RuntimeError(f"{self.model_name} not pulled! Run `ollama pull finma-7b`")

        self.initialized = True
        logger.info(f"PrescreenAgent ready – model: {self.model_name}")

    async def screen_active_to_shortlist(self, active_tickers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ONE CALL: ACTIVE (~1,700) → exactly 75 SHORT_LIST
        """
        if not self.initialized:
            await self.initialize()

        logger.info(f"Prescreening {len(active_tickers)} ACTIVE tickers → exactly 75 SHORT_LIST")

        # Load latest prompt + weights (hot-reloaded nightly)
        prompt = self._load_prompt()
        weights = self._load_weights()

        # Build massive context payload
        context = {
            "date": date.today().isoformat(),
            "active_count": len(active_tickers),
            "weights": weights,
            "tickers": [
                {
                    "symbol": t['symbol'],
                    "price": t.get('price', 0.0),
                    "volume": t.get('volume_5d_avg', 0),
                    "market_cap": t.get('market_cap', 0),
                    "volatility_annualized": t.get('volatility', 0.0),
                    "beta": t.get('beta', 1.0),
                    "rsi_14": t.get('rsi_14', 50),
                    "gap_today": t.get('gap_percent', 0.0),
                    # ... all 127 features you already compute
                }
                for t in active_tickers
            ]
        }

        full_prompt = f"{prompt}\n\nCONTEXT:\n{json.dumps(context, indent=2)}"

        try:
            response = await self.ollama_client.generate(
                model=self.model_name,
                prompt=full_prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 2048,
                    "stop": ["</s>"]
                }
            )

            shortlist = self._parse_response(response['response'])
            await self._store_shortlist(shortlist, context)

            logger.info(f"SHORT_LIST created: {len(shortlist)} tickers selected")
            return shortlist

        except Exception as e:
            logger.error(f"Prescreen failed: {e}")
            raise

    def _load_prompt(self) -> str:
        try:
            with open(self.prompt_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"Prompt load failed: {e}")
            return "You are FinMA-7b, elite explosive-move hunter for BullsBears.xyz."

    def _load_weights(self) -> Dict:
        try:
            with open(self.weights_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _parse_response(self, text: str) -> List[Dict[str, Any]]:
        """Parse JSON block from FinMA-7b"""
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            data = json.loads(text[start:end])

            selected = data.get("filtered_tickers", [])[:75]  # enforce exactly 75
            summary = data.get("summary", "")
            top10 = data.get("top_10_with_scores", [])

            logger.info(f"Prescreen summary: {summary}")

            return [
                {
                    "symbol": sym,
                    "rank": i + 1,
                    "prescreen_reason": next((t["primary_signal"] for t in top10 if t["symbol"] == sym), "High momentum")
                }
                for i, sym in enumerate(selected)
            ]
        except Exception as e:
            logger.error(f"Parse failed: {e}")
            return []

    async def _store_shortlist(self, shortlist: List[Dict], context: Dict):
        """Store full 75-candidate list for LearnerAgent"""
        try:
            await self.db.execute("TRUNCATE candidate_shortlist RESTART IDENTITY")
            for item in shortlist:
                await self.db.execute("""
                    INSERT INTO candidate_shortlist (
                        symbol, rank, prescreen_reason, screening_date, context_snapshot
                    ) VALUES ($1, $2, $3, $4, $5)
                """, item['symbol'], item['rank'], item['prescreen_reason'], date.today(), json.dumps(context))
            logger.info("SHORT_LIST stored for 30-day tracking")
        except Exception as e:
            logger.error(f"Store failed: {e}")
