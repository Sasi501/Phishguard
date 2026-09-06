export const COLORS = {
  baseBg:         '#050508',
  neonCyan:       '#00e5ff',
  neonAmber:      '#ffa940',
  neonCrimson:    '#ff4d4f',
  neonGreen:      '#39ff14',
  glass:          'rgba(255, 255, 255, 0.04)',
  glassBorder:    'rgba(0, 229, 255, 0.15)',
  glassShadow:    '0 8px 32px rgba(0, 229, 255, 0.08)',
  text:           '#e0e0e0',
  textMuted:      'rgba(224, 224, 224, 0.7)',
} as const

export const FONTS = {
  body:    "'Inter', system-ui, sans-serif",
  heading: "'Orbitron', 'Share Tech Mono', monospace",
} as const

export const DURATIONS = {
  arcFill:        1200,   // ms — ThreatMeter arc ease-out fill
  barFill:        800,    // ms — EnginePanel bar fill
  barStagger:     150,    // ms — delay between each bar
  scanLine:       1200,   // ms — loading scan-line sweep loop
  spinner:        900,    // ms — loading arc rotation
  particleMin:    0.2,    // px/frame — slowest particle drift
  particleMax:    1.0,    // px/frame — fastest particle drift
  badgePulse:     1500,   // ms — phishing ThreatBadge glow pulse
  systemPulse:    2000,   // ms — "SYSTEM ONLINE" nav pulse
  xaiStagger:     80,     // ms — XAI list item fade-in delay
  xaiFade:        300,    // ms — each XAI item fade duration
  statusCycle:    1000,   // ms — loading status message rotation
} as const

export const SIZES = {
  navHeight:      64,     // px
  scannerMaxW:    680,    // px
  historyMax:     20,     // entries
  urlTruncate:    50,     // characters
  imageSizeLimit: 10 * 1024 * 1024,  // 10 MB in bytes
} as const

// Risk level → accent color mapping
export const RISK_COLORS: Record<string, string> = {
  safe:       COLORS.neonGreen,
  suspicious: COLORS.neonAmber,
  phishing:   COLORS.neonCrimson,
}
