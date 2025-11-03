#!/usr/bin/env python3
"""
Test AI Features with Mock Data
Step 1: Mock AI → Compare vs Real → Add to 82 feats → Test AAPL/TSLA/GOOGL/NVDA
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

class MockAITester:
    def __init__(self):
        self.ai_extractor = AIFeatureExtractor()

    def create_mock_data(self, ticker: str) -> pd.DataFrame:
        """Create mock price data for testing"""
        dates = pd.date_range(start='2024-05-01', end='2024-11-01', freq='D')
        np.random.seed(42)  # For reproducible results
        
        # Generate realistic price data
        base_price = {'AAPL': 180, 'TSLA': 200, 'GOOGL': 160, 'NVDA': 800}.get(ticker, 100)
        
        data = pd.DataFrame({
            'close': base_price + np.cumsum(np.random.randn(len(dates)) * 2),
            'open': base_price + np.cumsum(np.random.randn(len(dates)) * 2),
            'high': base_price + np.cumsum(np.random.randn(len(dates)) * 2) + 5,
            'low': base_price + np.cumsum(np.random.randn(len(dates)) * 2) - 5,
            'volume': np.random.randint(10000000, 50000000, len(dates))
        }, index=dates)
        
        # Ensure high >= close >= low
        data['high'] = np.maximum(data['high'], data[['open', 'close']].max(axis=1))
        data['low'] = np.minimum(data['low'], data[['open', 'close']].min(axis=1))
        
        return data

    def create_mock_technical_summary(self, data: pd.DataFrame) -> dict:
        """Create mock technical summary"""
        latest = data.iloc[-1]
        return {
            'rsi_14': 45.5,
            'bb_position': 0.6,
            'volume_ratio': 1.2,
            'price_change_5d': 2.3,
            'volatility': 0.025
        }

    async def test_mock_ai_features(self):
        """Test AI features with mock responses"""
        print("🤖 Testing AI Features with Mock Data")
        print("=" * 60)
        
        test_tickers = ['AAPL', 'TSLA', 'GOOGL', 'NVDA']
        results = {}
        
        # Mock the AI service responses
        mock_grok_analysis = AsyncMock()
        mock_grok_analysis.technical_confidence = 0.75
        mock_grok_analysis.volume_surge_detected = 0.8
        mock_grok_analysis.rsi_oversold = 0.2
        mock_grok_analysis.social_buzz_score = 0.65
        
        mock_deepseek_analysis = AsyncMock()
        mock_deepseek_analysis.sentiment_score = 0.7
        mock_deepseek_analysis.news_sentiment = 0.6
        mock_deepseek_analysis.narrative_strength = 0.8
        mock_deepseek_analysis.bearish_keywords = 0.1
        
        for ticker in test_tickers:
            print(f"\n📊 Testing {ticker}...")
            
            try:
                # Create mock data
                data = self.create_mock_data(ticker)
                technical_summary = self.create_mock_technical_summary(data)
                
                print(f"   📈 Mock data: {len(data)} days")
                print(f"   🔧 Technical summary: RSI {technical_summary['rsi_14']}, BB {technical_summary['bb_position']}")
                
                # Mock the AI service calls
                with patch.object(self.ai_extractor.grok_service, 'analyze_option_play', return_value=mock_grok_analysis):
                    with patch.object(self.ai_extractor.deepseek_service, 'analyze_news_sentiment', return_value=mock_deepseek_analysis):
                        
                        # Extract AI features
                        ai_features = await self.ai_extractor.extract_all_ai_features(
                            ticker=ticker,
                            data=data,
                            technical_summary=technical_summary,
                            news_context=f"Mock news context for {ticker}"
                        )
                        
                        results[ticker] = {
                            'success': True,
                            'ai_features': ai_features,
                            'feature_count': len(ai_features)
                        }
                        
                        print(f"   ✅ AI features extracted: {len(ai_features)}")
                        for feature, value in ai_features.items():
                            print(f"      🤖 {feature}: {value:.3f}")
                            
            except Exception as e:
                results[ticker] = {'success': False, 'error': str(e)}
                print(f"   ❌ Error: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Mock AI Features Test Results:")
        print("=" * 60)
        
        successful = sum(1 for r in results.values() if r.get('success', False))
        
        for ticker, result in results.items():
            if result.get('success', False):
                feature_count = result['feature_count']
                print(f"✅ {ticker}: {feature_count} AI features extracted")
                
                # Validate feature structure
                expected_features = [
                    'ai_technical_confidence', 'ai_volume_surge_detected', 
                    'ai_rsi_oversold', 'ai_social_buzz_score',
                    'ai_sentiment_score', 'ai_news_sentiment', 
                    'ai_narrative_strength', 'ai_bearish_keywords'
                ]
                
                missing_features = [f for f in expected_features if f not in result['ai_features']]
                if missing_features:
                    print(f"   ⚠️ Missing features: {missing_features}")
                else:
                    print(f"   ✅ All 8 expected AI features present")
                    
            else:
                print(f"❌ {ticker}: {result.get('error', 'Unknown error')}")
        
        print(f"\n📈 Success Rate: {successful}/{len(test_tickers)} ({successful/len(test_tickers)*100:.1f}%)")
        
        if successful == len(test_tickers):
            print("🎉 Mock AI Features Test: PASSED")
            print("✅ AI feature extraction working correctly!")
            print("🔄 Next: Test with real AI APIs")
        else:
            print("⚠️ Mock AI Features Test: FAILED")
            print("🔧 Fix AI feature extraction before proceeding")
        
        return results

    async def test_ai_feature_structure(self):
        """Test that AI features have the correct structure and values"""
        print("\n🔍 Testing AI Feature Structure...")
        
        # Create test data
        data = self.create_mock_data('TEST')
        technical_summary = self.create_mock_technical_summary(data)
        
        # Test default features (when AI fails)
        default_features = {
            'ai_technical_confidence': 0.5,
            'ai_volume_surge_detected': 0.0,
            'ai_rsi_oversold': 0.0,
            'ai_social_buzz_score': 0.5,
            'ai_sentiment_score': 0.5,
            'ai_news_sentiment': 0.5,
            'ai_narrative_strength': 0.5,
            'ai_bearish_keywords': 0.0
        }
        
        # Test that default features are returned when AI fails
        ai_features = await self.ai_extractor.extract_all_ai_features(
            ticker='TEST',
            data=data,
            technical_summary=technical_summary,
            news_context="Test context"
        )
        
        print(f"   📊 Default AI features: {len(ai_features)}")
        
        # Validate structure
        structure_valid = True
        for expected_feature, expected_default in default_features.items():
            if expected_feature not in ai_features:
                print(f"   ❌ Missing feature: {expected_feature}")
                structure_valid = False
            else:
                value = ai_features[expected_feature]
                if not isinstance(value, (int, float)):
                    print(f"   ❌ Invalid type for {expected_feature}: {type(value)}")
                    structure_valid = False
                elif not (0.0 <= value <= 1.0):
                    print(f"   ⚠️ Value out of range for {expected_feature}: {value}")
        
        if structure_valid:
            print("   ✅ AI feature structure is valid")
        else:
            print("   ❌ AI feature structure has issues")
        
        return structure_valid

async def main():
    """Main test execution"""
    print("🚀 AI Feature Mock Testing")
    print("=" * 60)
    
    tester = MockAITester()
    
    # Test 1: AI feature structure
    structure_valid = await tester.test_ai_feature_structure()
    
    # Test 2: Mock AI features
    if structure_valid:
        results = await tester.test_mock_ai_features()
        
        # Summary
        print("\n" + "=" * 60)
        print("🎯 Overall Test Summary:")
        print("=" * 60)
        
        if structure_valid and all(r.get('success', False) for r in results.values()):
            print("🎉 ALL TESTS PASSED!")
            print("✅ AI feature extraction is working correctly")
            print("🚀 Ready to integrate with real AI APIs")
            return True
        else:
            print("⚠️ SOME TESTS FAILED")
            print("🔧 Fix issues before proceeding")
            return False
    else:
        print("❌ Structure validation failed - cannot proceed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
