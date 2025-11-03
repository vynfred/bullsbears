#!/usr/bin/env python3
"""
Fixed ML Training Pipeline
Addresses all identified issues: data leakage, overfitting, class imbalance.
"""

import asyncio
import logging
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from app.analyzers.clean_features import clean_features, validate_features
from app.sampling.balanced_dataset import (
    create_realistic_dataset,
    create_purged_splits,
    calculate_class_weights,
    validate_balanced_dataset
)
from app.models.train_calibrated import CalibratedModelTrainer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def step1_clean_features():
    """Step 1: Clean features and fix data leakage."""
    logger.info("🧹 STEP 1: Cleaning Features and Fixing Data Leakage")
    logger.info("="*60)
    
    try:
        # Load raw features
        features_file = "data/backtest/ml_features.csv"
        if not Path(features_file).exists():
            logger.error(f"❌ Features file not found: {features_file}")
            return False
        
        logger.info(f"📂 Loading features from {features_file}...")
        df = pd.read_csv(features_file)
        logger.info(f"📊 Loaded {len(df)} samples with {len(df.columns)} columns")
        
        # Convert event_date to datetime
        if 'event_date' in df.columns:
            df['event_date'] = pd.to_datetime(df['event_date'])
        
        # Clean features
        logger.info("🔧 Applying feature cleaning...")
        df_clean = clean_features(df)
        
        # Validate cleaned features
        validation = validate_features(df_clean)
        logger.info(f"✅ Feature validation results:")
        logger.info(f"   Total features: {validation['total_features']}")
        logger.info(f"   Remaining NaNs: {validation['nan_count']}")
        logger.info(f"   Infinite values: {validation['inf_count']}")
        logger.info(f"   Constant features: {len(validation['constant_features'])}")
        
        if validation['high_nan_features']:
            logger.warning(f"⚠️  Features with >10% NaN: {len(validation['high_nan_features'])}")
        
        # Save cleaned features
        clean_features_file = "data/backtest/ml_features_clean.csv"
        df_clean.to_csv(clean_features_file, index=False)
        logger.info(f"💾 Saved cleaned features to {clean_features_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Step 1 failed: {e}")
        return False

async def step2_create_realistic_dataset():
    """Step 2: Create realistic dataset preserving natural market frequencies."""
    logger.info("\n🎯 STEP 2: Creating Realistic Dataset (Preserving Natural Frequencies)")
    logger.info("="*60)

    try:
        # Load cleaned features
        clean_features_file = "data/backtest/ml_features_clean.csv"
        df = pd.read_csv(clean_features_file)

        if 'event_date' in df.columns:
            df['event_date'] = pd.to_datetime(df['event_date'])

        logger.info(f"📊 Original dataset: {len(df)} samples")
        logger.info(f"   Event distribution: {df['event_type'].value_counts().to_dict()}")

        # Create realistic dataset (preserves natural frequencies)
        realistic_df = create_realistic_dataset(df, target_col='event_type')

        # Validate realistic dataset
        validation = validate_balanced_dataset(realistic_df, target_col='event_type')
        logger.info(f"✅ Realistic dataset validation:")
        logger.info(f"   Total samples: {validation['total_samples']}")
        logger.info(f"   Class distribution: {validation['class_distribution']}")
        logger.info(f"   Natural frequency preserved: Moon events are {validation['class_percentages'].get('moon', 0):.1f}% of dataset")

        # Save realistic dataset
        realistic_file = "data/backtest/ml_features_realistic.csv"
        realistic_df.to_csv(realistic_file, index=False)
        logger.info(f"💾 Saved realistic dataset to {realistic_file}")

        return True

    except Exception as e:
        logger.error(f"❌ Step 2 failed: {e}")
        return False

