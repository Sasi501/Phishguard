"""
PhishGuard — ML Model Reproducibility Verifier
Trains two CatBoost classifiers on the same dataset subset with identical seeds
and verifies that they produce bit-identical evaluations and classification decisions.
"""
import os
import sys
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.model_selection import train_test_split

# Paths
ML_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(ML_DIR, "data", "dataset.csv")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.feature_extractor import extract_features, FEATURE_NAMES

def verify_reproducibility():
    print("=" * 60)
    print("PhishGuard — ML Model Reproducibility Verification")
    print("=" * 60)

    if not os.path.exists(DATASET_PATH):
        print(f"[!] Dataset not found at {DATASET_PATH}")
        sys.exit(1)

    # Load a small slice of the dataset for testing reproducibility quickly
    print(f"[*] Loading dataset from {DATASET_PATH}")
    dataset = pd.read_csv(DATASET_PATH)
    print(f"[+] Loaded dataset. Sampling 1000 items to verify reproducibility...")
    sample = dataset.sample(n=min(1000, len(dataset)), random_state=42)

    # Extract features
    print("[*] Extracting features...")
    features = []
    for url in sample["url"]:
        try:
            features.append(extract_features(url))
        except Exception:
            features.append({name: 0 for name in FEATURE_NAMES})

    X = pd.DataFrame(features)
    y = sample["label"].values

    # Train/test split with deterministic state
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Common params
    params = {
        "iterations": 100,
        "learning_rate": 0.05,
        "depth": 6,
        "random_seed": 1337,
        "verbose": 0,
        "auto_class_weights": "Balanced"
    }

    print("\n[*] Training Model A...")
    model_a = CatBoostClassifier(**params)
    model_a.fit(X_train, y_train)

    print("[*] Training Model B...")
    model_b = CatBoostClassifier(**params)
    model_b.fit(X_train, y_train)

    # Predictions
    preds_a = model_a.predict_proba(X_test)[:, 1]
    preds_b = model_b.predict_proba(X_test)[:, 1]

    # Check identical prediction probabilities
    diff = np.max(np.abs(preds_a - preds_b))
    print(f"\n[*] Maximum absolute difference in predictions: {diff:.12f}")

    # Check feature importances
    imp_a = model_a.get_feature_importance()
    imp_b = model_b.get_feature_importance()
    imp_diff = np.max(np.abs(imp_a - imp_b))
    print(f"[*] Maximum absolute difference in feature importances: {imp_diff:.12f}")

    success = (diff == 0.0) and (imp_diff == 0.0)
    
    if success:
        print(f"\n[+] SUCCESS: Both models trained identically! (Reproducibility: 100%)")
        # Save verification metrics report
        report = {
            "reproducible": True,
            "max_pred_difference": float(diff),
            "max_importance_difference": float(imp_diff),
            "random_seed": params["random_seed"]
        }
        report_path = os.path.join(ML_DIR, "models", "reproducibility_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"[+] Verification report saved to: {report_path}")
        return True
    else:
        print(f"\n[!] WARNING: Model predictions are not identical! Difference: {diff}")
        return False

if __name__ == "__main__":
    success = verify_reproducibility()
    sys.exit(0 if success else 1)
