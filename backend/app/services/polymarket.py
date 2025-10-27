"""
Polymarket API integration for prediction market data.
Focuses on economic events and earnings with high probability outcomes.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PredictionMarket:
    """Data class for prediction market information."""
    market_id: str
    question: str
    category: str
    probability: float
    volume: float
    end_date: datetime
    description: str
    relevance_score: float
    impact_level: str  # HIGH, MEDIUM, LOW

class PolymarketService:
    """Service for fetching prediction market data from Polymarket."""
    
    def __init__(self):
        self.base_url = "https://gamma-api.polymarket.com"
        self.session = None
        
        # Categories we care about for trading
        self.relevant_categories = {
            'economics': ['inflation', 'fed', 'interest rates', 'gdp', 'unemployment'],
            'earnings': ['earnings', 'revenue', 'profit', 'guidance'],
            'politics': ['election', 'policy', 'regulation', 'trade'],
            'crypto': ['bitcoin', 'ethereum', 'crypto', 'sec'],
            'tech': ['ai', 'tech', 'apple', 'google', 'microsoft', 'tesla']
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'OptionsTrader/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_high_probability_events(self, 
                                        min_probability: float = 0.8,
                                        days_ahead: int = 7) -> List[PredictionMarket]:
        """
        Get prediction markets with high probability (>80%) that could impact trading.
        
        Args:
            min_probability: Minimum probability threshold (default 0.8 = 80%)
            days_ahead: Look ahead this many days (default 7)
            
        Returns:
            List of high-probability prediction markets
        """
        try:
            if not self.session:
                async with self:
                    return await self._fetch_markets(min_probability, days_ahead)
            else:
                return await self._fetch_markets(min_probability, days_ahead)
                
        except Exception as e:
            logger.error(f"Error fetching Polymarket data: {e}")
            return []
    
    async def _fetch_markets(self, min_probability: float, days_ahead: int) -> List[PredictionMarket]:
        """Fetch and filter prediction markets."""
        markets = []
        
        try:
            # Get active markets
            url = f"{self.base_url}/markets"
            params = {
                'active': 'true',
                'limit': 100,
                'offset': 0
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    raw_markets = data.get('data', [])
                    
                    for market_data in raw_markets:
                        market = await self._process_market(market_data, min_probability, days_ahead)
                        if market:
                            markets.append(market)
                else:
                    logger.warning(f"Polymarket API returned status {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
        
        # Sort by relevance score and probability
        markets.sort(key=lambda x: (x.relevance_score, x.probability), reverse=True)
        return markets
    
    async def _process_market(self, market_data: Dict, 
                            min_probability: float, days_ahead: int) -> Optional[PredictionMarket]:
        """Process individual market data."""
        try:
            # Extract basic info
            market_id = market_data.get('id', '')
            question = market_data.get('question', '')
            description = market_data.get('description', '')
            
            # Get end date
            end_date_str = market_data.get('endDate')
            if not end_date_str:
                return None
            
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            
            # Check if within our timeframe
            now = datetime.now()
            if end_date < now or end_date > now + timedelta(days=days_ahead):
                return None
            
            # Get probability (handle different data structures safely)
            outcomes = market_data.get('outcomes', [])
            max_probability = 0.0

            if outcomes:
                # Handle list of outcomes with error checking
                if isinstance(outcomes, list):
                    for outcome in outcomes:
                        try:
                            if isinstance(outcome, dict):
                                prob = float(outcome.get('price', 0))
                                max_probability = max(max_probability, prob)
                            else:
                                # Handle case where outcome is not a dict
                                logger.warning(f"Unexpected outcome format for market {market_data.get('id', 'unknown')}: {type(outcome)}")
                                continue
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error parsing outcome probability: {e}")
                            continue
                else:
                    # Handle case where outcomes is not a list
                    logger.warning(f"Unexpected outcomes format: {type(outcomes)}")
                    # Try to extract probability from alternative fields
                    max_probability = float(market_data.get('probability', 0))
                    if max_probability == 0:
                        max_probability = float(market_data.get('price', 0))
            else:
                # No outcomes, try alternative probability fields
                try:
                    max_probability = float(market_data.get('probability', 0))
                    if max_probability == 0:
                        max_probability = float(market_data.get('price', 0))
                except (ValueError, TypeError):
                    logger.warning(f"No valid probability data for market {market_data.get('id', 'unknown')}")
                    return None
            
            # Skip if probability is too low
            if max_probability < min_probability:
                return None
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance(question, description)
            if relevance_score < 0.3:  # Skip irrelevant markets
                return None
            
            # Get volume
            volume = float(market_data.get('volume', 0))
            
            # Determine category
            category = self._categorize_market(question, description)
            
            # Determine impact level
            impact_level = self._determine_impact_level(question, volume, max_probability)
            
            return PredictionMarket(
                market_id=market_id,
                question=question,
                category=category,
                probability=max_probability,
                volume=volume,
                end_date=end_date,
                description=description,
                relevance_score=relevance_score,
                impact_level=impact_level
            )
            
        except Exception as e:
            logger.warning(f"Error processing market: {e}")
            return None
    
    def _calculate_relevance(self, question: str, description: str) -> float:
        """Calculate how relevant this market is to trading decisions."""
        text = f"{question} {description}".lower()
        relevance_score = 0.0
        
        # Check for relevant keywords
        for category, keywords in self.relevant_categories.items():
            category_score = 0.0
            for keyword in keywords:
                if keyword in text:
                    category_score += 1.0
            
            # Weight different categories
            if category == 'economics':
                relevance_score += category_score * 0.4  # Highest weight
            elif category == 'earnings':
                relevance_score += category_score * 0.3
            elif category in ['politics', 'crypto', 'tech']:
                relevance_score += category_score * 0.2
            else:
                relevance_score += category_score * 0.1
        
        # Normalize to 0-1 scale
        return min(relevance_score / 5.0, 1.0)
    
    def _categorize_market(self, question: str, description: str) -> str:
        """Categorize the market based on content."""
        text = f"{question} {description}".lower()
        
        # Check categories in order of priority
        if any(keyword in text for keyword in self.relevant_categories['economics']):
            return 'economics'
        elif any(keyword in text for keyword in self.relevant_categories['earnings']):
            return 'earnings'
        elif any(keyword in text for keyword in self.relevant_categories['politics']):
            return 'politics'
        elif any(keyword in text for keyword in self.relevant_categories['crypto']):
            return 'crypto'
        elif any(keyword in text for keyword in self.relevant_categories['tech']):
            return 'tech'
        else:
            return 'other'
    
    def _determine_impact_level(self, question: str, volume: float, probability: float) -> str:
        """Determine the potential market impact level."""
        text = question.lower()
        
        # High impact indicators
        high_impact_keywords = [
            'fed', 'federal reserve', 'interest rate', 'inflation', 'gdp',
            'unemployment', 'election', 'president', 'congress', 'war',
            'recession', 'crisis', 'apple', 'microsoft', 'google', 'tesla'
        ]
        
        # Medium impact indicators
        medium_impact_keywords = [
            'earnings', 'revenue', 'profit', 'guidance', 'sec', 'regulation',
            'policy', 'trade', 'tariff', 'bitcoin', 'ethereum'
        ]
        
        # Check keywords
        has_high_impact = any(keyword in text for keyword in high_impact_keywords)
        has_medium_impact = any(keyword in text for keyword in medium_impact_keywords)
        
        # Consider volume and probability
        high_volume = volume > 1000000  # $1M+ volume
        very_high_probability = probability > 0.9
        
        if has_high_impact and (high_volume or very_high_probability):
            return 'HIGH'
        elif has_high_impact or (has_medium_impact and high_volume):
            return 'MEDIUM'
        else:
            return 'LOW'
    
    async def get_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific market."""
        try:
            if not self.session:
                async with self:
                    return await self._fetch_market_details(market_id)
            else:
                return await self._fetch_market_details(market_id)
                
        except Exception as e:
            logger.error(f"Error fetching market details for {market_id}: {e}")
            return None
    
    async def _fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed market information."""
        try:
            url = f"{self.base_url}/markets/{market_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Market details API returned status {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching market details: {e}")
            return None

# Utility function for easy usage
async def get_high_impact_events(min_probability: float = 0.8, days_ahead: int = 7) -> List[PredictionMarket]:
    """Convenience function to get high-impact prediction market events."""
    async with PolymarketService() as service:
        return await service.get_high_probability_events(min_probability, days_ahead)
