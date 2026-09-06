"""
PhishGuard — CatBoost → ONNX Exporter
Exports the trained CatBoost URL classifier to ONNX format for use
in the Chrome extension via onnxruntime-web.

Usage:
    python backend/ml/export_onnx.py

Output:
    extension/model/phishguard_url_classifier.onnx
"""
import os
import sys
import json

ML_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(ML_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
MODEL_PATH = os.path.join(ML_DIR, "models", "catboost_model.cbm")
OUTPUT_DIR = os.path.join(ROOT_DIR, "extension", "model")
OUTPUT_ONNX = os.path.join(OUTPUT_DIR, "phishguard_url_classifier.onnx")
META_FILE = os.path.join(OUTPUT_DIR, "model_meta.json")

sys.path.insert(0, BACKEND_DIR)


def export():
    print("=" * 60)
    print("PhishGuard -- CatBoost -> ONNX Export")
    print("=" * 60)

    if not os.path.exists(MODEL_PATH):
        print(f"[!] CatBoost model not found at {MODEL_PATH}")
        print("    Run backend/ml/train_model.py first.")
        sys.exit(1)

    print(f"[*] Loading CatBoost model from: {MODEL_PATH}")
    from catboost import CatBoostClassifier
    model = CatBoostClassifier()
    model.load_model(MODEL_PATH)
    print("[+] Model loaded successfully.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"[*] Exporting to ONNX: {OUTPUT_ONNX}")
    model.save_model(
        OUTPUT_ONNX,
        format="onnx",
        export_parameters={
            "onnx_domain": "ai.catboost",
            "onnx_model_version": 1,
            "onnx_doc_string": "PhishGuard URL Phishing Classifier",
            "onnx_graph_name": "PhishGuardURLClassifier"
        }
    )
    print(f"[+] ONNX model exported: {OUTPUT_ONNX}")
    print(f"    File size: {os.path.getsize(OUTPUT_ONNX) / 1024:.1f} KB")

    # Export feature names so the JS knows the correct input order
    from ml.feature_extractor import FEATURE_NAMES
    meta = {
        "feature_names": FEATURE_NAMES,
        "num_features": len(FEATURE_NAMES),
        "model_file": "phishguard_url_classifier.onnx",
        "input_name": "features",
        "classes": ["safe", "phishing"],
        "thresholds": {
            "phishing": 0.70,
            "suspicious": 0.40
        }
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[+] Model metadata saved: {META_FILE}")
    print(f"    Features ({len(FEATURE_NAMES)}): {', '.join(FEATURE_NAMES)}")

    print("\n" + "=" * 60)
    print("EXPORT COMPLETE!")
    print("=" * 60)
    print("    Load in extension with:")
    print("  const session = await InferenceSession.create('model/phishguard_url_classifier.onnx')")


if __name__ == "__main__":
    export()
