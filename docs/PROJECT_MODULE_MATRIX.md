# Project module matrix

The matrix summarizes implementation and the runtime evidence available for this repository as of 2026-09-26. “Partially verified” means some behavior was exercised but environment or feature coverage was incomplete; it does not mean the feature was bypassed.

| # | Module | Implementation | Integration / evidence | Runtime status | Status | Limitation |
|---:|---|---|---|---|---|---|
| 1 | Browser extension | Manifest V3 extension with tab detection, backend scan, status, and retry | JavaScript syntax checks; real `https://example.com` result in isolated Microsoft Edge | Runtime verified in Edge | IMPLEMENTED + RUNTIME VERIFIED IN EDGE | Chrome unpacked loading blocked by managed developer-mode policy |
| 2 | URL ML / CatBoost | URL feature extraction and CatBoost inference | Backend tests, saved metrics artifact, public live scan | Live signal and raw probability observed | IMPLEMENTED + VERIFIED | Evaluation metrics apply to URL ML only |
| 3 | NLP / DistilBERT | Optional submitted-text analysis | NLP tests; frontend correctly reported unavailable when no text was submitted | No NLP result in the final public scan | IMPLEMENTED + PARTIALLY VERIFIED | No held-out evaluation artifact |
| 4 | Vision / EfficientNet-B3 | Optional image/screenshot analysis | Vision tests; frontend explicitly reported screenshot unavailable | No Vision result in the final public scan | IMPLEMENTED + PARTIALLY VERIFIED | Screenshot capture is environment/configuration dependent; no held-out metrics |
| 5 | Domain Intelligence | Domain signals and final-URL metadata | Backend tests; observed available result on public scan and restricted result on loopback | Runtime verified for available/restricted paths | IMPLEMENTED + VERIFIED | Network/private-address restrictions limit evidence |
| 6 | Threat Intelligence | Threat feed status and match evidence | TI tests and `/api/ti/status/`; public scan returned no match | Runtime status observed; a feed returned HTTP 429 | IMPLEMENTED + PARTIALLY VERIFIED | Feed availability varies |
| 7 | Redirect Resolver | Bounded redirect traversal with loop and limit states | Backend redirect tests; live 2-hop and redirect-limit checks | Runtime verified | IMPLEMENTED + VERIFIED | External network availability is environment dependent |
| 8 | Multi-modal Fusion | Meta-learner and weighted partial-fusion paths | Fusion tests; live complete and partial scans | Runtime verified | IMPLEMENTED + VERIFIED | No held-out ensemble evaluation/calibration artifact |
| 9 | XAI Investigation Center | User/analyst views, factors, provenance, limitations | Fusion tests and live scan; URL ML signal now reconciles across result surfaces | Live score consistency verified | IMPLEMENTED + VERIFIED | Explanations remain evidence summaries, not causal proof |
| 10 | URL Anatomy | URL component analysis in dashboard | Frontend build and live scan | Runtime UI verified | IMPLEMENTED + VERIFIED | Existing Fast Refresh lint warning |
| 11 | Threat Intelligence dashboard | Displays match, scope, and feed evidence | Frontend build and live public scan | Runtime UI verified | IMPLEMENTED + PARTIALLY VERIFIED | Feed-specific availability varies |
| 12 | Redirect forensics | Redirect chain, state, and evidence display | Backend tests and live controlled redirect | Runtime verified | IMPLEMENTED + VERIFIED | Browser/meta-refresh behavior is environment dependent |
| 13 | HITL workflow | Submission and analyst review API/UI | Backend HITL tests; no database-backed case submitted | Partially verified | IMPLEMENTED + PARTIALLY VERIFIED | MongoDB was unavailable during runtime verification |
| 14 | HITL evidence snapshot | Captures scan/XAI evidence for review | Snapshot/API tests | Tests passed; database workflow not runtime verified | IMPLEMENTED + PARTIALLY VERIFIED | MongoDB unavailable |
| 15 | Evidence provenance | `source`, `score_type`, and `url_scope` fields | Fusion tests and populated live Evidence Matrix | Runtime verified | IMPLEMENTED + VERIFIED | Restricted analysis can yield partial evidence |
| 16 | Model registry | Registry API and dashboard surface | Registry tests and UI build | Implementation/test evidence available | IMPLEMENTED + PARTIALLY VERIFIED | Filesystem-backed prototype; production lifecycle not verified |
| 17 | Engine/system health | Health and TI status visibility | `/api/health/` and `/api/ti/status/` responses checked | Runtime verified | IMPLEMENTED + VERIFIED | Database, HITL, XAI, and ONNX have no reliable status field |
| 18 | Scan history and analytics | Recent scans and analytics from React session state | Live three-scan timeline and session-only notice | Analytics runtime verified; not persistent | IMPLEMENTED + PARTIALLY VERIFIED | History is lost with session state |
| 19 | Main risk dashboard | Risk result and linked analysis panels | Public, loopback, and controlled-redirect frontend scans | Runtime verified | IMPLEMENTED + VERIFIED | Output depends on available engine evidence |
| 20 | SSRF protections | Blocks private/loopback destinations during network-dependent operations | Tests and live loopback scan; Domain/Redirect marked restricted/blocked | Runtime verified for tested cases | IMPLEMENTED + VERIFIED | Not a claim of complete security or a substitute for production threat modeling |
| 21 | Authentication | Login/register/token helpers and protected routes | Code/tests present; database-backed runtime not exercised | Partially verified | IMPLEMENTED + PARTIALLY VERIFIED | MongoDB unavailable; no production deployment claim |
| 22 | Extension online/offline/retry | Health checks, backend result, offline state, retry | Live Edge public and loopback scans; backend stop/offline/restart/retry sequence | Runtime verified in Edge | IMPLEMENTED + RUNTIME VERIFIED IN EDGE | Chrome environment blocked by managed policy |
| 23 | Model Evaluation | Evaluation UI backed by URL CatBoost artifact | Live UI; `metrics.json` has 0.979, 0.988, 0.9699, 0.9789, 0.9963 | URL ML only; partial product coverage | IMPLEMENTED + PARTIALLY VERIFIED | No held-out NLP, Vision, or ensemble metrics; artifact cannot substantiate extra requested precision digits |
| 24 | Analyst investigation mode | XAI analyst evidence and feature view | Live XAI evidence and frontend/backend tests | Runtime UI verified | IMPLEMENTED + PARTIALLY VERIFIED | HITL review lifecycle requires unavailable MongoDB |
| 25 | Documentation | Architecture, API, model, XAI, security, testing, deployment, and status docs | Updated from latest test and runtime evidence | Documentation reviewed | IMPLEMENTED + VERIFIED | Generated project-report artifacts outside `docs/` need separate review before submission |

## Cross-module runtime evidence

- Local health endpoint returned HTTP 200 with `status: ok` and readiness fields for ML, NLP, Vision, Domain, and Ensemble.
- Frontend production build passed; lint passed with the existing `URLAnatomy.tsx` Fast Refresh warning.
- Full backend suite: 76 passed; focused fusion/XAI suite: 15 passed.
- The `https://example.com` frontend scan showed URL ML engine signal **4.93%**, raw CatBoost probability **98.59%**, and final ensemble risk **1.73% / Safe**. These are distinct quantities; see [XAI](./XAI.md).
- MongoDB was unavailable. Chrome unpacked extension loading was blocked by managed policy; Edge was used for extension runtime verification.
