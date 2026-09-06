# Implementation Plan: PhishGuard UI Overhaul

## Overview

Transforms the existing single-file React app into a production-grade cybersecurity dashboard with a cyberpunk/glassmorphism aesthetic. The plan follows the component dependency order: foundation → shared types and hook → leaf components with no inter-component dependencies → composite components → root wiring → CI enforcement.

All implementation is in TypeScript + React 19 + Vite inside `frontend/`. Plain CSS co-located with each component; no CSS-in-JS or CSS Modules. Animations use CSS keyframes (transform + opacity) or minimal RAF loops (ThreatMeter arc, ParticleBackground canvas). Spec files are at `.kiro/specs/phishguard-ui-overhaul/`.

---

## Tasks

- [x] 1. Foundation — theme tokens, shared types, global CSS, font loading, and Vite config
  - [x] 1.1 Create `src/theme.ts` with all color, font, duration, and size constants
    - Export `COLORS`, `FONTS`, `DURATIONS`, `SIZES`, and `RISK_COLORS` exactly as specified in the design's "Theme Tokens" section
    - Use `as const` for all objects so downstream code gets literal types
    - _Requirements: 12.5_

  - [x] 1.2 Create `src/types/api.ts` with all shared TypeScript interfaces
    - Define `RiskLevel`, `AnalyzeRequest`, `AnalyzeResponse`, `ScanEntry`, and `UseAnalysisState` exactly as specified in the design's "API Types" section
    - `ScanEntry.id` uses `crypto.randomUUID()`; `timestamp` is `Date`
    - _Requirements: 12.4_

  - [x] 1.3 Rewrite `src/index.css` with CSS custom properties, global reset, glassmorphism utility class, and all shared keyframe animations
    - Declare all `--color-*`, `--glass-*`, `--font-*`, `--dur-*`, and `--nav-height` custom properties on `:root`
    - Add `.glass-card` utility class with `background`, `backdrop-filter`, `border`, `box-shadow`, and `border-radius: 16px`
    - Add global `*:focus-visible` rule: `outline: 2px solid var(--color-neon-cyan); outline-offset: 2px`
    - Add `@media (prefers-reduced-motion: reduce)` block that sets `animation-duration: 0.01ms !important`, `animation-iteration-count: 1 !important`, `transition-duration: 0.01ms !important` on `*, *::before, *::after`
    - Define keyframes: `pg-pulse`, `spin`, `scan-sweep`, `badge-pulse`, `fade-up`, `banner-enter`, and `bar-fill`
    - Set `body` background to `var(--color-base-bg)` and `font-family` to `var(--font-body)`; set `color` to `var(--color-text)`
    - _Requirements: 1.1, 1.4, 10.2, 10.4, 11.3_

  - [x] 1.4 Update `index.html` to add Google Fonts and correct page title
    - Add `<link rel="preconnect" href="https://fonts.googleapis.com">` and `<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>`
    - Add the Google Fonts stylesheet `<link>` for Inter (weights 400, 500, 600) and Orbitron (weights 700, 900) with `display=swap` in the URL
    - Update `<title>` to `PhishGuard — AI Phishing Detection`
    - _Requirements: 1.7, 11.3_

  - [x] 1.5 Update `vite.config.ts` to enforce the 150 KB bundle cap
    - Set `build.chunkSizeWarningLimit` to `200` (kB uncompressed, ~150 KB gzipped)
    - Add `build.rollupOptions.output.manualChunks` to split `react` and `react-dom` into a `vendor` chunk
    - _Requirements: 11.5, 11.6_

- [x] 2. `useAnalysis` custom hook
  - [x] 2.1 Create `src/hooks/useAnalysis.ts` implementing the API state machine
    - Implement the `idle → loading → (success | error)` state transitions using a single `useState<{loading, result, error}>` object
    - `analyze(req)` builds `FormData`, attaches an `AbortController` timeout of 10 000 ms, POSTs to `/api/analyze-ensemble/`, clamps `ensemble_score_percent` to [0, 100] on success
    - On `AbortError` or `TypeError` (fetch failed), set the fallback network-error message from Req 8.2
    - On non-2xx response, extract `detail` field from JSON body or fall back to `"Server error {status}"`
    - Expose `reset()` to return all fields to initial values
    - _Requirements: 8.2, 8.3, 12.3_

  - [ ]* 2.2 Write property-based tests for `useAnalysis` state invariants
    - **Property 1: After `analyze()` resolves, exactly one of `result` or `error` is non-null and `loading` is false**
    - **Validates: Requirements 8.2, 12.3**
    - Use `fast-check` (or Hypothesis equivalent); generate arbitrary mock fetch responses (2xx with valid JSON, 4xx, 5xx, network abort) and assert the XOR invariant holds in all cases

