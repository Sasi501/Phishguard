# PhishGuard AI Handoff Brief

## 1) Project name
PhishGuard

## 2) What this project is
A browser-level phishing detection system that checks URLs in real time and blocks phishing pages before users interact with them.

Core flow:
- Chrome extension watches tab/navigation
- Sends URL to backend API
- Backend runs multiple checks (ML, NLP, domain intelligence, LLM)
- Fusion engine decides risk
- Extension shows safe / suspicious / phishing state
- Optional dashboard shows details and analyst feedback

## 3) Main architecture

### A. Browser extension
Location: `phishguard/extension/`

Main files:
- `extension/manifest.json` — Chrome extension config and permissions
- `extension/src/background.js` — service worker; intercepts URL checks, caches result, updates icon
- `extension/src/content.js` — injects phishing overlay warning page
- `extension/src/popup.html` / `popup.js` — popup UI

Purpose:
- Detect URL while user browses
- Show warning/blocked page
- Query backend for classification

### B. Backend API + detection engine
Location: `phishguard/backend/`

Main files/folders:
- `backend/main.py` — backend entry
- `backend/db.py` — DB config
- `backend/detector/` — detection service and HITL audit
- `backend/ml/` — ML feature extraction and model inference
- `backend/nlp/` — NLP scoring and model assets
- `backend/domain_module/` — redirect, shortener, WHOIS/domain checks, TI integration
- `backend/ensemble_module/` — fusion engine and meta-learner

Purpose:
- Receive URL scans from extension
- Run background checks
- Combine model outputs
- Return risk score + explanation

### C. Frontend dashboard
Location: `phishguard/frontend/`

Main files:
- `frontend/src/App.tsx` — main dashboard
- `frontend/src/components/` — scanner, XAI, model registry, HITL UI

Purpose:
- Manual URL scan UI
- Explainability panel
- Analyst review and model registry controls

### D. Reports / docs
Location: `phishguard/reports/`

Purpose:
- Security review and dependency audits
- ML review and smoke tests
- Operational notes

## 4) What each module does

### `backend/ml/`
- Extracts URL features such as length, entropy, special characters, digits, query structure
- Runs ML classifier
- Model artifacts are under `backend/ml/models/`

### `backend/nlp/`
- Checks deceptive language and suspicious token patterns in URLs
- Tries to detect impersonation and brand-like text in path/subdomain

### `backend/domain_module/`
- Expands short links
- Traces redirects
- Checks domain intelligence / reputation indicators
- Detects suspicious domain patterns

### `backend/ensemble_module/`
- Fusion engine combines ML + NLP + domain + LLM outputs
- Produces final risk score, confidence, and signals

### `backend/detector/`
- HITL audit file and labels
- Human review / analyst feedback handling

### `extension/src/background.js`
- Main real-time gate
- Fetches API result
- Updates badge color and behavior

### `frontend/src/components/`
- UI for model registry, explanation panel, manual scanner, analyst labeling

## 5) Current project status
From the repo notes and plan:

Completed:
- Redirect unwrapper
- Shortener expansion
- URL feature engine
- Threat intel integration
- Screenshot pipeline placeholder
- NLP pipeline
- Local model registry + promotion flow
- Ensemble fusion engine + meta-learner
- Registry UI + artifact download support
- Security and dependency audit tracking
- Smoke tests for LLM + ensemble pipeline

Known issues / risks:
- Gemini rate limits may trigger fallback behavior
- Dependency conflicts may exist between some Google packages
- Need more hardening around production deployment and secret cleanup
- Need more verification before promoting models publicly

## 6) Project file map

### Root
- `phishguard/README.md` — quickstart
- `phishguard/PROJECT_OVERVIEW.md` — full architecture overview
- `phishguard/plan.md` — roadmap and current priorities
- `phishguard/AI_PROJECT_BRIEF.md` — this file

### Backend
- `phishguard/backend/main.py`
- `phishguard/backend/db.py`
- `phishguard/backend/requirements.txt`
- `phishguard/backend/detector/`
- `phishguard/backend/ml/`
- `phishguard/backend/nlp/`
- `phishguard/backend/domain_module/`
- `phishguard/backend/ensemble_module/`

### Extension
- `phishguard/extension/manifest.json`
- `phishguard/extension/src/background.js`
- `phishguard/extension/src/content.js`
- `phishguard/extension/src/popup.js`

### Frontend
- `phishguard/frontend/package.json`
- `phishguard/frontend/src/`

## 7) What to do next

### Priority 1 — security and dependency cleanup
Do first before exposing more functionality:
- Audit Python dependencies in `backend/requirements.txt`
- Check for secret leaks in repo and env files
- Review backend API endpoints for validation and rate limiting
- Confirm LLM API handling is safe and failure-tolerant

### Priority 2 — production hardening
- Move from local/dev DB setup to Postgres
- Add Redis cache for production
- Separate model artifact storage from repo
- Harden API and deployment environment

### Priority 3 — UX and analyst workflow
- Finish HITL labeling flow in frontend
- Add more explainable output for risk features
- Improve audit log visibility

### Priority 4 — model quality
- Add adversarial URL test cases
- Add drift detection and retraining triggers
- Expand multilingual NLP support

## 8) Short AI handoff prompt
Use this to paste into another AI:

"This is a phishing URL detection project called PhishGuard. It has a Chrome extension frontend, a Python backend, and a React dashboard. The extension calls the backend API with a URL. The backend runs ML, NLP, domain intelligence, and Gemini-based reasoning, then fuses the outputs into a final phishing risk score. Key folders: phishguard/backend, phishguard/extension, phishguard/frontend, phishguard/reports. Current plan priority: security + dependency audit, secret scan, API hardening, production deployment, HITL UI, explainability, and model quality improvements. Please review the repo, identify the most critical next tasks, and propose a minimal execution plan with file-by-file actions and validation steps."

## 9) Best immediate action
Start with:
1. dependency audit
2. secret scan
3. security review of API and model exposure
4. then finish the minor UI + HITL tasks

This is the safest path before broader deployment or public release.

## 10) What the AI should focus on first
- Find unsafe or inconsistent requirements/dependencies
- Check for committed secrets or env leakage
- Inspect API validation and caching logic
- Confirm the ensemble/fusion pipeline is stable
- Identify missing production protections
- Recommend a direct next-step sprint plan
