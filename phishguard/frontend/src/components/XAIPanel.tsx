import { DURATIONS } from '../theme'
import type { XaiEvidence } from '../types/api'
import './XAIPanel.css'

interface XAIPanelProps {
  summary?: string
  reasons?: string[]
  xai?: XaiEvidence | null
}

const THREAT_KEYWORDS = [
  'phishing', 'suspicious', 'malicious', 'fake',
  'spoofed', 'fraudulent', 'deceptive', 'flagged',
  'risk', 'unknown', 'ssl', 'imitation', 'match',
  'typosquatting', 'unresolved', 'redirect'
] as const

function classifyReason(text: string): 'threat' | 'safe' {
  const lower = text.toLowerCase()
  return THREAT_KEYWORDS.some(kw => lower.includes(kw)) ? 'threat' : 'threat'
}

function severityToGlyph(severity?: string): string {
  if (severity === 'high') return '🔴'
  if (severity === 'medium') return '🟠'
  if (severity === 'low') return '🟡'
  return '⚪'
}

export default function XAIPanel({ summary, reasons = [], xai }: XAIPanelProps) {
  const evidence = xai ?? null

  if (!summary && (!reasons || reasons.length === 0) && !evidence) return null

  return (
    <section className="xai-panel glass-card" aria-label="AI analysis explanation">
      <h2 className="xai-panel__heading">WHY WAS THIS DETECTED?</h2>

      <div className="xai-panel__block">
        <h3>Overall Explanation</h3>
        <p className="xai-panel__summary">{evidence?.summary ?? summary ?? 'No structured explanation is available for this scan.'}</p>
      </div>

      {evidence && (
        <>
          {evidence.risk_factors.length > 0 && (
            <div className="xai-panel__block">
              <h3>Risk Factors</h3>
              <ul className="xai-panel__list xai-panel__list--risk">
                {evidence.risk_factors.map((factor, index) => (
                  <li key={`${factor.title}-${index}`} className="xai-panel__item xai-panel__item--risk">
                    <span className="xai-panel__icon">{severityToGlyph(factor.severity)}</span>
                    <div>
                      <strong>{factor.title}</strong>
                      <p>{factor.description}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {evidence.safety_factors.length > 0 && (
            <div className="xai-panel__block">
              <h3>Safety / Supporting Factors</h3>
              <ul className="xai-panel__list xai-panel__list--safe">
                {evidence.safety_factors.map((factor, index) => (
                  <li key={`${factor.title}-${index}`} className="xai-panel__item xai-panel__item--safe">
                    <span className="xai-panel__icon">🟢</span>
                    <div>
                      <strong>{factor.title}</strong>
                      <p>{factor.description}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {evidence.engine_signals.length > 0 && (
            <div className="xai-panel__block">
              <h3>Individual Engine Signals (not final ensemble)</h3>
              <div className="xai-panel__signal-list">
                {evidence.engine_signals.map((signal, index) => (
                  <div key={`${signal.engine}-${index}`} className="xai-panel__signal">
                    <div className="xai-panel__signal-head">
                      <span>{signal.engine}</span>
                      <strong>{signal.match_status ?? `${Math.round(signal.score)}%`}</strong>
                    </div>
                    <div className="xai-panel__meter" aria-label={`${signal.engine} risk`}>
                      <div
                        className="xai-panel__meter-fill"
                        style={{
                          width: `${Math.min(100, Math.max(0, signal.score))}%`,
                          background: signal.risk_level === 'phishing' || signal.risk_level === 'high' || signal.risk_level === 'suspicious' || signal.risk_level === 'medium'
                            ? 'var(--color-neon-crimson)'
                            : signal.risk_level === 'safe' || signal.risk_level === 'low'
                              ? 'var(--color-neon-green)'
                              : 'var(--color-neon-amber)',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {evidence.feature_importance.length > 0 && (
            <div className="xai-panel__block">
              <h3>AI Feature Importance</h3>
              <table className="xai-panel__table">
                <thead>
                  <tr>
                    <th>Feature</th>
                    <th>Impact</th>
                  </tr>
                </thead>
                <tbody>
                  {evidence.feature_importance.map((item, index) => (
                    <tr key={`${item.feature}-${index}`}>
                      <td>{item.feature}</td>
                      <td>{item.impact >= 0 ? '+' : ''}{item.impact.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {(evidence.risk_factors.length > 0 || evidence.safety_factors.length > 0 || evidence.feature_importance.length > 0) && (
            <details className="xai-panel__details">
              <summary>Technical Explanation</summary>
              <div className="xai-panel__technical">
                {evidence.engine_signals.length > 0 && (
                  <ul>
                    {evidence.engine_signals.map((signal, idx) => (
                      <li key={`${signal.engine}-${idx}`}>
                        <strong>{signal.engine}:</strong> {signal.match_status ?? `${signal.score}%`} · {signal.risk_level}
                      </li>
                    ))}
                  </ul>
                )}
                {evidence.feature_importance.length > 0 && (
                  <ul>
                    {evidence.feature_importance.map((item, idx) => (
                      <li key={`${item.feature}-${idx}`}>
                        <strong>{item.feature}:</strong> value={String(item.value)} impact={item.impact}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </details>
          )}
        </>
      )}

      {!evidence && reasons && reasons.length > 0 && (
        <ul className="xai-panel__reasons" aria-label="Threat indicators">
          {reasons.map((reason, index) => {
            const type = classifyReason(reason)
            return (
              <li
                key={index}
                className={`xai-panel__reason xai-panel__reason--${type}`}
                style={{
                  animationDelay: `${index * DURATIONS.xaiStagger}ms`,
                  animationDuration: `${DURATIONS.xaiFade}ms`,
                } as React.CSSProperties}
              >
                <span className="xai-panel__icon" aria-hidden="true">⚠️</span>
                <span className="xai-panel__reason-text">{reason}</span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
