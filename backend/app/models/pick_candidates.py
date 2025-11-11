"""
Pick Candidates – FINAL v3.3 (November 11, 2025)
Tracks all 75 SHORT_LIST candidates for BrainAgent learning
No legacy agent junk. Pure signal.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, List, Any

from ..core.database import Base


class ShortListCandidate(Base):
    """All 75 SHORT_LIST candidates – fuel for BrainAgent"""
    __tablename__ = "shortlist_candidates"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    date = Column(DateTime, nullable=False, default=func.now(), index=True)
    rank = Column(Integer, nullable=False)  # 1–75 from FinMA-7b
    prescreen_reason = Column(Text, nullable=True)

    # Vision flags (6 booleans)
    wyckoff_phase_2 = Column(Boolean, default=False)
    weekly_triangle_coil = Column(Boolean, default=False)
    volume_shelf_breakout = Column(Boolean, default=False)
    p_shape_profile = Column(Boolean, default=False)
    fakeout_wick_rejection = Column(Boolean, default=False)
    spring_setup = Column(Boolean, default=False)

    # Social + context
    social_score = Column(Integer, nullable=False)  # -5 to +5
    headlines = Column(JSON, nullable=True)  # top 3
    events = Column(JSON, nullable=True)
    polymarket_prob = Column(Float, nullable=True)

    # Arbitrator decision
    selected = Column(Boolean, default=False, index=True)
    arbitrator_model = Column(String(50), nullable=True)  # Gemini 2.5 Pro, etc.
    arbitrator_reason = Column(Text, nullable=True)
    target_low = Column(Float, nullable=True)
    target_high = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    support_level = Column(Float, nullable=True)

    # 30-day tracking
    max_gain_pct = Column(Float, nullable=True)
    final_gain_pct = Column(Float, nullable=True)
    moon_20pct = Column(Boolean, default=False)
    rug_20pct = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())


class FinalPick(Base):
    """The 3–6 picks sent to users"""
    __tablename__ = "final_picks"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, default=func.now(), index=True)
    symbol = Column(String(10), nullable=False)
    direction = Column(String(10), nullable=False)  # moon/rug
    confidence = Column(Integer, nullable=False)  # 0–100
    target_low = Column(Float, nullable=True)
    target_high = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    support_level = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    arbitrator_model = Column(String(50), nullable=True)

    # Link back to shortlist
    shortlist_id = Column(Integer, ForeignKey("shortlist_candidates.id"))
    shortlist = relationship("ShortListCandidate")


# === LEGACY TABLES (keep for migration only) ===
# pick_candidates → DELETE after migration
# candidate_price_tracking → DELETE
# candidate_retrospective_analysis → DELETE
# candidate_model_learning → DELETE