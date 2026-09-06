# Requirements Document

## Introduction

PhishGuard is an AI-powered phishing detection platform that combines ML, NLP, and domain intelligence engines into an ensemble scoring system. The current UI is a functional but visually minimal single-page form. This overhaul replaces it with a premium, next-generation cybersecurity dashboard that communicates analytical power through motion, data visualization, and a cyberpunk/glassmorphism aesthetic — making the interface feel as sophisticated as the backend AI it exposes.

The redesigned Dashboard is a single-page application built on React 19 + TypeScript + Vite. It retains the existing API contract (`POST /api/analyze-ensemble/`) and adds no new backend endpoints.

---

## Glossary

- **Dashboard**: The single-page application delivered to the browser.
- **Scanner**: The UI subsystem responsible for collecting URL, optional text, and optional image inputs and submitting them to the API.
- **ThreatMeter**: The animated radial/arc gauge component that displays the ensemble risk score.
- **ThreatBadge**: The color-coded, animated status indicator that displays the ensemble risk level label (SAFE / SUSPICIOUS / PHISHING).
- **EnginePanel**: The section that visualises per-engine scores (ML, NLP, Domain Intelligence) as individual animated bar or arc widgets.
- **XAIPanel**: The section that renders the XAI summary and reasons list returned by the API.
- **ParticleBackground**: The full-screen animated canvas layer that renders ambient floating particles or a grid mesh.
- **ScanHistory**: The in-session list of previous scan results stored in browser memory.
- **API**: The FastAPI backend endpoint at `POST /api/analyze-ensemble/`.
- **RiskLevel**: One of three discrete values returned by the API — `safe`, `suspicious`, or `phishing`.
- **EnsembleScore**: The numeric percentage (0–100) returned by the API field `ensemble_score_percent`.
- **IndividualScores**: The per-engine score map returned by the API field `individual_scores_percent`.
- **XAISummary**: The natural-language explanation string returned by the API field `xai_summary`.
- **Reasons**: The array of strings returned by the API field `reasons`.
- **LoadingState**: The period between form submission and API response.
- **ErrorState**: The condition where the API returns a non-2xx response or a network error occurs.
- **GlassmorphismCard**: A UI panel styled with semi-transparent background, backdrop blur, and a subtle glowing border.
- **NeonCyan**: The primary accent color `#00e5ff`.
- **NeonAmber**: The warning accent color `#ffa940`.
- **NeonCrimson**: The danger accent color `#ff4d4f`.
- **NeonGreen**: The safe accent color `#39ff14`.
- **BaseBackground**: The near-black base color `#050508`.
- **AnimationDuration**: The configured CSS/JS transition time for a given animated element.

---

## Requirements

### Requirement 1: Visual Foundation and Layout

**User Story:** As a security analyst, I want a visually immersive dark dashboard layout, so that the tool feels authoritative and purpose-built for threat analysis.

#### Acceptance Criteria

1. THE Dashboard SHALL use `#050508` as the full-viewport background color, covering 100% of viewport width and height with no visible gaps or default browser background.
2. THE Dashboard SHALL render a ParticleBackground layer beneath all content consisting of dot particles or an animated hex/grid mesh using `#00E5FF` at 4–8% opacity, where each particle drifts at a speed between 0.2 and 1.0 pixels per second.
3. THE Dashboard SHALL organize content into three regions: a fixed top navigation bar occupying 100% of viewport width, a central Scanner panel centered horizontally within the content area, and a results area rendered directly below the Scanner panel.
4. THE Dashboard SHALL apply the following styles to all GlassmorphismCards: `background: rgba(255,255,255,0.04)`, `backdrop-filter: blur(16px)`, a 1px solid border using `#00E5FF` at 15% opacity, and `box-shadow: 0 8px 32px rgba(0,229,255,0.08)`.
5. WHEN the viewport width is less than 768px, THE Dashboard SHALL arrange all content regions in a single-column vertical stack.
6. WHEN the viewport width is 768px or greater, THE Dashboard SHALL arrange content regions in a multi-column grid layout with a minimum of 2 columns.
7. THE Dashboard SHALL load the Inter typeface for all body text elements and Orbitron or Share Tech Mono for all heading and numeric readout elements via Google Fonts, with fallback to a system sans-serif font if Google Fonts fails to load within 3 seconds.

---

### Requirement 2: Navigation Bar

**User Story:** As a user, I want a fixed header that identifies the product and signals active status, so that the interface feels live and operational at all times.

#### Acceptance Criteria

