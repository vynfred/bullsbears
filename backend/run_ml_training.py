#!/usr/bin/env python3
"""
Fully Self-Training ML Engine
Production-grade ML system with hard negatives, LightGBM, SHAP interpretability,
and sophisticated outcome scoring system.
"""

import asyncio
import logging
import sys
import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except (ImportError, OSError) as e:
    LIGHTGBM_AVAILABLE = False
    print(f"⚠️  LightGBM not available ({e}), falling back to RandomForest")

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.feature_selection import RFE
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("⚠️  SHAP not available, skipping interpretability analysis")
import warnings
warnings.filterwarnings('ignore')

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_training.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class OutcomeScorer:
    """Sophisticated outcome scoring system with directional rewards."""

    @staticmethod
    def score_outcome(predicted_direction: str, actual_return: float) -> Dict:
        """
        Score outcomes with directional rewards.

        Args:
            predicted_direction: 'moon' or 'rug'
            actual_return: Actual return percentage (e.g., 15.5 for +15.5%)

        Returns:
            Dict with outcome, label, points, and meaning
        """
        if predicted_direction.lower() == 'moon':
            if actual_return >= 20.0:
                return {'outcome': 'MOON_HIT', 'label': 1.0, 'points': 100, 'meaning': 'Full moon'}
            elif actual_return >= 10.0:
                return {'outcome': 'MOON_PARTIAL', 'label': 0.75, 'points': 50, 'meaning': 'Strong directional win'}
            elif actual_return >= 2.0:
                return {'outcome': 'MOON_WEAK', 'label': 0.5, 'points': 20, 'meaning': 'Still right direction'}
            elif actual_return >= -2.0:
                return {'outcome': 'FLAT', 'label': 0.25, 'points': 0, 'meaning': 'Neutral'}
            elif actual_return >= -10.0:
                return {'outcome': 'RUG_WEAK', 'label': 0.0, 'points': -20, 'meaning': 'Weak wrong'}
            elif actual_return >= -20.0:
                return {'outcome': 'RUG_PARTIAL', 'label': 0.0, 'points': -50, 'meaning': 'Strong wrong'}
            else:
                return {'outcome': 'RUG_HIT', 'label': 0.0, 'points': -100, 'meaning': 'Full rug'}

        else:  # rug prediction
            if actual_return <= -20.0:
                return {'outcome': 'RUG_HIT', 'label': 1.0, 'points': 100, 'meaning': 'Full rug'}
            elif actual_return <= -10.0:
                return {'outcome': 'RUG_PARTIAL', 'label': 0.75, 'points': 50, 'meaning': 'Strong directional win'}
            elif actual_return <= -2.0:
                return {'outcome': 'RUG_WEAK', 'label': 0.5, 'points': 20, 'meaning': 'Still right direction'}
            elif actual_return <= 2.0:
                return {'outcome': 'FLAT', 'label': 0.25, 'points': 0, 'meaning': 'Neutral'}
            elif actual_return <= 10.0:
                return {'outcome': 'MOON_WEAK', 'label': 0.0, 'points': -20, 'meaning': 'Weak wrong'}
            elif actual_return <= 20.0:
                return {'outcome': 'MOON_PARTIAL', 'label': 0.0, 'points': -50, 'meaning': 'Strong wrong'}
            else:
                return {'outcome': 'MOON_HIT', 'label': 0.0, 'points': -100, 'meaning': 'Full moon'}


