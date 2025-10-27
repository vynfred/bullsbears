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

from ..services.risk_profile_service import RiskProfileService, InsightStyle, MarketOutlook

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
    # New fields for advanced analysis
    contracts: int = 1
    strategy_name: str = ""
    strategy_description: str = ""
    breakeven_price: float = 0.0
    confidence_level: str = "MEDIUM"
    delta: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    gamma: float = 0.0

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
        self.risk_profile_service = RiskProfileService()
    
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

    async def analyze_with_advanced_settings(self,
                                           symbol: str,
                                           technical_data: Dict[str, Any],
                                           confidence_score: float,
                                           user_preferences: Dict[str, Any],
                                           timeframe_days: int = 7,
                                           position_size_dollars: float = 1000) -> Optional[OptionRecommendation]:
        """
        Analyze option opportunities with advanced user settings.

        Args:
            symbol: Stock symbol
            technical_data: Technical analysis data
            confidence_score: Overall confidence score
            user_preferences: User preferences including advanced settings
            timeframe_days: Target timeframe (1-30 days)
            position_size_dollars: Dollar amount to invest

        Returns:
            Option recommendation tailored to user's risk profile and settings
        """

        # Extract advanced settings
        insight_style_str = user_preferences.get('insight_style', 'professional_trader')
        iv_threshold = user_preferences.get('iv_threshold', 50.0)
        earnings_alert = user_preferences.get('earnings_alert', True)
        shares_owned = user_preferences.get('shares_owned', {})

        # Convert insight style string to enum
        try:
            insight_style = InsightStyle(insight_style_str)
        except ValueError:
            insight_style = InsightStyle.PROFESSIONAL_TRADER

        # Get current stock price and implied volatility
        current_price = technical_data.get('current_price', 100.0)
        implied_volatility = await self._get_implied_volatility(symbol)

        # Check IV threshold
        if implied_volatility and implied_volatility > iv_threshold:
            logger.info(f"IV {implied_volatility:.1f}% exceeds threshold {iv_threshold}% for {symbol}")
            # Still proceed but prefer low-vega strategies

        # Check earnings proximity if enabled
        if earnings_alert:
            days_to_earnings = await self._get_days_to_earnings(symbol)
            if days_to_earnings and days_to_earnings <= 7:
                logger.info(f"Earnings in {days_to_earnings} days for {symbol} - adjusting strategy")
                # Reduce position size or avoid high-gamma strategies
                position_size_dollars *= 0.5

        # Determine market outlook from technical data
        market_outlook = self._determine_market_outlook(technical_data, confidence_score)

        # Get strategy recommendations for this insight style
        strategies = self.risk_profile_service.get_strategies_for_profile(insight_style, market_outlook)

        # Filter strategies based on user settings
        filtered_strategies = self.risk_profile_service.filter_strategies_by_settings(
            strategies, iv_threshold, earnings_alert, shares_owned, symbol
        )

        if not filtered_strategies:
            logger.warning(f"No suitable strategies found for {symbol} with current settings")
            return None

        # Select best strategy (for now, take the first one)
        selected_strategy = filtered_strategies[0]

        # Get position sizing rules for this insight style
        sizing_rules = self.risk_profile_service.get_position_sizing_rules(risk_profile)

        # Adjust position size based on insight style
        max_risk_per_trade = sizing_rules['max_risk_per_trade']
        adjusted_position_size = min(position_size_dollars,
                                   position_size_dollars * max_risk_per_trade / 0.02)  # Scale from 2% base

        # Generate the actual option recommendation
        return await self._generate_strategy_recommendation(
            symbol, selected_strategy, current_price, adjusted_position_size,
            timeframe_days, sizing_rules
        )

    def _determine_market_outlook(self, technical_data: Dict, confidence_score: float) -> MarketOutlook:
        """Determine market outlook from technical analysis."""

        if not technical_data or 'indicators' not in technical_data:
            return MarketOutlook.NEUTRAL

        indicators = technical_data['indicators']
        bullish_signals = 0
        bearish_signals = 0

        # RSI analysis
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if rsi < 30:
                bullish_signals += 2
            elif rsi > 70:
                bearish_signals += 2
            elif 40 <= rsi <= 60:
                # Neutral RSI
                pass

        # MACD analysis
        if 'macd' in indicators:
            macd_line = indicators['macd'].get('macd', 0)
            signal_line = indicators['macd'].get('signal', 0)
            if macd_line > signal_line:
                bullish_signals += 1
            else:
                bearish_signals += 1

        # Moving average analysis
        if 'sma_20' in indicators and 'sma_50' in indicators:
            if indicators['sma_20'] > indicators['sma_50']:
                bullish_signals += 1
            else:
                bearish_signals += 1

        # Use confidence score as a tie-breaker
        if bullish_signals > bearish_signals:
            return MarketOutlook.BULLISH
        elif bearish_signals > bullish_signals:
            return MarketOutlook.BEARISH
        else:
            return MarketOutlook.NEUTRAL

    async def _get_implied_volatility(self, symbol: str) -> Optional[float]:
        """Get current implied volatility for the symbol."""
        try:
            # This is a simplified implementation
            # In production, you'd get this from options data
            ticker = yf.Ticker(symbol)
            options = ticker.option_chain()

            if options.calls.empty:
                return None

            # Get ATM call IV as proxy
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
            atm_calls = options.calls[abs(options.calls['strike'] - current_price) < 5]

            if not atm_calls.empty:
                return atm_calls['impliedVolatility'].mean() * 100

            return None
        except Exception as e:
            logger.error(f"Error getting IV for {symbol}: {e}")
            return None

    async def _get_days_to_earnings(self, symbol: str) -> Optional[int]:
        """Get days until next earnings announcement."""
        try:
            # This is a placeholder - in production you'd use earnings calendar API
            # For now, return None to indicate no earnings data
            return None
        except Exception as e:
            logger.error(f"Error getting earnings date for {symbol}: {e}")
            return None

    async def _generate_strategy_recommendation(self,
                                              symbol: str,
                                              strategy,
                                              current_price: float,
                                              position_size: float,
                                              timeframe_days: int,
                                              sizing_rules: Dict) -> OptionRecommendation:
        """Generate specific option recommendation based on strategy."""

        # Calculate target price based on strategy and timeframe
        if strategy.market_outlook == MarketOutlook.BULLISH:
            target_price = current_price * (1 + 0.05 + timeframe_days * 0.002)  # 5% + time factor
            option_type = "CALL"
        elif strategy.market_outlook == MarketOutlook.BEARISH:
            target_price = current_price * (1 - 0.05 - timeframe_days * 0.002)  # -5% - time factor
            option_type = "PUT"
        else:  # NEUTRAL
            target_price = current_price  # No directional bias
            option_type = "CALL"  # Default, but strategy might be straddle/strangle

        # Calculate strike price based on strategy
        if "OTM" in strategy.description:
            if option_type == "CALL":
                strike = current_price * 1.05  # 5% OTM
            else:
                strike = current_price * 0.95  # 5% OTM
        elif "ITM" in strategy.description:
            if option_type == "CALL":
                strike = current_price * 0.95  # 5% ITM
            else:
                strike = current_price * 1.05  # 5% ITM
        else:  # ATM
            strike = current_price

        # Calculate expiration date
        expiration_date = datetime.now() + timedelta(days=timeframe_days)
        expiration_str = expiration_date.strftime("%Y-%m-%d")

        # Estimate option price (simplified Black-Scholes approximation)
        time_to_expiry = timeframe_days / 365.0
        volatility = 0.25  # 25% assumed volatility

        entry_price = self._estimate_option_price(
            current_price, strike, time_to_expiry, volatility, option_type
        )

        # Calculate position sizing
        contracts = max(1, int(position_size / (entry_price * 100)))

        # Set profit target and stop loss based on risk profile
        profit_target_pct = sizing_rules['profit_target']
        stop_loss_pct = sizing_rules['stop_loss']

        target_price_option = entry_price * (1 + profit_target_pct)
        stop_loss_price = entry_price * (1 - stop_loss_pct)

        # Calculate max profit/loss
        max_profit = (target_price_option - entry_price) * contracts * 100
        max_loss = (entry_price - stop_loss_price) * contracts * 100

        # Calculate probability of profit (simplified)
        prob_profit = self._calculate_probability_profit(
            current_price, strike, target_price, time_to_expiry, volatility, option_type
        )

        return OptionRecommendation(
            symbol=symbol,
            option_type=option_type,
            strike=round(strike, 2),
            expiration=expiration_str,
            entry_price=round(entry_price, 2),
            target_price=round(target_price_option, 2),
            stop_loss=round(stop_loss_price, 2),
            probability_profit=round(prob_profit * 100, 1),
            max_profit=round(max_profit, 2),
            max_loss=round(max_loss, 2),
            risk_reward_ratio=round(max_profit / max_loss if max_loss > 0 else 0, 2),
            contracts=contracts,
            strategy_name=strategy.name,
            strategy_description=strategy.description,
            breakeven_price=round(strike + entry_price if option_type == "CALL" else strike - entry_price, 2),
            delta=self._estimate_delta(current_price, strike, time_to_expiry, volatility, option_type),
            theta=self._estimate_theta(current_price, strike, time_to_expiry, volatility, option_type),
            vega=self._estimate_vega(current_price, strike, time_to_expiry, volatility),
            gamma=self._estimate_gamma(current_price, strike, time_to_expiry, volatility),
            confidence_level="HIGH" if prob_profit > 0.7 else "MEDIUM" if prob_profit > 0.5 else "LOW"
        )

    def _estimate_option_price(self, spot: float, strike: float, time_to_expiry: float,
                              volatility: float, option_type: str) -> float:
        """Estimate option price using simplified Black-Scholes."""

        if time_to_expiry <= 0:
            # At expiration
            if option_type == "CALL":
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)

        d1 = (np.log(spot / strike) + (self.risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)

        if option_type == "CALL":
            price = spot * norm.cdf(d1) - strike * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(d2)
        else:
            price = strike * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)

        return max(0.01, price)  # Minimum price of $0.01

    def _calculate_probability_profit(self, spot: float, strike: float, target: float,
                                    time_to_expiry: float, volatility: float, option_type: str) -> float:
        """Calculate probability of reaching profit target."""

        if option_type == "CALL":
            breakeven = strike + self._estimate_option_price(spot, strike, time_to_expiry, volatility, option_type)
            # Probability that stock price > breakeven at expiration
            d = (np.log(spot / breakeven) + (self.risk_free_rate - 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
            return norm.cdf(d)
        else:
            breakeven = strike - self._estimate_option_price(spot, strike, time_to_expiry, volatility, option_type)
            # Probability that stock price < breakeven at expiration
            d = (np.log(spot / breakeven) + (self.risk_free_rate - 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
            return norm.cdf(-d)

    def _estimate_delta(self, spot: float, strike: float, time_to_expiry: float,
                       volatility: float, option_type: str) -> float:
        """Estimate option delta."""
        if time_to_expiry <= 0:
            return 1.0 if (option_type == "CALL" and spot > strike) or (option_type == "PUT" and spot < strike) else 0.0

        d1 = (np.log(spot / strike) + (self.risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))

        if option_type == "CALL":
            return norm.cdf(d1)
        else:
            return -norm.cdf(-d1)

    def _estimate_theta(self, spot: float, strike: float, time_to_expiry: float,
                       volatility: float, option_type: str) -> float:
        """Estimate option theta (time decay)."""
        if time_to_expiry <= 0:
            return 0.0

        d1 = (np.log(spot / strike) + (self.risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)

        theta_common = -(spot * norm.pdf(d1) * volatility) / (2 * np.sqrt(time_to_expiry))

        if option_type == "CALL":
            theta = theta_common - self.risk_free_rate * strike * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(d2)
        else:
            theta = theta_common + self.risk_free_rate * strike * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(-d2)

        return theta / 365  # Convert to daily theta

    def _estimate_vega(self, spot: float, strike: float, time_to_expiry: float, volatility: float) -> float:
        """Estimate option vega (volatility sensitivity)."""
        if time_to_expiry <= 0:
            return 0.0

        d1 = (np.log(spot / strike) + (self.risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))

        return spot * norm.pdf(d1) * np.sqrt(time_to_expiry) / 100  # Convert to percentage

    def _estimate_gamma(self, spot: float, strike: float, time_to_expiry: float, volatility: float) -> float:
        """Estimate option gamma (delta sensitivity)."""
        if time_to_expiry <= 0:
            return 0.0

        d1 = (np.log(spot / strike) + (self.risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))

        return norm.pdf(d1) / (spot * volatility * np.sqrt(time_to_expiry))
    
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
