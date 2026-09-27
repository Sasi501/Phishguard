// PhishGuard -- Background Service Worker
// Intercepts navigation, calls API, updates icon & triggers alerts
// Backend analysis is authoritative; ONNX is only an explicitly labeled pre-screen.

import {
  BACKEND_BASE_URL,
  HEALTH_URL,
  HEALTH_TIMEOUT_MS,
  REQUEST_TIMEOUT_MS,
  SCAN_URL,
} from './config.js';

// ─── On-Device ONNX Inference ──────────────────────────────────────────────
// Uses onnxruntime-web via CDN — no build step required
import { extractFeatures } from './feature_extractor.js';

// The vector fed to the session is always built from model_meta.json, which
// backend/ml/export_onnx.py writes directly from the trained model's own
// feature_names_. The schema is validated before the tensor is created and a
// warm-up inference runs at load time, so a wrong-shaped or wrong-ordered
// vector can never reach the model silently. When local inference cannot run
// the pre-screen is null — nothing is fabricated; the backend stays the only
// source of truth.

const ONNX_CDN = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.19.2/dist/ort.min.js';
const ONNX_MODEL_PATH = chrome.runtime.getURL('model/phishguard_url_classifier.onnx');
const ONNX_META_PATH = chrome.runtime.getURL('model/model_meta.json');
const LOCAL_CONFIDENCE_THRESHOLD = 0.65; // Only trust local if score >= 65% or <= 35%

let _ort = null;
let _ortSession = null;
let _modelMeta = null;
let _onnxLoading = false;

/** Read a named output from either a Map or a plain-object result. */
function _readOutput(results, name) {
  if (!results) return undefined;
  if (typeof results.get === 'function') return results.get(name);
  return results[name];
}

function _toScalar(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') return value;
  if (value.data && value.data.length > 0) return Number(value.data[0]);
  return null;
}

/**
 * Read a [prob_safe, prob_phishing] pair out of the `probabilities` output.
 *
 * CatBoost exports `probabilities` as `seq(map(int64, tensor(float)))`, which
 * onnxruntime-web surfaces as an Array of Map/object — NOT as a tensor with a
 * `.data` buffer. Handles that, a plain Map, and a regular tensor alike.
 *
 * @returns {{safeProb: number, phishingProb: number}|null}
 */
export function parseProbabilities(raw) {
  if (!raw) return null;

  if (raw.data && typeof raw.data.length === 'number' && raw.data.length >= 2) {
    return { safeProb: Number(raw.data[0]), phishingProb: Number(raw.data[1]) };
  }

  const entry = Array.isArray(raw) ? raw[0] : raw;
  if (!entry) return null;

  const lookup = (key) => (typeof entry.get === 'function' ? entry.get(key) : entry[key]);
  const safeProb = _toScalar(lookup(0));
  const phishingProb = _toScalar(lookup(1));
  if (safeProb === null || phishingProb === null) return null;
  return { safeProb, phishingProb };
}

async function _loadOnnxRuntime() {
  if (_onnxLoading) return;
  _onnxLoading = true;
  try {
    // Dynamically import onnxruntime-web from CDN
    const { default: ort } = await import(ONNX_CDN);

    const metaResponse = await fetch(ONNX_META_PATH);
    if (!metaResponse.ok) {
      throw new Error(`model_meta.json unavailable (HTTP ${metaResponse.status}).`);
    }
    const meta = await metaResponse.json();
    if (
      !Array.isArray(meta.feature_names) ||
      !Number.isInteger(meta.num_features) ||
      meta.feature_names.length !== meta.num_features ||
      meta.input_name !== 'features'
    ) {
      throw new Error('model_meta.json declares an inconsistent feature schema.');
    }

    const session = await ort.InferenceSession.create(ONNX_MODEL_PATH);

    // Warm-up inference: proves a real inference executes AND enforces the
    // dimension check before any result can be produced. A model whose input
    // width disagrees with model_meta.json fails here and disables local
    // screening instead of ever returning a wrong-shaped answer.
    const probe = new ort.Tensor(
      'float32',
      new Float32Array(meta.num_features),
      [1, meta.num_features]
    );
    await session.run({ features: probe });

    _ort = ort;
    _modelMeta = meta;
    _ortSession = session;
    console.log(`[PhishGuard ONNX] Local model loaded: ${ONNX_MODEL_PATH} (${meta.num_features} features)`);
  } catch (e) {
    _ort = null;
    _modelMeta = null;
    _ortSession = null;
    console.warn('[PhishGuard ONNX] Could not load local model, will use API only:', e.message);
  }
}

/**
 * Run on-device inference for a URL.
 * Returns null if local model is not available or result confidence is too low.
 */
