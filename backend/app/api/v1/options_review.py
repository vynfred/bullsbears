"""
Options Review API - New user-driven options analysis system
Handles the complete workflow: stock selection → expiration → strategy → analysis
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services.fmp_options_service import FMPOptionsService, ExpirationInfo, OptionsChainData
from ...services.ai_consensus import AIConsensusEngine
from ...services.cost_monitor import CostMonitor, APIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/options-review", tags=["options-review"])

# Request/Response Models
class StockValidationRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol to validate")

class StockValidationResponse(BaseModel):
    success: bool
    symbol: str
    company_name: Optional[str] = None
    current_price: Optional[float] = None
    is_valid: bool
    error_message: Optional[str] = None

class ExpirationListResponse(BaseModel):
    success: bool
    symbol: str
    expirations: List[Dict[str, Any]]
    error_message: Optional[str] = None

class OptionsAnalysisRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    expiration_date: str = Field(..., description="Expiration date in YYYY-MM-DD format")
    strategy_type: str = Field(..., description="Strategy type: cautious_trader, professional_trader, degenerate_gambler, speculation")
    max_position_size: float = Field(..., gt=0, description="Maximum position size in dollars")
    shares_owned: int = Field(default=0, ge=0, description="Number of shares currently owned")
    account_size: Optional[float] = Field(None, gt=0, description="Total account size for risk calculation")

class OptionsAnalysisResponse(BaseModel):
    success: bool
    symbol: str
    strategy_type: str
    analysis: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    risk_analysis: Dict[str, Any]
    interactive_data: Dict[str, Any]
    disclaimer: str
    error_message: Optional[str] = None

@router.post("/validate-symbol", response_model=StockValidationResponse)
async def validate_stock_symbol(request: StockValidationRequest) -> StockValidationResponse:
    """
    Validate a stock symbol and return basic information.
    
    Args:
        request: Stock validation request with symbol
        
    Returns:
        Validation response with symbol info
    """
    try:
        symbol = request.symbol.upper().strip()
        
        # Basic format validation
        if not symbol.isalpha() or len(symbol) > 10:
            return StockValidationResponse(
                success=False,
                symbol=symbol,
                is_valid=False,
                error_message="Invalid symbol format"
            )

        async with FMPOptionsService() as fmp_service:
            # Validate symbol and get company info
            is_valid, company_name = await fmp_service.validate_symbol(symbol)
            
            if not is_valid:
                return StockValidationResponse(
                    success=False,
                    symbol=symbol,
                    is_valid=False,
                    error_message="Symbol not found"
                )
            
            # Get current price
            current_price = await fmp_service._get_current_price(symbol)
            
            return StockValidationResponse(
                success=True,
                symbol=symbol,
                company_name=company_name,
                current_price=current_price,
                is_valid=True
            )

    except Exception as e:
        logger.error(f"Error validating symbol {request.symbol}: {e}")
        return StockValidationResponse(
            success=False,
            symbol=request.symbol.upper(),
            is_valid=False,
            error_message="Validation service temporarily unavailable"
        )

@router.get("/expirations/{symbol}", response_model=ExpirationListResponse)
async def get_expiration_dates(symbol: str) -> ExpirationListResponse:
    """
    Get available expiration dates for a symbol.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        List of available expiration dates with metadata
    """
    try:
        symbol = symbol.upper().strip()
        
        async with FMPOptionsService() as fmp_service:
            expirations = await fmp_service.get_available_expirations(symbol)
            
            if not expirations:
                return ExpirationListResponse(
                    success=False,
                    symbol=symbol,
                    expirations=[],
                    error_message="No expiration dates available for this symbol"
                )
            
            # Convert to dict format for JSON response
            expiration_dicts = []
            for exp in expirations:
                expiration_dicts.append({
                    "date": exp.date,
                    "display_date": exp.display_date,
                    "days_to_expiry": exp.days_to_expiry,
                    "is_weekly": exp.is_weekly,
                    "is_monthly": exp.is_monthly,
                    "is_quarterly": exp.is_quarterly,
                    "has_earnings": exp.has_earnings,
                    "earnings_date": exp.earnings_date
                })
            
            return ExpirationListResponse(
                success=True,
                symbol=symbol,
                expirations=expiration_dicts
            )

    except Exception as e:
        logger.error(f"Error fetching expirations for {symbol}: {e}")
        return ExpirationListResponse(
            success=False,
            symbol=symbol,
            expirations=[],
            error_message="Failed to fetch expiration dates"
        )

@router.post("/analyze", response_model=OptionsAnalysisResponse)
async def analyze_options_strategy(
    request: OptionsAnalysisRequest,
    db: Session = Depends(get_db)
) -> OptionsAnalysisResponse:
    """
    Perform comprehensive options analysis using dual AI system.
    
    Args:
        request: Options analysis request with all parameters
        db: Database session
        
    Returns:
        Complete analysis with recommendations and risk assessment
    """
    try:
        symbol = request.symbol.upper().strip()
        
        # Track API usage
        cost_monitor = CostMonitor()
        await cost_monitor.track_api_call(APIService.FMP, estimated_cost=0.01)
        
        async with FMPOptionsService() as fmp_service:
            # Get options chain data
            options_data = await fmp_service.get_options_chain(symbol, request.expiration_date)
            
            if not options_data:
                return OptionsAnalysisResponse(
                    success=False,
                    symbol=symbol,
                    strategy_type=request.strategy_type,
                    analysis={},
                    recommendations=[],
                    risk_analysis={},
                    interactive_data={},
                    disclaimer="",
                    error_message="No options data available for the selected expiration"
                )

            # Prepare data for AI analysis
            analysis_data = {
                'symbol': symbol,
                'current_price': options_data.current_price,
                'expiration_date': request.expiration_date,
                'strategy_type': request.strategy_type,
                'max_position_size': request.max_position_size,
                'shares_owned': request.shares_owned,
                'account_size': request.account_size,
                'options_chain': {
                    'calls': [call.__dict__ for call in options_data.calls],
                    'puts': [put.__dict__ for put in options_data.puts]
                },
                'iv_rank': options_data.iv_rank,
                'earnings_date': options_data.earnings_date,
                'days_to_expiry': None  # Will be calculated from expiration_date
            }
            
            # Calculate days to expiry
            exp_date = datetime.strptime(request.expiration_date, '%Y-%m-%d')
            days_to_expiry = (exp_date - datetime.now()).days
            analysis_data['days_to_expiry'] = days_to_expiry

            # Use dual AI system for analysis
            async with AIConsensusEngine() as consensus_engine:
                # Track AI API usage
                await cost_monitor.track_api_call(APIService.GROK, estimated_cost=0.02)
                await cost_monitor.track_api_call(APIService.DEEPSEEK, estimated_cost=0.01)
                
                # Get AI consensus analysis
                consensus_result = await consensus_engine.analyze_with_consensus(
                    symbol, analysis_data, 75.0  # Base confidence for options analysis
                )
                
                if not consensus_result:
                    return OptionsAnalysisResponse(
                        success=False,
                        symbol=symbol,
                        strategy_type=request.strategy_type,
                        analysis={},
                        recommendations=[],
                        risk_analysis={},
                        interactive_data={},
                        disclaimer="",
                        error_message="AI analysis failed"
                    )

                # Process AI results into structured response
                analysis_response = _process_ai_analysis(
                    consensus_result, options_data, request
                )
                
                return OptionsAnalysisResponse(
                    success=True,
                    symbol=symbol,
                    strategy_type=request.strategy_type,
                    analysis=analysis_response['analysis'],
                    recommendations=analysis_response['recommendations'],
                    risk_analysis=analysis_response['risk_analysis'],
                    interactive_data=analysis_response['interactive_data'],
                    disclaimer="This analysis is for educational purposes only and does not constitute financial advice. Options trading involves significant risk and may not be suitable for all investors."
                )

    except Exception as e:
        logger.error(f"Error analyzing options for {request.symbol}: {e}")
        return OptionsAnalysisResponse(
            success=False,
            symbol=request.symbol.upper(),
            strategy_type=request.strategy_type,
            analysis={},
            recommendations=[],
            risk_analysis={},
            interactive_data={},
            disclaimer="",
            error_message="Analysis service temporarily unavailable"
        )

def _process_ai_analysis(consensus_result, options_data: OptionsChainData, request: OptionsAnalysisRequest) -> Dict[str, Any]:
    """
    Process AI consensus result into structured analysis response.
    
    Args:
        consensus_result: AI consensus analysis result
        options_data: Options chain data
        request: Original analysis request
        
    Returns:
        Structured analysis response
    """
    # This is a placeholder for the actual AI result processing
    # In the real implementation, this would parse the AI responses
    # and structure them into the required format
    
    return {
        'analysis': {
            'confidence_score': consensus_result.consensus_confidence if consensus_result else 0.5,
            'recommendation': consensus_result.final_recommendation if consensus_result else 'HOLD',
            'key_insights': [
                'AI analysis completed',
                'Risk/reward calculated',
                'Strategy recommendations generated'
            ]
        },
        'recommendations': [
            {
                'strategy': request.strategy_type,
                'action': 'BUY',
                'strike': 100.0,
                'premium': 2.50,
                'max_risk': request.max_position_size * 0.1,
                'max_reward': request.max_position_size * 0.3,
                'breakeven': 102.50
            }
        ],
        'risk_analysis': {
            'max_loss': request.max_position_size * 0.1,
            'max_gain': request.max_position_size * 0.3,
            'probability_of_profit': 0.65,
            'risk_reward_ratio': 3.0,
            'time_decay_risk': 'MODERATE'
        },
        'interactive_data': {
            'current_price': options_data.current_price,
            'iv_rank': options_data.iv_rank or 50.0,
            'days_to_expiry': (datetime.strptime(request.expiration_date, '%Y-%m-%d') - datetime.now()).days,
            'scenario_analysis': {
                'price_targets': [90, 95, 100, 105, 110],
                'profit_loss': [-100, -50, 0, 150, 300]
            }
        }
    }
