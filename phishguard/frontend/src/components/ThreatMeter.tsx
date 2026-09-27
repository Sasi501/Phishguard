import { useEffect, useRef, useState } from 'react'
import type { RiskLevel } from '../types/api'
import { RISK_COLORS, DURATIONS } from '../theme'
import ThreatBadge from './ThreatBadge'
import './ThreatMeter.css'

interface ThreatMeterProps {
  score: number | null       // already clamped 0–100 when available
  riskLevel: RiskLevel
}

const CIRCUMFERENCE = 2 * Math.PI * 80

function easeOut(t: number): number {
  return 1 - Math.pow(1 - t, 3)  // cubic ease-out
}

export default function ThreatMeter({ score, riskLevel }: ThreatMeterProps) {
  const arcRef = useRef<SVGCircleElement>(null)
  const [animatedScore, setAnimatedScore] = useState<number | null>(null)
  const validScore = typeof score === 'number' && Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : null

  useEffect(() => {
    if (validScore === null) {
      if (arcRef.current) arcRef.current.style.strokeDashoffset = String(CIRCUMFERENCE)
      setAnimatedScore(null)
      return
    }
    const scoreToAnimate = validScore
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (prefersReducedMotion) {
      // Set final state immediately, no animation
      if (arcRef.current) {
        arcRef.current.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - scoreToAnimate / 100))
      }
      setAnimatedScore(Math.round(scoreToAnimate))
      return
    }

    const startTime = performance.now()
    let rafId: number

    function step(now: number) {
      const elapsed = now - startTime
      const t = Math.min(elapsed / DURATIONS.arcFill, 1)
      const easedT = easeOut(t)
      const current = easedT * scoreToAnimate

      if (arcRef.current) {
        arcRef.current.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - current / 100))
      }
      setAnimatedScore(Math.round(current))

      if (t < 1) {
        rafId = requestAnimationFrame(step)
      }
    }

    rafId = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafId)
  }, [validScore, riskLevel])

  const arcColor = RISK_COLORS[riskLevel] ?? '#888'

  return (
    <figure
      className="threat-meter"
      aria-label={`Threat score: ${validScore === null ? 'unavailable' : `${validScore}%`} — ${riskLevel}`}
    >
      <div className="threat-meter__gauge-wrapper">
        <svg
          viewBox="0 0 200 200"
          className="threat-meter__svg"
          aria-hidden="true"
        >
          {/* Background track */}
          <circle
            cx="100"
            cy="100"
            r="80"
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="12"
          />
          {/* Animated arc */}
          <circle
            ref={arcRef}
            cx="100"
            cy="100"
            r="80"
            fill="none"
            stroke={arcColor}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${CIRCUMFERENCE} ${CIRCUMFERENCE}`}
            strokeDashoffset={CIRCUMFERENCE}
            className="threat-meter__arc"
            style={{
              filter: `drop-shadow(0 0 8px ${arcColor})`,
            }}
          />
        </svg>
        <div className="threat-meter__center">
          <span className={`threat-meter__score${animatedScore === null ? ' threat-meter__score--unavailable' : ''}`}>
            {animatedScore === null ? 'Unavailable' : animatedScore}
          </span>
          <span className="threat-meter__label">THREAT LEVEL</span>
        </div>
      </div>
      <ThreatBadge riskLevel={riskLevel} size="normal" />
    </figure>
  )
}
