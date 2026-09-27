# PhishGuard Documentation

PhishGuard is a multi-modal phishing-analysis prototype with URL, text, vision, domain, threat-intelligence, redirect, fusion, XAI, HITL, browser-extension, and React dashboard surfaces.

## Evidence policy

Only repository-backed implementation and executed verification are described here. Runtime claims are qualified when MongoDB, browser automation, screenshot capture, or a live endpoint was unavailable.

Latest verification: backend 76 tests passed (15 focused fusion/XAI tests); frontend build and lint passed (one existing URLAnatomy Fast Refresh warning); extension syntax and Manifest V3 passed; runtime was verified in isolated Microsoft Edge. Chrome extension loading was blocked by managed policy, and MongoDB was unavailable for HITL runtime verification. See [final project status](./FINAL_PROJECT_STATUS.md).

The public `https://example.com` scan produced a raw CatBoost probability of 98.59%, URL ML engine signal of 4.93% after existing domain-age moderation, and final ensemble risk of 1.73% / Safe. These are distinct values. Held-out evaluation evidence is URL ML-only; the saved artifact supports rounded values only.

- [Architecture](./ARCHITECTURE.md)
- [Models and evaluation](./MODELS.md)
- [API](./API.md)
- [Security](./SECURITY.md)
- [XAI](./XAI.md)
- [Testing](./TESTING.md)
- [Deployment](./DEPLOYMENT.md)
- [Project module matrix](./PROJECT_MODULE_MATRIX.md)
- [Final project status](./FINAL_PROJECT_STATUS.md)