- [x] 3. `ParticleBackground` component
  - [x] 3.1 Create `src/components/ParticleBackground.tsx` with canvas particle system
    - Full-screen `<canvas>` positioned `fixed`, `z-index: -1`, covering 100 vw × 100 vh with pointer-events disabled
    - Implement `initParticles(W, H)`: particle count = `Math.floor((W * H) / 12000)`, each with random position, velocity derived from a random angle × random speed in [0.2, 1.0], radius in [1, 2] px, alpha in [0.04, 0.08]
    - Implement `drawFrame(ctx, particles, W, H)`: clear canvas, advance each particle by its velocity, wrap edges (x < 0 → x = W, etc.), draw with `rgba(0, 229, 255, alpha)`
    - Start RAF loop in `useEffect`; store RAF id in `useRef`; cancel on unmount
    - Attach `visibilitychange` listener: `document.hidden` → `cancelAnimationFrame`; becoming visible → restart loop
    - Attach `ResizeObserver` on canvas container: on size change, reset canvas dimensions and reinitialise particles
    - When `window.matchMedia('(prefers-reduced-motion: reduce)').matches` is true, draw one static frame only — no RAF loop
    - _Requirements: 1.2, 10.4, 11.2_

- [x] 4. `NavigationBar` component
  - [x] 4.1 Create `src/components/NavigationBar.tsx` and `NavigationBar.css`
    - Render a `<nav role="navigation" aria-label="Main navigation">` fixed at top, `height: var(--nav-height)` (64 px), full viewport width, `z-index` above content
    - Apply `.glass-card` styles to nav background; add `backdrop-filter: blur(12px)`
    - Display "PHISHGUARD" in `var(--font-heading)`, `var(--color-neon-cyan)`, with `text-shadow: 0 0 12px var(--color-neon-cyan)`
    - Display "SYSTEM ONLINE" status indicator with a green dot; apply `animation: pg-pulse var(--dur-nav-pulse) ease-in-out infinite` (keyframe defined in `index.css`) — animates `opacity` and `transform: scale`
    - On viewports ≤ 768 px, hide all nav items except logo and status indicator (CSS `@media` query)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. `ThreatBadge` component
  - [x] 5.1 Create `src/components/ThreatBadge.tsx` and `ThreatBadge.css`
    - Accept `riskLevel: RiskLevel` and `size?: 'normal' | 'small'` props
    - Render a pill (`border-radius: 9999px`) with `RISK_COLORS[riskLevel]` as background and `box-shadow: 0 0 4px 4px {color}99` (60% opacity)
    - Display uppercase `riskLevel` text using `var(--font-heading)` and dark foreground for contrast
    - When `riskLevel === 'phishing'`, apply `animation: badge-pulse var(--dur-badge-pulse) ease-in-out infinite`
    - Add `role="status"` and `aria-label={\`Risk level: ${riskLevel}\`}`
    - Adjust font size and padding for `size === 'small'` (used by ScanHistory)
    - _Requirements: 5.5, 5.6, 10.6_

- [x] 6. `ThreatMeter` component
  - [x] 6.1 Create `src/components/ThreatMeter.tsx` and `ThreatMeter.css`
    - Accept `score: number` (already clamped 0–100) and `riskLevel: RiskLevel`
    - Render an SVG `viewBox="0 0 200 200"` with a background track circle and a foreground arc circle: `cx=100, cy=100, r=80`; circumference `C = 2π × 80 ≈ 502.65`; `stroke-dasharray: C C`; initial `stroke-dashoffset: C`
    - Apply `transform: rotate(-90deg); transform-origin: center` to the arc circle so the arc starts at 12 o'clock
    - Set arc `stroke` to `RISK_COLORS[riskLevel]`; track circle `stroke` to `rgba(255,255,255,0.08)`
    - On mount or `score`/`riskLevel` change, run RAF animation loop implementing cubic ease-out `t → 1 - (1-t)³` over `DURATIONS.arcFill` (1200 ms); update `strokeDashoffset` directly on the SVG element via `useRef`; also call `setAnimatedScore(Math.round(currentScore))` on each frame for the center text
    - Skip RAF loop when `prefers-reduced-motion: reduce`; set final offset synchronously
    - Render the animated score integer in large type (min 48 px) using `var(--font-heading)` at the SVG center via absolute-positioned `<div>` or SVG `<text>`
    - Render "THREAT LEVEL" label below the score in `var(--color-neon-cyan)` at 70% opacity, 10–14 px
    - Render `<ThreatBadge riskLevel={riskLevel} size="normal">` below the arc
    - Wrap in `<figure aria-label={\`Threat score: ${score}% — ${riskLevel}\`}>` with SVG `aria-hidden="true"`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.7, 10.3, 10.6_

