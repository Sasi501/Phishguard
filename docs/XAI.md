# Explainable AI

The XAI Investigation Center is implemented in `frontend/src/components/XAIPanel.tsx`. It provides user and analyst views for:

- final ensemble risk separately from engine signals;
- risk and safety factors;
- URL anatomy and provenance;
- feature attribution using backend-reported method labels;
- redirect evidence;
- Domain/TI metadata and availability;
- engine status and limitations.

The UI does not convert fusion weights into per-scan contributions and does not fabricate unavailable attribution. Domain and threat evidence are additive fields assembled from existing analysis results.

## URL ML score semantics

The backend invokes URL ML once per analysis and reuses that inference result. The raw CatBoost phishing probability (`ml_result.ml_score`) can differ from the URL ML engine signal in the existing complete-scan fallback path: if domain age is available, the existing fusion path may moderate `scores['ml']` before forming its engine signal. XAI must not describe the raw probability as if it were the engine signal.

When raw inference is present, the additive `xai.url_ml_evidence` object labels:

- `raw_model_probability_percent`: raw URL model inference;
- `engine_signal_percent`: the URL signal used by the engine result and fusion;
- `engine_signal_adjustment`: identifies existing domain-age moderation when the values differ.

The panel labels the URL ML engine signal, raw model probability, and final ensemble risk separately. The engine signal should agree with the `url_ml` structured engine signal and the corresponding `individual_scores_percent` value. Legacy results without the additive fields remain readable using their existing structured engine signals. SHAP and feature-importance evidence retain their original semantics and are not converted into score contributions.

Live `https://example.com` verification observed raw CatBoost probability **98.59%**, moderated URL ML engine signal **4.93%**, and final ensemble risk **1.73% / Safe**. The exact example is environment/model-output evidence, not a fixed expected output for future scans.
