"""
Insider & Political Trading Analyzer
Analyzes insider trading, political trades, and institutional flows
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TradeType(Enum):
    """Types of insider trades"""
    BUY = "BUY"
    SELL = "SELL"


class TraderType(Enum):
    """Types of traders"""
    INSIDER = "INSIDER"           # Company insiders (CEO, CFO, etc.)
    POLITICAL = "POLITICAL"       # Congress members, senators
    INSTITUTIONAL = "INSTITUTIONAL"  # Hedge funds, mutual funds


@dataclass
class InsiderTrade:
    """Individual insider trade record"""
    symbol: str
    trader_name: str
    trader_type: TraderType
    trade_type: TradeType
    shares: int
    price: float
    value: float
    date: datetime
    position_change_percent: float  # % change in their holdings


@dataclass
class InsiderAnalysis:
    """Analysis of insider trading activity"""
    insider_sentiment_score: float      # 0-100 (bullish insider activity)
    political_sentiment_score: float    # 0-100 (political confidence)
    institutional_flow_score: float     # 0-100 (institutional buying)
    recent_insider_trades: List[InsiderTrade]
    key_insights: List[str]
    confidence_boost: float             # Additional confidence from insider activity


class InsiderTradingAnalyzer:
    """
    Analyzes insider trading, political trades, and institutional flows
    """
    
    def __init__(self):
        # Scoring weights
        self.insider_weights = {
            'CEO': 3.0,
            'CFO': 2.5,
            'President': 2.0,
            'Director': 1.5,
            'Officer': 1.0
        }
        
        self.political_weights = {
            'Senator': 2.0,
            'Representative': 1.5,
            'Committee Chair': 2.5
        }
        
        # Time decay factors
        self.time_decay_days = 90  # Trades older than 90 days have less impact
        
    async def analyze_insider_activity(self, symbol: str, lookback_days: int = 90) -> InsiderAnalysis:
        """
        Analyze insider trading activity for a symbol
        
        Args:
            symbol: Stock symbol
            lookback_days: How far back to look for trades
            
        Returns:
            InsiderAnalysis with sentiment scores and insights
        """
        try:
            # Get recent insider trades
            insider_trades = await self._get_insider_trades(symbol, lookback_days)
            political_trades = await self._get_political_trades(symbol, lookback_days)
            institutional_flows = await self._get_institutional_flows(symbol, lookback_days)
            
            # Calculate sentiment scores
            insider_sentiment = self._calculate_insider_sentiment(insider_trades)
            political_sentiment = self._calculate_political_sentiment(political_trades)
            institutional_flow = self._calculate_institutional_flow(institutional_flows)
            
            # Generate insights
            insights = self._generate_insights(insider_trades, political_trades, institutional_flows)
            
            # Calculate confidence boost
            confidence_boost = self._calculate_confidence_boost(
                insider_sentiment, political_sentiment, institutional_flow
            )
            
            # Combine all trades for recent activity
            all_trades = insider_trades + political_trades
            recent_trades = sorted(all_trades, key=lambda x: x.date, reverse=True)[:10]
            
            return InsiderAnalysis(
                insider_sentiment_score=insider_sentiment,
                political_sentiment_score=political_sentiment,
                institutional_flow_score=institutional_flow,
                recent_insider_trades=recent_trades,
                key_insights=insights,
                confidence_boost=confidence_boost
            )
            
        except Exception as e:
            logger.error(f"Error analyzing insider activity for {symbol}: {e}")
            return self._get_default_analysis()
    
    async def _get_insider_trades(self, symbol: str, days: int) -> List[InsiderTrade]:
        """
        Get insider trades from SEC Form 4 filings
        
        Data sources:
        - SEC EDGAR API (free)
        - OpenInsider API
        - Fintel API
        """
        try:
            # Mock data - replace with actual API calls
            cutoff_date = datetime.now() - timedelta(days=days)
            
            mock_trades = [
                InsiderTrade(
                    symbol=symbol,
                    trader_name="John Smith",
                    trader_type=TraderType.INSIDER,
                    trade_type=TradeType.BUY,
                    shares=10000,
                    price=150.00,
                    value=1500000,
                    date=datetime.now() - timedelta(days=5),
                    position_change_percent=15.2
                ),
                InsiderTrade(
                    symbol=symbol,
                    trader_name="Jane Doe",
                    trader_type=TraderType.INSIDER,
                    trade_type=TradeType.SELL,
                    shares=5000,
                    price=148.50,
                    value=742500,
                    date=datetime.now() - timedelta(days=12),
                    position_change_percent=-8.3
                )
            ]
            
            return [trade for trade in mock_trades if trade.date >= cutoff_date]
            
        except Exception as e:
            logger.error(f"Error fetching insider trades for {symbol}: {e}")
            return []
    
    async def _get_political_trades(self, symbol: str, days: int) -> List[InsiderTrade]:
        """
        Get political trades from Congress/Senate disclosures
        
        Data sources:
        - Capitol Trades API
        - Senate Stock Watcher
        - Congress Trading API
        - House/Senate disclosure reports
        """
        try:
            # Mock data - replace with actual API calls
            cutoff_date = datetime.now() - timedelta(days=days)
            
            mock_trades = [
                InsiderTrade(
                    symbol=symbol,
                    trader_name="Senator Johnson",
                    trader_type=TraderType.POLITICAL,
                    trade_type=TradeType.BUY,
                    shares=2000,
                    price=145.00,
                    value=290000,
                    date=datetime.now() - timedelta(days=47),  # 45+ day delay
                    position_change_percent=25.0
                )
            ]
            
            return [trade for trade in mock_trades if trade.date >= cutoff_date]
            
        except Exception as e:
            logger.error(f"Error fetching political trades for {symbol}: {e}")
            return []
    
    async def _get_institutional_flows(self, symbol: str, days: int) -> List[InsiderTrade]:
        """
        Get institutional trading flows from 13F filings
        
        Data sources:
        - SEC 13F filings
        - WhaleWisdom API
        - Institutional holdings data
        """
        try:
            # Mock data - replace with actual API calls
            cutoff_date = datetime.now() - timedelta(days=days)
            
            mock_flows = [
                InsiderTrade(
                    symbol=symbol,
                    trader_name="Berkshire Hathaway",
                    trader_type=TraderType.INSTITUTIONAL,
                    trade_type=TradeType.BUY,
                    shares=1000000,
                    price=147.50,
                    value=147500000,
                    date=datetime.now() - timedelta(days=30),
                    position_change_percent=12.5
                )
            ]
            
            return [flow for flow in mock_flows if flow.date >= cutoff_date]
            
        except Exception as e:
            logger.error(f"Error fetching institutional flows for {symbol}: {e}")
            return []
    
    def _calculate_insider_sentiment(self, trades: List[InsiderTrade]) -> float:
        """Calculate insider sentiment score from trades"""
        if not trades:
            return 50.0  # Neutral
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for trade in trades:
            # Get position weight based on trader title
            position_weight = self.insider_weights.get('Director', 1.0)  # Default weight
            
            # Time decay
            days_ago = (datetime.now() - trade.date).days
            time_weight = max(0.1, 1.0 - (days_ago / self.time_decay_days))
            
            # Trade direction score
            trade_score = 100 if trade.trade_type == TradeType.BUY else 0
            
            # Size weight (larger trades matter more)
            size_weight = min(2.0, trade.value / 1000000)  # Cap at 2x for $1M+ trades
            
            # Combined weight
            combined_weight = position_weight * time_weight * size_weight
            
            total_weighted_score += trade_score * combined_weight
            total_weight += combined_weight
        
        if total_weight == 0:
            return 50.0
        
        return total_weighted_score / total_weight
    
    def _calculate_political_sentiment(self, trades: List[InsiderTrade]) -> float:
        """Calculate political sentiment score"""
        if not trades:
            return 50.0  # Neutral
        
        # Similar to insider sentiment but with political weights
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for trade in trades:
            position_weight = self.political_weights.get('Representative', 1.5)
            
            # Political trades have 45+ day delay, so less time decay
            days_ago = (datetime.now() - trade.date).days
            time_weight = max(0.3, 1.0 - (days_ago / 180))  # 6 month decay
            
            trade_score = 100 if trade.trade_type == TradeType.BUY else 0
            size_weight = min(1.5, trade.value / 500000)  # Smaller trades for politicians
            
            combined_weight = position_weight * time_weight * size_weight
            
            total_weighted_score += trade_score * combined_weight
            total_weight += combined_weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 50.0
    
    def _calculate_institutional_flow(self, flows: List[InsiderTrade]) -> float:
        """Calculate institutional flow score"""
        if not flows:
            return 50.0
        
        buy_value = sum(flow.value for flow in flows if flow.trade_type == TradeType.BUY)
        sell_value = sum(flow.value for flow in flows if flow.trade_type == TradeType.SELL)
        
        if buy_value + sell_value == 0:
            return 50.0
        
        # Net flow percentage
        net_flow = (buy_value - sell_value) / (buy_value + sell_value)
        
        # Convert to 0-100 score
        return 50 + (net_flow * 50)
    
    def _generate_insights(self, insider_trades: List[InsiderTrade], 
                          political_trades: List[InsiderTrade], 
                          institutional_flows: List[InsiderTrade]) -> List[str]:
        """Generate key insights from trading activity"""
        insights = []
        
        # Insider activity insights
        if insider_trades:
            recent_insider_buys = [t for t in insider_trades if t.trade_type == TradeType.BUY]
            if len(recent_insider_buys) >= 2:
                insights.append(f"• {len(recent_insider_buys)} insider purchases in last 90 days")
        
        # Political activity insights
        if political_trades:
            recent_political = [t for t in political_trades if 
                              (datetime.now() - t.date).days <= 60]
            if recent_political:
                insights.append("• Recent political trading activity detected (45+ day delay)")
        
        # Institutional flow insights
        if institutional_flows:
            big_flows = [f for f in institutional_flows if f.value > 50000000]  # $50M+
            if big_flows:
                insights.append(f"• {len(big_flows)} major institutional position changes")
        
        # Default insight
        if not insights:
            insights.append("• No significant insider or institutional activity detected")
        
        return insights
    
    def _calculate_confidence_boost(self, insider_score: float, political_score: float, 
                                  institutional_score: float) -> float:
        """Calculate confidence boost from insider activity"""
        
        # Weighted average of all scores
        weighted_score = (
            insider_score * 0.5 +           # Insider trades most important
            institutional_score * 0.3 +     # Institutional flows second
            political_score * 0.2           # Political trades least (45 day delay)
        )
        
        # Convert to confidence boost (-10% to +15%)
        if weighted_score > 70:
            return min(15.0, (weighted_score - 50) * 0.3)
        elif weighted_score < 30:
            return max(-10.0, (weighted_score - 50) * 0.2)
        else:
            return 0.0  # Neutral
    
    def _get_default_analysis(self) -> InsiderAnalysis:
        """Default analysis when data unavailable"""
        return InsiderAnalysis(
            insider_sentiment_score=50.0,
            political_sentiment_score=50.0,
            institutional_flow_score=50.0,
            recent_insider_trades=[],
            key_insights=["• Insider trading data temporarily unavailable"],
            confidence_boost=0.0
        )


# Global instance
_insider_analyzer = None

async def get_insider_trading_analyzer() -> InsiderTradingAnalyzer:
    """Get global insider trading analyzer instance"""
    global _insider_analyzer
    if _insider_analyzer is None:
        _insider_analyzer = InsiderTradingAnalyzer()
    return _insider_analyzer
