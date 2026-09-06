import { useState } from 'react'
import type { ScanEntry } from '../types/api'
import { SIZES } from '../theme'
import ThreatBadge from './ThreatBadge'
import './ScanHistory.css'

interface ScanHistoryProps {
  entries: ScanEntry[]
  onSelect: (entry: ScanEntry) => void
}

function formatTimestamp(d: Date): string {
  return d.toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  })
}

function truncateUrl(url: string, max: number): string {
  return url.length > max ? url.slice(0, max) + '…' : url
}

export default function ScanHistory({ entries, onSelect }: ScanHistoryProps) {
  const [expanded, setExpanded] = useState(false)

  if (entries.length === 0) return null

  return (
    <section className="scan-history glass-card" aria-label="Scan history">
      <button
        type="button"
        className="scan-history__header"
        aria-expanded={expanded}
        aria-controls="scan-history-list"
        onClick={() => setExpanded(v => !v)}
      >
        <span className="scan-history__title">SCAN HISTORY ({entries.length})</span>
        <span className="scan-history__chevron" aria-hidden="true">{expanded ? '▲' : '▼'}</span>
      </button>

      <div
        id="scan-history-list"
        className={`scan-history__list${expanded ? ' scan-history__list--expanded' : ''}`}
        aria-live="polite"
      >
        {entries.map(entry => (
          <button
            key={entry.id}
            type="button"
            className="scan-history__entry"
            onClick={() => onSelect(entry)}
            aria-label={`View scan result for ${entry.url}, risk: ${entry.result.ensemble_risk_level}, score: ${(Math.round(entry.result.ensemble_score_percent * 10) / 10).toFixed(1)}%`}
          >
            <span className="scan-history__entry-url" title={entry.url}>
              {truncateUrl(entry.url, SIZES.urlTruncate)}
            </span>
            <span className="scan-history__entry-meta">
              <ThreatBadge riskLevel={entry.result.ensemble_risk_level} size="small" />
              <span className="scan-history__entry-score">
                {(Math.round(entry.result.ensemble_score_percent * 10) / 10).toFixed(1)}%
              </span>
              <span className="scan-history__entry-time">
                {formatTimestamp(entry.timestamp)}
              </span>
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
