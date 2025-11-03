#!/usr/bin/env python3
"""
Feature Extraction Script
Extracts technical indicators and features from historical data for ML training.
"""

import asyncio
import logging
import sys
import pandas as pd
import numpy as np
import talib
from datetime import datetime
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('feature_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract technical indicators and features for ML training."""
    
    def __init__(self, lookback_days=10):
        self.lookback_days = lookback_days
        
    def extract_technical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract technical indicators from OHLCV data."""
        features = pd.DataFrame(index=data.index)
        
        # Price features
        features['close'] = data['Close']
        features['open'] = data['Open']
        features['high'] = data['High']
        features['low'] = data['Low']
        features['volume'] = data['Volume']
        
        # Price ratios
        features['high_low_ratio'] = data['High'] / data['Low']
        features['close_open_ratio'] = data['Close'] / data['Open']
        
        # Moving averages
        features['sma_5'] = talib.SMA(data['Close'], timeperiod=5)
        features['sma_10'] = talib.SMA(data['Close'], timeperiod=10)
        features['sma_20'] = talib.SMA(data['Close'], timeperiod=20)
        
        # Price relative to moving averages
        features['close_sma5_ratio'] = data['Close'] / features['sma_5']
        features['close_sma10_ratio'] = data['Close'] / features['sma_10']
        features['close_sma20_ratio'] = data['Close'] / features['sma_20']
        
        # RSI
        features['rsi_14'] = talib.RSI(data['Close'], timeperiod=14)
        features['rsi_7'] = talib.RSI(data['Close'], timeperiod=7)
        
        # MACD
        macd, macd_signal, macd_hist = talib.MACD(data['Close'])
        features['macd'] = macd
        features['macd_signal'] = macd_signal
        features['macd_histogram'] = macd_hist
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(data['Close'])
        features['bb_upper'] = bb_upper
        features['bb_middle'] = bb_middle
        features['bb_lower'] = bb_lower
        features['bb_position'] = (data['Close'] - bb_lower) / (bb_upper - bb_lower)
        
        # Volume indicators
        features['volume_sma_10'] = talib.SMA(data['Volume'], timeperiod=10)
        features['volume_ratio'] = data['Volume'] / features['volume_sma_10']
        
        # Volatility
        features['atr_14'] = talib.ATR(data['High'], data['Low'], data['Close'], timeperiod=14)
        features['volatility_10'] = data['Close'].rolling(10).std()
        
        # Price momentum
        features['momentum_5'] = talib.MOM(data['Close'], timeperiod=5)
        features['momentum_10'] = talib.MOM(data['Close'], timeperiod=10)
        features['roc_5'] = talib.ROC(data['Close'], timeperiod=5)
        features['roc_10'] = talib.ROC(data['Close'], timeperiod=10)
        
        # Stochastic
        stoch_k, stoch_d = talib.STOCH(data['High'], data['Low'], data['Close'])
        features['stoch_k'] = stoch_k
        features['stoch_d'] = stoch_d
        
        # Williams %R
        features['williams_r'] = talib.WILLR(data['High'], data['Low'], data['Close'])
        
        # Commodity Channel Index
        features['cci'] = talib.CCI(data['High'], data['Low'], data['Close'])
        
        return features
    
    def extract_pattern_features(self, data: pd.DataFrame, event_date: pd.Timestamp) -> dict:
        """Extract features for a specific event date."""
        # Get data up to event date
        event_idx = data.index.get_loc(event_date)
        
        if event_idx < self.lookback_days:
            return None  # Not enough historical data
        
        # Get lookback window
        start_idx = event_idx - self.lookback_days
        window_data = data.iloc[start_idx:event_idx + 1]
        
        # Extract technical features
        tech_features = self.extract_technical_features(window_data)
        
        # Get the last row (event date features)
        event_features = tech_features.iloc[-1].to_dict()
        
        # Add trend features (comparing current to lookback period)
        lookback_close = window_data['Close'].iloc[0]
        current_close = window_data['Close'].iloc[-1]
        
        event_features['price_trend_pct'] = ((current_close - lookback_close) / lookback_close) * 100
        event_features['volume_trend'] = window_data['Volume'].iloc[-1] / window_data['Volume'].iloc[0]
        
        # Add recent volatility
        event_features['recent_volatility'] = window_data['Close'].pct_change().std() * 100
        
        # Add gap features
        if len(window_data) > 1:
            prev_close = window_data['Close'].iloc[-2]
            current_open = window_data['Open'].iloc[-1]
            event_features['gap_pct'] = ((current_open - prev_close) / prev_close) * 100
        else:
            event_features['gap_pct'] = 0
        
        return event_features


async def main():
    """Run feature extraction on detected events."""
    logger.info("🎯 BullsBears.xyz - Feature Extraction")
    logger.info("=" * 60)
    
    try:
        # Check if required files exist
        data_file = Path("data/backtest/nasdaq_6mo_full.pkl")
        moon_events_file = Path("data/backtest/moon_events_full.csv")
        rug_events_file = Path("data/backtest/rug_events_full.csv")
        
        if not data_file.exists():
            logger.error(f"❌ Data file not found: {data_file}")
            return False
        
        if not moon_events_file.exists() or not rug_events_file.exists():
            logger.error("❌ Event files not found. Please run move detection first.")
            return False
        
        # Load data and events
        logger.info("📊 Loading historical data and events...")
        data = pd.read_pickle(data_file)
        moon_events = pd.read_csv(moon_events_file)
        rug_events = pd.read_csv(rug_events_file)
        
        logger.info(f"✅ Loaded {len(moon_events)} moon events and {len(rug_events)} rug events")
        
        # Initialize feature extractor
        extractor = FeatureExtractor(lookback_days=10)
        
        # Extract features for moon events
        logger.info("🌙 Extracting features for moon events...")
        moon_features = []
        
        for _, event in moon_events.iterrows():
            ticker = event['ticker']
            event_date = pd.to_datetime(event['start_date']).tz_localize('UTC')

            if ticker in data.columns.get_level_values(0):
                ticker_data = data[ticker].dropna()
                features = extractor.extract_pattern_features(ticker_data, event_date)
                
                if features:
                    features['ticker'] = ticker
                    features['event_type'] = 'moon'
                    features['target_return'] = event['return_pct']
                    features['event_date'] = event_date
                    moon_features.append(features)
        
        # Extract features for rug events
        logger.info("💥 Extracting features for rug events...")
        rug_features = []
        
        for _, event in rug_events.iterrows():
            ticker = event['ticker']
            event_date = pd.to_datetime(event['start_date']).tz_localize('UTC')

            if ticker in data.columns.get_level_values(0):
                ticker_data = data[ticker].dropna()
                features = extractor.extract_pattern_features(ticker_data, event_date)
                
                if features:
                    features['ticker'] = ticker
                    features['event_type'] = 'rug'
                    features['target_return'] = event['return_pct']
                    features['event_date'] = event_date
                    rug_features.append(features)
        
        # Combine and save features
        all_features = moon_features + rug_features
        
        if all_features:
            features_df = pd.DataFrame(all_features)
            
            # Save features
            features_file = Path("data/backtest/ml_features.csv")
            features_df.to_csv(features_file, index=False)
            
            logger.info(f"💾 Saved {len(all_features)} feature vectors to {features_file}")
            logger.info(f"📊 Feature columns: {len(features_df.columns)}")
            logger.info(f"🌙 Moon events with features: {len(moon_features)}")
            logger.info(f"💥 Rug events with features: {len(rug_features)}")
            
            # Show feature summary
            logger.info("📈 Feature extraction completed successfully!")
            return True
        else:
            logger.error("❌ No features extracted")
            return False
        
    except Exception as e:
        logger.error(f"💥 Feature extraction failed: {e}")
        logger.exception("Full error traceback:")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logger.info("🚀 Ready for next phase: ML model training!")
        sys.exit(0)
    else:
        logger.error("💥 Feature extraction failed. Check logs for details.")
        sys.exit(1)
