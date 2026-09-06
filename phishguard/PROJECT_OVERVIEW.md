# 🛡️ PhishGuard — Master Project Documentation & Team Onboarding Guide

> **Project Name:** PhishGuard  
> **Type:** Real-Time AI-Powered Phishing Detection System & Cyber Threat Intelligence Platform  
> **Target Audience:** Team Members, Developers, Security Analysts, and Stakeholders  
> **Document Purpose:** All-in-One Technical Overview, Architectural Breakdown, Setup Guide, and Developer Roadmap  

---

## 📋 Table of Contents
1. [Project Overview & Vision](#1-project-overview--vision)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Core System Components](#3-core-system-components)
4. [Multi-Engine AI Detection Architecture](#4-multi-engine-ai-detection-architecture)
5. [Data Flow & Interception Lifecycle](#5-data-flow--interception-lifecycle)
6. [Repository Folder Structure](#6-repository-folder-structure)
7. [Team Roles & Task Division](#7-team-roles--task-division)
8. [Step-by-Step Environment & Local Setup Guide](#8-step-by-step-environment--local-setup-guide)
9. [API Reference & Endpoint Contracts](#9-api-reference--endpoint-contracts)
10. [Explainable AI (XAI) & Human-in-the-Loop (HITL) Audit](#10-explainable-ai-xai--human-in-the-loop-hitl-audit)
11. [Current Capabilities & Future Roadmap](#11-current-capabilities--future-roadmap)
12. [How to Export This File to PDF](#12-how-to-export-this-file-to-pdf)

---

## 1. Project Overview & Vision

**PhishGuard** is an enterprise-ready, real-time phishing URL detection and cyber threat intelligence platform. It bridges browser-level zero-day threat prevention with a cloud-native backend powered by ensemble machine learning, natural language processing (NLP), domain intelligence, and Google Gemini AI LLM reasoning.

### The Problem
Traditional phishing defense relies heavily on static domain blocklists (e.g., Google Safe Browsing, PhishTank). Attackers bypass these lists easily by spinning up temporary subdomains, using URL shorteners, typosquatting brand names, or executing zero-day phishing campaigns that exist for only a few hours before blocklists update.

### The Solution
PhishGuard provides **instant, active protection** at the browser level before credentials can be submitted:
- **Zero-Day Detection:** Uses tabular ML, NLP semantics, structural domain analysis, and Gemini AI to detect deceptive URLs even if they have never been seen before.
- **Sub-Second Latency:** Tiered caching strategy (Session cache -> Local DB cache -> Fast ONNX ML model) ensures legitimate traffic is never slowed down.
- **Explainable Cyber Security (XAI):** Doesn't just say "malicious" — breaks down *why* (e.g., typosquatting score, brand impersonation, suspicious TLD, entropy level).
- **Proactive Browser Defense:** Chrome Extension automatically blocks navigation to malicious sites with a high-contrast protective overlay screen.
- **Interactive Security Ops Dashboard:** React-based management interface for security teams to monitor threats, audit edge cases (HITL), inspect telemetry, and tune model parameters.

---

## 2. High-Level Architecture

The PhishGuard ecosystem is built around three core subsystems communicating seamlessly:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             CHROME EXTENSION (MV3)                               │
│  - Service Worker (background.js): Intercepts web navigation in real-time       │
│  - Content Script (content.js): Injects full-page warning modal on malicious sites│
│  - Toolbar Popup (popup.html/js): Quick status summary & risk score bar           │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ HTTP REST API
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                BACKEND SERVICES                                  │
│  - Django / FastAPI REST Framework                                               │
│  - Whitelist Check (Instant pass for trusted platforms)                          │
│  - SHA-256 TTL Cache (DB / Redis 6h cache)                                       │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                    MULTI-ENGINE FUSION PIPELINE                            │  │
│  │                                                                            │  │
│  │  1. ML Engine        │ 2. NLP Engine      │ 3. Domain Intel  │ 4. Gemini LLM│  │
│  │  CatBoost / ONNX     │ DeBERTa / BERT     │ Redirect & WHOIS │ 1.5/2.0 Flash│  │
│  │  Structural features │ Semantic signals │ Threat Feeds     │ Deep Reasoning│  │
│  └──────────────────────┴──────────────────┴──────────────────┴──────────────┘  │
│                                         │                                        │
│                                         ▼                                        │
│                            ENSEMBLE META-LEARNER FUSION                          │
│                        Final Risk Score & XAI Breakdown                          │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ Real-Time Feeds / Audit
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            REACT WEB DASHBOARD (FE)                              │
│  - Real-Time URL Scanner & Interactive Threat Meter                              │
│  - Multi-Engine Decomposition Panel (ML vs NLP vs Domain vs LLM breakdown)       │
│  - Human-in-the-Loop (HITL) Analyst Labeling & Feedback Module                   │
│  - System Telemetry & Model Registry Dashboard                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core System Components

### 🟢 A. Chrome Browser Extension (Manifest V3)
- **Role:** Active real-time client scanner.
- **Key Files:**
  - `extension/manifest.json`: Configuration, permissions (`webNavigation`, `storage`, `tabs`, `<all_urls>`).
  - `extension/src/background.js`: Background service worker. Listens to `chrome.webNavigation.onCommitted`, maintains an in-memory session cache, queries the Backend API, and toggles extension badge states (🟢 Safe, 🟡 Suspicious, 🔴 Phishing).
  - `extension/src/content.js`: DOM content script injected at `document_start`. If a page is flagged as `phishing`, it intercepts rendering and injects a full-page modal warning.
  - `extension/src/popup.html` & `popup.js`: Extension popup UI showing details, confidence score, risk tags, and reason for the current active tab.

### 🔵 B. Backend API & Intelligence Pipeline
- **Role:** High-throughput URL inspection, risk assessment, caching, and model inference.
- **Key Files & Modules:**
  - `backend/main.py` / `backend/detector/views.py`: API entry points handling request validation, caching logic, and response formatting.
  - `backend/ml/`: Feature extraction (`feature_extractor.py`), CatBoost tabular classifier exportable to ONNX for fast feature scoring.
  - `backend/nlp/`: NLP semantic classifier (`nlp_service.py`) detecting deceptive language patterns and tokenized URL tricks.
  - `backend/domain_module/`: Domain intelligence service (`domain_service.py`), shortener expander, redirect chain analyzer, WHOIS/DNS check, Threat Intel (TI) integration.
  - `backend/ensemble_module/`: Fusion Engine (`fusion_engine.py`) and meta-learner (`meta_learner.pkl`) synthesizing predictions across all engines.
  - `backend/detector/hitl_service.py`: Human-in-the-loop feedback persistence and audit logging.

### 🟣 C. React Web Dashboard (Frontend)
- **Role:** Web UI for security operations, interactive manual scanning, model telemetry, and analyst labeling.
- **Tech Stack:** React 18, TypeScript, Vite, CSS Modules / Tailwind styling.
- **Key Features:**
  - **Live Scanner:** Input any URL to get an instant multi-engine report.
  - **XAI Breakdown:** Visual graphs detailing top suspicious signals (e.g., domain entropy, typosquatting distance).
  - **Engine Panel:** Compare individual engine confidence scores side-by-side.
  - **HITL Auditor:** Allows security team members to re-label misclassified URLs and trigger model retrains.

---

## 4. Multi-Engine AI Detection Architecture

PhishGuard avoids single points of failure by combining 4 complementary detection engines:

| Engine | Technology | Responsibilities | Latency Target |
|---|---|---|---|
| **1. ML Engine** | CatBoost Classifier exported to ONNX | Extracts 25+ structural & statistical URL features (length, digit count, entropy, path depth, query param count, special symbols). | `< 15ms` |
| **2. NLP Engine** | Transformer / DeBERTa NLP Pipeline | Analyzes semantic sequences, brand keywords inside path/subdomain, and tokenized character anomalies. | `< 50ms` |
| **3. Domain Intel** | Python Async HTTP + WHOIS / DNS | Unrolls shortened URLs (bit.ly, t.co), inspects multi-hop HTTP redirect chains, domain age, and IP reputation blocklists. | `< 150ms` |
| **4. Gemini LLM Engine** | Google Gemini 1.5/2.0 Flash API | Performs deep contextual reasoning on zero-day attacks, evaluates brand impersonation intent, and produces structured XAI reasons. | `~400-800ms` |
| **5. Fusion Meta-Learner** | Logistic Regression / Random Forest Ensemble | Aggregates individual engine probabilities into a single normalized confidence score and risk classification. | `< 5ms` |

---

## 5. Data Flow & Interception Lifecycle

```
[User clicks link / navigates to URL]
                 │
                 ▼
     [Extension: background.js]
                 │
                 ├─ Check URL scheme (Ignore chrome://, file://)
                 ├─ Check Extension In-Memory Cache ──(Hit)──► Apply cached icon & stop
                 │
                 ▼ (Miss)
        [POST request to API /api/scan/]
                 │
                 ├─ Check Backend Whitelist (Google, GitHub, etc.) ──(Hit)──► Return SAFE (0.99)
                 ├─ Check Backend DB TTL Cache (6 hours TTL) ───────(Hit)──► Return Cached Result
                 │
                 ▼ (Miss)
     ┌───────────────────────────────────────────────────────────┐
     │              PARALLEL MULTI-ENGINE EXECUTION              │
     │  - ML Engine (Feature Extractor + CatBoost/ONNX)         │
     │  - NLP Engine (Semantic Transformer model)               │
     │  - Domain Intel (Redirect unspooling, WHOIS, TI lookup)  │
     │  - Gemini LLM Service (Deep Reasoning & XAI Generation)  │
     └─────────────────────────────┬─────────────────────────────┘
                                   │
                                   ▼
                   [Ensemble Fusion Meta-Learner]
                                   │
              Computes: Risk Level + Confidence + Signals
                                   │
                                   ├─ Store result in DB Cache
                                   ▼
                   [HTTP Response to Chrome Extension]
                                   │
       ┌───────────────────────────┴───────────────────────────┐
       │                                                       │
  🟢 SAFE                                                🔴 PHISHING
  - Green Extension Icon                                 - Red Badge Icon
  - Allow Normal Navigation                              - Send PHISHING_ALERT to content.js
                                                         - Inject Full-Page Blocking Overlay
```

---

## 6. Repository Folder Structure

```
phishguard/
├── backend/                            # Python Backend Server & AI Modules
│   ├── detector/                       # Core API app & HITL logic
│   │   ├── hitl_audit.json             # Audit trail log for human overrides
│   │   ├── hitl_labels.json            # Security analyst label storage
│   │   ├── hitl_service.py             # Analyst feedback handler
│   │   └── views.py                    # API endpoints
│   ├── domain_module/                  # Domain Intelligence & Reputation
│   │   ├── domain_intelligence.py      # Master domain inspection wrapper
│   │   ├── redirect_unwrapper.py       # Multi-hop HTTP redirect tracer
│   │   ├── shortener_expander.py       # Expands bit.ly, tinyurl, etc.
│   │   └── ti_integration.py           # Threat Intelligence feed connector
│   ├── ensemble_module/                # Multi-Engine Fusion Layer
│   │   ├── fusion_engine.py            # Meta-learner prediction aggregator
│   │   └── models/meta_learner.pkl     # Trained meta-learner weights
│   ├── ml/                             # Machine Learning Pipeline
│   │   ├── feature_extractor.py        # 25+ statistical URL feature extractor
│   │   ├── ml_service.py               # ONNX / CatBoost inference runner
│   │   ├── train_model.py              # ML model training pipeline
│   │   └── models/catboost_model.cbm   # Trained tabular ML model
│   ├── nlp/                            # Natural Language Processing Engine
│   │   ├── nlp_service.py              # Transformer URL sequence scorer
│   │   └── models/                     # Tokenizer and weights configuration
│   ├── main.py                         # FastAPI / Django entry point
│   ├── db.py                           # SQLite / PostgreSQL connection layer
│   └── requirements.txt                # Backend dependencies
│
├── extension/                          # Chrome Extension (Manifest V3)
│   ├── manifest.json                   # MV3 permissions & content script rules
│   ├── icons/                          # Extension icons (16px, 48px, 128px)
│   └── src/
│       ├── background.js               # Service Worker (interceptor & cache)
│       ├── content.js                  # Injection script for blocking overlay
│       ├── popup.html                  # Extension popup markup
│       └── popup.js                    # Extension popup controller
│
├── frontend/                           # React Security Operations Dashboard
│   ├── public/                         # Static assets & icons
│   ├── src/
│   │   ├── components/                 # UI Components
│   │   │   ├── ScannerPanel.tsx        # Manual URL input & scanner
│   │   │   ├── ThreatMeter.tsx         # Radial risk score meter
│   │   │   ├── XAIPanel.tsx            # Explainable AI feature breakdown
│   │   │   ├── EnginePanel.tsx         # Multi-engine score decomposition
│   │   │   ├── HITLLabelingPanel.tsx   # Analyst feedback interface
│   │   │   ├── ModelRegistryPanel.tsx  # Model weights & system telemetry
│   │   │   └── HeroDashboard.tsx       # Main analytics view
│   │   ├── hooks/                      # Custom React Hooks (`useAnalysis.ts`)
│   │   ├── App.tsx                     # Main dashboard container
│   │   └── index.tsx                   # React root entry point
│   ├── package.json                    # Node dependencies
│   └── vite.config.ts                  # Vite bundle configuration
│
├── reports/                            # Performance, ML, & Security Reports
│   ├── security-audit-2026-08-17.md    # Security evaluation report
│   ├── ml-model-review-2026-08-17.md   # Model benchmark report
│   └── llm-ensemble-smoke-tests.md     # Smoke test results
│
├── generate_icons.py                   # Script to generate browser extension icons
├── README.md                           # Quickstart guide
└── PROJECT_OVERVIEW.md                 # ← THIS ALL-IN-ONE DOCUMENTATION FILE
```

---

## 7. Team Roles & Task Division

To collaborate effectively, here is a suggested division of responsibilities across team members:

```
                              ┌──────────────────────────┐
                              │  TEAM LEAD / ARCHITECT   │
                              │ Core integration, reviews│
                              └────────────┬─────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│ BACKEND & AI TEAM│             │  FRONTEND TEAM   │             │ EXTENSION TEAM   │
│ - ML / ONNX models│             │ - React Dashboard│             │ - MV3 background │
│ - Gemini Prompt  │             │ - XAI Analytics  │             │ - Content Scripts│
│ - Domain Intel   │             │ - HITL UI Panel  │             │ - DOM Blocking UI│
│ - FastAPI/Django │             │ - User Experience│             │ - State Storage  │
└──────────────────┘             └──────────────────┘             └──────────────────┘
```

### 🔹 1. Backend & AI Engineers
- **Focus Areas:** `backend/ml/`, `backend/nlp/`, `backend/domain_module/`, `backend/ensemble_module/`, `backend/detector/`
- **Tasks:**
  - Retrain and optimize CatBoost/ONNX tabular model with fresh datasets.
  - Tune Google Gemini system prompt (`backend/detector/views.py` / `gemini_service.py`) for accurate zero-day classification.
  - Enhance Domain Intelligence (add WHOIS lookup caching, integrate live threat feeds like OpenPhish or URLhaus).
  - Fine-tune ensemble fusion weights in `fusion_engine.py`.

### 🔹 2. Frontend Engineers
- **Focus Areas:** `frontend/src/components/`, `frontend/src/hooks/`
- **Tasks:**
  - Refine React + TypeScript dashboard UI/UX.
  - Improve XAI visual charts (e.g., render feature contribution metrics clearly).
  - Build real-time telemetry streaming and history log filtering in the dashboard.
  - Ensure responsive design across mobile and desktop browser views.

### 🔹 3. Browser Extension Engineers
- **Focus Areas:** `extension/src/`
- **Tasks:**
  - Maintain Chrome Manifest V3 compliance in `background.js`.
  - Optimize tab switching and extension icon updating logic.
  - Improve the blocking modal UI injected by `content.js` (add override options, user reporting button).
  - Add sync storage settings allowing users/analysts to change the Backend API server URL dynamically.

---

## 8. Step-by-Step Environment & Local Setup Guide

Follow these instructions to run the entire PhishGuard platform locally on your machine.

### Prerequisites
- **Python:** Version 3.10 or higher
- **Node.js:** Version 18.x or higher + `npm`
- **Google Gemini API Key:** Free key available at [Google AI Studio](https://aistudio.google.com)
- **Browser:** Google Chrome or Brave

---

### Step 1: Clone Repository & Set Up Backend

1. Open your terminal and navigate to the project directory:
   ```bash
   cd phishguard/backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # On Windows:
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux:
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create environment file `.env`:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` and insert your Gemini API Key:
   ```env
   DJANGO_SECRET_KEY=your-custom-secret-key-here
   GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
   DEBUG=True
   ```

6. Run database setup and start backend server:
   ```bash
   # If using Django:
   python manage.py migrate
   python manage.py runserver

   # If running via main.py / FastAPI:
   python main.py
   ```
   *The backend API will run at:* `http://127.0.0.1:8000`

---

### Step 2: Set Up & Run React Dashboard (Frontend)

1. Open a new terminal tab and navigate to `frontend`:
   ```bash
   cd phishguard/frontend
   ```

2. Install Node modules:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The Dashboard will be accessible at:* `http://localhost:5173`

---

### Step 3: Load Chrome Browser Extension

1. Build icons if needed:
   ```bash
   cd phishguard
   python generate_icons.py
   ```

2. Open Google Chrome and navigate to `chrome://extensions`.
3. Enable **Developer mode** using the toggle in the top-right corner.
4. Click **Load unpacked** (top-left).
5. Select the `phishguard/extension` directory.
6. The 🛡️ **PhishGuard** icon will now appear in your browser toolbar!

---

## 9. API Reference & Endpoint Contracts

### 1. `POST /api/scan/` — Main URL Analysis Endpoint
Scans a target URL through the multi-engine fusion pipeline.

- **Request Body:**
  ```json
  {
    "url": "https://paypa1-security-update.account-verify.com/login"
  }
  ```

- **Response Body:**
  ```json
  {
    "url": "https://paypa1-security-update.account-verify.com/login",
    "risk_level": "phishing",
    "confidence": 0.96,
    "reason": "Deceptive typosquatting domain impersonating PayPal combined with excessive subdomain depth and high entropy.",
    "signals": [
      "typosquatting_brand",
      "excessive_subdomains",
      "high_entropy_path",
      "suspicious_tld"
    ],
    "engine_scores": {
      "ml_onnx": 0.94,
      "nlp_transformer": 0.91,
      "domain_intel": 0.88,
      "gemini_llm": 0.98
    },
    "cached": false,
    "scan_timestamp": "2026-08-19T22:30:00Z"
  }
  ```

---

### 2. `GET /api/health/` — System Health & Uptime Probe
Returns status of backend, database connection, and AI models.

- **Response Body:**
  ```json
  {
    "status": "healthy",
    "services": {
      "database": "connected",
      "ml_engine": "loaded (onnx)",
      "gemini_api": "active"
    }
  }
  ```

---

### 3. `POST /api/hitl/label/` — Security Analyst Override
Submits analyst feedback for a misclassified URL to update the HITL audit ledger.

- **Request Body:**
  ```json
  {
    "url": "https://example-internal-login.company.com",
    "corrected_label": "safe",
    "analyst_notes": "Internal corporate staging portal, verified legitimate."
  }
  ```

---

## 10. Explainable AI (XAI) & Human-in-the-Loop (HITL) Audit

### Explainable AI (XAI)
Modern cybersecurity tools must be transparent. PhishGuard's XAI panel isolates the exact factors driving a risk score:
- **Lexical Signals:** URL length > 75 chars, `@` symbol count, ip address in hostname.
- **Entropy Analysis:** Randomness score of domain/path strings (detects randomly generated malicious URLs).
- **Brand Distance:** Levenshtein edit-distance calculation against top 100 global brands (PayPal, Microsoft, Google, Bank of America).
- **LLM Reasoning:** Gemini provides a human-readable explanation of attacker intent.

### Human-in-the-Loop (HITL)
No AI is 100% infallible. PhishGuard includes a built-in HITL feedback ledger:
1. When an analyst identifies a false positive or false negative, they flag it via the React Dashboard or API.
2. The override is written to `backend/detector/hitl_labels.json` and `hitl_audit.json`.
3. The fusion engine dynamically adjusts feature weights for flagged domain patterns.
4. Flagged samples are added to the retraining queue for subsequent ML & NLP batch runs.

---

## 11. Current Capabilities & Future Roadmap

### ✅ What Works Today (Current Capabilities)
- [x] Full MV3 Chrome Extension with active URL interception & tab status updates.
- [x] Full-page dark mode blocking modal for phishing URLs with bypass option.
- [x] Multi-engine backend incorporating CatBoost/ONNX tabular ML, NLP, Domain Intel, and Gemini 1.5/2.0 LLM.
- [x] 3-tier caching system (Session cache -> Local SQLite DB -> Multi-engine calculation).
- [x] React Operations Dashboard with interactive scanner, XAI breakdown, and HITL labeling panel.
- [x] Domain whitelist bypass for top trusted platforms.

### 🚀 Upcoming Roadmap (Planned Enhancements)
- [ ] **Google Safe Browsing & OpenPhish Live Feeds:** Direct integration with public threat feeds for instant blocklist sync.
- [ ] **Visual Screenshot Phishing Detection (Gemini Vision):** Capture rendering of questionable pages to detect visual brand logo cloning.
- [ ] **PostgreSQL & Redis Scaling:** Migrate SQLite cache to Redis for microsecond response times under high concurrency.
- [ ] **Firefox & Edge Extension Port:** Extend Manifest V3 extension compatibility to Firefox WebExtensions.
- [ ] **Automated Retraining Pipeline:** Scheduled Github Action / Cron job to automatically retrain the ONNX model using fresh HITL labels.

---

## 12. How to Export This File to PDF

If you want to share this document as a formatted **PDF file** with your team:

### Method 1: VS Code (Recommended)
1. Install the extension **Markdown PDF** or **Markdown Preview Enhanced** in VS Code.
2. Open `PROJECT_OVERVIEW.md`.
3. Right-click anywhere in the file editor.
4. Select **Markdown PDF: Export (pdf)**.

### Method 2: Browser Print
1. Open `PROJECT_OVERVIEW.md` in GitHub or any Markdown viewer in your browser.
2. Press `Ctrl + P` (or `Cmd + P` on Mac).
3. Select **"Save as PDF"** as the printer destination and click **Save**.

---

*Documentation compiled for the PhishGuard Project Team.*  
*Keep building, stay secure! 🛡️*
