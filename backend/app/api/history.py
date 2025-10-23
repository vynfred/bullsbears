"""
API endpoints for option history tracking and back testing.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
import json
import yfinance as yf
from pydantic import BaseModel

from ..core.database import get_db
from ..models import ChosenOption, OptionPriceHistory
from ..services.ai_option_generator import AIOptionPlay

router = APIRouter()


class ChooseOptionRequest(BaseModel):
    symbol: str
    company_name: str
    option_type: str
    strike: float
    expiration: str
    entry_price: float
    target_price: float
    stop_loss: float
    confidence_score: float
    ai_recommendation: str
    position_size: int
    max_profit: float
    max_loss: float
    risk_reward_ratio: float
    summary: str
    key_factors: List[str]


class ChosenOptionResponse(BaseModel):
    id: int
    symbol: str
    company_name: str
    option_type: str
    strike: float
    expiration: str
    entry_price: float
    target_price: float
    stop_loss: float
    confidence_score: float
    ai_recommendation: str
    chosen_at: datetime
    position_size: int
    max_profit: float
    max_loss: float
    risk_reward_ratio: float
    summary: str
    key_factors: List[str]
    is_expired: bool
    final_price: Optional[float]
    actual_profit_loss: Optional[float]


class OptionPricePoint(BaseModel):
    timestamp: datetime
    price: float
    underlying_price: Optional[float]


class OptionChartData(BaseModel):
    chosen_option: ChosenOptionResponse
    price_history: List[OptionPricePoint]
    current_price: Optional[float]
    current_profit_loss: Optional[float]


@router.post("/choose-option", response_model=dict)
async def choose_option(
    request: ChooseOptionRequest,
    db: Session = Depends(get_db)
):
    """
    Save a chosen option play to history.
    """
    try:
        # Create new chosen option record
        chosen_option = ChosenOption(
            symbol=request.symbol,
            company_name=request.company_name,
            option_type=request.option_type,
            strike=request.strike,
            expiration=request.expiration,
            entry_price=request.entry_price,
            target_price=request.target_price,
            stop_loss=request.stop_loss,
            confidence_score=request.confidence_score,
            ai_recommendation=request.ai_recommendation,
            position_size=request.position_size,
            max_profit=request.max_profit,
            max_loss=request.max_loss,
            risk_reward_ratio=request.risk_reward_ratio,
            summary=request.summary,
            key_factors=json.dumps(request.key_factors),
            chosen_at=datetime.utcnow()
        )
        
        db.add(chosen_option)
        db.commit()
        db.refresh(chosen_option)
        
        # Record initial price point
        price_history = OptionPriceHistory(
            chosen_option_id=chosen_option.id,
            symbol=request.symbol,
            option_type=request.option_type,
            strike=request.strike,
            expiration=request.expiration,
            price=request.entry_price,
            timestamp=datetime.utcnow()
        )
        
        db.add(price_history)
        db.commit()
        
        return {
            "success": True,
            "message": "Option play saved to history",
            "chosen_option_id": chosen_option.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save option: {str(e)}")


@router.get("/chosen-options", response_model=List[ChosenOptionResponse])
async def get_chosen_options(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get all chosen option plays ordered by most recent.
    """
    try:
        chosen_options = db.query(ChosenOption)\
            .order_by(desc(ChosenOption.chosen_at))\
            .limit(limit)\
            .all()
        
        result = []
        for option in chosen_options:
            key_factors = json.loads(option.key_factors) if option.key_factors else []
            result.append(ChosenOptionResponse(
                id=option.id,
                symbol=option.symbol,
                company_name=option.company_name,
                option_type=option.option_type,
                strike=option.strike,
                expiration=option.expiration,
                entry_price=option.entry_price,
                target_price=option.target_price,
                stop_loss=option.stop_loss,
                confidence_score=option.confidence_score,
                ai_recommendation=option.ai_recommendation,
                chosen_at=option.chosen_at,
                position_size=option.position_size,
                max_profit=option.max_profit,
                max_loss=option.max_loss,
                risk_reward_ratio=option.risk_reward_ratio,
                summary=option.summary,
                key_factors=key_factors,
                is_expired=option.is_expired,
                final_price=option.final_price,
                actual_profit_loss=option.actual_profit_loss
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve options: {str(e)}")


@router.get("/option-chart/{option_id}", response_model=OptionChartData)
async def get_option_chart(
    option_id: int,
    db: Session = Depends(get_db)
):
    """
    Get chart data for a specific chosen option.
    """
    try:
        # Get the chosen option
        chosen_option = db.query(ChosenOption).filter(ChosenOption.id == option_id).first()
        if not chosen_option:
            raise HTTPException(status_code=404, detail="Option not found")
        
        # Get price history
        price_history = db.query(OptionPriceHistory)\
            .filter(OptionPriceHistory.chosen_option_id == option_id)\
            .order_by(OptionPriceHistory.timestamp)\
            .all()
        
        # Convert to response format
        key_factors = json.loads(chosen_option.key_factors) if chosen_option.key_factors else []
        chosen_option_response = ChosenOptionResponse(
            id=chosen_option.id,
            symbol=chosen_option.symbol,
            company_name=chosen_option.company_name,
            option_type=chosen_option.option_type,
            strike=chosen_option.strike,
            expiration=chosen_option.expiration,
            entry_price=chosen_option.entry_price,
            target_price=chosen_option.target_price,
            stop_loss=chosen_option.stop_loss,
            confidence_score=chosen_option.confidence_score,
            ai_recommendation=chosen_option.ai_recommendation,
            chosen_at=chosen_option.chosen_at,
            position_size=chosen_option.position_size,
            max_profit=chosen_option.max_profit,
            max_loss=chosen_option.max_loss,
            risk_reward_ratio=chosen_option.risk_reward_ratio,
            summary=chosen_option.summary,
            key_factors=key_factors,
            is_expired=chosen_option.is_expired,
            final_price=chosen_option.final_price,
            actual_profit_loss=chosen_option.actual_profit_loss
        )
        
        price_points = [
            OptionPricePoint(
                timestamp=point.timestamp,
                price=point.price,
                underlying_price=point.underlying_price
            )
            for point in price_history
        ]
        
        # Calculate current profit/loss if not expired
        current_price = None
        current_profit_loss = None
        if not chosen_option.is_expired and price_history:
            latest_price = price_history[-1].price
            current_price = latest_price
            price_diff = latest_price - chosen_option.entry_price
            current_profit_loss = price_diff * chosen_option.position_size * 100  # Assuming standard option multiplier
        
        return OptionChartData(
            chosen_option=chosen_option_response,
            price_history=price_points,
            current_price=current_price,
            current_profit_loss=current_profit_loss
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chart data: {str(e)}")


@router.post("/backtest", response_model=dict)
async def backtest_options(
    db: Session = Depends(get_db)
):
    """
    Run back test analysis on all chosen options.
    """
    try:
        chosen_options = db.query(ChosenOption).all()
        
        total_plays = len(chosen_options)
        profitable_plays = 0
        total_profit_loss = 0.0
        
        for option in chosen_options:
            if option.actual_profit_loss is not None:
                total_profit_loss += option.actual_profit_loss
                if option.actual_profit_loss > 0:
                    profitable_plays += 1
        
        win_rate = (profitable_plays / total_plays * 100) if total_plays > 0 else 0
        
        return {
            "success": True,
            "backtest_results": {
                "total_plays": total_plays,
                "profitable_plays": profitable_plays,
                "losing_plays": total_plays - profitable_plays,
                "win_rate": round(win_rate, 2),
                "total_profit_loss": round(total_profit_loss, 2),
                "average_profit_loss": round(total_profit_loss / total_plays, 2) if total_plays > 0 else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run backtest: {str(e)}")
