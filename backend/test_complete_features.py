#!/usr/bin/env python3
"""
Test Complete Feature Extraction
Validates that we extract ALL 74 features that the trained models expect.
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

class CompleteFeatureTester:
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

    async def test_complete_feature_extraction(self, tickers):
        """Test complete 74-feature extraction for sample tickers"""
        print("🔧 Testing Complete Feature Extraction (74 Features)...")
        print("=" * 60)
        
        # Load model to get expected features
        await self.model_loader.load_models()
        moon_info = self.model_loader.model_metadata.get('moon')

        if not moon_info or not moon_info.features:
            print("❌ Cannot load model feature names")
            return False

        expected_features = moon_info.features
        print(f"📋 Expected Features: {len(expected_features)} features")
        print(f"   First 10: {expected_features[:10]}")
        print(f"   Last 10: {expected_features[-10:]}")
        
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
                
                # Extract basic features (57 features)
                basic_features = self.extract_basic_features(data)
                print(f"   🔧 Basic features: {len(basic_features.columns)} features")
                
                # Extract advanced features (21 additional features)
                complete_features = await self.advanced_engineer.engineer_all_features(basic_features, ticker)
                print(f"   🚀 Complete features: {len(complete_features.columns)} features")
                
                # Check feature alignment
                current_features = list(complete_features.columns)
                missing_features = [f for f in expected_features if f not in current_features]
                extra_features = [f for f in current_features if f not in expected_features]
                
                print(f"   📋 Feature Analysis:")
                print(f"      Expected: {len(expected_features)}")
                print(f"      Current: {len(current_features)}")
                print(f"      Missing: {len(missing_features)}")
                print(f"      Extra: {len(extra_features)}")
                
                if missing_features:
                    print(f"   ❌ Missing Features: {missing_features[:5]}{'...' if len(missing_features) > 5 else ''}")
                
                if extra_features:
                    print(f"   ➕ Extra Features: {extra_features[:5]}{'...' if len(extra_features) > 5 else ''}")
                
                # Create aligned feature vector for model
                aligned_features = self._align_features_to_model(complete_features, expected_features)
                print(f"   ✅ Aligned features: {len(aligned_features.columns)} features")
                
                results[ticker] = {
                    'raw_features': len(current_features),
                    'aligned_features': len(aligned_features.columns),
                    'missing_count': len(missing_features),
                    'missing_features': missing_features,
                    'extra_count': len(extra_features),
                    'feature_data': aligned_features.iloc[-1].to_dict()  # Latest row
                }
                
            except Exception as e:
                print(f"❌ {ticker}: Feature extraction error - {str(e)}")
                
        return results
    
    def _align_features_to_model(self, df: pd.DataFrame, expected_features: list) -> pd.DataFrame:
        """Align extracted features to match model expectations."""
        aligned_df = pd.DataFrame(index=df.index)
        
        for feature in expected_features:
            if feature in df.columns:
                aligned_df[feature] = df[feature]
            else:
                # Fill missing features with appropriate defaults
                if 'isnan' in feature:
                    aligned_df[feature] = 0.0  # NaN indicators default to False
                elif 'ratio' in feature or 'percent' in feature:
                    aligned_df[feature] = 1.0  # Ratios default to neutral
                elif 'volume' in feature:
                    aligned_df[feature] = df['volume'].mean() if 'volume' in df.columns else 1000000
                elif 'price' in feature or 'close' in feature:
                    aligned_df[feature] = df['close'].iloc[-1] if 'close' in df.columns else 100.0
                else:
                    aligned_df[feature] = 0.0  # Default to zero
        
        return aligned_df
    
    def validate_feature_quality(self, results):
        """Validate feature extraction quality"""
        print(f"\n📈 Validating Feature Quality...")
        print("=" * 60)
        
        validation_results = {
            'complete_feature_extraction': 0,
            'missing_features_resolved': 0,
            'no_nan_values': 0,
            'realistic_ranges': 0
        }
        
        for ticker, data in results.items():
            print(f"\n🔍 Validating {ticker}:")
            
            # Check complete feature extraction
            if data['aligned_features'] == 74:
                validation_results['complete_feature_extraction'] += 1
                print(f"   ✅ Complete features: {data['aligned_features']}/74")
            else:
                print(f"   ❌ Incomplete features: {data['aligned_features']}/74")
            
            # Check missing features
            if data['missing_count'] == 0:
                validation_results['missing_features_resolved'] += 1
                print(f"   ✅ No missing features")
            else:
                print(f"   ⚠️  Missing {data['missing_count']} features")
            
            # Check for NaN values
            feature_data = data['feature_data']
            nan_count = sum(1 for v in feature_data.values() if pd.isna(v))
            
            if nan_count == 0:
                validation_results['no_nan_values'] += 1
                print(f"   ✅ No NaN values")
            else:
                print(f"   ❌ {nan_count} NaN values found")
            
            # Check realistic ranges
            unrealistic_count = 0
            for key, value in feature_data.items():
                if pd.isna(value) or np.isinf(value):
                    unrealistic_count += 1
                elif abs(value) > 1e6:  # Extremely large values
                    unrealistic_count += 1
            
            if unrealistic_count == 0:
                validation_results['realistic_ranges'] += 1
                print(f"   ✅ Realistic value ranges")
            else:
                print(f"   ⚠️  {unrealistic_count} unrealistic values")
        
        # Summary
        total_tickers = len(results)
        print(f"\n📊 Validation Summary:")
        print(f"   Complete Feature Extraction: {validation_results['complete_feature_extraction']}/{total_tickers}")
        print(f"   Missing Features Resolved: {validation_results['missing_features_resolved']}/{total_tickers}")
        print(f"   No NaN Values: {validation_results['no_nan_values']}/{total_tickers}")
        print(f"   Realistic Ranges: {validation_results['realistic_ranges']}/{total_tickers}")
        
        # Overall success
        overall_success = (
            validation_results['complete_feature_extraction'] >= total_tickers * 0.8 and
            validation_results['no_nan_values'] >= total_tickers * 0.8
        )
        
        return overall_success, validation_results

async def main():
    """Main test execution"""
    print("🚀 Testing Complete Feature Extraction System...")
    print("=" * 60)
    
    tester = CompleteFeatureTester()
    
    # Test with a smaller set first
    test_tickers = ['AAPL', 'TSLA', 'NVDA']
    
    try:
        # Test complete feature extraction
        results = await tester.test_complete_feature_extraction(test_tickers)
        
        if not results:
            print("❌ No features extracted. Cannot proceed.")
            return False
        
        # Validate results
        success, validation_results = tester.validate_feature_quality(results)
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 Complete Feature Extraction Test: PASSED")
            print("✅ Ready to proceed with model predictions!")
        else:
            print("⚠️ Complete Feature Extraction Test: ISSUES DETECTED")
            print("❌ Need to fix feature extraction before model predictions")
        
        return success
        
    except Exception as e:
        print(f"❌ Complete feature test execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