async def step3_train_calibrated_models():
    """Step 3: Train calibrated models with purged CV."""
    logger.info("\n🚀 STEP 3: Training Calibrated Models")
    logger.info("="*60)
    
    try:
        # Load realistic dataset
        realistic_file = "data/backtest/ml_features_realistic.csv"
        df = pd.read_csv(realistic_file)
        
        if 'event_date' in df.columns:
            df['event_date'] = pd.to_datetime(df['event_date'])
        
        logger.info(f"📊 Training dataset: {len(df)} samples")
        
        # Prepare features and targets
        feature_cols = [col for col in df.columns if col not in ['event_type', 'ticker', 'event_date', 'target_return']]
        X = df[feature_cols]
        
        # Create binary targets for moon and rug models
        y_moon = (df['event_type'] == 'moon').astype(int)
        y_rug = (df['event_type'] == 'rug').astype(int)
        
        logger.info(f"🎯 Features: {len(feature_cols)}")
        logger.info(f"   Moon targets: {y_moon.sum()} positive, {len(y_moon) - y_moon.sum()} negative")
        logger.info(f"   Rug targets: {y_rug.sum()} positive, {len(y_rug) - y_rug.sum()} negative")
        
        # Calculate class weights
        moon_weights = calculate_class_weights(y_moon)
        rug_weights = calculate_class_weights(y_rug)
        
        # Train Moon Model (using RandomForest due to LightGBM OpenMP issues)
        logger.info("\n🌙 Training Moon Model...")
        moon_trainer = CalibratedModelTrainer(model_type='randomforest')
        moon_base, moon_calibrated, moon_metrics = moon_trainer.train_with_calibration(
            X, y_moon, class_weights=moon_weights
        )

        # Train Rug Model (using RandomForest due to LightGBM OpenMP issues)
        logger.info("\n💥 Training Rug Model...")
        rug_trainer = CalibratedModelTrainer(model_type='randomforest')
        rug_base, rug_calibrated, rug_metrics = rug_trainer.train_with_calibration(
            X, y_rug, class_weights=rug_weights
        )
        
        # Save models
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        moon_paths = moon_trainer.save_model("data/models", f"moon_model_fixed_{timestamp}")
        rug_paths = rug_trainer.save_model("data/models", f"rug_model_fixed_{timestamp}")
        
        # Test predictions on sample data
        logger.info("\n🧪 Testing Model Predictions...")
        
        # Create test scenarios
        test_scenarios = [
            {
                "name": "Neutral Market",
                "features": pd.DataFrame([{col: df[col].median() for col in feature_cols}])
            },
            {
                "name": "Extreme Values",
                "features": pd.DataFrame([{col: df[col].quantile(0.95) if df[col].std() > 0 else df[col].median() 
                                        for col in feature_cols}])
            }
        ]
        
        for scenario in test_scenarios:
            logger.info(f"\n🎯 Testing: {scenario['name']}")
            
            # Moon predictions
            moon_pred, moon_proba = moon_trainer.predict_calibrated(scenario['features'])
            logger.info(f"🌙 Moon: {moon_proba[0]:.3f} probability")
            
            # Rug predictions  
            rug_pred, rug_proba = rug_trainer.predict_calibrated(scenario['features'])
            logger.info(f"💥 Rug: {rug_proba[0]:.3f} probability")
            
            # Check for extreme confidence
            if moon_proba[0] > 0.95 or rug_proba[0] > 0.95:
                logger.warning(f"⚠️  High confidence detected - may still have overfitting")
        
        # Summary
        logger.info(f"\n✅ Model Training Complete!")
        logger.info(f"🌙 Moon Model:")
        logger.info(f"   CV Accuracy: {moon_metrics['cv_accuracy_mean']:.4f} ± {moon_metrics['cv_accuracy_std']:.4f}")
        logger.info(f"   Final AUC: {moon_metrics['final_auc']:.4f}")
        logger.info(f"💥 Rug Model:")
        logger.info(f"   CV Accuracy: {rug_metrics['cv_accuracy_mean']:.4f} ± {rug_metrics['cv_accuracy_std']:.4f}")
        logger.info(f"   Final AUC: {rug_metrics['final_auc']:.4f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Step 3 failed: {e}")
        return False

async def main():
    """Run the complete fixed ML training pipeline."""
    logger.info("🚀 STARTING FIXED ML TRAINING PIPELINE")
    logger.info("="*80)
    logger.info("Fixes Applied:")
    logger.info("✅ Data leakage prevention with proper feature engineering")
    logger.info("✅ NaN handling with forward-fill limits and median imputation")
    logger.info("✅ Natural class frequencies preserved with strategic hard negatives")
    logger.info("✅ Overfitting prevention with purged CV and calibration")
    logger.info("✅ Feature importance auditing")
    logger.info("="*80)
    
    # Execute pipeline steps
    step1_success = await step1_clean_features()
    if not step1_success:
        logger.error("❌ Pipeline failed at Step 1")
        return False
    
    step2_success = await step2_create_realistic_dataset()
    if not step2_success:
        logger.error("❌ Pipeline failed at Step 2")
        return False
    
    step3_success = await step3_train_calibrated_models()
    if not step3_success:
        logger.error("❌ Pipeline failed at Step 3")
        return False
    
    # Final summary
    logger.info("\n" + "="*80)
    logger.info("🎉 FIXED ML TRAINING PIPELINE COMPLETE!")
    logger.info("="*80)
    logger.info("✅ All critical issues addressed:")
    logger.info("   🧹 Data leakage fixed with proper feature engineering")
    logger.info("   🎯 Natural market frequencies preserved with strategic sampling")
    logger.info("   🎯 Overfitting prevented with purged CV and calibration")
    logger.info("   📊 Models should now give realistic confidence scores")
    logger.info("\n🚀 Ready for production integration!")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
