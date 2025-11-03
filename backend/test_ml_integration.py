#!/usr/bin/env python3
"""
Test ML Model Integration
Quick test to verify ML models are loaded and working with analyzers.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from app.services.model_loader import get_model_loader
from app.analyzers.moon_analyzer import MoonAnalyzer
from app.analyzers.rug_analyzer import RugAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_model_loader():
    """Test model loading functionality."""
    logger.info("🚀 Testing ML Model Loader...")
    
    try:
        # Get model loader
        loader = await get_model_loader()
        
        # Check model health
        health = loader.get_model_health()
        logger.info(f"📊 Model Health: {health}")
        
        # Test sample prediction with all 38 features
        sample_features = {
            # Basic OHLCV
            'close': 100.0, 'open': 99.0, 'high': 101.0, 'low': 98.0, 'volume': 1000000,
            # Price ratios
            'high_low_ratio': 1.03, 'close_open_ratio': 1.01,
            # Moving averages
            'sma_5': 99.5, 'sma_10': 99.0, 'sma_20': 98.5,
            # SMA ratios
            'close_sma5_ratio': 1.005, 'close_sma10_ratio': 1.01, 'close_sma20_ratio': 1.015,
            # RSI
            'rsi_14': 25.0, 'rsi_7': 20.0,  # Oversold
            # MACD
            'macd': 0.5, 'macd_signal': 0.2, 'macd_histogram': 0.3,
            # Bollinger Bands
            'bb_upper': 105.0, 'bb_middle': 100.0, 'bb_lower': 95.0, 'bb_position': 0.2,
            # Volume
            'volume_sma_10': 800000, 'volume_ratio': 1.25,  # Volume surge
            # Volatility and momentum
            'atr_14': 2.5, 'volatility_10': 0.025, 'momentum_5': 1.0, 'momentum_10': 2.0,
            # Rate of change
            'roc_5': 2.0, 'roc_10': 3.0,
            # Stochastic
            'stoch_k': 20.0, 'stoch_d': 25.0,  # Oversold
            # Other indicators
            'williams_r': -80.0, 'cci': -150.0,  # Oversold
            # Trend features
            'price_trend_pct': 1.5, 'volume_trend': 0.25, 'recent_volatility': 0.03, 'gap_pct': 0.5
        }
        
        # Test moon prediction
        moon_confidence, moon_details = await loader.predict_moon(sample_features)
        logger.info(f"🌙 Moon prediction: {moon_confidence:.1%} confidence")
        logger.info(f"   Details: {moon_details}")
        
        # Test rug prediction
        rug_confidence, rug_details = await loader.predict_rug(sample_features)
        logger.info(f"💥 Rug prediction: {rug_confidence:.1%} confidence")
        logger.info(f"   Details: {rug_details}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Model loader test failed: {e}")
        return False

async def test_ml_prediction_direct():
    """Test ML prediction directly without full analyzer pipeline."""
    logger.info("🔍 Testing Direct ML Prediction...")

    try:
        # Get model loader
        loader = await get_model_loader()

        # Test different scenarios
        scenarios = [
            {
                "name": "Oversold Moon Setup",
                "features": {
                    # Basic OHLCV
                    'close': 100.0, 'open': 99.0, 'high': 101.0, 'low': 98.0, 'volume': 1500000,
                    # Price ratios
                    'high_low_ratio': 1.03, 'close_open_ratio': 1.01,
                    # Moving averages
                    'sma_5': 99.5, 'sma_10': 99.0, 'sma_20': 98.5,
                    # SMA ratios
                    'close_sma5_ratio': 1.005, 'close_sma10_ratio': 1.01, 'close_sma20_ratio': 1.015,
                    # RSI - Oversold
                    'rsi_14': 25.0, 'rsi_7': 20.0,
                    # MACD - Bullish divergence
                    'macd': 0.5, 'macd_signal': 0.2, 'macd_histogram': 0.3,
                    # Bollinger Bands - Near lower band
                    'bb_upper': 105.0, 'bb_middle': 100.0, 'bb_lower': 95.0, 'bb_position': 0.2,
                    # Volume - Surge
                    'volume_sma_10': 800000, 'volume_ratio': 1.875,
                    # Volatility and momentum
                    'atr_14': 2.5, 'volatility_10': 0.025, 'momentum_5': 1.0, 'momentum_10': 2.0,
                    # Rate of change
                    'roc_5': 2.0, 'roc_10': 3.0,
                    # Stochastic - Oversold
                    'stoch_k': 20.0, 'stoch_d': 25.0,
                    # Other indicators
                    'williams_r': -80.0, 'cci': -150.0,
                    # Trend features
                    'price_trend_pct': 1.5, 'volume_trend': 0.25, 'recent_volatility': 0.03, 'gap_pct': 0.5
                }
            },
            {
                "name": "Overbought Rug Setup",
                "features": {
                    # Basic OHLCV
                    'close': 100.0, 'open': 101.0, 'high': 102.0, 'low': 99.5, 'volume': 2000000,
                    # Price ratios
                    'high_low_ratio': 1.025, 'close_open_ratio': 0.99,
                    # Moving averages
                    'sma_5': 100.5, 'sma_10': 101.0, 'sma_20': 101.5,
                    # SMA ratios
                    'close_sma5_ratio': 0.995, 'close_sma10_ratio': 0.99, 'close_sma20_ratio': 0.985,
                    # RSI - Overbought
                    'rsi_14': 75.0, 'rsi_7': 80.0,
                    # MACD - Bearish divergence
                    'macd': -0.3, 'macd_signal': 0.1, 'macd_histogram': -0.4,
                    # Bollinger Bands - Near upper band
                    'bb_upper': 105.0, 'bb_middle': 100.0, 'bb_lower': 95.0, 'bb_position': 0.8,
                    # Volume - High distribution
                    'volume_sma_10': 1200000, 'volume_ratio': 1.67,
                    # Volatility and momentum
                    'atr_14': 3.0, 'volatility_10': 0.035, 'momentum_5': -0.5, 'momentum_10': -1.0,
                    # Rate of change
                    'roc_5': -1.0, 'roc_10': -2.0,
                    # Stochastic - Overbought
                    'stoch_k': 80.0, 'stoch_d': 75.0,
                    # Other indicators
                    'williams_r': -20.0, 'cci': 150.0,
                    # Trend features
                    'price_trend_pct': -1.0, 'volume_trend': 0.67, 'recent_volatility': 0.04, 'gap_pct': -0.5
                }
            }
        ]

        for scenario in scenarios:
            logger.info(f"\n🎯 Testing {scenario['name']}...")

            # Test moon prediction
            moon_conf, moon_details = await loader.predict_moon(scenario['features'])
            logger.info(f"🌙 Moon: {moon_conf:.1%} confidence")
            if moon_conf >= 0.75:
                logger.info(f"   ✅ Above threshold - would generate alert")
            else:
                logger.info(f"   ⚠️  Below threshold - no alert")

            # Test rug prediction
            rug_conf, rug_details = await loader.predict_rug(scenario['features'])
            logger.info(f"💥 Rug: {rug_conf:.1%} confidence")
            if rug_conf >= 0.75:
                logger.info(f"   ✅ Above threshold - would generate alert")
            else:
                logger.info(f"   ⚠️  Below threshold - no alert")

        return True

    except Exception as e:
        logger.error(f"❌ Direct ML prediction test failed: {e}")
        return False

async def main():
    """Run all tests."""
    logger.info("🎯 Starting ML Integration Tests...")
    
    # Test 1: Model Loader
    loader_success = await test_model_loader()
    
    # Test 2: Direct ML Prediction
    prediction_success = await test_ml_prediction_direct()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("="*50)
    logger.info(f"🤖 Model Loader: {'✅ PASS' if loader_success else '❌ FAIL'}")
    logger.info(f"🔮 ML Predictions: {'✅ PASS' if prediction_success else '❌ FAIL'}")

    overall_success = loader_success and prediction_success
    logger.info(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        logger.info("🚀 ML integration is ready for production!")
    else:
        logger.info("⚠️  Please fix issues before proceeding.")
    
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
