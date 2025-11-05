"""
Bullish Alerts API - Endpoints for "When Bullish?" pattern alerts
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from ...core.database import get_db
from ...models.analysis_results import AnalysisResult, AlertType, AlertOutcome
from ...analyzers.bullish_analyzer import BullishAnalyzer, analyze_bullish_potential

router = APIRouter(prefix="/bullish_alerts", tags=["bullish_alerts"])


class BullishAlertResponse(BaseModel):
    """Response model for bullish alerts"""
    id: int
    symbol: str
    company_name: Optional[str]
    confidence: float
    reasons: List[str]
    technical_score: float
    sentiment_score: float
    social_score: float
    earnings_score: float
    timestamp: datetime
    target_timeframe: str
    risk_factors: List[str]
    alert_outcome: Optional[str]
    actual_move_percent: Optional[float]
    days_to_move: Optional[int]

    class Config:
        from_attributes = True


class MoonAnalysisRequest(BaseModel):
    """Request model for moon analysis"""
    symbol: str
    company_name: Optional[str] = None


class MoonAnalysisResponse(BaseModel):
    """Response model for moon analysis"""
    symbol: str
    company_name: Optional[str]
    has_alert: bool
    confidence: Optional[float]
    reasons: Optional[List[str]]
    technical_score: Optional[float]
    sentiment_score: Optional[float]
    social_score: Optional[float]
    earnings_score: Optional[float]
    risk_factors: Optional[List[str]]
    message: str


@router.get("/", response_model=List[BullishAlertResponse])
async def get_moon_alerts(
    limit: int = Query(50, le=200, description="Maximum number of alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    outcome: Optional[str] = Query(None, description="Filter by outcome (PENDING, SUCCESS, FAILURE, PARTIAL)"),
    min_confidence: Optional[float] = Query(None, ge=0, le=100, description="Minimum confidence score"),
    days_back: Optional[int] = Query(7, ge=1, le=90, description="Days back to search"),
    db: Session = Depends(get_db)
):
    """
    Get moon alerts with optional filtering.
    Returns alerts for potential +20% stock jumps.
    """
    try:
        # Build query
        query = db.query(AnalysisResult).filter(
            AnalysisResult.alert_type == AlertType.MOON
        )
        
        # Apply filters
        if symbol:
            query = query.filter(AnalysisResult.symbol.ilike(f"%{symbol}%"))
            
        if outcome:
            try:
                outcome_enum = AlertOutcome(outcome.upper())
                query = query.filter(AnalysisResult.alert_outcome == outcome_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid outcome: {outcome}")
        
        if min_confidence is not None:
            query = query.filter(AnalysisResult.pattern_confidence >= min_confidence)
            
        # Time filter
        cutoff_date = datetime.now() - timedelta(days=days_back)
        query = query.filter(AnalysisResult.timestamp >= cutoff_date)
        
        # Order by timestamp (newest first) and apply pagination
        alerts = query.order_by(desc(AnalysisResult.timestamp)).offset(offset).limit(limit).all()
        
        # Convert to response format
        response_alerts = []
        for alert in alerts:
            features = alert.features_json or {}
            
            response_alert = BullishAlertResponse(
                id=alert.id,
                symbol=alert.symbol,
                company_name=alert.symbol,  # Could be enhanced with actual company names
                confidence=alert.pattern_confidence or alert.confidence_score,
                reasons=features.get('reasons', []),
                technical_score=alert.technical_score,
                sentiment_score=alert.news_sentiment_score,
                social_score=alert.social_sentiment_score,
                earnings_score=alert.earnings_score,
                timestamp=alert.timestamp,
                target_timeframe=features.get('target_timeframe', '1-3 days'),
                risk_factors=features.get('risk_factors', []),
                alert_outcome=alert.alert_outcome.value if alert.alert_outcome else None,
                actual_move_percent=alert.actual_move_percent,
                days_to_move=alert.days_to_move
            )
            response_alerts.append(response_alert)
        
        return response_alerts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving moon alerts: {str(e)}")


@router.get("/latest", response_model=List[BullishAlertResponse])
async def get_latest_moon_alerts(
    limit: int = Query(10, le=50, description="Number of latest alerts to return"),
    db: Session = Depends(get_db)
):
    """
    Get the latest moon alerts.
    Optimized endpoint for dashboard display.
    """
    try:
        alerts = db.query(AnalysisResult).filter(
            AnalysisResult.alert_type == AlertType.MOON
        ).order_by(desc(AnalysisResult.timestamp)).limit(limit).all()
        
        response_alerts = []
        for alert in alerts:
            features = alert.features_json or {}
            
            response_alert = BullishAlertResponse(
                id=alert.id,
                symbol=alert.symbol,
                company_name=alert.symbol,
                confidence=alert.pattern_confidence or alert.confidence_score,
                reasons=features.get('reasons', []),
                technical_score=alert.technical_score,
                sentiment_score=alert.news_sentiment_score,
                social_score=alert.social_sentiment_score,
                earnings_score=alert.earnings_score,
                timestamp=alert.timestamp,
                target_timeframe=features.get('target_timeframe', '1-3 days'),
                risk_factors=features.get('risk_factors', []),
                alert_outcome=alert.alert_outcome.value if alert.alert_outcome else None,
                actual_move_percent=alert.actual_move_percent,
                days_to_move=alert.days_to_move
            )
            response_alerts.append(response_alert)
        
        return response_alerts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest moon alerts: {str(e)}")


@router.post("/analyze", response_model=MoonAnalysisResponse)
async def analyze_symbol_for_moon(
    request: MoonAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze a specific symbol for moon potential.
    Returns real-time analysis without storing as an alert.
    """
    try:
        # Validate symbol
        if not request.symbol or len(request.symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol")
        
        symbol = request.symbol.upper().strip()
        
        # Run moon analysis
        alert = await analyze_moon_potential(symbol, request.company_name)
        
        if alert:
            return MoonAnalysisResponse(
                symbol=symbol,
                company_name=request.company_name or symbol,
                has_alert=True,
                confidence=alert.confidence,
                reasons=alert.reasons,
                technical_score=alert.technical_score,
                sentiment_score=alert.sentiment_score,
                social_score=alert.social_score,
                earnings_score=alert.earnings_score,
                risk_factors=alert.risk_factors,
                message=f"Moon potential detected with {alert.confidence:.1f}% confidence"
            )
        else:
            return MoonAnalysisResponse(
                symbol=symbol,
                company_name=request.company_name or symbol,
                has_alert=False,
                confidence=None,
                reasons=None,
                technical_score=None,
                sentiment_score=None,
                social_score=None,
                earnings_score=None,
                risk_factors=None,
                message="No significant moon potential detected at this time"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing symbol: {str(e)}")


@router.get("/stats")
async def get_moon_alert_stats(
    days_back: int = Query(30, ge=1, le=365, description="Days back for statistics"),
    db: Session = Depends(get_db)
):
    """
    Get statistics about moon alert performance.
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Total alerts
        total_alerts = db.query(AnalysisResult).filter(
            and_(
                AnalysisResult.alert_type == AlertType.MOON,
                AnalysisResult.timestamp >= cutoff_date
            )
        ).count()
        
        # Alerts by outcome
        outcomes = {}
        for outcome in AlertOutcome:
            count = db.query(AnalysisResult).filter(
                and_(
                    AnalysisResult.alert_type == AlertType.MOON,
                    AnalysisResult.timestamp >= cutoff_date,
                    AnalysisResult.alert_outcome == outcome
                )
            ).count()
            outcomes[outcome.value] = count
        
        # Success rate (only for resolved alerts)
        resolved_alerts = outcomes.get('SUCCESS', 0) + outcomes.get('FAILURE', 0) + outcomes.get('PARTIAL', 0)
        success_rate = (outcomes.get('SUCCESS', 0) / resolved_alerts * 100) if resolved_alerts > 0 else 0
        
        # Average confidence of successful alerts
        successful_alerts = db.query(AnalysisResult).filter(
            and_(
                AnalysisResult.alert_type == AlertType.MOON,
                AnalysisResult.timestamp >= cutoff_date,
                AnalysisResult.alert_outcome == AlertOutcome.SUCCESS
            )
        ).all()
        
        avg_successful_confidence = sum(a.pattern_confidence or 0 for a in successful_alerts) / len(successful_alerts) if successful_alerts else 0
        
        return {
            "period_days": days_back,
            "total_alerts": total_alerts,
            "outcomes": outcomes,
            "success_rate_percent": round(success_rate, 1),
            "average_successful_confidence": round(avg_successful_confidence, 1),
            "resolved_alerts": resolved_alerts,
            "pending_alerts": outcomes.get('PENDING', 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving moon alert stats: {str(e)}")


@router.get("/{alert_id}", response_model=BullishAlertResponse)
async def get_moon_alert_by_id(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific moon alert by ID.
    """
    try:
        alert = db.query(AnalysisResult).filter(
            and_(
                AnalysisResult.id == alert_id,
                AnalysisResult.alert_type == AlertType.MOON
            )
        ).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Moon alert not found")
        
        features = alert.features_json or {}
        
        return BullishAlertResponse(
            id=alert.id,
            symbol=alert.symbol,
            company_name=alert.symbol,
            confidence=alert.pattern_confidence or alert.confidence_score,
            reasons=features.get('reasons', []),
            technical_score=alert.technical_score,
            sentiment_score=alert.news_sentiment_score,
            social_score=alert.social_sentiment_score,
            earnings_score=alert.earnings_score,
            timestamp=alert.timestamp,
            target_timeframe=features.get('target_timeframe', '1-3 days'),
            risk_factors=features.get('risk_factors', []),
            alert_outcome=alert.alert_outcome.value if alert.alert_outcome else None,
            actual_move_percent=alert.actual_move_percent,
            days_to_move=alert.days_to_move
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving moon alert: {str(e)}")
