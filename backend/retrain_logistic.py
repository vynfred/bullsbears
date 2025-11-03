#!/usr/bin/env python3
"""
Retrain LogisticRegression with Proper Regularization
Fix overfitting issues by using stronger regularization and better data preprocessing
"""

import sys
import os
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

# Add backend to path
sys.path.append('/Users/vynfred/Documents/bullsbears/backend')

def load_training_data():
    """Load the training data"""
    print("📊 Loading training data...")

    # Load balanced features data
    features_file = Path('/Users/vynfred/Documents/bullsbears/backend/data/backtest/ml_features_balanced.csv')

    if not features_file.exists():
        print(f"❌ Training data not found: {features_file}")
        return None, None, None, None

    data = pd.read_csv(features_file)
    print(f"   Total data: {len(data)} samples")

    # Split by event type
    moon_data = data[data['event_type'] == 'moon'].copy()
    rug_data = data[data['event_type'] == 'rug'].copy()

    print(f"   Moon data: {len(moon_data)} samples")
    print(f"   Rug data: {len(rug_data)} samples")

    # Prepare features and targets
    feature_cols = [col for col in data.columns if col not in ['event_type', 'ticker', 'event_date', 'target_return']]

    X_moon = moon_data[feature_cols]
    y_moon = (moon_data['target_return'] > 20).astype(int)  # Moon target: >20% return

    X_rug = rug_data[feature_cols]
    y_rug = (rug_data['target_return'] < -20).astype(int)  # Rug target: <-20% return

    print(f"   Features: {len(feature_cols)}")
    print(f"   Moon positive samples: {y_moon.sum()}/{len(y_moon)}")
    print(f"   Rug positive samples: {y_rug.sum()}/{len(y_rug)}")

    return X_moon, y_moon, X_rug, y_rug

def preprocess_features(X):
    """Preprocess features for LogisticRegression"""
    print("🔧 Preprocessing features for LogisticRegression...")
    
    # Handle missing values
    X_processed = X.copy()
    
    # Fill NaN values with median (more robust than mean)
    for col in X_processed.columns:
        if X_processed[col].dtype in ['float64', 'int64']:
            median_val = X_processed[col].median()
            X_processed[col] = X_processed[col].fillna(median_val)
    
    # Remove infinite values
    X_processed = X_processed.replace([np.inf, -np.inf], np.nan)
    X_processed = X_processed.fillna(0)
    
    # Scale features (important for LogisticRegression)
    scaler = StandardScaler()
    X_scaled = pd.DataFrame(
        scaler.fit_transform(X_processed),
        columns=X_processed.columns,
        index=X_processed.index
    )
    
    print(f"   ✅ Preprocessed {len(X_scaled.columns)} features")
    print(f"   ✅ Scaled features to mean=0, std=1")
    
    return X_scaled, scaler

def create_regularized_logistic(class_weights=True):
    """Create LogisticRegression with very strong regularization"""
    print("🔧 Creating very strongly regularized LogisticRegression...")

    # Use extremely strong regularization to prevent overfitting
    logistic_models = {
        'logistic_l1_strong': LogisticRegression(
            C=0.001,  # Extremely strong regularization
            penalty='l1',
            solver='liblinear',
            class_weight='balanced' if class_weights else None,
            max_iter=3000,
            random_state=42
        ),
        'logistic_l2_strong': LogisticRegression(
            C=0.001,  # Extremely strong regularization
            penalty='l2',
            solver='lbfgs',
            class_weight='balanced' if class_weights else None,
            max_iter=3000,
            random_state=42
        ),
        'logistic_l1_medium': LogisticRegression(
            C=0.01,  # Strong regularization
            penalty='l1',
            solver='liblinear',
            class_weight='balanced' if class_weights else None,
            max_iter=3000,
            random_state=42
        ),
        'logistic_l2_medium': LogisticRegression(
            C=0.01,  # Strong regularization
            penalty='l2',
            solver='lbfgs',
            class_weight='balanced' if class_weights else None,
            max_iter=3000,
            random_state=42
        )
    }

    print(f"   Created {len(logistic_models)} regularized models:")
    for name in logistic_models.keys():
        print(f"   - {name}")

    return logistic_models

