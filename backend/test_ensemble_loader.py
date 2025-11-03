#!/usr/bin/env python3
"""
Test script for ensemble model loading
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def test_ensemble_models():
    """Test loading and using ensemble models."""
    print("🚀 Testing Ensemble Model Loading...")
    
    try:
        from app.services.model_loader import ModelLoader
        print("✅ ModelLoader imported successfully")
        
        # Create loader instance
        loader = ModelLoader()
        print("✅ ModelLoader instance created")
        
        # Check if ensemble files exist
        models_dir = backend_dir / "data" / "models"
        ensemble_files = list(models_dir.glob("*ensemble*.joblib"))
        print(f"📁 Found {len(ensemble_files)} ensemble files")
        
        if not ensemble_files:
            print("❌ No ensemble files found!")
            return False
        
        # Load models
        print("📥 Loading models...")
        success = await loader.load_models()
        
        if not success:
            print("❌ Failed to load models")
            return False
        
        print("✅ Models loaded successfully!")
        
        # Get health status
        health = loader.get_model_health()
        print(f"📊 Health Check:")
        print(f"   Models loaded: {health['models_loaded']}")
        print(f"   Confidence threshold: {health['confidence_threshold']:.0%}")
        
        # Check each model
        for model_type in ['moon', 'rug']:
            model_health = health.get(f'{model_type}_model', {})
            if model_health.get('loaded'):
                print(f"\n🎯 {model_type.title()} Model:")
                print(f"   Type: {'Ensemble' if model_health.get('is_ensemble') else 'Single'}")
                print(f"   Version: {model_health.get('version', 'unknown')}")
                print(f"   Accuracy: {model_health.get('accuracy', 0):.1%}")
                print(f"   Features: {model_health.get('features_count', 0)}")
                
                if model_health.get('is_ensemble'):
                    print(f"   Base Models: {model_health.get('base_models', [])}")
                    individual_acc = model_health.get('individual_accuracies', {})
                    for name, acc in individual_acc.items():
                        print(f"     {name}: {acc:.1%}")
            else:
                print(f"❌ {model_type.title()} model not loaded")
        
        # Test predictions with realistic features
        print("\n🧪 Testing Predictions...")
        
        # Create dummy features matching the expected 74 features
        dummy_features = {
            'close': 100.0, 'open': 99.0, 'high': 101.0, 'low': 98.0, 'volume': 1000000.0,
            'high_low_ratio': 1.03, 'close_open_ratio': 1.01, 'sma_5': 99.5, 'sma_10': 99.0, 'sma_20': 98.5,
            'close_sma5_ratio': 1.005, 'close_sma10_ratio': 1.01, 'rsi_14': 55.0, 'rsi_7': 60.0,
            'macd': 0.5, 'macd_signal': 0.3, 'macd_histogram': 0.2, 'bb_upper': 102.0, 'bb_middle': 100.0, 'bb_lower': 98.0,
            'bb_position': 0.5, 'volume_sma_10': 900000.0, 'volume_ratio': 1.1, 'atr_14': 2.0, 'volatility_10': 0.02,
            'momentum_5': 0.01, 'momentum_10': 0.015, 'roc_5': 1.0, 'roc_10': 1.5, 'stoch_k': 60.0, 'stoch_d': 55.0,
            'williams_r': -40.0, 'cci': 50.0, 'price_trend_pct': 0.01, 'volume_trend': 0.1, 'recent_volatility': 0.02,
            'gap_pct': 0.005
        }
        
        # Add NaN indicator features (all False for clean data)
        nan_features = ['sma_20_isnan', 'rsi_14_isnan', 'rsi_7_isnan', 'macd_isnan', 'macd_signal_isnan', 
                       'macd_histogram_isnan', 'bb_upper_isnan', 'bb_middle_isnan', 'bb_lower_isnan',
                       'stoch_k_isnan', 'stoch_d_isnan', 'williams_r_isnan', 'cci_isnan', 'atr_14_isnan', 'volume_ratio_isnan']
        for feature in nan_features:
            dummy_features[feature] = 0.0
        
        # Add advanced features (set to neutral values)
        advanced_features = {
            'close_sma20_ratio': 1.015, 'short_ratio': 0.0, 'short_percent_float': 0.0, 'shares_short': 0.0,
            'shares_short_prior': 0.0, 'short_interest_change': 0.0, 'days_to_cover': 0.0, 'squeeze_potential': 0.0,
            'put_call_ratio': 0.0, 'options_stock_volume_ratio': 0.1, 'unusual_call_activity': 0.0, 'unusual_put_activity': 0.0,
            'gamma_exposure_proxy': 0.0, 'intraday_spread': 0.01, 'price_impact': 0.02, 'liquidity_proxy': 0.8,
            'buying_pressure': 0.5, 'selling_pressure': 0.5, 'net_order_flow': 0.0, 'momentum_sentiment': 0.5,
            'trend_strength': 0.0, 'fear_greed_proxy': 0.0
        }
        dummy_features.update(advanced_features)
        
        print(f"📊 Using {len(dummy_features)} features for prediction")
        
        # Test moon prediction
        moon_conf, moon_details = await loader.predict_moon(dummy_features)
        print(f"\n🌙 Moon Prediction:")
        print(f"   Confidence: {moon_conf:.3f}")
        print(f"   Above threshold: {moon_details.get('above_threshold', False)}")
        print(f"   Is ensemble: {moon_details.get('is_ensemble', False)}")
        
        if moon_details.get('is_ensemble'):
            print(f"   Model agreement: {moon_details.get('model_agreement', 0):.3f}")
            individual_preds = moon_details.get('individual_predictions', {})
            for name, pred in individual_preds.items():
                print(f"     {name}: {pred:.3f}")
        
        # Test rug prediction
        rug_conf, rug_details = await loader.predict_rug(dummy_features)
        print(f"\n💥 Rug Prediction:")
        print(f"   Confidence: {rug_conf:.3f}")
        print(f"   Above threshold: {rug_details.get('above_threshold', False)}")
        print(f"   Is ensemble: {rug_details.get('is_ensemble', False)}")
        
        if rug_details.get('is_ensemble'):
            print(f"   Model agreement: {rug_details.get('model_agreement', 0):.3f}")
            individual_preds = rug_details.get('individual_predictions', {})
            for name, pred in individual_preds.items():
                print(f"     {name}: {pred:.3f}")
        
        print("\n🎉 Ensemble model testing complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ensemble_models())
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed!")
        sys.exit(1)