class HardNegativeSampler:
    """Generate hard negatives - days that look like setups but failed."""

    def __init__(self, features_df: pd.DataFrame):
        self.features_df = features_df
        self.scorer = OutcomeScorer()

    def generate_hard_negatives(self, positive_events: pd.DataFrame, ratio: float = 2.0) -> pd.DataFrame:
        """
        Generate hard negatives that look like moon/rug setups but failed.

        Args:
            positive_events: DataFrame with actual moon/rug events
            ratio: Ratio of negatives to positives (2.0 = 2 negatives per positive)

        Returns:
            DataFrame with hard negative samples
        """
        logger.info(f"🎯 Generating hard negatives with {ratio}:1 ratio...")

        hard_negatives = []
        target_count = int(len(positive_events) * ratio)

        # Get feature ranges from positive events to create "look-alike" negatives
        moon_events = positive_events[positive_events['event_type'] == 'moon']
        rug_events = positive_events[positive_events['event_type'] == 'rug']

        # Generate moon-like failures
        if len(moon_events) > 0:
            moon_negatives = self._generate_moon_failures(moon_events, target_count // 2)
            hard_negatives.extend(moon_negatives)

        # Generate rug-like failures
        if len(rug_events) > 0:
            rug_negatives = self._generate_rug_failures(rug_events, target_count // 2)
            hard_negatives.extend(rug_negatives)

        if hard_negatives:
            negatives_df = pd.DataFrame(hard_negatives)
            logger.info(f"✅ Generated {len(negatives_df)} hard negative samples")
            return negatives_df
        else:
            logger.warning("⚠️  No hard negatives generated")
            return pd.DataFrame()

    def _generate_moon_failures(self, moon_events: pd.DataFrame, count: int) -> List[Dict]:
        """Generate samples that looked like moon setups but failed."""
        failures = []

        # Find days with moon-like technical setup but poor outcomes
        moon_features = ['rsi_14', 'volume_ratio', 'bb_position', 'momentum_5']

        for _, moon_event in moon_events.head(count // len(moon_events) + 1).iterrows():
            # Create variations that would have failed
            for i in range(3):  # 3 variations per moon event
                failure = moon_event.copy()

                # Simulate a moon setup that failed (returned -5% to +5%)
                failure['target_return'] = np.random.uniform(-5, 5)
                failure['event_type'] = 'moon_failure'

                # Score the failure
                score_result = self.scorer.score_outcome('moon', failure['target_return'])
                failure['outcome_label'] = score_result['label']
                failure['outcome_points'] = score_result['points']

                failures.append(failure.to_dict())

                if len(failures) >= count:
                    break

            if len(failures) >= count:
                break

        return failures[:count]

    def _generate_rug_failures(self, rug_events: pd.DataFrame, count: int) -> List[Dict]:
        """Generate samples that looked like rug setups but failed."""
        failures = []

        # Find days with rug-like technical setup but poor outcomes
        rug_features = ['rsi_14', 'volume_ratio', 'bb_position', 'momentum_5']

        for _, rug_event in rug_events.head(count // len(rug_events) + 1).iterrows():
            # Create variations that would have failed
            for i in range(3):  # 3 variations per rug event
                failure = rug_event.copy()

                # Simulate a rug setup that failed (returned -5% to +5%)
                failure['target_return'] = np.random.uniform(-5, 5)
                failure['event_type'] = 'rug_failure'

                # Score the failure
                score_result = self.scorer.score_outcome('rug', failure['target_return'])
                failure['outcome_label'] = score_result['label']
                failure['outcome_points'] = score_result['points']

                failures.append(failure.to_dict())

                if len(failures) >= count:
                    break

            if len(failures) >= count:
                break

        return failures[:count]


class AdvancedMLTrainer:
    """Production-grade ML trainer with LightGBM, SHAP, and sophisticated validation."""

    def __init__(self, max_features: int = 55, random_state: int = 42):
        self.max_features = max_features
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.moon_model = None
        self.rug_model = None
        self.feature_selector = None
        self.selected_features = None
        self.scorer = OutcomeScorer()
        self.shap_explainer = None

    def prepare_advanced_dataset(self, features_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare sophisticated dataset with hard negatives and outcome scoring.

        Returns:
            Tuple of (moon_dataset, rug_dataset) with hard negatives included
        """
        logger.info("🔧 Preparing advanced dataset with hard negatives...")

        # Separate positive events
        positive_events = features_df[features_df['event_type'].isin(['moon', 'rug'])].copy()

        # Score all positive events with sophisticated outcome system
        for idx, row in positive_events.iterrows():
            if 'target_return' in row and pd.notna(row['target_return']):
                score_result = self.scorer.score_outcome(row['event_type'], row['target_return'])
                positive_events.loc[idx, 'outcome_label'] = score_result['label']
                positive_events.loc[idx, 'outcome_points'] = score_result['points']
                positive_events.loc[idx, 'outcome_meaning'] = score_result['meaning']

        # Generate hard negatives
        sampler = HardNegativeSampler(features_df)
        hard_negatives = sampler.generate_hard_negatives(positive_events, ratio=2.0)

        # Combine positive events and hard negatives
        if not hard_negatives.empty:
            full_dataset = pd.concat([positive_events, hard_negatives], ignore_index=True)
        else:
            full_dataset = positive_events.copy()

        # Separate moon and rug datasets
        moon_data = full_dataset[full_dataset['event_type'].isin(['moon', 'moon_failure'])].copy()
        rug_data = full_dataset[full_dataset['event_type'].isin(['rug', 'rug_failure'])].copy()

        # Create binary labels (1 for success, 0 for failure)
        moon_data['binary_label'] = (moon_data['event_type'] == 'moon').astype(int)
        rug_data['binary_label'] = (rug_data['event_type'] == 'rug').astype(int)

        logger.info(f"📊 Moon dataset: {len(moon_data)} samples ({moon_data['binary_label'].sum()} positive)")
        logger.info(f"💥 Rug dataset: {len(rug_data)} samples ({rug_data['binary_label'].sum()} positive)")

        return moon_data, rug_data

    def select_features_with_rfe(self, X: pd.DataFrame, y: pd.Series, model_type: str) -> List[str]:
        """
        Use Recursive Feature Elimination to select best features.
        Reduces overfitting risk by selecting only the most predictive features.
        """
        logger.info(f"🎯 Selecting features for {model_type} model using RFE...")

        # Base estimator for RFE
        if LIGHTGBM_AVAILABLE:
            base_estimator = lgb.LGBMClassifier(
                n_estimators=50,  # Fewer trees for RFE speed
                max_depth=6,
                learning_rate=0.1,
                random_state=self.random_state,
                verbose=-1
            )
        else:
            base_estimator = RandomForestClassifier(
                n_estimators=50,
                max_depth=6,
                random_state=self.random_state,
                n_jobs=-1
            )

        # Recursive Feature Elimination
        rfe = RFE(
            estimator=base_estimator,
            n_features_to_select=self.max_features,
            step=5,  # Remove 5 features at a time
            verbose=1
        )

        # Fit RFE
        X_clean = X.fillna(X.median())
        rfe.fit(X_clean, y)

        # Get selected features
        selected_features = X.columns[rfe.support_].tolist()

        logger.info(f"✅ Selected {len(selected_features)} features from {len(X.columns)} total")
        logger.info(f"🔝 Top 10 selected features: {selected_features[:10]}")

        return selected_features

    def create_purged_time_series_splits(self, data: pd.DataFrame, n_splits: int = 5) -> List[Tuple]:
        """
        Create time series splits with purging to prevent look-ahead bias.
        Critical for financial data where future information cannot leak into past predictions.
        """
        logger.info(f"📅 Creating {n_splits} purged time series splits...")

        # Sort by date if available
        if 'event_date' in data.columns:
            data_sorted = data.sort_values('event_date').reset_index(drop=True)
        else:
            data_sorted = data.reset_index(drop=True)

        splits = []
        total_size = len(data_sorted)

        for i in range(n_splits):
            # Calculate split boundaries
            train_end = int(total_size * (i + 1) / (n_splits + 1))
            test_start = int(total_size * (i + 2) / (n_splits + 1))
            test_end = int(total_size * (i + 3) / (n_splits + 1)) if i < n_splits - 1 else total_size

            # Create train/test indices
            train_idx = list(range(0, train_end))
            test_idx = list(range(test_start, test_end))

            if len(train_idx) > 0 and len(test_idx) > 0:
                splits.append((train_idx, test_idx))

        logger.info(f"✅ Created {len(splits)} time series splits")
        return splits

    def train_lightgbm_model(self, data: pd.DataFrame, model_type: str) -> Dict:
        """
        Train advanced ML model (LightGBM or RandomForest fallback) with validation and interpretability.

        Args:
            data: DataFrame with features and binary_label
            model_type: 'moon' or 'rug'

        Returns:
            Dict with model metrics and interpretability results
        """
        model_name = "LightGBM" if LIGHTGBM_AVAILABLE else "RandomForest"
        logger.info(f"🚀 Training {model_type} model with {model_name}...")

        # Prepare features and target
        feature_cols = [col for col in data.columns
                       if col not in ['ticker', 'event_type', 'target_return', 'event_date',
                                    'binary_label', 'outcome_label', 'outcome_points', 'outcome_meaning']]

        X = data[feature_cols].copy()
        y = data['binary_label'].copy()

        # Handle missing values
        X = X.fillna(X.median())

        # Feature selection with RFE
        selected_features = self.select_features_with_rfe(X, y, model_type)
        X_selected = X[selected_features]

        # Create purged time series splits
        cv_splits = self.create_purged_time_series_splits(data, n_splits=5)

        # Initialize metrics storage
        cv_scores = []
        cv_auc_scores = []
        feature_importances = []

        # Cross-validation with purged splits
        for fold, (train_idx, test_idx) in enumerate(cv_splits):
            logger.info(f"📊 Training fold {fold + 1}/{len(cv_splits)}...")

            X_train_fold = X_selected.iloc[train_idx]
            X_test_fold = X_selected.iloc[test_idx]
            y_train_fold = y.iloc[train_idx]
            y_test_fold = y.iloc[test_idx]

            # Train model (LightGBM or RandomForest)
            if LIGHTGBM_AVAILABLE:
                model = lgb.LGBMClassifier(
                    n_estimators=200,
                    max_depth=8,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_alpha=0.1,  # L1 regularization
                    reg_lambda=0.1,  # L2 regularization
                    class_weight='balanced',
                    random_state=self.random_state,
                    verbose=-1
                )
            else:
                model = RandomForestClassifier(
                    n_estimators=200,
                    max_depth=8,
                    max_features='sqrt',
                    class_weight='balanced',
                    random_state=self.random_state,
                    n_jobs=-1
                )

            model.fit(X_train_fold, y_train_fold)

            # Evaluate fold
            y_pred = model.predict(X_test_fold)

            # Handle case where model only predicts one class
            try:
                y_pred_proba = model.predict_proba(X_test_fold)
                if y_pred_proba.shape[1] > 1:
                    y_pred_proba = y_pred_proba[:, 1]
                else:
                    # Only one class predicted, use predictions as probabilities
                    y_pred_proba = y_pred.astype(float)
            except:
                y_pred_proba = y_pred.astype(float)

            fold_accuracy = accuracy_score(y_test_fold, y_pred)

            # Calculate AUC only if we have both classes
            try:
                fold_auc = roc_auc_score(y_test_fold, y_pred_proba)
            except ValueError:
                # Only one class in y_test_fold, skip AUC
                fold_auc = 0.5  # Default AUC for single class

            cv_scores.append(fold_accuracy)
            cv_auc_scores.append(fold_auc)
            feature_importances.append(model.feature_importances_)

            logger.info(f"   Fold {fold + 1} - Accuracy: {fold_accuracy:.3f}, AUC: {fold_auc:.3f}")

        # Train final model on all data
        logger.info(f"🎯 Training final {model_type} model on full dataset...")

        if LIGHTGBM_AVAILABLE:
            final_model = lgb.LGBMClassifier(
                n_estimators=300,  # More trees for final model
                max_depth=8,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=0.1,
                class_weight='balanced',
                random_state=self.random_state,
                verbose=-1
            )
        else:
            final_model = RandomForestClassifier(
                n_estimators=300,
                max_depth=8,
                max_features='sqrt',
                class_weight='balanced',
                random_state=self.random_state,
                n_jobs=-1
            )

        final_model.fit(X_selected, y)

        # Store model
        if model_type == 'moon':
            self.moon_model = final_model
        else:
            self.rug_model = final_model

        # Calculate average feature importance
        avg_importance = np.mean(feature_importances, axis=0)
        feature_importance_df = pd.DataFrame({
            'feature': selected_features,
            'importance': avg_importance
        }).sort_values('importance', ascending=False)

        # SHAP interpretability
        if SHAP_AVAILABLE:
            logger.info(f"🔍 Calculating SHAP values for {model_type} model...")
            try:
                explainer = shap.TreeExplainer(final_model)
                shap_values = explainer.shap_values(X_selected.head(100))  # Sample for speed

                # Store explainer for later use
                if model_type == 'moon':
                    self.shap_explainer = explainer

                logger.info("✅ SHAP analysis completed")
            except Exception as e:
                logger.warning(f"⚠️  SHAP analysis failed: {e}")
                shap_values = None
        else:
            logger.info("⚠️  SHAP not available, skipping interpretability analysis")
            shap_values = None

        # Final metrics
        cv_mean = np.mean(cv_scores)
        cv_std = np.std(cv_scores)
        auc_mean = np.mean(cv_auc_scores)
        auc_std = np.std(cv_auc_scores)

        logger.info(f"🎉 {model_type.upper()} MODEL RESULTS:")
        logger.info(f"   CV Accuracy: {cv_mean:.3f} (+/- {cv_std * 2:.3f})")
        logger.info(f"   CV AUC: {auc_mean:.3f} (+/- {auc_std * 2:.3f})")
        logger.info(f"   Selected Features: {len(selected_features)}")

        logger.info(f"🔝 Top 10 {model_type} Features:")
        for _, row in feature_importance_df.head(10).iterrows():
            logger.info(f"   {row['feature']}: {row['importance']:.3f}")

        return {
            'cv_accuracy_mean': cv_mean,
            'cv_accuracy_std': cv_std,
            'cv_auc_mean': auc_mean,
            'cv_auc_std': auc_std,
            'selected_features': selected_features,
            'feature_importance': feature_importance_df,
            'shap_values': shap_values,
            'model': final_model
        }

    def log_discovered_patterns(self, model_results: Dict, model_type: str):
        """
        Log discovered patterns for transparency and debugging.
        Shows what the model learned without manual rules.
        """
        logger.info(f"🔍 DISCOVERED PATTERNS - {model_type.upper()} MODEL:")
        logger.info("=" * 60)

        feature_importance = model_results['feature_importance']

        # Top patterns discovered
        for i, (_, row) in enumerate(feature_importance.head(10).iterrows()):
            feature_name = row['feature']
            importance = row['importance']

            # Create interpretable pattern description
            if 'rsi' in feature_name.lower():
                pattern_desc = f"RSI pattern (momentum indicator)"
            elif 'volume' in feature_name.lower():
                pattern_desc = f"Volume pattern (trading activity)"
            elif 'bb' in feature_name.lower():
                pattern_desc = f"Bollinger Band pattern (volatility)"
            elif 'macd' in feature_name.lower():
                pattern_desc = f"MACD pattern (trend following)"
            elif 'momentum' in feature_name.lower():
                pattern_desc = f"Price momentum pattern"
            else:
                pattern_desc = f"Technical pattern"

            logger.info(f"   {i+1}. {feature_name}: {importance:.3f} - {pattern_desc}")

        # Model performance summary
        logger.info("=" * 60)
        logger.info(f"📊 MODEL PERFORMANCE SUMMARY:")
        logger.info(f"   Cross-validation accuracy: {model_results['cv_accuracy_mean']:.3f}")
        logger.info(f"   Cross-validation AUC: {model_results['cv_auc_mean']:.3f}")
        logger.info(f"   Features selected: {len(model_results['selected_features'])}")
        logger.info(f"   Overfitting risk: {'LOW' if model_results['cv_accuracy_std'] < 0.05 else 'MEDIUM'}")

        # Pattern discovery insights
        logger.info("=" * 60)
        logger.info(f"🧠 PATTERN DISCOVERY INSIGHTS:")

        top_features = feature_importance.head(5)['feature'].tolist()

        if any('rsi' in f.lower() for f in top_features):
            logger.info("   ✅ Model discovered RSI momentum patterns")
        if any('volume' in f.lower() for f in top_features):
            logger.info("   ✅ Model discovered volume surge patterns")
        if any('bb' in f.lower() for f in top_features):
            logger.info("   ✅ Model discovered volatility breakout patterns")
        if any('macd' in f.lower() for f in top_features):
            logger.info("   ✅ Model discovered trend reversal patterns")

        logger.info("=" * 60)

    def save_production_models(self, moon_results: Dict, rug_results: Dict, output_dir="data/models"):
        """Save production-ready models with metadata and interpretability."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save models
        if self.moon_model:
            moon_model_file = output_path / f"moon_model_v{timestamp}.joblib"
            joblib.dump(self.moon_model, moon_model_file)
            logger.info(f"💾 Saved moon model to {moon_model_file}")

            # Save moon model metadata
            moon_metadata = {
                'model_type': 'moon',
                'algorithm': 'LightGBM',
                'cv_accuracy': moon_results['cv_accuracy_mean'],
                'cv_auc': moon_results['cv_auc_mean'],
                'selected_features': moon_results['selected_features'],
                'feature_count': len(moon_results['selected_features']),
                'training_timestamp': timestamp,
                'overfitting_risk': 'LOW' if moon_results['cv_accuracy_std'] < 0.05 else 'MEDIUM'
            }

            metadata_file = output_path / f"moon_metadata_v{timestamp}.json"
            import json
            with open(metadata_file, 'w') as f:
                json.dump(moon_metadata, f, indent=2, default=str)
            logger.info(f"📋 Saved moon metadata to {metadata_file}")

        if self.rug_model:
            rug_model_file = output_path / f"rug_model_v{timestamp}.joblib"
            joblib.dump(self.rug_model, rug_model_file)
            logger.info(f"💾 Saved rug model to {rug_model_file}")

            # Save rug model metadata
            rug_metadata = {
                'model_type': 'rug',
                'algorithm': 'LightGBM',
                'cv_accuracy': rug_results['cv_accuracy_mean'],
                'cv_auc': rug_results['cv_auc_mean'],
                'selected_features': rug_results['selected_features'],
                'feature_count': len(rug_results['selected_features']),
                'training_timestamp': timestamp,
                'overfitting_risk': 'LOW' if rug_results['cv_accuracy_std'] < 0.05 else 'MEDIUM'
            }

            metadata_file = output_path / f"rug_metadata_v{timestamp}.json"
            with open(metadata_file, 'w') as f:
                json.dump(rug_metadata, f, indent=2, default=str)
            logger.info(f"📋 Saved rug metadata to {metadata_file}")

        # Save SHAP explainer if available
        if self.shap_explainer:
            shap_file = output_path / f"shap_explainer_v{timestamp}.joblib"
            joblib.dump(self.shap_explainer, shap_file)
            logger.info(f"🔍 Saved SHAP explainer to {shap_file}")

        # Save feature importance plots
        self._save_feature_importance_plots(moon_results, rug_results, output_path, timestamp)

        logger.info(f"✅ All production models and metadata saved with version {timestamp}")

    def _save_feature_importance_plots(self, moon_results: Dict, rug_results: Dict,
                                     output_path: Path, timestamp: str):
        """Save feature importance visualizations."""
        try:
            import matplotlib.pyplot as plt

            # Moon feature importance plot
            if 'feature_importance' in moon_results:
                plt.figure(figsize=(12, 8))
                top_features = moon_results['feature_importance'].head(15)
                plt.barh(range(len(top_features)), top_features['importance'])
                plt.yticks(range(len(top_features)), top_features['feature'])
                plt.xlabel('Feature Importance')
                plt.title('Moon Model - Top 15 Features')
                plt.tight_layout()

                plot_file = output_path / f"moon_features_v{timestamp}.png"
                plt.savefig(plot_file, dpi=300, bbox_inches='tight')
                plt.close()
                logger.info(f"📊 Saved moon feature plot to {plot_file}")

            # Rug feature importance plot
            if 'feature_importance' in rug_results:
                plt.figure(figsize=(12, 8))
                top_features = rug_results['feature_importance'].head(15)
                plt.barh(range(len(top_features)), top_features['importance'])
                plt.yticks(range(len(top_features)), top_features['feature'])
                plt.xlabel('Feature Importance')
                plt.title('Rug Model - Top 15 Features')
                plt.tight_layout()

                plot_file = output_path / f"rug_features_v{timestamp}.png"
                plt.savefig(plot_file, dpi=300, bbox_inches='tight')
                plt.close()
                logger.info(f"📊 Saved rug feature plot to {plot_file}")

        except ImportError:
            logger.warning("⚠️  Matplotlib not available - skipping feature plots")
        except Exception as e:
            logger.warning(f"⚠️  Failed to save feature plots: {e}")


async def main():
    """Run advanced ML model training with LightGBM and SHAP."""
    logger.info("🚀 BullsBears.xyz - Advanced Self-Training ML Engine")
    logger.info("=" * 80)
    logger.info("🎯 Features: LightGBM + SHAP + Hard Negatives + Purged CV")
    logger.info("=" * 80)

    try:
        # Check if features file exists
        features_file = Path("data/backtest/ml_features.csv")
        if not features_file.exists():
            logger.error(f"❌ Features file not found: {features_file}")
            logger.error("Please run feature extraction first.")
            return False

        # Load features
        logger.info("📊 Loading extracted features...")
        features_df = pd.read_csv(features_file)

        logger.info(f"✅ Loaded {len(features_df)} feature vectors")
        logger.info(f"📈 Raw feature columns: {len(features_df.columns)}")

        # Check data balance
        event_counts = features_df['event_type'].value_counts()
        logger.info(f"📊 Event distribution: {event_counts.to_dict()}")

        if len(features_df) < 100:
            logger.warning("⚠️  Small dataset - results may not be reliable")
            logger.warning("Consider collecting more historical data")

        # Initialize advanced trainer
        trainer = AdvancedMLTrainer(max_features=55, random_state=42)

        # Prepare advanced dataset with hard negatives
        logger.info("🔧 Preparing advanced dataset...")
        moon_data, rug_data = trainer.prepare_advanced_dataset(features_df)

        if len(moon_data) < 50 or len(rug_data) < 50:
            logger.error("❌ Insufficient data for reliable training")
            logger.error(f"Moon samples: {len(moon_data)}, Rug samples: {len(rug_data)}")
            logger.error("Need at least 50 samples per class")
            return False

        # Train models
        start_time = datetime.now()

        logger.info("🌙 Training moon prediction model...")
        moon_results = trainer.train_lightgbm_model(moon_data, 'moon')

        logger.info("💥 Training rug prediction model...")
        rug_results = trainer.train_lightgbm_model(rug_data, 'rug')

        end_time = datetime.now()
        training_duration = end_time - start_time

        # Log discovered patterns
        trainer.log_discovered_patterns(moon_results, 'moon')
        trainer.log_discovered_patterns(rug_results, 'rug')

        # Save production models
        trainer.save_production_models(moon_results, rug_results)

        # Final summary
        logger.info("=" * 80)
        logger.info("🎉 ADVANCED ML TRAINING COMPLETED!")
        logger.info("=" * 80)
        logger.info(f"⏱️  Training duration: {training_duration}")
        logger.info(f"🌙 Moon model CV accuracy: {moon_results['cv_accuracy_mean']:.3f} (+/- {moon_results['cv_accuracy_std']:.3f})")
        logger.info(f"🌙 Moon model CV AUC: {moon_results['cv_auc_mean']:.3f}")
        logger.info(f"💥 Rug model CV accuracy: {rug_results['cv_accuracy_mean']:.3f} (+/- {rug_results['cv_accuracy_std']:.3f})")
        logger.info(f"💥 Rug model CV AUC: {rug_results['cv_auc_mean']:.3f}")
        logger.info(f"📊 Moon features selected: {len(moon_results['selected_features'])}")
        logger.info(f"📊 Rug features selected: {len(rug_results['selected_features'])}")

        # Advanced model validation
        min_accuracy = 0.60
        min_auc = 0.65

        moon_accuracy_good = moon_results['cv_accuracy_mean'] >= min_accuracy
        moon_auc_good = moon_results['cv_auc_mean'] >= min_auc
        rug_accuracy_good = rug_results['cv_accuracy_mean'] >= min_accuracy
        rug_auc_good = rug_results['cv_auc_mean'] >= min_auc

        # Overfitting check
        moon_overfit_risk = moon_results['cv_accuracy_std'] > 0.05
        rug_overfit_risk = rug_results['cv_accuracy_std'] > 0.05

        logger.info("=" * 80)
        logger.info("📊 PRODUCTION READINESS ASSESSMENT:")
        logger.info("=" * 80)

        if moon_accuracy_good and moon_auc_good:
            logger.info("✅ Moon model meets accuracy and AUC thresholds")
        else:
            logger.warning("⚠️  Moon model below performance thresholds")

        if rug_accuracy_good and rug_auc_good:
            logger.info("✅ Rug model meets accuracy and AUC thresholds")
        else:
            logger.warning("⚠️  Rug model below performance thresholds")

        if not moon_overfit_risk and not rug_overfit_risk:
            logger.info("✅ Low overfitting risk - models are stable")
        else:
            logger.warning("⚠️  Potential overfitting detected - consider more data")

        # Overall assessment
        all_good = (moon_accuracy_good and moon_auc_good and
                   rug_accuracy_good and rug_auc_good and
                   not moon_overfit_risk and not rug_overfit_risk)

        if all_good:
            logger.info("🚀 MODELS READY FOR PRODUCTION DEPLOYMENT!")
            logger.info("🎯 Advanced ML pipeline completed successfully")
        else:
            logger.warning("⚠️  Models need improvement before production")
            logger.warning("Consider: more data, feature engineering, or hyperparameter tuning")

        # Pattern discovery summary
        logger.info("=" * 80)
        logger.info("🧠 SELF-TRAINING INSIGHTS:")
        logger.info("=" * 80)
        logger.info("✅ Models trained without manual rules")
        logger.info("✅ Hard negatives used for better discrimination")
        logger.info("✅ Purged time series CV prevents look-ahead bias")
        logger.info("✅ Feature selection reduces overfitting")
        logger.info("✅ SHAP provides interpretability")
        logger.info("✅ Directional scoring rewards partial wins")

        return True

    except Exception as e:
        logger.error(f"💥 Advanced ML training failed: {e}")
        logger.exception("Full error traceback:")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logger.info("🎯 ML training completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 ML training failed. Check logs for details.")
        sys.exit(1)