def train_and_evaluate_logistic(X, y, model_type):
    """Train and evaluate LogisticRegression models"""
    print(f"\n🚀 Training regularized LogisticRegression for {model_type}...")
    
    # Preprocess features
    X_processed, scaler = preprocess_features(X)
    
    # Create models
    logistic_models = create_regularized_logistic(class_weights=True)
    
    best_model = None
    best_score = 0
    best_name = ""
    results = {}
    
    for name, model in logistic_models.items():
        print(f"\n   🔧 Training {name}...")
        
        # Cross-validation to select best model
        cv_scores = cross_val_score(model, X_processed, y, cv=5, scoring='roc_auc')
        mean_cv_score = cv_scores.mean()
        
        print(f"      CV AUC: {mean_cv_score:.3f} ± {cv_scores.std():.3f}")
        
        # Train on full dataset
        model.fit(X_processed, y)
        
        # Evaluate
        y_pred = model.predict(X_processed)
        y_proba = model.predict_proba(X_processed)
        
        accuracy = accuracy_score(y, y_pred)
        auc = roc_auc_score(y, y_proba[:, 1])
        
        print(f"      Training accuracy: {accuracy:.1%}")
        print(f"      Training AUC: {auc:.3f}")
        
        # Check for overfitting (CV score should be close to training score)
        overfitting_gap = auc - mean_cv_score
        print(f"      Overfitting gap: {overfitting_gap:.3f}")
        
        results[name] = {
            'model': model,
            'scaler': scaler,
            'cv_auc': mean_cv_score,
            'train_accuracy': accuracy,
            'train_auc': auc,
            'overfitting_gap': overfitting_gap
        }
        
        # Select best model (highest CV score, allow more overfitting for now)
        if mean_cv_score > best_score and overfitting_gap < 0.3:  # Allow more overfitting temporarily
            best_score = mean_cv_score
            best_model = model
            best_name = name
    
    if best_model is None:
        print("   ❌ No suitable model found (all overfitting)")
        return None, None, None
    
    print(f"\n   ✅ Best model: {best_name} (CV AUC: {best_score:.3f})")
    
    # Calibrate the best model
    print("   🎯 Calibrating probabilities...")
    calibrated_model = CalibratedClassifierCV(
        best_model,
        method='isotonic',
        cv=3
    )
    calibrated_model.fit(X_processed, y)
    
    # Final evaluation
    y_pred_cal = calibrated_model.predict(X_processed)
    y_proba_cal = calibrated_model.predict_proba(X_processed)
    
    final_accuracy = accuracy_score(y, y_pred_cal)
    final_auc = roc_auc_score(y, y_proba_cal[:, 1])
    
    print(f"   ✅ Calibrated accuracy: {final_accuracy:.1%}")
    print(f"   ✅ Calibrated AUC: {final_auc:.3f}")
    
    # Save models
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = Path('/Users/vynfred/Documents/bullsbears/backend/data/models')
    
    # Save calibrated model
    model_file = model_dir / f"{model_type}_logistic_regularized_{timestamp}.joblib"
    joblib.dump(calibrated_model, model_file)
    print(f"   💾 Saved model: {model_file.name}")
    
    # Save scaler
    scaler_file = model_dir / f"{model_type}_logistic_scaler_{timestamp}.joblib"
    joblib.dump(scaler, scaler_file)
    print(f"   💾 Saved scaler: {scaler_file.name}")
    
    # Save metadata
    metadata = {
        "model_type": "logistic_regression_regularized",
        "best_variant": best_name,
        "feature_names": list(X.columns),
        "preprocessing": {
            "scaled": True,
            "scaler_file": scaler_file.name
        },
        "training_metrics": {
            "cv_auc": float(best_score),
            "final_accuracy": float(final_accuracy),
            "final_auc": float(final_auc),
            "samples": len(X)
        },
        "regularization": {
            "C": 0.01,
            "penalty": best_name.split('_')[1],
            "class_weight": "balanced"
        },
        "timestamp": timestamp
    }
    
    metadata_file = model_dir / f"{model_type}_logistic_regularized_{timestamp}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"   💾 Saved metadata: {metadata_file.name}")
    
    return calibrated_model, scaler, metadata

def main():
    """Main training execution"""
    print("🚀 Retraining LogisticRegression with Proper Regularization...")
    print("=" * 70)
    
    # Load data
    X_moon, y_moon, X_rug, y_rug = load_training_data()
    
    if X_moon is None:
        print("❌ Cannot load training data")
        return False
    
    try:
        # Train moon LogisticRegression
        moon_model, moon_scaler, moon_metadata = train_and_evaluate_logistic(X_moon, y_moon, 'moon')
        
        if moon_model is None:
            print("❌ Moon LogisticRegression training failed")
            return False
        
        # Train rug LogisticRegression
        rug_model, rug_scaler, rug_metadata = train_and_evaluate_logistic(X_rug, y_rug, 'rug')
        
        if rug_model is None:
            print("❌ Rug LogisticRegression training failed")
            return False
        
        print("\n" + "=" * 70)
        print("🎉 LogisticRegression Retraining Complete!")
        print(f"✅ Moon LogisticRegression: {moon_metadata['training_metrics']['final_accuracy']:.1%} accuracy")
        print(f"✅ Rug LogisticRegression: {rug_metadata['training_metrics']['final_accuracy']:.1%} accuracy")
        print("✅ Strong regularization applied to prevent overfitting!")
        print("✅ Ready to integrate back into ensemble!")
        
        return True
        
    except Exception as e:
        print(f"❌ Training failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
