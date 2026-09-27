# PhishGuard

Multi-Modal Intelligence Techniques for Phishing Detection.

## Components

- FastAPI backend: `phishguard/backend`
- React dashboard: `phishguard/frontend`
- Chrome Manifest V3 extension: `phishguard/extension`
- Repository-backed URL ML evaluation and model registry
- XAI Investigation Center, Evidence Matrix, Scan Analytics, and HITL surfaces

## Local development

Start the backend from `phishguard/backend` and the frontend from `phishguard/frontend`. Load `phishguard/extension` as an unpacked extension when testing extension behavior. MongoDB and optional Redis are environment-dependent.

## Testing

Backend: `pytest -q`

Frontend: `npm run build` and `npm run lint`

Extension: `node --check` on the extension scripts.

## Evidence and limitations

The current verified project evidence is consolidated under [`docs/`](./docs/). The backend suite passes with 76 tests, the frontend build and lint pass, and the Manifest V3 extension was runtime verified in isolated Microsoft Edge. Chrome unpacked-extension runtime was blocked by managed policy; MongoDB was unavailable for HITL runtime verification.

The verified `https://example.com` scan showed a raw CatBoost probability of 98.59%, URL ML engine signal of 4.93% after existing domain-age moderation, and final ensemble risk of 1.73% / Safe. These are different quantities. Held-out evaluation figures apply to the URL ML model only; no overall ensemble, NLP, Vision, or extension accuracy claim is made. Scan Analytics is session-only. See [`docs/FINAL_PROJECT_STATUS.md`](./docs/FINAL_PROJECT_STATUS.md) for the full status and limitations.
