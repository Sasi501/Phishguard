// PhishGuard popup displays backend results separately from any local pre-screen.

import { API_BASE_URL, BACKEND_BASE_URL } from './config.js';

const STATE_CONFIG = {
  safe: {
    emoji: "✓",
    label: "SYSTEM SAFE",
    sub: "The backend completed an analysis and returned a safe ensemble result.",
    dotClass: "safe",
  },
  suspicious: {
    emoji: "⚠",
    label: "REVIEW REQUIRED",
    sub: "The backend ensemble result requires review.",
    dotClass: "suspicious",
  },
  phishing: {
    emoji: "✕",
    label: "THREAT DETECTED",
    sub: "The backend ensemble result classified this URL as phishing.",
    dotClass: "phishing",
  },
  loading: {
    emoji: null,
    label: "ANALYZING...",
    sub: "Connecting to the PhishGuard backend...",
    dotClass: "loading",
  },
  offline: {
    emoji: "?",
    label: "SERVER OFFLINE",
    sub: "Unable to reach the PhishGuard analysis server.",
    dotClass: "error",
  },
  error: {
    emoji: "!",
    label: "ANALYSIS ERROR",
    sub: "The server responded, but analysis did not complete.",
    dotClass: "error",
  },
  unavailable: {
    emoji: "?",
    label: "ANALYSIS UNAVAILABLE",
    sub: "No final ensemble score was returned.",
    dotClass: "error",
  },
};

function truncate(str, n) {
  return str && str.length > n ? str.slice(0, n) + "…" : str;
}

function renderRedirectAnalysis(analysis) {
  const box = document.getElementById("redirect-box");
  if (!analysis || typeof analysis !== "object") {
    box.style.display = "none";
    return;
  }

  const state = analysis.resolution_state || "unavailable";
  const labels = {
    completed: "Destination resolved successfully",
    blocked: "Redirect resolution blocked",
    failed: "Redirect resolution failed",
    loop: "Redirect loop detected",
    limit_exceeded: "Redirect limit exceeded",
    unavailable: "Redirect resolution unavailable",
  };
  const tone = state === "completed"
    ? ""
    : ["blocked", "loop", "limit_exceeded"].includes(state) ? "warning" : "failed";
  const count = Number.isFinite(analysis.num_redirects) ? analysis.num_redirects : 0;
  const summary = document.getElementById("redirect-summary");
  summary.className = `redirect-summary ${tone}`;
  summary.textContent = count > 0
    ? `${count} redirect${count === 1 ? "" : "s"} detected — ${labels[state] || state.replaceAll("_", " ")}.`
    : (labels[state] || state.replaceAll("_", " "));

  const destination = document.getElementById("redirect-destination");
  destination.textContent = "";
  if (analysis.final_url) {
    const label = document.createElement("strong");
    label.textContent = "Final destination: ";
    destination.appendChild(label);
    destination.appendChild(document.createTextNode(truncate(analysis.final_url, 100)));
  }

  const flags = document.getElementById("redirect-flags");
  flags.innerHTML = "";
  const flagTexts = [];
  if (analysis.suspicious_redirects) flagTexts.push("Suspicious chain indicator");
  if (analysis.loop_detected) flagTexts.push("Loop detected");
  if (analysis.has_meta_refresh) flagTexts.push("Meta refresh");
  flagTexts.forEach(text => {
    const flag = document.createElement("span");
    flag.className = "redirect-flag";
    flag.textContent = text;
    flags.appendChild(flag);
  });
  box.style.display = "block";
}

