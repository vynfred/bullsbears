"""
Configuration management for the BullsBears application.
"""
import os
from typing import List, Optional
from pydantic import validator, Field
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from both backend/.env and root .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))  # Root .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))  # Backend .env


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "BullsBears"
    app_version: str = "2.1.0"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str
    
    # Database
    database_url: str
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "bullsbears"
    database_user: str
    database_password: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # API Keys - Core Data Sources
    alpha_vantage_api_key: str = Field(..., env="ALPHA_VANTAGE_API_KEY")
    finnhub_api_key: Optional[str] = Field(None, env="FINNHUB_API_KEY")
    polygon_api_key: Optional[str] = Field(None, env="POLYGON_API_KEY")
    newsapi_key: Optional[str] = Field(None, env="NEWS_API_KEY")
    databento_api_key: Optional[str] = Field(None, env="DATABENTO_API_KEY")

    # API Keys - Economic & Regulatory Data
    sec_api_key: str = Field(..., env="SEC_API")
    fred_api_key: str = Field(..., env="fred_api_key")
    bls_api_key: str = Field(..., env="BUREEAU_OF_LABOR_STATS_API_KEY")

    # API Keys - AI Services (Dual AI System)
    grok_api_key: str = Field(..., env="GROK_API_KEY")
    deepseek_api_key: str = Field(..., env="DEEPSEEK_API_KEY")

    # API Keys - Social Media
    reddit_client_id: Optional[str] = Field(None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(None, env="REDDIT_CLIENT_SECRET")

    # Rate Limiting Configuration
    api_rate_limit_per_minute: int = 15  # Max API calls per minute (reduced)
    api_batch_delay_seconds: float = 2.0  # Delay between API batches (increased)
    api_retry_max_attempts: int = 3  # Max retry attempts for failed API calls
    api_retry_base_delay: float = 2.0  # Base delay for exponential backoff (increased)
    # Removed Yahoo Finance - not used for news data
    fred_api_key: Optional[str] = None
    nasdaq_api_key: Optional[str] = None
    nasdaq_enabled: bool = True
    fmp_api_key: Optional[str] = None
    alpaca_api_key: Optional[str] = None
    alpaca_secret_key: Optional[str] = None
    polygon_news_api_key: Optional[str] = None
    
    # API Keys - News Sources
    alpha_vantage_news_enabled: bool = True
    
    # API Keys - Social Media
    twitter_bearer_token: Optional[str] = None
    twitter_api_key: Optional[str] = Field(None, env="TWITTER_API_KEY")
    twitter_secret: Optional[str] = Field(None, env="TWITTER_SECRET")
    stocktwits_access_token: Optional[str] = None
    reddit_client_id: Optional[str] = Field(None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(None, env="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field("BullsBears/2.1", env="REDDIT_USER_AGENT")

    # AI APIs - Configuration handled above in dual AI section
    
    # CORS - Allow all origins for development
    allowed_origins: str = Field("*", env="ALLOWED_ORIGINS")
    allowed_methods: str = Field("GET,POST,PUT,DELETE,OPTIONS", env="ALLOWED_METHODS")
    allowed_headers: str = Field("*", env="ALLOWED_HEADERS")
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Caching (in seconds)
    cache_api_responses: int = 30
    cache_indicators: int = 300
    cache_user_preferences: int = 3600
    cache_historical_data: int = 86400
    cache_news: int = 600  # 10 minutes
    cache_social_media: int = 300  # 5 minutes
    cache_complete_analysis: int = 600  # 10 minutes for complete analysis

    # Pre-computed Analysis Caching (in seconds)
    cache_precomputed_analysis: int = 1800  # 30 minutes for precomputed analysis
    cache_precomputed_technical: int = 3600  # 1 hour for technical data
    cache_precomputed_sentiment: int = 1800  # 30 minutes for sentiment data
    cache_precomputed_news: int = 86400  # 1 day for news data (testing phase)
    cache_stale_data_warning: int = 7200  # 2 hours before showing stale warning

    # Precompute System Configuration
    precompute_enabled: bool = False  # Feature flag for precompute system
    precompute_top_stocks_count: int = 10  # Number of top stocks to precompute
    precompute_market_hours_interval: int = 3600  # 1 hour during market hours
    precompute_after_hours_interval: int = 7200  # 2 hours after market hours
    precompute_weekend_interval: int = 14400  # 4 hours on weekends

    # Rate Limiting for Real-time Fallbacks
    realtime_requests_per_day: int = 5  # Free tier limit for real-time requests
    realtime_api_calls_per_request: int = 2  # Max API calls per real-time request

    # ML Model Storage (Phase 2)
    model_dir: str = Field(default="models", env="MODEL_DIR")  # Directory for storing ML models
    
    # Market Hours (Eastern Time)
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 16
    market_close_minute: int = 0
    
    # WebSocket
    ws_heartbeat_interval: int = 30
    ws_max_connections: int = 1000
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    analytics_enabled: bool = False
    
    # Legal
    disclaimer_enabled: bool = True
    terms_version: str = "1.0"
    privacy_version: str = "1.0"
    
    def get_allowed_origins(self) -> List[str]:
        """Parse CORS origins from string."""
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    def get_allowed_methods(self) -> List[str]:
        """Parse CORS methods from string."""
        return [method.strip() for method in self.allowed_methods.split(",")]

    def get_allowed_headers(self) -> List[str]:
        """Parse CORS headers from string."""
        if self.allowed_headers == "*":
            return ["*"]
        return [header.strip() for header in self.allowed_headers.split(",")]

    @property
    def MODEL_DIR(self) -> str:
        """Get absolute path to model directory."""
        import os
        if os.path.isabs(self.model_dir):
            return self.model_dir
        # Relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(project_root, self.model_dir)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Global settings instance
settings = get_settings()