- [x] 7. `EnginePanel` component
  - [x] 7.1 Create `src/components/EnginePanel.tsx` and `EnginePanel.css`
    - Accept `scores: Record<string, number>` prop; render nothing when `Object.keys(scores).length === 0` or scores is null/undefined
    - Render engine widgets in a responsive grid: `grid-template-columns: 1fr` below 768 px, `repeat(2, 1fr)` at 768 px+ (CSS `@media`)
    - Each widget shows: engine name in `var(--font-heading)`, a bar track div, a bar fill div, and the score as a whole-number integer percentage
    - Bar fill uses `transform: scaleX(0)` initial state with `transform-origin: left`; CSS `animation: bar-fill var(--dur-bar) ease-out forwards` drives `transform: scaleX(var(--target-scale))` where `--target-scale = score / 100`
    - Set `animation-delay: calc(index × DURATIONS.barStagger ms)` via inline `style` with `--delay` custom property
    - Color each bar fill based on score threshold: < 30 → `var(--color-neon-green)`, 30–69 → `var(--color-neon-amber)`, ≥ 70 → `var(--color-neon-crimson)` (applied as inline `background` or a data attribute + CSS)
    - Add `role="meter" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100} aria-label={\`${engineName} score\`}` on each bar wrapper
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 10.5_

- [x] 8. `XAIPanel` component
  - [x] 8.1 Create `src/components/XAIPanel.tsx` and `XAIPanel.css`
    - Accept `summary: string` and `reasons: string[]` props; render nothing when both are empty
    - Render summary inside a `.glass-card` with a `3px solid var(--color-neon-cyan)` left border
    - Implement `classifyReason(text)` using the `THREAT_KEYWORDS` list (case-insensitive); return `'threat'` or `'safe'`
    - Render each reason as a `<li>` prefixed with an inline SVG or Unicode icon: `⚠` in `var(--color-neon-crimson)` for `'threat'`, `✓` in `var(--color-neon-green)` for `'safe'`
    - Apply staggered fade-in: each `<li>` gets `animation: fade-up var(--dur-xai-fade, 300ms) ease-in-out forwards` with inline `animation-delay: calc(index × 80ms)`
    - Each icon-only element needs `aria-label` or `aria-hidden="true"` with the text conveying meaning
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 10.5_

- [x] 9. `ErrorBanner` component
  - [x] 9.1 Create `src/components/ErrorBanner.tsx` and `ErrorBanner.css`
    - Accept `message: string` and `onDismiss: () => void` props
    - Render a `<div role="alert">` with `border-left: 4px solid var(--color-neon-crimson)` and `background: rgba(255, 77, 79, 0.15)`
    - Apply `animation: banner-enter 250ms ease-out forwards` on mount
    - Include a dismiss `<button>` with `×` label and `aria-label="Dismiss error"` that calls `onDismiss` on click; style with NeonCrimson color and visible focus ring
    - _Requirements: 8.1, 8.4, 10.5_

- [x] 10. `ScannerPanel` component
  - [x] 10.1 Create `src/components/ScannerPanel.tsx` and `ScannerPanel.css`
    - Accept `loading: boolean` and `onSubmit: (req: AnalyzeRequest) => void` props
    - Render inside a `.glass-card` with `max-width: var(--scanner-max-w, 680px)` centered in the page
    - URL input: apply `var(--color-neon-cyan)` accent border, intensify to a neon glow `box-shadow` on `:focus` (via CSS `:focus-visible` or `onFocus`/`onBlur`)
    - "Advanced Options" toggle button: `aria-expanded={showAdvanced}` and `aria-controls="advanced-options-panel"`; panel `<div id="advanced-options-panel">` with `hidden={!showAdvanced}` to remove from tab order when collapsed
    - Image upload input: accept `image/jpeg,image/png,image/gif,image/webp,image/bmp`; on change, validate MIME type and size ≤ 10 MB (`SIZES.imageSizeLimit`); set `imageError` state on violation
    - Validation before submit: check URL not empty (Req 3.6), check URL starts with `http://` or `https://` (Req 3.7); display inline `<span>` error adjacent to the URL field without submitting
    - Loading state: disable all inputs and submit button; render full-width `.scan-line` div with `animation: scan-sweep var(--dur-scan-line) linear infinite`; render `.spinner` div with `animation: spin var(--dur-spinner) linear infinite`; cycle through `LOADING_MESSAGES` via `setInterval(fn, DURATIONS.statusCycle)` in `useEffect` — clear interval when `loading` becomes false
    - Submit button: "SCAN TARGET", full-width, NeonCyan `background`/`color`, glowing `box-shadow: 0 0 16px var(--color-neon-cyan)`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.1, 4.2, 4.3, 4.4, 4.5, 10.1, 10.2, 10.8_

