# API

Important routes include:

- `GET /api/health/` — backend and engine readiness fields.
- `POST /api/analyze-ensemble/` — multipart URL analysis with optional text/image.
- `GET /api/scan/` and `POST /api/scan/` — compatibility scan surface.
- `POST /api/analyze-domain/` — domain analysis.
- `GET/POST /api/unwrap-redirect/` — redirect resolution.
- `GET /api/ti/status/` — threat-intelligence status.
- Registry routes under `/api/registry/`.
- HITL routes under `/api/hitl/`.
- Authentication routes include `/api/login/` and `/api/register/`.

The ensemble response includes `ensemble_score_percent`, `ensemble_risk_level`, `analysis_status`, `engine_status`, `individual_scores_percent`, `redirect_analysis`, and structured `xai` evidence. Missing or restricted evidence is represented explicitly.

Structured XAI additively includes optional `url_ml_evidence` metadata when raw URL inference is available: `raw_model_probability_percent`, `engine_signal_percent`, and `engine_signal_adjustment`. Older stored scans and HITL snapshots may omit this field; consumers should continue to use the existing `engine_signals` and tolerate missing optional metadata. `ensemble_score_percent` remains a separate final result.
