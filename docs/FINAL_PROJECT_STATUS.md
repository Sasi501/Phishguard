# Final project status

## Classification

**READY WITH ENVIRONMENT LIMITATIONS**

The implementation and targeted live checks are complete. Backend tests, frontend build/lint, extension syntax/Manifest V3 checks, and XAI score-consistency verification passed. This is not a claim of production readiness, overall ensemble accuracy, or complete verification of database-backed workflows.

## Latest verification

- Backend `pytest -q`: **76 passed**, 7 dependency/framework deprecation warnings.
- Focused fusion/XAI tests: **15 passed**.
- Frontend `npm run build`: **passed**.
- Frontend `npm run lint`: **passed**, with the existing `URLAnatomy.tsx` Fast Refresh warning.
- Extension `node --check` for `src/background.js`, `src/content.js`, and `src/popup.js`: **passed**.
- Extension manifest: **Manifest V3 valid**.
- Extension runtime: **verified in isolated Microsoft Edge** with a real backend result and offline/retry test.
- Chrome extension runtime: **blocked** because managed developer-mode policy prevents unpacked loading.
- `git diff --check`: **passed**.

## Live public scan and score semantics

For the frontend scan of `https://example.com`:

| Quantity | Observed | Meaning |
|---|---:|---|
| Raw CatBoost probability | 98.59% | Raw probability emitted by URL ML inference |
| URL ML engine signal | 4.93% | Existing domain-age moderation was applied before this signal entered the fusion result; this is the value shown by the dashboard card, Evidence Matrix, XAI engine signal, and `individual_scores_percent` |
| Final ensemble risk | 1.73% / Safe | Backend-reported final fusion result; distinct from the raw probability and individual URL signal |

These figures are not interchangeable. The raw probability is explicitly labeled as raw inference; the URL ML engine signal is the existing adjusted signal; the ensemble is the final fused result. Feature importance/SHAP values are attribution evidence and are not risk-score contributions.

## URL ML held-out evaluation

The repository artifact `phishguard/backend/ml/models/metrics.json` records:

- Accuracy: **97.90%** (`0.979`)
- Precision: **98.80%** (`0.988`)
- Recall: **96.99%** (`0.9699`)
- F1: **97.89%** (`0.9789`)
- ROC-AUC: **99.63%** (`0.9963`)

These are **URL ML model held-out evaluation metrics only**. They are not overall PhishGuard accuracy, ensemble accuracy, extension accuracy, or live-scan accuracy. The artifact rounds metric fractions to four decimal places and does not support the additional precision in the separately supplied figures `97.905%`, `98.798%`, `96.990%`, `97.886%`, and `99.634%`; those additional digits are not independently verified here.

No held-out NLP, Vision, or fusion performance artifact was verified.

## Module status

The repository documents **25 modules** in the [project module matrix](./PROJECT_MODULE_MATRIX.md). Required highlights:

- **Extension:** IMPLEMENTED + RUNTIME VERIFIED IN EDGE; Chrome runtime blocked by managed developer-mode policy.
- **HITL:** IMPLEMENTED + PARTIALLY VERIFIED; MongoDB unavailable during runtime verification.
- **XAI:** IMPLEMENTED + VERIFIED; live URL ML score consistency verified.
- **Evidence Matrix:** IMPLEMENTED + VERIFIED.
- **Analytics:** IMPLEMENTED + PARTIALLY VERIFIED; session-only data.
- **Model Evaluation:** IMPLEMENTED + PARTIALLY VERIFIED; held-out evidence currently available for URL ML only.

## Remaining environment limitations

- MongoDB on localhost was unavailable; HITL database workflow and evidence persistence were not runtime-tested.
- Chrome unpacked-extension loading was prevented by managed policy; Microsoft Edge was used for extension runtime verification.
- Automatic screenshot acquisition produced no real screenshot in the tested environment, so Vision evidence was unavailable in the public scan.
- PhishTank returned HTTP 429 during TI status inspection; TI remained active with other feeds.
- The project remains a prototype and has no verified production deployment or overall ensemble accuracy claim.

## Submission caveats

Do not describe URL ML metrics as overall system or ensemble performance. Do not claim Chrome runtime, database-backed HITL runtime, or guaranteed screenshot acquisition.

Separate generated files at the repository root named `PHISHGUARD_PROJECT_REPORT.md`, `.docx`, and `.pdf` were not part of the verified consolidated documentation set. The Markdown report contains unsupported ensemble-accuracy, latency, and enterprise-readiness claims; review or replace those report artifacts before including them in a final submission. They were preserved during this documentation cleanup.

The extension source also initializes a missing stored token to the literal `demo-token`. This behavior was not changed during cleanup; do not treat that placeholder as a production credential or as evidence of a secure extension authentication setup.

No commit or push was performed.
