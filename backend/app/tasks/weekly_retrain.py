"""
Advanced Weekly Retraining Tasks for Fully Self-Training Loop
Uses sophisticated outcome scoring, hard negatives, and LightGBM for continuous improvement
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from celery import Celery
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import pickle
import os
import lightgbm as lgb
from sklearn.feature_selection import RFE
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import joblib
import shap

from ..core.celery_app import celery_app
from ..core.database import get_db
from ..models.analysis_results import AnalysisResult, AlertType, AlertOutcome
from ..core.config import settings

logger = logging.getLogger(__name__)


class AdvancedOutcomeScorer:
    """Advanced outcome scoring with directional rewards."""

    @staticmethod
    def score_alert_outcome(predicted_direction: str, actual_return: float) -> Dict:
        """Score outcomes with sophisticated directional system."""
        if predicted_direction.lower() == 'moon':
            if actual_return >= 20.0:
                return {'outcome': 'MOON_HIT', 'label': 1.0, 'points': 100, 'meaning': 'Full moon'}
            elif actual_return >= 10.0:
                return {'outcome': 'MOON_PARTIAL', 'label': 0.75, 'points': 50, 'meaning': 'Strong directional win'}
            elif actual_return >= 2.0:
                return {'outcome': 'MOON_WEAK', 'label': 0.5, 'points': 20, 'meaning': 'Still right direction'}
            elif actual_return >= -2.0:
                return {'outcome': 'FLAT', 'label': 0.25, 'points': 0, 'meaning': 'Neutral'}
            else:
                return {'outcome': 'WRONG_DIRECTION', 'label': 0.0, 'points': -20, 'meaning': 'Wrong direction'}
        else:  # rug prediction
            if actual_return <= -20.0:
                return {'outcome': 'RUG_HIT', 'label': 1.0, 'points': 100, 'meaning': 'Full rug'}
            elif actual_return <= -10.0:
                return {'outcome': 'RUG_PARTIAL', 'label': 0.75, 'points': 50, 'meaning': 'Strong directional win'}
            elif actual_return <= -2.0:
                return {'outcome': 'RUG_WEAK', 'label': 0.5, 'points': 20, 'meaning': 'Still right direction'}
            elif actual_return <= 2.0:
                return {'outcome': 'FLAT', 'label': 0.25, 'points': 0, 'meaning': 'Neutral'}
            else:
                return {'outcome': 'WRONG_DIRECTION', 'label': 0.0, 'points': -20, 'meaning': 'Wrong direction'}


class AdvancedHardNegativeGenerator:
    """Generate hard negatives from failed alerts for better training."""

    def __init__(self, training_data: pd.DataFrame):
        self.training_data = training_data
        self.scorer = AdvancedOutcomeScorer()

    def generate_hard_negatives(self, ratio: float = 2.0) -> pd.DataFrame:
        """Generate hard negatives from alerts that looked promising but failed."""
        logger.info(f"🎯 Generating hard negatives from failed alerts...")

        # Get failed alerts (those that looked like setups but didn't work)
        failed_alerts = self.training_data[
            (self.training_data['outcome_points'] <= 0) &  # Failed or neutral
            (self.training_data['confidence_score'] >= 60)  # But had high confidence
        ].copy()

        if len(failed_alerts) == 0:
            logger.warning("No failed high-confidence alerts found for hard negatives")
            return pd.DataFrame()

        # Create variations of failed alerts as hard negatives
        hard_negatives = []
        target_count = int(len(self.training_data) * ratio)

        for _, failed_alert in failed_alerts.iterrows():
            # Create multiple variations
            for i in range(3):
                negative = failed_alert.copy()

                # Add noise to features to create variations
                feature_cols = [col for col in negative.index
                              if col not in ['symbol', 'alert_type', 'timestamp', 'outcome']]

                for col in feature_cols:
                    if pd.notna(negative[col]) and isinstance(negative[col], (int, float)):
                        # Add small random noise (±5%)
                        noise = np.random.normal(0, 0.05) * negative[col]
                        negative[col] = negative[col] + noise

                # Mark as hard negative
                negative['is_hard_negative'] = True
                negative['binary_label'] = 0  # Negative sample

                hard_negatives.append(negative)

                if len(hard_negatives) >= target_count:
                    break

            if len(hard_negatives) >= target_count:
                break

        if hard_negatives:
            negatives_df = pd.DataFrame(hard_negatives)
            logger.info(f"✅ Generated {len(negatives_df)} hard negative samples")
            return negatives_df
        else:
            return pd.DataFrame()


@celery_app.task(bind=True)
def advanced_weekly_retrain(self):
    """
    Advanced weekly retraining with LightGBM, hard negatives, and sophisticated scoring.
    """
    try:
        logger.info("🚀 Starting advanced weekly model retraining")
        start_time = datetime.now()

        # Get enhanced training data from the past 4 weeks
        training_data = _get_enhanced_training_data(weeks_back=4)

        if len(training_data) < 100:  # Higher threshold for advanced training
            logger.warning(f"Insufficient training data: {len(training_data)} samples")
            return {
                "status": "skipped",
                "reason": "insufficient_data",
                "samples": len(training_data),
                "minimum_required": 100
            }

        # Generate hard negatives
        neg_generator = AdvancedHardNegativeGenerator(training_data)
        hard_negatives = neg_generator.generate_hard_negatives(ratio=1.5)

        # Combine original data with hard negatives
        if not hard_negatives.empty:
            enhanced_data = pd.concat([training_data, hard_negatives], ignore_index=True)
        else:
            enhanced_data = training_data.copy()

        logger.info(f"📊 Enhanced dataset: {len(enhanced_data)} samples")

        # Train advanced models
        moon_metrics = _train_advanced_moon_model(enhanced_data)
        rug_metrics = _train_advanced_rug_model(enhanced_data)

        # Update performance tracking with advanced metrics
        _update_advanced_performance_tracking(moon_metrics, rug_metrics)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"🎉 Advanced weekly retraining completed in {duration:.1f}s")

        return {
            "status": "success",
            "duration_seconds": duration,
            "training_samples": len(training_data),
            "hard_negatives": len(hard_negatives) if not hard_negatives.empty else 0,
            "total_samples": len(enhanced_data),
            "moon_cv_accuracy": moon_metrics.get("cv_accuracy", 0),
            "moon_cv_auc": moon_metrics.get("cv_auc", 0),
            "rug_cv_accuracy": rug_metrics.get("cv_accuracy", 0),
            "rug_cv_auc": rug_metrics.get("cv_auc", 0),
            "overfitting_risk": "LOW" if (moon_metrics.get("cv_std", 1) < 0.05 and
                                        rug_metrics.get("cv_std", 1) < 0.05) else "MEDIUM"
        }

    except Exception as e:
        logger.error(f"💥 Advanced weekly retraining failed: {e}")
        raise self.retry(countdown=3600, exc=e)  # Retry in 1 hour


@celery_app.task(bind=True)
def update_alert_outcomes(self):
    """
    Update outcomes for pending alerts by checking actual price movements.
    Runs daily to track alert performance.
    """
    try:
        logger.info("Starting alert outcome updates")
        start_time = datetime.now()
        
        # Get pending alerts that are old enough to evaluate (3+ days)
        cutoff_date = datetime.now() - timedelta(days=3)
        updated_count = _update_pending_outcomes(cutoff_date)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Updated {updated_count} alert outcomes in {duration:.1f}s")
        
        return {
            "status": "success",
            "updated_alerts": updated_count,
            "duration_seconds": duration
        }
        
    except Exception as e:
        logger.error(f"Alert outcome update failed: {e}")
        raise self.retry(countdown=1800, exc=e)  # Retry in 30 minutes


def _get_training_data(weeks_back: int = 4) -> pd.DataFrame:
    """Get training data from completed alerts"""
    db = next(get_db())
    
    try:
        # Get alerts from the past N weeks with outcomes
        cutoff_date = datetime.now() - timedelta(weeks=weeks_back)
        
        alerts = db.query(AnalysisResult).filter(
            and_(
                AnalysisResult.timestamp >= cutoff_date,
                AnalysisResult.alert_type.in_([AlertType.MOON, AlertType.RUG]),
                AnalysisResult.alert_outcome.in_([AlertOutcome.SUCCESS, AlertOutcome.FAILURE, AlertOutcome.PARTIAL])
            )
        ).all()
        
        if not alerts:
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for alert in alerts:
            features = alert.features_json or {}
            
            row = {
                'symbol': alert.symbol,
                'alert_type': alert.alert_type.value,
                'timestamp': alert.timestamp,
                'confidence_score': alert.confidence_score,
                'technical_score': alert.technical_score,
                'news_sentiment_score': alert.news_sentiment_score,
                'social_sentiment_score': alert.social_sentiment_score,
                'earnings_score': alert.earnings_score,
                'pattern_confidence': alert.pattern_confidence,
                'actual_move_percent': alert.actual_move_percent or 0,
                'days_to_move': alert.days_to_move or 0,
                'outcome': alert.alert_outcome.value,
                'success': 1 if alert.alert_outcome == AlertOutcome.SUCCESS else 0
            }
            
            # Add feature data if available
            if isinstance(features, dict):
                row.update(features)
            
            data.append(row)
        
        df = pd.DataFrame(data)
        logger.info(f"Retrieved {len(df)} training samples")
        return df
        
    except Exception as e:
        logger.error(f"Error getting training data: {e}")
        return pd.DataFrame()
    finally:
        db.close()


def _train_moon_model(training_data: pd.DataFrame) -> Dict[str, float]:
    """Train RandomForest model for moon predictions"""
    try:
        # Filter for moon alerts only
        moon_data = training_data[training_data['alert_type'] == 'MOON'].copy()
        
        if len(moon_data) < 20:
            logger.warning("Insufficient moon training data")
            return {"accuracy": 0, "precision": 0, "recall": 0, "f1": 0}
        
        # Prepare features
        feature_columns = [
            'confidence_score', 'technical_score', 'news_sentiment_score',
            'social_sentiment_score', 'earnings_score', 'pattern_confidence'
        ]
        
        X = moon_data[feature_columns].fillna(50.0)  # Fill missing with neutral
        y = moon_data['success']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0)
        }
        
        # Cross-validation
        cv_scores = cross_val_score(model, X, y, cv=5)
        metrics["cv_accuracy"] = cv_scores.mean()
        metrics["cv_std"] = cv_scores.std()
        
        # Save model
        model_path = os.path.join(settings.MODEL_DIR, "moon_model.pkl")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        logger.info(f"Moon model trained: {metrics['accuracy']:.3f} accuracy")
        return metrics
        
    except Exception as e:
        logger.error(f"Error training moon model: {e}")
        return {"accuracy": 0, "precision": 0, "recall": 0, "f1": 0}


def _train_rug_model(training_data: pd.DataFrame) -> Dict[str, float]:
    """Train RandomForest model for rug predictions"""
    try:
        # Filter for rug alerts only
        rug_data = training_data[training_data['alert_type'] == 'RUG'].copy()
        
        if len(rug_data) < 20:
            logger.warning("Insufficient rug training data")
            return {"accuracy": 0, "precision": 0, "recall": 0, "f1": 0}
        
        # Prepare features
        feature_columns = [
            'confidence_score', 'technical_score', 'news_sentiment_score',
            'social_sentiment_score', 'earnings_score', 'pattern_confidence'
        ]
        
        X = rug_data[feature_columns].fillna(50.0)  # Fill missing with neutral
        y = rug_data['success']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0)
        }
        
        # Cross-validation
        cv_scores = cross_val_score(model, X, y, cv=5)
        metrics["cv_accuracy"] = cv_scores.mean()
        metrics["cv_std"] = cv_scores.std()
        
        # Save model
        model_path = os.path.join(settings.MODEL_DIR, "rug_model.pkl")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        logger.info(f"Rug model trained: {metrics['accuracy']:.3f} accuracy")
        return metrics
        
    except Exception as e:
        logger.error(f"Error training rug model: {e}")
        return {"accuracy": 0, "precision": 0, "recall": 0, "f1": 0}


def _update_performance_tracking(moon_metrics: Dict, rug_metrics: Dict):
    """Update model performance tracking in database"""
    db = next(get_db())
    
    try:
        # This would store performance metrics in a dedicated table
        # For now, just log the metrics
        logger.info(f"Moon model performance: {moon_metrics}")
        logger.info(f"Rug model performance: {rug_metrics}")
        
        # TODO: Create ModelPerformance table to track metrics over time
        
    except Exception as e:
        logger.error(f"Error updating performance tracking: {e}")
    finally:
        db.close()


def _update_pending_outcomes(cutoff_date: datetime) -> int:
    """Update outcomes for pending alerts by checking actual price movements"""
    db = next(get_db())
    updated_count = 0
    
    try:
        # Get pending alerts older than cutoff
        pending_alerts = db.query(AnalysisResult).filter(
            and_(
                AnalysisResult.alert_outcome == AlertOutcome.PENDING,
                AnalysisResult.timestamp <= cutoff_date,
                AnalysisResult.alert_type.in_([AlertType.MOON, AlertType.RUG])
            )
        ).all()
        
        for alert in pending_alerts:
            try:
                # Check actual price movement
                outcome = _check_price_movement(alert)
                
                if outcome:
                    alert.alert_outcome = outcome['outcome']
                    alert.actual_move_percent = outcome['move_percent']
                    alert.days_to_move = outcome['days_to_move']
                    alert.outcome_timestamp = datetime.now()
                    alert.outcome_notes = outcome.get('notes', '')
                    
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Error updating outcome for alert {alert.id}: {e}")
                continue
        
        db.commit()
        logger.info(f"Updated {updated_count} alert outcomes")
        
    except Exception as e:
        logger.error(f"Error updating pending outcomes: {e}")
        db.rollback()
    finally:
        db.close()
    
    return updated_count


def _check_price_movement(alert: AnalysisResult) -> Optional[Dict[str, Any]]:
    """Check actual price movement for an alert"""
    try:
        # This would use yfinance or another data source to check actual price movement
        # For now, simulate the outcome checking
        
        import random
        
        # Simulate checking price movement
        # In production, this would fetch actual price data
        
        if alert.alert_type == AlertType.MOON:
            # Simulate moon outcome (60% success rate for demo)
            if random.random() < 0.6:
                move_percent = random.uniform(20, 50)  # Successful moon
                outcome = AlertOutcome.SUCCESS
            else:
                move_percent = random.uniform(-10, 15)  # Failed moon
                outcome = AlertOutcome.FAILURE if move_percent < 10 else AlertOutcome.PARTIAL
        else:  # RUG
            # Simulate rug outcome (55% success rate for demo)
            if random.random() < 0.55:
                move_percent = random.uniform(-50, -20)  # Successful rug
                outcome = AlertOutcome.SUCCESS
            else:
                move_percent = random.uniform(-15, 10)  # Failed rug
                outcome = AlertOutcome.FAILURE if move_percent > -10 else AlertOutcome.PARTIAL
        
        days_to_move = random.randint(1, 3)
        
        return {
            'outcome': outcome,
            'move_percent': move_percent,
            'days_to_move': days_to_move,
            'notes': f'Simulated outcome check on {datetime.now().strftime("%Y-%m-%d")}'
        }
        
    except Exception as e:
        logger.error(f"Error checking price movement: {e}")
        return None