- [x] 11. `ScanHistory` component
  - [x] 11.1 Create `src/components/ScanHistory.tsx` and `ScanHistory.css`
    - Accept `entries: ScanEntry[]` and `onSelect: (entry: ScanEntry) => void` props; render nothing when `entries.length === 0`
    - Render a collapsible panel; internal `expanded` state defaults to `false`
    - Header `<button>` shows "SCAN HISTORY (N)"; `aria-expanded={expanded}` and `aria-controls="scan-history-list"`; clicking toggles `expanded`
    - List `<div id="scan-history-list">` uses `max-height: 0 / max-height: 600px` + `overflow: hidden` CSS transition for expand/collapse; add `aria-live="polite"` for screen reader announcements
    - Each entry is a `<button>` (or `role="button"`) that calls `onSelect(entry)` when activated; display:
      - Truncated URL (max 50 chars + `…`) via `truncateUrl()`
      - `<ThreatBadge riskLevel={entry.result.ensemble_risk_level} size="small">`
      - Score as `(Math.round(score * 10) / 10).toFixed(1)%`
      - Timestamp via `formatTimestamp(entry.timestamp)` → `HH:MM:SS`
    - Apply visible focus indicator on each entry button
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 10.1, 10.2, 10.8_

- [x] 12. Checkpoint — verify component library compiles
  - Ensure all component files and CSS files compile without TypeScript errors. Run `npx tsc --noEmit` in the `frontend/` directory. Fix any type errors before proceeding.

- [x] 13. `App.tsx` refactor — root state owner wiring all components
  - [x] 13.1 Rewrite `App.tsx` to wire all components using `useAnalysis` and history state
    - Import and use the `useAnalysis()` hook; manage `history: ScanEntry[]` (max `SIZES.historyMax` = 20 via `.slice(0, 20)`) and `activeEntry: ScanEntry | null` with `useState`
    - Capture the submitted URL in a `useRef` (`lastUrlRef`) set inside `handleSubmit` before calling `analysis.analyze(req)`; use it when constructing `ScanEntry` in the `useEffect` that watches `analysis.result`
    - `handleSubmit`: clear `activeEntry`, call `analysis.analyze(req)` — error banner auto-dismisses because `analysis.reset()` is called internally at the start of `analyze()`
    - `displayResult = activeEntry?.result ?? analysis.result`
    - Render: `<ParticleBackground>`, `<NavigationBar>`, `<main>` containing:
      - `{analysis.error && !activeEntry && <ErrorBanner message={analysis.error} onDismiss={analysis.reset} />}`
      - `<ScannerPanel loading={analysis.loading} onSubmit={handleSubmit} />`
      - `{displayResult && <ThreatMeter score={displayResult.ensemble_score_percent} riskLevel={displayResult.ensemble_risk_level} />}`
      - `{displayResult?.individual_scores_percent && Object.keys(displayResult.individual_scores_percent).length > 0 && <EnginePanel scores={displayResult.individual_scores_percent} />}`
      - `{displayResult && (displayResult.xai_summary || displayResult.reasons?.length > 0) && <XAIPanel summary={displayResult.xai_summary} reasons={displayResult.reasons} />}`
      - `{history.length > 0 && <ScanHistory entries={history} onSelect={setActiveEntry} />}`
    - Apply top-level layout styles: `min-height: 100vh`, `padding-top: var(--nav-height)`, `display: flex; flex-direction: column; align-items: center`
    - Responsive grid for results area: single column < 768 px, `grid-template-columns: repeat(2, 1fr)` ≥ 768 px (Req 1.5, 1.6)
    - _Requirements: 1.3, 1.5, 1.6, 8.3, 9.1, 9.2, 9.7, 12.1, 12.2_

  - [x] 13.2 Rewrite `App.css` to contain only global layout rules
    - Remove all pre-existing styles unrelated to this overhaul
    - Add layout rules: `#root` and `main` layout, results grid, content centering, `padding-top: var(--nav-height)` offset
    - _Requirements: 1.3, 1.5, 1.6_

