"""
User Preferences API endpoints for managing trading settings and advanced options configuration.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging

from ...core.database import get_db
from ...models.user_preferences import UserPreferences
from ...services.risk_profile_service import RiskProfileService, InsightStyle, MarketOutlook

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/preferences/{user_id}")
async def get_user_preferences(
    user_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user preferences and trading settings.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        User preferences including advanced options settings
    """
    try:
        # Get or create user preferences
        preferences = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if not preferences:
            # Create default preferences
            preferences = UserPreferences(user_id=user_id)
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
        
        return {
            "success": True,
            "data": preferences.to_dict(),
            "message": "User preferences retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving preferences for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve preferences: {str(e)}")


@router.put("/preferences/{user_id}")
async def update_user_preferences(
    user_id: str,
    preferences_data: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update user preferences and trading settings.
    
    Args:
        user_id: User identifier
        preferences_data: Updated preferences data
        db: Database session
        
    Returns:
        Updated user preferences
    """
    try:
        # Get or create user preferences
        preferences = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if not preferences:
            preferences = UserPreferences(user_id=user_id)
            db.add(preferences)
        
        # Update preferences with provided data
        for key, value in preferences_data.items():
            if hasattr(preferences, key):
                setattr(preferences, key, value)
        
        db.commit()
        db.refresh(preferences)
        
        return {
            "success": True,
            "data": preferences.to_dict(),
            "message": "User preferences updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating preferences for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")


@router.get("/insight-styles")
async def get_insight_styles() -> Dict[str, Any]:
    """
    Get available insight styles and their descriptions.

    Returns:
        Insight styles with strategies and characteristics
    """
    try:
        risk_service = RiskProfileService()

        profiles = {}
        for style in InsightStyle:
            description = risk_service.get_insight_style_description(style)
            strategies = risk_service.get_all_strategies_for_profile(style)
            sizing_rules = risk_service.get_position_sizing_rules(style)
            
            profiles[style.value] = {
                "description": description,
                "strategies": {
                    outlook.value: [
                        {
                            "name": strategy.name,
                            "description": strategy.description,
                            "risk_level": strategy.risk_level,
                            "max_loss": strategy.max_loss,
                            "profit_potential": strategy.profit_potential,
                            "delta_range": strategy.delta_range,
                            "theta_focus": strategy.theta_focus,
                            "vega_sensitivity": strategy.vega_sensitivity
                        }
                        for strategy in strategy_list
                    ]
                    for outlook, strategy_list in strategies.items()
                },
                "sizing_rules": sizing_rules
            }
        
        return {
            "success": True,
            "data": profiles,
            "message": "Insight styles retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving insight styles: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve insight styles: {str(e)}")


@router.post("/preferences/{user_id}/shares")
async def update_shares_owned(
    user_id: str,
    shares_data: Dict[str, int],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update shares owned for covered call strategies.
    
    Args:
        user_id: User identifier
        shares_data: Dictionary of {symbol: shares_count}
        db: Database session
        
    Returns:
        Updated shares owned data
    """
    try:
        preferences = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if not preferences:
            preferences = UserPreferences(user_id=user_id)
            db.add(preferences)
        
        # Update shares owned
        current_shares = preferences.shares_owned or {}
        current_shares.update(shares_data)
        preferences.shares_owned = current_shares
        
        db.commit()
        db.refresh(preferences)
        
        return {
            "success": True,
            "data": {
                "shares_owned": preferences.shares_owned,
                "covered_call_eligible": [
                    symbol for symbol, shares in preferences.shares_owned.items() 
                    if shares >= 100
                ]
            },
            "message": "Shares owned updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating shares for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update shares: {str(e)}")


@router.get("/preferences/{user_id}/covered-calls")
async def get_covered_call_opportunities(
    user_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get covered call opportunities based on user's share holdings.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        Available covered call opportunities
    """
    try:
        preferences = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if not preferences or not preferences.shares_owned:
            return {
                "success": True,
                "data": {
                    "opportunities": [],
                    "message": "No share holdings found for covered call strategies"
                }
            }
        
        opportunities = []
        for symbol, shares in preferences.shares_owned.items():
            if shares >= 100:
                contracts_available = shares // 100
                opportunities.append({
                    "symbol": symbol,
                    "shares_owned": shares,
                    "contracts_available": contracts_available,
                    "strategy": "Covered Call",
                    "description": f"Sell calls against {shares} shares of {symbol}"
                })
        
        return {
            "success": True,
            "data": {
                "opportunities": opportunities,
                "total_symbols": len(opportunities)
            },
            "message": f"Found {len(opportunities)} covered call opportunities"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving covered call opportunities for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve opportunities: {str(e)}")


@router.get("/preferences/defaults")
async def get_default_preferences() -> Dict[str, Any]:
    """
    Get default preference values for new users.
    
    Returns:
        Default preference settings
    """
    return {
        "success": True,
        "data": {
            "risk_tolerance": "moderate",
            "max_position_size": 1000.0,
            "preferred_expiration_days": 30,
            "min_confidence_threshold": 70.0,
            "shares_owned": {},
            "iv_threshold": 50.0,
            "earnings_alert": True,
            "insight_style": "professional_trader",
            "theme": "dark",
            "show_greeks": True,
            "show_technical_indicators": True
        },
        "message": "Default preferences retrieved successfully"
    }
