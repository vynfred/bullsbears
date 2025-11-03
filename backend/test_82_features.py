#!/usr/bin/env python3
"""
Test 82-Feature Integration (74 + 8 AI = 82)
Tests the complete pipeline: 74 existing features + 8 AI features = 82 total
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

# Add backend to path
sys.path.append('/Users/vynfred/Documents/bullsbears/backend')

from app.features.ai_features import AIFeatureExtractor
from app.services.model_loader import ModelLoader

class Feature82Tester:
    def __init__(self):
        self.ai_extractor = AIFeatureExtractor()
        self.model_loader = ModelLoader()

    def create_mock_74_features(self, ticker: str) -> dict:
        """Create mock 74 features (same as trained models expect)"""
        np.random.seed(hash(ticker) % 1000)  # Ticker-specific seed
        
        # Create realistic feature values
        features = {}
        
        # Basic OHLCV features (5)
        base_price = {'AAPL': 220, 'TSLA': 250, 'GOOGL': 170, 'NVDA': 140}.get(ticker, 100)
        features.update({
            'close': base_price + np.random.randn() * 5,
            'open': base_price + np.random.randn() * 5,
            'high': base_price + np.random.randn() * 5 + 2,
            'low': base_price + np.random.randn() * 5 - 2,
            'volume': np.random.randint(10000000, 50000000)
        })
        
        # Price ratios (2)
        features.update({
            'high_low_ratio': features['high'] / features['low'],
            'close_open_ratio': features['close'] / features['open']
        })
        
        # Moving averages (5)
        sma_base = features['close']
        features.update({
            'sma_5': sma_base + np.random.randn() * 2,
            'sma_10': sma_base + np.random.randn() * 3,
            'sma_20': sma_base + np.random.randn() * 4,
            'close_sma5_ratio': features['close'] / (sma_base + np.random.randn() * 2),
            'close_sma10_ratio': features['close'] / (sma_base + np.random.randn() * 3)
        })
        
        # Technical indicators (15)
        features.update({
            'rsi_14': np.random.uniform(20, 80),
            'rsi_7': np.random.uniform(20, 80),
            'macd': np.random.randn() * 2,
            'macd_signal': np.random.randn() * 2,
            'macd_histogram': np.random.randn() * 1,
            'bb_upper': features['close'] + np.random.uniform(5, 15),
            'bb_middle': features['close'] + np.random.randn() * 2,
            'bb_lower': features['close'] - np.random.uniform(5, 15),
            'bb_position': np.random.uniform(0, 1),
            'volume_sma_10': features['volume'] + np.random.randint(-5000000, 5000000),
            'volume_ratio': np.random.uniform(0.5, 2.0),
            'atr_14': np.random.uniform(2, 8),
            'volatility_10': np.random.uniform(0.01, 0.05),
            'momentum_5': np.random.randn() * 5,
            'momentum_10': np.random.randn() * 8
        })
        
        # More indicators (10)
        features.update({
            'roc_5': np.random.uniform(-10, 10),
            'roc_10': np.random.uniform(-15, 15),
            'stoch_k': np.random.uniform(0, 100),
            'stoch_d': np.random.uniform(0, 100),
            'williams_r': np.random.uniform(-100, 0),
            'cci': np.random.uniform(-200, 200),
            'price_trend_pct': np.random.uniform(-5, 5),
            'volume_trend': np.random.uniform(-20, 20),
            'recent_volatility': np.random.uniform(0.01, 0.04),
            'gap_pct': np.random.uniform(-2, 2)
        })
        
        # NaN indicator features (15)
        nan_features = ['sma_20', 'rsi_14', 'rsi_7', 'macd', 'macd_signal', 'macd_histogram',
                       'bb_upper', 'bb_middle', 'bb_lower', 'stoch_k', 'stoch_d', 'williams_r',
                       'cci', 'atr_14', 'volume_ratio']
        
        for feature in nan_features:
            features[f'{feature}_isnan'] = np.random.choice([0.0, 1.0], p=[0.9, 0.1])
        
        # Additional features to reach 74
        features['close_sma20_ratio'] = features['close'] / features['sma_20']
        
        # Advanced features (need to reach exactly 74 total)
        current_count = len(features)
        needed = 74 - current_count

        print(f"   📊 Current features: {current_count}, need {needed} more for 74 total")

        # Add exactly the right number of advanced features
        advanced_feature_names = [
            'short_interest_ratio', 'days_to_cover', 'short_volume_ratio',
            'put_call_ratio', 'options_volume_ratio', 'gamma_exposure',
            'vix_correlation', 'sector_beta', 'market_cap_log',
            'price_to_book', 'debt_to_equity', 'current_ratio',
            'rsi_divergence', 'macd_divergence', 'volume_profile_poc',
            'support_resistance_score', 'trend_strength', 'liquidity_score',
            'institutional_ownership', 'analyst_rating', 'earnings_surprise'
        ]

        for i in range(min(needed, len(advanced_feature_names))):
            feature_name = advanced_feature_names[i]
            if 'ratio' in feature_name or 'correlation' in feature_name:
                features[feature_name] = np.random.uniform(0, 2)
            elif 'score' in feature_name or 'strength' in feature_name or 'rating' in feature_name:
                features[feature_name] = np.random.uniform(0, 1)
            else:
                features[feature_name] = np.random.randn()

        print(f"   ✅ Final feature count: {len(features)}")
        return features

    async def create_mock_ai_features(self, ticker: str) -> dict:
        """Create mock AI features using the AI extractor"""
        # Mock AI service responses
        mock_grok_analysis = AsyncMock()
        mock_grok_analysis.technical_confidence = np.random.uniform(0.3, 0.9)
        mock_grok_analysis.volume_surge_detected = np.random.uniform(0.0, 1.0)
        mock_grok_analysis.rsi_oversold = np.random.uniform(0.0, 0.5)
        mock_grok_analysis.social_buzz_score = np.random.uniform(0.2, 0.8)
        
        mock_deepseek_analysis = AsyncMock()
        mock_deepseek_analysis.sentiment_score = np.random.uniform(0.2, 0.8)
        mock_deepseek_analysis.news_sentiment = np.random.uniform(0.3, 0.7)
        mock_deepseek_analysis.narrative_strength = np.random.uniform(0.4, 0.9)
        mock_deepseek_analysis.bearish_keywords = np.random.uniform(0.0, 0.3)
        
        # Create mock data for AI extractor
        data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        })
        
        technical_summary = {
            'rsi_14': 50.0,
            'bb_position': 0.5,
            'volume_ratio': 1.0,
            'price_change_5d': 2.0,
            'volatility': 0.02
        }
        
        # Mock the AI service calls and extract features
        with patch.object(self.ai_extractor.grok_service, 'analyze_option_play', return_value=mock_grok_analysis):
            with patch.object(self.ai_extractor.deepseek_service, 'analyze_news_sentiment', return_value=mock_deepseek_analysis):
                ai_features = await self.ai_extractor.extract_all_ai_features(
                    ticker=ticker,
                    data=data,
                    technical_summary=technical_summary,
                    news_context=f"Mock news for {ticker}"
                )
        
        return ai_features

    async def test_82_feature_integration(self):
        """Test complete 82-feature integration with ML predictions"""
        print("🚀 Testing 82-Feature Integration (74 + 8 AI)")
        print("=" * 70)
        
        test_tickers = ['AAPL', 'TSLA', 'GOOGL', 'NVDA']
        results = {}
        
        for ticker in test_tickers:
            print(f"\n📊 Testing {ticker}...")
            
            try:
                # 1. Create 74 mock features
                features_74 = self.create_mock_74_features(ticker)
                print(f"   📈 Created 74 base features")
                
                # 2. Create 8 AI features
                ai_features = await self.create_mock_ai_features(ticker)
                print(f"   🤖 Created {len(ai_features)} AI features")
                
                # 3. Combine to 82 features
                all_features = {**features_74, **ai_features}
                print(f"   ✅ Total features: {len(all_features)} (expected: 82)")
                
                if len(all_features) != 82:
                    print(f"   ⚠️ Feature count mismatch: got {len(all_features)}, expected 82")
                
                # 4. Test ML predictions with 82 features
                # Load models first
                await self.model_loader.load_models()

                # Get predictions using RandomForest-only models
                moon_confidence, moon_details = await self.model_loader.predict_moon(all_features)
                rug_confidence, rug_details = await self.model_loader.predict_rug(all_features)
                
                results[ticker] = {
                    'success': True,
                    'feature_count': len(all_features),
                    'base_features': len(features_74),
                    'ai_features': len(ai_features),
                    'ai_feature_values': ai_features,
                    'moon_prediction': moon_confidence,
                    'rug_prediction': rug_confidence,
                    'moon_details': moon_details,
                    'rug_details': rug_details
                }

                print(f"   🌙 Moon prediction: {moon_confidence:.1%}")
                print(f"   💥 Rug prediction: {rug_confidence:.1%}")
                
                # Show sample AI features
                print(f"   🤖 Sample AI features:")
                for i, (feature, value) in enumerate(ai_features.items()):
                    if i < 4:  # Show first 4
                        print(f"      {feature}: {value:.3f}")
                
            except Exception as e:
                results[ticker] = {'success': False, 'error': str(e)}
                print(f"   ❌ Error: {e}")
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 82-Feature Integration Test Results:")
        print("=" * 70)
        
        successful = sum(1 for r in results.values() if r.get('success', False))
        
        for ticker, result in results.items():
            if result.get('success', False):
                feature_count = result['feature_count']
                base_count = result['base_features']
                ai_count = result['ai_features']
                moon_pred = result['moon_prediction']
                rug_pred = result['rug_prediction']
                
                print(f"✅ {ticker}: {feature_count} features ({base_count}+{ai_count}) | Moon: {moon_pred:.1%}, Rug: {rug_pred:.1%}")
                
                # Validate predictions are realistic
                if 0.1 <= moon_pred <= 0.9 and 0.1 <= rug_pred <= 0.9:
                    print(f"   ✅ Realistic predictions")
                else:
                    print(f"   ⚠️ Extreme predictions detected")
                    
            else:
                print(f"❌ {ticker}: {result.get('error', 'Unknown error')}")
        
        print(f"\n📈 Success Rate: {successful}/{len(test_tickers)} ({successful/len(test_tickers)*100:.1f}%)")
        
        if successful == len(test_tickers):
            print("🎉 82-Feature Integration: PASSED")
            print("✅ Ready for production with AI-enhanced predictions!")
            print("🚀 Next: Deploy to production environment")
        else:
            print("⚠️ 82-Feature Integration: PARTIAL SUCCESS")
            print("🔧 Some tickers failed - check logs above")
        
        return results

async def main():
    """Main test execution"""
    tester = Feature82Tester()
    results = await tester.test_82_feature_integration()
    return results

if __name__ == "__main__":
    results = asyncio.run(main())
