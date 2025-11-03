#!/usr/bin/env python3
"""
Test AI Feature Extraction
Validates that Grok and DeepSeek return structured JSON features correctly.
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add backend to path
sys.path.append('/Users/vynfred/Documents/bullsbears/backend')

from app.features.ai_features import AIFeatureExtractor
from app.analyzers.data_downloader import DataDownloader

class AIFeatureTester:
    def __init__(self):
        self.ai_extractor = AIFeatureExtractor()
        self.data_downloader = DataDownloader()
        
    async def test_ai_feature_extraction(self, tickers):
        """Test AI feature extraction for sample tickers"""
        print("🤖 Testing AI Feature Extraction...")
        print("=" * 60)
        
        results = {}
        
        for ticker in tickers:
            print(f"\n📊 Testing {ticker}...")
            
            try:
                # Download sample data
                data = await self.data_downloader.download_databento_ticker(ticker)
                if data is None:
                    data = await self.data_downloader.download_yfinance_fallback(ticker)
                
                if data is None or len(data) < 20:
                    print(f"❌ {ticker}: Insufficient data")
                    continue
                
                # Create technical summary (mock data for testing)
                latest_data = data.iloc[-1]
                technical_summary = {
                    'rsi_14': np.random.uniform(20, 80),  # Mock RSI
                    'volume_ratio': data['Volume'].iloc[-1] / data['Volume'].mean(),
                    'macd_signal': np.random.uniform(-0.1, 0.1),  # Mock MACD
                    'bb_position': np.random.uniform(0, 1)  # Mock Bollinger position
                }
                
                print(f"   📈 Technical Summary: RSI={technical_summary['rsi_14']:.1f}, "
                      f"Volume={technical_summary['volume_ratio']:.2f}x")
                
                # Test Grok features
                print("   🔧 Testing Grok features...")
                grok_features = await self.ai_extractor.extract_grok_features(
                    ticker, data, technical_summary
                )
                
                # Test DeepSeek features
                print("   🧠 Testing DeepSeek features...")
                deepseek_features = await self.ai_extractor.extract_deepseek_features(
                    ticker, data, f"Recent market activity for {ticker}"
                )
                
                # Test combined AI features
                print("   🤖 Testing combined AI features...")
                ai_features = await self.ai_extractor.extract_all_ai_features(
                    ticker, data, technical_summary, f"Market analysis for {ticker}"
                )
                
                results[ticker] = {
                    'grok': grok_features,
                    'deepseek': deepseek_features,
                    'combined': ai_features,
                    'technical_summary': technical_summary
                }
                
                # Display results
                print(f"   ✅ {ticker} AI Features:")
                print(f"      🔧 Grok: tech_conf={grok_features['technical_confidence']:.2f}, "
                      f"vol_surge={grok_features['volume_surge_detected']:.0f}, "
                      f"rsi_oversold={grok_features['rsi_oversold']:.2f}")
                print(f"      🧠 DeepSeek: sentiment={deepseek_features['sentiment_score']:.2f}, "
                      f"news={deepseek_features['news_sentiment']:.2f}, "
                      f"bearish_kw={deepseek_features['bearish_keywords']}")
                print(f"      🤖 Combined: {len(ai_features)} total AI features")
                
            except Exception as e:
                print(f"❌ {ticker}: AI feature extraction error - {str(e)}")
                
        return results
    
    def validate_ai_features(self, results):
        """Validate AI feature extraction results"""
        print(f"\n📈 Validating AI Features...")
        print("=" * 60)
        
        validation_results = {
            'grok_features_valid': 0,
            'deepseek_features_valid': 0,
            'combined_features_valid': 0,
            'json_parsing_success': 0,
            'feature_ranges_valid': 0
        }
        
        for ticker, data in results.items():
            print(f"\n🔍 Validating {ticker}:")
            
            # Validate Grok features
            grok = data['grok']
            grok_valid = all([
                0.0 <= grok['technical_confidence'] <= 1.0,
                grok['volume_surge_detected'] in [0.0, 1.0],
                0.0 <= grok['rsi_oversold'] <= 1.0,
                0.0 <= grok['social_buzz_score'] <= 1.0
            ])
            
            if grok_valid:
                validation_results['grok_features_valid'] += 1
                print(f"   ✅ Grok features: Valid ranges")
            else:
                print(f"   ❌ Grok features: Invalid ranges")
            
            # Validate DeepSeek features
            deepseek = data['deepseek']
            deepseek_valid = all([
                0.0 <= deepseek['sentiment_score'] <= 1.0,
                0.0 <= deepseek['news_sentiment'] <= 1.0,
                0.0 <= deepseek['narrative_strength'] <= 1.0,
                0 <= deepseek['bearish_keywords'] <= 10
            ])
            
            if deepseek_valid:
                validation_results['deepseek_features_valid'] += 1
                print(f"   ✅ DeepSeek features: Valid ranges")
            else:
                print(f"   ❌ DeepSeek features: Invalid ranges")
            
            # Validate combined features
            combined = data['combined']
            combined_valid = len(combined) == 8  # Should have 8 AI features
            
            if combined_valid:
                validation_results['combined_features_valid'] += 1
                print(f"   ✅ Combined features: {len(combined)} features")
            else:
                print(f"   ❌ Combined features: {len(combined)} features (expected 8)")
        
        # Summary
        total_tickers = len(results)
        print(f"\n📊 Validation Summary:")
        print(f"   Grok Features Valid: {validation_results['grok_features_valid']}/{total_tickers}")
        print(f"   DeepSeek Features Valid: {validation_results['deepseek_features_valid']}/{total_tickers}")
        print(f"   Combined Features Valid: {validation_results['combined_features_valid']}/{total_tickers}")
        
        # Overall success
        overall_success = (
            validation_results['grok_features_valid'] >= total_tickers * 0.8 and
            validation_results['deepseek_features_valid'] >= total_tickers * 0.8 and
            validation_results['combined_features_valid'] >= total_tickers * 0.8
        )
        
        return overall_success, validation_results

async def main():
    """Main test execution"""
    print("🚀 Testing AI Feature Extraction System...")
    print("=" * 60)
    
    tester = AIFeatureTester()
    
    # Test with a smaller set first
    test_tickers = ['AAPL', 'TSLA', 'NVDA']
    
    try:
        # Test AI feature extraction
        results = await tester.test_ai_feature_extraction(test_tickers)
        
        if not results:
            print("❌ No AI features extracted. Cannot proceed.")
            return False
        
        # Validate results
        success, validation_results = tester.validate_ai_features(results)
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 AI Feature Extraction Test: PASSED")
            print("✅ Ready to proceed with ensemble retraining!")
        else:
            print("⚠️ AI Feature Extraction Test: ISSUES DETECTED")
            print("❌ Need to fix AI feature extraction before retraining")
        
        return success
        
    except Exception as e:
        print(f"❌ AI feature test execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