1. THE Dashboard SHALL render a fixed top navigation bar with a height between 56 px and 72 px that remains visible during scroll and occupies the full viewport width.
2. THE Dashboard SHALL display the PhishGuard logo mark (or stylized text "PHISHGUARD") in the navigation bar using the NeonCyan color with a text-shadow glow effect.
3. THE Dashboard SHALL display a "SYSTEM ONLINE" status indicator in the navigation bar that animates with a repeating pulse at a 2-second cycle interval using a fade or scale keyframe animation.
4. WHEN the user is on a viewport wider than 768 px, THE Dashboard SHALL display a horizontal navigation bar with all navigation items visible.
5. WHEN the viewport width is 768 px or narrower, THE Dashboard SHALL collapse the navigation bar to show only the logo and the "SYSTEM ONLINE" status indicator, hiding all other navigation items.

---

### Requirement 3: Scanner Input Panel

**User Story:** As a security analyst, I want a clean, focused input panel for submitting URLs, so that I can quickly initiate threat scans without distraction.

#### Acceptance Criteria

1. THE Scanner SHALL render inside a GlassmorphismCard centered on the page with a maximum width of 680 px.
2. THE Scanner SHALL display a URL input field with a NeonCyan accent that intensifies on focus with a glow outline effect.
3. THE Scanner SHALL display a collapsible "Advanced Options" section that reveals the optional text textarea and image file upload inputs when expanded.
4. WHEN the "Advanced Options" section is collapsed, THE Scanner SHALL hide the text textarea and image upload input from view and from tab order.
5. THE Scanner SHALL display a "SCAN TARGET" submit button that spans the full width of the form with NeonCyan styling and a glowing box-shadow.
6. WHEN the URL input field is empty and the user activates the submit button, THE Scanner SHALL display an inline validation message indicating that a URL is required, adjacent to the URL field, without submitting to the API.
7. WHEN the user types a value that does not include a valid `http://` or `https://` scheme, THE Scanner SHALL display an inline validation message indicating a valid URL with scheme is required, without submitting to the API.
8. WHEN the user selects a file for the image upload input, THE Scanner SHALL reject files that are not of type image/jpeg, image/png, image/gif, image/webp, or image/bmp, and SHALL display an inline validation message indicating only image files are accepted.
9. WHEN the user selects an image file larger than 10 MB, THE Scanner SHALL reject the file and display an inline validation message indicating the file size limit is 10 MB.

---

### Requirement 4: Loading / Scanning State

**User Story:** As a user, I want a visually engaging loading experience during analysis, so that I understand the system is actively working and feel confident in its processing power.

#### Acceptance Criteria

1. WHEN the Dashboard is in LoadingState, THE Scanner SHALL disable the submit button and all input fields so that no clicks, keystrokes, or form submissions are accepted.
2. WHEN the Dashboard is in LoadingState, THE Dashboard SHALL display a full-width neon horizontal scan-line that sweeps from top to bottom of the Scanner panel continuously with a 1.2-second loop, remaining visible until LoadingState ends.
3. WHEN the Dashboard is in LoadingState, THE Dashboard SHALL display sequentially cycling status messages (e.g., "Resolving domain…", "Running ML classifier…", "Analyzing NLP signals…", "Fusing ensemble scores…") with each message displayed for between 800 ms and 2000 ms, cycling back to the first message after the last.
4. WHEN the Dashboard is in LoadingState, THE Dashboard SHALL render a circular spinner or arc loader in NeonCyan completing a full 360-degree rotation every 0.9 seconds.
5. WHEN the API returns a success response or an error response, THE Dashboard SHALL exit LoadingState, re-enable all input fields and the submit button, and remove the loading animations.

---

### Requirement 5: Threat Meter (Ensemble Score Display)

**User Story:** As a security analyst, I want an animated radial gauge that shows the ensemble threat score, so that I can instantly understand the overall risk level at a glance.

#### Acceptance Criteria

1. WHEN the API returns a result, THE Dashboard SHALL render the ThreatMeter as a circular arc gauge with the arc fill animating from 0% to the EnsembleScore value over 1.2 seconds using an ease-out easing function.
2. THE ThreatMeter SHALL color the arc fill according to RiskLevel: NeonGreen for `safe`, NeonAmber for `suspicious`, and NeonCrimson for `phishing`.
3. THE ThreatMeter SHALL display the EnsembleScore as a whole-number integer percentage between 0 and 100 in large type (minimum 48px) at the center of the arc, using the monospace heading font.
4. THE ThreatMeter SHALL display a "THREAT LEVEL" label below the numeric score in NeonCyan at 70% opacity, with a font size between 10px and 14px.
5. THE ThreatMeter SHALL render the ThreatBadge below the arc: a pill-shaped element (border-radius ≥ 9999px) containing the RiskLevel text in uppercase, using the corresponding risk color as background with a box-shadow glow of at least 4px spread matching that color at 60% opacity.
6. WHEN the RiskLevel is `phishing`, THE ThreatBadge SHALL animate with a pulsing glow at a 1.5-second interval, alternating the box-shadow spread between a minimum of 4px and a maximum of 16px.
7. WHEN the API returns an EnsembleScore outside the range 0–100, THE Dashboard SHALL clamp the displayed value to 0 (minimum) or 100 (maximum) without throwing an error.
8. WHEN the ThreatMeter is not displaying a result (no API call has completed or the last call resulted in an error), THE ThreatMeter SHALL not be rendered in the DOM.

