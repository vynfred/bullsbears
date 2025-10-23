"""
Enhanced options analysis with entry/exit pricing, probability calculations,
and position sizing recommendations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy.stats import norm
import yfinance as yf
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OptionRecommendation:
    """Data class for option recommendations."""
    symbol: str
    option_type: str  # CALL or PUT
    strike: float
    expiration: str
    entry_price: float
    target_price: float
    stop_loss: float
    probability_profit: float
    max_profit: float
    max_loss: float
    risk_reward_ratio: float
    position_size: int
    reasoning: str
    strategy: str

@dataclass
class ProbabilityAnalysis:
    """Data class for probability calculations."""
    prob_profit: float
    prob_target: float
    prob_breakeven: float
    expected_return: float
    risk_adjusted_return: float

class OptionsAnalyzer:
    """Enhanced options analysis with pricing and probability calculations."""
    
    def __init__(self):
        self.risk_free_rate = 0.05  # 5% risk-free rate (approximate)
    
    async def analyze_option_opportunity(self, 
                                       symbol: str,
                                       technical_data: Dict[str, Any],
                                       confidence_score: float,
                                       timeframe_days: int = 7,
                                       position_size_dollars: float = 1000) -> Optional[OptionRecommendation]:
        """
        Analyze and recommend the best option play for a symbol.
        
        Args:
            symbol: Stock symbol
            technical_data: Technical analysis data
            confidence_score: Overall confidence score
            timeframe_days: Target timeframe (1-30 days)
            position_size_dollars: Dollar amount to invest
            
        Returns:
            OptionRecommendation with complete analysis
        """
        try:
            # Get current stock data
            ticker = yf.Ticker(symbol)
            current_price = await self._get_current_price(ticker)
            if not current_price:
                return None
            
            # Get historical volatility
            volatility = await self._calculate_volatility(ticker)
            if not volatility:
                return None
            
            # Determine option type and strike based on technical analysis
            option_type, target_price = self._determine_option_strategy(
                current_price, technical_data, confidence_score
            )
            
            # Calculate optimal strike price
            strike_price = self._calculate_optimal_strike(
                current_price, target_price, option_type, timeframe_days
            )
            
            # Get expiration date
            expiration_date = self._get_optimal_expiration(timeframe_days)
            
            # Calculate option pricing (simplified Black-Scholes)
            entry_price = self._estimate_option_price(
                current_price, strike_price, volatility, timeframe_days / 365, option_type
            )
            
            # Calculate target and stop loss prices
            target_option_price, stop_loss_price = self._calculate_exit_prices(
                entry_price, confidence_score
            )
            
            # Calculate probability analysis
            prob_analysis = self._calculate_probabilities(
                current_price, strike_price, target_price, volatility, timeframe_days / 365, option_type
            )
            
            # Calculate position sizing
            position_size = self._calculate_position_size(
                entry_price, position_size_dollars, stop_loss_price
            )
            
            # Calculate risk/reward metrics
            max_profit = (target_option_price - entry_price) * position_size * 100
            max_loss = (entry_price - stop_loss_price) * position_size * 100
            risk_reward_ratio = max_profit / max_loss if max_loss > 0 else 0
            
            # Generate reasoning
            reasoning = self._generate_option_reasoning(
                symbol, option_type, strike_price, current_price, 
                technical_data, confidence_score, prob_analysis
            )
            
            # Determine strategy name
            strategy = self._get_strategy_name(option_type, strike_price, current_price)
            
            return OptionRecommendation(
                symbol=symbol,
                option_type=option_type,
                strike=strike_price,
                expiration=expiration_date,
                entry_price=entry_price,
                target_price=target_option_price,
                stop_loss=stop_loss_price,
                probability_profit=prob_analysis.prob_profit,
                max_profit=max_profit,
                max_loss=max_loss,
                risk_reward_ratio=risk_reward_ratio,
                position_size=position_size,
                reasoning=reasoning,
                strategy=strategy
            )
            
        except Exception as e:
            logger.error(f"Error analyzing option opportunity for {symbol}: {e}")
            return None
    
    async def _get_current_price(self, ticker) -> Optional[float]:
        """Get current stock price."""
        try:
            info = ticker.info
            return info.get('regularMarketPrice') or info.get('currentPrice')
        except:
            try:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    return hist['Close'].iloc[-1]
            except:
                pass
        return None
    
    async def _calculate_volatility(self, ticker) -> Optional[float]:
        """Calculate historical volatility."""
        try:
            hist = ticker.history(period="3mo")
            if hist.empty:
                return None
            
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            return volatility
        except:
            return None
    
    def _determine_option_strategy(self, current_price: float, 
                                 technical_data: Dict, confidence_score: float) -> Tuple[str, float]:
        """Determine whether to buy calls or puts and target price."""
        
        # Default to neutral
        option_type = "CALL"
        target_price = current_price * 1.05  # 5% move
        
        if not technical_data or 'indicators' not in technical_data:
            return option_type, target_price
        
        indicators = technical_data['indicators']
        bullish_signals = 0
        bearish_signals = 0
        
        # RSI analysis
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if rsi < 30:  # Oversold - bullish
                bullish_signals += 2
                target_price = current_price * 1.08  # 8% move up
            elif rsi > 70:  # Overbought - bearish
                bearish_signals += 2
                target_price = current_price * 0.92  # 8% move down
        
        # MACD analysis
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            signal = indicators['macd_signal']
            if macd > signal:
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        # Moving average analysis
        if 'sma_20' in indicators and 'sma_50' in indicators:
            sma20 = indicators['sma_20']
            sma50 = indicators['sma_50']
            if sma20 > sma50:
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        # Bollinger Bands analysis
        if all(k in indicators for k in ['bb_upper', 'bb_lower']):
            bb_upper = indicators['bb_upper']
            bb_lower = indicators['bb_lower']
            
            if current_price <= bb_lower:  # Near lower band - bullish
                bullish_signals += 1
                target_price = current_price * 1.06
            elif current_price >= bb_upper:  # Near upper band - bearish
                bearish_signals += 1
                target_price = current_price * 0.94
        
        # Determine final strategy
        if bullish_signals > bearish_signals:
            option_type = "CALL"
            # Adjust target based on confidence
            multiplier = 1.03 + (confidence_score / 100) * 0.05  # 3-8% move
            target_price = current_price * multiplier
        else:
            option_type = "PUT"
            # Adjust target based on confidence
            multiplier = 0.97 - (confidence_score / 100) * 0.05  # 3-8% move down
            target_price = current_price * multiplier
        
        return option_type, target_price
    
    def _calculate_optimal_strike(self, current_price: float, target_price: float, 
                                option_type: str, timeframe_days: int) -> float:
        """Calculate optimal strike price."""
        
        if option_type == "CALL":
            # For calls, use slightly OTM strike for better leverage
            if timeframe_days <= 7:  # Short term - closer to ATM
                strike = current_price * 1.01  # 1% OTM
            else:  # Longer term - more OTM
                strike = current_price * 1.02  # 2% OTM
        else:  # PUT
            # For puts, use slightly OTM strike
            if timeframe_days <= 7:
                strike = current_price * 0.99  # 1% OTM
            else:
                strike = current_price * 0.98  # 2% OTM
        
        # Round to nearest $0.50 for liquid strikes
        return round(strike * 2) / 2
    
    def _get_optimal_expiration(self, timeframe_days: int) -> str:
        """Get optimal expiration date with +/- 2 days grace period."""
        # Calculate target expiration date
        target_date = datetime.now() + timedelta(days=timeframe_days)

        # Apply +/- 2 days grace period to find the closest available expiration
        # This accommodates options that aren't exactly weekly intervals
        grace_period = 2

        # Generate potential expiration dates within grace period
        potential_dates = []
        for offset in range(-grace_period, grace_period + 1):
            candidate_date = target_date + timedelta(days=offset)

            # Adjust to Friday (typical expiration day) if not already
            days_until_friday = (4 - candidate_date.weekday()) % 7
            if days_until_friday > 0:
                candidate_date += timedelta(days=days_until_friday)

            potential_dates.append(candidate_date)

        # Choose the date closest to our target timeframe
        best_date = min(potential_dates, key=lambda d: abs((d - target_date).days))

        return best_date.strftime("%Y-%m-%d")
    
    def _estimate_option_price(self, stock_price: float, strike: float, 
                             volatility: float, time_to_expiry: float, option_type: str) -> float:
        """Estimate option price using simplified Black-Scholes."""
        
        try:
            # Black-Scholes parameters
            S = stock_price
            K = strike
            T = time_to_expiry
            r = self.risk_free_rate
            sigma = volatility
            
            # Calculate d1 and d2
            d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            
            if option_type == "CALL":
                price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            else:  # PUT
                price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            
            return max(price, 0.05)  # Minimum $0.05
            
        except:
            # Fallback to intrinsic value + time value estimate
            if option_type == "CALL":
                intrinsic = max(stock_price - strike, 0)
            else:
                intrinsic = max(strike - stock_price, 0)
            
            time_value = stock_price * volatility * np.sqrt(time_to_expiry) * 0.4
            return max(intrinsic + time_value, 0.05)
    
    def _calculate_exit_prices(self, entry_price: float, confidence_score: float) -> Tuple[float, float]:
        """Calculate target and stop loss prices."""
        
        # Target price based on confidence (higher confidence = higher target)
        profit_multiplier = 1.5 + (confidence_score / 100) * 1.0  # 1.5x to 2.5x
        target_price = entry_price * profit_multiplier
        
        # Stop loss (risk 30-50% of premium)
        risk_percentage = 0.5 - (confidence_score / 100) * 0.2  # 30-50% risk
        stop_loss = entry_price * (1 - risk_percentage)
        
        return target_price, max(stop_loss, 0.01)
    
    def _calculate_probabilities(self, stock_price: float, strike: float, target_price: float,
                               volatility: float, time_to_expiry: float, option_type: str) -> ProbabilityAnalysis:
        """Calculate probability of profit and other metrics."""
        
        try:
            # Calculate probability of reaching target price
            if option_type == "CALL":
                # Probability stock price > strike at expiration
                d2 = (np.log(stock_price / strike) + (self.risk_free_rate - 0.5 * volatility ** 2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
                prob_profit = norm.cdf(d2)
                
                # Probability of reaching target
                d2_target = (np.log(stock_price / target_price) + (self.risk_free_rate - 0.5 * volatility ** 2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
                prob_target = norm.cdf(d2_target)
                
            else:  # PUT
                d2 = (np.log(stock_price / strike) + (self.risk_free_rate - 0.5 * volatility ** 2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
                prob_profit = norm.cdf(-d2)
                
                d2_target = (np.log(stock_price / target_price) + (self.risk_free_rate - 0.5 * volatility ** 2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
                prob_target = norm.cdf(-d2_target)
            
            # Breakeven probability (simplified)
            prob_breakeven = prob_profit * 0.8  # Rough estimate
            
            # Expected return (simplified)
            expected_return = prob_profit * 0.5 - (1 - prob_profit) * 0.3
            
            # Risk-adjusted return
            risk_adjusted_return = expected_return / volatility
            
            return ProbabilityAnalysis(
                prob_profit=prob_profit,
                prob_target=prob_target,
                prob_breakeven=prob_breakeven,
                expected_return=expected_return,
                risk_adjusted_return=risk_adjusted_return
            )
            
        except:
            # Fallback to simple estimates
            return ProbabilityAnalysis(
                prob_profit=0.6,
                prob_target=0.4,
                prob_breakeven=0.5,
                expected_return=0.1,
                risk_adjusted_return=0.2
            )
    
    def _calculate_position_size(self, entry_price: float, total_dollars: float, 
                               stop_loss: float) -> int:
        """Calculate position size based on risk management."""
        
        # Risk per contract
        risk_per_contract = (entry_price - stop_loss) * 100  # 100 shares per contract
        
        # Maximum risk (2% of total capital)
        max_risk = total_dollars * 0.02
        
        # Calculate position size
        if risk_per_contract > 0:
            max_contracts = int(max_risk / risk_per_contract)
        else:
            max_contracts = 1
        
        # Also consider total cost
        cost_per_contract = entry_price * 100
        max_contracts_by_cost = int(total_dollars * 0.1 / cost_per_contract)  # Use max 10% of capital
        
        return max(1, min(max_contracts, max_contracts_by_cost, 10))  # Cap at 10 contracts
    
    def _generate_option_reasoning(self, symbol: str, option_type: str, strike: float,
                                 current_price: float, technical_data: Dict, 
                                 confidence_score: float, prob_analysis: ProbabilityAnalysis) -> str:
        """Generate reasoning for the option recommendation."""
        
        reasons = []
        
        # Direction reasoning
        direction = "bullish" if option_type == "CALL" else "bearish"
        reasons.append(f"{direction.capitalize()} setup based on technical analysis")
        
        # Strike reasoning
        otm_percent = abs(strike - current_price) / current_price * 100
        reasons.append(f"{otm_percent:.1f}% OTM strike for optimal risk/reward")
        
        # Probability reasoning
        prob_percent = prob_analysis.prob_profit * 100
        reasons.append(f"{prob_percent:.0f}% probability of profit")
        
        # Confidence reasoning
        if confidence_score >= 80:
            reasons.append("High confidence technical setup")
        elif confidence_score >= 70:
            reasons.append("Moderate confidence with good risk/reward")
        
        return "; ".join(reasons)
    
    def _get_strategy_name(self, option_type: str, strike: float, current_price: float) -> str:
        """Get strategy name based on option characteristics."""
        
        if option_type == "CALL":
            if strike <= current_price:
                return "ITM Call"
            else:
                return "OTM Call"
        else:
            if strike >= current_price:
                return "ITM Put"
            else:
                return "OTM Put"
