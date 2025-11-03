#!/usr/bin/env python3
"""
Test RandomForest-Only Predictions
Test predictions using only RandomForest from existing ensemble models
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
from pathlib import Path

# Add backend to path
sys.path.append('/Users/vynfred/Documents/bullsbears/backend')

from app.analyzers.data_downloader import DataDownloader
from app.features.advanced_features import AdvancedFeatureEngineer
import talib

class RandomForestOnlyTester:
    def __init__(self):
        self.data_downloader = DataDownloader()
        self.advanced_engineer = AdvancedFeatureEngineer()
        self.moon_rf_model = None
        self.rug_rf_model = None
        self.feature_names = None
    
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
    
    def load_rf_models(self):
        """Load RandomForest models from existing ensemble"""
        print("🌲 Loading RandomForest models from ensemble...")
        
        model_dir = Path('/Users/vynfred/Documents/bullsbears/backend/data/models')
        
        # Find latest ensemble models
        moon_rf_files = list(model_dir.glob('moon_ensemble_*_random_forest.joblib'))
        rug_rf_files = list(model_dir.glob('rug_ensemble_*_random_forest.joblib'))
        
        if not moon_rf_files or not rug_rf_files:
            print("❌ RandomForest model files not found")
            return False
        
        # Get latest files
        moon_rf_file = sorted(moon_rf_files)[-1]
        rug_rf_file = sorted(rug_rf_files)[-1]
        
        print(f"   Loading moon RF: {moon_rf_file.name}")
        print(f"   Loading rug RF: {rug_rf_file.name}")
        
        # Load models
        self.moon_rf_model = joblib.load(moon_rf_file)
        self.rug_rf_model = joblib.load(rug_rf_file)
        
        # Load feature names from metadata
        metadata_file = moon_rf_file.parent / f"{moon_rf_file.stem.replace('_random_forest', '')}_ensemble_metadata.json"
        if metadata_file.exists():
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            self.feature_names = metadata.get('feature_names', [])
            print(f"   ✅ Loaded {len(self.feature_names)} feature names")
        else:
            print("⚠️  Metadata file not found, will use feature order")
        
        print("   ✅ RandomForest models loaded successfully")
        return True
    
    def predict_rf_only(self, features_dict, model_type):
        """Make prediction using only RandomForest"""
        model = self.moon_rf_model if model_type == 'moon' else self.rug_rf_model
        
        if model is None:
            return 0.0, {"error": "Model not loaded"}
        
        # Prepare feature vector
        if self.feature_names:
            feature_vector = []
            for feature_name in self.feature_names:
                feature_vector.append(features_dict.get(feature_name, 0.0))
        else:
            feature_vector = list(features_dict.values())
        
        # Make prediction
        feature_df = pd.DataFrame([feature_vector], columns=self.feature_names or list(features_dict.keys()))
        prediction_proba = model.predict_proba(feature_df)
        
        confidence = prediction_proba[0][1] if prediction_proba.shape[1] > 1 else prediction_proba[0][0]
        
        prediction_details = {
            "model_type": f"{model_type}_rf_only",
            "confidence": float(confidence),
            "model_name": "RandomForest",
            "features_used": len(feature_vector),
            "prediction_time": datetime.now().isoformat()
        }
        
        return float(confidence), prediction_details
        
    async def test_rf_predictions(self, tickers):
        """Test RandomForest-only predictions"""
        print("🔮 Testing RandomForest-Only Predictions...")
        print("=" * 60)
        
        # Load models
        if not self.load_rf_models():
            return {}
        
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
                
                # Test RandomForest-only predictions
                moon_confidence, moon_details = self.predict_rf_only(latest_features, 'moon')
                rug_confidence, rug_details = self.predict_rf_only(latest_features, 'rug')
                
                results[ticker] = {
                    'moon_confidence': moon_confidence,
                    'moon_details': moon_details,
                    'rug_confidence': rug_confidence,
                    'rug_details': rug_details,
                    'latest_price': data['Close'].iloc[-1],
                    'feature_count': len(complete_features.columns)
                }
                
                # Display results
                print(f"   🌙 Moon (RF Only): {moon_confidence:.1%}")
                print(f"   💥 Rug (RF Only): {rug_confidence:.1%}")
                
            except Exception as e:
                print(f"❌ {ticker}: Prediction error - {str(e)}")
                
        return results
    
    def validate_rf_predictions(self, results):
        """Validate RandomForest-only prediction quality"""
        print(f"\n📈 Validating RandomForest-Only Predictions...")
        print("=" * 60)
        
        validation_results = {
            'realistic_ranges': 0,
            'no_extremes': 0,
            'reasonable_spread': 0
        }
        
        for ticker, data in results.items():
            print(f"\n🔍 Validating {ticker}:")
            
            moon_conf = data['moon_confidence']
            rug_conf = data['rug_confidence']
            
            # Check realistic ranges (10-90%)
            if 0.1 <= moon_conf <= 0.9 and 0.1 <= rug_conf <= 0.9:
                validation_results['realistic_ranges'] += 1
                print(f"   ✅ Realistic ranges: Moon {moon_conf:.1%}, Rug {rug_conf:.1%}")
            else:
                print(f"   ⚠️  Extreme ranges: Moon {moon_conf:.1%}, Rug {rug_conf:.1%}")
            
            # Check no extreme predictions (>95% or <5%)
            if 0.05 < moon_conf < 0.95 and 0.05 < rug_conf < 0.95:
                validation_results['no_extremes'] += 1
                print(f"   ✅ No extreme predictions")
            else:
                print(f"   ❌ Extreme prediction detected")
            
            # Check reasonable spread between moon and rug
            spread = abs(moon_conf - rug_conf)
            if spread > 0.1:  # At least 10% difference
                validation_results['reasonable_spread'] += 1
                print(f"   ✅ Good spread: {spread:.1%} difference")
            else:
                print(f"   ⚠️  Low spread: {spread:.1%} difference")
        
        # Summary
        total_tickers = len(results)
        print(f"\n📊 RandomForest-Only Validation Summary:")
        print(f"   Realistic Ranges: {validation_results['realistic_ranges']}/{total_tickers}")
        print(f"   No Extremes: {validation_results['no_extremes']}/{total_tickers}")
        print(f"   Reasonable Spread: {validation_results['reasonable_spread']}/{total_tickers}")
        
        # Overall success
        overall_success = (
            validation_results['realistic_ranges'] >= total_tickers * 0.8 and
            validation_results['no_extremes'] >= total_tickers * 0.8
        )
        
        return overall_success, validation_results

async def main():
    """Main test execution"""
    print("🚀 Testing RandomForest-Only Predictions...")
    print("=" * 60)
    
    tester = RandomForestOnlyTester()
    
    # Test with the same problematic tickers
    test_tickers = ['AAPL', 'TSLA', 'GOOGL', 'NVDA']
    
    try:
        # Test RandomForest-only predictions
        results = await tester.test_rf_predictions(test_tickers)
        
        if not results:
            print("❌ No predictions made. Cannot proceed.")
            return False
        
        # Validate results
        success, validation_results = tester.validate_rf_predictions(results)
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 RandomForest-Only Predictions Test: PASSED")
            print("✅ RandomForest models make realistic predictions!")
            print("✅ LogisticRegression was the source of extreme predictions")
        else:
            print("⚠️ RandomForest-Only Predictions Test: MIXED RESULTS")
            print("❓ Need to investigate RandomForest predictions further")
        
        return success
        
    except Exception as e:
        print(f"❌ RandomForest test execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
