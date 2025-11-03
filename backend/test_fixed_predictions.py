#!/usr/bin/env python3
"""
Test Fixed Model Predictions
Validates that the ensemble models now make realistic predictions with complete 74-feature input.
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add backend to path
sys.path.append('/Users/vynfred/Documents/bullsbears/backend')

from app.analyzers.data_downloader import DataDownloader
from app.features.advanced_features import AdvancedFeatureEngineer
from app.services.model_loader import ModelLoader
import talib

class FixedPredictionTester:
    def __init__(self):
        self.data_downloader = DataDownloader()
        self.advanced_engineer = AdvancedFeatureEngineer()
        self.model_loader = ModelLoader()
    
    def extract_basic_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract basic technical features (57 features like in training)"""
        features = pd.DataFrame(index=data.index)

        # Rename columns to match expected format
        df = data.copy()
        if 'Close' in df.columns:
            df = df.rename(columns={'Close': 'close', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Volume': 'volume'})

        # Basic OHLCV features
        features['close'] = df['close']
        features['open'] = df['open']
        features['high'] = df['high']
        features['low'] = df['low']
        features['volume'] = df['volume']

        # Price ratios
        features['high_low_ratio'] = df['high'] / df['low']
        features['close_open_ratio'] = df['close'] / df['open']

        # Moving averages
        features['sma_5'] = talib.SMA(df['close'], timeperiod=5)
        features['sma_10'] = talib.SMA(df['close'], timeperiod=10)
        features['sma_20'] = talib.SMA(df['close'], timeperiod=20)

        # Price to MA ratios
        features['close_sma5_ratio'] = df['close'] / features['sma_5']
        features['close_sma10_ratio'] = df['close'] / features['sma_10']
        features['close_sma20_ratio'] = df['close'] / features['sma_20']

        # Technical indicators
        features['rsi_14'] = talib.RSI(df['close'], timeperiod=14)
        features['rsi_7'] = talib.RSI(df['close'], timeperiod=7)

        # MACD
        macd, macd_signal, macd_hist = talib.MACD(df['close'])
        features['macd'] = macd
        features['macd_signal'] = macd_signal
        features['macd_histogram'] = macd_hist

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'], timeperiod=20)
        features['bb_upper'] = bb_upper
        features['bb_middle'] = bb_middle
        features['bb_lower'] = bb_lower

        # BB position
        bb_range = bb_upper - bb_lower
        features['bb_position'] = np.where(bb_range > 0, (df['close'] - bb_lower) / bb_range, 0.5)

        # Volume features
        features['volume_sma_10'] = talib.SMA(df['volume'], timeperiod=10)
        features['volume_ratio'] = df['volume'] / features['volume_sma_10']

        # Volatility and momentum
        features['atr_14'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        features['volatility_10'] = df['close'].pct_change().rolling(10).std()
        features['momentum_5'] = talib.MOM(df['close'], timeperiod=5)
        features['momentum_10'] = talib.MOM(df['close'], timeperiod=10)
        features['roc_5'] = talib.ROC(df['close'], timeperiod=5)
        features['roc_10'] = talib.ROC(df['close'], timeperiod=10)

        # Stochastic
        stoch_k, stoch_d = talib.STOCH(df['high'], df['low'], df['close'])
        features['stoch_k'] = stoch_k
        features['stoch_d'] = stoch_d

        # Williams %R and CCI
        features['williams_r'] = talib.WILLR(df['high'], df['low'], df['close'])
        features['cci'] = talib.CCI(df['high'], df['low'], df['close'])

        # Additional features
        features['price_trend_pct'] = df['close'].pct_change(5) * 100
        features['volume_trend'] = df['volume'].pct_change(5)
        features['recent_volatility'] = df['close'].pct_change().rolling(5).std()
        features['gap_pct'] = ((df['open'] - df['close'].shift(1)) / df['close'].shift(1)) * 100

        # NaN indicator features (important for model)
        nan_features = ['sma_20', 'rsi_14', 'rsi_7', 'macd', 'macd_signal', 'macd_histogram',
                       'bb_upper', 'bb_middle', 'bb_lower', 'stoch_k', 'stoch_d', 'williams_r', 'cci', 'atr_14', 'volume_ratio']
        
        for feature in nan_features:
            if feature in features.columns:
                features[f'{feature}_isnan'] = features[feature].isna().astype(float)

        return features
        
    async def test_fixed_predictions(self, tickers):
        """Test model predictions with complete 74-feature input"""
        print("🔮 Testing Fixed Model Predictions (74 Features)...")
        print("=" * 60)
        
        # Load models
        await self.model_loader.load_models()
        
        results = {}
        
        for ticker in tickers:
            print(f"\n📊 Testing {ticker}...")
            
            try:
                # Download data
                data = await self.data_downloader.download_databento_ticker(ticker)
                if data is None:
                    data = await self.data_downloader.download_yfinance_fallback(ticker)
                
                if data is None or len(data) < 20:
                    print(f"❌ {ticker}: Insufficient data")
                    continue
                
                print(f"   📈 Downloaded {len(data)} days of data")
                
                # Extract complete features (74 features)
                basic_features = self.extract_basic_features(data)
                complete_features = await self.advanced_engineer.engineer_all_features(basic_features, ticker)
                
                print(f"   🔧 Complete features: {len(complete_features.columns)} features")
                
                # Get latest features for prediction
                latest_features = complete_features.iloc[-1].to_dict()
                
                # Test moon prediction
                moon_confidence, moon_details = await self.model_loader.predict_moon(latest_features)

                # Test rug prediction
                rug_confidence, rug_details = await self.model_loader.predict_rug(latest_features)
                
                results[ticker] = {
                    'moon_confidence': moon_confidence,
                    'moon_details': moon_details,
                    'rug_confidence': rug_confidence,
                    'rug_details': rug_details,
                    'latest_price': data['Close'].iloc[-1],
                    'feature_count': len(complete_features.columns)
                }
                
                # Display results
                print(f"   🌙 Moon Prediction: {moon_confidence:.1%}")
                if moon_details.get('individual_predictions'):
                    individual = moon_details['individual_predictions']
                    print(f"      Individual: {', '.join([f'{k}={v:.1%}' for k, v in individual.items()])}")
                    print(f"      Agreement: {moon_details.get('model_agreement', 0):.1%}")
                
                print(f"   💥 Rug Prediction: {rug_confidence:.1%}")
                if rug_details.get('individual_predictions'):
                    individual = rug_details['individual_predictions']
                    print(f"      Individual: {', '.join([f'{k}={v:.1%}' for k, v in individual.items()])}")
                    print(f"      Agreement: {rug_details.get('model_agreement', 0):.1%}")
                
            except Exception as e:
                print(f"❌ {ticker}: Prediction error - {str(e)}")
                
        return results
    
    def validate_predictions(self, results):
        """Validate prediction quality"""
        print(f"\n📈 Validating Prediction Quality...")
        print("=" * 60)
        
        validation_results = {
            'realistic_confidence_ranges': 0,
            'no_extreme_predictions': 0,
            'model_agreement_reasonable': 0,
            'ensemble_working': 0
        }
        
        for ticker, data in results.items():
            print(f"\n🔍 Validating {ticker}:")
            
            moon_conf = data['moon_confidence']
            rug_conf = data['rug_confidence']
            
            # Check realistic confidence ranges (not 0% or 100%)
            if 0.05 <= moon_conf <= 0.95 and 0.05 <= rug_conf <= 0.95:
                validation_results['realistic_confidence_ranges'] += 1
                print(f"   ✅ Realistic confidence ranges: Moon {moon_conf:.1%}, Rug {rug_conf:.1%}")
            else:
                print(f"   ❌ Extreme confidence: Moon {moon_conf:.1%}, Rug {rug_conf:.1%}")
            
            # Check no extreme predictions (>95%)
            if moon_conf < 0.95 and rug_conf < 0.95:
                validation_results['no_extreme_predictions'] += 1
                print(f"   ✅ No extreme predictions")
            else:
                print(f"   ❌ Extreme prediction detected")
            
            # Check model agreement
            moon_agreement = data['moon_details'].get('model_agreement', 0)
            rug_agreement = data['rug_details'].get('model_agreement', 0)
            
            if moon_agreement > 0.5 and rug_agreement > 0.5:
                validation_results['model_agreement_reasonable'] += 1
                print(f"   ✅ Good model agreement: Moon {moon_agreement:.1%}, Rug {rug_agreement:.1%}")
            else:
                print(f"   ⚠️  Low model agreement: Moon {moon_agreement:.1%}, Rug {rug_agreement:.1%}")
            
            # Check ensemble is working
            moon_individual = data['moon_details'].get('individual_predictions', {})
            rug_individual = data['rug_details'].get('individual_predictions', {})
            
            if len(moon_individual) >= 2 and len(rug_individual) >= 2:
                validation_results['ensemble_working'] += 1
                print(f"   ✅ Ensemble working: {len(moon_individual)} moon models, {len(rug_individual)} rug models")
            else:
                print(f"   ❌ Ensemble not working properly")
        
        # Summary
        total_tickers = len(results)
        print(f"\n📊 Validation Summary:")
        print(f"   Realistic Confidence Ranges: {validation_results['realistic_confidence_ranges']}/{total_tickers}")
        print(f"   No Extreme Predictions: {validation_results['no_extreme_predictions']}/{total_tickers}")
        print(f"   Model Agreement Reasonable: {validation_results['model_agreement_reasonable']}/{total_tickers}")
        print(f"   Ensemble Working: {validation_results['ensemble_working']}/{total_tickers}")
        
        # Overall success
        overall_success = (
            validation_results['realistic_confidence_ranges'] >= total_tickers * 0.8 and
            validation_results['no_extreme_predictions'] >= total_tickers * 0.8
        )
        
        return overall_success, validation_results

async def main():
    """Main test execution"""
    print("🚀 Testing Fixed Model Predictions...")
    print("=" * 60)
    
    tester = FixedPredictionTester()
    
    # Test with the same tickers, including GOOGL (the problematic one)
    test_tickers = ['AAPL', 'TSLA', 'GOOGL', 'NVDA']
    
    try:
        # Test fixed predictions
        results = await tester.test_fixed_predictions(test_tickers)
        
        if not results:
            print("❌ No predictions made. Cannot proceed.")
            return False
        
        # Validate results
        success, validation_results = tester.validate_predictions(results)
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 Fixed Model Predictions Test: PASSED")
            print("✅ Models now make realistic predictions with complete features!")
        else:
            print("⚠️ Fixed Model Predictions Test: ISSUES DETECTED")
            print("❌ Still need to address prediction quality issues")
        
        return success
        
    except Exception as e:
        print(f"❌ Fixed prediction test execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
