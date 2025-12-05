"""
Analytics API endpoints for model accuracy, recent outcomes, and accuracy trends
Provides data for the Analytics dashboard tab
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from ...core.database import get_asyncpg_pool

router = APIRouter()


class ModelAccuracyStats(BaseModel):
    """Model accuracy statistics"""
    overall_accuracy: float
    total_predictions: int
    bullish_accuracy: float = 0.0
    bearish_accuracy: float = 0.0
    high_confidence_accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0


class RecentPickOutcome(BaseModel):
    """Recent pick outcome"""
    id: int
    symbol: str
    sentiment: str  # 'bullish' or 'bearish'
    confidence: float
    outcome: str  # 'win', 'loss', 'partial'
    change_percent: float
    days_to_outcome: int
    created_at: str


class AccuracyTrendPoint(BaseModel):
    """Accuracy trend data point"""
    date: str
    accuracy: float
    total_picks: int
    bullish_accuracy: float = 0.0
    bearish_accuracy: float = 0.0


@router.get("/model-accuracy", response_model=ModelAccuracyStats)
async def get_model_accuracy():
    """
    Get overall model accuracy statistics
    Calculates win rate from pick_outcomes_detailed table
    """
    try:
        db = await get_asyncpg_pool()
        
        # Get overall accuracy (win includes win, medium_hit, moonshot)
        overall_stats = await db.fetchrow("""
            SELECT
                COUNT(*) as total_predictions,
                COALESCE(
                    ROUND(100.0 * SUM(CASE WHEN outcome IN ('win', 'medium_hit', 'moonshot') THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2),
                    0.0
                ) as overall_accuracy,
                COALESCE(
                    ROUND(100.0 * SUM(CASE WHEN outcome IN ('win', 'medium_hit', 'moonshot') AND direction = 'bullish' THEN 1 ELSE 0 END) /
                          NULLIF(SUM(CASE WHEN direction = 'bullish' THEN 1 ELSE 0 END), 0), 2),
                    0.0
                ) as bullish_accuracy,
                COALESCE(
                    ROUND(100.0 * SUM(CASE WHEN outcome IN ('win', 'medium_hit', 'moonshot') AND direction = 'bearish' THEN 1 ELSE 0 END) /
                          NULLIF(SUM(CASE WHEN direction = 'bearish' THEN 1 ELSE 0 END), 0), 2),
                    0.0
                ) as bearish_accuracy
            FROM pick_outcomes_detailed
            WHERE outcome IN ('win', 'medium_hit', 'moonshot', 'loss')
        """)
        
        # Get high confidence accuracy (>= 70%)
        high_conf_stats = await db.fetchrow("""
            SELECT
                COALESCE(
                    ROUND(100.0 * SUM(CASE WHEN pod.outcome IN ('win', 'medium_hit', 'moonshot') THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2),
                    0.0
                ) as high_confidence_accuracy
            FROM pick_outcomes_detailed pod
            JOIN picks p ON pod.pick_id = p.id
            WHERE pod.outcome IN ('win', 'medium_hit', 'moonshot', 'loss')
              AND p.confidence >= 0.70
        """)
        
        total = overall_stats['total_predictions'] or 0
        accuracy = float(overall_stats['overall_accuracy'] or 0.0)
        
        return ModelAccuracyStats(
            overall_accuracy=accuracy,
            total_predictions=total,
            bullish_accuracy=float(overall_stats['bullish_accuracy'] or 0.0),
            bearish_accuracy=float(overall_stats['bearish_accuracy'] or 0.0),
            high_confidence_accuracy=float(high_conf_stats['high_confidence_accuracy'] or 0.0),
            precision=accuracy,  # Simplified: using accuracy as precision
            recall=accuracy,     # Simplified: using accuracy as recall
            f1_score=accuracy    # Simplified: using accuracy as F1
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch model accuracy: {str(e)}")


@router.get("/recent-outcomes", response_model=List[RecentPickOutcome])
async def get_recent_outcomes(limit: int = Query(default=20, le=100)):
    """
    Get recent pick outcomes with details
    Returns completed picks with their outcomes
    """
    try:
        db = await get_asyncpg_pool()
        
        rows = await db.fetch("""
            SELECT
                pod.id,
                pod.symbol,
                pod.direction as sentiment,
                p.confidence,
                pod.outcome,
                COALESCE(pod.max_gain_percent, 0.0) as change_percent,
                COALESCE(
                    EXTRACT(DAY FROM (pod.outcome_determined_at - p.created_at)),
                    0
                ) as days_to_outcome,
                p.created_at
            FROM pick_outcomes_detailed pod
            JOIN picks p ON pod.pick_id = p.id
            WHERE pod.outcome IN ('win', 'medium_hit', 'moonshot', 'loss')
            ORDER BY pod.outcome_determined_at DESC
            LIMIT $1
        """, limit)
        
        outcomes = []
        for row in rows:
            outcomes.append(RecentPickOutcome(
                id=row['id'],
                symbol=row['symbol'],
                sentiment=row['sentiment'],
                confidence=float(row['confidence']),
                outcome=row['outcome'],
                change_percent=float(row['change_percent']),
                days_to_outcome=int(row['days_to_outcome']),
                created_at=row['created_at'].isoformat()
            ))
        
        return outcomes

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent outcomes: {str(e)}")


@router.get("/accuracy-trend", response_model=List[AccuracyTrendPoint])
async def get_accuracy_trend(period: str = Query(default="30d", regex="^(7d|30d|90d)$")):
    """
    Get accuracy trend over time
    Groups picks by day and calculates daily accuracy

    Args:
        period: Time period - '7d', '30d', or '90d'
    """
    try:
        db = await get_asyncpg_pool()

        # Parse period to days
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)

        # Get daily accuracy trend
        rows = await db.fetch("""
            SELECT
                DATE(p.created_at) as date,
                COUNT(*) as total_picks,
                COALESCE(
                    ROUND(100.0 * SUM(CASE WHEN pod.outcome IN ('win', 'medium_hit', 'moonshot') THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2),
                    0.0
                ) as accuracy,
                COALESCE(
                    ROUND(100.0 * SUM(CASE WHEN pod.outcome IN ('win', 'medium_hit', 'moonshot') AND pod.direction = 'bullish' THEN 1 ELSE 0 END) /
                          NULLIF(SUM(CASE WHEN pod.direction = 'bullish' THEN 1 ELSE 0 END), 0), 2),
                    0.0
                ) as bullish_accuracy,
                COALESCE(
                    ROUND(100.0 * SUM(CASE WHEN pod.outcome IN ('win', 'medium_hit', 'moonshot') AND pod.direction = 'bearish' THEN 1 ELSE 0 END) /
                          NULLIF(SUM(CASE WHEN pod.direction = 'bearish' THEN 1 ELSE 0 END), 0), 2),
                    0.0
                ) as bearish_accuracy
            FROM picks p
            JOIN pick_outcomes_detailed pod ON p.id = pod.pick_id
            WHERE p.created_at >= NOW() - INTERVAL '1 day' * $1
              AND pod.outcome IN ('win', 'medium_hit', 'moonshot', 'loss')
            GROUP BY DATE(p.created_at)
            ORDER BY date ASC
        """, days)

        trend_data = []
        for row in rows:
            trend_data.append(AccuracyTrendPoint(
                date=row['date'].isoformat(),
                accuracy=float(row['accuracy']),
                total_picks=row['total_picks'],
                bullish_accuracy=float(row['bullish_accuracy']),
                bearish_accuracy=float(row['bearish_accuracy'])
            ))

        return trend_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch accuracy trend: {str(e)}")

