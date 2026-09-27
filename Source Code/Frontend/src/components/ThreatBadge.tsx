import type { RiskLevel } from '../types/api'
import { RISK_COLORS } from '../theme'
import './ThreatBadge.css'

interface ThreatBadgeProps {
  riskLevel: RiskLevel
  size?: 'normal' | 'small'
}

export default function ThreatBadge({ riskLevel, size = 'normal' }: ThreatBadgeProps) {
  const color = RISK_COLORS[riskLevel] ?? '#888'
  const isPulsing = riskLevel === 'phishing'

  return (
    <span
      className={`threat-badge threat-badge--${riskLevel} threat-badge--${size}${isPulsing ? ' threat-badge--pulsing' : ''}`}
      role="status"
      aria-label={`Risk level: ${riskLevel}`}
      style={{ '--badge-color': color } as React.CSSProperties}
    >
      {riskLevel.toUpperCase()}
    </span>
  )
}
