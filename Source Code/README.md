# PhishGuard — Multi-Modal Intelligence Platform for Phishing Detection

PhishGuard is an advanced, multi-modal cybersecurity intelligence platform engineered to detect sophisticated, zero-day, and multi-stage phishing attacks across URL structures, domain infrastructure, real-time threat intelligence feeds, page textual content, visual rendering, and redirect topologies.

---

## 📁 Source Code Directory Structure

```
Source Code/
├── Backend/                 # FastAPI REST API, orchestration, and intelligence services
│   ├── main.py              # Application entrypoint and endpoint definitions
│   ├── db.py                # MongoDB persistence & scan telemetry
│   ├── requirements.txt     # Python dependency specifications
│   ├── detector/            # Human-In-The-Loop (HITL) audit and review service
│   ├── domain_module/       # Domain intelligence, WHOIS/DNS heuristics, redirect unwrapper, TI feeds
│   ├── ensemble_module/     # Dynamic multi-modal fusion engine and stacking meta-learner
│   ├── ml/                  # URL feature extraction (30+ features) and CatBoost inference
│   ├── nlp/                 # Multilingual DistilBERT keyword & urgency inference
│   ├── vision_module/       # EfficientNet-B3 visual classification and screenshot pipeline
│   └── registry/            # Model registry, versioning, rollback, and storage providers
├── Frontend/                # React 19 + TypeScript + Vite modern web application
│   ├── src/                 # Application source code
│   │   ├── components/      # UI components (Basic View summary, XAI panel, Evidence matrix, etc.)
│   │   ├── hooks/           # Custom React hooks (useAnalysis, useCountUp, etc.)
│   │   ├── types/           # Strict TypeScript interface definitions for API responses
│   │   ├── App.tsx          # Master application layout with Basic vs Advanced modes
│   │   └── theme.ts         # Design tokens, color palettes, and sizing constraints
│   ├── index.html           # HTML5 document template
│   └── package.json         # Node.js dependencies and script definitions
├── Browser Extension/       # Chrome Manifest V3 browser extension
│   ├── manifest.json        # Extension configuration & permissions
│   ├── src/                 # Background worker, content script, popup, and ONNX runtime
│   ├── icons/               # Extension icons
│   └── model/               # Quantized ONNX model and metadata for client-side local inference
├── Models/                  # Serialized trained model weights and metadata
│   ├── CatBoost/            # CatBoost URL classifier (`catboost_model.cbm`) & metrics
│   ├── Meta-Learner/        # Stacking ensemble meta-learner (`meta_learner.pkl`)
│   ├── NLP-DistilBERT/      # DistilBERT transformer safetensors & tokenizer configs
│   ├── Vision-EfficientNet/ # EfficientNet-B3 PyTorch weights (`efficientnet_b3_phishguard.pth`)
│   └── Browser-ONNX/        # Client-side ONNX runtime model for instant evaluation
├── Registry/                # Model registry configuration and active model pointers
├── Tests/                   # Complete automated test suites
│   ├── Backend/             # 19 Pytest test suites covering chaos, fusion, SSRF, XAI, etc.
│   ├── Frontend/            # Unit test suites verifying evidence provenance and engine state
│   └── E2E/                 # End-to-end integration and smoke test scripts
└── README.md                # System documentation and execution guide
```

---

## 🚀 Quick Start Guide

### 1. Backend Service Setup

#### Prerequisites
- Python 3.11+ (or Python 3.13)
- (Optional) MongoDB instance running on `localhost:27017`

#### Installation & Execution
```bash
# Navigate to Backend folder
cd "Source Code/Backend"

# Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at `http://localhost:8000/docs`.

---

### 2. Frontend Application Setup

#### Prerequisites
- Node.js 18+ (Node 20+ recommended)
- npm or yarn

#### Installation & Execution
```bash
# Navigate to Frontend folder
cd "Source Code/Frontend"

# Install dependencies
npm install

# Start development server with proxy to backend (port 8000)
npm run dev

# Run production build validation
npm run build

# Run unit tests
npm run test:status
```
The application will be accessible at `http://localhost:5173`.

---

### 3. Chrome / Edge Browser Extension Setup

1. Open Google Chrome or Microsoft Edge.
2. Navigate to `chrome://extensions/` (or `edge://extensions/`).
3. Enable **Developer mode** (toggle switch in the top right).
4. Click **Load unpacked**.
5. Select the `Source Code/Browser Extension/` directory.
6. The PhishGuard extension icon will appear in your browser toolbar, enabling real-time on-device URL analysis and backend deep-scan synchronization.

---

## 🧪 Testing and Validation

### Run Backend Unit & Integration Tests (183 tests)
```bash
cd "Source Code/Backend"
pytest tests/ -v
```

### Run Frontend Unit Tests
```bash
cd "Source Code/Frontend"
npm run test:status
```

---

## 🛡️ Core Security Architecture
- **SSRF & Private Network Protection**: RFC 1918, RFC 4193, loopback, link-local, and cloud metadata (169.254.169.254) addresses are strictly blocked before issuing network queries.
- **Controlled TI Synchronization**: In-memory caching with atomic threading locks prevents duplicate network calls during feed synchronizations.
- **Explainable AI (XAI)**: SHAP tree explainability, Grad-CAM visual heatmaps, and structured evidence provenance prevent hallucinated or fake 0% scores.
