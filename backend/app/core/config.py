"""
BullsBears Configuration Management
Based on ARCHITECTURE_GUIDE.md and PROJECT_ROADMAP.md

Architecture:
- Google Cloud SQL: Prime DB + 30-day candidate tracking + learning history
- RunPod: Qwen2.5:3B for Screener_Agent + Learner_Agent (single RTX 4090 serverless endpoint)
- Cloud APIs: Groq Vision + Grok Social + Rotating Arbitrator
- Firebase: Real-time picks & user experience
"""
import os
from typing import List, Optional, Dict
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from root .env
# Get the project root directory (3 levels up from this file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """BullsBears Application Settings - Production Architecture"""

    # ============================================================================
    # APPLICATION CORE
    # ============================================================================
    app_name: str = "BullsBears"
    app_version: str = "2.1.0"
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # ============================================================================
    # GOOGLE CLOUD SQL - Prime DB + 30-day candidate tracking + learning history
    # ============================================================================
    database_url: Optional[str] = Field(None, env="DATABASE_URL")
    database_host: str = Field(default="localhost", env="DATABASE_HOST")
    database_port: int = Field(default=5432, env="DATABASE_PORT")
    database_name: str = Field(default="bullsbears", env="DATABASE_NAME")
    database_user: Optional[str] = Field(None, env="DATABASE_USER")
    database_password: Optional[str] = Field(None, env="DATABASE_PASSWORD")

    # Database connection pool settings
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")

    # ============================================================================
    # REDIS - Caching and Celery
    # ============================================================================
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")

    # ============================================================================
    # FMP API - Premium tier (300 calls/min, 20 GB/month cap)
    # ============================================================================
    fmp_api_key: Optional[str] = Field(None, env="FMP_API_KEY")
    fmp_base_url: str = "https://financialmodelingprep.com/api/v3"
    fmp_rate_limit: int = 300  # calls per minute for Premium tier
    fmp_monthly_limit: int = 20  # GB per month

    # ============================================================================
    # RUNPOD - Qwen2.5-Coder-32B-Instructprescreen + Learner (RTX 4090 serverless)
    # ============================================================================
    runpod_api_key: Optional[str] = Field(None, env="RUNPOD_API_KEY")
    runpod_endpoint_id: Optional[str] = Field(None, env="RUNPOD_ENDPOINT_ID")
    runpod_base_url: str = "https://api.runpod.ai/v2"
    runpod_endpoint_name: str = "Qwen2.5-Coder-32B-Instruct-prescreen"
    runpod_gpu_type: str = "RTX 4090"
    runpod_workers: int = 1
    runpod_volume_size: int = 120  # GB

    # ============================================================================
    # CLOUD AI APIS - Vision + Social + Rotating Arbitrator
    # ============================================================================

    # Groq - Vision Agent (Llama-3.2-11B-Vision)
    groq_api_key: Optional[str] = Field(None, env="GROQ_API_KEY")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_vision_model: str = "llama-3.2-11b-vision-preview"

    # Grok - Social Context Agent
    grok_api_key: Optional[str] = Field(None, env="GROK_API_KEY")
    grok_base_url: str = "https://api.x.ai/v1"
    grok_model: str = "grok-beta"

    # Rotating Arbitrator Models - API Keys
    deepseek_api_key: Optional[str] = Field(None, env="DEEPSEEK_API_KEY")
    gemini_api_key: Optional[str] = Field(None, env="GEMINI_2.5_PRO_API_KEY")
    claude_api_key: Optional[str] = Field(None, env="CLAUDE_ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")

    # ============================================================================
    # WEEKLY ARBITRATOR ROTATION (6-week cycle)
    # ============================================================================
    # Strategy: Each model gets 1 full week (Mon-Fri = 5 trading days)
    # Why: 15-30 picks per model = statistically significant performance data
    #
    # How it works:
    # - ISO week number determines which model to use
    # - Week 1 (Jan 1-7): Qwen2.5:32b
    # - Week 2 (Jan 8-14): DeepSeek-V3
    # - Week 3 (Jan 15-21): Gemini 2.5 Pro
    # - etc.
    # - After Week 6, cycle repeats
    #
    # Saturday: SYSTEM OFF (no market, arbitrator returns None)
    # Sunday: Pre-market prep (uses current week's model)
    #
    # Fallback: If primary model fails, falls back through other models,
    #           always ending with Qwen2.5:32b on RunPod (guaranteed)
    # ============================================================================
    arbitrator_weekly_rotation: List[str] = [
        "qwen2.5:32b",      # Week 1 (RunPod baseline - always available)
        "deepseek-v3",      # Week 2 (RunPod or DeepSeek API)
        "gemini-2.5-pro",   # Week 3 (Google AI API)
        "grok-4",           # Week 4 (X.AI API)
        "claude-sonnet-4",  # Week 5 (Anthropic API)
        "gpt-5-o3"          # Week 6 (OpenAI API)
    ]

    # ============================================================================
    # FIREBASE - Real-time picks & user experience
    # ============================================================================
    firebase_project_id: str = Field(default="603494406675", env="FIREBASE_PROJECT_ID")
    firebase_credentials_path: Optional[str] = Field(None, env="FIREBASE_CREDENTIALS_PATH")
    firebase_database_url: Optional[str] = Field(None, env="FIREBASE_DATABASE_URL")

    # Firebase data structure paths
    firebase_picks_path: str = "/picks/latest"
    firebase_stats_path: str = "/stats/performance"
    firebase_watchlist_path: str = "/watchlist"
    firebase_notifications_path: str = "/notifications"

    # ============================================================================
    # STOCK CLASSIFICATION TIERS
    # ============================================================================
    # 4-Tier Pipeline: ALL → ACTIVE → SHORT_LIST → PICKS
    tier_all_count: int = 3800  # Complete NASDAQ stock universe
    tier_active_count: int = 1700  # Daily filtered high-potential symbols
    tier_short_list_count: int = 75  # Qwen2.5-Coder-32B-Instruct pre-screened explosive candidates
    tier_picks_count_min: int = 3  # Minimum final picks
    tier_picks_count_max: int = 6  # Maximum final picks

    # Stock filtering criteria for ACTIVE tier
    min_price: float = 1.25  # Minimum stock price
    min_volume: int = 100000  # Minimum daily volume
    min_market_cap: int = 500000000  # Minimum market cap ($500M)

    # ============================================================================
    # KILL SWITCH CONFIGURATION
    # ============================================================================
    kill_switch_vix_threshold: float = 30.0  # VIX > 30
    kill_switch_spy_threshold: float = -2.0  # SPY pre-market < -2%
    kill_switch_enabled: bool = True

    # ============================================================================
    # DAILY PIPELINE SCHEDULE (Eastern Time)
    # ============================================================================
    pipeline_data_update_time: str = "03:00"  # FMP Premium daily delta update
    pipeline_active_filter_time: str = "03:05"  # Logic filter → ACTIVE
    pipeline_prescreen_time: str = "03:10"  # RunPod Qwen2.5-Coder-32B-Instruct → SHORT_LIST
    pipeline_chart_generation_time: str = "03:15"  # Matplotlib charts
    pipeline_vision_analysis_time: str = "03:16"  # Groq Vision
    pipeline_social_context_time: str = "03:17"  # Grok API
    pipeline_arbitrator_time: str = "03:20"  # Final picks
    pipeline_firebase_publish_time: str = "03:25"  # Picks → Firebase
    pipeline_learning_time: str = "04:01"  # BrainAgent + LearnerAgent

    # ============================================================================
    # VISION ANALYSIS - 6 Boolean Flags
    # ============================================================================
    vision_flags: List[str] = [
        "wyckoff_phase_2",
        "weekly_triangle_coil",
        "volume_shelf_breakout",
        "p_shape_profile",
        "fakeout_wick_rejection",
        "spring_setup"
    ]

    # Chart generation settings
    chart_width: int = 256
    chart_height: int = 256
    chart_days_back: int = 90  # 90-day candles + volume

    # ============================================================================
    # SOCIAL CONTEXT SCORING
    # ============================================================================
    social_score_min: float = -5.0  # Extreme bearish panic / bearish setup
    social_score_max: float = 5.0   # Extreme FOMO / bullish chatter
    social_score_neutral: float = 0.0

    # ============================================================================
    # TARGET ANALYSIS FRAMEWORK (DB-DRIVEN, LEARNER-UPDATED)
    # ============================================================================
    # NOTE: These are DEFAULT values only. Actual values loaded from feature_weights table.
    # Learner Agent updates these based on historical performance and market conditions.

    # Base target ranges (static defaults, overridden by DB)
    target_bullish_low: float = 0.15    # +15% low target (default)
    target_bullish_high_min: float = 0.30  # +30% high target minimum
    target_bullish_high_max: float = 0.50  # +50% high target maximum
    target_bearish_low_min: float = -0.15  # -15% bearish low
    target_bearish_low_max: float = -0.20  # -20% bearish low
    target_bearish_high_min: float = -0.35 # -35% bearish high
    target_bearish_high_max: float = -0.45 # -45% bearish high

    # Adaptive target calculation (loaded from feature_weights)
    # target_actual = target_bullish_base * (1 + volatility * target_volatility_multiplier) * target_momentum_factor
    target_bullish_base: float = 0.20  # Base 20% target
    target_volatility_multiplier: float = 1.5  # Multiply by stock volatility
    target_momentum_factor: float = 0.8  # Momentum adjustment

    # Stop loss and risk/reward (DB-driven, Learner-optimized)
    stop_loss_bullish_min: float = -0.05  # -5% stop loss minimum (default)
    stop_loss_bullish_max: float = -0.10  # -10% stop loss maximum (default)
    stop_loss_bullish: float = -0.07  # Adaptive stop loss (loaded from DB)
    min_risk_reward_ratio: float = 2.5  # Minimum 2.5:1 risk/reward (loaded from DB)

    # Timeframe settings (DB-driven)
    target_timeframe_min_days: int = 1     # Minimum 1 trading day
    target_timeframe_max_days: int = 5     # Maximum 5 trading days
    target_timeframe_days: int = 3         # Default target timeframe (loaded from DB)
    tracking_period_days: int = 30         # 30-day tracking for learning

    # Confidence calculation factors
    confidence_agreement_weight: float = 0.3  # Weight for agent agreement
    confidence_trust_weight: float = 0.4      # Weight for agent trust scores
    confidence_volatility_weight: float = 0.2  # Weight for volatility adjustment
    confidence_social_weight: float = 0.1     # Weight for social alignment

    # ============================================================================
    # LEARNING SYSTEM CONFIGURATION
    # ============================================================================
    learning_enabled: bool = True
    learning_history_path: str = "backend/app/services/prompts/learning_history"

    # Prompt files that get hot-reloaded nightly (relative to backend/app/services/)
    # All agents load these directly via Path(__file__).parent.parent / "prompts"
    prompt_files: Dict[str, str] = {
        "screen": "backend/app/services/prompts/screen_prompt.txt",
        "learner": "backend/app/services/prompts/learner_prompt.txt",
        "vision": "backend/app/services/prompts/vision_prompt.txt",
        "social": "backend/app/services/prompts/social_prompt.txt",
        "arbitrator": "backend/app/services/prompts/arbitrator_prompt.txt"
    }

    # Weight and bias files for learning system (relative to backend/app/services/)
    weight_files: Dict[str, str] = {
        "weights": "backend/app/services/prompts/weights.json",
        "arbitrator_bias": "backend/app/services/prompts/arbitrator_bias.json",
        "fallback_config": "backend/app/services/prompts/arbitrator_fallback_config.json"
    }

    # ============================================================================
    # MARKET HOURS & TIMING
    # ============================================================================
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 16
    market_close_minute: int = 0
    market_timezone: str = "US/Eastern"

    # ============================================================================
    # CACHING CONFIGURATION
    # ============================================================================
    cache_api_responses: int = 30      # 30 seconds
    cache_indicators: int = 300        # 5 minutes
    cache_historical_data: int = 86400 # 1 day
    cache_news: int = 600              # 10 minutes
    cache_social_media: int = 300      # 5 minutes
    cache_complete_analysis: int = 600 # 10 minutes
    cache_charts: int = 3600           # 1 hour for generated charts

    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # API-specific rate limits
    fmp_requests_per_minute: int = 300  # Premium tier
    groq_requests_per_minute: int = 30
    grok_requests_per_minute: int = 100

    # ============================================================================
    # CELERY CONFIGURATION
    # ============================================================================
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: List[str] = ["json"]
    celery_timezone: str = "US/Eastern"

    # ============================================================================
    # WEBSOCKET CONFIGURATION
    # ============================================================================
    ws_heartbeat_interval: int = 30
    ws_max_connections: int = 1000
    ws_connection_timeout: int = 60

    # ============================================================================
    # CORS CONFIGURATION
    # ============================================================================
    allowed_origins: str = Field(default="*", env="ALLOWED_ORIGINS")
    allowed_methods: str = Field(default="GET,POST,PUT,DELETE,OPTIONS", env="ALLOWED_METHODS")
    allowed_headers: str = Field(default="*", env="ALLOWED_HEADERS")

    # ============================================================================
    # MONITORING & LOGGING
    # ============================================================================
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    analytics_enabled: bool = Field(default=False, env="ANALYTICS_ENABLED")
    performance_monitoring: bool = Field(default=True, env="PERFORMANCE_MONITORING")

    # Logging configuration
    log_file_path: str = Field(default="logs/bullsbears.log", env="LOG_FILE_PATH")
    log_max_bytes: int = Field(default=10485760, env="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")

    # ============================================================================
    # ADMIN AUTHENTICATION
    # ============================================================================
    admin_email: str = Field(default="hellovynfred@gmail.com", env="ADMIN_EMAIL")
    admin_password_hash: str = Field(
        default="692eb0e8bb02e3f11acef0699acc6a66c70ef29145d679fc3d8b68957c94fe24",
        env="ADMIN_PASSWORD_HASH"
    )

    # ============================================================================
    # SECURITY & LEGAL
    # ============================================================================
    disclaimer_enabled: bool = True
    terms_version: str = "1.0"
    privacy_version: str = "1.0"

    # API security
    api_key_header: str = "X-API-Key"
    max_request_size: int = 10485760  # 10MB
    request_timeout: int = 30  # seconds

    # ============================================================================
    # MODEL STORAGE
    # ============================================================================
    ai_model_dir: str = Field(default="models", env="MODEL_DIR")
    model_cache_dir: str = Field(default="models/cache", env="MODEL_CACHE_DIR")

    # RunPod local models
    runpod_models: Dict[str, Dict[str, str]] = {
        "Qwen2.5-Coder-32B-Instruct": {
            "name": "Qwen2.5-Coder-32B-Instruct",
            "size": "19GB",
            "purpose": "Prescreen agent"
        },
    }
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

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

    def get_current_arbitrator(self) -> Optional[str]:
        """
        Get current arbitrator model based on weekly rotation.
        Returns None on Saturdays (market closed).
        Each model gets 1 full week (5 trading days) for meaningful performance data.
        """
        from datetime import datetime

        now = datetime.now()
        weekday = now.weekday()

        # Saturday = market closed, no arbitrator needed
        if weekday == 5:
            return None

        # Calculate which week of the year (0-51)
        week_of_year = now.isocalendar()[1]

        # Rotate through models every week
        model_index = week_of_year % len(self.arbitrator_weekly_rotation)
        return self.arbitrator_weekly_rotation[model_index]

    def get_database_url(self) -> str:
        """Get complete database URL for connection."""
        if self.database_url:
            return self.database_url

        # Check if using Cloud SQL Unix socket (starts with /cloudsql/)
        if self.database_host.startswith("/cloudsql/"):
            # For Cloud SQL Unix socket, use host parameter format
            # asyncpg format: postgresql://user:pass@/dbname?host=/cloudsql/instance
            if self.database_user and self.database_password:
                return (f"postgresql://{self.database_user}:{self.database_password}"
                       f"@/{self.database_name}?host={self.database_host}")
            return f"postgresql:///{self.database_name}?host={self.database_host}"

        # Standard TCP connection
        if self.database_user and self.database_password:
            return (f"postgresql://{self.database_user}:{self.database_password}"
                   f"@{self.database_host}:{self.database_port}/{self.database_name}")

        return f"postgresql://{self.database_host}:{self.database_port}/{self.database_name}"

    def get_redis_url(self) -> str:
        """Get complete Redis URL for connection."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return self.redis_url

    def is_market_hours(self) -> bool:
        """Check if current time is within market hours (Eastern Time)."""
        from datetime import datetime
        import pytz

        et = pytz.timezone(self.market_timezone)
        now = datetime.now(et)

        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        market_open = now.replace(hour=self.market_open_hour, minute=self.market_open_minute, second=0, microsecond=0)
        market_close = now.replace(hour=self.market_close_hour, minute=self.market_close_minute, second=0, microsecond=0)

        return market_open <= now <= market_close

    def get_prompt_file_path(self, prompt_type: str) -> str:
        """
        Get absolute path to prompt file.
        Prompt files are stored in backend/app/services/prompts/
        """
        if prompt_type not in self.prompt_files:
            raise ValueError(f"Unknown prompt type: {prompt_type}. Available: {list(self.prompt_files.keys())}")

        # Paths in config are already relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        return os.path.join(project_root, self.prompt_files[prompt_type])

    def get_weight_file_path(self, weight_type: str) -> str:
        """
        Get absolute path to weight/bias file.
        Weight files are stored in backend/app/services/prompts/
        """
        if weight_type not in self.weight_files:
            raise ValueError(f"Unknown weight type: {weight_type}. Available: {list(self.weight_files.keys())}")

        # Paths in config are already relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        return os.path.join(project_root, self.weight_files[weight_type])

    @property
    def MODEL_DIR(self) -> str:
        """Get absolute path to model directory."""
        if os.path.isabs(self.ai_model_dir):
            return self.ai_model_dir
        # Relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(project_root, self.ai_model_dir)

    @property
    def LEARNING_HISTORY_DIR(self) -> str:
        """
        Get absolute path to learning history directory.
        Learning history is stored in backend/app/services/prompts/learning_history/
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        return os.path.join(project_root, self.learning_history_path)

    def validate_required_apis(self) -> Dict[str, bool]:
        """Validate that required API keys are present for production."""
        required_apis = {
            "fmp_api_key": bool(self.fmp_api_key),
            "runpod_api_key": bool(self.runpod_api_key),
            "runpod_endpoint_id": bool(self.runpod_endpoint_id),
            "groq_api_key": True,  # Optional for admin dashboard
            "grok_api_key": True,  # Optional for admin dashboard
            "database_url": bool(self.database_url or (self.database_user and self.database_password))
        }

        # At least one arbitrator API key should be present (optional for admin)
        arbitrator_apis = [
            self.deepseek_api_key,
            self.gemini_api_key,
            self.claude_api_key,
            self.openai_api_key
        ]
        required_apis["arbitrator_api"] = True  # Optional for admin dashboard

        return required_apis

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env
        protected_namespaces = ('settings_',)  # Fix namespace warning


