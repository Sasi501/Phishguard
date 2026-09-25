// PhishGuard -- Background Service Worker
// Intercepts navigation, calls API, updates icon & triggers alerts
// On-device ONNX inference runs first for fast local results.

const API_BASE = "http://127.0.0.1:8000/api"; // Change to your deployed URL

// ─── On-Device ONNX Inference ──────────────────────────────────────────────
// Uses onnxruntime-web via CDN — no build step required
import { extractFeatures } from './feature_extractor.js';

const ONNX_CDN = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.19.2/dist/ort.min.js';
const ONNX_MODEL_PATH = chrome.runtime.getURL('model/phishguard_url_classifier.onnx');
const LOCAL_CONFIDENCE_THRESHOLD = 0.65; // Only trust local if score >= 65% or <= 35%

let _ortSession = null;
let _onnxLoading = false;

async function _loadOnnxRuntime() {
  if (_onnxLoading) return;
  _onnxLoading = true;
  try {
    // Dynamically import onnxruntime-web from CDN
    const { default: ort } = await import(ONNX_CDN);
    _ortSession = await ort.InferenceSession.create(ONNX_MODEL_PATH);
    console.log('[PhishGuard ONNX] Local model loaded:', ONNX_MODEL_PATH);
  } catch (e) {
    console.warn('[PhishGuard ONNX] Could not load local model, will use API only:', e.message);
    _ortSession = null;
  }
}

/**
 * Run on-device inference for a URL.
 * Returns null if local model is not available or result confidence is too low.
 */
async function localInfer(url) {
  if (!_ortSession) return null;
  try {
    const features = extractFeatures(url); // Float32Array[19]
    const tensor = new (await import(ONNX_CDN)).Tensor('float32', features, [1, features.length]);
    const feeds = { features: tensor };
    const results = await _ortSession.run(feeds);

    // CatBoost ONNX output: probabilities shape [1, 2] — [prob_safe, prob_phishing]
    const probs = results.probabilities?.data || results[Object.keys(results)[0]]?.data;
    if (!probs || probs.length < 2) return null;

    const phishingProb = probs[1];
    const safeProb = probs[0];

    // Only return a local result if confidence is high (avoid uncertain zone)
    const maxConf = Math.max(phishingProb, safeProb);
    if (maxConf < LOCAL_CONFIDENCE_THRESHOLD) {
      console.log(`[PhishGuard ONNX] Low confidence (${(maxConf * 100).toFixed(1)}%), deferring to API`);
      return null;
    }

    const riskLevel = phishingProb >= 0.70 ? 'phishing' : phishingProb >= 0.40 ? 'suspicious' : 'safe';
    console.log(`[PhishGuard ONNX] Local result: ${riskLevel} (${(phishingProb * 100).toFixed(1)}%)`);
    return {
      risk_level: riskLevel,
      confidence: phishingProb,
      reason: '[On-Device] Classified by local ONNX model without network request.',
      signals: ['on_device_inference'],
      local: true,
    };
  } catch (e) {
    console.warn('[PhishGuard ONNX] Local inference error:', e.message);
    return null;
  }
}

// Start loading the ONNX model in the background immediately
_loadOnnxRuntime();

const ICON_STATES = {
  safe:       { color: "#39ff14", label: "✓" },
  suspicious: { color: "#ffaa00", label: "!" },
  phishing:   { color: "#ff003c", label: "✕" },
  loading:    { color: "#00e5ff", label: "…" },
  error:      { color: "#8b949e", label: "?" },
};

// In-memory LRU cache per session
class LRUCache {
  constructor(maxSize) {
    this.maxSize = maxSize;
    this.cache = new Map();
  }
  get(key) {
    if (!this.cache.has(key)) return undefined;
    const val = this.cache.get(key);
    this.cache.delete(key); // remove
    this.cache.set(key, val); // add to end (most recently used)
    return val;
  }
  set(key, value) {
    if (this.cache.has(key)) this.cache.delete(key);
    this.cache.set(key, value);
    if (this.cache.size > this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey); // evict least recently used
    }
  }
  has(key) { return this.cache.has(key); }
}

const sessionCache = new LRUCache(500);

// Track tabs currently being scanned
const pendingScans = new Set();


// ─── Icon Drawing ────────────────────────────────────────────────────────────

