"""
User preferences and settings models.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text
from sqlalchemy.sql import func

from ..core.database import Base


class UserPreferences(Base):
    """User preferences and trading settings."""
    
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), unique=True, index=True, nullable=False)  # Anonymous user ID
    
    # Trading preferences
    risk_tolerance = Column(String(20), default="moderate")  # conservative, moderate, aggressive
    max_position_size = Column(Float, default=1000.0)  # Maximum position size in dollars
    preferred_expiration_days = Column(Integer, default=30)  # Preferred days to expiration
    min_confidence_threshold = Column(Float, default=70.0)  # Minimum confidence for recommendations

    # Advanced options settings
    shares_owned = Column(JSON, default=dict)  # Dict of {symbol: shares} for covered strategies
    iv_threshold = Column(Float, default=50.0)  # Max implied volatility threshold (20-80%)
    earnings_alert = Column(Boolean, default=True)  # Include/avoid trades near earnings
    insight_style = Column(String(30), default="professional_trader")  # cautious_trader, professional_trader, degenerate_gambler
    
    # Notification preferences
    email_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)
    high_confidence_alerts = Column(Boolean, default=True)
    market_open_alerts = Column(Boolean, default=False)
    
    # Display preferences
    theme = Column(String(10), default="dark")  # dark, light
    default_chart_timeframe = Column(String(10), default="1D")  # 1D, 5D, 1M, 3M, 6M, 1Y
    show_greeks = Column(Boolean, default=True)
    show_technical_indicators = Column(Boolean, default=True)
    
    # Watchlist and favorites
    watchlist_symbols = Column(JSON, default=list)  # List of stock symbols
    favorite_strategies = Column(JSON, default=list)  # List of preferred option strategies
    
    # Analysis weights (custom confidence scoring)
    technical_weight = Column(Float, default=35.0)
    news_weight = Column(Float, default=25.0)
    social_weight = Column(Float, default=20.0)
    earnings_weight = Column(Float, default=15.0)
    market_weight = Column(Float, default=5.0)
    
    # Trading hours preferences
    timezone = Column(String(50), default="America/New_York")
    trading_hours_only = Column(Boolean, default=True)
    extended_hours = Column(Boolean, default=False)
    
    # Data source preferences
    preferred_data_source = Column(String(50), default="alpha_vantage")
    backup_data_enabled = Column(Boolean, default=True)
    
    # Privacy and analytics
    analytics_enabled = Column(Boolean, default=True)
    data_sharing_enabled = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<UserPreferences(user_id='{self.user_id}', risk_tolerance='{self.risk_tolerance}')>"
    
    def to_dict(self):
        """Convert preferences to dictionary for API responses."""
        return {
            "user_id": self.user_id,
            "risk_tolerance": self.risk_tolerance,
            "max_position_size": self.max_position_size,
            "preferred_expiration_days": self.preferred_expiration_days,
            "min_confidence_threshold": self.min_confidence_threshold,
            "shares_owned": self.shares_owned or {},
            "iv_threshold": self.iv_threshold,
            "earnings_alert": self.earnings_alert,
            "risk_profile": self.risk_profile,
            "email_notifications": self.email_notifications,
            "push_notifications": self.push_notifications,
            "high_confidence_alerts": self.high_confidence_alerts,
            "market_open_alerts": self.market_open_alerts,
            "theme": self.theme,
            "default_chart_timeframe": self.default_chart_timeframe,
            "show_greeks": self.show_greeks,
            "show_technical_indicators": self.show_technical_indicators,
            "watchlist_symbols": self.watchlist_symbols or [],
            "favorite_strategies": self.favorite_strategies or [],
            "technical_weight": self.technical_weight,
            "news_weight": self.news_weight,
            "social_weight": self.social_weight,
            "earnings_weight": self.earnings_weight,
            "market_weight": self.market_weight,
            "timezone": self.timezone,
            "trading_hours_only": self.trading_hours_only,
            "extended_hours": self.extended_hours,
            "preferred_data_source": self.preferred_data_source,
            "backup_data_enabled": self.backup_data_enabled,
            "analytics_enabled": self.analytics_enabled,
            "data_sharing_enabled": self.data_sharing_enabled,
        }
