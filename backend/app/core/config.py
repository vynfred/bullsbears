"""
Configuration management for the BullsBears application.
"""
import os
from typing import List, Optional
from pydantic import validator, Field
from pydantic_settings import BaseSettings
from functools import lru_cache


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
    
    # API Keys - Stock/Options Data
    alpha_vantage_api_key: str
    yahoo_finance_enabled: bool = True
    fmp_api_key: Optional[str] = None
    alpaca_api_key: Optional[str] = None
    alpaca_secret_key: Optional[str] = None
    benzinga_api_key: Optional[str] = None
    benzinga_enabled: bool = True
    benzinga_rate_limit: int = 5
    polygon_news_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    fred_api_key: Optional[str] = None
    nasdaq_api_key: Optional[str] = None
    nasdaq_enabled: bool = True
    
    # API Keys - News Sources
    news_api_key: str
    alpha_vantage_news_enabled: bool = True
    
    # API Keys - Social Media
    twitter_bearer_token: Optional[str] = None
    twitter_api_key: Optional[str] = Field(None, env="TWITTER_API_KEY")
    twitter_secret: Optional[str] = Field(None, env="TWITTER_SECRET")
    stocktwits_access_token: Optional[str] = None
    reddit_client_id: Optional[str] = Field(None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(None, env="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field("BullsBears/2.1", env="REDDIT_USER_AGENT")

    # AI APIs
    grok_api_key: Optional[str] = Field(None, env="grok_api")
    
    # CORS
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    allowed_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    allowed_headers: str = "*"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Caching (in seconds)
    cache_api_responses: int = 30
    cache_indicators: int = 300
    cache_user_preferences: int = 3600
    cache_historical_data: int = 86400
    
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
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    def get_allowed_methods(self) -> List[str]:
        """Parse CORS methods from string."""
        return [method.strip() for method in self.allowed_methods.split(",")]

    def get_allowed_headers(self) -> List[str]:
        """Parse CORS headers from string."""
        if self.allowed_headers == "*":
            return ["*"]
        return [header.strip() for header in self.allowed_headers.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Global settings instance
settings = get_settings()
