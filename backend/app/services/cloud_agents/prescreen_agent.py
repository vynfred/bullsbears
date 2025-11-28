# backend/app/services/cloud_agents/screen_agent.py
"""
Prescreen Agent - Fireworks.ai qwen2.5-72b-instruct
ACTIVE tier (~1,700) → SHORT_LIST (exactly 75)
"""

import httpx
import json
import logging
from pathlib import Path
from app.core.config import settings
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

class PrescreenAgent:
    def __init__(self):
        self.model = "accounts/fireworks/models/qwen2.5-72b-instruct"
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "screen_prompt.txt"
    
    async def initialize(self):
        """Initialize agent"""
        pass
    
    async def run_prescreen(self) -> dict:
        """Run prescreen via Fireworks.ai"""
        logger.info("Running prescreen with qwen2.5-72b-instruct")
        
        # Get active stocks from database
        db = await get_asyncpg_pool()
        stocks = await db.fetch("SELECT * FROM active_stocks LIMIT 1700")
        
        # Load prompt
        prompt = self.prompt_path.read_text(encoding="utf-8")
        
        # Call Fireworks API
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.fireworks.ai/inference/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.FIREWORKS_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 4096
                }
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        
        # Parse JSON response
        result = json.loads(content)
        
        return {
            "shortlist_count": len(result.get("filtered_tickers", [])),
            "tickers": result.get("filtered_tickers", []),
            "summary": result.get("summary", "")
        }