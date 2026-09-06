# 🛡️ PhishGuard — Full Project Analysis

## 1. Project Purpose

PhishGuard is a **real-time AI-powered phishing detection system** delivered as a **Chrome browser extension** backed by a **cloud API**. Its core mission: intercept every URL a user navigates to, analyze it for phishing signals using Google Gemini AI, and immediately alert or block the user if the site is malicious — all before they can be deceived into entering credentials or personal data.

---

## 2. Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **Extension Platform** | Chrome Extension Manifest V3 | Browser integration |
| **Extension Worker** | JavaScript (Service Worker) | Background URL interception |
| **Extension UI** | HTML + Vanilla CSS + JS | Popup & content injection |
| **Backend Framework** | Django 4.2 + Django REST Framework | REST API server |
| **AI Engine** | Google Gemini 1.5 Flash (`gemini-1.5-flash-latest`) | URL risk classification |
| **Database** | SQLite (dev) → PostgreSQL (prod) | Persistent URL scan cache |
| **Cache Layer** | Django DB Cache → Redis (prod) | Fast TTL-based result caching |
| **CORS** | `django-cors-headers` | Allow extension ↔ API communication |
| **API Throttling** | DRF AnonRateThrottle | Rate limiting (200 req/day/IP) |
| **Deployment** | Gunicorn + Railway/Render/GCP | Production WSGI server |
| **Icon Generation** | Python (`generate_icons.py`) | One-time PNG icon creation |

---

## 3. Architecture Overview

```
User navigates to URL
        │
        ▼
background.js (Service Worker — MV3)
 ├─ Check: non-HTTP? → mark safe, skip
 ├─ Check: session cache (Map, max 500 entries)? → instant result
 └─ POST { url } → Django /api/scan/
                    │
                    ├─ Whitelisted domain? → safe (0.99 confidence), no AI call
                    ├─ DB cache hit (within 6h TTL)? → return cached
                    └─ Gemini 1.5 Flash API
                          │
                          └─ JSON: { risk_level, confidence, reason, signals }
                                    │
                              Save to SQLite (6h TTL)
                                    │
                              Response → extension

Result Applied:
  🟢 safe       → Green icon
  🟡 suspicious  → Yellow icon + "!" badge
  🔴 phishing   → Red icon + "!!" badge + full-page blocking overlay
```

### Extension Components

| File | Role |
|---|---|
| `background.js` | Service worker; intercepts `webNavigation.onCommitted`, scans URLs, applies icon state, sends phishing message to content script |
| `content.js` | Injected into every page at `document_start`; listens for `PHISHING_ALERT` message and renders the full-page blocking modal |
| `popup.html/js` | Toolbar popup; reads `chrome.storage.local` for current tab's scan result and renders status card with confidence bar, reason, signals |
| `manifest.json` | MV3 manifest; declares permissions: `tabs`, `activeTab`, `storage`, `webNavigation`, `notifications`, `<all_urls>` |

### Backend Components

| File | Role |
|---|---|
| `views.py` → `ScanURLView` | Core API endpoint; whitelist check → DB cache → Gemini call → store & respond |
| `views.py` → `HealthCheckView` | `/api/health/` uptime probe |
| `gemini_service.py` | Constructs structured prompt, calls Gemini API, strips markdown from response, validates + normalizes JSON |
| `models.py` → `URLScanResult` | DB cache model: `url_hash` (SHA-256), `risk_level`, `confidence`, `reason`, `signals` (JSONField), `expires_at` |
| `settings.py` | Django settings; DB cache, CORS, DRF throttling, Gemini API key from `.env` |

---

## 4. How It Works — Step by Step

1. **User visits a page** → Chrome fires `webNavigation.onCommitted`
2. **background.js** filters out `chrome://`, `file://`, `data:` URLs — only processes `http/https`
3. Checks **session-level in-memory cache** (fast, no network hop)
4. If not cached, sets icon to **grey "loading"** state and POSTs URL to `/api/scan/`
5. **Django** checks whitelist first (15 major trusted domains — instant safe response)
6. Then checks **SQLite DB cache** by SHA-256 hash of URL — returns if within 6h TTL
7. Otherwise calls **Gemini 1.5 Flash** with a carefully engineered system prompt listing 10 signal types
8. Response is parsed, validated, stored in DB, and returned
9. **background.js** applies the result:
   - Updates tab icon color + badge text
   - Stores in `chrome.storage.local` for popup
   - If phishing: sends `PHISHING_ALERT` message to content script
