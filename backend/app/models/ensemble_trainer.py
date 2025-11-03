#!/usr/bin/env python3
"""
Ensemble Model Trainer
Combine multiple models for better predictions: LightGBM + RandomForest (LogisticRegression temporarily removed)
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, Dict, Any, List
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
# from sklearn.linear_model import LogisticRegression  # Temporarily removed
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, roc_auc_score
import joblib
import json
from pathlib import Path

# Try to import LightGBM
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except (ImportError, OSError):
    LIGHTGBM_AVAILABLE = False
    lgb = None

logger = logging.getLogger(__name__)

class EnsembleModelTrainer:
    """Advanced ensemble trainer combining multiple algorithms."""
    
    def __init__(self):
        self.ensemble_model = None
        self.base_models = {}
        self.feature_names = None
        self.training_metrics = {}
        
    def create_base_models(self, class_weights: Dict = None) -> Dict[str, Any]:
        """Create diverse base models for ensemble."""
        models = {}
        
        # Model 1: RandomForest (Tree-based, handles non-linear patterns)
        models['random_forest'] = RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features='sqrt',
            class_weight='balanced' if class_weights else None,
            random_state=42,
            n_jobs=-1
        )
        
        # Model 2: LightGBM (Gradient boosting, different from RF)
        if LIGHTGBM_AVAILABLE:
            scale_pos_weight = 1.0
            if class_weights and len(class_weights) == 2:
                neg_weight = class_weights.get(0, 1.0)
                pos_weight = class_weights.get(1, 1.0)
                scale_pos_weight = neg_weight / pos_weight
            
            models['lightgbm'] = lgb.LGBMClassifier(
                n_estimators=500,
                learning_rate=0.05,
                max_depth=8,
                num_leaves=31,
                feature_fraction=0.8,
                bagging_fraction=0.8,
                bagging_freq=5,
                lambda_l1=0.5,
                lambda_l2=0.5,
                min_child_samples=20,
                scale_pos_weight=scale_pos_weight,
                random_state=42,
                verbose=-1
            )
        
        # Model 3: Logistic Regression (TEMPORARILY REMOVED - overfitting issues)
        # models['logistic'] = LogisticRegression(
        #     C=1.0,  # Regularization
        #     penalty='elasticnet',  # L1 + L2 regularization
        #     l1_ratio=0.5,  # Balance between L1 and L2
        #     solver='saga',
        #     class_weight='balanced' if class_weights else None,
        #     random_state=42,
        #     max_iter=1000
        # )
        
        logger.info(f"🤖 Created {len(models)} base models for ensemble:")
        for name in models.keys():
            logger.info(f"   - {name}")
        
        return models
    
    def train_ensemble(self, X: pd.DataFrame, y: pd.Series, 
                      class_weights: Dict = None) -> Tuple[Any, Dict]:
        """
        Train ensemble model with cross-validation.
        
        Returns:
            Tuple of (ensemble_model, metrics)
        """
        logger.info("🚀 Training ensemble model...")
        
        self.feature_names = X.columns.tolist()
        
        # Create base models
        base_models = self.create_base_models(class_weights)
        self.base_models = base_models
        
        # Create ensemble using soft voting (probability averaging)
        ensemble_estimators = [(name, model) for name, model in base_models.items()]
        
        ensemble = VotingClassifier(
            estimators=ensemble_estimators,
            voting='soft',  # Use probability averaging
            n_jobs=-1
        )
        
        # Train ensemble
        logger.info("🎯 Training ensemble with soft voting...")
        ensemble.fit(X, y)
        
        # Calibrate the ensemble probabilities
        logger.info("🎯 Calibrating ensemble probabilities...")
        calibrated_ensemble = CalibratedClassifierCV(
            ensemble,
            method='isotonic',
            cv=3
        )
        calibrated_ensemble.fit(X, y)
        
        # Evaluate ensemble
        y_pred = calibrated_ensemble.predict(X)
        y_proba = calibrated_ensemble.predict_proba(X)[:, 1]
        
        # Individual model performance
        individual_scores = {}
        for name, model in base_models.items():
            model.fit(X, y)
            pred = model.predict(X)
            proba = model.predict_proba(X)[:, 1]
            
            individual_scores[name] = {
                'accuracy': accuracy_score(y, pred),
                'auc': roc_auc_score(y, proba) if len(np.unique(y)) > 1 else 0.0
            }
        
        # Ensemble metrics
        ensemble_accuracy = accuracy_score(y, y_pred)
        ensemble_auc = roc_auc_score(y, y_proba) if len(np.unique(y)) > 1 else 0.0
        
        metrics = {
            'ensemble_accuracy': ensemble_accuracy,
            'ensemble_auc': ensemble_auc,
            'individual_models': individual_scores,
            'n_features': len(self.feature_names),
            'n_samples': len(X),
            'class_distribution': y.value_counts().to_dict(),
            'ensemble_type': 'soft_voting_calibrated'
        }
        
        # Feature importance (from RandomForest)
        if 'random_forest' in base_models:
            rf_model = base_models['random_forest']
            feature_importance = dict(zip(self.feature_names, rf_model.feature_importances_))
            metrics['feature_importance'] = feature_importance
        
        self.ensemble_model = calibrated_ensemble
        self.training_metrics = metrics
        
        logger.info(f"✅ Ensemble training complete:")
        logger.info(f"   Ensemble Accuracy: {ensemble_accuracy:.4f}")
        logger.info(f"   Ensemble AUC: {ensemble_auc:.4f}")
        
        for name, scores in individual_scores.items():
            logger.info(f"   {name}: {scores['accuracy']:.4f} acc, {scores['auc']:.4f} AUC")
        
        return calibrated_ensemble, metrics
    
    def predict_ensemble(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Make ensemble predictions with individual model breakdown.
        
        Returns:
            Tuple of (predictions, probabilities, individual_predictions)
        """
        if self.ensemble_model is None:
            raise ValueError("Ensemble model not trained yet")
        
        # Ensemble predictions
        predictions = self.ensemble_model.predict(X)
        probabilities = self.ensemble_model.predict_proba(X)[:, 1]
        
        # Individual model predictions for transparency
        individual_predictions = {}
        
        for name, model in self.base_models.items():
            try:
                pred = model.predict(X)
                proba = model.predict_proba(X)[:, 1]
                individual_predictions[name] = {
                    'predictions': pred,
                    'probabilities': proba
                }
            except Exception as e:
                logger.warning(f"⚠️  Individual prediction failed for {name}: {e}")
        
        return predictions, probabilities, individual_predictions
    
    def get_model_agreement(self, X: pd.DataFrame) -> np.ndarray:
        """
        Calculate agreement between base models.
        High agreement = more confident predictions.
        """
        if not self.base_models:
            return np.zeros(len(X))
        
        all_probabilities = []
        
        for name, model in self.base_models.items():
            try:
                proba = model.predict_proba(X)[:, 1]
                all_probabilities.append(proba)
            except Exception as e:
                logger.warning(f"⚠️  Agreement calculation failed for {name}: {e}")
        
        if not all_probabilities:
            return np.zeros(len(X))
        
        # Calculate standard deviation of probabilities (lower = more agreement)
        prob_array = np.array(all_probabilities)
        agreement = 1.0 - np.std(prob_array, axis=0)  # Higher value = more agreement
        
        return agreement
    
    def save_ensemble(self, model_dir: str, model_name: str) -> Dict[str, str]:
        """Save ensemble model and metadata."""
        model_dir = Path(model_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save ensemble model
        ensemble_path = model_dir / f"{model_name}_ensemble.joblib"
        joblib.dump(self.ensemble_model, ensemble_path)
        
        # Save individual models
        individual_paths = {}
        for name, model in self.base_models.items():
            model_path = model_dir / f"{model_name}_{name}.joblib"
            joblib.dump(model, model_path)
            individual_paths[name] = str(model_path)
        
        # Save metadata
        metadata = {
            'model_type': 'ensemble',
            'ensemble_type': 'soft_voting_calibrated',
            'base_models': list(self.base_models.keys()),
            'feature_names': self.feature_names,
            'training_metrics': self.training_metrics,
            'individual_model_paths': individual_paths
        }
        
        metadata_path = model_dir / f"{model_name}_ensemble_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"💾 Ensemble model saved:")
        logger.info(f"   Ensemble: {ensemble_path}")
        logger.info(f"   Individual models: {len(individual_paths)}")
        logger.info(f"   Metadata: {metadata_path}")
        
        return {
            'ensemble_model': str(ensemble_path),
            'individual_models': individual_paths,
            'metadata': str(metadata_path)
        }

def load_ensemble_model(model_dir: str, model_name: str) -> Tuple[Any, Dict]:
    """Load ensemble model and metadata."""
    model_dir = Path(model_dir)
    
    # Load ensemble model
    ensemble_path = model_dir / f"{model_name}_ensemble.joblib"
    ensemble_model = joblib.load(ensemble_path)
    
    # Load metadata
    metadata_path = model_dir / f"{model_name}_ensemble_metadata.json"
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    return ensemble_model, metadata
