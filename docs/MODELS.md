# Models and evaluation

## URL ML

CatBoost URL classification is loaded by `backend/ml/ml_service.py`. The repository artifact `backend/ml/models/metrics.json` records held-out metrics from `backend/ml/train_model.py`: 79,996 training samples, 20,000 test samples, and an 80/20 split.

The saved metrics are accuracy 0.979 (97.90%), precision 0.988 (98.80%), recall 0.9699 (96.99%), F1 0.9789 (97.89%), and ROC-AUC 0.9963 (99.63%). These are **URL ML model held-out evaluation metrics only**. They are not overall PhishGuard accuracy, ensemble accuracy, extension accuracy, or live-scan accuracy.

`train_model.py` rounds saved metric fractions to four decimal places. The repository artifact therefore cannot substantiate additional precision such as 97.905%, 98.798%, 96.990%, 97.886%, or 99.634%; those extra digits should not be presented as verified without a more precise evaluation artifact.

## NLP and Vision

DistilBERT/NLP and EfficientNet-B3/Vision integration code exists, but no repository-backed held-out metrics artifact was found during the audit.

## Fusion

The meta-learner and weighted partial-fusion paths are integrated into `ensemble_module/fusion_engine.py`. No held-out ensemble calibration or performance report was found. In the existing no-meta-learner complete-scan fallback, domain-age moderation may adjust the URL ML engine score before fusion. This does not change the raw model output; XAI labels the raw probability, engine signal, and final ensemble separately.

## Reproducibility

`backend/ml/models/reproducibility_report.json` records identical predictions and feature importances for the repository reproducibility check with seed 1337. This is a reproducibility check, not a generalization metric.
