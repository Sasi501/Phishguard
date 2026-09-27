import type { XaiEvidence } from '../types/api'
import './ThreatIntelligence.css'

interface ThreatIntelligenceProps {
  xai?: XaiEvidence | null
}

function normalizeStatus(value?: string): string {
  if (!value) return 'Unavailable'
  const normalized = value.toUpperCase()
  if (normalized === 'MATCH') return 'MATCH'
  if (normalized === 'NO MATCH') return 'NO MATCH'
  return normalized
}

function normalizeRisk(value?: string): string {
  if (!value) return 'Unavailable'
  const map: Record<string, string> = {
    safe: 'SAFE',
    low: 'LOW',
    medium: 'MEDIUM',
    high: 'HIGH',
    suspicious: 'SUSPICIOUS',
    phishing: 'PHISHING',
  }
  return map[value.toLowerCase()] ?? value.toUpperCase()
}

function toneForRisk(value?: string): string {
  const normalized = value?.toLowerCase() ?? ''
  if (normalized === 'safe') return 'safe'
  if (normalized === 'low') return 'low'
  if (normalized === 'medium' || normalized === 'suspicious') return 'medium'
  if (normalized === 'high' || normalized === 'phishing') return 'high'
  return 'unknown'
}

export default function ThreatIntelligence({ xai }: ThreatIntelligenceProps) {
  const signal = xai?.engine_signals?.find(signal => signal.engine?.toLowerCase().includes('threat')) ?? null
  const sourceNames = signal?.sources && signal.sources.length > 0 ? signal.sources.map(source => source.toLowerCase()) : []

  const backendStatus = signal?.match_status ? normalizeStatus(signal.match_status) : null
  const scoreValue = signal && typeof signal.score === 'number' && Number.isFinite(signal.score)
    ? Math.min(100, Math.max(0, signal.score))
    : null

  return (
    <section className="threat-intelligence glass-card" aria-label="Threat intelligence report">
      <div className="threat-intelligence__header">
        <h2 className="threat-intelligence__title">THREAT INTELLIGENCE</h2>
      </div>

      <div className="threat-intelligence__summary">
        <div className="threat-intelligence__summary-item">
          <span className="threat-intelligence__label">Status</span>
          <strong className="threat-intelligence__value">
            {backendStatus ?? (signal?.status === 'restricted' ? 'Restricted' : signal?.status ?? 'Unavailable')}
          </strong>
        </div>
        <div className="threat-intelligence__summary-item">
          <span className="threat-intelligence__label">Risk</span>
          <strong className="threat-intelligence__value">{signal ? normalizeRisk(signal.risk_level) : 'Unavailable'}</strong>
        </div>
        {scoreValue !== null && (
          <div className="threat-intelligence__summary-item">
            <span className="threat-intelligence__label">Threat Match Signal</span>
            <strong className="threat-intelligence__value">{Math.round(scoreValue)}%</strong>
          </div>
        )}
      </div>

      {signal ? (
        <div className="threat-intelligence__panel">
          <div className="threat-intelligence__panel-head">
            <span>Threat Intelligence Signal · Final URL</span>
            <strong>{normalizeRisk(signal.risk_level)}</strong>
          </div>

          {backendStatus && (
            <div className="threat-intelligence__match" aria-live="polite">
              <span className="threat-intelligence__match-icon" aria-hidden="true">
                {backendStatus === 'MATCH' ? '⚠' : backendStatus === 'NO MATCH' ? '✓' : '•'}
              </span>
              <span>{backendStatus}</span>
            </div>
          )}
          {signal.status && signal.status !== 'available' && signal.reason && (
            <p className="threat-intelligence__empty">{signal.reason}</p>
          )}

          {scoreValue !== null && (
            <div className="threat-intelligence__meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(scoreValue)} aria-label={`Threat intelligence score ${Math.round(scoreValue)} percent`}>
              <div className={`threat-intelligence__meter-fill threat-intelligence__meter-fill--${toneForRisk(signal.risk_level)}`} style={{ width: `${scoreValue}%` }} />
            </div>
          )}

          {sourceNames.length > 0 && (
            <div className="threat-intelligence__sources">
              <span className="threat-intelligence__sources-label">Sources</span>
              <div className="threat-intelligence__chips">
                {sourceNames.map((source, index) => (
                  <span key={`${source}-${index}`} className="threat-intelligence__chip">{source}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className="threat-intelligence__empty">Threat intelligence evidence unavailable for this scan.</p>
      )}
    </section>
  )
}
