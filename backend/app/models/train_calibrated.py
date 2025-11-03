#!/usr/bin/env python3
"""
Calibrated Model Training
Fix overfitting with purged CV and probability calibration.
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, Dict, Any
from sklearn.model_selection import TimeSeriesSplit
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
from sklearn.ensemble import RandomForestClassifier
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except (ImportError, OSError) as e:
    LIGHTGBM_AVAILABLE = False
    lgb = None
    print(f"LightGBM not available: {e}")
import joblib
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class CalibratedModelTrainer:
    """Advanced model trainer with calibration and overfitting prevention."""
    
    def __init__(self, model_type: str = 'lightgbm'):
        self.model_type = model_type
        self.model = None
        self.calibrator = None
        self.feature_names = None
        self.training_metrics = {}
        
    def create_base_model(self, class_weights: Dict = None) -> Any:
        """Create base model with regularization."""
        if self.model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
            # Calculate scale_pos_weight for binary classification
            scale_pos_weight = 1.0
            if class_weights and len(class_weights) == 2:
                neg_weight = class_weights.get(0, 1.0)
                pos_weight = class_weights.get(1, 1.0)
                scale_pos_weight = neg_weight / pos_weight

            model = lgb.LGBMClassifier(
                n_estimators=1000,
                learning_rate=0.05,
                max_depth=6,
                num_leaves=31,
                feature_fraction=0.7,  # Feature bagging
                bagging_fraction=0.8,  # Row bagging
                bagging_freq=5,
                lambda_l1=1.0,  # L1 regularization
                lambda_l2=1.0,  # L2 regularization
                min_child_samples=20,  # Prevent overfitting
                scale_pos_weight=scale_pos_weight,
                random_state=42,
                verbose=-1
            )
        else:
            # RandomForest (primary model due to LightGBM issues)
            model = RandomForestClassifier(
                n_estimators=500,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                max_features='sqrt',
                class_weight='balanced' if class_weights else None,
                random_state=42,
                n_jobs=-1
            )

        return model
    
    def purged_time_series_split(self, df: pd.DataFrame, n_splits: int = 5, embargo_pct: float = 0.01) -> list:
        """
        Create purged time series splits to prevent data leakage.
        
        Args:
            df: DataFrame with event_date column
            n_splits: Number of CV splits
            embargo_pct: Percentage of data to embargo between train/test
        """
        if 'event_date' not in df.columns:
            logger.warning("No event_date column, using standard TimeSeriesSplit")
            tscv = TimeSeriesSplit(n_splits=n_splits)
            return list(tscv.split(df))
        
        # Sort by date
        df_sorted = df.sort_values('event_date').reset_index(drop=True)
        n_total = len(df_sorted)
        n_embargo = int(n_total * embargo_pct)
        
        splits = []
        
        for i in range(n_splits):
            # Calculate split points
            test_start = int(n_total * (i + 1) / (n_splits + 1))
            test_end = int(n_total * (i + 2) / (n_splits + 1))
            
            # Train on data before test (with embargo)
            train_end = max(0, test_start - n_embargo)
            train_indices = df_sorted.index[:train_end].tolist()
            
            # Test on specific time window
            test_indices = df_sorted.index[test_start:test_end].tolist()
            
            if len(train_indices) > 0 and len(test_indices) > 0:
                splits.append((train_indices, test_indices))
        
        logger.info(f"📅 Created {len(splits)} purged time series splits with {embargo_pct*100:.1f}% embargo")
        
        return splits
    
    def train_with_calibration(self, X: pd.DataFrame, y: pd.Series, 
                             class_weights: Dict = None) -> Tuple[Any, Any, Dict]:
        """
        Train model with cross-validation and probability calibration.
        
        Returns:
            Tuple of (base_model, calibrated_model, metrics)
        """
        logger.info(f"🚀 Training {self.model_type} model with calibration...")
        
        self.feature_names = X.columns.tolist()
        
        # Create base model
        base_model = self.create_base_model(class_weights)
        
        # Purged time series cross-validation
        cv_splits = self.purged_time_series_split(
            pd.concat([X, y], axis=1), 
            n_splits=5, 
            embargo_pct=0.01
        )
        
        # Cross-validation scores
        cv_scores = []
        cv_auc_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(cv_splits):
            logger.info(f"📊 Training fold {fold + 1}/{len(cv_splits)}...")
            
            X_train_fold = X.iloc[train_idx]
            y_train_fold = y.iloc[train_idx]
            X_val_fold = X.iloc[val_idx]
            y_val_fold = y.iloc[val_idx]
            
            # Train on fold
            if self.model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
                base_model.fit(
                    X_train_fold, y_train_fold,
                    eval_set=[(X_val_fold, y_val_fold)],
                    callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
                )
            else:
                base_model.fit(X_train_fold, y_train_fold)
            
            # Validate
            y_pred = base_model.predict(X_val_fold)
            y_proba = base_model.predict_proba(X_val_fold)[:, 1]
            
            fold_accuracy = accuracy_score(y_val_fold, y_pred)
            cv_scores.append(fold_accuracy)
            
            if len(np.unique(y_val_fold)) > 1:  # Can calculate AUC
                fold_auc = roc_auc_score(y_val_fold, y_proba)
                cv_auc_scores.append(fold_auc)
            
            logger.info(f"   Fold {fold + 1} accuracy: {fold_accuracy:.4f}")
        
        # Train final model on all data
        logger.info("🎯 Training final model on full dataset...")
        if self.model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
            # Use 20% for early stopping
            X_train_final, X_val_final, y_train_final, y_val_final = \
                self._create_validation_split(X, y, test_size=0.2)

            base_model.fit(
                X_train_final, y_train_final,
                eval_set=[(X_val_final, y_val_final)],
                callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
            )
        else:
            base_model.fit(X, y)
        
        # Calibrate probabilities using isotonic regression
        logger.info("🎯 Calibrating probabilities...")
        calibrated_model = CalibratedClassifierCV(
            base_model, 
            method='isotonic',  # Better for small datasets
            cv=3  # Use 3-fold for calibration
        )
        calibrated_model.fit(X, y)
        
        # Calculate final metrics
        y_pred_final = calibrated_model.predict(X)
        y_proba_final = calibrated_model.predict_proba(X)[:, 1]
        
        metrics = {
            'cv_accuracy_mean': np.mean(cv_scores),
            'cv_accuracy_std': np.std(cv_scores),
            'cv_auc_mean': np.mean(cv_auc_scores) if cv_auc_scores else 0.0,
            'cv_auc_std': np.std(cv_auc_scores) if cv_auc_scores else 0.0,
            'final_accuracy': accuracy_score(y, y_pred_final),
            'final_auc': roc_auc_score(y, y_proba_final) if len(np.unique(y)) > 1 else 0.0,
            'n_features': len(self.feature_names),
            'n_samples': len(X),
            'class_distribution': y.value_counts().to_dict()
        }
        
        # Feature importance
        if hasattr(base_model, 'feature_importances_'):
            feature_importance = dict(zip(self.feature_names, base_model.feature_importances_))
            metrics['feature_importance'] = feature_importance
            
            # Check for overfitting indicators
            max_importance = max(base_model.feature_importances_)
            if max_importance > 0.4:
                logger.warning(f"⚠️  High feature importance detected: {max_importance:.3f}")
                logger.warning("   This may indicate overfitting or data leakage")
        
        self.model = base_model
        self.calibrator = calibrated_model
        self.training_metrics = metrics
        
        logger.info(f"✅ Model training complete:")
        logger.info(f"   CV Accuracy: {metrics['cv_accuracy_mean']:.4f} ± {metrics['cv_accuracy_std']:.4f}")
        logger.info(f"   CV AUC: {metrics['cv_auc_mean']:.4f} ± {metrics['cv_auc_std']:.4f}")
        logger.info(f"   Final Accuracy: {metrics['final_accuracy']:.4f}")
        logger.info(f"   Final AUC: {metrics['final_auc']:.4f}")
        
        return base_model, calibrated_model, metrics
    
    def _create_validation_split(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2):
        """Create validation split for early stopping."""
        from sklearn.model_selection import train_test_split
        return train_test_split(X, y, test_size=test_size, random_state=42, stratify=y)
    
    def predict_calibrated(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Make calibrated predictions."""
        if self.calibrator is None:
            raise ValueError("Model not trained yet")
        
        predictions = self.calibrator.predict(X)
        probabilities = self.calibrator.predict_proba(X)[:, 1]
        
        return predictions, probabilities
    
    def save_model(self, model_dir: str, model_name: str) -> Dict[str, str]:
        """Save calibrated model and metadata."""
        model_dir = Path(model_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save base model
        base_model_path = model_dir / f"{model_name}_base.joblib"
        joblib.dump(self.model, base_model_path)
        
        # Save calibrated model
        calibrated_model_path = model_dir / f"{model_name}_calibrated.joblib"
        joblib.dump(self.calibrator, calibrated_model_path)
        
        # Save metadata
        metadata = {
            'model_type': self.model_type,
            'feature_names': self.feature_names,
            'training_metrics': self.training_metrics,
            'calibrated': True,
            'overfitting_risk': 'LOW' if self.training_metrics.get('cv_accuracy_std', 1.0) < 0.05 else 'HIGH'
        }
        
        metadata_path = model_dir / f"{model_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"💾 Model saved:")
        logger.info(f"   Base: {base_model_path}")
        logger.info(f"   Calibrated: {calibrated_model_path}")
        logger.info(f"   Metadata: {metadata_path}")
        
        return {
            'base_model': str(base_model_path),
            'calibrated_model': str(calibrated_model_path),
            'metadata': str(metadata_path)
        }

def load_calibrated_model(model_dir: str, model_name: str) -> Tuple[Any, Dict]:
    """Load calibrated model and metadata."""
    model_dir = Path(model_dir)
    
    # Load calibrated model
    calibrated_model_path = model_dir / f"{model_name}_calibrated.joblib"
    calibrated_model = joblib.load(calibrated_model_path)
    
    # Load metadata
    metadata_path = model_dir / f"{model_name}_metadata.json"
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    return calibrated_model, metadata
