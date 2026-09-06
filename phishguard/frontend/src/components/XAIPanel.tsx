import { DURATIONS } from '../theme'
import './XAIPanel.css'

interface XAIPanelProps {
  summary: string
  reasons: string[]
}

const THREAT_KEYWORDS = [
  'phishing', 'suspicious', 'malicious', 'fake',
  'spoofed', 'fraudulent', 'deceptive', 'flagged',
  'risk', 'unknown', 'ssl', 'imitation', 'match',
  'typosquatting', 'unresolved', 'redirect'
] as const

function classifyReason(text: string): 'threat' | 'safe' {
  const lower = text.toLowerCase()
  return THREAT_KEYWORDS.some(kw => lower.includes(kw)) ? 'threat' : 'threat' // Default to threat indicator in XAI breakdown
}

export default function XAIPanel({ summary, reasons }: XAIPanelProps) {
  if (!summary && (!reasons || reasons.length === 0)) return null

  return (
    <section className="xai-panel glass-card" aria-label="AI analysis explanation">
      {summary && (
        <p className="xai-panel__summary">{summary}</p>
      )}
      {reasons && reasons.length > 0 && (
        <ul className="xai-panel__reasons" aria-label="Threat indicators">
          {reasons.map((reason, index) => {
            const type = classifyReason(reason)
            return (
              <li
                key={index}
                className={`xai-panel__reason xai-panel__reason--threat`}
                style={{
                  animationDelay: `${index * DURATIONS.xaiStagger}ms`,
                  animationDuration: `${DURATIONS.xaiFade}ms`,
                } as React.CSSProperties}
              >
                <span
                  className="xai-panel__icon"
                  aria-hidden="true"
                >
                  ⚠️
                </span>
                <span className="xai-panel__reason-text">{reason}</span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