function drawIcon(state) {
  const { color, label } = ICON_STATES[state] || ICON_STATES.loading;
  const size = 32;
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext("2d");

  // Background circle
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();

  // Inner white circle for depth
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size / 2 - 3, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(255,255,255,0.15)";
  ctx.fill();

  // Label text
  ctx.fillStyle = "#ffffff";
  ctx.font = `bold ${size * 0.5}px sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, size / 2, size / 2 + 1);

  return ctx.getImageData(0, 0, size, size);
}

async function setTabIcon(tabId, state) {
  try {
    const imageData = drawIcon(state);
    await chrome.action.setIcon({ tabId, imageData: { 32: imageData } });

    // Badge text for extra visibility
    const badges = { safe: "", suspicious: "!", phishing: "!!", loading: "", error: "?" };
    const badgeColors = { safe: "#39ff14", suspicious: "#ffaa00", phishing: "#ff003c", loading: "#00e5ff", error: "#8b949e" };

    await chrome.action.setBadgeText({ tabId, text: badges[state] || "" });
    await chrome.action.setBadgeBackgroundColor({ tabId, color: badgeColors[state] || "#8b949e" });
  } catch (e) {
    // Tab may have been closed
  }
}


// ─── URL Scanning ─────────────────────────────────────────────────────────────

function getOfflineEstimate(url) {
  try {
    const parsed = new URL(url);
    if (/^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(parsed.hostname)) {
      return { risk_level: "suspicious", confidence: 0.6, reason: "[Offline Estimate] Direct IP address detected.", signals: ["ip_address_url"] };
    }
    const badWords = ["login", "verify", "secure", "update", "account"];
    if (badWords.some(w => url.toLowerCase().includes(w))) {
      return { risk_level: "suspicious", confidence: 0.5, reason: "[Offline Estimate] Suspicious keywords found in URL.", signals: ["deceptive_path"] };
    }
    return { risk_level: "safe", confidence: 0.9, reason: "[Offline Estimate] Server unreachable, but no immediate red flags.", signals: [] };
  } catch(e) {
    return { risk_level: "suspicious", confidence: 0.5, reason: "[Offline Estimate] Invalid URL format.", signals: [] };
  }
}

function getRedirectAnalysis(raw) {
  const analysis = raw?.redirect_analysis;
  if (!analysis || typeof analysis !== "object") return null;
  return {
    original_url: analysis.original_url || "",
    final_url: analysis.final_url || "",
    num_redirects: Number.isFinite(analysis.num_redirects) ? analysis.num_redirects : 0,
    resolution_state: analysis.resolution_state || "unavailable",
    suspicious_redirects: Boolean(analysis.suspicious_redirects),
    loop_detected: Boolean(analysis.loop_detected),
    has_meta_refresh: Boolean(analysis.has_meta_refresh),
  };
}

async function scanURL(url, tabId) {
  // Skip non-http URLs (chrome://, file://, etc.)
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    await setTabIcon(tabId, "safe");
    return;
  }

  // Skip extension pages
  if (url.startsWith("chrome-extension://")) return;

  // Session cache hit
  if (sessionCache.has(url)) {
    const cached = sessionCache.get(url);
    await applyResult(cached, tabId, url);
    return;
  }

  // Prevent duplicate concurrent scans for same tab
  if (pendingScans.has(tabId)) return;
  pendingScans.add(tabId);

  await setTabIcon(tabId, "loading");

  await chrome.storage.local.set({
    [`tab_${tabId}`]: { url, state: "loading", reason: "Scanning...", signals: [], confidence: 0 }
  });

  // ── Try on-device ONNX inference first ──────────────────────────────────
  const localResult = await localInfer(url);
  if (localResult) {
    // High-confidence local result — apply immediately, no API call
    sessionCache.set(url, localResult);
    await applyResult(localResult, tabId, url);
    pendingScans.delete(tabId);
    return;
  }

  // Helper: detect common shortener hosts (kept small to avoid false positives)
  function isLikelyShortener(u) {
    try {
      const parsed = new URL(u);
      const host = parsed.hostname.split(":")[0].toLowerCase();
      const KNOWN = new Set([
        "bit.ly", "t.co", "tinyurl.com", "ow.ly", "is.gd", "rebrand.ly", "buff.ly",
        "goo.gl", "v.gd", "cutt.ly", "short.io", "rb.gy", "tiny.cc", "lnkd.in",
        "surl.li", "shorturl.at", "t.ly", "clck.ru", "qr.ae", "adf.ly", "bc.vc",
        "j.mp", "x.co", "su.pr", "soo.gd", "s.id", "rotf.lol", "cli.re", "bl.ink",
        "tiny.one", "hyperurl.co", "1url.com", "0rz.tw", "b.link"
      ]);
      return KNOWN.has(host);
    } catch (e) {
      return false;
    }
  }

  try {
    // 15-second timeout — backend can be slow due to WHOIS + Gemini
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);

    // If URL is a likely shortener, call the domain analyze endpoint (returns expanded final_url)
    if (isLikelyShortener(url)) {
      const response = await fetch(`${API_BASE}/analyze-domain/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!response.ok) throw new Error(`API error ${response.status}`);
      const raw = await response.json();

      const result = {
        risk_level:  raw.domain_risk_level || raw.risk_level || "safe",
        confidence:  raw.domain_score || raw.confidence || 0,
        reason:      raw.metadata?.ssl_error || raw.reason || "",
        signals:     raw.domain_signals || raw.signals || [],
        redirect_analysis: getRedirectAnalysis(raw),
      };

      // Cache mapped result
      sessionCache.set(url, result);

      await applyResult(result, tabId, url);

      return;
    }

    // Default (non-shortener): use the compatibility /scan/ endpoint
    const formData = new FormData();
    formData.append("url", url);

    const response = await fetch(`${API_BASE}/scan/`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (!response.ok) throw new Error(`API error ${response.status}`);

    const raw = await response.json();

    // Map backend fields → extension fields
    const result = {
      risk_level:  raw.ensemble_risk_level || raw.risk_level || "safe",
      confidence:  raw.ensemble_score_percent != null
                     ? raw.ensemble_score_percent / 100
                     : (raw.confidence || 0),
      reason:      raw.xai_summary || raw.reason || "",
      signals:     raw.reasons || raw.signals || [],
      redirect_analysis: getRedirectAnalysis(raw),
    };

    // Cache mapped result
    sessionCache.set(url, result);

    await applyResult(result, tabId, url);

  } catch (err) {
    console.error("PhishGuard scan error:", err);
    const fallbackResult = getOfflineEstimate(url);
    await applyResult(fallbackResult, tabId, url);
  } finally {
    pendingScans.delete(tabId);
  }
}


