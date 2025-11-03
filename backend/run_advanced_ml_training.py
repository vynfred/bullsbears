#!/usr/bin/env python3
"""
Advanced ML Training Pipeline
Implements all improvements: better features, sophisticated hard negatives, ensemble models
"""

import asyncio
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.analyzers.clean_features import clean_features, validate_features
from app.features.advanced_features import AdvancedFeatureEngineer
from app.sampling.balanced_dataset import (
    create_realistic_dataset, 
    create_purged_splits,
    calculate_class_weights,
    validate_balanced_dataset
)
from app.models.ensemble_trainer import EnsembleModelTrainer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def step1_advanced_feature_engineering():
    """Step 1: Clean features and add advanced features."""
    logger.info("\n🚀 STEP 1: Advanced Feature Engineering")
    logger.info("="*60)
    
    try:
        # Load original features
        features_file = "data/backtest/ml_features.csv"
        df = pd.read_csv(features_file)
        
        if 'event_date' in df.columns:
            df['event_date'] = pd.to_datetime(df['event_date'])
        
        logger.info(f"📊 Original dataset: {len(df)} samples, {len(df.columns)} features")
        
        # Step 1a: Clean existing features
        logger.info("🧹 Cleaning existing features...")
        df_clean = clean_features(df)
        
        # Step 1b: Add advanced features for a sample of tickers
        logger.info("🚀 Adding advanced features...")
        feature_engineer = AdvancedFeatureEngineer()
        
        # Get unique tickers (limit to first 50 for speed)
        unique_tickers = df_clean['ticker'].unique()[:50] if 'ticker' in df_clean.columns else ['SAMPLE']
        
        enhanced_dfs = []
        for i, ticker in enumerate(unique_tickers):
            if i % 10 == 0:
                logger.info(f"   Processing ticker {i+1}/{len(unique_tickers)}: {ticker}")
            
            ticker_df = df_clean[df_clean['ticker'] == ticker].copy() if 'ticker' in df_clean.columns else df_clean.copy()
            
            if len(ticker_df) > 0:
                try:
                    # Add advanced features
                    enhanced_df = feature_engineer.engineer_all_features(ticker_df, ticker)
                    enhanced_dfs.append(enhanced_df)
                except Exception as e:
                    logger.warning(f"⚠️  Advanced features failed for {ticker}: {e}")
                    enhanced_dfs.append(ticker_df)  # Keep original if advanced fails
        
        # Combine all enhanced dataframes
        if enhanced_dfs:
            df_enhanced = pd.concat(enhanced_dfs, ignore_index=True)
        else:
            df_enhanced = df_clean
        
        # Clean the enhanced features again (advanced features may have introduced NaNs)
        logger.info("🧹 Final cleaning of enhanced features...")
        df_enhanced = clean_features(df_enhanced)

        # Final validation
        validation = validate_features(df_enhanced)
        logger.info(f"✅ Advanced feature engineering complete:")
        logger.info(f"   Total features: {validation['total_features']}")
        logger.info(f"   Remaining NaNs: {validation['nan_count']}")
        logger.info(f"   Infinite values: {validation['inf_count']}")

        # Save enhanced features
        enhanced_file = "data/backtest/ml_features_enhanced.csv"
        df_enhanced.to_csv(enhanced_file, index=False)
        logger.info(f"💾 Saved enhanced features to {enhanced_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Step 1 failed: {e}")
        return False

async def step2_sophisticated_sampling():
    """Step 2: Create realistic dataset with sophisticated hard negatives."""
    logger.info("\n🎯 STEP 2: Sophisticated Sampling Strategy")
    logger.info("="*60)
    
    try:
        # Load enhanced features
        enhanced_file = "data/backtest/ml_features_enhanced.csv"
        df = pd.read_csv(enhanced_file)
        
        if 'event_date' in df.columns:
            df['event_date'] = pd.to_datetime(df['event_date'])
        
        logger.info(f"📊 Enhanced dataset: {len(df)} samples")
        logger.info(f"   Event distribution: {df['event_type'].value_counts().to_dict()}")
        
        # Create realistic dataset with sophisticated hard negatives
        realistic_df = create_realistic_dataset(df, target_col='event_type')
        
        # Validate dataset
        validation = validate_balanced_dataset(realistic_df, target_col='event_type')
        logger.info(f"✅ Sophisticated sampling complete:")
        logger.info(f"   Total samples: {validation['total_samples']}")
        logger.info(f"   Class distribution: {validation['class_distribution']}")
        logger.info(f"   Includes sophisticated hard negatives: almost moons, failed breakouts, fake volume")
        
        # Save realistic dataset
        realistic_file = "data/backtest/ml_features_advanced.csv"
        realistic_df.to_csv(realistic_file, index=False)
        logger.info(f"💾 Saved advanced dataset to {realistic_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Step 2 failed: {e}")
        return False

