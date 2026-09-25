// PhishGuard — Popup Script
// Reads scan result from chrome.storage.local and renders it

const STATE_CONFIG = {
  safe: {
    emoji: "✓",
    label: "SYSTEM SAFE",
    sub: "No anomalies detected.",
    dotClass: "safe",
  },
  suspicious: {
    emoji: "⚠",
    label: "WARNING",
    sub: "Anomalous signals detected.",
    dotClass: "suspicious",
  },
  phishing: {
    emoji: "✕",
    label: "THREAT BLOCKED",
    sub: "High-probability phishing vector.",
    dotClass: "phishing",
  },
  loading: {
    emoji: null,
    label: "ANALYZING...",
    sub: "Extracting features & querying AI...",
    dotClass: "loading",
  },
  error: {
    emoji: "?",
    label: "SYSTEM OFFLINE",
    sub: "Connection to core server failed.",
    dotClass: "error",
  },
};

function escapeHTML(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

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
  const config = STATE_CONFIG[state] || STATE_CONFIG.loading;

  // Status dot
  const dot = document.getElementById("status-dot");
  dot.className = `status-dot ${config.dotClass}`;
  if (state === "loading") {
    dot.innerHTML = `<div class="spinner"></div>`;
  } else {
    dot.innerHTML = `<span style="font-size:20px">${config.emoji}</span>`;
  }

  // Label
  const label = document.getElementById("status-label");
  label.className = `status-label ${config.dotClass}`;
  label.textContent = config.label;

  // Sub label
  document.getElementById("status-sub").textContent = config.sub;

  if (!data || state === "loading" || state === "error") {
    renderRedirectAnalysis(null);
    return;
  }

  renderRedirectAnalysis(data.redirect_analysis);

  // Confidence bar
  const confPct = Math.round((data.confidence || 0) * 100);
  document.getElementById("conf-row").style.display = "block";
  document.getElementById("conf-val").textContent = `${confPct}%`;
  const fill = document.getElementById("conf-fill");
  fill.className = `conf-fill ${state}`;
  // Small delay so CSS transition fires
  setTimeout(() => { fill.style.width = `${confPct}%`; }, 50);

  // Reason
  if (data.reason) {
    const box = document.getElementById("reason-box");
    box.style.display = "block";
    box.textContent = data.reason;
  }

  // Signals
  if (data.signals && data.signals.length > 0) {
    const box = document.getElementById("signals-box");
    box.style.display = "block";
    const list = document.getElementById("signals-list");
    list.innerHTML = data.signals
      .map(s => `<span class="signal-tag ${state === 'phishing' ? 'phishing' : ''}">${escapeHTML(s)}</span>`)
      .join("");
  }

  // URL preview
  if (data.url) {
    document.getElementById("url-box").style.display = "flex";
    document.getElementById("url-text").textContent = truncate(data.url, 60);
  }

  // Cached badge
  if (data.cached) {
    document.getElementById("cached-badge").style.display = "inline-block";
  }
}

// Auth Handlers
const API_BASE = "http://127.0.0.1:8000/api";

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
    const res = await fetch(`${API_BASE}/${action}/`, {
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

// Main: get active tab → read storage → render
async function init() {
  try {
    const stored = await chrome.storage.local.get(["pg_token"]);
    if (!stored.pg_token) {
      document.getElementById("auth-overlay").style.display = "flex";
      return;
    } else {
      document.getElementById("auth-overlay").style.display = "none";
    }

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return renderState(null);

    const key = `tab_${tab.id}`;
    const tabStored = await chrome.storage.local.get(key);
    const data = tabStored[key];

    renderState(data || null);
  } catch (err) {
    console.error("PhishGuard popup error:", err);
    renderState({ state: "error" });
  }
}

init();
