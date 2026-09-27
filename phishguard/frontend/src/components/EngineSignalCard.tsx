import type { XaiEngineSignal } from '../types/api'
import './EngineSignalCard.css'

interface EngineSignalCardProps {
  signal?: XaiEngineSignal | null
}

function normalizeRiskLabel(riskLevel?: string): string {
  if (!riskLevel) return 'UNKNOWN'
  const map: Record<string, string> = {
    safe: 'SAFE',
    low: 'LOW',
    medium: 'MEDIUM',
    high: 'HIGH',
    suspicious: 'SUSPICIOUS',
    phishing: 'PHISHING',
  }
  return map[riskLevel.toLowerCase()] ?? riskLevel.toUpperCase()
}

function toneForRisk(riskLevel?: string): string {
  const normalized = riskLevel?.toLowerCase() ?? ''
  if (normalized === 'safe') return 'safe'
  if (normalized === 'low') return 'low'
  if (normalized === 'medium' || normalized === 'suspicious') return 'medium'
  if (normalized === 'high' || normalized === 'phishing') return 'high'
  return 'unknown'
}

export default function EngineSignalCard({ signal }: EngineSignalCardProps) {
  if (!signal) {
    return null
  }

  const title = signal.engine || 'UNKNOWN ENGINE'
  const riskLabel = normalizeRiskLabel(signal.risk_level)
  const tone = toneForRisk(signal.risk_level)
  const scoreValue = typeof signal.score === 'number' && Number.isFinite(signal.score) ? signal.score : null
  const scoreText = scoreValue !== null ? `${scoreValue.toFixed(2)}%` : null
  const hasMatchStatus = Boolean(signal.match_status)

  const matchText = hasMatchStatus
    ? signal.match_status === 'MATCH'
      ? 'MATCH FOUND'
      : signal.match_status === 'NO MATCH'
        ? 'NO MATCH'
        : signal.match_status
    : null

  const displayStatus = matchText ?? (scoreText ?? 'NOT ANALYZED')
  const numericWidth = scoreValue === null ? 0 : Math.min(100, Math.max(0, scoreValue))
  const statusLabel = signal.status === 'restricted'
    ? 'RESTRICTED'
    : signal.status === 'error'
      ? 'ERROR'
      : signal.status === 'unavailable'
        ? 'UNAVAILABLE'
        : 'NOT ANALYZED'

  return (
    <article
      className={`engine-signal-card engine-signal-card--${tone}`}
      aria-label={`${title}: ${riskLabel}${scoreText ? `, ${scoreText}` : ''}${matchText ? `, ${matchText}` : ''}`}
    >
      <div className="engine-signal-card__header">
        <span className="engine-signal-card__name">{title}</span>
        <span className={`engine-signal-card__badge engine-signal-card__badge--${tone}`}>{riskLabel}</span>
      </div>

      {scoreText ? (
        <div className="engine-signal-card__score" aria-label={`${title} engine signal ${scoreText}`}>
          {scoreText}
        </div>
      ) : (
        <div className="engine-signal-card__status-text">{statusLabel}</div>
      )}

      {scoreValue !== null && (
        <div
          className="engine-signal-card__meter"
          role="meter"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={scoreValue}
          aria-label={`${title} signal strength ${scoreText}`}
        >
          <div className="engine-signal-card__meter-fill" style={{ width: `${numericWidth}%` }} />
        </div>
      )}

      {matchText ? (
        <div className="engine-signal-card__status" aria-live="polite">
          <span className="engine-signal-card__status-icon" aria-hidden="true">
            {matchText === 'NO MATCH' ? '✓' : '⚠'}
          </span>
          <span>{matchText}</span>
        </div>
      ) : (
        <p className="engine-signal-card__meta">
          {scoreText ? `Individual ${signal.score_type === 'match_signal' ? 'match' : 'engine'} signal` : 'No numeric signal reported'}
        </p>
      )}

      {signal.url_scope && (
        <p className="engine-signal-card__meta">
          Source scope: {signal.url_scope.replaceAll('_', ' ')}
        </p>
      )}

      {signal.sources && signal.sources.length > 0 && (
        <p className="engine-signal-card__sources">{signal.sources.slice(0, 2).join(', ')}</p>
      )}

      {!signal.sources?.length && !matchText && !scoreText && (
        <p className="engine-signal-card__meta">{signal.reason || 'Not analyzed for this scan.'}</p>
      )}

      {!matchText && !scoreText && (
        <p className="engine-signal-card__meta subtle">{displayStatus}</p>
      )}
    </article>
  )
}
