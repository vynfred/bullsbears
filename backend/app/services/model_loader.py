"""
ML Model Loading Service
Efficient caching and loading of trained ML models with versioning and fallback mechanisms.
"""

import asyncio
import logging
import joblib
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    """Information about a loaded model"""
    model_type: str  # 'moon' or 'rug'
    version: str
    accuracy: float
    features: List[str]
    loaded_at: datetime
    file_path: str
    is_ensemble: bool = False
    base_models: Optional[Dict[str, Any]] = None
    ensemble_accuracy: Optional[float] = None
    individual_accuracies: Optional[Dict[str, float]] = None

class ModelLoader:
    """
    Service for loading and caching trained ML models.
    Provides efficient model access with health checks and fallback mechanisms.
    """
    
    def __init__(self, models_dir: str = "data/models"):
        self.models_dir = Path(models_dir)
        self.cached_models = {}
        self.model_metadata = {}
        self.shap_explainer = None
        self.confidence_threshold = 0.70  # Adjusted for ensemble models

        # Ensure models directory exists
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
    async def load_models(self) -> bool:
        """
        Load all available ML models into memory cache.
        
        Returns:
            bool: True if models loaded successfully, False otherwise
        """
        try:
            logger.info("🚀 Loading ML models into cache...")
            
            # Find latest model files - prioritize ensemble models
            moon_model_file = self._find_latest_model_file("moon_ensemble", "moon_model")
            rug_model_file = self._find_latest_model_file("rug_ensemble", "rug_model")
            shap_file = self._find_latest_model_file("shap_explainer")
            
            if not moon_model_file or not rug_model_file:
                logger.error("❌ Required model files not found")
                return False
            
            # Load moon model
            moon_success = await self._load_single_model("moon", moon_model_file)
            
            # Load rug model  
            rug_success = await self._load_single_model("rug", rug_model_file)
            
            # Load SHAP explainer (optional)
            if shap_file:
                try:
                    self.shap_explainer = joblib.load(shap_file)
                    logger.info("✅ SHAP explainer loaded successfully")
                except Exception as e:
                    logger.warning(f"⚠️  SHAP explainer failed to load: {e}")
            
            success = moon_success and rug_success
            
            if success:
                logger.info("🎉 All ML models loaded successfully!")
                logger.info(f"🌙 Moon model: {self.model_metadata['moon'].accuracy:.1%} accuracy")
                logger.info(f"💥 Rug model: {self.model_metadata['rug'].accuracy:.1%} accuracy")
                logger.info(f"🎯 Confidence threshold: {self.confidence_threshold:.0%}")
            else:
                logger.error("❌ Failed to load required models")
                
            return success
            
        except Exception as e:
            logger.error(f"💥 Model loading failed: {e}")
            return False
    
    async def _load_single_model(self, model_type: str, model_file: Path) -> bool:
        """Load a single model and its metadata."""
        try:
            # Load the model
            model = joblib.load(model_file)

            # Check if this is an ensemble model
            is_ensemble = "ensemble" in model_file.stem

            # Load metadata - handle ensemble and legacy formats
            if is_ensemble:
                # Ensemble format: moon_ensemble_20251102_165030_ensemble.joblib
                # Metadata format: moon_ensemble_20251102_165030_ensemble_metadata.json
                metadata_file = model_file.parent / f"{model_file.stem}_metadata.json"
            elif "calibrated" in model_file.stem:
                # New calibrated model format: moon_model_fixed_20251102_163817_calibrated.joblib
                base_name = model_file.stem.replace("_calibrated", "")
                metadata_file = model_file.parent / f"{base_name}_metadata.json"
            else:
                # Old format: moon_model_v20251102_155922.joblib
                version_part = "_".join(model_file.stem.split('_')[-2:])
                metadata_file = model_file.parent / f"{model_type}_metadata_{version_part}.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

                # Extract version from filename
                if is_ensemble:
                    version = model_file.stem.split('_')[-2]  # Get timestamp from ensemble filename
                elif "calibrated" in model_file.stem:
                    version = model_file.stem.split('_')[-2]  # Get timestamp part
                else:
                    version = model_file.stem.split('_')[-1]

                # Handle ensemble vs single model metadata
                if is_ensemble:
                    training_metrics = metadata.get('training_metrics', {})
                    accuracy = training_metrics.get('ensemble_accuracy', 0.0)
                    features = metadata.get('feature_names', [])

                    # Load individual base models for agreement scoring
                    base_models = {}
                    individual_accuracies = {}
                    individual_paths = metadata.get('individual_model_paths', {})

                    for model_name, model_path in individual_paths.items():
                        try:
                            base_model_file = self.models_dir / Path(model_path).name
                            if base_model_file.exists():
                                base_models[model_name] = joblib.load(base_model_file)
                                # Get individual accuracy from metadata
                                individual_metrics = training_metrics.get('individual_models', {}).get(model_name, {})
                                individual_accuracies[model_name] = individual_metrics.get('accuracy', 0.0)
                                logger.info(f"✅ Loaded base model {model_name}: {individual_accuracies[model_name]:.1%} accuracy")
                        except Exception as e:
                            logger.warning(f"⚠️  Failed to load base model {model_name}: {e}")

                    model_info = ModelInfo(
                        model_type=model_type,
                        version=version,
                        accuracy=accuracy,
                        features=features,
                        loaded_at=datetime.now(),
                        file_path=str(model_file),
                        is_ensemble=True,
                        base_models=base_models,
                        ensemble_accuracy=accuracy,
                        individual_accuracies=individual_accuracies
                    )
                else:
                    # Handle single model metadata formats
                    training_metrics = metadata.get('training_metrics', {})
                    accuracy = training_metrics.get('cv_accuracy_mean', metadata.get('cv_accuracy', 0.0))
                    features = metadata.get('feature_names', metadata.get('selected_features', []))

                    model_info = ModelInfo(
                        model_type=model_type,
                        version=version,
                        accuracy=accuracy,
                        features=features,
                        loaded_at=datetime.now(),
                        file_path=str(model_file)
                    )
            else:
                logger.warning(f"⚠️  Metadata file not found for {model_type} model")
                model_info = ModelInfo(
                    model_type=model_type,
                    version="unknown",
                    accuracy=0.0,
                    features=[],
                    loaded_at=datetime.now(),
                    file_path=str(model_file),
                    is_ensemble=is_ensemble
                )
            
            # Cache the model and metadata
            self.cached_models[model_type] = model
            self.model_metadata[model_type] = model_info

            if is_ensemble:
                logger.info(f"✅ {model_type.title()} ensemble loaded: {model_info.accuracy:.1%} accuracy ({len(model_info.base_models or {})} base models)")
            else:
                logger.info(f"✅ {model_type.title()} model loaded: {model_info.accuracy:.1%} accuracy")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load {model_type} model: {e}")
            return False
    
    def _find_latest_model_file(self, *prefixes: str) -> Optional[Path]:
        """Find the latest model file with given prefixes, prioritizing ensemble models."""
        try:
            for prefix in prefixes:
                # First, look for ensemble models
                if "ensemble" in prefix:
                    ensemble_files = list(self.models_dir.glob(f"{prefix}_*_ensemble.joblib"))
                    if ensemble_files:
                        logger.info(f"🎯 Found {len(ensemble_files)} ensemble {prefix} models")
                        latest_file = max(ensemble_files, key=lambda f: f.stat().st_mtime)
                        logger.info(f"✅ Using ensemble model: {latest_file.name}")
                        return latest_file

                # Then, look for calibrated fixed models
                calibrated_files = list(self.models_dir.glob(f"{prefix}_fixed_*_calibrated.joblib"))
                if calibrated_files:
                    logger.info(f"🎯 Found {len(calibrated_files)} calibrated {prefix} models")
                    latest_file = max(calibrated_files, key=lambda f: f.stat().st_mtime)
                    logger.info(f"✅ Using calibrated model: {latest_file.name}")
                    return latest_file

                # Fallback to old model files
                model_files = list(self.models_dir.glob(f"{prefix}_*.joblib"))
                if model_files:
                    # Sort by modification time, return latest
                    latest_file = max(model_files, key=lambda f: f.stat().st_mtime)
                    logger.warning(f"⚠️  Using legacy model (not calibrated): {latest_file.name}")
                    return latest_file

            return None

        except Exception as e:
            logger.error(f"Error finding model files: {e}")
            return None
    
    async def predict_moon(self, features: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        """
        Predict moon probability using cached model.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Tuple of (confidence, prediction_details)
        """
        return await self._predict_with_model("moon", features)
    
    async def predict_rug(self, features: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        """
        Predict rug probability using cached model.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Tuple of (confidence, prediction_details)
        """
        return await self._predict_with_model("rug", features)
    
    async def _predict_with_model(self, model_type: str, features: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        """Internal method to make predictions with cached models."""
        try:
            if model_type not in self.cached_models:
                logger.error(f"❌ {model_type} model not loaded")
                return 0.0, {"error": "Model not loaded"}

            model = self.cached_models[model_type]
            model_info = self.model_metadata[model_type]

            # Prepare feature vector
            feature_vector = self._prepare_feature_vector(features, model_info.features)

            if feature_vector is None:
                return 0.0, {"error": "Feature preparation failed"}

            # TEMPORARY FIX: Use RandomForest-only predictions to avoid LogisticRegression overfitting
            if model_info.is_ensemble and model_info.base_models and 'random_forest' in model_info.base_models:
                logger.info(f"🌲 Using RandomForest-only prediction for {model_type} (LogisticRegression temporarily disabled)")

                # Use only RandomForest from the ensemble
                rf_model = model_info.base_models['random_forest']
                feature_df = pd.DataFrame([feature_vector], columns=model_info.features)
                prediction_proba = rf_model.predict_proba(feature_df)

                if prediction_proba.shape[1] > 1:
                    confidence = prediction_proba[0][1]  # Positive class probability
                else:
                    confidence = prediction_proba[0][0]  # Single class prediction
            else:
                # Fallback to full ensemble if RandomForest not available
                prediction_proba = model.predict_proba([feature_vector])

                # Get confidence (probability of positive class)
                if prediction_proba.shape[1] > 1:
                    confidence = prediction_proba[0][1]  # Probability of positive class
                else:
                    confidence = prediction_proba[0][0]  # Single class prediction

            # Prepare prediction details
            prediction_details = {
                "model_type": model_type,
                "model_version": model_info.version,
                "model_accuracy": model_info.accuracy,
                "raw_confidence": float(confidence),
                "threshold": self.confidence_threshold,
                "above_threshold": confidence >= self.confidence_threshold,
                "features_used": len(model_info.features),
                "prediction_time": datetime.now().isoformat(),
                "is_ensemble": model_info.is_ensemble,
                "using_rf_only": model_info.is_ensemble and model_info.base_models and 'random_forest' in model_info.base_models
            }

            # Add ensemble-specific details (MODIFIED: RandomForest-only mode)
            if model_info.is_ensemble and model_info.base_models:
                individual_predictions = {}
                individual_probabilities = []

                # Get predictions from individual base models
                feature_df = pd.DataFrame([dict(zip(model_info.features, feature_vector))],
                                        columns=model_info.features)

                # TEMPORARY: Only show RandomForest predictions, skip LogisticRegression
                for model_name, base_model in model_info.base_models.items():
                    if model_name == 'logistic':
                        logger.info(f"⚠️  Skipping {model_name} prediction (temporarily disabled due to overfitting)")
                        continue

                    try:
                        base_proba = base_model.predict_proba(feature_df)
                        base_confidence = base_proba[0][1] if base_proba.shape[1] > 1 else base_proba[0][0]
                        individual_predictions[model_name] = float(base_confidence)
                        individual_probabilities.append(base_confidence)
                    except Exception as e:
                        logger.warning(f"⚠️  Base model {model_name} prediction failed: {e}")
                        individual_predictions[model_name] = 0.0

                # Calculate model agreement (1.0 - std deviation of probabilities)
                if individual_probabilities:
                    agreement = 1.0 - np.std(individual_probabilities)
                    agreement = max(0.0, min(1.0, agreement))  # Clamp to [0, 1]
                else:
                    agreement = 0.0

                prediction_details.update({
                    "individual_predictions": individual_predictions,
                    "model_agreement": float(agreement),
                    "individual_accuracies": model_info.individual_accuracies or {},
                    "ensemble_accuracy": model_info.ensemble_accuracy
                })
            
            # Add SHAP explanation if available (for non-ensemble models)
            if self.shap_explainer and model_type == "moon" and not model_info.is_ensemble:
                try:
                    shap_values = self.shap_explainer.shap_values([feature_vector])
                    if isinstance(shap_values, list):
                        shap_values = shap_values[1]  # Positive class

                    # Get top contributing features
                    feature_importance = dict(zip(model_info.features, shap_values[0]))
                    top_features = sorted(feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:5]

                    prediction_details["top_contributing_features"] = [
                        {"feature": feat, "importance": float(imp)} for feat, imp in top_features
                    ]
                except Exception as e:
                    logger.warning(f"SHAP explanation failed: {e}")

            # For ensemble models, add feature importance from metadata
            elif model_info.is_ensemble:
                try:
                    # Load feature importance from ensemble metadata
                    metadata_file = Path(model_info.file_path).parent / f"{Path(model_info.file_path).stem.replace('_ensemble', '')}_ensemble_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)

                        feature_importance = metadata.get('training_metrics', {}).get('feature_importance', {})
                        if feature_importance:
                            # Get top 5 most important features
                            top_features = sorted(feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
                            prediction_details["top_contributing_features"] = [
                                {"feature": feat, "importance": float(imp)} for feat, imp in top_features
                            ]
                except Exception as e:
                    logger.warning(f"Feature importance extraction failed: {e}")

            return float(confidence), prediction_details
            
        except Exception as e:
            logger.error(f"💥 Prediction failed for {model_type}: {e}")
            return 0.0, {"error": str(e)}
    
    def _prepare_feature_vector(self, features: Dict[str, float], expected_features: List[str]) -> Optional[np.ndarray]:
        """Prepare feature vector for model prediction."""
        try:
            if not expected_features:
                # Fallback: use all provided features in alphabetical order
                expected_features = sorted(features.keys())
            
            # Create feature vector in correct order
            feature_vector = []
            missing_features = []
            
            for feature_name in expected_features:
                if feature_name in features:
                    value = features[feature_name]
                    # Handle NaN values
                    if pd.isna(value):
                        value = 0.0
                    feature_vector.append(float(value))
                else:
                    missing_features.append(feature_name)
                    feature_vector.append(0.0)  # Default value for missing features
            
            if missing_features:
                logger.warning(f"Missing features filled with 0.0: {missing_features[:5]}...")
            
            return np.array(feature_vector)
            
        except Exception as e:
            logger.error(f"Feature vector preparation failed: {e}")
            return None
    
    def get_model_health(self) -> Dict[str, Any]:
        """Get health status of loaded models."""
        health = {
            "models_loaded": len(self.cached_models),
            "models_available": ["moon", "rug"],
            "shap_available": self.shap_explainer is not None,
            "confidence_threshold": self.confidence_threshold,
            "last_check": datetime.now().isoformat()
        }
        
        for model_type in ["moon", "rug"]:
            if model_type in self.model_metadata:
                info = self.model_metadata[model_type]
                model_health = {
                    "loaded": True,
                    "version": info.version,
                    "accuracy": info.accuracy,
                    "features_count": len(info.features),
                    "loaded_at": info.loaded_at.isoformat(),
                    "is_ensemble": info.is_ensemble
                }

                # Add ensemble-specific information
                if info.is_ensemble:
                    model_health.update({
                        "ensemble_accuracy": info.ensemble_accuracy,
                        "base_models_count": len(info.base_models or {}),
                        "base_models": list((info.base_models or {}).keys()),
                        "individual_accuracies": info.individual_accuracies or {}
                    })

                health[f"{model_type}_model"] = model_health
            else:
                health[f"{model_type}_model"] = {"loaded": False}
        
        return health

# Global model loader instance
_model_loader = None

async def get_model_loader() -> ModelLoader:
    """Get or create global model loader instance."""
    global _model_loader
    
    if _model_loader is None:
        _model_loader = ModelLoader()
        await _model_loader.load_models()
    
    return _model_loader

async def predict_moon_ml(features: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
    """Convenience function for moon prediction."""
    loader = await get_model_loader()
    return await loader.predict_moon(features)

async def predict_rug_ml(features: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
    """Convenience function for rug prediction."""
    loader = await get_model_loader()
    return await loader.predict_rug(features)
