# backend/app/core/config.py
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"

    # Required — core infra (set in Render dashboard)
    DATABASE_URL: str
    REDIS_URL: str

    # API Keys — required for full functionality, but allow startup without them
    # This allows Celery worker to start even if env vars are missing
    FIREWORKS_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROK_API_KEY: str = ""
    FMP_API_KEY: str = ""
    FIREBASE_SERVICE_ACCOUNT: str = ""  # full JSON string

    # Optional
    KILL_SWITCH_VIX_THRESHOLD: float = 35.0
    KILL_SWITCH_SPY_DROP_PCT: float = 2.0

    # Permanent winner — no rotation ever again
    ARBITRATOR_MODEL: str = "accounts/fireworks/models/qwen2.5-72b-instruct"

    model_config = {
        "env_file": None,
        "extra": "ignore",
        "frozen": True,
    }

    def validate_api_keys(self) -> dict:
        """Check which API keys are configured"""
        return {
            "fireworks": bool(self.FIREWORKS_API_KEY),
            "groq": bool(self.GROQ_API_KEY),
            "grok": bool(self.GROK_API_KEY),
            "fmp": bool(self.FMP_API_KEY),
            "firebase": bool(self.FIREBASE_SERVICE_ACCOUNT),
        }


settings = Settings()