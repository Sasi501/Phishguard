# Testing

Latest verified state:

- Backend: `pytest -q` — 76 passed, 7 deprecation/pending-deprecation warnings.
- Focused fusion/XAI tests: 15 passed.
- Frontend: `npm run build` — passed.
- Frontend: `npm run lint` — passed with the existing `URLAnatomy.tsx` Fast Refresh warning.
- Extension JavaScript: `node --check` passed for `src/background.js`, `src/content.js`, and `src/popup.js`.
- Extension manifest: Manifest V3 validated.
- `git diff --check` — passed.

Runtime verification included HTTP 200 from local `/api/health/` and Vite, public and loopback scans, a controlled redirect, live Edge extension scans, and Edge offline/retry behavior. The final public scan showed URL ML engine signal 4.93%, raw CatBoost probability 98.59%, and ensemble score 1.73% / Safe. The three values are explicitly distinguished in XAI and are not interchangeable.

Chrome unpacked-extension runtime was blocked by managed developer-mode policy. MongoDB was unavailable, so HITL persistence and review lifecycle were not runtime verified. PhishTank returned HTTP 429 during TI status inspection. Automatic screenshot acquisition did not produce a real screenshot in the public scan.
