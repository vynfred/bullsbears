"""
Main FastAPI application for Options Trading Analyzer.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog
import time
from datetime import datetime, timedelta

from .core.config import settings
from .core.database import init_db, close_db
from .core.redis_client import redis_client
from .api.v1 import analysis, recommendations
from .api import history
from .services.ai_option_generator import AIOptionGenerator
from .websocket import live_data

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Options Trading Analyzer API", version=settings.app_version)
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Initialize Redis (optional for development)
        try:
            await redis_client.connect()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning("Redis connection failed, continuing without caching", error=str(e))
        
        # Add startup timestamp to Redis
        await redis_client.set("app:startup_time", int(time.time()))

        # Log API configuration status
        import os
        critical_apis = {
            "Alpha Vantage": bool(os.getenv("ALPHA_VANTAGE_API_KEY") and os.getenv("ALPHA_VANTAGE_API_KEY") != "demo"),
            "News API": bool(os.getenv("NEWS_API_KEY") and os.getenv("NEWS_API_KEY") != "demo")
        }
        optional_apis = {
            "Reddit": bool(os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET")),
            "Twitter": bool(os.getenv("TWITTER_API_KEY") and os.getenv("TWITTER_SECRET")),
            "Finnhub": bool(os.getenv("FINNHUB_API_KEY") and os.getenv("FINNHUB_API_KEY") != "demo"),
            "Grok AI": bool(os.getenv("GROK_API_KEY") and os.getenv("GROK_API_KEY") != "demo")
        }

        critical_configured = sum(critical_apis.values())
        total_critical = len(critical_apis)
        optional_configured = sum(optional_apis.values())

        logger.info("API Configuration Status",
                   critical_configured=f"{critical_configured}/{total_critical}",
                   optional_configured=f"{optional_configured}/{len(optional_apis)}",
                   demo_mode=critical_configured < total_critical)

        if critical_configured < total_critical:
            logger.warning("Running in DEMO MODE - Some critical APIs not configured")
            for api, configured in critical_apis.items():
                if not configured:
                    logger.warning(f"Missing critical API: {api}")
        else:
            logger.info("All critical APIs configured - Full functionality available")

        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Options Trading Analyzer API")
    
    try:
        # Close database connections
        await close_db()
        logger.info("Database connections closed")
        
        # Close Redis connections
        try:
            await redis_client.disconnect()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.warning("Error closing Redis connections", error=str(e))
        
        logger.info("Application shutdown completed successfully")
        
    except Exception as e:
        logger.error("Error during application shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Real-time options trading analysis with confidence-rated recommendations",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=settings.get_allowed_methods(),
    allow_headers=settings.get_allowed_headers(),
)

# Add trusted host middleware for security
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )

# Include API routers
app.include_router(analysis.router)
app.include_router(recommendations.router)
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(live_data.router, tags=["websocket"])


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time
    )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        method=request.method,
        url=str(request.url),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": id(request)
        }
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "version": settings.app_version,
        "service": settings.app_name
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependency status."""
    health_status = {
        "status": "healthy",
        "timestamp": int(time.time()),
        "version": settings.app_version,
        "service": settings.app_name,
        "dependencies": {}
    }

    # Check Redis connection (optional)
    try:
        if redis_client.client:
            await redis_client.client.ping()
            health_status["dependencies"]["redis"] = {"status": "healthy"}
        else:
            health_status["dependencies"]["redis"] = {"status": "not_configured"}
    except Exception as e:
        health_status["dependencies"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        # Don't mark as degraded since Redis is optional for development

    # Check database connection (basic check)
    try:
        from .core.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        health_status["dependencies"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["dependencies"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    return health_status


@app.get("/health/config")
async def configuration_health_check():
    """Check API configuration status without exposing sensitive data."""
    import os

    # Define API configurations
    api_configs = {
        "critical": {
            "alpha_vantage": bool(os.getenv("ALPHA_VANTAGE_API_KEY") and os.getenv("ALPHA_VANTAGE_API_KEY") != "demo"),
            "news_api": bool(os.getenv("NEWS_API_KEY") and os.getenv("NEWS_API_KEY") != "demo")
        },
        "optional": {
            "reddit": bool(os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET")),
            "twitter": bool(os.getenv("TWITTER_API_KEY") and os.getenv("TWITTER_SECRET")),
            "finnhub": bool(os.getenv("FINNHUB_API_KEY") and os.getenv("FINNHUB_API_KEY") != "demo"),
            "grok_ai": bool(os.getenv("GROK_API_KEY") and os.getenv("GROK_API_KEY") != "demo")
        }
    }

    # Calculate overall status
    critical_configured = sum(api_configs["critical"].values())
    total_critical = len(api_configs["critical"])
    optional_configured = sum(api_configs["optional"].values())
    total_optional = len(api_configs["optional"])

    # Determine status
    if critical_configured == total_critical:
        if optional_configured == total_optional:
            status = "fully_configured"
            status_color = "green"
        else:
            status = "partially_configured"
            status_color = "yellow"
    else:
        status = "missing_critical"
        status_color = "red"

    # Check if in demo mode
    demo_mode = critical_configured < total_critical

    return {
        "status": status,
        "status_color": status_color,
        "demo_mode": demo_mode,
        "critical_apis": {
            "configured": critical_configured,
            "total": total_critical,
            "apis": api_configs["critical"]
        },
        "optional_apis": {
            "configured": optional_configured,
            "total": total_optional,
            "apis": api_configs["optional"]
        },
        "timestamp": int(time.time())
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs" if settings.debug else "Documentation not available in production",
        "health_check": "/health",
        "disclaimer": "This application provides analysis for educational purposes only. Not financial advice."
    }


# AI Option Generation Endpoint
@app.post("/api/v1/generate-plays")
async def generate_option_plays(
    max_plays: int = 5,
    min_confidence: float = 70.0,
    timeframe_days: int = 7,
    position_size: float = 1000.0,
    risk_tolerance: str = "MODERATE",
    directional_bias: str = "AI_DECIDES"
):
    """
    Generate AI-powered option plays with comprehensive analysis.

    Args:
        max_plays: Maximum number of plays to generate (1-5)
        min_confidence: Minimum confidence threshold (70-100)
        timeframe_days: Target timeframe in days (1-30)
        position_size: Dollar amount to invest per play
        risk_tolerance: Risk tolerance level (LOW, MODERATE, HIGH)
        directional_bias: Directional bias (BULLISH, BEARISH, AI_DECIDES)
    """
    try:
        # Check rate limit (5 generations per day)
        rate_limit_key = "ai_generations:daily"
        current_count = await redis_client.get(rate_limit_key) or 0
        current_count = int(current_count)

        if current_count >= 5:
            return {
                "success": False,
                "error": "Daily limit of 5 AI generations reached. Limit resets at midnight EST.",
                "plays": [],
                "count": 0,
                "rate_limit_exceeded": True,
                "current_usage": current_count,
                "daily_limit": 5
            }

        # Validate parameters
        max_plays = max(1, min(max_plays, 5))
        min_confidence = max(50.0, min(min_confidence, 100.0))  # Allow lower confidence for testing
        timeframe_days = max(1, min(timeframe_days, 30))
        position_size = max(100.0, min(position_size, 10000.0))

        if risk_tolerance not in ["LOW", "MODERATE", "HIGH"]:
            risk_tolerance = "MODERATE"

        if directional_bias not in ["BULLISH", "BEARISH", "AI_DECIDES"]:
            directional_bias = "AI_DECIDES"

        # Generate option plays
        generator = AIOptionGenerator()
        plays = await generator.generate_option_plays(
            max_plays=max_plays,
            min_confidence=min_confidence,
            timeframe_days=timeframe_days,
            position_size_dollars=position_size,
            risk_tolerance=risk_tolerance,
            directional_bias=directional_bias
        )

        # Convert to serializable format
        plays_data = []
        for play in plays:
            plays_data.append({
                "symbol": play.symbol,
                "company_name": play.company_name,
                "option_type": play.option_type,
                "strike": play.strike,
                "expiration": play.expiration,
                "entry_price": play.entry_price,
                "target_price": play.target_price,
                "stop_loss": play.stop_loss,
                "probability_profit": play.probability_profit,
                "max_profit": play.max_profit,
                "max_loss": play.max_loss,
                "risk_reward_ratio": play.risk_reward_ratio,
                "position_size": play.position_size,
                "confidence_score": play.confidence_score,
                "technical_score": play.technical_score,
                "news_sentiment": play.news_sentiment,
                "catalyst_impact": play.catalyst_impact,
                "volume_score": play.volume_score,
                "ai_recommendation": play.ai_recommendation,
                "ai_confidence": play.ai_confidence,
                "risk_warning": play.risk_warning,
                "summary": play.summary,
                "key_factors": play.key_factors,
                "catalysts": play.catalysts,
                "volume_alerts": play.volume_alerts,
                "polymarket_events": play.polymarket_events,
                "generated_at": play.generated_at.isoformat(),
                "expires_at": play.expires_at.isoformat()
            })

        # Increment rate limit counter (expires at midnight EST)
        import pytz
        est = pytz.timezone('US/Eastern')
        now_est = datetime.now(est)
        midnight_est = now_est.replace(hour=23, minute=59, second=59, microsecond=999999) + timedelta(seconds=1)
        seconds_until_midnight = int((midnight_est - now_est).total_seconds())

        await redis_client.cache_with_ttl(rate_limit_key, current_count + 1, seconds_until_midnight)

        return {
            "success": True,
            "plays": plays_data,
            "count": len(plays_data),
            "parameters": {
                "max_plays": max_plays,
                "min_confidence": min_confidence,
                "timeframe_days": timeframe_days,
                "position_size": position_size,
                "risk_tolerance": risk_tolerance,
                "directional_bias": directional_bias
            },
            "generated_at": datetime.now().isoformat(),
            "rate_limit_info": {
                "current_usage": current_count + 1,
                "daily_limit": 5,
                "remaining": max(0, 4 - current_count)
            }
        }

    except Exception as e:
        logger.error(f"Error generating option plays: {e}")
        return {
            "success": False,
            "error": str(e),
            "plays": [],
            "count": 0
        }


@app.get("/api/v1/rate-limit-status")
async def get_rate_limit_status():
    """Get current rate limit status for AI generations."""
    try:
        rate_limit_key = "ai_generations:daily"
        current_count = await redis_client.get(rate_limit_key) or 0
        current_count = int(current_count)

        # Calculate time until reset
        import pytz
        est = pytz.timezone('US/Eastern')
        now_est = datetime.now(est)
        midnight_est = now_est.replace(hour=23, minute=59, second=59, microsecond=999999) + timedelta(seconds=1)
        seconds_until_reset = int((midnight_est - now_est).total_seconds())

        return {
            "current_usage": current_count,
            "daily_limit": 5,
            "remaining": max(0, 5 - current_count),
            "resets_in_seconds": seconds_until_reset,
            "reset_time_est": midnight_est.isoformat(),
            "can_generate": current_count < 5
        }
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        return {
            "current_usage": 0,
            "daily_limit": 5,
            "remaining": 5,
            "resets_in_seconds": 86400,
            "reset_time_est": None,
            "can_generate": True
        }

# Include API routers (will be added in next phase)
# from .api.v1 import api_router
# app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
