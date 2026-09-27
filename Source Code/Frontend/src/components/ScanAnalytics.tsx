import type { ScanEntry } from '../types/api'
import './ScanAnalytics.css'

interface ScanAnalyticsProps {
  entries: ScanEntry[]
}

type RiskBucket = 'safe' | 'suspicious' | 'phishing' | 'partial' | 'failed'

function bucketFor(entry: ScanEntry): RiskBucket {
  if (entry.result.analysis_status === 'failed') return 'failed'
  if (entry.result.analysis_status === 'partial' || entry.result.analysis_status === 'restricted') return 'partial'
  const risk = entry.result.ensemble_risk_level
  if (risk === 'safe') return 'safe'
  if (risk === 'suspicious' || risk === 'medium' || risk === 'high') return 'suspicious'
  if (risk === 'phishing') return 'phishing'
  return 'partial'
}

function scoreText(entry: ScanEntry): string {
  const score = entry.result.ensemble_score_percent
  return typeof score === 'number' && Number.isFinite(score) ? `${score.toFixed(2)}%` : 'Unavailable'
}

function statusText(entry: ScanEntry): string {
  return entry.result.analysis_status || 'status unavailable'
}

export default function ScanAnalytics({ entries }: ScanAnalyticsProps) {
  const counts = entries.reduce<Record<RiskBucket, number>>((acc, entry) => {
    const bucket = bucketFor(entry)
    acc[bucket] += 1
    return acc
  }, { safe: 0, suspicious: 0, phishing: 0, partial: 0, failed: 0 })
  const categories = [
    ['safe', 'Safe'], ['suspicious', 'Suspicious'], ['phishing', 'Phishing'], ['partial', 'Partial / Restricted'], ['failed', 'Failed'],
  ].filter(([key]) => counts[key as RiskBucket] > 0)
  const engineKeys = ['url_ml', 'nlp', 'vision', 'domain_intelligence', 'threat_intelligence', 'redirect']
  const engineLabels: Record<string, string> = {
    url_ml: 'URL ML', nlp: 'NLP', vision: 'Vision', domain_intelligence: 'Domain', threat_intelligence: 'Threat Intelligence', redirect: 'Redirect',
  }
  const hasHistoricalEngineData = entries.some(entry => Boolean(entry.result.engine_status || entry.result.xai?.engine_status))

  return (
    <section className="scan-analytics glass-card" aria-labelledby="scan-analytics-heading">
      <header className="scan-analytics__header">
        <div>
          <p className="scan-analytics__eyebrow">SESSION ANALYTICS</p>
          <h2 id="scan-analytics-heading">SCAN ANALYTICS</h2>
          <p>Analytics are based on available scan-session records. History is held in React state and is not persistent.</p>
        </div>
        <strong className="scan-analytics__total">{entries.length}<span>Total Scans</span></strong>
      </header>
      {entries.length === 0 ? (
        <div className="scan-analytics__empty">No scan data available yet.</div>
      ) : (
        <>
          <div className="scan-analytics__summary">
            {categories.map(([key, label]) => <div key={key}><span>{label}</span><strong>{counts[key as RiskBucket]}</strong></div>)}
          </div>
          <div className="scan-analytics__grid">
            <section className="scan-analytics__card" aria-labelledby="risk-distribution-heading">
              <h3 id="risk-distribution-heading">Risk Distribution</h3>
              <div className="scan-analytics__bars">
                {categories.map(([key, label]) => (
                  <div className="scan-analytics__bar-row" key={key}>
                    <span>{label}</span>
                    <div className="scan-analytics__bar-track"><i style={{ width: `${counts[key as RiskBucket] / entries.length * 100}%` }} /></div>
                    <strong>{counts[key as RiskBucket]}</strong>
                  </div>
                ))}
              </div>
              <p className="scan-analytics__muted">Bars represent counts in the current session only.</p>
            </section>
            <section className="scan-analytics__card" aria-labelledby="engine-summary-heading">
              <h3 id="engine-summary-heading">Historical Engine Availability</h3>
              {hasHistoricalEngineData ? (
                <ul className="scan-analytics__engine-list">
                  {engineKeys.map(key => {
                    const observed = entries.flatMap(entry => {
                      const status = entry.result.engine_status?.[key]?.status || entry.result.xai?.engine_status?.[key]?.status
                      return status ? [status] : []
                    })
                    return <li key={key}><span>{engineLabels[key]}</span><strong>{observed.length ? [...new Set(observed)].join(', ') : 'Not stored'}</strong></li>
                  })}
                </ul>
              ) : <p className="scan-analytics__empty">Historical engine availability is not stored.</p>}
            </section>
          </div>
          <section className="scan-analytics__timeline" aria-labelledby="timeline-heading">
            <h3 id="timeline-heading">Recent Scan Timeline</h3>
            <div className="scan-analytics__timeline-table-wrap">
              <table className="scan-analytics__timeline-table">
                <thead><tr><th>Time</th><th>URL / Domain</th><th>Final risk</th><th>Score</th><th>Analysis status</th></tr></thead>
                <tbody>{[...entries].reverse().map(entry => (
                  <tr key={entry.id}>
                    <td>{entry.timestamp instanceof Date && Number.isFinite(entry.timestamp.getTime()) ? entry.timestamp.toLocaleString() : 'Timestamp unavailable'}</td>
                    <td title={entry.url}>{entry.url || 'URL unavailable'}</td>
                    <td>{entry.result.ensemble_risk_level || 'Unknown'}</td>
                    <td>{scoreText(entry)}</td>
                    <td>{statusText(entry)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </section>
  )
}
