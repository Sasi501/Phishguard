import type { RedirectAnalysis as RedirectAnalysisData, RedirectHop } from '../types/api'
import './RedirectAnalysis.css'

interface RedirectAnalysisProps {
  analysis?: RedirectAnalysisData
}

const STATE_LABELS: Record<string, string> = {
  completed: 'Resolution completed',
  blocked: 'Destination blocked',
  failed: 'Resolution failed',
  loop: 'Redirect loop detected',
  limit_exceeded: 'Redirect limit reached',
  unavailable: 'Resolution unavailable',
}

function stateTone(state: string): string {
  if (state === 'completed') return 'completed'
  if (state === 'blocked' || state === 'loop' || state === 'limit_exceeded') return 'warning'
  return 'failed'
}

function hopLabel(hop: RedirectHop, index: number, total: number): string {
  if (index === 0) return 'Original URL'
  if (index === total - 1 && hop.status_code === 200) return 'Final destination'
  return `Redirect hop ${index}`
}

export default function RedirectAnalysis({ analysis }: RedirectAnalysisProps) {
  if (!analysis) return null

  const state = analysis.resolution_state || 'unavailable'
  const tone = stateTone(state)
  const chain = analysis.redirect_chain ?? []
  const hops = chain.length > 0
    ? chain
    : [{ url: analysis.original_url, status_code: null } satisfies RedirectHop]

  return (
    <section className="redirect-analysis glass-card" aria-labelledby="redirect-analysis-heading">
      <div className="redirect-analysis__header">
        <div>
          <p className="redirect-analysis__eyebrow">URL PATH EVIDENCE</p>
          <h2 id="redirect-analysis-heading" className="redirect-analysis__title">REDIRECT ANALYSIS</h2>
        </div>
        <span className={`redirect-analysis__state redirect-analysis__state--${tone}`}>
          <span className="redirect-analysis__state-dot" aria-hidden="true" />
          {STATE_LABELS[state] ?? state.replaceAll('_', ' ')}
        </span>
      </div>

      <div className="redirect-analysis__summary">
        <div>
          <span className="redirect-analysis__label">Redirects</span>
          <strong>{analysis.num_redirects}</strong>
        </div>
        <div>
          <span className="redirect-analysis__label">Meta refresh</span>
          <strong>{analysis.has_meta_refresh ? 'Detected' : 'None detected'}</strong>
        </div>
        <div>
          <span className="redirect-analysis__label">Chain signal</span>
          <strong className={analysis.suspicious_redirects ? 'redirect-analysis__warning-text' : ''}>
            {analysis.suspicious_redirects ? 'Suspicious' : 'No suspicious indicator'}
          </strong>
        </div>
      </div>

      <div className="redirect-analysis__chain" aria-label="Redirect chain">
        {hops.map((hop, index) => (
          <div className="redirect-analysis__hop" key={`${hop.url}-${index}`}>
            <div className="redirect-analysis__node" aria-hidden="true">
              <span />
            </div>
            <div className="redirect-analysis__hop-content">
              <div className="redirect-analysis__hop-heading">
                <span className="redirect-analysis__hop-label">{hopLabel(hop, index, hops.length)}</span>
                {hop.status_code !== null && hop.status_code !== undefined && (
                  <span className="redirect-analysis__status">HTTP {hop.status_code}</span>
                )}
              </div>
              <code>{hop.url}</code>
              {hop.note && <span className="redirect-analysis__note">{hop.note.replaceAll('_', ' ')}</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="redirect-analysis__destination">
        <span className="redirect-analysis__label">Final resolved URL</span>
        <code>{analysis.final_url}</code>
      </div>

      {(analysis.loop_detected || state === 'limit_exceeded' || state === 'blocked' || state === 'failed' || state === 'unavailable') && (
        <div className={`redirect-analysis__notice redirect-analysis__notice--${tone}`} role="status">
          {analysis.loop_detected && 'Resolution stopped after a repeated URL was detected.'}
          {!analysis.loop_detected && state === 'limit_exceeded' && 'Resolution stopped because the redirect limit was reached.'}
          {!analysis.loop_detected && state === 'blocked' && 'A destination was blocked by SSRF protection.'}
          {!analysis.loop_detected && (state === 'failed' || state === 'unavailable') && 'The chain could not be fully resolved; the available result is shown as evidence.'}
        </div>
      )}

      {analysis.suspicious_redirects && (
        <p className="redirect-analysis__disclaimer">
          Suspicious redirect chain is supporting evidence only. It is not a final phishing verdict; review the ensemble risk assessment separately.
        </p>
      )}

      {analysis.errors.length > 0 && (
        <details className="redirect-analysis__errors">
          <summary>Resolution limitations ({analysis.errors.length})</summary>
          <ul>
            {analysis.errors.map((error, index) => <li key={`${error}-${index}`}>{error}</li>)}
          </ul>
        </details>
      )}
    </section>
  )
}
