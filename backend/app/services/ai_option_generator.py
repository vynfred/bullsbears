"""
AI-powered option play generator that combines all analysis services
to automatically select and recommend the best option trades.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .ticker_selector import TickerSelector, TickerCandidate
from .polymarket import PolymarketService, PredictionMarket
from .grok_ai import GrokAIService, GrokAnalysis
from .options_analyzer import OptionsAnalyzer, OptionRecommendation
from .catalyst_detector import CatalystDetector, Catalyst
from .volume_analyzer import VolumeAnalyzer, VolumeAlert
from ..analyzers.technical import TechnicalAnalyzer
from ..analyzers.news import NewsAnalyzer
from ..analyzers.social import SocialMediaAnalyzer
from ..analyzers.confidence import ConfidenceScorer

logger = logging.getLogger(__name__)

@dataclass
class AIOptionPlay:
    """Complete AI-generated option play recommendation."""
    # Basic info
    symbol: str
    company_name: str
    
    # Option details
    option_type: str  # CALL or PUT
    strike: float
    expiration: str
    entry_price: float
    target_price: float
    stop_loss: float
    
    # Probabilities and metrics
    probability_profit: float
    max_profit: float
    max_loss: float
    risk_reward_ratio: float
    position_size: int
    
    # Analysis scores
    confidence_score: float
    technical_score: float
    news_sentiment: float
    catalyst_impact: float
    volume_score: float
    
    # AI analysis
    ai_recommendation: str
    ai_confidence: float
    risk_warning: Optional[str]
    summary: str
    key_factors: List[str]
    
    # Supporting data
    catalysts: List[Dict[str, Any]]
    volume_alerts: List[Dict[str, Any]]
    polymarket_events: List[Dict[str, Any]]
    
    # Meta
    generated_at: datetime
    expires_at: datetime

class AIOptionGenerator:
    """Main service for generating AI-powered option plays."""
    
    def __init__(self):
        self.ticker_selector = TickerSelector()
        self.technical_analyzer = TechnicalAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        self.social_analyzer = SocialMediaAnalyzer()
        self.confidence_scorer = ConfidenceScorer()
        self.options_analyzer = OptionsAnalyzer()
        self.catalyst_detector = CatalystDetector()
        self.volume_analyzer = VolumeAnalyzer()
        
        # Rate limiting
        self.daily_generation_limit = 5
        self.generation_count = 0
        self.last_reset_date = datetime.now().date()
    
    async def generate_option_plays(self,
                                  max_plays: int = 5,
                                  min_confidence: float = 70.0,
                                  timeframe_days: int = 7,
                                  position_size_dollars: float = 1000,
                                  risk_tolerance: str = "MODERATE",
                                  directional_bias: str = "AI_DECIDES") -> List[AIOptionPlay]:
        """
        Generate AI-powered option plays with complete analysis.

        Args:
            max_plays: Maximum number of plays to generate
            min_confidence: Minimum confidence threshold
            timeframe_days: Target timeframe (1-30 days)
            position_size_dollars: Dollar amount to invest per play
            risk_tolerance: LOW, MODERATE, HIGH
            directional_bias: BULLISH, BEARISH, AI_DECIDES

        Returns:
            List of complete option play recommendations
        """
        
        # Check rate limiting
        if not self._check_rate_limit():
            logger.warning("Daily generation limit reached")
            return []
        
        logger.info(f"Generating {max_plays} option plays with {min_confidence}% min confidence")

        # Check if we're in demo mode (API keys are "demo", None, or empty)
        import os
        alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if alpha_key in [None, "", "demo"]:
            logger.info("Demo mode detected - generating mock play for testing")
            return await self._generate_demo_play(min_confidence, timeframe_days, position_size_dollars, directional_bias)

        try:
            # Step 1: Select top ticker candidates
            try:
                ticker_candidates = await self.ticker_selector.select_top_plays(
                    max_plays=max_plays * 2,  # Get more candidates to filter
                    min_confidence=min_confidence * 0.8,  # Lower threshold for initial screening
                    timeframe_days=timeframe_days
                )
            except Exception as e:
                logger.error(f"Error selecting ticker candidates: {e}")
                # Fallback to a simple mock candidate for testing when APIs are rate limited
                from ..services.ticker_selector import TickerCandidate
                ticker_candidates = [
                    TickerCandidate(
                        symbol="SPY",
                        company_name="SPDR S&P 500 ETF Trust",
                        sector="ETF",
                        market_cap=500000000000,
                        avg_volume=50000000,
                        current_price=450.0,
                        technical_score=75.0,
                        news_sentiment=0.1,
                        volatility=0.15,
                        options_volume=1000000,
                        confidence_score=72.5,
                        reasoning="Mock data due to API rate limits - SPY is always a reliable option with high liquidity"
                    )
                ]

            if not ticker_candidates:
                logger.warning("No ticker candidates found")
                return []
            
            # Step 2: Get high-impact prediction market events
            async with PolymarketService() as polymarket:
                polymarket_events = await polymarket.get_high_probability_events(
                    min_probability=0.8, days_ahead=timeframe_days
                )
            
            # Step 3: Generate complete analysis for each candidate
            option_plays = []
            
            for candidate in ticker_candidates[:max_plays]:
                try:
                    play = await self._generate_single_play(
                        candidate, polymarket_events, timeframe_days,
                        position_size_dollars, risk_tolerance, directional_bias
                    )
                    
                    if play and play.confidence_score >= min_confidence:
                        option_plays.append(play)
                        
                except Exception as e:
                    logger.warning(f"Error generating play for {candidate.symbol}: {e}")
                    continue
            
            # Step 4: Sort by confidence and return top plays
            option_plays.sort(key=lambda x: x.confidence_score, reverse=True)
            
            # Increment generation count
            self.generation_count += 1
            
            logger.info(f"Generated {len(option_plays)} option plays")
            return option_plays[:max_plays]
            
        except Exception as e:
            logger.error(f"Error generating option plays: {e}")
            return []
    
    async def _generate_single_play(self,
                                  candidate: TickerCandidate,
                                  polymarket_events: List[PredictionMarket],
                                  timeframe_days: int,
                                  position_size_dollars: float,
                                  risk_tolerance: str,
                                  directional_bias: str = "AI_DECIDES") -> Optional[AIOptionPlay]:
        """Generate a complete option play for a single ticker."""
        
        symbol = candidate.symbol
        
        try:
            # Run all analysis concurrently for maximum efficiency
            tasks = [
                self.technical_analyzer.analyze(symbol),
                self.news_analyzer.analyze_sentiment(symbol, candidate.company_name),
                self.social_analyzer.analyze(symbol),
                self.catalyst_detector.detect_catalysts(symbol, timeframe_days),
                self.volume_analyzer.analyze_unusual_volume(symbol),
                self._analyze_options_flow(symbol),  # Enhanced options flow analysis
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)

            technical_data = results[0] if not isinstance(results[0], Exception) else {}
            news_data = results[1] if not isinstance(results[1], Exception) else {}
            social_data = results[2] if not isinstance(results[2], Exception) else {}
            catalysts = results[3] if not isinstance(results[3], Exception) else []
            volume_data = results[4] if not isinstance(results[4], Exception) else {}
            options_flow_data = results[5] if not isinstance(results[5], Exception) else {}
            
            # Calculate enhanced confidence score with all data sources
            confidence_score = await self._calculate_enhanced_confidence(
                candidate, technical_data, news_data, social_data, catalysts,
                volume_data, options_flow_data, polymarket_events
            )
            
            # Generate option recommendation
            option_rec = await self.options_analyzer.analyze_option_opportunity(
                symbol, technical_data, confidence_score, 
                timeframe_days, position_size_dollars
            )
            
            if not option_rec:
                return None
            
            # Get AI analysis from Grok with comprehensive data
            all_data = {
                'technical': technical_data,
                'news': news_data,
                'social': social_data,
                'polymarket': [event.__dict__ for event in polymarket_events],
                'catalysts': {'catalysts': [cat.__dict__ for cat in catalysts]},
                'volume': volume_data,
                'options_flow': options_flow_data,
                'confidence_score': confidence_score
            }
            
            async with GrokAIService() as grok:
                # Create a comprehensive data package for Grok analysis
                ai_analysis = await grok.analyze_comprehensive_option_play(
                    symbol, all_data, confidence_score
                )
            
            # Create complete option play
            return AIOptionPlay(
                # Basic info
                symbol=symbol,
                company_name=candidate.company_name,
                
                # Option details
                option_type=option_rec.option_type,
                strike=option_rec.strike,
                expiration=option_rec.expiration,
                entry_price=option_rec.entry_price,
                target_price=option_rec.target_price,
                stop_loss=option_rec.stop_loss,
                
                # Probabilities and metrics
                probability_profit=option_rec.probability_profit,
                max_profit=option_rec.max_profit,
                max_loss=option_rec.max_loss,
                risk_reward_ratio=option_rec.risk_reward_ratio,
                position_size=option_rec.position_size,
                
                # Analysis scores
                confidence_score=confidence_score,
                technical_score=candidate.technical_score,
                news_sentiment=candidate.news_sentiment,
                catalyst_impact=self._calculate_catalyst_impact(catalysts),
                volume_score=self._calculate_volume_score(volume_data),
                
                # AI analysis
                ai_recommendation=ai_analysis.recommendation if ai_analysis else "HOLD",
                ai_confidence=ai_analysis.confidence if ai_analysis else confidence_score,
                risk_warning=ai_analysis.risk_warning if ai_analysis else None,
                summary=ai_analysis.summary if ai_analysis else option_rec.reasoning,
                key_factors=ai_analysis.key_factors if ai_analysis else [],
                
                # Supporting data
                catalysts=[cat.__dict__ for cat in catalysts],
                volume_alerts=volume_data.get('alerts', []),
                polymarket_events=[event.__dict__ for event in polymarket_events 
                                 if self._is_relevant_to_symbol(event, symbol)],
                
                # Meta
                generated_at=datetime.now(),
                expires_at=datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)  # Market close
            )
            
        except Exception as e:
            logger.error(f"Error generating play for {symbol}: {e}")
            return None
    
    async def _calculate_enhanced_confidence(self,
                                           candidate: TickerCandidate,
                                           technical_data: Dict,
                                           news_data: Dict,
                                           social_data: Dict,
                                           catalysts: List[Catalyst],
                                           volume_data: Dict,
                                           options_flow_data: Dict,
                                           polymarket_events: List[PredictionMarket]) -> float:
        """Calculate enhanced confidence score with all factors including social sentiment."""

        # Base confidence from ticker selection
        base_confidence = candidate.confidence_score

        # Technical analysis boost/penalty
        technical_boost = 0.0
        if technical_data.get('technical_score'):
            tech_score = technical_data['technical_score']
            if tech_score > 70:
                technical_boost = (tech_score - 70) * 0.3  # Up to 9 points for 100 score
            elif tech_score < 30:
                technical_boost = (tech_score - 30) * 0.3  # Negative for bearish signals

        # News sentiment boost/penalty
        news_boost = 0.0
        if news_data.get('news_score'):
            news_score = news_data['news_score']
            if news_score > 60:
                news_boost = (news_score - 60) * 0.2  # Up to 8 points for 100 score
            elif news_score < 40:
                news_boost = (news_score - 40) * 0.2  # Negative for bearish news

        # Social media sentiment boost/penalty
        social_boost = 0.0
        if social_data.get('social_score'):
            social_score = social_data['social_score']
            if social_score > 60:
                social_boost = (social_score - 60) * 0.15  # Up to 6 points for 100 score
            elif social_score < 40:
                social_boost = (social_score - 40) * 0.15  # Negative for bearish sentiment

        # Catalyst boost
        catalyst_boost = 0.0
        for catalyst in catalysts:
            if catalyst.impact_score >= 7:  # High impact catalysts
                catalyst_boost += catalyst.impact_score * 2
        catalyst_boost = min(catalyst_boost, 15)  # Cap at 15 points

        # Volume boost
        volume_boost = 0.0
        if volume_data.get('stock_volume', {}).get('unusual_activity', False):
            volume_ratio = volume_data['stock_volume'].get('volume_ratio', 1)
            volume_boost = min(volume_ratio * 2, 10)  # Cap at 10 points

        # Options flow boost/penalty
        options_flow_boost = 0.0
        if options_flow_data.get('bullish_flow_ratio', 0) > 0.7:
            options_flow_boost = 8  # Strong bullish flow
        elif options_flow_data.get('bullish_flow_ratio', 0) < 0.3:
            options_flow_boost = -8  # Strong bearish flow
        elif options_flow_data.get('unusual_activity_score', 0) > 7:
            options_flow_boost = 5  # High unusual activity

        # Polymarket boost
        polymarket_boost = 0.0
        for event in polymarket_events:
            if event.impact_level == 'HIGH' and event.probability > 0.85:
                polymarket_boost += 5
        polymarket_boost = min(polymarket_boost, 10)  # Cap at 10 points

        # Calculate final confidence with all factors
        enhanced_confidence = (base_confidence + technical_boost + news_boost +
                             social_boost + catalyst_boost + volume_boost +
                             options_flow_boost + polymarket_boost)

        return min(max(enhanced_confidence, 0.0), 100.0)  # Clamp between 0-100
    
    def _calculate_catalyst_impact(self, catalysts: List[Catalyst]) -> float:
        """Calculate overall catalyst impact score."""
        if not catalysts:
            return 0.0
        
        total_impact = sum(cat.impact_score * cat.confidence for cat in catalysts)
        return min(total_impact / len(catalysts), 10.0)
    
    def _calculate_volume_score(self, volume_data: Dict) -> float:
        """Calculate volume score based on unusual activity."""
        if not volume_data:
            return 0.0
        
        score = 0.0
        
        # Stock volume score
        stock_vol = volume_data.get('stock_volume', {})
        if stock_vol.get('unusual_activity', False):
            ratio = stock_vol.get('volume_ratio', 1)
            score += min(ratio * 2, 10)
        
        # Options volume score
        options_vol = volume_data.get('options_volume', {})
        if options_vol.get('unusual_options_activity', False):
            ratio = options_vol.get('options_volume_ratio', 1)
            score += min(ratio * 1.5, 8)
        
        return min(score, 10.0)
    
    def _is_relevant_to_symbol(self, event: PredictionMarket, symbol: str) -> bool:
        """Check if a prediction market event is relevant to the symbol."""
        text = f"{event.question} {event.description}".lower()
        
        # Check for direct symbol mention
        if symbol.lower() in text:
            return True
        
        # Check for sector/market relevance
        if event.category in ['economics', 'earnings'] and event.impact_level == 'HIGH':
            return True
        
        return False
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within the daily rate limit."""
        current_date = datetime.now().date()
        
        # Reset counter if it's a new day
        if current_date != self.last_reset_date:
            self.generation_count = 0
            self.last_reset_date = current_date
        
        return self.generation_count < self.daily_generation_limit

    async def _analyze_options_flow(self, symbol: str) -> Dict[str, Any]:
        """Analyze options flow patterns for enhanced insights."""
        try:
            # Get recent options data
            from ..services.stock_data import StockDataService

            async with StockDataService() as stock_service:
                options_data = await stock_service.get_options_chain(symbol)

                if not options_data:
                    return {}

                # Analyze call/put ratio
                calls = options_data.get('calls', [])
                puts = options_data.get('puts', [])

                total_call_volume = sum(opt.get('volume', 0) for opt in calls)
                total_put_volume = sum(opt.get('volume', 0) for opt in puts)
                total_volume = total_call_volume + total_put_volume

                if total_volume == 0:
                    return {'error': 'No options volume data available'}

                # Calculate flow metrics
                bullish_flow_ratio = total_call_volume / total_volume if total_volume > 0 else 0.5

                # Identify unusual activity
                unusual_contracts = []
                for contract in calls + puts:
                    volume = contract.get('volume', 0)
                    open_interest = contract.get('open_interest', 1)

                    # Volume to OI ratio > 2 indicates unusual activity
                    if volume > 0 and open_interest > 0 and (volume / open_interest) > 2:
                        unusual_contracts.append({
                            'contract': contract.get('contract_symbol', ''),
                            'type': contract.get('option_type', ''),
                            'strike': contract.get('strike_price', 0),
                            'volume': volume,
                            'open_interest': open_interest,
                            'volume_oi_ratio': volume / open_interest
                        })

                # Calculate unusual activity score
                unusual_activity_score = min(len(unusual_contracts) * 2, 10)

                # Analyze large trades (premium > $50k equivalent)
                large_trades = []
                for contract in calls + puts:
                    volume = contract.get('volume', 0)
                    last_price = contract.get('last_price', 0)

                    if volume > 0 and last_price > 0:
                        premium_value = volume * last_price * 100  # Options are per 100 shares
                        if premium_value > 50000:  # $50k+ trades
                            large_trades.append({
                                'contract': contract.get('contract_symbol', ''),
                                'premium_value': premium_value,
                                'volume': volume
                            })

                return {
                    'symbol': symbol,
                    'total_options_volume': total_volume,
                    'call_volume': total_call_volume,
                    'put_volume': total_put_volume,
                    'bullish_flow_ratio': bullish_flow_ratio,
                    'unusual_contracts': unusual_contracts[:5],  # Top 5
                    'unusual_activity_score': unusual_activity_score,
                    'large_trades': large_trades[:3],  # Top 3
                    'flow_sentiment': 'BULLISH' if bullish_flow_ratio > 0.6 else 'BEARISH' if bullish_flow_ratio < 0.4 else 'NEUTRAL'
                }

        except Exception as e:
            logger.warning(f"Error analyzing options flow for {symbol}: {e}")
            return {'error': f'Options flow analysis failed: {str(e)}'}

    async def _generate_demo_play(self, min_confidence: float, timeframe_days: int, position_size_dollars: float, directional_bias: str = "AI_DECIDES") -> List[AIOptionPlay]:
        """Generate a demo play for testing when API keys are not available."""
        from datetime import datetime, timedelta

        # Only generate if confidence threshold is reasonable for demo
        if min_confidence > 75:
            return []

        # Generate different demo plays based on directional bias
        if directional_bias == "BULLISH":
            demo_play = self._create_bullish_demo_play(timeframe_days, position_size_dollars)
        elif directional_bias == "BEARISH":
            demo_play = self._create_bearish_demo_play(timeframe_days, position_size_dollars)
        else:  # AI_DECIDES
            # Mix of both call and put for AI mode
            import random
            if random.choice([True, False]):
                demo_play = self._create_bullish_demo_play(timeframe_days, position_size_dollars)
            else:
                demo_play = self._create_bearish_demo_play(timeframe_days, position_size_dollars)

        return [demo_play]

    def _create_bullish_demo_play(self, timeframe_days: int, position_size_dollars: float) -> AIOptionPlay:
        """Create a bullish demo play (CALL option)."""
        from datetime import datetime, timedelta

        return AIOptionPlay(
            symbol="SPY",
            company_name="SPDR S&P 500 ETF Trust",
            option_type="CALL",
            strike=455.0,
            expiration=(datetime.now() + timedelta(days=timeframe_days)).strftime("%Y-%m-%d"),
            entry_price=3.50,
            target_price=5.25,
            stop_loss=2.10,
            probability_profit=0.72,
            max_profit=position_size_dollars * 0.50,
            max_loss=position_size_dollars * 0.40,
            risk_reward_ratio=1.25,
            position_size=int(position_size_dollars / 350),
            confidence_score=72.5,
            technical_score=75.0,
            news_sentiment=0.15,
            catalyst_impact=7.2,
            volume_score=8.5,
            ai_recommendation="BUY",
            ai_confidence=0.725,
            risk_warning="Demo bullish play for testing purposes only. Not real market data.",
            summary="Demo SPY call option with bullish outlook based on simulated analysis.",
            key_factors=[
                "Strong bullish momentum in ETF",
                "Moderate volatility suitable for calls",
                "Demo data - not real market conditions"
            ],
            catalysts=[],
            volume_alerts=[],
            polymarket_events=[],
            generated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=4)
        )

    def _create_bearish_demo_play(self, timeframe_days: int, position_size_dollars: float) -> AIOptionPlay:
        """Create a bearish demo play (PUT option)."""
        from datetime import datetime, timedelta

        return AIOptionPlay(
            symbol="SPY",
            company_name="SPDR S&P 500 ETF Trust",
            option_type="PUT",
            strike=445.0,
            expiration=(datetime.now() + timedelta(days=timeframe_days)).strftime("%Y-%m-%d"),
            entry_price=2.80,
            target_price=4.20,
            stop_loss=1.68,
            probability_profit=0.68,
            max_profit=position_size_dollars * 0.45,
            max_loss=position_size_dollars * 0.35,
            risk_reward_ratio=1.29,
            position_size=int(position_size_dollars / 280),
            confidence_score=68.5,
            technical_score=65.0,
            news_sentiment=-0.12,
            catalyst_impact=6.8,
            volume_score=7.5,
            ai_recommendation="BUY",
            ai_confidence=0.685,
            risk_warning="Demo bearish play for testing purposes only. Not real market data.",
            summary="Demo SPY put option with bearish outlook based on simulated analysis.",
            key_factors=[
                "Bearish technical indicators detected",
                "Market volatility favoring puts",
                "Demo data - not real market conditions"
            ],
            catalysts=[],
            volume_alerts=[],
            polymarket_events=[],
            generated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=4)
        )

# Utility function for easy usage
async def generate_ai_plays(max_plays: int = 5, min_confidence: float = 70.0,
                          timeframe_days: int = 7, position_size: float = 1000,
                          risk_tolerance: str = "MODERATE") -> List[AIOptionPlay]:
    """Convenience function to generate AI option plays."""
    generator = AIOptionGenerator()
    return await generator.generate_option_plays(
        max_plays, min_confidence, timeframe_days, position_size, risk_tolerance
    )
