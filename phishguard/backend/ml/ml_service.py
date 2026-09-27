"""
PhishGuard — ML Service
Loads the trained CatBoost model and provides predictions for the Django backend.
Singleton pattern ensures the model is loaded once and reused.
"""

import os
import json

import numpy as np
from catboost import CatBoostClassifier

from .feature_extractor import (
    UNMODELED_FEATURE_NAMES,
    extract_features,
    validate_model_schema,
)


# Paths
ML_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(ML_DIR, "models", "catboost_model.cbm")
METRICS_PATH = os.path.join(ML_DIR, "models", "metrics.json")


class MLPredictor:
    """Singleton ML predictor — loads model once, reuses for all requests."""

    _instance = None
    _model = None
    _metrics = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        """Load the CatBoost model from disk."""
        if self._model is not None:
            return

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"ML model not found at {MODEL_PATH}. "
                "Run train_model.py first!"
            )

        print(f"[PhishGuard ML] Loading CatBoost model from {MODEL_PATH}")
        model = CatBoostClassifier()
        model.load_model(MODEL_PATH)

        # The trained model is the authoritative feature schema. Fail loudly
        # on any drift instead of silently feeding a differently-ordered or
        # differently-sized vector to the model.
        self._feature_names = validate_model_schema(model.feature_names_)
        self._model = model

        print(
            "[PhishGuard ML] Model loaded successfully "
            f"({len(self._feature_names)} features)."
        )

        # Load metrics if available
        if os.path.exists(METRICS_PATH):
            with open(METRICS_PATH, "r") as f:
                self._metrics = json.load(f)

    def predict(self, url: str) -> dict:
        """
        Predict phishing probability for a single URL.

        Returns:
            {
                "ml_score": float (0.0 to 1.0, probability of phishing),
                "ml_risk_level": "safe" | "suspicious" | "phishing",
                "ml_features": { feature_name: value, ... },   # model inputs only
                "ml_unmodeled_features": { feature_name: value, ... },  # analysis only
                "shap_features": [ { "feature": name, "value": val,
                                     "shap_value": sv }, ... ]  # model inputs only
            }
        """
        self._load_model()

        # Extract features and build the vector in the model's own order.
        features = extract_features(url)
        model_names = self._feature_names
        feature_values = [features[name] for name in model_names]

        # Predict
        prob = self._model.predict_proba([feature_values])[0]
        phishing_prob = float(prob[1])  # Probability of class 1 (phishing)

        # Classify
        if phishing_prob >= 0.7:
            risk_level = "phishing"
        elif phishing_prob >= 0.4:
            risk_level = "suspicious"
        else:
            risk_level = "safe"

        # SHAP Explainability Integration
        try:
            import shap
            explainer = shap.TreeExplainer(self._model)
            shap_vals = explainer.shap_values([feature_values])[0]
            
            # Combine feature names, values, and their SHAP contributions
            shap_contributions = [
                {
                    "feature": name,
                    "value": features[name],
                    "shap_value": round(float(val), 4),
                }
                for name, val in zip(model_names, shap_vals)
            ]
            
            # For phishing, we want to explain what pushed the score UP (positive shap_value)
            top_features = sorted(
                [f for f in shap_contributions if f["shap_value"] > 0],
                key=lambda x: x["shap_value"],
                reverse=True,
            )[:3] # Top 3 SHAP features
            
            if not top_features:
                # Fallback to absolute magnitude if nothing pushed it up significantly
                top_features = sorted(
                    shap_contributions,
                    key=lambda x: abs(x["shap_value"]),
                    reverse=True,
                )[:3]
                
        except ImportError:
            # Fallback if shap isn't installed
            feature_importance = self._model.get_feature_importance()
            top_features = sorted(
                [
                    {
                        "feature": name,
                        "value": features[name],
                        "importance": round(float(imp), 2),
                    }
                    for name, imp in zip(model_names, feature_importance)
                ],
                key=lambda x: x.get("importance", 0),
                reverse=True,
            )[:3]

        return {
            "ml_score": round(phishing_prob, 4),
            "ml_risk_level": risk_level,
            # Exactly the features the model consumed, in the model's order.
            "ml_features": {name: features[name] for name in model_names},
            # URL-analysis signals the trained model does NOT use. Kept
            # separate so they can never be mistaken for model evidence.
            "ml_unmodeled_features": {
                name: features[name] for name in UNMODELED_FEATURE_NAMES
            },
            "shap_features": top_features,
        }

    def get_metrics(self) -> dict:
        """Return training metrics if available."""
        self._load_model()
        return self._metrics or {}

    def is_available(self) -> bool:
        """Check if the ML model file exists."""
        return os.path.exists(MODEL_PATH)


# Module-level singleton
_predictor = MLPredictor()


def predict_url(url: str) -> dict:
    """Convenience function — predict phishing probability for a URL."""
    return _predictor.predict(url)


def is_ml_available() -> bool:
    """Check if the ML model is ready."""
    return _predictor.is_available()
