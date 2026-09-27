import type { XaiEvidence } from '../types/api'
import './DomainIntelligence.css'

interface DomainIntelligenceProps {
  url?: string | null
  xai?: XaiEvidence | null
}

function getHostName(url?: string | null): string {
  if (!url) return 'Unavailable'

  try {
    const parsed = new URL(url)
    return parsed.hostname || 'Unavailable'
  } catch {
    return 'Unavailable'
  }
}

function normalizeRiskString(value?: string): string {
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

function riskTone(value?: string): string {
  if (!value) return 'unknown'
  const normalized = value.toLowerCase()
  if (normalized === 'safe') return 'safe'
  if (normalized === 'low') return 'low'
  if (normalized === 'medium' || normalized === 'suspicious') return 'medium'
  if (normalized === 'high' || normalized === 'phishing') return 'high'
  return 'unknown'
}

export default function DomainIntelligence({ url, xai }: DomainIntelligenceProps) {
  const domainSignal = xai?.engine_signals?.find(signal => signal.engine?.toLowerCase().includes('domain')) ?? null
  const hostName = getHostName(url)

  const domainNotes = [
    ...(xai?.risk_factors ?? []).filter(factor => /domain|ssl|registr|whois|age|certificate/i.test(`${factor.title ?? ''} ${factor.description ?? ''}`)),
    ...(xai?.safety_factors ?? []).filter(factor => /domain|ssl|registr|whois|age|certificate/i.test(`${factor.title ?? ''} ${factor.description ?? ''}`)),
  ]

  const scoreValue = domainSignal && typeof domainSignal.score === 'number' && Number.isFinite(domainSignal.score)
    ? Math.min(100, Math.max(0, domainSignal.score))
    : null

  return (
    <section className="domain-intelligence glass-card" aria-label="Domain intelligence overview">
      <div className="domain-intelligence__header">
        <h2 className="domain-intelligence__title">DOMAIN INTELLIGENCE</h2>
      </div>

      <div className="domain-intelligence__summary">
        <div className="domain-intelligence__summary-item">
          <span className="domain-intelligence__label">Host</span>
          <strong className="domain-intelligence__value">{hostName}</strong>
        </div>
        <div className="domain-intelligence__summary-item">
          <span className="domain-intelligence__label">Status</span>
          <strong className="domain-intelligence__value domain-intelligence__value--status">
            {domainSignal?.status === 'restricted'
              ? 'RESTRICTED'
              : domainSignal
                ? normalizeRiskString(domainSignal.risk_level)
                : 'UNAVAILABLE'}
          </strong>
        </div>
        {scoreValue !== null && (
          <div className="domain-intelligence__summary-item">
            <span className="domain-intelligence__label">Domain Risk Signal</span>
            <strong className="domain-intelligence__value">{Math.round(scoreValue)}%</strong>
          </div>
        )}
      </div>

      {domainSignal ? (
        <div className="domain-intelligence__signal">
          <div className="domain-intelligence__signal-head">
            <span>Domain Risk Signal · Final URL</span>
            <strong>{normalizeRiskString(domainSignal.risk_level)}</strong>
          </div>
          {domainSignal.status && domainSignal.status !== 'available' && domainSignal.reason && (
            <p className="domain-intelligence__empty">{domainSignal.reason}</p>
          )}
          {scoreValue !== null && (
            <div className="domain-intelligence__meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(scoreValue)} aria-label={`Domain intelligence score ${Math.round(scoreValue)} percent`}>
              <div className={`domain-intelligence__meter-fill domain-intelligence__meter-fill--${riskTone(domainSignal.risk_level)}`} style={{ width: `${scoreValue}%` }} />
            </div>
          )}
          {domainSignal.match_status && (
            <div className="domain-intelligence__status">
              <span className="domain-intelligence__status-icon" aria-hidden="true">
                {domainSignal.match_status === 'MATCH' ? '⚠' : '✓'}
              </span>
              <span>{domainSignal.match_status}</span>
            </div>
          )}
        </div>
      ) : (
        <p className="domain-intelligence__empty">No domain signal was returned for this scan.</p>
      )}

      {domainNotes.length > 0 ? (
        <div className="domain-intelligence__notes">
          <h3 className="domain-intelligence__notes-title">Domain Facts</h3>
          <ul className="domain-intelligence__list">
            {domainNotes.map((note, index) => (
              <li key={`${note.title ?? 'domain-note'}-${index}`} className="domain-intelligence__list-item">
                <span className="domain-intelligence__bullet" aria-hidden="true">•</span>
                <span>{note.description || note.title || 'Domain status unavailable.'}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="domain-intelligence__empty">No additional domain metadata was returned by the backend for this scan.</p>
      )}
    </section>
  )
}
