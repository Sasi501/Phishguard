"""
PhishGuard — CatBoost Model Trainer
Trains a CatBoost classifier on URL features for phishing detection.
Includes evaluation metrics and SHAP explainability.
"""

import os
import sys
import json
import time
import warnings

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, classification_report,
    confusion_matrix,
)

warnings.filterwarnings("ignore")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.feature_extractor import extract_features, FEATURE_NAMES

# Paths
ML_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ML_DIR, "data")
MODEL_DIR = os.path.join(ML_DIR, "models")
DATASET_PATH = os.path.join(DATA_DIR, "dataset.csv")
MODEL_PATH = os.path.join(MODEL_DIR, "catboost_model.cbm")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")


def extract_all_features(urls, labels=None):
    """Extract features for a list of URLs with progress tracking."""
    print(f"[*] Extracting features for {len(urls)} URLs...")
    features = []
    errors = 0
    start = time.time()

    for i, url in enumerate(urls):
        if (i + 1) % 5000 == 0 or i == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"    Progress: {i+1}/{len(urls)} ({rate:.0f} URLs/sec)")
        try:
            feats = extract_features(url)
            features.append(feats)
        except Exception:
            errors += 1
            # Use zeros for failed extractions
            features.append({name: 0 for name in FEATURE_NAMES})

    elapsed = time.time() - start
    print(f"[+] Feature extraction complete in {elapsed:.1f}s ({errors} errors)")

    df = pd.DataFrame(features)
    return df


def train_model():
    """Train CatBoost model on the dataset."""
    print("=" * 60)
    print("PhishGuard — Model Training")
    print("=" * 60)

    # Check dataset exists
    if not os.path.exists(DATASET_PATH):
        print(f"[!] Dataset not found at {DATASET_PATH}")
        print("[*] Run download_data.py first!")
        sys.exit(1)

    # Load dataset
    print(f"\n[*] Loading dataset from {DATASET_PATH}")
    dataset = pd.read_csv(DATASET_PATH)
    print(f"[+] Loaded {len(dataset)} URLs")
    print(f"    Phishing: {len(dataset[dataset['label'] == 1])}")
    print(f"    Legitimate: {len(dataset[dataset['label'] == 0])}")

    # Extract features
    print()
    X = extract_all_features(dataset["url"].tolist())
    y = dataset["label"].values

    # Train/test split
    print(f"\n[*] Splitting data 80/20...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"    Train: {len(X_train)} | Test: {len(X_test)}")

    # Create CatBoost pools
    train_pool = Pool(X_train, y_train, feature_names=FEATURE_NAMES)
    test_pool = Pool(X_test, y_test, feature_names=FEATURE_NAMES)

    # Train CatBoost
    print(f"\n[*] Training CatBoost classifier...")
    model = CatBoostClassifier(
        iterations=1000,
        learning_rate=0.05,
        depth=8,
        l2_leaf_reg=3,
        eval_metric="AUC",
        random_seed=42,
        verbose=100,
        early_stopping_rounds=50,
        auto_class_weights="Balanced",
    )

    model.fit(
        train_pool,
        eval_set=test_pool,
        use_best_model=True,
    )

    # Evaluate
    print(f"\n{'=' * 60}")
    print("EVALUATION RESULTS")
    print(f"{'=' * 60}")

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_prob)

    print(f"\n  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  ROC-AUC:   {roc_auc:.4f}")

    print(f"\n  Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Legitimate", "Phishing"]))

    cm = confusion_matrix(y_test, y_pred)
    print(f"  Confusion Matrix:")
    print(f"    TN={cm[0][0]:>6}  FP={cm[0][1]:>6}")
    print(f"    FN={cm[1][0]:>6}  TP={cm[1][1]:>6}")

    # Feature importance
    print(f"\n  Feature Importance (CatBoost):")
    importances = model.get_feature_importance()
    feat_imp = sorted(
        zip(FEATURE_NAMES, importances),
        key=lambda x: x[1],
        reverse=True,
    )
    for name, imp in feat_imp:
        bar = "#" * int(imp / 2)
        print(f"    {name:25s} {imp:6.2f}  {bar}")

    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_model(MODEL_PATH)
    print(f"\n[+] Model saved to: {MODEL_PATH}")

    # Save metrics
    metrics = {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "feature_importance": {name: round(float(imp), 4) for name, imp in feat_imp},
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"[+] Metrics saved to: {METRICS_PATH}")

    # SHAP explainability
    print(f"\n[*] Generating SHAP explanations...")
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        # Use a sample for SHAP (full dataset is slow)
        sample_size = min(500, len(X_test))
        X_sample = X_test.iloc[:sample_size]
        shap_values = explainer.shap_values(X_sample)

        # Save mean absolute SHAP values
        mean_shap = np.abs(shap_values).mean(axis=0)
        shap_importance = {
            name: round(float(val), 4)
            for name, val in sorted(
                zip(FEATURE_NAMES, mean_shap),
                key=lambda x: x[1],
                reverse=True,
            )
        }
        metrics["shap_importance"] = shap_importance
        with open(METRICS_PATH, "w") as f:
            json.dump(metrics, f, indent=2)

        print(f"[+] SHAP importance:")
        for name, val in shap_importance.items():
            bar = "#" * int(val * 20)
            print(f"    {name:25s} {val:6.4f}  {bar}")

    except Exception as e:
        print(f"[!] SHAP generation failed: {e}")

    print(f"\n{'=' * 60}")
    print("TRAINING COMPLETE!")
    print(f"{'=' * 60}")

    return model


if __name__ == "__main__":
    train_model()
