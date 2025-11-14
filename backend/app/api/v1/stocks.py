from fastapi import APIRouter, HTTPException
from ...services.stock_filter_service import get_stock_filter_service

router = APIRouter()

@router.post("/filter-active")
async def filter_active_stocks(force_refresh: bool = False):
    """Manually trigger NASDAQ → ACTIVE filtering"""
    try:
        filter_service = await get_stock_filter_service()
        active_stocks = await filter_service.get_active_stocks(force_refresh=force_refresh)
        metrics = await filter_service.get_filter_metrics()
        
        return {
            "success": True,
            "active_count": len(active_stocks),
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filter-health")
async def filter_health_check():
    """Health check for stock filter service"""
    try:
        filter_service = await get_stock_filter_service()
        health = await filter_service.health_check()
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filter-metrics")
async def get_filter_metrics():
    """Get latest filtering metrics"""
    try:
        filter_service = await get_stock_filter_service()
        metrics = await filter_service.get_filter_metrics()
        return metrics or {"message": "No metrics available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
