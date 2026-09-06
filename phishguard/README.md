# 🛡️ PhishGuard — AI-Powered Phishing URL Detector

A Chrome extension + Django cloud backend that detects phishing URLs in real-time using Google Gemini AI.

---

## 📁 Project Structure

```
phishguard/
├── backend/                        # Django REST API
│   ├── phishguard_project/         # Django project settings & URLs
│   ├── detector/                   # Core app: models, views, Gemini service
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── extension/                      # Chrome Extension (Manifest V3)
│   ├── manifest.json
│   ├── icons/                      # Auto-generated PNG icons
│   └── src/
│       ├── background.js           # Service worker — scans URLs, updates icon
│       ├── content.js              # Injects phishing warning overlay
│       ├── popup.html              # Extension popup UI
│       └── popup.js                # Popup logic
└── generate_icons.py               # One-time icon generator script
```

---

## ⚙️ How It Works

```
User visits URL
      │
      ▼
background.js (service worker)
      │  POST { url } 
      ▼
Django API /api/scan/
      │
      ├─ DB cache hit? ──► return cached result
      │
      └─ Gemini 1.5 Flash API
            │  Returns: { risk_level, confidence, reason, signals }
            ▼
      Save to DB cache (6h TTL)
            │
            ▼
      Response to extension
            │
      ┌─────┴─────┐
      │           │
   🟢 safe    🟡 suspicious    🔴 phishing
   Icon green  Icon yellow     Icon red +
                               Blocking overlay alert
```

---

## 🚀 Backend Setup

### 1. Create virtual environment & install deps

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env:
#   DJANGO_SECRET_KEY=<generate a long random string>
#   GEMINI_API_KEY=<your key from https://aistudio.google.com>
#   DEBUG=True
```

### 3. Run migrations & create cache table

```bash
python manage.py migrate
python manage.py createcachetable
python manage.py createsuperuser   # optional, for admin panel
```

### 4. Start the server

```bash
python manage.py runserver
# API available at: http://127.0.0.1:8000/api/scan/
```

### Test the API manually

```bash
curl -X POST http://127.0.0.1:8000/api/scan/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://paypa1-secure-login.tk/verify/account"}'
```

Expected response:
```json
{
  "risk_level": "phishing",
  "confidence": 0.97,
  "reason": "Typosquatted PayPal domain combined with suspicious TLD and deceptive path.",
  "signals": ["typosquatting", "suspicious_tld", "brand_impersonation", "deceptive_path"],
  "cached": false
}
```

---

## 🧩 Chrome Extension Setup

### 1. Generate icons (one time only)

```bash
cd ..   # back to phishguard root
python generate_icons.py
```

### 2. Point extension to your backend

Open `extension/src/background.js` and update:
```js
const API_BASE = "http://127.0.0.1:8000/api";
// Change to your deployed URL in production:
// const API_BASE = "https://your-app.railway.app/api";
```

### 3. Load in Chrome

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top right toggle)
3. Click **"Load unpacked"**
4. Select the `extension/` folder
5. PhishGuard icon appears in the toolbar ✅

---

## 🌐 Deploying to Production

### Backend (Railway / Render / GCP)

1. Set environment variables on your platform:
   - `DJANGO_SECRET_KEY`
   - `GEMINI_API_KEY`
   - `DEBUG=False`
   - `ALLOWED_HOSTS=your-domain.com`

2. Switch to PostgreSQL (recommended):
   ```python
   # In settings.py, replace DATABASES with:
   import dj_database_url
   DATABASES = {'default': dj_database_url.config()}
   ```
   Add `dj-database-url` and `psycopg2-binary` to requirements.txt

3. Switch to Redis cache (recommended for scale):
   ```python
   CACHES = {
       "default": {
           "BACKEND": "django.core.cache.backends.redis.RedisCache",
           "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1"),
       }
   }
   ```
   Add `redis` to requirements.txt

4. Run with Gunicorn:
   ```bash
   gunicorn phishguard_project.wsgi:application --bind 0.0.0.0:$PORT
   ```

### Extension (Chrome Web Store)

1. Update `API_BASE` in `background.js` to production URL
2. Zip the `extension/` folder
3. Submit to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)

---

## 🔑 Getting Your Gemini API Key

1. Visit [https://aistudio.google.com](https://aistudio.google.com)
2. Sign in with Google
3. Click **"Get API Key"** → **"Create API key"**
4. Copy key → paste into `.env` as `GEMINI_API_KEY`

Free tier: 15 requests/minute, 1 million tokens/day — plenty for development.

---

## 📊 Risk Levels

| Level | Icon | Meaning |
|-------|------|---------|
| `safe` | 🟢 | Legitimate, trusted site |
| `suspicious` | 🟡 | Unusual patterns — proceed carefully |
| `phishing` | 🔴 | High-confidence malicious site — **blocking alert shown** |

---

## 🏗️ Architecture Notes

- **Caching**: Results cached in Django DB for 6 hours (configurable via `CACHE_URL_TTL` in settings)
- **Whitelist**: Major known-safe domains (Google, GitHub, etc.) skip API calls entirely
- **Rate limiting**: DRF throttling set to 200 requests/day per IP (adjust in settings)
- **Session cache**: Extension also caches results in-memory per browser session for instant re-checks
