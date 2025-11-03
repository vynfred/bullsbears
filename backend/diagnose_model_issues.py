#!/usr/bin/env python3
"""
Diagnose ML Model Issues
Investigate why models are predicting 99%+ confidence on everything.
"""

import asyncio
import logging
import sys
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from app.services.model_loader import get_model_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def diagnose_model_predictions():
    """Diagnose why models are predicting extreme confidence."""
    logger.info("🔍 Diagnosing Model Prediction Issues...")
    
    try:
        # Load models directly
        moon_model = joblib.load("data/models/moon_model_v20251102_155922.joblib")
        rug_model = joblib.load("data/models/rug_model_v20251102_155922.joblib")
        
        logger.info(f"🌙 Moon model type: {type(moon_model)}")
        logger.info(f"💥 Rug model type: {type(rug_model)}")
        
        # Test with different feature scenarios
        scenarios = [
            {
                "name": "Neutral Market",
                "features": [50.0] * 38  # All neutral values
            },
            {
                "name": "Random Values",
                "features": np.random.normal(50, 10, 38).tolist()
            },
            {
                "name": "Extreme Bullish",
                "features": [100.0] * 38  # All extreme bullish
            },
            {
                "name": "Extreme Bearish", 
                "features": [0.0] * 38  # All extreme bearish
            },
            {
                "name": "Training Data Sample",
                "features": [9.21, 9.03, 9.44, 9.03, 435242.0, 1.045, 1.019, 8.592, 8.441, 0.0,
                           1.071, 1.090, 0.0, 62.646, 0.0, 0.0, 0.0, 0.0, 9.667, 8.592,
                           7.516, 0.787, 1041875.2, 0.417, 0.0, 0.473, 0.85, 0.70, 10.167,
                           8.225, 83.579, 72.902, 0.0, 0.0, 8.225, 0.823, 5.898, -0.110]
            }
        ]
        
        for scenario in scenarios:
            logger.info(f"\n🎯 Testing: {scenario['name']}")
            features = np.array(scenario['features']).reshape(1, -1)
            
            # Moon predictions
            try:
                moon_proba = moon_model.predict_proba(features)
                moon_pred = moon_model.predict(features)
                logger.info(f"🌙 Moon - Prediction: {moon_pred[0]}, Probabilities: {moon_proba[0]}")
            except Exception as e:
                logger.error(f"🌙 Moon prediction failed: {e}")
            
            # Rug predictions
            try:
                rug_proba = rug_model.predict_proba(features)
                rug_pred = rug_model.predict(features)
                logger.info(f"💥 Rug - Prediction: {rug_pred[0]}, Probabilities: {rug_proba[0]}")
            except Exception as e:
                logger.error(f"💥 Rug prediction failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Diagnosis failed: {e}")
        return False

async def analyze_training_data():
    """Analyze the training data for issues."""
    logger.info("📊 Analyzing Training Data...")
    
    try:
        # Load training data
        df = pd.read_csv("data/backtest/ml_features.csv")
        
        logger.info(f"📈 Training data shape: {df.shape}")
        logger.info(f"🎯 Event types: {df['event_type'].value_counts()}")
        
        # Check for data leakage indicators
        logger.info("\n🔍 Checking for potential data leakage...")
        
        # Check target return distribution
        logger.info(f"📊 Target return stats:")
        logger.info(f"   Moon returns: {df[df['event_type'] == 'moon']['target_return'].describe()}")
        logger.info(f"   Rug returns: {df[df['event_type'] == 'rug']['target_return'].describe()}")
        
        # Check for suspicious feature patterns
        feature_cols = [col for col in df.columns if col not in ['ticker', 'event_type', 'target_return', 'event_date']]
        
        logger.info(f"\n📋 Feature analysis:")
        logger.info(f"   Total features: {len(feature_cols)}")
        logger.info(f"   Features with NaN: {df[feature_cols].isnull().sum().sum()}")
        logger.info(f"   Features with zeros: {(df[feature_cols] == 0).sum().sum()}")
        
        # Check feature distributions
        logger.info(f"\n📈 Feature value ranges:")
        for col in feature_cols[:10]:  # First 10 features
            logger.info(f"   {col}: {df[col].min():.3f} to {df[col].max():.3f}")
        
        # Check class balance
        moon_count = len(df[df['event_type'] == 'moon'])
        rug_count = len(df[df['event_type'] == 'rug'])
        logger.info(f"\n⚖️  Class balance:")
        logger.info(f"   Moon events: {moon_count} ({moon_count/len(df)*100:.1f}%)")
        logger.info(f"   Rug events: {rug_count} ({rug_count/len(df)*100:.1f}%)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Training data analysis failed: {e}")
        return False

async def test_feature_importance():
    """Test feature importance to understand model behavior."""
    logger.info("🎯 Analyzing Feature Importance...")
    
    try:
        # Load models
        moon_model = joblib.load("data/models/moon_model_v20251102_155922.joblib")
        
        # Get feature importance
        if hasattr(moon_model, 'feature_importances_'):
            importances = moon_model.feature_importances_
            
            # Load feature names
            import json
            with open("data/models/moon_metadata_v20251102_155922.json", 'r') as f:
                metadata = json.load(f)
            
            feature_names = metadata['selected_features']
            
            # Sort by importance
            feature_importance = list(zip(feature_names, importances))
            feature_importance.sort(key=lambda x: x[1], reverse=True)
            
            logger.info("🔝 Top 10 Most Important Features:")
            for i, (feature, importance) in enumerate(feature_importance[:10]):
                logger.info(f"   {i+1}. {feature}: {importance:.4f}")
            
            # Check if any features have extreme importance
            max_importance = max(importances)
            if max_importance > 0.5:
                logger.warning(f"⚠️  Extremely high feature importance detected: {max_importance:.4f}")
                logger.warning("   This could indicate overfitting or data leakage")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Feature importance analysis failed: {e}")
        return False

async def main():
    """Run all diagnostic tests."""
    logger.info("🚨 Starting Model Diagnostic Analysis...")
    
    # Test 1: Model Predictions
    pred_success = await diagnose_model_predictions()
    
    # Test 2: Training Data Analysis
    data_success = await analyze_training_data()
    
    # Test 3: Feature Importance
    importance_success = await test_feature_importance()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("🚨 DIAGNOSTIC RESULTS SUMMARY")
    logger.info("="*60)
    logger.info(f"🔮 Model Predictions: {'✅ ANALYZED' if pred_success else '❌ FAILED'}")
    logger.info(f"📊 Training Data: {'✅ ANALYZED' if data_success else '❌ FAILED'}")
    logger.info(f"🎯 Feature Importance: {'✅ ANALYZED' if importance_success else '❌ FAILED'}")
    
    overall_success = pred_success and data_success and importance_success
    
    if overall_success:
        logger.info("\n🔍 DIAGNOSIS COMPLETE - Check results above for issues")
        logger.info("⚠️  If models predict 99%+ on everything, we have overfitting!")
    else:
        logger.info("\n❌ DIAGNOSIS INCOMPLETE - Some tests failed")
    
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
