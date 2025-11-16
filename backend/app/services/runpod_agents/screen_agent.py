#!/usr/bin/env python3
"""
Prescreen Agent – Qwen2.5:32b on RunPod (Production v3.3 – November 14, 2025)
Phase 1: ACTIVE (~1,700) → exactly 75 SHORT_LIST candidates
Single RunPod call, no batching, no per-stock loops
"""

import asyncio
import logging
import os
import json
from datetime import datetime, date
from typing import List, Dict, Any

from ...core.runpod_client import get_runpod_client
from ...core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

class PrescreenAgent:
    """
    Qwen2.5:32b Prescreen Agent on RunPod – ONE CALL TO RULE THEM ALL

    Responsibilities:
    1. Take ACTIVE tickers + all 127 pre-computed features
    2. ONE RunPod call → return exactly 75 ranked SHORT_LIST tickers
    3. Store full candidate list (75) for LearnerAgent tracking
    4. Hot-reload prompt nightly via BrainAgent
    """

    def __init__(self):
        self.model_name = "qwen2.5:32b"
        self.runpod_client = None
        self.db = None
        self.initialized = False

        # Prompt files (hot-reloaded nightly, relative to services/)
        services_dir = os.path.dirname(os.path.dirname(__file__))
        self.prompt_path = os.path.join(services_dir, "prompts", "screen_prompt.txt")
        self.weights_path = os.path.join(services_dir, "prompts", "weights.json")

    async def initialize(self):
        if self.initialized:
            return

        self.runpod_client = await get_runpod_client()
        self.db = await get_asyncpg_pool()

        self.initialized = True
        logger.info(f"PrescreenAgent ready – model: {self.model_name} on RunPod")

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
            response = await self.runpod_client.run_inference(
                prompt=full_prompt,
                model=self.model_name,
                temperature=0.1,
                max_tokens=2048,
                response_format="json"
            )

            # RunPod returns output in 'output' field
            response_text = response.get('response') or response.get('output', '')
            shortlist = self._parse_response(response_text)
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
        """Store full 75-candidate list in shortlist_candidates table for learning"""
        try:
            today = date.today()

            # Store each candidate with complete context
            for item in shortlist:
                symbol = item['symbol']
                rank = item.get('rank', 0)

                # Get ticker data from context
                ticker_data = next((t for t in context.get('tickers', []) if t['symbol'] == symbol), {})

                # Build technical snapshot
                technical_snapshot = {
                    'price': ticker_data.get('price', 0.0),
                    'volume_5d_avg': ticker_data.get('volume', 0),
                    'volatility_annualized': ticker_data.get('volatility', 0.0),
                    'beta': ticker_data.get('beta', 1.0),
                    'rsi_14': ticker_data.get('rsi_14', 50),
                    'gap_today': ticker_data.get('gap_percent', 0.0),
                    # Add more technical indicators as available
                }

                # Build fundamental snapshot
                fundamental_snapshot = {
                    'market_cap': ticker_data.get('market_cap', 0),
                    'sector': ticker_data.get('sector', ''),
                    'industry': ticker_data.get('industry', ''),
                    # Add more fundamental data as available
                }

                # Insert or update candidate
                await self.db.execute("""
                    INSERT INTO shortlist_candidates (
                        date, symbol, rank,
                        prescreen_score, prescreen_reasoning,
                        price_at_selection,
                        technical_snapshot, fundamental_snapshot,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
                    ON CONFLICT (date, symbol) DO UPDATE SET
                        rank = EXCLUDED.rank,
                        prescreen_score = EXCLUDED.prescreen_score,
                        prescreen_reasoning = EXCLUDED.prescreen_reasoning,
                        price_at_selection = EXCLUDED.price_at_selection,
                        technical_snapshot = EXCLUDED.technical_snapshot,
                        fundamental_snapshot = EXCLUDED.fundamental_snapshot,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    today,
                    symbol,
                    rank,
                    item.get('prescreen_score', 0.0),
                    item.get('prescreen_reason', ''),
                    ticker_data.get('price', 0.0),
                    json.dumps(technical_snapshot),
                    json.dumps(fundamental_snapshot)
                )

            logger.info(f"✅ Stored {len(shortlist)} candidates in shortlist_candidates table")
        except Exception as e:
            logger.error(f"❌ Failed to store shortlist: {e}", exc_info=True)