function renderState(data) {
  const state = data?.state || "loading";
  const config = STATE_CONFIG[state] || STATE_CONFIG.unavailable;
  const backendStatus = data?.backend_status || "connecting";
  const indicator = document.getElementById("backend-indicator");
  const statusLabels = {
    connecting: "CONNECTING TO PHISHGUARD...",
    online: "● PHISHGUARD ONLINE",
    offline: "● PHISHGUARD OFFLINE",
    unknown: "● BACKEND STATUS UNKNOWN",
  };
  indicator.textContent = statusLabels[backendStatus] || statusLabels.unknown;
  indicator.className = `footer-brand ${backendStatus}`;

  const dot = document.getElementById("status-dot");
  dot.className = `status-dot ${config.dotClass}`;
  dot.innerHTML = state === "loading"
    ? `<div class="spinner"></div>`
    : `<span style="font-size:20px">${config.emoji}</span>`;

  const label = document.getElementById("status-label");
  label.className = `status-label ${config.dotClass}`;
  label.textContent = /timed out/i.test(data?.error || "")
    ? "BACKEND TIMEOUT"
    : config.label;

  let sub = config.sub;
  if (state === "loading" && data?.message) sub = data.message;
  if (state === "offline" && data?.error) sub = data.error;
  if (state === "error" && data?.error) sub = data.error;
  if (state === "unavailable" && data?.analysis_status === "partial") {
    sub = "Backend returned a partial analysis without a final ensemble score.";
  }
  if (data?.analysis_status === "partial" && ["safe", "suspicious", "phishing"].includes(state)) {
    sub = `Partial backend analysis. Final Ensemble Risk: ${state}. See individual engine status below.`;
  }
  document.getElementById("status-sub").textContent = sub;

  const scoreRow = document.getElementById("conf-row");
  const score = data?.ensemble_score_percent;
  if (backendStatus === "online" && typeof score === "number" && Number.isFinite(score)) {
    scoreRow.style.display = "block";
    document.getElementById("conf-val").textContent = `${score.toFixed(2)}%`;
    const fill = document.getElementById("conf-fill");
    fill.className = `conf-fill ${["safe", "suspicious", "phishing"].includes(state) ? state : "loading"}`;
    setTimeout(() => { fill.style.width = `${Math.max(0, Math.min(100, score))}%`; }, 50);
  } else {
    scoreRow.style.display = "none";
    document.getElementById("conf-fill").style.width = "0";
  }

  const reasonBox = document.getElementById("reason-box");
  const summary = data?.xai_summary || "";
  if (summary) {
    reasonBox.style.display = "block";
    reasonBox.replaceChildren();
    const heading = document.createElement("strong");
    heading.textContent = "XAI SUMMARY //";
    const text = document.createElement("p");
    text.textContent = summary;
    reasonBox.append(heading, text);
  } else if (data?.error) {
    reasonBox.style.display = "block";
    reasonBox.replaceChildren();
    const heading = document.createElement("strong");
    heading.textContent = "SERVER RESPONSE //";
    const text = document.createElement("p");
    text.textContent = data.error;
    reasonBox.append(heading, text);
  } else {
    reasonBox.style.display = "none";
    reasonBox.replaceChildren();
  }

  renderEngineSignals(data);
  renderRedirectAnalysis(data?.redirect_analysis);
  renderLocalPreScreen(data?.local_pre_screen);

  const urlBox = document.getElementById("url-box");
  if (data?.url) {
    urlBox.style.display = "flex";
    document.getElementById("url-text").textContent = truncate(data.url, 60);
  } else {
    urlBox.style.display = "none";
  }

  const retryButton = document.getElementById("retry-button");
  retryButton.style.display = state === "loading" ? "none" : "block";
  retryButton.disabled = state === "loading";
}

function renderEngineSignals(data) {
  const box = document.getElementById("signals-box");
  const list = document.getElementById("signals-list");
  list.replaceChildren();
  const signals = Array.isArray(data?.engine_signals) ? data.engine_signals : [];
  if (signals.length === 0) {
    box.style.display = "none";
    return;
  }

  const labels = {
    url_ml: "URL ML Signal · Original URL",
    nlp: "NLP Signal · Submitted Text",
    vision: "Vision Signal · Submitted Image",
    domain_intelligence: "Domain Risk Signal · Final URL",
    threat_intelligence: "Threat Intelligence Signal · Final URL",
  };
  signals.forEach(signal => {
    const row = document.createElement("div");
    row.className = "engine-signal";
    const title = document.createElement("strong");
    title.textContent = labels[signal.source] || signal.engine;
    const value = document.createElement("span");
    if (signal.source === "threat_intelligence" && signal.match_status) {
      value.textContent = signal.match_status;
    } else if (signal.score_type === "engine_signal" && Number.isFinite(signal.score)) {
      value.textContent = `${signal.score.toFixed(2)}%`;
    } else {
      value.textContent = String(signal.status || "unavailable").toUpperCase();
    }
    const detail = document.createElement("small");
    detail.textContent = signal.reason || `${signal.status || "unavailable"}${signal.url_scope ? ` · ${signal.url_scope.replaceAll("_", " ")}` : ""}`;
    row.append(title, value, detail);
    list.appendChild(row);
  });
  box.style.display = "block";
}

