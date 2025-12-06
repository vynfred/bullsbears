# app/models/stock_classifications.py
from sqlalchemy import Column, Integer, String, DECIMAL, BigInteger, Date, DateTime, Boolean, JSON, Index
from sqlalchemy.sql import func

from ..core.database import Base


class StockClassification(Base):
    """
    Maps to stock_classifications table in SQL
    Tracks stock tier progression: ALL → ACTIVE → SHORT_LIST → PICKS
    Updated weekly (Sunday 2 AM ET)
    """
    __tablename__ = 'stock_classifications'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    exchange = Column(String(10), default='NASDAQ', index=True)
    current_tier = Column(String(20), nullable=False, index=True)  # ALL, ACTIVE, SHORT_LIST, PICKS

    # v5 metrics for tier qualification
    last_price = Column(DECIMAL(10, 2))
    avg_volume_20d = Column(BigInteger)
    market_cap = Column(BigInteger)

    # Company info
    company_name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))

    # Tier qualification tracking
    last_qualified_date = Column(Date, index=True)
    qualified_days_count = Column(Integer, default=0)
    selection_fatigue_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_classifications_tier', 'current_tier'),
        Index('idx_classifications_symbol', 'symbol'),
        Index('idx_classifications_updated', 'updated_at'),
    )

    def __repr__(self):
        return f"<StockClassification(symbol='{self.symbol}', tier='{self.current_tier}')>"

class ShortlistCandidate(Base):
    """
    Maps to shortlist_candidates table in SQL
    Stores all 75 SHORT_LIST candidates daily (not just final picks)
    Used by Learner to analyze what we DIDN'T pick
    Complete schema with 34 columns
    """
    __tablename__ = "shortlist_candidates"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    date = Column(DateTime, nullable=False)
    rank = Column(Integer, nullable=False)  # 1-75 ranking from prescreen

    # Prescreen data
    prescreen_reason = Column(String)  # Text explanation
    prescreen_score = Column(DECIMAL(5, 4))  # Numeric score
    price_at_selection = Column(DECIMAL(10, 2))

    # Vision analysis - individual boolean flags (6 patterns)
    wyckoff_phase_2 = Column(Boolean)
    weekly_triangle_coil = Column(Boolean)
    volume_shelf_breakout = Column(Boolean)
    p_shape_profile = Column(Boolean)
    fakeout_wick_rejection = Column(Boolean)
    spring_setup = Column(Boolean)

    # Vision analysis - JSONB and text
    vision_flags = Column(JSON)  # Complete vision data
    vision_analysis_text = Column(String)

    # Social sentiment
    social_score = Column(Integer, nullable=False)  # -5 to +5
    headlines = Column(JSON)
    events = Column(JSON)
    social_data = Column(JSON)  # Complete social data

    # Polymarket probability
    polymarket_prob = Column(DECIMAL(10, 4))

    # Complete snapshots (JSONB)
    technical_snapshot = Column(JSON)
    fundamental_snapshot = Column(JSON)

    # Arbitrator output
    selected = Column(Boolean)  # Was this selected as final pick?
    arbitrator_model = Column(String(50))  # Which model selected it
    arbitrator_reason = Column(String)
    target_low = Column(DECIMAL(10, 2))
    target_high = Column(DECIMAL(10, 2))
    stop_loss = Column(DECIMAL(10, 2))
    support_level = Column(DECIMAL(10, 2))

    # Outcome tracking
    max_gain_pct = Column(DECIMAL(10, 4))
    final_gain_pct = Column(DECIMAL(10, 4))
    bullish_20pct = Column(Boolean)  # Hit +20% target
    bearish_20pct = Column(Boolean)   # Hit -20% loss

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_shortlist_date_symbol', 'date', 'symbol'),
        Index('idx_shortlist_date', 'date'),
        Index('idx_shortlist_selected', 'selected'),
        Index('idx_shortlist_prescreen_score', 'prescreen_score'),
        Index('idx_shortlist_price', 'price_at_selection'),
        Index('idx_shortlist_bullish_20pct', 'bullish_20pct'),
        Index('idx_shortlist_bearish_20pct', 'bearish_20pct'),
    )

    def __repr__(self):
        return f"<ShortlistCandidate(symbol='{self.symbol}', date='{self.date}', rank={self.rank}, selected={self.selected})>"
