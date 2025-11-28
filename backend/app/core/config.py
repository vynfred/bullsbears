# backend/app/core/config.py
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"

    # Required — set in Render dashboard only
    DATABASE_URL: str
    REDIS_URL: str
    FIREWORKS_API_KEY: str
    GROQ_API_KEY: str
    GROK_API_KEY: str
    FMP_API_KEY: str
    FIREBASE_SERVICE_ACCOUNT: str  # full JSON string

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


settings = Settings()