function renderLocalPreScreen(preScreen) {
  const box = document.getElementById("local-prescreen");
  if (!preScreen) {
    box.style.display = "none";
    return;
  }
  document.getElementById("local-prescreen-risk").textContent =
    `${String(preScreen.risk_level || "unavailable").toUpperCase()} · Local ONNX phishing signal: ${preScreen.phishing_probability_percent}%`;
  box.style.display = "block";
}

// Auth Handlers
async function handleAuth(action) {
  const username = document.getElementById("auth-username").value.trim();
  const password = document.getElementById("auth-password").value.trim();
  const errorDiv = document.getElementById("auth-error");
  
  if (!username || !password) {
    errorDiv.textContent = "Please enter username and password";
    return;
  }
  
  errorDiv.textContent = "Loading...";
  try {
    const res = await fetch(`${API_BASE_URL}/${action}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) {
      errorDiv.textContent = data.error || (data.non_field_errors && data.non_field_errors[0]) || "Authentication failed";
      return;
    }
    
    // Save token
    await chrome.storage.local.set({ pg_token: data.token });
    document.getElementById("auth-overlay").style.display = "none";
    // Trigger a rescan of current tab if needed or just re-init
    init();
  } catch (e) {
    errorDiv.textContent = "Network error. Is the server running?";
  }
}

document.getElementById("auth-login-btn").addEventListener("click", () => handleAuth("login"));
document.getElementById("auth-register-btn").addEventListener("click", () => handleAuth("register"));

let activeTabId = null;

async function requestActiveTabScan(force = false) {
  renderState({
    state: "loading",
    backend_status: "connecting",
    message: "Connecting to the PhishGuard analysis server...",
  });
  try {
    const response = await chrome.runtime.sendMessage({
      type: "PHISHGUARD_SCAN_ACTIVE_TAB",
      force,
    });
    if (!response?.ok) {
      renderState({
        state: "error",
        backend_status: "unknown",
        error: response?.error || "The extension could not start a scan.",
      });
      return;
    }
    activeTabId = response.tabId;
    const stored = await chrome.storage.local.get(`tab_${activeTabId}`);
    if (stored[`tab_${activeTabId}`]) renderState(stored[`tab_${activeTabId}`]);
  } catch (error) {
    renderState({
      state: "offline",
      backend_status: "offline",
      error: `Unable to contact the extension service worker: ${error.message}`,
      server_url: BACKEND_BASE_URL,
    });
  }
}

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "local" || activeTabId === null) return;
  const change = changes[`tab_${activeTabId}`];
  if (change?.newValue) renderState(change.newValue);
});

document.getElementById("retry-button").addEventListener("click", () => {
  requestActiveTabScan(true);
});

// Recheck backend health and analyze the current tab whenever the popup opens.
async function init() {
  try {
    const stored = await chrome.storage.local.get(["pg_token"]);
    if (!stored.pg_token) {
      document.getElementById("auth-overlay").style.display = "flex";
    } else {
      document.getElementById("auth-overlay").style.display = "none";
    }
    await requestActiveTabScan(false);
  } catch (err) {
    console.error("PhishGuard popup error:", err);
    renderState({
      state: "error",
      backend_status: "unknown",
      error: `Popup could not initialize: ${err.message}`,
    });
  }
}

init();
