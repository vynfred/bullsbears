#!/usr/bin/env python3
"""
Test RandomForest Only
Quick test to create RandomForest-only models to test predictions without LogisticRegression
"""

import sys
import os
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, roc_auc_score

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

def train_rf_only(X, y, model_type):
    """Train RandomForest only model"""
    print(f"\n🌲 Training {model_type} RandomForest (ONLY)...")
    
    # Create RandomForest model
    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    
    # Calibrate the model
    calibrated_rf = CalibratedClassifierCV(
        rf_model,
        method='isotonic',
        cv=3
    )
    
    # Train
    print("   Training RandomForest...")
    calibrated_rf.fit(X, y)
    
    # Evaluate
    y_pred = calibrated_rf.predict(X)
    y_proba = calibrated_rf.predict_proba(X)
    
    accuracy = accuracy_score(y, y_pred)
    auc = roc_auc_score(y, y_proba[:, 1])
    
    print(f"   ✅ Training accuracy: {accuracy:.1%}")
    print(f"   ✅ Training AUC: {auc:.3f}")
    
    # Save models
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = Path('/Users/vynfred/Documents/bullsbears/backend/data/models')
    
    # Save RandomForest model
    rf_file = model_dir / f"{model_type}_rf_only_{timestamp}.joblib"
    joblib.dump(calibrated_rf, rf_file)
    print(f"   💾 Saved RandomForest: {rf_file.name}")
    
    # Save metadata
    metadata = {
        "model_type": "single_model",
        "model_name": "random_forest_calibrated",
        "feature_names": list(X.columns),
        "training_metrics": {
            "accuracy": float(accuracy),
            "auc": float(auc),
            "samples": len(X)
        },
        "timestamp": timestamp,
        "note": "RandomForest only - no LogisticRegression"
    }
    
    metadata_file = model_dir / f"{model_type}_rf_only_{timestamp}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"   💾 Saved metadata: {metadata_file.name}")
    
    return calibrated_rf, metadata

def main():
    """Main training execution"""
    print("🚀 Training RandomForest Only Models...")
    print("=" * 60)
    
    # Load data
    X_moon, y_moon, X_rug, y_rug = load_training_data()
    
    if X_moon is None:
        print("❌ Cannot load training data")
        return False
    
    try:
        # Train moon RandomForest
        moon_rf, moon_metadata = train_rf_only(X_moon, y_moon, 'moon')
        
        # Train rug RandomForest
        rug_rf, rug_metadata = train_rf_only(X_rug, y_rug, 'rug')
        
        print("\n" + "=" * 60)
        print("🎉 RandomForest Training Complete!")
        print(f"✅ Moon RandomForest: {moon_metadata['training_metrics']['accuracy']:.1%} accuracy")
        print(f"✅ Rug RandomForest: {rug_metadata['training_metrics']['accuracy']:.1%} accuracy")
        print("✅ Ready to test predictions with RandomForest only!")
        
        return True
        
    except Exception as e:
        print(f"❌ Training failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
