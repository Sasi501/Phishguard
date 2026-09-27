import os
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

ENSEMBLE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(ENSEMBLE_DIR, "models")
META_LEARNER_PATH = os.path.join(MODEL_DIR, "meta_learner.pkl")

def train_meta_learner():
    print("[PhishGuard Ensemble] Training Level-2 Meta-Learner (Logistic Regression)...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Dummy data for training the meta-learner
    # Features: [ml_score, nlp_score, vision_score, domain_score]
    # In a real scenario, this would be the out-of-fold predictions from validation set
    
    # 0 = Safe, 1 = Phishing
    X_train = np.array([
        [0.1, 0.2, 0.1, 0.1], # Safe
        [0.9, 0.8, 0.9, 0.9], # Phishing
        [0.8, 0.1, 0.8, 0.9], # Phishing (Vision/URL heavy)
        [0.2, 0.9, 0.1, 0.2], # Phishing (NLP heavy)
        [0.5, 0.5, 0.5, 0.5], # Borderline
        [0.1, 0.1, 0.1, 0.9], # Suspicious Domain
        [0.1, 0.1, 0.9, 0.1]  # Suspicious UI
    ])
    y_train = np.array([0, 1, 1, 1, 0, 1, 1])
    
    # Train Logistic Regression with L2 regularization
    clf = LogisticRegression(penalty='l2', C=1.0, solver='lbfgs', random_state=42)
    clf.fit(X_train, y_train)
    
    joblib.dump(clf, META_LEARNER_PATH)
    print(f"[PhishGuard Ensemble] Meta-Learner saved to {META_LEARNER_PATH}")
    print(f"[PhishGuard Ensemble] Learned weights (ML, NLP, Vision, Domain): {clf.coef_[0]}")

if __name__ == "__main__":
    train_meta_learner()
