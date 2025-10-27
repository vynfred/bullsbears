"""
Insight Style Service for Options Trading

Manages different insight styles and their associated strategies:
- Cautious Trader (Low Risk: Defined, Income-Focused)
- Professional Trader (Medium Risk: Balanced, Structured)
- Degenerate Gambler (High Risk: Aggressive, High-Reward)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class InsightStyle(Enum):
    CAUTIOUS_TRADER = "cautious_trader"
    PROFESSIONAL_TRADER = "professional_trader"
    DEGENERATE_GAMBLER = "degenerate_gambler"

class MarketOutlook(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

@dataclass
class StrategyRecommendation:
    """Data class for strategy recommendations."""
    name: str
    description: str
    risk_level: str
    max_loss: str
    profit_potential: str
    market_outlook: MarketOutlook
    delta_range: Optional[str] = None
    theta_focus: bool = False
    vega_sensitivity: str = "low"
    
class RiskProfileService:
    """Service for managing risk profiles and strategy recommendations."""
    
    def __init__(self):
        self.strategies = self._initialize_strategies()
    
    def _initialize_strategies(self) -> Dict[InsightStyle, Dict[MarketOutlook, List[StrategyRecommendation]]]:
        """Initialize all strategy recommendations by insight style and market outlook."""

        return {
            InsightStyle.CAUTIOUS_TRADER: {
                MarketOutlook.BULLISH: [
                    StrategyRecommendation(
                        name="Bull Put Spread",
                        description="Credit; OTM short/long puts; delta -0.2 to -0.4; theta positive",
                        risk_level="Low",
                        max_loss="Defined",
                        profit_potential="Income-focused",
                        market_outlook=MarketOutlook.BULLISH,
                        delta_range="-0.2 to -0.4",
                        theta_focus=True,
                        vega_sensitivity="low"
                    )
                ],
                MarketOutlook.BEARISH: [
                    StrategyRecommendation(
                        name="Bear Call Spread",
                        description="Credit; OTM short/long calls; delta 0.2 to 0.4; theta positive",
                        risk_level="Low",
                        max_loss="Defined",
                        profit_potential="Income-focused",
                        market_outlook=MarketOutlook.BEARISH,
                        delta_range="0.2 to 0.4",
                        theta_focus=True,
                        vega_sensitivity="low"
                    )
                ],
                MarketOutlook.NEUTRAL: [
                    StrategyRecommendation(
                        name="Short Strangle",
                        description="Credit; OTM call + put; wings ±20% strikes; theta decay focus",
                        risk_level="Low",
                        max_loss="Defined with wings",
                        profit_potential="Income-focused",
                        market_outlook=MarketOutlook.NEUTRAL,
                        delta_range="±20% strikes",
                        theta_focus=True,
                        vega_sensitivity="medium"
                    )
                ]
            },

            InsightStyle.PROFESSIONAL_TRADER: {
                MarketOutlook.BULLISH: [
                    StrategyRecommendation(
                        name="Bull Call Spread",
                        description="Debit; ITM/OTM calls; delta 0.4-0.6; max loss defined",
                        risk_level="Medium",
                        max_loss="Premium paid",
                        profit_potential="Balanced risk/reward",
                        market_outlook=MarketOutlook.BULLISH,
                        delta_range="0.4-0.6",
                        theta_focus=False,
                        vega_sensitivity="medium"
                    )
                ],
                MarketOutlook.BEARISH: [
                    StrategyRecommendation(
                        name="Bear Put Spread",
                        description="Debit; ITM/OTM puts; delta -0.4 to -0.6; max loss capped",
                        risk_level="Medium",
                        max_loss="Premium paid",
                        profit_potential="Balanced risk/reward",
                        market_outlook=MarketOutlook.BEARISH,
                        delta_range="-0.4 to -0.6",
                        theta_focus=False,
                        vega_sensitivity="medium"
                    )
                ],
                MarketOutlook.NEUTRAL: [
                    StrategyRecommendation(
                        name="Iron Condor",
                        description="Credit; short strangle + protective wings; breakeven ±10% move",
                        risk_level="Medium",
                        max_loss="Defined",
                        profit_potential="Range-bound profit",
                        market_outlook=MarketOutlook.NEUTRAL,
                        delta_range="±10% breakeven",
                        theta_focus=True,
                        vega_sensitivity="low"
                    )
                ]
            },

            InsightStyle.DEGENERATE_GAMBLER: {
                MarketOutlook.BULLISH: [
                    StrategyRecommendation(
                        name="Naked Call",
                        description="Long OTM call; delta >0.7; unlimited upside on rally",
                        risk_level="High",
                        max_loss="Premium paid",
                        profit_potential="Unlimited on rally",
                        market_outlook=MarketOutlook.BULLISH,
                        delta_range=">0.7",
                        theta_focus=False,
                        vega_sensitivity="high"
                    )
                ],
                MarketOutlook.BEARISH: [
                    StrategyRecommendation(
                        name="Naked Put",
                        description="Long OTM put; delta < -0.7; high payout on drop",
                        risk_level="High",
                        max_loss="Premium paid",
                        profit_potential="High payout potential",
                        market_outlook=MarketOutlook.BEARISH,
                        delta_range="< -0.7",
                        theta_focus=False,
                        vega_sensitivity="high"
                    )
                ],
                MarketOutlook.NEUTRAL: [
                    StrategyRecommendation(
                        name="Long Straddle",
                        description="Debit; ATM call + put; vega >0.5 bet on volatility breakout",
                        risk_level="High",
                        max_loss="Premium paid",
                        profit_potential="Volatility breakout bet",
                        market_outlook=MarketOutlook.NEUTRAL,
                        delta_range="Vega >0.5",
                        theta_focus=False,
                        vega_sensitivity="very high"
                    )
                ]
            }
        }
    
    def get_strategies_for_profile(self, insight_style: InsightStyle,
                                 market_outlook: MarketOutlook) -> List[StrategyRecommendation]:
        """Get strategy recommendations for a specific insight style and market outlook."""
        return self.strategies.get(insight_style, {}).get(market_outlook, [])

    def get_all_strategies_for_profile(self, insight_style: InsightStyle) -> Dict[MarketOutlook, List[StrategyRecommendation]]:
        """Get all strategies for an insight style across all market outlooks."""
        return self.strategies.get(insight_style, {})

    def get_insight_style_description(self, insight_style: InsightStyle) -> Dict[str, str]:
        """Get description and characteristics of an insight style."""
        descriptions = {
            InsightStyle.CAUTIOUS_TRADER: {
                "name": "Cautious Trader",
                "description": "Low Risk: Defined, Income-Focused",
                "characteristics": "Prefers credit spreads, defined risk, consistent income generation",
                "max_risk_per_trade": "2% of portfolio",
                "preferred_strategies": "Credit spreads, covered calls, cash-secured puts"
            },
            InsightStyle.PROFESSIONAL_TRADER: {
                "name": "Professional Trader",
                "description": "Medium Risk: Balanced, Structured",
                "characteristics": "Balanced approach, structured trades, risk management focus",
                "max_risk_per_trade": "5% of portfolio",
                "preferred_strategies": "Debit spreads, iron condors, calendar spreads"
            },
            InsightStyle.DEGENERATE_GAMBLER: {
                "name": "Degenerate Gambler",
                "description": "High Risk: Aggressive, High-Reward",
                "characteristics": "High risk tolerance, seeks maximum returns, volatility plays",
                "max_risk_per_trade": "10% of portfolio",
                "preferred_strategies": "Long options, straddles, high-delta plays"
            }
        }
        return descriptions.get(insight_style, {})
    
    def filter_strategies_by_settings(self, strategies: List[StrategyRecommendation],
                                    iv_threshold: float,
                                    earnings_alert: bool,
                                    shares_owned: Dict[str, int],
                                    symbol: str) -> List[StrategyRecommendation]:
        """Filter strategies based on user settings."""
        filtered = []
        
        for strategy in strategies:
            # Skip high vega strategies if IV is too high
            if iv_threshold < 40 and strategy.vega_sensitivity in ["high", "very high"]:
                continue
                
            # Add covered call option if user owns shares
            if symbol in shares_owned and shares_owned[symbol] >= 100:
                if strategy.market_outlook == MarketOutlook.BULLISH:
                    # Add covered call as an option
                    covered_call = StrategyRecommendation(
                        name="Covered Call",
                        description=f"Own {shares_owned[symbol]} shares + sell call",
                        risk_level="Low",
                        max_loss="Opportunity cost",
                        profit_potential="Premium + limited upside",
                        market_outlook=MarketOutlook.BULLISH,
                        delta_range="0.2-0.4",
                        theta_focus=True,
                        vega_sensitivity="low"
                    )
                    filtered.append(covered_call)
            
            filtered.append(strategy)
        
        return filtered
    
    def get_position_sizing_rules(self, insight_style: InsightStyle) -> Dict[str, Any]:
        """Get position sizing rules for an insight style."""
        rules = {
            InsightStyle.CAUTIOUS_TRADER: {
                "max_risk_per_trade": 0.02,  # 2%
                "max_portfolio_allocation": 0.10,  # 10%
                "preferred_win_rate": 0.70,  # 70%
                "max_dte": 45,  # Days to expiration
                "profit_target": 0.25,  # 25% of max profit
                "stop_loss": 0.50  # 50% of premium
            },
            InsightStyle.PROFESSIONAL_TRADER: {
                "max_risk_per_trade": 0.05,  # 5%
                "max_portfolio_allocation": 0.20,  # 20%
                "preferred_win_rate": 0.60,  # 60%
                "max_dte": 60,
                "profit_target": 0.50,  # 50% of max profit
                "stop_loss": 0.75  # 75% of premium
            },
            InsightStyle.DEGENERATE_GAMBLER: {
                "max_risk_per_trade": 0.10,  # 10%
                "max_portfolio_allocation": 0.30,  # 30%
                "preferred_win_rate": 0.40,  # 40% (high risk/reward)
                "max_dte": 30,
                "profit_target": 1.00,  # 100% of max profit (let it ride)
                "stop_loss": 1.00  # 100% of premium (no stop loss)
            }
        }
        return rules.get(insight_style, rules[InsightStyle.PROFESSIONAL_TRADER])
