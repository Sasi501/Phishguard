# Architecture

The backend is FastAPI under `phishguard/backend`. The React/TypeScript dashboard is under `phishguard/frontend`. The Chrome Manifest V3 extension is under `phishguard/extension`.

## Analysis flow

Submitted URL → URL ML → optional submitted text/NLP → optional submitted image or screenshot/Vision → redirect resolution → Domain Intelligence and Threat Intelligence on the resolved URL → fusion → final ensemble result → XAI evidence → dashboard/HITL.

The backend can return partial analysis when network-dependent evidence is restricted or unavailable. URL ML, NLP, Vision, Domain/TI, redirect evidence, and the final ensemble are represented separately.

## Provenance

The response uses `source`, `score_type`, and `url_scope` where available. URL ML is scoped to the original URL, NLP to submitted text, Vision to submitted image, Domain/TI to the final URL, and redirects to the full chain.

The URL ML inference probability, URL ML engine signal passed into fusion, and final ensemble result are distinct values. In the existing fallback path, domain-age moderation can adjust the URL score before fusion. XAI reports raw probability and engine signal separately when available; neither is a feature-attribution contribution.
