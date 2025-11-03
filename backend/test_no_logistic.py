#!/usr/bin/env python3
"""
Test Ensemble Without LogisticRegression
Quick test to retrain ensemble with only RandomForest + LightGBM
"""

import sys
import os
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, roc_auc_score
import lightgbm as lgb

# Add backend to path
sys.path.append('/Users/vynfred/Documents/bullsbears/backend')

def load_training_data():
    """Load the training data"""
    print("📊 Loading training data...")
    
    # Load moon data
    moon_file = Path('/Users/vynfred/Documents/bullsbears/backend/data/training/moon_training_data_20241102.csv')
    rug_file = Path('/Users/vynfred/Documents/bullsbears/backend/data/training/rug_training_data_20241102.csv')
    
    if not moon_file.exists() or not rug_file.exists():
        print("❌ Training data files not found")
        return None, None, None, None
    
    moon_data = pd.read_csv(moon_file)
    rug_data = pd.read_csv(rug_file)
    
    print(f"   Moon data: {len(moon_data)} samples")
    print(f"   Rug data: {len(rug_data)} samples")
    
    # Prepare features and targets
    feature_cols = [col for col in moon_data.columns if col not in ['target', 'ticker', 'date']]
    
    X_moon = moon_data[feature_cols]
    y_moon = moon_data['target']
    X_rug = rug_data[feature_cols]
    y_rug = rug_data['target']
    
    print(f"   Features: {len(feature_cols)}")
    
    return X_moon, y_moon, X_rug, y_rug

def create_models_no_logistic():
    """Create ensemble models without LogisticRegression"""
    print("🤖 Creating models (NO LogisticRegression)...")
    
    models = {}
    
    # Model 1: Random Forest
    models['random_forest'] = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    
    # Model 2: LightGBM
    models['lightgbm'] = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=10,
        learning_rate=0.1,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight='balanced',
        random_state=42,
        verbose=-1
    )
    
    print(f"   Created {len(models)} models: {list(models.keys())}")
    return models

def train_ensemble_no_logistic(X, y, model_type):
    """Train ensemble without LogisticRegression"""
    print(f"\n🚀 Training {model_type} ensemble (NO LogisticRegression)...")
    
    # Create models
    models = create_models_no_logistic()
    
    # Create voting classifier
    voting_models = [(name, model) for name, model in models.items()]
    ensemble = VotingClassifier(
        estimators=voting_models,
        voting='soft'
    )
    
    # Calibrate the ensemble
    calibrated_ensemble = CalibratedClassifierCV(
        ensemble,
        method='isotonic',
        cv=3
    )
    
    # Train
    print("   Training ensemble...")
    calibrated_ensemble.fit(X, y)
    
    # Evaluate
    y_pred = calibrated_ensemble.predict(X)
    y_proba = calibrated_ensemble.predict_proba(X)
    
    accuracy = accuracy_score(y, y_pred)
    auc = roc_auc_score(y, y_proba[:, 1])
    
    print(f"   ✅ Training accuracy: {accuracy:.1%}")
    print(f"   ✅ Training AUC: {auc:.3f}")
    
    # Save models
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = Path('/Users/vynfred/Documents/bullsbears/backend/data/models')
    
    # Save ensemble
    ensemble_file = model_dir / f"{model_type}_ensemble_{timestamp}_no_logistic.joblib"
    joblib.dump(calibrated_ensemble, ensemble_file)
    print(f"   💾 Saved ensemble: {ensemble_file.name}")
    
    # Save individual models
    individual_models = {}
    for name, model in models.items():
        model.fit(X, y)  # Train individual model
        model_file = model_dir / f"{model_type}_ensemble_{timestamp}_{name}.joblib"
        joblib.dump(model, model_file)
        individual_models[name] = model
        print(f"   💾 Saved {name}: {model_file.name}")
    
    # Save metadata
    metadata = {
        "model_type": "ensemble",
        "ensemble_type": "soft_voting_calibrated_no_logistic",
        "base_models": list(models.keys()),
        "feature_names": list(X.columns),
        "training_metrics": {
            "accuracy": float(accuracy),
            "auc": float(auc),
            "samples": len(X)
        },
        "timestamp": timestamp,
        "removed_models": ["logistic"]
    }
    
    metadata_file = model_dir / f"{model_type}_ensemble_{timestamp}_no_logistic_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"   💾 Saved metadata: {metadata_file.name}")
    
    return calibrated_ensemble, individual_models, metadata

def main():
    """Main training execution"""
    print("🚀 Training Ensemble Without LogisticRegression...")
    print("=" * 60)
    
    # Load data
    X_moon, y_moon, X_rug, y_rug = load_training_data()
    
    if X_moon is None:
        print("❌ Cannot load training data")
        return False
    
    try:
        # Train moon ensemble
        moon_ensemble, moon_models, moon_metadata = train_ensemble_no_logistic(X_moon, y_moon, 'moon')
        
        # Train rug ensemble
        rug_ensemble, rug_models, rug_metadata = train_ensemble_no_logistic(X_rug, y_rug, 'rug')
        
        print("\n" + "=" * 60)
        print("🎉 Ensemble Training Complete (NO LogisticRegression)!")
        print(f"✅ Moon ensemble: {moon_metadata['training_metrics']['accuracy']:.1%} accuracy")
        print(f"✅ Rug ensemble: {rug_metadata['training_metrics']['accuracy']:.1%} accuracy")
        print("✅ Ready to test predictions without LogisticRegression!")
        
        return True
        
    except Exception as e:
        print(f"❌ Training failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