async function applyResult(result, tabId, url) {
  const { risk_level, confidence, reason, signals, redirect_analysis } = result;

  // Save to local storage for popup
  await chrome.storage.local.set({
    [`tab_${tabId}`]: {
      url,
      state: risk_level,
      reason,
      signals: signals || [],
      confidence: confidence || 0,
      redirect_analysis: redirect_analysis || null,
    }
  });

  await setTabIcon(tabId, risk_level);

  // For PHISHING — inject a blocking alert via content script
  if (risk_level === "phishing") {
    try {
      await chrome.tabs.sendMessage(tabId, {
        type: "PHISHING_ALERT",
        reason,
        signals: signals || [],
        confidence,
        url,
      });
    } catch (e) {
      // Content script may not be ready yet — it will check on its own load
    }
  }
}


// ─── Event Listeners ──────────────────────────────────────────────────────────

// Trigger on every navigation (before page loads)
chrome.webNavigation.onCommitted.addListener(async (details) => {
  // Only main frame, not iframes
  if (details.frameId !== 0) return;

  // Skip internal Chrome pages
  const skip = ["chrome://", "chrome-extension://", "about:", "data:", "javascript:"];
  if (skip.some(s => details.url.startsWith(s))) return;

  await scanURL(details.url, details.tabId);
});

// Clean up storage when tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.local.remove(`tab_${tabId}`);
  pendingScans.delete(tabId);
});

// Re-scan when tab is activated (in case icon got reset)
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const stored = await chrome.storage.local.get(`tab_${activeInfo.tabId}`);
  const data = stored[`tab_${activeInfo.tabId}`];
  if (data && data.state) {
    await setTabIcon(activeInfo.tabId, data.state);
  }
});

// ─── Auto-set demo token so popup skips login gate ────────────────────────
chrome.storage.local.get(["pg_token"], (stored) => {
  if (!stored.pg_token) {
    chrome.storage.local.set({ pg_token: "demo-token" });
  }
});
