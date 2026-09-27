import type { RiskLevel } from '../types/api'
import './RiskAssessmentCard.css'

interface RiskAssessmentCardProps {
  score: number | null
  riskLevel: RiskLevel
  url?: string
}

function formatRiskLabel(riskLevel: RiskLevel): string {
  const labels: Record<RiskLevel, string> = {
    safe: 'SAFE',
    low: 'LOW',
    medium: 'MEDIUM',
    suspicious: 'SUSPICIOUS',
    high: 'HIGH',
    phishing: 'PHISHING',
    unavailable: 'UNAVAILABLE',
  }

  return labels[riskLevel] ?? riskLevel.toUpperCase()
}

export default function RiskAssessmentCard({ score, riskLevel, url }: RiskAssessmentCardProps) {
  const safeScore = typeof score === 'number' && Number.isFinite(score) ? Math.min(100, Math.max(0, score)) : null
  const riskLabel = formatRiskLabel(riskLevel)
  const meterWidth = `${safeScore ?? 0}%`

  return (
    <section className="risk-card glass-card" aria-label={`Risk assessment. Overall risk score is ${safeScore === null ? 'unavailable' : `${safeScore.toFixed(2)} percent`}, risk level ${riskLabel}.`}>
      <div className="risk-card__header">
        <div>
          <p className="risk-card__eyebrow">PHISHGUARD RISK ASSESSMENT</p>
          <h2 className="risk-card__title">{url ? 'SCAN RESULT' : 'OVERALL RISK'}</h2>
          {url && <p className="risk-card__url" title={url}>{url}</p>}
        </div>
        <span className={`risk-card__badge risk-card__badge--${riskLevel}`}>
          {riskLabel}
        </span>
      </div>

      <div className="risk-card__score-block">
        <div className={`risk-card__score${safeScore === null ? ' risk-card__score--unavailable' : ''}`}>
          {safeScore === null ? 'Unavailable' : `${safeScore.toFixed(2)}%`}
        </div>
        <div className="risk-card__score-label">FINAL ENSEMBLE RISK SCORE</div>
      </div>

      {safeScore !== null ? (
        <div className="risk-card__meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={safeScore} aria-label={`Overall risk score: ${safeScore.toFixed(2)} percent`}>
          <div className="risk-card__meter-scale">
            <span>0%</span>
            <span>100%</span>
          </div>
          <div className="risk-card__meter-track">
            <div className="risk-card__meter-fill" style={{ width: meterWidth }} />
            <div className="risk-card__meter-marker" style={{ left: meterWidth }} aria-hidden="true" />
          </div>
        </div>
      ) : (
        <p className="risk-card__score-unavailable" role="status">The analysis API did not return a usable ensemble score.</p>
      )}

    </section>
  )
}
