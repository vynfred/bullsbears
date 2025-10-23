"""
Unusual volume detection service for identifying abnormal trading activity.
Tracks options flow, dark pool activity, and block trades.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VolumeAlert:
    """Data class for volume alerts."""
    symbol: str
    alert_type: str  # OPTIONS_FLOW, DARK_POOL, BLOCK_TRADE, UNUSUAL_VOLUME
    timestamp: datetime
    volume: float
    avg_volume: float
    volume_ratio: float
    price: float
    description: str
    significance: str  # HIGH, MEDIUM, LOW

@dataclass
class OptionsFlow:
    """Data class for options flow data."""
    symbol: str
    option_type: str  # CALL or PUT
    strike: float
    expiration: str
    volume: int
    open_interest: int
    premium: float
    unusual_activity: bool

class VolumeAnalyzer:
    """Service for analyzing unusual volume and options flow."""
    
    def __init__(self):
        self.unusual_threshold = 5.0  # 5x average volume
        self.block_trade_threshold = 10000  # Minimum shares for block trade
        
    async def analyze_unusual_volume(self, symbol: str, 
                                   lookback_days: int = 20) -> Dict[str, Any]:
        """
        Analyze unusual volume activity for a symbol.
        
        Args:
            symbol: Stock symbol to analyze
            lookback_days: Days to look back for average calculation
            
        Returns:
            Dictionary with volume analysis results
        """
        try:
            # Get historical data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{lookback_days + 5}d")
            
            if hist.empty:
                return {}
            
            # Calculate volume metrics
            volume_analysis = await self._analyze_stock_volume(hist, symbol)
            
            # Get options volume (simplified - would need real options data)
            options_analysis = await self._analyze_options_volume(symbol, hist)
            
            # Detect dark pool activity (estimated)
            dark_pool_analysis = await self._estimate_dark_pool_activity(hist, symbol)
            
            # Detect block trades
            block_trades = await self._detect_block_trades(hist, symbol)
            
            # Generate alerts
            alerts = self._generate_volume_alerts(
                symbol, volume_analysis, options_analysis, 
                dark_pool_analysis, block_trades
            )
            
            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'stock_volume': volume_analysis,
                'options_volume': options_analysis,
                'dark_pool': dark_pool_analysis,
                'block_trades': block_trades,
                'alerts': [alert.__dict__ for alert in alerts],
                'summary': self._generate_volume_summary(volume_analysis, options_analysis, alerts)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing volume for {symbol}: {e}")
            return {}
    
    async def _analyze_stock_volume(self, hist: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Analyze stock volume patterns."""
        
        if len(hist) < 20:
            return {}
        
        current_volume = hist['Volume'].iloc[-1]
        avg_volume_20d = hist['Volume'].iloc[-20:-1].mean()
        avg_volume_5d = hist['Volume'].iloc[-5:-1].mean()
        
        volume_ratio = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
        volume_trend = avg_volume_5d / avg_volume_20d if avg_volume_20d > 0 else 1
        
        # Calculate volume percentiles
        volume_percentile = (hist['Volume'].iloc[-1] > hist['Volume'].iloc[:-1]).sum() / len(hist['Volume'].iloc[:-1]) * 100
        
        # Detect volume spikes
        volume_spikes = []
        for i in range(len(hist) - 5, len(hist)):
            if i > 0:
                daily_ratio = hist['Volume'].iloc[i] / avg_volume_20d
                if daily_ratio >= self.unusual_threshold:
                    volume_spikes.append({
                        'date': hist.index[i].strftime('%Y-%m-%d'),
                        'volume': hist['Volume'].iloc[i],
                        'ratio': daily_ratio,
                        'price': hist['Close'].iloc[i]
                    })
        
        return {
            'current_volume': current_volume,
            'avg_volume_20d': avg_volume_20d,
            'avg_volume_5d': avg_volume_5d,
            'volume_ratio': volume_ratio,
            'volume_trend': volume_trend,
            'volume_percentile': volume_percentile,
            'unusual_activity': volume_ratio >= self.unusual_threshold,
            'volume_spikes': volume_spikes
        }
    
    async def _analyze_options_volume(self, symbol: str, hist: pd.DataFrame) -> Dict[str, Any]:
        """Analyze options volume (simplified estimation)."""
        
        try:
            # This is a simplified estimation - in production, use real options data
            current_volume = hist['Volume'].iloc[-1]
            avg_volume = hist['Volume'].iloc[-20:-1].mean()
            
            # Estimate options volume based on stock volume and volatility
            volatility = hist['Close'].pct_change().std() * np.sqrt(252)
            
            # Popular options stocks typically have higher options/stock volume ratios
            popular_options_stocks = {
                'AAPL', 'TSLA', 'SPY', 'QQQ', 'AMZN', 'MSFT', 'NVDA', 'META'
            }
            
            base_ratio = 0.3 if symbol in popular_options_stocks else 0.1
            volatility_multiplier = min(volatility * 2, 2.0)  # Cap at 2x
            
            estimated_options_volume = current_volume * base_ratio * volatility_multiplier
            estimated_avg_options_volume = avg_volume * base_ratio
            
            options_volume_ratio = estimated_options_volume / estimated_avg_options_volume if estimated_avg_options_volume > 0 else 1
            
            # Estimate call/put ratio (simplified)
            price_change = (hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]
            call_put_ratio = 1.5 if price_change > 0.02 else 0.7 if price_change < -0.02 else 1.0
            
            return {
                'estimated_options_volume': estimated_options_volume,
                'estimated_avg_options_volume': estimated_avg_options_volume,
                'options_volume_ratio': options_volume_ratio,
                'call_put_ratio': call_put_ratio,
                'unusual_options_activity': options_volume_ratio >= 3.0,
                'high_volatility': volatility > 0.3
            }
            
        except Exception as e:
            logger.warning(f"Error analyzing options volume: {e}")
            return {}
    
    async def _estimate_dark_pool_activity(self, hist: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Estimate dark pool activity based on price/volume patterns."""
        
        try:
            # Look for signs of dark pool activity:
            # 1. Large volume with minimal price movement
            # 2. Volume spikes without corresponding price spikes
            
            recent_data = hist.tail(5)
            
            dark_pool_signals = []
            for i in range(len(recent_data)):
                volume = recent_data['Volume'].iloc[i]
                price_change = abs(recent_data['Close'].iloc[i] - recent_data['Open'].iloc[i]) / recent_data['Open'].iloc[i]
                
                # High volume, low price movement could indicate dark pool
                if volume > hist['Volume'].mean() * 2 and price_change < 0.01:
                    dark_pool_signals.append({
                        'date': recent_data.index[i].strftime('%Y-%m-%d'),
                        'volume': volume,
                        'price_change': price_change,
                        'likelihood': 'HIGH' if volume > hist['Volume'].mean() * 3 else 'MEDIUM'
                    })
            
            # Calculate overall dark pool probability
            avg_volume = hist['Volume'].mean()
            recent_avg_volume = recent_data['Volume'].mean()
            recent_avg_price_change = abs(recent_data['Close'] - recent_data['Open']).mean() / recent_data['Open'].mean()
            
            dark_pool_probability = 0.0
            if recent_avg_volume > avg_volume * 1.5 and recent_avg_price_change < 0.015:
                dark_pool_probability = min((recent_avg_volume / avg_volume - 1) * 0.3, 0.8)
            
            return {
                'dark_pool_signals': dark_pool_signals,
                'dark_pool_probability': dark_pool_probability,
                'unusual_activity': len(dark_pool_signals) > 0,
                'recent_volume_ratio': recent_avg_volume / avg_volume if avg_volume > 0 else 1
            }
            
        except Exception as e:
            logger.warning(f"Error estimating dark pool activity: {e}")
            return {}
    
    async def _detect_block_trades(self, hist: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
        """Detect potential block trades."""
        
        block_trades = []
        
        try:
            # Look for volume spikes that could indicate block trades
            avg_volume = hist['Volume'].mean()
            
            for i in range(len(hist) - 5, len(hist)):
                volume = hist['Volume'].iloc[i]
                
                # Potential block trade: volume > 3x average and > minimum threshold
                if volume > avg_volume * 3 and volume > self.block_trade_threshold:
                    price = hist['Close'].iloc[i]
                    price_impact = abs(hist['Close'].iloc[i] - hist['Open'].iloc[i]) / hist['Open'].iloc[i]
                    
                    block_trades.append({
                        'date': hist.index[i].strftime('%Y-%m-%d'),
                        'volume': volume,
                        'price': price,
                        'price_impact': price_impact,
                        'volume_ratio': volume / avg_volume,
                        'estimated_value': volume * price,
                        'significance': 'HIGH' if volume > avg_volume * 5 else 'MEDIUM'
                    })
            
        except Exception as e:
            logger.warning(f"Error detecting block trades: {e}")
        
        return block_trades
    
    def _generate_volume_alerts(self, symbol: str, stock_volume: Dict, 
                              options_volume: Dict, dark_pool: Dict, 
                              block_trades: List[Dict]) -> List[VolumeAlert]:
        """Generate volume alerts based on analysis."""
        
        alerts = []
        
        # Stock volume alerts
        if stock_volume.get('unusual_activity', False):
            alerts.append(VolumeAlert(
                symbol=symbol,
                alert_type='UNUSUAL_VOLUME',
                timestamp=datetime.now(),
                volume=stock_volume.get('current_volume', 0),
                avg_volume=stock_volume.get('avg_volume_20d', 0),
                volume_ratio=stock_volume.get('volume_ratio', 0),
                price=0,  # Would need current price
                description=f"Volume {stock_volume.get('volume_ratio', 0):.1f}x above average",
                significance='HIGH' if stock_volume.get('volume_ratio', 0) > 10 else 'MEDIUM'
            ))
        
        # Options volume alerts
        if options_volume.get('unusual_options_activity', False):
            alerts.append(VolumeAlert(
                symbol=symbol,
                alert_type='OPTIONS_FLOW',
                timestamp=datetime.now(),
                volume=options_volume.get('estimated_options_volume', 0),
                avg_volume=options_volume.get('estimated_avg_options_volume', 0),
                volume_ratio=options_volume.get('options_volume_ratio', 0),
                price=0,
                description=f"Options volume {options_volume.get('options_volume_ratio', 0):.1f}x above average",
                significance='HIGH' if options_volume.get('options_volume_ratio', 0) > 5 else 'MEDIUM'
            ))
        
        # Dark pool alerts
        if dark_pool.get('unusual_activity', False):
            alerts.append(VolumeAlert(
                symbol=symbol,
                alert_type='DARK_POOL',
                timestamp=datetime.now(),
                volume=0,
                avg_volume=0,
                volume_ratio=dark_pool.get('recent_volume_ratio', 0),
                price=0,
                description=f"Potential dark pool activity detected",
                significance='MEDIUM'
            ))
        
        # Block trade alerts
        for trade in block_trades:
            if trade.get('significance') == 'HIGH':
                alerts.append(VolumeAlert(
                    symbol=symbol,
                    alert_type='BLOCK_TRADE',
                    timestamp=datetime.now(),
                    volume=trade.get('volume', 0),
                    avg_volume=0,
                    volume_ratio=trade.get('volume_ratio', 0),
                    price=trade.get('price', 0),
                    description=f"Large block trade: {trade.get('volume', 0):,.0f} shares",
                    significance=trade.get('significance', 'MEDIUM')
                ))
        
        return alerts
    
    def _generate_volume_summary(self, stock_volume: Dict, options_volume: Dict, 
                               alerts: List[VolumeAlert]) -> str:
        """Generate a summary of volume analysis."""
        
        summary_parts = []
        
        # Stock volume summary
        if stock_volume.get('unusual_activity', False):
            ratio = stock_volume.get('volume_ratio', 0)
            summary_parts.append(f"Stock volume {ratio:.1f}x above average")
        
        # Options volume summary
        if options_volume.get('unusual_options_activity', False):
            ratio = options_volume.get('options_volume_ratio', 0)
            summary_parts.append(f"Options activity {ratio:.1f}x above normal")
        
        # Alert summary
        high_alerts = [a for a in alerts if a.significance == 'HIGH']
        if high_alerts:
            summary_parts.append(f"{len(high_alerts)} high-significance alerts")
        
        if not summary_parts:
            return "Normal volume patterns detected"
        
        return "; ".join(summary_parts)

# Utility function for easy usage
async def analyze_volume(symbol: str, lookback_days: int = 20) -> Dict[str, Any]:
    """Convenience function to analyze volume for a symbol."""
    analyzer = VolumeAnalyzer()
    return await analyzer.analyze_unusual_volume(symbol, lookback_days)