---

### Requirement 6: Engine Score Panels

**User Story:** As a security analyst, I want to see how each individual AI engine scored the target, so that I can understand which signals drove the overall result.

#### Acceptance Criteria

1. WHEN the API returns IndividualScores, THE EnginePanel SHALL render one widget per engine key in the IndividualScores map.
2. WHEN the API returns an empty or null IndividualScores map, THE EnginePanel SHALL not render.
3. EACH engine widget SHALL display the engine name, a horizontal animated progress bar, and the numeric score as a whole-number integer percentage.
4. THE EnginePanel SHALL animate each progress bar fill from 0% to its score value sequentially, with each bar starting its animation 150 ms after the previous one, over 0.8 seconds using ease-out easing.
5. THE EnginePanel SHALL color each progress bar based on the individual engine's score: below 30% uses NeonGreen, 30–69% uses NeonAmber, and 70% and above uses NeonCrimson.
6. THE EnginePanel SHALL render engine widgets inside a responsive grid: one column on viewports narrower than 768 px, and a minimum of two columns on viewports 768 px and wider.

---

### Requirement 7: XAI Explanation Panel

**User Story:** As a security analyst, I want a clear, readable explanation of why the AI reached its verdict, so that I can justify the result to stakeholders or investigate further.

#### Acceptance Criteria

1. WHEN the API returns a non-empty XAISummary, THE XAIPanel SHALL render the XAISummary text inside a GlassmorphismCard with a NeonCyan left-border accent of 3px width.
2. WHEN the API returns a non-empty Reasons array, THE XAIPanel SHALL render each Reasons entry as a list item prefixed with a colored threat-indicator icon: NeonCrimson warning icon if the reason text contains any of the following exact keywords (case-insensitive): "phishing", "suspicious", "malicious", "fake", "spoofed", "fraudulent", "deceptive"; NeonGreen check icon otherwise.
3. THE XAIPanel SHALL reveal its content with a staggered fade-in animation, with each list item fading in over 300 ms using ease-in-out easing, appearing 80 ms after the previous one.
4. WHEN the API returns an empty Reasons array and an empty XAISummary, THE XAIPanel SHALL not render.

---

### Requirement 8: Error Handling

**User Story:** As a user, I want clear, styled error feedback when something goes wrong, so that I understand the issue and can take corrective action.

#### Acceptance Criteria

1. WHEN the Dashboard is in ErrorState, THE Dashboard SHALL display an error notification banner below the Scanner panel with a NeonCrimson left-border and a background of NeonCrimson at 15% opacity.
2. THE error notification SHALL display the error message text returned by the API, or the fallback message "Unable to reach the analysis server. Check your connection and try again." when the error is a network failure (defined as: no HTTP response received due to a timeout exceeding 10 seconds, a DNS resolution failure, or a connection refused response).
3. WHEN the user submits a new scan while an error notification is visible, THE Dashboard SHALL dismiss the error notification before the new LoadingState begins.
4. THE error notification SHALL include a dismiss button (×) that removes the notification from the DOM when activated.

---

### Requirement 9: Scan History (Session Memory)

**User Story:** As a security analyst, I want to see a list of URLs I've scanned in the current session, so that I can quickly compare results without re-submitting.

#### Acceptance Criteria