10. **content.js** receives the alert and injects a **full-page dark modal** blocking access, with confidence bar, reason text, signal tags, and two buttons: "Go Back to Safety" or "Proceed Anyway"
11. **popup.js** reads storage and renders a premium status card when user clicks the toolbar icon

---

## 5. Current System Capabilities ✅

- ✅ **End-to-end phishing detection** pipeline working
- ✅ **Three-tier caching:** session → DB → Gemini (minimizes latency & cost)
- ✅ **Domain whitelist** bypasses AI for 15 major trusted sites
- ✅ **Full-page blocking overlay** with animated shield icon for phishing sites
- ✅ **Rich popup UI** with confidence bar, signals, reason, cached badge
- ✅ **Dynamic canvas-drawn icons** — no static icon files needed at runtime
- ✅ **Rate limiting** (200/day per IP via DRF)
- ✅ **Health check endpoint** for uptime monitoring
- ✅ **Admin panel** via Django admin for DB inspection
- ✅ **Manifest V3 compliant** (future-proof Chrome extension architecture)
- ✅ **Production-ready guidance** (Gunicorn, PostgreSQL, Redis, env vars)
- ✅ **XSS-safe** content injection (`escapeHTML` used in all user-visible text)

---

## 6. Drawbacks & Current Weaknesses ⚠️

### Backend
| Issue | Impact |
|---|---|
| `CORS_ALLOW_ALL_ORIGINS = True` is set (overriding the restricted list above it) | **Security risk** — any origin can call the API in production |
| SQLite for caching | Not suitable for concurrent production load; no TTL auto-purge |
| No authentication on `/api/scan/` | Anyone who discovers the URL can consume the Gemini quota |
| `google-generativeai` pinned to `>=0.7.0` but code uses `google.genai` (new SDK style) | Could break on minor version changes |
| No async support | Django sync views block threads during Gemini calls (avg ~800ms) |
| No URL normalization | `https://site.com/` and `https://site.com` are cached separately |
| Whitelist is hardcoded | Can't be updated at runtime; doesn't cover subdomains of safe brands properly |
| No logging / monitoring | No structured logs, no Sentry, no metrics |

### Extension
| Issue | Impact |
|---|---|
| `API_BASE` is hardcoded to `http://127.0.0.1:8000` | Breaks when server is remote; requires manual code edit |
| `chrome-extension://` check is redundant | `webNavigation.onCommitted` events won't fire for extension pages anyway |
| Session cache capped at 500 entries with LRU-like eviction (only removes first, not least-recently-used) | Not true LRU; infrequently accessed URLs evict recent ones |
| No retry logic on API failure | One network error silently marks tab as "error" indefinitely |
| `notifications` permission declared but never used | Unnecessary permission can flag extension in review |
| Content script runs at `document_start` but is passive until message received | Wastes resources on every page load |
| No offline mode | If server is down, extension shows error with no fallback |

---

## 7. Enhancement Ideas 💡

### Immediate / High Priority
- **Fix CORS in production**: Set `CORS_ALLOW_ALL_ORIGINS = False` and whitelist only the specific Chrome extension origin (`chrome-extension://[extension-id]`)
- **Add API key authentication**: Require `X-API-Key` header from the extension to prevent quota abuse
- **URL normalization**: Strip trailing slashes, normalize scheme, lowercase host before hashing
- **Configurable `API_BASE`**: Store backend URL in `chrome.storage.sync` so users can point to their own server without code changes
- **Auto-cleanup expired cache**: Add a Django management command (`manage.py clearcache`) or celery task to purge expired `URLScanResult` rows

