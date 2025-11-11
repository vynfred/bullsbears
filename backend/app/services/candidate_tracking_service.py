"""
Candidate Tracking Service
Track all predictor agent candidates and perform retrospective analysis
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from ..models.pick_candidates import (
    PickCandidate, CandidatePriceTracking, CandidateRetrospectiveAnalysis, 
    CandidateModelLearning
)
from ..core.database import get_database
from ..core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


@dataclass
class CandidateData:
    """Data structure for storing candidate information"""
    ticker: str
    predictor_agent: str
    agent_model: str
    agent_confidence: float
    prediction_type: str  # 'bullish' or 'bearish'
    reasoning: str
    vision_targets: Dict[str, Any]
    current_price: float
    market_conditions: Dict[str, Any]
    technical_indicators: Dict[str, Any]
    sentiment_score: float


@dataclass
class RetrospectiveResults:
    """Results from retrospective analysis"""
    total_candidates: int
    selected_picks: int
    rejected_candidates: int
    missed_opportunities: List[Dict[str, Any]]
    performance_comparison: Dict[str, float]
    model_recommendations: Dict[str, Any]


class CandidateTrackingService:
    """
    Service for tracking predictor agent candidates and retrospective analysis
    """
    
    def __init__(self):
        self.db_session = None
        self.redis_client = None
        self.tracking_period_days = 30  # Track candidates for 30 days
        self.analysis_frequency_days = 7  # Run retrospective analysis weekly
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.db_session = await get_database_session()
        self.redis_client = await get_redis_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.db_session:
            await self.db_session.close()
        if self.redis_client:
            await self.redis_client.disconnect()
    
    async def store_candidate(self, candidate_data: CandidateData, prediction_cycle: str) -> int:
        """
        Store a predictor agent candidate for tracking
        
        Args:
            candidate_data: Candidate information from predictor agent
            prediction_cycle: Current prediction cycle ('morning', 'afternoon', etc.)
            
        Returns:
            Candidate ID for tracking
        """
        try:
            # Extract vision targets
            vision_targets = candidate_data.vision_targets
            target_low = vision_targets.get('conservative_target')
            target_medium = vision_targets.get('expected_target')
            target_high = vision_targets.get('optimistic_target')
            target_timeframe = vision_targets.get('timeframe_days', 14)
            
            # Create candidate record
            candidate = PickCandidate(
                ticker=candidate_data.ticker,
                prediction_cycle=prediction_cycle,
                predictor_agent=candidate_data.predictor_agent,
                agent_model=candidate_data.agent_model,
                agent_confidence=candidate_data.agent_confidence,
                prediction_type=candidate_data.prediction_type,
                reasoning=candidate_data.reasoning,
                vision_targets=candidate_data.vision_targets,
                target_low=target_low,
                target_medium=target_medium,
                target_high=target_high,
                target_timeframe_days=target_timeframe,
                current_price=candidate_data.current_price,
                market_conditions=candidate_data.market_conditions,
                technical_indicators=candidate_data.technical_indicators,
                sentiment_score=candidate_data.sentiment_score
            )
            
            self.db_session.add(candidate)
            await self.db_session.commit()
            
            # Start price tracking
            await self._start_price_tracking(candidate.id, candidate_data.ticker, candidate_data.current_price)
            
            logger.info(f"Stored candidate {candidate.id}: {candidate_data.ticker} from {candidate_data.predictor_agent}")
            return candidate.id
            
        except Exception as e:
            logger.error(f"Error storing candidate: {e}")
            await self.db_session.rollback()
            raise
    
    async def mark_candidate_selected(self, candidate_id: int, final_pick_id: int, arbitrator_reasoning: str):
        """
        Mark a candidate as selected by the arbitrator
        
        Args:
            candidate_id: ID of the selected candidate
            final_pick_id: ID of the final pick record
            arbitrator_reasoning: Arbitrator's reasoning for selection
        """
        try:
            candidate = await self.db_session.get(PickCandidate, candidate_id)
            if candidate:
                candidate.selected_by_arbitrator = True
                candidate.final_pick_id = final_pick_id
                candidate.arbitrator_reasoning = arbitrator_reasoning
                
                await self.db_session.commit()
                logger.info(f"Marked candidate {candidate_id} as selected")
            
        except Exception as e:
            logger.error(f"Error marking candidate as selected: {e}")
            await self.db_session.rollback()
    
    async def update_candidate_prices(self, ticker: str, current_price: float):
        """
        Update price tracking for all active candidates of a ticker
        
        Args:
            ticker: Stock ticker
            current_price: Current stock price
        """
        try:
            # Get active candidates for this ticker (within tracking period)
            cutoff_date = datetime.now() - timedelta(days=self.tracking_period_days)
            
            candidates = await self.db_session.execute(
                f"""
                SELECT id, current_price, target_low, target_medium, target_high, prediction_date
                FROM pick_candidates 
                WHERE ticker = '{ticker}' 
                AND prediction_date >= '{cutoff_date}'
                AND outcome_analyzed = FALSE
                """
            )
            
            for candidate in candidates:
                candidate_id = candidate.id
                prediction_price = candidate.current_price
                prediction_date = candidate.prediction_date
                
                # Calculate performance metrics
                percent_change = ((current_price - prediction_price) / prediction_price) * 100
                days_since_prediction = (datetime.now() - prediction_date).days
                
                # Check target achievements
                target_low_achieved = False
                target_medium_achieved = False
                target_high_achieved = False
                
                if candidate.target_low and current_price >= candidate.target_low:
                    target_low_achieved = True
                if candidate.target_medium and current_price >= candidate.target_medium:
                    target_medium_achieved = True
                if candidate.target_high and current_price >= candidate.target_high:
                    target_high_achieved = True
                
                # Store price tracking record
                price_tracking = CandidatePriceTracking(
                    candidate_id=candidate_id,
                    ticker=ticker,
                    price=current_price,
                    percent_change=percent_change,
                    days_since_prediction=days_since_prediction,
                    target_low_achieved=target_low_achieved,
                    target_medium_achieved=target_medium_achieved,
                    target_high_achieved=target_high_achieved
                )
                
                self.db_session.add(price_tracking)
                
                # Update candidate max/min prices
                await self._update_candidate_extremes(candidate_id, current_price, percent_change)
            
            await self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Error updating candidate prices for {ticker}: {e}")
            await self.db_session.rollback()
    
    async def _update_candidate_extremes(self, candidate_id: int, current_price: float, percent_change: float):
        """Update candidate's max/min price tracking"""
        try:
            candidate = await self.db_session.get(PickCandidate, candidate_id)
            if candidate:
                # Update max price reached
                if candidate.max_price_reached is None or current_price > candidate.max_price_reached:
                    candidate.max_price_reached = current_price
                
                # Update min price reached
                if candidate.min_price_reached is None or current_price < candidate.min_price_reached:
                    candidate.min_price_reached = current_price
                
                # Update max gain percent
                if candidate.max_gain_percent is None or percent_change > candidate.max_gain_percent:
                    candidate.max_gain_percent = percent_change
                
                # Check if targets were hit for the first time
                if not candidate.target_low_hit and candidate.target_low and current_price >= candidate.target_low:
                    candidate.target_low_hit = True
                    if candidate.days_to_target_hit is None:
                        candidate.days_to_target_hit = (datetime.now() - candidate.prediction_date).days
                
                if not candidate.target_medium_hit and candidate.target_medium and current_price >= candidate.target_medium:
                    candidate.target_medium_hit = True
                    if candidate.days_to_target_hit is None:
                        candidate.days_to_target_hit = (datetime.now() - candidate.prediction_date).days
                
                if not candidate.target_high_hit and candidate.target_high and current_price >= candidate.target_high:
                    candidate.target_high_hit = True
                    if candidate.days_to_target_hit is None:
                        candidate.days_to_target_hit = (datetime.now() - candidate.prediction_date).days
                
        except Exception as e:
            logger.error(f"Error updating candidate extremes: {e}")
    
    async def _start_price_tracking(self, candidate_id: int, ticker: str, initial_price: float):
        """Start price tracking for a new candidate"""
        try:
            # Create initial price tracking record
            initial_tracking = CandidatePriceTracking(
                candidate_id=candidate_id,
                ticker=ticker,
                price=initial_price,
                percent_change=0.0,
                days_since_prediction=0,
                target_low_achieved=False,
                target_medium_achieved=False,
                target_high_achieved=False
            )
            
            self.db_session.add(initial_tracking)
            
            # Cache ticker for price update monitoring
            cache_key = f"candidate_tracking_tickers"
            await self.redis_client.sadd(cache_key, ticker)
            await self.redis_client.expire(cache_key, 86400 * self.tracking_period_days)  # Expire after tracking period
            
        except Exception as e:
            logger.error(f"Error starting price tracking: {e}")
    
    async def run_retrospective_analysis(self, analysis_period_days: int = 30) -> RetrospectiveResults:
        """
        Run retrospective analysis to identify missed opportunities
        
        Args:
            analysis_period_days: How many days back to analyze
            
        Returns:
            RetrospectiveResults with analysis findings
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=analysis_period_days)
            
            # Get all candidates from analysis period
            candidates = await self.db_session.execute(
                f"""
                SELECT * FROM pick_candidates 
                WHERE prediction_date >= '{cutoff_date}'
                AND outcome_analyzed = FALSE
                """
            )
            
            selected_candidates = [c for c in candidates if c.selected_by_arbitrator]
            rejected_candidates = [c for c in candidates if not c.selected_by_arbitrator]
            
            # Calculate performance metrics
            selected_performance = await self._calculate_performance_metrics(selected_candidates)
            rejected_performance = await self._calculate_performance_metrics(rejected_candidates)
            
            # Identify missed opportunities
            missed_opportunities = await self._identify_missed_opportunities(rejected_candidates, selected_performance['avg_performance'])
            
            # Generate model recommendations
            model_recommendations = await self._generate_model_recommendations(
                selected_candidates, rejected_candidates, missed_opportunities
            )
            
            # Store analysis results
            analysis_record = CandidateRetrospectiveAnalysis(
                analysis_period_days=analysis_period_days,
                total_candidates=len(candidates),
                selected_picks=len(selected_candidates),
                rejected_candidates=len(rejected_candidates),
                selected_picks_avg_performance=selected_performance['avg_performance'],
                rejected_candidates_avg_performance=rejected_performance['avg_performance'],
                missed_opportunities_count=len(missed_opportunities),
                selected_target_hit_rate=selected_performance['target_hit_rate'],
                rejected_target_hit_rate=rejected_performance['target_hit_rate'],
                top_missed_opportunities=missed_opportunities[:10],  # Top 10
                model_adjustment_recommendations=model_recommendations
            )
            
            self.db_session.add(analysis_record)
            await self.db_session.commit()
            
            # Mark candidates as analyzed
            for candidate in candidates:
                candidate.outcome_analyzed = True
                candidate.analysis_date = datetime.now()
            
            await self.db_session.commit()
            
            results = RetrospectiveResults(
                total_candidates=len(candidates),
                selected_picks=len(selected_candidates),
                rejected_candidates=len(rejected_candidates),
                missed_opportunities=missed_opportunities,
                performance_comparison={
                    'selected_avg': selected_performance['avg_performance'],
                    'rejected_avg': rejected_performance['avg_performance']
                },
                model_recommendations=model_recommendations
            )
            
            logger.info(f"Retrospective analysis complete: {len(missed_opportunities)} missed opportunities identified")
            return results
            
        except Exception as e:
            logger.error(f"Error in retrospective analysis: {e}")
            raise

    async def _calculate_performance_metrics(self, candidates: List[Any]) -> Dict[str, float]:
        """Calculate performance metrics for a group of candidates"""
        if not candidates:
            return {'avg_performance': 0.0, 'target_hit_rate': 0.0}

        total_performance = 0.0
        targets_hit = 0
        valid_candidates = 0

        for candidate in candidates:
            if candidate.max_gain_percent is not None:
                total_performance += candidate.max_gain_percent
                valid_candidates += 1

            # Check if any target was hit
            if candidate.target_low_hit or candidate.target_medium_hit or candidate.target_high_hit:
                targets_hit += 1

        avg_performance = total_performance / valid_candidates if valid_candidates > 0 else 0.0
        target_hit_rate = targets_hit / len(candidates) if candidates else 0.0

        return {
            'avg_performance': avg_performance,
            'target_hit_rate': target_hit_rate
        }

    async def _identify_missed_opportunities(self, rejected_candidates: List[Any], selected_avg_performance: float) -> List[Dict[str, Any]]:
        """Identify rejected candidates that outperformed selected picks"""
        missed_opportunities = []

        for candidate in rejected_candidates:
            if candidate.max_gain_percent and candidate.max_gain_percent > selected_avg_performance:
                missed_opportunities.append({
                    'candidate_id': candidate.id,
                    'ticker': candidate.ticker,
                    'predictor_agent': candidate.predictor_agent,
                    'agent_confidence': candidate.agent_confidence,
                    'prediction_type': candidate.prediction_type,
                    'performance': candidate.max_gain_percent,
                    'targets_hit': {
                        'low': candidate.target_low_hit,
                        'medium': candidate.target_medium_hit,
                        'high': candidate.target_high_hit
                    },
                    'days_to_target': candidate.days_to_target_hit,
                    'arbitrator_reasoning': candidate.arbitrator_reasoning
                })

        # Sort by performance (best missed opportunities first)
        missed_opportunities.sort(key=lambda x: x['performance'], reverse=True)

        return missed_opportunities

    async def _generate_model_recommendations(self, selected_candidates: List[Any], rejected_candidates: List[Any], missed_opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate recommendations for model improvements"""
        recommendations = {
            'predictor_adjustments': {},
            'arbitrator_adjustments': {},
            'confidence_calibration': {},
            'threshold_adjustments': {}
        }

        # Analyze predictor performance
        predictor_performance = {}
        for candidate in rejected_candidates:
            agent = candidate.predictor_agent
            if agent not in predictor_performance:
                predictor_performance[agent] = {'total': 0, 'good_missed': 0, 'avg_performance': 0.0}

            predictor_performance[agent]['total'] += 1
            if candidate.max_gain_percent:
                predictor_performance[agent]['avg_performance'] += candidate.max_gain_percent

            # Check if this was a missed opportunity
            if any(mo['candidate_id'] == candidate.id for mo in missed_opportunities):
                predictor_performance[agent]['good_missed'] += 1

        # Calculate predictor recommendations
        for agent, stats in predictor_performance.items():
            if stats['total'] > 0:
                avg_perf = stats['avg_performance'] / stats['total']
                miss_rate = stats['good_missed'] / stats['total']

                if miss_rate > 0.3:  # If more than 30% of rejected candidates were good
                    recommendations['predictor_adjustments'][agent] = {
                        'action': 'increase_weight',
                        'reason': f'High miss rate ({miss_rate:.1%}) with avg performance {avg_perf:.1f}%',
                        'suggested_weight_increase': min(0.2, miss_rate * 0.5)
                    }

        # Analyze confidence calibration
        high_confidence_missed = [mo for mo in missed_opportunities if mo['agent_confidence'] > 0.7]
        if len(high_confidence_missed) > len(missed_opportunities) * 0.5:
            recommendations['confidence_calibration']['high_confidence_bias'] = {
                'issue': 'High confidence candidates being rejected despite good performance',
                'suggestion': 'Lower arbitrator threshold for high-confidence predictions',
                'affected_count': len(high_confidence_missed)
            }

        # Arbitrator threshold recommendations
        if len(missed_opportunities) > len(selected_candidates) * 0.3:
            recommendations['threshold_adjustments']['selection_threshold'] = {
                'issue': 'Too many good candidates being rejected',
                'suggestion': 'Lower selection threshold or increase daily pick count',
                'missed_count': len(missed_opportunities)
            }

        return recommendations


# Global instance
candidate_tracking_service = None

async def get_candidate_tracking_service() -> CandidateTrackingService:
    """Get global CandidateTrackingService instance"""
    global candidate_tracking_service
    if candidate_tracking_service is None:
        candidate_tracking_service = CandidateTrackingService()
    return candidate_tracking_service
