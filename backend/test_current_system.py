#!/usr/bin/env python3
"""
Test Current Ensemble System
Validates current ensemble models work correctly before adding AI features.
Tests moon/rug analyzers with sample tickers, verifies predictions, confidence scores, and model agreement.
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import talib

# Add backend to path
sys.path.append('/Users/vynfred/Documents/bullsbears/backend')

from app.services.model_loader import ModelLoader
from app.analyzers.data_downloader import DataDownloader
from app.features.advanced_features import AdvancedFeatureEngineer

class CurrentSystemTester:
    def __init__(self):
        self.model_loader = ModelLoader()
        self.data_downloader = DataDownloader()
        self.feature_engineer = AdvancedFeatureEngineer()
        
    async def test_model_loading(self):
        """Test ensemble model loading"""
        print("🤖 Testing Model Loading...")
        
        # Load models
        await self.model_loader.load_models()
        health = self.model_loader.get_model_health()

        print(f"✅ Models loaded: {health['models_loaded']}")
        print(f"✅ Confidence threshold: {self.model_loader.confidence_threshold}%")
        
        # Check moon model
        if "moon" in self.model_loader.model_metadata:
            moon_info = self.model_loader.model_metadata["moon"]
            print(f"🌙 Moon Model: {moon_info.model_type} (v{moon_info.version})")
            print(f"   Accuracy: {moon_info.accuracy:.1%}")
            print(f"   Features: {len(moon_info.features)}")
            print(f"   Is Ensemble: {moon_info.is_ensemble}")
            if moon_info.is_ensemble and moon_info.base_models:
                print(f"   Base Models: {list(moon_info.base_models.keys())}")

        # Check rug model
        if "rug" in self.model_loader.model_metadata:
            rug_info = self.model_loader.model_metadata["rug"]
            print(f"💥 Rug Model: {rug_info.model_type} (v{rug_info.version})")
            print(f"   Accuracy: {rug_info.accuracy:.1%}")
            print(f"   Features: {len(rug_info.features)}")
            print(f"   Is Ensemble: {rug_info.is_ensemble}")
            if rug_info.is_ensemble and rug_info.base_models:
                print(f"   Base Models: {list(rug_info.base_models.keys())}")
        
        return health['models_loaded'] == 2
    
    async def test_data_download(self, tickers):
        """Test data downloading for sample tickers"""
        print(f"\n📊 Testing Data Download for {len(tickers)} tickers...")

        results = {}
        for ticker in tickers:
            try:
                # Try Databento first, then yfinance fallback
                data = await self.data_downloader.download_databento_ticker(ticker)

                if data is None:
                    # Fallback to yfinance
                    data = await self.data_downloader.download_yfinance_fallback(ticker)

                if data is not None and len(data) > 0:
                    results[ticker] = data
                    print(f"✅ {ticker}: {len(data)} days of data")
                else:
                    print(f"❌ {ticker}: No data")

            except Exception as e:
                print(f"❌ {ticker}: Error - {str(e)}")

        return results
    
    def extract_basic_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract basic technical features (57 features like in training)"""
        features = pd.DataFrame(index=data.index)

        # Rename columns to match expected format
        df = data.copy()
        if 'Close' in df.columns:
            df = df.rename(columns={'Close': 'close', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Volume': 'volume'})

        # Price features
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

        # Price relative to moving averages
        features['close_sma5_ratio'] = df['close'] / features['sma_5']
        features['close_sma10_ratio'] = df['close'] / features['sma_10']
        features['close_sma20_ratio'] = df['close'] / features['sma_20']

        # RSI
        features['rsi_14'] = talib.RSI(df['close'], timeperiod=14)
        features['rsi_7'] = talib.RSI(df['close'], timeperiod=7)

        # MACD
        macd, macd_signal, macd_hist = talib.MACD(df['close'])
        features['macd'] = macd
        features['macd_signal'] = macd_signal
        features['macd_histogram'] = macd_hist

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'])
        features['bb_upper'] = bb_upper
        features['bb_middle'] = bb_middle
        features['bb_lower'] = bb_lower
        features['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)

        # Volume indicators
        features['volume_sma_10'] = talib.SMA(df['volume'], timeperiod=10)
        features['volume_ratio'] = df['volume'] / features['volume_sma_10']

        # Volatility
        features['atr_14'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        features['volatility_10'] = df['close'].rolling(10).std()

        # Price momentum
        features['momentum_5'] = talib.MOM(df['close'], timeperiod=5)
        features['momentum_10'] = talib.MOM(df['close'], timeperiod=10)
        features['roc_5'] = talib.ROC(df['close'], timeperiod=5)
        features['roc_10'] = talib.ROC(df['close'], timeperiod=10)

        # Stochastic
        stoch_k, stoch_d = talib.STOCH(df['high'], df['low'], df['close'])
        features['stoch_k'] = stoch_k
        features['stoch_d'] = stoch_d

        # Williams %R
        features['williams_r'] = talib.WILLR(df['high'], df['low'], df['close'])

        # Commodity Channel Index
        features['cci'] = talib.CCI(df['high'], df['low'], df['close'])

        return features

    def test_feature_extraction(self, ticker_data):
        """Test feature extraction for sample data"""
        print(f"\n🔧 Testing Feature Extraction...")

        feature_results = {}
        for ticker, data in ticker_data.items():
            try:
                # Extract basic features (57 features like in training)
                basic_features = self.extract_basic_features(data)

                # Extract advanced features (21 more features)
                advanced_features = self.feature_engineer.engineer_all_features(basic_features, ticker)

                # Get latest features (most recent day)
                if len(advanced_features) > 0:
                    latest_features = advanced_features.iloc[-1]
                    feature_results[ticker] = latest_features

                    print(f"✅ {ticker}: {len(latest_features)} features extracted")
                    print(f"   Sample features: RSI={latest_features.get('rsi_14', 'N/A'):.2f}, "
                          f"Volume_Ratio={latest_features.get('volume_ratio', 'N/A'):.2f}")
                else:
                    print(f"❌ {ticker}: No features extracted")

            except Exception as e:
                print(f"❌ {ticker}: Feature extraction error - {str(e)}")

        return feature_results
    
    async def test_ensemble_predictions(self, feature_data):
        """Test ensemble model predictions"""
        print(f"\n🎯 Testing Ensemble Predictions...")

        prediction_results = {}
        for ticker, features in feature_data.items():
            try:
                # Convert pandas Series to dictionary for model input
                feature_dict = features.to_dict()

                # Test moon prediction - returns (confidence, details)
                moon_confidence, moon_details = await self.model_loader.predict_moon(feature_dict)

                # Test rug prediction - returns (confidence, details)
                rug_confidence, rug_details = await self.model_loader.predict_rug(feature_dict)

                prediction_results[ticker] = {
                    'moon': {'confidence': moon_confidence, **moon_details},
                    'rug': {'confidence': rug_confidence, **rug_details}
                }

                print(f"✅ {ticker} Predictions:")
                print(f"   🌙 Moon: {moon_confidence:.1%} "
                      f"(Agreement: {moon_details.get('model_agreement', 0):.1%})")
                print(f"   💥 Rug:  {rug_confidence:.1%} "
                      f"(Agreement: {rug_details.get('model_agreement', 0):.1%})")

                # Check individual model predictions if ensemble
                if moon_details.get('is_ensemble') and 'individual_predictions' in moon_details:
                    individual = moon_details['individual_predictions']
                    print(f"      Individual: RF={individual.get('random_forest', 0):.1%}, "
                          f"LR={individual.get('logistic', 0):.1%}")

            except Exception as e:
                print(f"❌ {ticker}: Prediction error - {str(e)}")

        return prediction_results
    
    def analyze_results(self, predictions):
        """Analyze prediction results for validation"""
        print(f"\n📈 Analyzing Results...")
        
        moon_confidences = []
        rug_confidences = []
        moon_agreements = []
        rug_agreements = []
        
        for ticker, results in predictions.items():
            moon_conf = results['moon']['confidence']
            rug_conf = results['rug']['confidence']
            
            moon_confidences.append(moon_conf)
            rug_confidences.append(rug_conf)
            
            if 'model_agreement' in results['moon']:
                moon_agreements.append(results['moon']['model_agreement'])
            if 'model_agreement' in results['rug']:
                rug_agreements.append(results['rug']['model_agreement'])
        
        print(f"🌙 Moon Predictions:")
        print(f"   Average Confidence: {np.mean(moon_confidences):.1%}")
        print(f"   Range: {np.min(moon_confidences):.1%} - {np.max(moon_confidences):.1%}")
        if moon_agreements:
            print(f"   Average Agreement: {np.mean(moon_agreements):.1%}")
        
        print(f"💥 Rug Predictions:")
        print(f"   Average Confidence: {np.mean(rug_confidences):.1%}")
        print(f"   Range: {np.min(rug_confidences):.1%} - {np.max(rug_confidences):.1%}")
        if rug_agreements:
            print(f"   Average Agreement: {np.mean(rug_agreements):.1%}")
        
        # Validation checks
        realistic_moon = 0.1 <= np.mean(moon_confidences) <= 0.9
        realistic_rug = 0.1 <= np.mean(rug_confidences) <= 0.9
        
        print(f"\n✅ Validation Results:")
        print(f"   Realistic Moon Confidence: {'✅' if realistic_moon else '❌'}")
        print(f"   Realistic Rug Confidence: {'✅' if realistic_rug else '❌'}")
        print(f"   No 99%+ Overfitting: {'✅' if max(moon_confidences + rug_confidences) < 0.99 else '❌'}")
        
        return realistic_moon and realistic_rug

async def main():
    """Main test execution"""
    print("🚀 Testing Current Ensemble System...")
    print("=" * 60)
    
    tester = CurrentSystemTester()
    
    # Sample tickers for testing
    test_tickers = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL']
    
    try:
        # Step 1: Test model loading
        models_loaded = await tester.test_model_loading()
        if not models_loaded:
            print("❌ Model loading failed. Cannot proceed.")
            return False
        
        # Step 2: Test data download
        ticker_data = await tester.test_data_download(test_tickers)
        if not ticker_data:
            print("❌ Data download failed. Cannot proceed.")
            return False
        
        # Step 3: Test feature extraction
        feature_data = tester.test_feature_extraction(ticker_data)
        if not feature_data:
            print("❌ Feature extraction failed. Cannot proceed.")
            return False
        
        # Step 4: Test ensemble predictions
        predictions = await tester.test_ensemble_predictions(feature_data)
        if not predictions:
            print("❌ Ensemble predictions failed. Cannot proceed.")
            return False
        
        # Step 5: Analyze results
        validation_passed = tester.analyze_results(predictions)
        
        print("\n" + "=" * 60)
        if validation_passed:
            print("🎉 Current System Test: PASSED")
            print("✅ Ready to proceed with AI feature integration!")
        else:
            print("⚠️ Current System Test: ISSUES DETECTED")
            print("❌ Need to fix current system before AI integration")
        
        return validation_passed
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
