"""
Analytics API endpoints for detailed performance metrics and trends.
Provides data specifically for the Analytics tab in the frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta

from ...core.database import get_db
from ...services.statistics_service import statistics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/accuracy-trend")
async def get_accuracy_trend(
    period: str = Query("30d", description="Time period: 7d, 30d, or 90d"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get accuracy trend data over time for the analytics chart.
    
    Returns:
        - Daily/weekly accuracy points
        - Bullish vs bearish accuracy breakdown
        - Total picks per period
        - Confidence intervals
    """
    try:
        # Parse period
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)
        
        trend_data = await statistics_service.get_accuracy_trend(db, days)
        
        return {
            "status": "success",
            "data": trend_data,
            "period": period,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching accuracy trend: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch accuracy trend")


@router.get("/recent-outcomes")
async def get_recent_outcomes(
    limit: int = Query(10, ge=1, le=50, description="Number of recent outcomes to return"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get recent pick outcomes for the analytics carousel.
    
    Returns:
        - Recent completed picks with outcomes
        - Win/loss status
        - Percentage change achieved
        - Days to outcome
        - Confidence scores
    """
    try:
        outcomes = await statistics_service.get_recent_outcomes(db, limit)
        
        return {
            "status": "success",
            "data": outcomes,
            "count": len(outcomes),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching recent outcomes: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent outcomes")


@router.get("/performance-summary")
async def get_performance_summary(
    days: int = Query(30, ge=1, le=365, description="Days back for performance summary"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive performance summary for analytics dashboard.
    
    Returns:
        - Overall performance metrics
        - Confidence level breakdown
        - Win rates by category
        - Target hit statistics
    """
    try:
        summary = await statistics_service.get_performance_summary(db, days)
        
        return {
            "status": "success",
            "data": summary,
            "period_days": days,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching performance summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch performance summary")


@router.get("/model-metrics")
async def get_model_metrics(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed model performance metrics.
    
    Returns:
        - Precision, recall, F1 scores
        - Confusion matrix data
        - Feature importance
        - Model confidence calibration
    """
    try:
        metrics = await statistics_service.get_model_metrics(db)
        
        return {
            "status": "success",
            "data": metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching model metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch model metrics")


@router.get("/next-scan")
async def get_next_scan_info(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get information about the next scheduled scan.
    
    Returns:
        - Next scan time
        - Countdown timer data
        - Last scan results
        - System status
    """
    try:
        scan_info = await statistics_service.get_next_scan_info(db)
        
        return {
            "status": "success",
            "data": scan_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching next scan info: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch next scan info")