1. THE ScanHistory SHALL store up to 20 most-recent scan results in browser memory for the duration of the browser session, and SHALL NOT persist data to localStorage or any external service.
2. WHEN the user completes a scan and the ScanHistory already contains 20 entries, THE Dashboard SHALL remove the oldest entry before prepending the new result.
3. THE ScanHistory SHALL render each entry showing: the scanned URL (truncated to 50 characters with an ellipsis if longer), the ThreatBadge at reduced size, the EnsembleScore as a numeric percentage rounded to one decimal place, and the timestamp of the scan formatted as HH:MM:SS.
4. WHEN the user activates a ScanHistory entry, THE Dashboard SHALL restore the full result view for that entry displaying identical content to the original scan result view, without making a new API call.
5. WHEN the ScanHistory is empty, THE Dashboard SHALL not render the ScanHistory section.
6. THE ScanHistory SHALL render in a collapsible panel below the results area, collapsed by default, with a header showing "SCAN HISTORY (N)" where N is the count of stored entries; activating the header SHALL toggle the panel between expanded and collapsed states.
7. WHEN the user scans a URL that already exists in the ScanHistory, THE Dashboard SHALL store the new result as a separate entry with its own timestamp rather than replacing the existing entry.

---

### Requirement 10: Accessibility

**User Story:** As a user with accessibility needs, I want the dashboard to be navigable by keyboard and compatible with screen readers, so that I can use the tool regardless of my input method.

#### Acceptance Criteria

1. THE Dashboard SHALL maintain a logical tab order: navigation bar → URL input → Advanced Options toggle → submit button → results area → scan history.
2. ALL interactive elements (buttons, inputs, toggles, history entries) SHALL have a visible focus indicator consisting of a solid 2px NeonCyan outline on focus.
3. THE ThreatMeter arc animation SHALL respect the `prefers-reduced-motion` media query — WHEN `prefers-reduced-motion: reduce` is set, THE ThreatMeter SHALL display the final score state immediately without animation.
4. ALL animations and transitions (including ParticleBackground) SHALL respect the `prefers-reduced-motion` media query — WHEN `prefers-reduced-motion: reduce` is set, THE Dashboard SHALL disable all non-essential animations.
5. ALL images and icon-only interactive elements SHALL have descriptive `aria-label` or `alt` attributes that convey the element's purpose without relying on visual context.
6. THE ThreatBadge and ThreatMeter SHALL convey risk level through both color and text label, so that color is never the sole indicator of meaning.
7. THE Dashboard SHALL achieve a minimum contrast ratio of 4.5:1 between body text and its background for WCAG 2.1 AA compliance.
8. ALL non-native interactive elements (custom toggles, collapsible panels, history entries) SHALL expose appropriate ARIA roles, and stateful elements SHALL expose their current state via `aria-expanded` or `aria-pressed` attributes.

---

### Requirement 11: Performance

**User Story:** As a user on a mid-range device, I want the dashboard to load and animate smoothly, so that the experience feels fast and premium rather than sluggish.

#### Acceptance Criteria

1. THE Dashboard SHALL achieve a Lighthouse Performance score of 85 or above on a simulated mid-tier desktop connection (Moto G4 throttled profile).
2. THE ParticleBackground SHALL use `requestAnimationFrame` for its animation loop and SHALL pause the loop WHEN the browser tab is hidden (using the Page Visibility API) to avoid wasting CPU.
3. THE Dashboard SHALL load without layout shift caused by web font loading — THE Dashboard SHALL use `font-display: swap` for all custom typefaces.
4. ALL animated components SHALL use CSS `transform` and `opacity` properties exclusively for their transitions to enable GPU compositing and avoid layout recalculation.
5. THE Dashboard bundle size (excluding vendor chunks) SHALL not exceed 150 KB gzipped after production build.
6. THE build process SHALL emit a warning or fail the build WHEN the production bundle size (excluding vendor chunks) exceeds 150 KB gzipped, making the threshold enforceable at CI time.

---

### Requirement 12: Component Architecture

**User Story:** As a frontend developer, I want the UI split into focused, reusable components, so that the codebase is maintainable and individual components can be tested in isolation.

#### Acceptance Criteria

1. THE Dashboard SHALL be decomposed into at minimum the following components, each in its own file: `NavigationBar`, `ParticleBackground`, `ScannerPanel`, `ThreatMeter`, `ThreatBadge`, `EnginePanel`, `XAIPanel`, `ScanHistory`, `ErrorBanner`.
2. EACH component SHALL accept all variable data via typed React props with no implicit reliance on global mutable state other than the shared scan result context.
3. THE Dashboard SHALL manage API call state (loading, result, error) in a single custom React hook named `useAnalysis` exported from `src/hooks/useAnalysis.ts`.
4. THE Dashboard SHALL define all API response types in a shared TypeScript interface file at `src/types/api.ts`.
5. THE Dashboard SHALL define all color constants and theme tokens in a single file at `src/theme.ts` so that accent colors, font families, and animation durations can be changed from one location.
6. EACH component file SHALL export exactly one default component whose exported name matches the filename (e.g., `NavigationBar.tsx` exports `default NavigationBar`), so that components can be imported and tested in isolation without side effects.
