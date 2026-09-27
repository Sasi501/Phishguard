// PhishGuard — Content Script
// Injects a world-class, premium security warning overlay for confirmed phishing sites.
// Fully self-contained with zero page-style leakage.

(function () {
  "use strict";

  let overlayInjected = false;

  function injectPhishingOverlay({ reason, signals, ensemble_score_percent, url }) {
    if (overlayInjected) return;
    if (document.getElementById("phishguard-root")) return;
    overlayInjected = true;

    // Freeze the underlying page
    document.documentElement.style.overflow = "hidden";
    if (document.body) document.body.style.overflow = "hidden";

    const targetUrl = url || window.location.href;
    let urlHost = "";
    try {
      urlHost = new URL(targetUrl).hostname;
    } catch {
      urlHost = targetUrl;
    }

    const hasScore = typeof ensemble_score_percent === "number" && Number.isFinite(ensemble_score_percent);
    const scoreVal = hasScore ? Math.max(0, Math.min(100, Math.round(ensemble_score_percent))) : 99;
    
    let riskLabel = "CRITICAL THREAT";
    if (scoreVal < 60) {
      riskLabel = "SUSPICIOUS";
    } else if (scoreVal < 80) {
      riskLabel = "HIGH RISK";
    }

    const cleanSignals = Array.isArray(signals) ? signals : [];
    const signalsHtml = cleanSignals.length > 0
      ? cleanSignals.map(s => `
          <div class="pg-signal-chip">
            <svg class="pg-chip-icon" viewBox="0 0 16 16" fill="currentColor">
              <path fill-rule="evenodd" d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
            </svg>
            <span>${escapeHTML(s)}</span>
          </div>
        `).join("")
      : `
        <div class="pg-signal-chip">
          <svg class="pg-chip-icon" viewBox="0 0 16 16" fill="currentColor">
            <path fill-rule="evenodd" d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
          </svg>
          <span>Multi-layer AI Model consensus flagged deceptive payload</span>
        </div>
      `;

    const parsedReason = reason || "The PhishGuard neural ensemble detected high-confidence indicators of credential harvesting and identity deception on this domain.";

    // Root wrapper
    const root = document.createElement("div");
    root.id = "phishguard-root";

    root.innerHTML = `
      <div class="pg-wrapper">
        <!-- Ambient Background Glows -->
        <div class="pg-ambient-glow pg-glow-top"></div>
        <div class="pg-ambient-glow pg-glow-bottom"></div>
        <div class="pg-grid-mesh"></div>

        <!-- Main Content Container -->
        <div class="pg-card">
          
          <!-- Brand Badge Row -->
          <div class="pg-brand-row">
            <div class="pg-badge">
              <span class="pg-badge-pulse"></span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
              <span>PhishGuard Neural Shield</span>
            </div>
            <div class="pg-threat-tag">
              <span class="pg-threat-dot"></span>
              ${riskLabel}
            </div>
          </div>

          <!-- Hero Icon & Title Area -->
          <div class="pg-hero">
            <div class="pg-icon-wrapper">
              <div class="pg-icon-halo"></div>
              <svg class="pg-hero-shield" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="pgShieldMain" x1="12" y1="6" x2="60" y2="66" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stop-color="#ef4444"/>
                    <stop offset="60%" stop-color="#b91c1c"/>
                    <stop offset="100%" stop-color="#7f1d1d"/>
                  </linearGradient>
                  <linearGradient id="pgShieldRim" x1="12" y1="6" x2="60" y2="66" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stop-color="#fca5a5"/>
                    <stop offset="50%" stop-color="#ef4444" stop-opacity="0.6"/>
                    <stop offset="100%" stop-color="#991b1b"/>
                  </linearGradient>
                </defs>
                <!-- Shield Base -->
                <path d="M36 6L12 18V36C12 51.5 22.3 64.2 36 68C49.7 64.2 60 51.5 60 36V18L36 6Z" fill="url(#pgShieldMain)"/>
                <!-- Shield Rim Inner Stroke -->
                <path d="M36 8.5L14.5 19.3V36C14.5 49.8 23.7 61.2 36 64.9C48.3 61.2 57.5 49.8 57.5 36V19.3L36 8.5Z" fill="none" stroke="url(#pgShieldRim)" stroke-width="2"/>
                <!-- Exclamation Mark -->
                <path d="M36 24V40" stroke="#ffffff" stroke-width="4.5" stroke-linecap="round"/>
                <circle cx="36" cy="48.5" r="3" fill="#ffffff"/>
              </svg>
            </div>

            <h1 class="pg-heading">Deceptive Website Blocked</h1>
            <p class="pg-subheading">
              PhishGuard detected that <span class="pg-url-highlight">${escapeHTML(urlHost)}</span> is impersonating a legitimate service to steal passwords, financial details, or personal data.
            </p>
          </div>

          <!-- URL Bar Component -->
          <div class="pg-url-card">
            <div class="pg-url-left">
              <svg class="pg-lock-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clip-rule="evenodd"/>
              </svg>
              <div class="pg-url-text">
                <span class="pg-url-label">Suspect Destination</span>
                <span class="pg-url-val" title="${escapeHTML(targetUrl)}">${escapeHTML(truncate(targetUrl, 75))}</span>
              </div>
            </div>
            <div class="pg-score-pill">
              <span class="pg-score-num">${scoreVal}%</span>
              <span class="pg-score-text">Risk Score</span>
            </div>
          </div>

          <!-- Risk Progress Bar -->
          <div class="pg-meter-wrap">
            <div class="pg-meter-bar">
              <div class="pg-meter-fill" style="width: ${scoreVal}%;"></div>
            </div>
          </div>

          <!-- Analysis Insight Panel -->
          <div class="pg-insight-box">
            <div class="pg-insight-head">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
              <span>AI Ensemble Threat Analysis</span>
            </div>
            <p class="pg-insight-text">${escapeHTML(parsedReason)}</p>

            <div class="pg-signals-grid">
              ${signalsHtml}
            </div>
          </div>

          <!-- Primary Actions -->
          <div class="pg-actions">
            <button class="pg-btn-primary" id="pg-btn-safe">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="19" y1="12" x2="5" y2="12"/>
                <polyline points="12 19 5 12 12 5"/>
              </svg>
              <span>Return to Safety</span>
            </button>

            <div class="pg-secondary-row">
              <button class="pg-btn-link" id="pg-btn-override">
                Advanced: Proceed to dangerous site (unsafe)
              </button>
            </div>
          </div>

          <!-- Footer Attribution -->
          <div class="pg-card-footer">
            <div class="pg-footer-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
              <span>Zero-Trust AI Guard Active</span>
            </div>
            <div class="pg-footer-dot">·</div>
            <div class="pg-footer-item">
              <span>PhishGuard v2.0 Enterprise</span>
            </div>
          </div>

        </div>
      </div>
    `;

    // ── Spacious, Large-Format Ultra-Refined Styles ──────────────────────────
    const style = document.createElement("style");
    style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

      #phishguard-root {
        all: initial;
        position: fixed !important;
        inset: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        z-index: 2147483647 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        background-color: #050811 !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
        color: #f1f5f9 !important;
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
      }

      #phishguard-root *,
      #phishguard-root *::before,
      #phishguard-root *::after {
        box-sizing: border-box !important;
        margin: 0;
        padding: 0;
      }

      .pg-wrapper {
        min-height: 100vh;
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 48px 24px;
        position: relative;
        background: 
          radial-gradient(1200px 700px at 50% -5%, rgba(239, 68, 68, 0.22) 0%, transparent 65%),
          radial-gradient(1000px 600px at 50% 105%, rgba(30, 41, 59, 0.6) 0%, transparent 70%),
          #050811;
      }

      /* Ambient decorative lights */
      .pg-ambient-glow {
        position: absolute;
        border-radius: 50%;
        filter: blur(120px);
        pointer-events: none;
        z-index: 0;
      }
      .pg-glow-top {
        width: 650px;
        height: 380px;
        top: -60px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(220, 38, 38, 0.28);
      }
      .pg-glow-bottom {
        width: 750px;
        height: 320px;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(99, 102, 241, 0.14);
      }

      /* Grid mesh overlay */
      .pg-grid-mesh {
        position: absolute;
        inset: 0;
        background-image: 
          linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
        background-size: 54px 54px;
        mask-image: radial-gradient(ellipse at 50% 45%, black 45%, transparent 85%);
        -webkit-mask-image: radial-gradient(ellipse at 50% 45%, black 45%, transparent 85%);
        pointer-events: none;
        z-index: 0;
      }

      /* Large Sized Main Card */
      .pg-card {
        position: relative;
        z-index: 10;
        width: 100%;
        max-width: 820px;
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.96) 0%, rgba(10, 16, 30, 0.99) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 32px;
        padding: 48px 52px 38px;
        box-shadow: 
          0 0 0 1px rgba(255, 255, 255, 0.06) inset,
          0 35px 80px -20px rgba(0, 0, 0, 0.85),
          0 0 100px rgba(239, 68, 68, 0.16);
        backdrop-filter: blur(28px);
        -webkit-backdrop-filter: blur(28px);
        animation: pgCardEnter 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      }

      @keyframes pgCardEnter {
        from {
          opacity: 0;
          transform: translateY(28px) scale(0.96);
        }
        to {
          opacity: 1;
          transform: translateY(0) scale(1);
        }
      }

      /* Top Brand Row */
      .pg-brand-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 28px;
      }

      .pg-badge {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        background: rgba(255, 255, 255, 0.07);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 8px 18px;
        border-radius: 100px;
        font-size: 13.5px;
        font-weight: 600;
        color: #cbd5e1;
        letter-spacing: 0.02em;
      }

      .pg-badge-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #ef4444;
        box-shadow: 0 0 10px #ef4444;
        animation: pgDotPulse 1.8s infinite;
      }

      @keyframes pgDotPulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
      }

      .pg-threat-tag {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(239, 68, 68, 0.16);
        border: 1px solid rgba(239, 68, 68, 0.4);
        color: #fca5a5;
        font-size: 12.5px;
        font-weight: 800;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        padding: 7px 16px;
        border-radius: 100px;
      }

      .pg-threat-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #ef4444;
      }

      /* Hero Section */
      .pg-hero {
        text-align: center;
        margin-bottom: 32px;
      }

      .pg-icon-wrapper {
        position: relative;
        width: 96px;
        height: 96px;
        margin: 0 auto 22px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .pg-icon-halo {
        position: absolute;
        inset: -10px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(239, 68, 68, 0.45) 0%, transparent 70%);
        animation: pgHaloGlow 2.5s ease-in-out infinite;
      }

      @keyframes pgHaloGlow {
        0%, 100% { transform: scale(0.95); opacity: 0.65; }
        50% { transform: scale(1.18); opacity: 1; }
      }

      .pg-hero-shield {
        width: 86px;
        height: 86px;
        position: relative;
        z-index: 2;
        filter: drop-shadow(0 12px 24px rgba(185, 28, 28, 0.45));
      }

      .pg-heading {
        font-size: 34px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.025em;
        line-height: 1.22;
        margin-bottom: 12px;
      }

      .pg-subheading {
        font-size: 16px;
        color: #94a3b8;
        line-height: 1.65;
        max-width: 640px;
        margin: 0 auto;
      }

      .pg-url-highlight {
        color: #f87171;
        font-weight: 700;
        word-break: break-all;
      }

      /* URL Bar Card */
      .pg-url-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(0, 0, 0, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 16px 22px;
        margin-bottom: 14px;
        gap: 20px;
      }

      .pg-url-left {
        display: flex;
        align-items: center;
        gap: 14px;
        min-width: 0;
      }

      .pg-lock-icon {
        width: 22px;
        height: 22px;
        color: #ef4444;
        flex-shrink: 0;
      }

      .pg-url-text {
        display: flex;
        flex-direction: column;
        min-width: 0;
      }

      .pg-url-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: #64748b;
        margin-bottom: 3px;
      }

      .pg-url-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 14px;
        font-weight: 500;
        color: #e2e8f0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .pg-score-pill {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        flex-shrink: 0;
      }

      .pg-score-num {
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px;
        font-weight: 800;
        color: #ef4444;
        line-height: 1;
      }

      .pg-score-text {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        color: #64748b;
        letter-spacing: 0.06em;
        margin-top: 4px;
      }

      /* Risk Meter */
      .pg-meter-wrap {
        margin-bottom: 26px;
        padding: 0 4px;
      }

      .pg-meter-bar {
        width: 100%;
        height: 8px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        overflow: hidden;
        position: relative;
      }

      .pg-meter-fill {
        height: 100%;
        background: linear-gradient(90deg, #f59e0b 0%, #ef4444 55%, #dc2626 100%);
        border-radius: 12px;
        box-shadow: 0 0 14px rgba(239, 68, 68, 0.85);
        transition: width 1s cubic-bezier(0.16, 1, 0.3, 1);
      }

      /* AI Insight Section */
      .pg-insight-box {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 22px 26px;
        margin-bottom: 32px;
      }

      .pg-insight-head {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13.5px;
        font-weight: 700;
        color: #93c5fd;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 10px;
      }

      .pg-insight-text {
        font-size: 14.5px;
        color: #94a3b8;
        line-height: 1.7;
        margin-bottom: 16px;
      }

      .pg-signals-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }

      .pg-signal-chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-radius: 10px;
        padding: 7px 14px;
        font-size: 12.5px;
        font-weight: 600;
        color: #fca5a5;
        font-family: 'JetBrains Mono', monospace;
      }

      .pg-chip-icon {
        width: 14px;
        height: 14px;
        flex-shrink: 0;
        color: #ef4444;
      }

      /* Action Buttons */
      .pg-actions {
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin-bottom: 28px;
      }

      .pg-btn-primary {
        all: unset;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        width: 100%;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: #ffffff;
        font-size: 16.5px;
        font-weight: 700;
        padding: 18px 32px;
        border-radius: 16px;
        cursor: pointer;
        box-shadow: 0 6px 24px rgba(16, 185, 129, 0.38);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
      }

      .pg-btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 32px rgba(16, 185, 129, 0.5);
        background: linear-gradient(135deg, #34d399 0%, #059669 100%);
      }

      .pg-btn-primary:active {
        transform: translateY(0);
      }

      .pg-secondary-row {
        text-align: center;
      }

      .pg-btn-link {
        all: unset;
        font-size: 13.5px;
        font-weight: 500;
        color: #64748b;
        cursor: pointer;
        padding: 8px 16px;
        border-radius: 8px;
        transition: color 0.2s, background 0.2s;
      }

      .pg-btn-link:hover {
        color: #ef4444;
        text-decoration: underline;
      }

      /* Footer Area */
      .pg-card-footer {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding-top: 22px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        color: #475569;
        font-size: 12px;
        font-weight: 500;
      }

      .pg-footer-item {
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .pg-footer-dot {
        color: #334155;
      }

      /* Responsive Adjustments */
      @media (max-width: 680px) {
        .pg-card {
          padding: 32px 24px 28px;
          border-radius: 24px;
        }
        .pg-heading {
          font-size: 26px;
        }
        .pg-subheading {
          font-size: 14px;
        }
        .pg-url-card {
          flex-direction: column;
          align-items: flex-start;
          gap: 12px;
        }
        .pg-score-pill {
          align-items: flex-start;
        }
      }
    `;

    document.documentElement.appendChild(style);
    document.documentElement.appendChild(root);

    // Event Bindings
    const btnSafe = document.getElementById("pg-btn-safe");
    if (btnSafe) {
      btnSafe.addEventListener("click", () => {
        if (window.history.length > 1) {
          window.history.back();
        } else {
          window.location.href = "https://www.google.com";
        }
        setTimeout(() => {
          window.location.href = "https://www.google.com";
        }, 300);
      });
    }

    const btnOverride = document.getElementById("pg-btn-override");
    if (btnOverride) {
      btnOverride.addEventListener("click", () => {
        const confirmed = window.confirm(
          "⚠️ SECURITY OVERRIDE WARNING\n\n" +
          "You are about to bypass PhishGuard protection and proceed to a confirmed phishing target.\n\n" +
          "This website may immediately capture passwords, credit card numbers, or session tokens.\n\n" +
          "Are you absolutely certain you want to proceed?"
        );

        if (confirmed) {
          root.remove();
          style.remove();
          document.documentElement.style.overflow = "";
          if (document.body) document.body.style.overflow = "";
          overlayInjected = false;
        }
      });
    }
  }

  function escapeHTML(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function truncate(str, n) {
    if (!str) return "";
    return str.length > n ? str.slice(0, n) + "…" : str;
  }

  // Listen for alert messages from background worker
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type === "PHISHING_ALERT") {
      injectPhishingOverlay(message);
      sendResponse({ ok: true });
    }
  });

})();