### Medium Priority
- **Async Django views**: Switch to `async def post()` with `httpx` for non-blocking Gemini calls, increasing throughput significantly
- **True LRU session cache**: Use a proper LRU implementation or use `chrome.storage.session` (available in MV3)
- **Retry with exponential backoff**: Retry failed API calls 1–2 times before showing error state
- **Expanded whitelist with dynamic updates**: Fetch whitelist from a CDN-hosted JSON file, or integrate with a public URL reputation blocklist (e.g., Google Safe Browsing API)
- **User-reported URLs**: Add "Report as Phishing" / "Report as Safe" button in popup to collect feedback and improve the model context
- **Admin dashboard web UI**: A simple React/Vue frontend showing recent scans, stats, top detected signals

### Architecture Enhancements
- **Redis cache in production**: Replaces DB cache with sub-millisecond TTL lookups across multiple workers
- **PostgreSQL in production**: Replace SQLite with PostgreSQL for concurrent safe writes
- **Structured logging + Sentry**: Add `structlog` and Sentry integration for error tracking in production
- **Rate limiting per extension ID**: More granular than per-IP — prevents abuse while allowing legitimate high-usage scenarios

---

## 8. Future Update Ideas 🚀

| Feature | Description |
|---|---|
| **Multi-browser support** | Port to Firefox using WebExtensions API (manifest needs slight adaptation) |
| **Machine learning model** | Fine-tune a small BERT/DistilBERT classifier as a fast pre-filter before calling Gemini — reduces latency for obvious cases |
| **Phishing screenshot analysis** | Use Gemini Vision to analyze the actual page screenshot (DOM + visual) for brand impersonation |
| **Link hover preview** | Scan URLs on hover before the user clicks, showing a mini tooltip verdict |
| **Email integration** | Browser extension that scans links inside Gmail / Outlook web |
| **Threat intelligence feeds** | Integrate PhishTank, URLhaus, or OpenPhish feeds for blocklist augmentation |
| **Dashboard companion site** | User account with scan history, statistics, and threat reports |
| **Notification-based alerts** | Use the already-declared `notifications` permission to show OS-level alerts for phishing sites detected in background tabs |
| **QR code scanning** | Decode QR codes visible on page and scan the embedded URL |
| **Mobile companion app** | Use the Django backend to power an iOS/Android app for link checking |
| **Enterprise mode** | Centralized policy management, admin override for corporate whitelist/blacklist, audit logs |
| **Gemini model upgrades** | Swap to `gemini-2.0-flash` or `gemini-2.5-pro` as models improve; use structured output (`response_schema`) to eliminate JSON parsing fragility |

---

## 9. Project Outcome & Quality Assessment

| Dimension | Score | Notes |
|---|---|---|
| **Concept / Idea** | 🌟🌟🌟🌟🌟 | Highly practical, real-world cybersecurity tool |
| **Architecture** | 🌟🌟🌟🌟 | Clean separation; caching layers well designed |
| **Backend Code Quality** | 🌟🌟🌟🌟 | Clean DRF views, good error handling, type hints |
| **Extension Code Quality** | 🌟🌟🌟🌟 | MV3 compliant, clean async patterns, good UX states |
| **UI/UX Design** | 🌟🌟🌟🌟🌟 | Premium dark theme, animated blocking overlay, confidence bar |
| **Security Hardening** | 🌟🌟🌟 | CORS bug, no auth on API — needs production hardening |
| **Production Readiness** | 🌟🌟🌟 | Good guidance in README, but config gaps remain |
| **Test Coverage** | 🌟 | No test files found — major gap |
| **Overall** | **~3.8 / 5** | Excellent prototype; needs security hardening & tests before production |

---

## 10. Summary

PhishGuard is a **well-architected, polished prototype** of an AI-powered browser security tool. It demonstrates strong full-stack thinking — from low-level Chrome extension event APIs to Django REST backends and LLM integration. The UI is premium-grade, the caching strategy is thoughtful, and the Gemini prompt engineering produces structured, actionable results.

The primary gaps are in **production security** (open CORS, no API auth), **test coverage** (zero tests), and **scalability** (sync views, SQLite). These are all straightforward to address and would elevate this project from prototype to production-grade.