export async function localInfer(url) {
  if (!_ortSession || !_modelMeta || !_ort) return null;
  try {
    const features = extractFeatures(url, _modelMeta.feature_names);
    if (features.length !== _modelMeta.num_features) {
      throw new Error(
        `Feature vector length ${features.length} does not match model_meta.json ` +
          `num_features ${_modelMeta.num_features}.`
      );
    }
    const tensor = new _ort.Tensor('float32', features, [1, features.length]);
    const results = await _ortSession.run({ features: tensor });

    const parsed = parseProbabilities(_readOutput(results, 'probabilities'));
    if (!parsed) {
      console.warn('[PhishGuard ONNX] Model output did not contain two class probabilities.');
      return null;
    }
    const { safeProb, phishingProb } = parsed;

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
      phishing_probability: phishingProb,
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

/** True once the local ONNX session has loaded and a warm-up inference ran. */
export function isLocalModelReady() {
  return Boolean(_ortSession && _modelMeta);
}

/** The feature schema the local session was validated against (or null). */
export function getLocalModelMeta() {
  return _modelMeta;
}

const ICON_STATES = {
  safe:       { color: "#39ff14", label: "✓" },
  suspicious: { color: "#ffaa00", label: "!" },
  phishing:   { color: "#ff003c", label: "✕" },
  loading:    { color: "#00e5ff", label: "…" },
  error:      { color: "#8b949e", label: "?" },
};

// Track tabs currently being scanned
const pendingScans = new Map();


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

async function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const abortFromCaller = () => controller.abort();
  options.signal?.addEventListener("abort", abortFromCaller, { once: true });

  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (timedOut) {
      const timeoutError = new Error(`Request timed out after ${timeoutMs} ms.`);
      timeoutError.code = "REQUEST_TIMEOUT";
      throw timeoutError;
    }
    throw error;
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", abortFromCaller);
  }
}

async function responseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.error || `Backend returned HTTP ${response.status}.`;
  } catch {
    return `Backend returned HTTP ${response.status}.`;
  }
}

export function mapBackendResult(raw, url) {
  const score = raw.ensemble_score_percent;
  const validScore = typeof score === "number" && Number.isFinite(score) && score >= 0 && score <= 100;
  const validRiskLevel = ["safe", "suspicious", "phishing"].includes(raw.ensemble_risk_level);
  const analysisFailed = raw.analysis_status === "failed" || !validScore || !validRiskLevel;
  const riskLevel = validRiskLevel
    ? raw.ensemble_risk_level
    : "unavailable";
  const engineSignals = Array.isArray(raw.xai?.engine_signals)
    ? raw.xai.engine_signals.map(signal => {
        const hasScore = typeof signal.score === "number" && Number.isFinite(signal.score);
        const scoreType = signal.score_type || "engine_signal";
        const evidenceReturned = (hasScore && scoreType === "engine_signal") || Boolean(signal.match_status);
        return {
          engine: signal.engine || signal.source || "Engine",
          source: signal.source || "",
          status: signal.status || (evidenceReturned ? "available" : "unavailable"),
          score: hasScore ? signal.score : null,
          score_type: scoreType,
          url_scope: signal.url_scope || "",
          match_status: signal.match_status || "",
          reason: signal.reason || "",
        };
      })
    : [];

  return {
    url,
    state: analysisFailed ? "unavailable" : riskLevel,
    backend_status: "online",
    analysis_status: raw.analysis_status || "unknown",
    ensemble_score_percent: analysisFailed ? null : score,
    ensemble_risk_level: analysisFailed ? "unavailable" : riskLevel,
    xai_summary: raw.xai_summary || raw.xai?.summary || "",
    reasons: Array.isArray(raw.reasons) ? raw.reasons : [],
    individual_scores_percent:
      raw.individual_scores_percent && typeof raw.individual_scores_percent === "object"
        ? raw.individual_scores_percent
        : {},
    engine_signals: engineSignals,
    engine_status: raw.engine_status || {},
    redirect_analysis: getRedirectAnalysis(raw),
    server_url: BACKEND_BASE_URL,
  };
}

async function saveTabState(tabId, data) {
  await chrome.storage.local.set({ [`tab_${tabId}`]: data });
  const iconState = ["safe", "suspicious", "phishing", "loading"].includes(data.state)
    ? data.state
    : "error";
  await setTabIcon(tabId, iconState);

  if (data.state === "phishing" && data.backend_status === "online") {
    try {
      await chrome.tabs.sendMessage(tabId, {
        type: "PHISHING_ALERT",
        reason: data.xai_summary || data.reasons.join("; "),
        ensemble_score_percent: data.ensemble_score_percent,
        signals: data.reasons,
        url: data.url,
      });
    } catch {
      // The content script may not be ready yet.
    }
  }
}

