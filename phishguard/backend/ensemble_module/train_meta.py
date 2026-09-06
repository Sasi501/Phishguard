"""
Train a simple meta-learner for the ensemble fusion engine.

Usage:
  python train_meta.py --input labeled_signals.csv --output models/meta_learner.pkl

Expected CSV columns (example): ml_score,nlp_score,vision_score,domain_score,label
Where label is 0 (safe) or 1 (phishing).

If no input provided, the script will generate a small synthetic dataset for demonstration.
"""
import argparse
import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier


def load_csv(path):
    import csv
    X = []
    y = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            X.append([
                float(r.get('ml_score', 0.0)),
                float(r.get('nlp_score', 0.0)),
                float(r.get('vision_score', 0.0)),
                float(r.get('domain_score', 0.0)),
            ])
            y.append(int(r.get('label', 0)))
    return np.array(X), np.array(y)


def synth_dataset(n=200):
    rng = np.random.RandomState(42)
    X = rng.rand(n, 4)
    # define labels roughly: high ml and domain increase phishing probability
    y = ((X[:,0] > 0.7) | (X[:,3] > 0.6) | ((X[:,1] > 0.6) & (X[:,2] > 0.5))).astype(int)
    return X, y


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', help='CSV of labeled signals')
    p.add_argument('--output', default=os.path.join(os.path.dirname(__file__), 'models', 'meta_learner.pkl'))
    args = p.parse_args()

    if args.input and os.path.exists(args.input):
        X, y = load_csv(args.input)
    else:
        print('No input CSV provided or not found; generating synthetic dataset for demo')
        X, y = synth_dataset(500)

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    joblib.dump(clf, args.output)
    print('Saved meta-learner to', args.output)

if __name__ == '__main__':
    main()