# ============================================================================
# SETTINGS INSTANTIATION
# ============================================================================

@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Global settings instance
settings = get_settings()


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_configuration() -> Dict[str, bool]:
    """Validate the current configuration for production readiness."""
    validation_results = settings.validate_required_apis()

    # Add additional validations
    validation_results.update({
        "kill_switch_configured": settings.kill_switch_enabled,
        "pipeline_schedule_valid": all([
            settings.pipeline_data_update_time,
            settings.pipeline_prescreen_time,
            settings.pipeline_arbitrator_time,
            settings.pipeline_learning_time
        ]),
        "tier_counts_valid": (
            settings.tier_active_count > 0 and
            settings.tier_short_list_count > 0 and
            settings.tier_picks_count_max >= settings.tier_picks_count_min
        ),
        "vision_flags_configured": len(settings.vision_flags) == 6,
        "arbitrator_weekly_rotation_complete": len(settings.arbitrator_weekly_rotation) == 6
    })

    return validation_results


def get_configuration_summary() -> Dict[str, str]:
    """Get a summary of the current configuration for admin dashboard."""
    return {
        "app_version": settings.app_version,
        "environment": settings.environment,
        "database_configured": "✅" if settings.database_url else "❌",
        "fmp_api_configured": "✅" if settings.fmp_api_key else "❌",
        "runpod_configured": "✅" if settings.runpod_api_key and settings.runpod_endpoint_id else "❌",
        "groq_vision_configured": "✅" if settings.groq_api_key else "❌",
        "grok_social_configured": "✅" if settings.grok_api_key else "❌",
        "arbitrator_models": len([k for k in [
            settings.deepseek_api_key,
            settings.gemini_api_key,
            settings.claude_api_key,
            settings.openai_api_key
        ] if k]),
        "current_arbitrator": settings.get_current_arbitrator(),
        "kill_switch_status": "Enabled" if settings.kill_switch_enabled else "Disabled",
        "market_hours": "Open" if settings.is_market_hours() else "Closed",
        "tier_configuration": f"ALL→ACTIVE({settings.tier_active_count})→SHORT_LIST({settings.tier_short_list_count})→PICKS({settings.tier_picks_count_min}-{settings.tier_picks_count_max})"
    }


# Export commonly used settings for convenience
DATABASE_URL = settings.get_database_url()
REDIS_URL = settings.get_redis_url()
CURRENT_ARBITRATOR = settings.get_current_arbitrator()
IS_PRODUCTION = settings.environment == "production"
IS_DEVELOPMENT = settings.environment == "development"