export async function analyzeURL(url, tabId, signal) {
  if (!/^https?:\/\//i.test(url)) {
    await saveTabState(tabId, {
      url,
      state: "unavailable",
      backend_status: "unknown",
      error: "Only HTTP and HTTPS pages can be analyzed.",
      server_url: BACKEND_BASE_URL,
    });
    return;
  }

  await saveTabState(tabId, {
    url,
    state: "loading",
    backend_status: "connecting",
    message: "Connecting to the PhishGuard analysis server...",
    server_url: BACKEND_BASE_URL,
  });

  let healthResponse;
  try {
    healthResponse = await fetchWithTimeout(
      HEALTH_URL,
      { method: "GET", signal },
      HEALTH_TIMEOUT_MS,
    );
    if (!healthResponse.ok) {
      throw new Error(`Health check returned HTTP ${healthResponse.status}.`);
    }
    const health = await healthResponse.json();
    if (health.status !== "ok") {
      throw new Error("The backend health endpoint did not report status 'ok'.");
    }
  } catch (error) {
    if (signal.aborted) return;
    const localResult = await localInfer(url);
    if (signal.aborted) return;
    const message = error.code === "REQUEST_TIMEOUT"
      ? `Backend health check timed out at ${BACKEND_BASE_URL}.`
      : `Unable to reach the backend at ${BACKEND_BASE_URL}: ${error.message}`;
    await saveTabState(tabId, {
      url,
      state: "offline",
      backend_status: "offline",
      error: message,
      local_pre_screen: localResult
        ? {
            risk_level: localResult.risk_level,
            phishing_probability_percent: Number((localResult.phishing_probability * 100).toFixed(2)),
            label: "LOCAL PRE-SCREEN ONLY",
          }
        : null,
      server_url: BACKEND_BASE_URL,
    });
    return;
  }

  await saveTabState(tabId, {
    url,
    state: "loading",
    backend_status: "online",
    message: "PhishGuard online. Analyzing the current tab URL...",
    server_url: BACKEND_BASE_URL,
  });

  try {
    const formData = new FormData();
    formData.append("url", url);
    const response = await fetchWithTimeout(
      SCAN_URL,
      { method: "POST", body: formData, signal },
      REQUEST_TIMEOUT_MS,
    );
    if (!response.ok) {
      await saveTabState(tabId, {
        url,
        state: "error",
        backend_status: "online",
        error: await responseError(response),
        server_url: BACKEND_BASE_URL,
      });
      return;
    }

    const raw = await response.json();
    await saveTabState(tabId, mapBackendResult(raw, url));
  } catch (error) {
    if (signal.aborted) return;
    await saveTabState(tabId, {
      url,
      state: "error",
      backend_status: "online",
      error: error.code === "REQUEST_TIMEOUT"
        ? `Backend analysis timed out after ${REQUEST_TIMEOUT_MS} ms.`
        : `Backend analysis failed: ${error.message}`,
      server_url: BACKEND_BASE_URL,
    });
  }
}

function scanURL(url, tabId, force = false) {
  const existing = pendingScans.get(tabId);
  if (existing && !force) return existing.promise;
  if (existing) existing.controller.abort();

  const controller = new AbortController();
  const job = { controller, promise: null };
  job.promise = analyzeURL(url, tabId, controller.signal).finally(() => {
    if (pendingScans.get(tabId) === job) pendingScans.delete(tabId);
  });
  pendingScans.set(tabId, job);
  return job.promise;
}


// ─── Event Listeners ──────────────────────────────────────────────────────────

// Trigger on every navigation (before page loads)
chrome.webNavigation.onCommitted.addListener(async (details) => {
  // Only main frame, not iframes
  if (details.frameId !== 0) return;

  // Skip internal Chrome pages
  const skip = ["chrome://", "chrome-extension://", "about:", "data:", "javascript:"];
  if (skip.some(s => details.url.startsWith(s))) return;

  await scanURL(details.url, details.tabId, true);
});

// Clean up storage when tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.local.remove(`tab_${tabId}`);
  const pending = pendingScans.get(tabId);
  if (pending) pending.controller.abort();
  pendingScans.delete(tabId);
});

// Re-scan when tab is activated (in case icon got reset)
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const stored = await chrome.storage.local.get(`tab_${activeInfo.tabId}`);
  const data = stored[`tab_${activeInfo.tabId}`];
  if (data && data.state) {
    const iconState = ["safe", "suspicious", "phishing", "loading"].includes(data.state)
      ? data.state
      : "error";
    await setTabIcon(activeInfo.tabId, iconState);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "PHISHGUARD_SCAN_ACTIVE_TAB") return false;

  chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
    if (!tab?.id || !tab.url) {
      sendResponse({ ok: false, error: "No active browser tab is available." });
      return;
    }
    void scanURL(tab.url, tab.id, Boolean(message.force));
    sendResponse({ ok: true, tabId: tab.id, url: tab.url });
  }).catch(error => {
    sendResponse({ ok: false, error: error.message });
  });
  return true;
});

// ─── Auto-set demo token so popup skips login gate ────────────────────────
chrome.storage.local.get(["pg_token"], (stored) => {
  if (!stored.pg_token) {
    chrome.storage.local.set({ pg_token: "demo-token" });
  }
});
