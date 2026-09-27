// PhishGuard — Content Script
// Injects a full-page blocking warning overlay for confirmed phishing sites
// Styled with the deep dark hacker aesthetic (glassmorphism, neon accents)

(function () {
  "use strict";

  let overlayInjected = false;

  function injectPhishingOverlay({ reason, signals, ensemble_score_percent, url }) {
    if (overlayInjected) return;
    overlayInjected = true;

    // Freeze the page
    document.documentElement.style.overflow = "hidden";

    const overlay = document.createElement("div");
    overlay.id = "phishguard-overlay";

    const hasEnsembleScore = Number.isFinite(ensemble_score_percent);
    const ensembleScore = hasEnsembleScore
      ? Math.max(0, Math.min(100, Math.round(ensemble_score_percent)))
      : null;
    const signalList = (signals || [])
      .map(s => `<li>${escapeHTML(s)}</li>`)
      .join("");

    overlay.innerHTML = `
      <div class="pg-backdrop"></div>
      <div class="pg-modal">
        <div class="pg-header">
          <div class="pg-shield-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L3 6V12C3 17.25 7.08 22.1 12 23C16.92 22.1 21 17.25 21 12V6L12 2Z" fill="rgba(255,0,60,0.15)" stroke="#ff003c" stroke-width="1.5"/>
              <path d="M12 8V13" stroke="#ff003c" stroke-width="2.5" stroke-linecap="round"/>
              <circle cx="12" cy="16" r="1.2" fill="#ff003c"/>
            </svg>
          </div>
          <h1 class="pg-title">THREAT DETECTED</h1>
          <p class="pg-subtitle">Backend ensemble analysis classified this page as phishing</p>
        </div>

        <div class="pg-confidence-bar">
          <div class="pg-confidence-label">
            <span>FINAL ENSEMBLE RISK SCORE</span>
            <span class="pg-confidence-value">${hasEnsembleScore ? `${ensembleScore}%` : "Unavailable"}</span>
          </div>
          ${hasEnsembleScore ? `
          <div class="pg-bar-track">
            <div class="pg-bar-fill" style="width: ${ensembleScore}%"></div>
          </div>` : ""}
        </div>

        <div class="pg-reason">
          <div class="pg-reason-header">AI ANALYSIS //</div>
          <p>${escapeHTML(reason || "The backend ensemble classified this URL as phishing.")}</p>
        </div>

        ${signalList ? `
        <div class="pg-signals">
          <p class="pg-signals-title">EXTRACTED SIGNALS</p>
          <ul>${signalList}</ul>
        </div>` : ""}

        <div class="pg-url-preview">
          <span class="pg-url-label">TARGET:</span>
          <code>${escapeHTML(truncate(url || window.location.href, 80))}</code>
        </div>

        <div class="pg-actions">
          <button class="pg-btn pg-btn-safe" id="pg-go-back">
            ← Return to Safety
          </button>
          <button class="pg-btn pg-btn-danger" id="pg-proceed">
            Override (Unsafe)
          </button>
        </div>

        <p class="pg-footer">PHISHGUARD · AI-DRIVEN PROTECTION · v2.0</p>
      </div>
    `;

    // Styles — Deep Dark Hacker Aesthetic
    const style = document.createElement("style");
    style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

      #phishguard-overlay * { box-sizing: border-box; margin: 0; padding: 0; }
      #phishguard-overlay {
        position: fixed; inset: 0; z-index: 2147483647;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }

      .pg-backdrop {
        position: absolute; inset: 0;
        background: rgba(3, 3, 5, 0.95);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
      }

      /* Scanline effect on backdrop */
      .pg-backdrop::after {
        content: '';
        position: absolute; inset: 0;
        background: repeating-linear-gradient(
          0deg,
          transparent,
          transparent 2px,
          rgba(255, 0, 60, 0.03) 2px,
          rgba(255, 0, 60, 0.03) 4px
        );
        pointer-events: none;
        animation: pg-scanline 8s linear infinite;
      }

      @keyframes pg-scanline {
        0%   { transform: translateY(0); }
        100% { transform: translateY(100px); }
      }

      .pg-modal {
        position: relative; z-index: 1;
        background: rgba(5, 5, 8, 0.85);
        border: 1px solid rgba(255, 0, 60, 0.4);
        border-radius: 16px;
        padding: 36px;
        max-width: 540px; width: 90%;
        box-shadow:
          0 0 80px rgba(255, 0, 60, 0.15),
          0 0 0 1px rgba(255, 255, 255, 0.05) inset,
          0 24px 80px rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        animation: pg-slide-in 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      }

      @keyframes pg-slide-in {
        from { transform: translateY(-30px) scale(0.92); opacity: 0; }
        to   { transform: translateY(0) scale(1); opacity: 1; }
      }

      .pg-header { text-align: center; margin-bottom: 28px; }

      .pg-shield-icon {
        width: 72px; height: 72px;
        margin: 0 auto 20px;
        animation: pg-pulse 2s ease-in-out infinite;
      }

      @keyframes pg-pulse {
        0%, 100% { filter: drop-shadow(0 0 10px rgba(255,0,60,0.5)); }
        50%      { filter: drop-shadow(0 0 25px rgba(255,0,60,0.9)); }
      }

      .pg-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 24px;
        font-weight: 900;
        color: #ff003c;
        letter-spacing: 0.15em;
        text-shadow: 0 0 15px rgba(255, 0, 60, 0.5);
      }

      .pg-subtitle {
        font-size: 13px;
        color: #8b949e;
        margin-top: 8px;
        letter-spacing: 0.05em;
      }

      .pg-confidence-bar { margin-bottom: 24px; }

      .pg-confidence-label {
        display: flex; justify-content: space-between;
        font-family: 'Orbitron', sans-serif;
        font-size: 10px;
        color: #8b949e;
        margin-bottom: 8px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
      }

      .pg-confidence-value {
        font-family: 'JetBrains Mono', monospace;
        color: #ff003c;
        font-weight: 700;
        font-size: 14px;
        text-shadow: 0 0 8px rgba(255,0,60,0.4);
      }

      .pg-bar-track {
        height: 8px;
        background: rgba(0, 0, 0, 0.6);
        border-radius: 99px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.08);
      }

      .pg-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #ffaa00, #ff003c);
        border-radius: 99px;
        box-shadow: 0 0 12px rgba(255, 0, 60, 0.5);
        transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
      }

      .pg-reason {
        background: rgba(255, 0, 60, 0.05);
        border: 1px solid rgba(255, 0, 60, 0.2);
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 20px;
      }

      .pg-reason-header {
        font-family: 'Orbitron', sans-serif;
        font-size: 10px;
        color: #00e5ff;
        letter-spacing: 0.1em;
        margin-bottom: 10px;
        text-shadow: 0 0 6px rgba(0, 229, 255, 0.3);
      }

      .pg-reason p {
        font-size: 14px;
        color: #d1d5db;
        line-height: 1.7;
      }

      .pg-signals { margin-bottom: 20px; }

      .pg-signals-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 10px;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 10px;
      }

      .pg-signals ul { list-style: none; display: flex; flex-wrap: wrap; gap: 8px; }

      .pg-signals li {
        font-family: 'JetBrains Mono', monospace;
        background: rgba(255, 0, 60, 0.08);
        border: 1px solid rgba(255, 0, 60, 0.3);
        color: #ff003c;
        font-size: 11px;
        padding: 4px 12px;
        border-radius: 4px;
      }

      .pg-url-preview {
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 28px;
        display: flex;
        align-items: center;
        gap: 10px;
        overflow: hidden;
      }

      .pg-url-label {
        font-family: 'Orbitron', sans-serif;
        font-size: 9px;
        color: #8b949e;
        letter-spacing: 0.1em;
        flex-shrink: 0;
      }

      .pg-url-preview code {
        font-size: 11px;
        color: #ff003c;
        word-break: break-all;
        font-family: 'JetBrains Mono', monospace;
      }

      .pg-actions { display: flex; gap: 12px; margin-bottom: 20px; }

      .pg-btn {
        flex: 1;
        padding: 14px 20px;
        border-radius: 8px;
        font-family: 'Orbitron', sans-serif;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.05em;
        cursor: pointer;
        border: none;
        transition: all 0.3s ease;
        text-transform: uppercase;
      }

      .pg-btn-safe {
        background: rgba(57, 255, 20, 0.1);
        color: #39ff14;
        border: 1px solid #39ff14;
      }

      .pg-btn-safe:hover {
        background: #39ff14;
        color: #000;
        box-shadow: 0 0 20px rgba(57, 255, 20, 0.4);
        transform: translateY(-1px);
      }

      .pg-btn-danger {
        background: transparent;
        color: #8b949e;
        border: 1px solid rgba(255, 255, 255, 0.1);
        font-size: 10px;
      }

      .pg-btn-danger:hover {
        color: #ff003c;
        border-color: rgba(255, 0, 60, 0.5);
      }

      .pg-footer {
        text-align: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 9px;
        color: #374151;
        letter-spacing: 0.15em;
        text-transform: uppercase;
      }
    `;

    document.documentElement.appendChild(style);
    document.documentElement.appendChild(overlay);

    // Button handlers
    document.getElementById("pg-go-back").addEventListener("click", () => {
      window.history.back();
      // Fallback if no history
      setTimeout(() => { window.location.href = "chrome://newtab"; }, 300);
    });

    document.getElementById("pg-proceed").addEventListener("click", () => {
      if (confirm("⚠️ CRITICAL WARNING\n\nThis site has been classified as a phishing vector by PhishGuard AI.\n\nProceeding could expose your credentials and personal data.\n\nAre you absolutely sure?")) {
        overlay.remove();
        style.remove();
        document.documentElement.style.overflow = "";
        overlayInjected = false;
      }
    });
  }

  function escapeHTML(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function truncate(str, n) {
    return str.length > n ? str.slice(0, n) + "…" : str;
  }

  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "PHISHING_ALERT") {
      injectPhishingOverlay(message);
      sendResponse({ ok: true });
    }
  });

})();
