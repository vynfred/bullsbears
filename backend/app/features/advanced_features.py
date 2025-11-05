#!/usr/bin/env python3
"""
Advanced Feature Engineering
Add sophisticated features like short interest, options flow, and market microstructure.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional
import aiohttp
import asyncio
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class AdvancedFeatureEngineer:
    """Advanced feature engineering for better moon/rug prediction."""

    def __init__(self):
        self.feature_cache = {}

        # Professional API keys
        self.databento_key = os.getenv('DATABENTO_API_KEY')
        self.fmp_key = os.getenv('FMP_API_KEY')
        self.alpaca_key = os.getenv('ALPACA_API_KEY')
        self.alpaca_secret = os.getenv('ALPACA_SECRET_KEY')

        # API endpoints
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"
        self.alpaca_base_url = "https://paper-api.alpaca.markets/v2"
    
    async def add_short_interest_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Add short interest features using professional APIs (Databento → FMP → Alpaca fallback).

        Features:
        - Short interest ratio
        - Short percent of float
        - Days to cover
        - Short squeeze potential score
        """
        try:
            logger.info(f"📊 Adding short interest features for {symbol}...")

            # Try FMP first (most reliable for short interest)
            short_data = None
            if self.fmp_key:
                short_data = await self._get_fmp_short_interest(symbol)

            # Fallback to Alpaca (limited data)
            if not short_data and self.alpaca_key:
                short_data = await self._get_alpaca_short_interest(symbol)

            if short_data:
                # Add features to dataframe
                for col, value in short_data.items():
                    df[col] = value

                logger.info(f"✅ Added short interest features: {short_data.get('short_percent_float', 0):.1f}% float shorted")
            else:
                # Fill with defaults if all APIs fail
                self._add_default_short_interest_features(df)
                logger.warning(f"⚠️  Short interest data unavailable for {symbol}, using defaults")

        except Exception as e:
            logger.error(f"❌ Short interest feature extraction failed for {symbol}: {e}")
            self._add_default_short_interest_features(df)

        return df

    async def _get_fmp_short_interest(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get short interest data from Financial Modeling Prep."""
        try:
            url = f"{self.fmp_base_url}/key-metrics/{symbol}?apikey={self.fmp_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            latest = data[0]  # Most recent data

                            short_ratio = latest.get('shortRatio', 0.0)
                            return {
                                'short_ratio': short_ratio,
                                'short_percent_float': short_ratio * 100,  # Approximate
                                'shares_short': 0.0,  # FMP doesn't provide exact shares
                                'shares_short_prior': 0.0,
                                'short_interest_change': 0.0,
                                'days_to_cover': short_ratio,
                                'squeeze_potential': 1.0 if short_ratio > 0.2 else 0.0
                            }
        except Exception as e:
            logger.warning(f"FMP short interest API failed for {symbol}: {e}")

        return None

    async def _get_alpaca_short_interest(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get short interest data from Alpaca (placeholder - limited availability)."""
        # Alpaca doesn't provide direct short interest data
        # This is a placeholder for future implementation
        return None

    def _add_default_short_interest_features(self, df: pd.DataFrame):
        """Add default short interest features when APIs fail."""
        for col in ['short_ratio', 'short_percent_float', 'shares_short', 'shares_short_prior',
                   'short_interest_change', 'days_to_cover', 'squeeze_potential']:
            df[col] = 0.0
    
    async def add_options_flow_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Add options flow features that can predict large moves.
        
        Features:
        - Put/call ratio
        - Options volume vs stock volume
        - Unusual options activity
        - Gamma exposure
        """
        try:
            logger.info(f"📈 Adding options flow features for {symbol}...")

            # Try professional APIs for options data
            options_data = None

            # Try FMP for options data
            if self.fmp_key:
                options_data = await self._get_fmp_options_data(symbol)

            # Fallback to Databento (if available)
            if not options_data and self.databento_key:
                options_data = await self._get_databento_options_data(symbol)

            if options_data:
                # Add features to dataframe
                for col, value in options_data.items():
                    df[col] = value

                logger.info(f"✅ Added options features: P/C ratio {options_data.get('put_call_ratio', 0):.2f}")
            else:
                # Fill with defaults if all APIs fail
                self._add_default_options_features(df)
                logger.warning(f"⚠️  Options data unavailable for {symbol}, using defaults")

        except Exception as e:
            logger.error(f"❌ Options flow features failed for {symbol}: {e}")
            self._add_default_options_features(df)
        
        return df

    async def _get_fmp_options_data(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get options data from Financial Modeling Prep."""
        try:
            # FMP has limited options data - mainly put/call ratios
            url = f"{self.fmp_base_url}/historical/put-call-ratio/{symbol}?apikey={self.fmp_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            latest = data[0]

                            return {
                                'put_call_ratio': latest.get('putCallRatio', 0.0),
                                'options_stock_volume_ratio': 0.1,  # Estimate
                                'unusual_call_activity': 0.0,
                                'unusual_put_activity': 0.0,
                                'gamma_exposure_proxy': 0.0
                            }
        except Exception as e:
            logger.warning(f"FMP options API failed for {symbol}: {e}")

        return None

    async def _get_databento_options_data(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get options data from Databento (placeholder)."""
        # Databento has professional options data but requires specific implementation
        # This is a placeholder for future implementation
        return None

    def _add_default_options_features(self, df: pd.DataFrame):
        """Add default options features when APIs fail."""
        for col in ['put_call_ratio', 'options_stock_volume_ratio', 'unusual_call_activity',
                   'unusual_put_activity', 'gamma_exposure_proxy']:
            df[col] = 0.0

    def add_market_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add market microstructure features.
        
        Features:
        - Bid-ask spread
        - Order flow imbalance
        - Price impact
        - Liquidity measures
        """
        try:
            logger.info("🔬 Adding market microstructure features...")
            
            if 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
                # Intraday spread proxy (high-low relative to close)
                df['intraday_spread'] = (df['high'] - df['low']) / df['close']
                
                # Price impact proxy (gap from previous close)
                df['price_impact'] = df['close'].pct_change().abs()
                
                # Liquidity proxy (volume per price movement)
                price_change = df['close'].pct_change().abs()
                df['liquidity_proxy'] = np.where(
                    price_change > 0,
                    df['volume'] / (price_change * df['close']),
                    df['volume']  # Default if no price change
                )
                
                # Order flow imbalance proxy (using OHLC)
                # Buying pressure: (Close - Low) / (High - Low)
                range_val = df['high'] - df['low']
                df['buying_pressure'] = np.where(
                    range_val > 0,
                    (df['close'] - df['low']) / range_val,
                    0.5  # Neutral if no range
                )
                
                # Selling pressure: (High - Close) / (High - Low)
                df['selling_pressure'] = np.where(
                    range_val > 0,
                    (df['high'] - df['close']) / range_val,
                    0.5  # Neutral if no range
                )
                
                # Net order flow
                df['net_order_flow'] = df['buying_pressure'] - df['selling_pressure']
                
                logger.info("✅ Added microstructure features")
            else:
                logger.warning("⚠️  Insufficient OHLC data for microstructure features")
                # Fill with defaults
                for col in ['intraday_spread', 'price_impact', 'liquidity_proxy', 
                           'buying_pressure', 'selling_pressure', 'net_order_flow']:
                    df[col] = 0.0
        
        except Exception as e:
            logger.error(f"❌ Microstructure features failed: {e}")
            # Fill with defaults
            for col in ['intraday_spread', 'price_impact', 'liquidity_proxy', 
                       'buying_pressure', 'selling_pressure', 'net_order_flow']:
                df[col] = 0.0
        
        return df
    
    def add_sentiment_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Add sentiment-based features.
        
        Features:
        - Social media mentions
        - News sentiment
        - Analyst upgrades/downgrades
        """
        try:
            logger.info(f"💭 Adding sentiment features for {symbol}...")
            
            # Placeholder for sentiment features (would integrate with APIs)
            # For now, create proxy features based on price action
            
            # Momentum-based sentiment proxy
            if 'close' in df.columns:
                returns_5d = df['close'].pct_change(5)
                returns_20d = df['close'].pct_change(20)
                
                # Positive momentum = bullish sentiment proxy
                df['momentum_sentiment'] = np.where(returns_5d > 0.05, 1.0, 
                                                   np.where(returns_5d < -0.05, -1.0, 0.0))
                
                # Trend strength
                df['trend_strength'] = abs(returns_20d)
                
                # Volatility-based fear/greed
                volatility = df['close'].pct_change().rolling(10).std()
                df['fear_greed_proxy'] = np.where(volatility > volatility.median(), -1.0, 1.0)
                
                logger.info("✅ Added sentiment proxy features")
            else:
                # Fill with defaults
                for col in ['momentum_sentiment', 'trend_strength', 'fear_greed_proxy']:
                    df[col] = 0.0
        
        except Exception as e:
            logger.error(f"❌ Sentiment features failed: {e}")
            # Fill with defaults
            for col in ['momentum_sentiment', 'trend_strength', 'fear_greed_proxy']:
                df[col] = 0.0

        return df

    async def add_economic_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Add economic and insider trading features.

        Features added:
        - insider_sentiment_score: Net insider buying/selling sentiment (0-1)
        - institutional_flow_score: Net institutional flow momentum (-1 to 1)
        - economic_headwind_tailwind: Macro economic conditions (-1 to 1)
        - event_catalyst_score: Proximity to economic events (0-1)
        - economic_confidence: Overall confidence in economic analysis (0-1)
        - risk_factor_count: Number of identified risk factors
        - bullish_catalyst_count: Number of bullish catalysts
        - bearish_catalyst_count: Number of bearish catalysts
        """
        try:
            logger.info(f"📊 Adding economic features for {symbol}...")

            # Import here to avoid circular imports
            from ..services.enhanced_economic_events_analyzer import EnhancedEconomicEventsAnalyzer

            # Get economic analysis
            economic_analyzer = EnhancedEconomicEventsAnalyzer()
            economic_features = await economic_analyzer.get_economic_features_for_ml(symbol)

            # Add features to dataframe
            for feature_name, feature_value in economic_features.items():
                df[feature_name] = feature_value

            logger.info(f"✅ Added {len(economic_features)} economic features for {symbol}")
            logger.info(f"   - Insider sentiment: {economic_features.get('economic_insider_sentiment', 0):.3f}")
            logger.info(f"   - Institutional flow: {economic_features.get('economic_institutional_flow', 0):.3f}")
            logger.info(f"   - Macro score: {economic_features.get('economic_macro_score', 0):.3f}")
            logger.info(f"   - Overall score: {economic_features.get('economic_overall_score', 0):.3f}")

        except Exception as e:
            logger.error(f"❌ Economic features failed for {symbol}: {e}")
            # Fill with defaults if economic analysis fails
            default_economic_features = {
                'economic_overall_score': 0.0,
                'economic_insider_sentiment': 0.0,
                'economic_institutional_flow': 0.0,
                'economic_macro_score': 0.0,
                'economic_confidence': 0.0,
                'economic_risk_factor_count': 0,
                'economic_bullish_catalyst_count': 0,
                'economic_bearish_catalyst_count': 0
            }

            for feature_name, feature_value in default_economic_features.items():
                df[feature_name] = feature_value

            logger.warning(f"⚠️  Economic features unavailable for {symbol}, using defaults")

        return df
    
    async def engineer_all_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Apply all advanced feature engineering."""
        logger.info(f"🚀 Engineering advanced features for {symbol}...")

        # Add all feature categories (async methods)
        df = await self.add_short_interest_features(df, symbol)
        df = await self.add_options_flow_features(df, symbol)
        df = self.add_market_microstructure_features(df)
        df = self.add_sentiment_features(df, symbol)
        df = await self.add_economic_features(df, symbol)

        # Clean up any NaNs or infinite values introduced by advanced features
        logger.info("🧹 Cleaning advanced features...")

        # Replace infinite values with NaN first
        df = df.replace([np.inf, -np.inf], np.nan)

        # Fill NaNs in advanced features with appropriate defaults
        advanced_feature_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in
                               ['short', 'options', 'put_call', 'volume_oi', 'gamma', 'spread', 'liquidity',
                                'buying_pressure', 'selling_pressure', 'momentum_sentiment', 'trend_strength', 'fear_greed',
                                'economic', 'insider', 'institutional', 'macro', 'catalyst', 'risk_factor'])]

        for col in advanced_feature_cols:
            if df[col].isna().any():
                # Use median for ratio/percentage features, 0 for binary features
                if 'ratio' in col.lower() or 'percent' in col.lower() or 'pressure' in col.lower():
                    fill_value = df[col].median() if not df[col].isna().all() else 0.0
                else:
                    fill_value = 0.0

                df[col] = df[col].fillna(fill_value)

        logger.info(f"✅ Advanced feature engineering complete: {len(df.columns)} total features")

        return df