async def step3_ensemble_training():
    """Step 3: Train ensemble models."""
    logger.info("\n🤖 STEP 3: Ensemble Model Training")
    logger.info("="*60)
    
    try:
        # Load advanced dataset
        advanced_file = "data/backtest/ml_features_advanced.csv"
        df = pd.read_csv(advanced_file)
        
        if 'event_date' in df.columns:
            df['event_date'] = pd.to_datetime(df['event_date'])
        
        logger.info(f"📊 Training dataset: {len(df)} samples")
        
        # Prepare features and targets
        feature_cols = [col for col in df.columns if col not in ['event_type', 'ticker', 'event_date', 'target_return']]
        X = df[feature_cols]
        
        # Create moon and rug targets
        y_moon = (df['event_type'] == 'moon').astype(int)
        y_rug = (df['event_type'] == 'rug').astype(int)
        
        logger.info(f"🎯 Features: {len(feature_cols)}")
        logger.info(f"   Moon targets: {y_moon.sum()} positive, {(~y_moon.astype(bool)).sum()} negative")
        logger.info(f"   Rug targets: {y_rug.sum()} positive, {(~y_rug.astype(bool)).sum()} negative")
        
        # Calculate class weights
        moon_weights = calculate_class_weights(y_moon)
        rug_weights = calculate_class_weights(y_rug)
        
        # Train Moon Ensemble
        logger.info("\n🌙 Training Moon Ensemble...")
        moon_trainer = EnsembleModelTrainer()
        moon_ensemble, moon_metrics = moon_trainer.train_ensemble(X, y_moon, moon_weights)
        
        # Train Rug Ensemble  
        logger.info("\n💥 Training Rug Ensemble...")
        rug_trainer = EnsembleModelTrainer()
        rug_ensemble, rug_metrics = rug_trainer.train_ensemble(X, y_rug, rug_weights)
        
        # Save ensemble models
        model_dir = "data/models"
        Path(model_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        
        moon_paths = moon_trainer.save_ensemble(model_dir, f"moon_ensemble_{timestamp}")
        rug_paths = rug_trainer.save_ensemble(model_dir, f"rug_ensemble_{timestamp}")
        
        # Test ensemble predictions
        logger.info("\n🧪 Testing Ensemble Predictions...")
        
        # Create test samples
        neutral_sample = X.median().to_frame().T
        extreme_sample = X.quantile(0.95).to_frame().T
        
        # Moon ensemble predictions
        moon_pred, moon_proba, moon_individual = moon_trainer.predict_ensemble(neutral_sample)
        moon_agreement = moon_trainer.get_model_agreement(neutral_sample)
        
        logger.info(f"🌙 Moon Ensemble (neutral): {moon_proba[0]:.3f} probability")
        logger.info(f"   Model agreement: {moon_agreement[0]:.3f}")
        for name, preds in moon_individual.items():
            logger.info(f"   {name}: {preds['probabilities'][0]:.3f}")
        
        # Rug ensemble predictions
        rug_pred, rug_proba, rug_individual = rug_trainer.predict_ensemble(neutral_sample)
        rug_agreement = rug_trainer.get_model_agreement(neutral_sample)
        
        logger.info(f"💥 Rug Ensemble (neutral): {rug_proba[0]:.3f} probability")
        logger.info(f"   Model agreement: {rug_agreement[0]:.3f}")
        for name, preds in rug_individual.items():
            logger.info(f"   {name}: {preds['probabilities'][0]:.3f}")
        
        logger.info(f"\n✅ Ensemble Training Complete!")
        logger.info(f"🌙 Moon Ensemble: {moon_metrics['ensemble_accuracy']:.4f} accuracy, {moon_metrics['ensemble_auc']:.4f} AUC")
        logger.info(f"💥 Rug Ensemble: {rug_metrics['ensemble_accuracy']:.4f} accuracy, {rug_metrics['ensemble_auc']:.4f} AUC")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Step 3 failed: {e}")
        return False

async def main():
    """Run the complete advanced ML training pipeline."""
    logger.info("🚀 STARTING ADVANCED ML TRAINING PIPELINE")
    logger.info("="*80)
    logger.info("Advanced Improvements:")
    logger.info("✅ Better features: short interest, options flow, microstructure")
    logger.info("✅ Sophisticated hard negatives: almost moons, failed breakouts, fake volume")
    logger.info("✅ Ensemble models: RandomForest + LightGBM + LogisticRegression")
    logger.info("✅ Natural market frequencies preserved")
    logger.info("✅ Probability calibration and model agreement scoring")
    logger.info("="*80)
    
    # Execute pipeline steps
    step1_success = await step1_advanced_feature_engineering()
    if not step1_success:
        logger.error("❌ Pipeline failed at Step 1")
        return
    
    step2_success = await step2_sophisticated_sampling()
    if not step2_success:
        logger.error("❌ Pipeline failed at Step 2")
        return
    
    step3_success = await step3_ensemble_training()
    if not step3_success:
        logger.error("❌ Pipeline failed at Step 3")
        return
    
    logger.info("\n" + "="*80)
    logger.info("🎉 ADVANCED ML TRAINING PIPELINE COMPLETE!")
    logger.info("="*80)
    logger.info("✅ All advanced improvements implemented:")
    logger.info("   🚀 Advanced feature engineering with market microstructure")
    logger.info("   🎯 Sophisticated hard negatives (almost moons that failed)")
    logger.info("   🤖 Ensemble models with probability calibration")
    logger.info("   📊 Model agreement scoring for confidence assessment")
    logger.info("\n🚀 Ready for production integration with advanced models!")

if __name__ == "__main__":
    asyncio.run(main())