- [x] 14. Bundle size enforcement script
  - [x] 14.1 Create `scripts/check-bundle-size.mjs` that fails the build if app chunks exceed 150 KB gzipped
    - Read all JS files from `dist/assets/` that are not named `vendor-*`
    - Gzip each file using Node's built-in `zlib.gzipSync` and sum the compressed sizes
    - If total > `150 * 1024` bytes, `console.error` the size and `process.exit(1)`
    - Add `"check-bundle": "vite build && node scripts/check-bundle-size.mjs"` to `package.json` scripts
    - _Requirements: 11.5, 11.6_

- [x] 15. Final integration, accessibility, and reduced-motion pass
  - [x] 15.1 Verify tab order and ARIA attributes across all components
    - Confirm DOM order matches the required tab order: navigation bar → URL input → Advanced Options toggle → submit button → results area → scan history (Req 10.1)
    - Verify `aria-expanded` on Advanced Options toggle and ScanHistory header (Req 10.8)
    - Verify `role="alert"` on `ErrorBanner`, `role="status"` on `ThreatBadge`, `role="meter"` on EnginePanel bars (Req 10.5)
    - Verify `aria-hidden="true"` on the ThreatMeter SVG and `aria-label` on the `<figure>` wrapper (Req 10.5)
    - _Requirements: 10.1, 10.5, 10.6, 10.7, 10.8_

  - [ ]* 15.2 Write property-based tests for the history length invariant
    - **Property 3: FOR ALL histories of length ≥ 20, after prepending a new entry `history.length === 20`**
    - **Validates: Requirements 9.1, 9.2**
    - Generate arbitrary `ScanEntry` arrays of length 0–25 via `fast-check`, apply the prepend-and-slice logic, assert length ≤ 20

  - [ ]* 15.3 Write property-based tests for `classifyReason` and ThreatBadge dual-modality
    - **Property 6: FOR ALL `reasons[i]` containing any keyword in `THREAT_KEYWORDS` (case-insensitive), `classifyReason` returns `'threat'`; for all others it returns `'safe'`**
    - **Property 4: FOR ALL `riskLevel ∈ {'safe', 'suspicious', 'phishing'}`, `ThreatBadge` renders non-empty text AND a color**
    - **Validates: Requirements 7.2, 10.6**

  - [ ]* 15.4 Write property-based tests for ThreatMeter score clamping
    - **Property 2: FOR ALL raw `score` values (including NaN, Infinity, negative, > 100), the displayed value is `Math.max(0, Math.min(100, score))`**
    - **Validates: Requirements 5.7**

- [x] 16. Final checkpoint — run build and bundle check
  - Run `npm run check-bundle` in `frontend/`. Fix any TypeScript errors and ensure the bundle check script reports total app chunk size ≤ 150 KB gzipped. Ask the user if any questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP build
- All CSS animations use `transform` and `opacity` only (except `bar-fill` which animates `transform: scaleX`) to ensure GPU compositing — no `width`, `height`, `top`, `left`, or layout properties are animated
- The `vendor` chunk (react + react-dom, ~45 KB gzipped) is excluded from the 150 KB app bundle limit
- Fonts are loaded from Google CDN with `display=swap` baked into the URL — no extra `@font-face` CSS needed
- Google Fonts load time: the 3-second fallback is handled automatically by `font-display: swap` in the stylesheet served by Google
- The `prefers-reduced-motion` media query is handled in two places: CSS (`index.css` global override) and JS (ParticleBackground canvas loop, ThreatMeter RAF loop) — both must be checked independently
- `ScanEntry` de-duplication is intentionally NOT done — Req 9.7 requires duplicate URLs to appear as separate entries with their own timestamps

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "1.5", "2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1", "4.1", "5.1"] },
    { "id": 3, "tasks": ["6.1", "7.1", "8.1", "9.1"] },
    { "id": 4, "tasks": ["10.1", "11.1"] },
    { "id": 5, "tasks": ["13.1", "13.2"] },
    { "id": 6, "tasks": ["14.1"] },
    { "id": 7, "tasks": ["15.1", "15.2", "15.3", "15.4"] }
  ]
}
```
