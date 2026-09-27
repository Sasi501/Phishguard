import type { AnalyzeResponse, XaiEngineSignal } from '../types/api'
import { inputLabel } from './evidenceProvenance'
import './EvidenceMatrix.css'

interface EvidenceMatrixProps {
  result: AnalyzeResponse
}

type EvidenceRow = {
  engine: string
  input: string
  scope: string
  signal: string
  status: string
  source: string
}

function signalFor(signals: XaiEngineSignal[], source: string): XaiEngineSignal | undefined {
  return signals.find(signal => signal.source === source)
}

function formatSignal(signal?: XaiEngineSignal): string {
  if (!signal) return 'Signal unavailable'
  if (signal.match_status) return signal.match_status === 'MATCH' ? 'Match found' : 'No match'
  if (typeof signal.score === 'number' && Number.isFinite(signal.score)) return `${signal.score.toFixed(2)}%`
  return signal.reason || 'Signal unavailable'
}

function formatStatus(signal?: XaiEngineSignal, fallback = 'unavailable'): string {
  return signal?.status || fallback || 'unavailable'
}

export default function EvidenceMatrix({ result }: EvidenceMatrixProps) {
  const signals = result.xai?.engine_signals ?? []
  const redirect = result.redirect_analysis ?? result.xai?.redirect_analysis
  const redirectSignal: XaiEngineSignal | undefined = redirect
    ? {
        engine: 'Redirect Analysis',
        risk_level: result.ensemble_risk_level,
        status: redirect.resolution_state === 'completed' ? 'available' : redirect.resolution_state === 'blocked' ? 'restricted' : 'error',
        score_type: 'redirect_evidence',
        url_scope: 'original_to_final',
      }
    : undefined
  const rows: EvidenceRow[] = [
    {
      engine: 'URL ML',
      input: inputLabel('url_ml', signalFor(signals, 'url_ml')?.url_scope),
      scope: signalFor(signals, 'url_ml')?.url_scope || 'original URL',
      signal: formatSignal(signalFor(signals, 'url_ml')),
      status: formatStatus(signalFor(signals, 'url_ml'), result.engine_status?.url_ml?.status),
      source: 'URL ML engine signal',
    },
    {
      engine: 'NLP',
      input: inputLabel('nlp', signalFor(signals, 'nlp')?.url_scope),
      scope: signalFor(signals, 'nlp')?.url_scope || 'submitted text',
      signal: formatSignal(signalFor(signals, 'nlp')),
      status: formatStatus(signalFor(signals, 'nlp'), result.engine_status?.nlp?.status),
      source: 'NLP engine signal',
    },
    {
      engine: 'Vision',
      input: inputLabel('vision', signalFor(signals, 'vision')?.url_scope),
      scope: signalFor(signals, 'vision')?.url_scope || 'submitted image',
      signal: formatSignal(signalFor(signals, 'vision')),
      status: formatStatus(signalFor(signals, 'vision'), result.engine_status?.vision?.status),
      source: 'Vision engine signal',
    },
    {
      engine: 'Domain Intelligence',
      input: inputLabel('domain_intelligence', signalFor(signals, 'domain_intelligence')?.url_scope),
      scope: signalFor(signals, 'domain_intelligence')?.url_scope || 'final URL',
      signal: formatSignal(signalFor(signals, 'domain_intelligence')),
      status: formatStatus(signalFor(signals, 'domain_intelligence'), result.engine_status?.domain_intelligence?.status),
      source: 'Domain engine signal',
    },
    {
      engine: 'Threat Intelligence',
      input: inputLabel('threat_intelligence', signalFor(signals, 'threat_intelligence')?.url_scope),
      scope: signalFor(signals, 'threat_intelligence')?.url_scope || 'final URL',
      signal: formatSignal(signalFor(signals, 'threat_intelligence')),
      status: formatStatus(signalFor(signals, 'threat_intelligence'), result.engine_status?.threat_intelligence?.status),
      source: 'Threat-intelligence match signal',
    },
    {
      engine: 'Redirect Analysis',
      input: inputLabel('redirect', redirectSignal?.url_scope),
      scope: 'original → final',
      signal: redirect
        ? `${redirect.num_redirects} redirect${redirect.num_redirects === 1 ? '' : 's'} · ${redirect.resolution_state}`
        : 'Redirect evidence unavailable',
      status: formatStatus(redirectSignal),
      source: 'Redirect resolver evidence',
    },
  ]

  return (
    <section className="evidence-matrix glass-card" aria-labelledby="evidence-matrix-heading">
      <header className="evidence-matrix__header">
        <div>
          <p className="evidence-matrix__eyebrow">PROVENANCE MATRIX</p>
          <h2 id="evidence-matrix-heading">MULTI-MODAL EVIDENCE MATRIX</h2>
          <p>Individual engine signals are evidence inputs and are not the final ensemble score.</p>
        </div>
        <div className="evidence-matrix__final">
          <span>FINAL ENSEMBLE RISK</span>
          <strong>{result.ensemble_score_percent === null ? 'Unavailable' : `${result.ensemble_score_percent.toFixed(2)}%`}</strong>
          <small>{result.ensemble_risk_level}</small>
        </div>
      </header>
      <div className="evidence-matrix__url-note">
        URL ML uses the original URL. Domain and Threat Intelligence use the final URL when the resolver provides one.
        Redirect evidence preserves the original → intermediate → final chain.
      </div>
      <div className="evidence-matrix__table-wrap">
        <table className="evidence-matrix__table">
          <caption className="sr-only">Engine inputs, provenance scopes, signals, statuses, and evidence sources</caption>
          <thead>
            <tr><th>Engine</th><th>Input</th><th>Scope</th><th>Signal</th><th>Status</th><th>Evidence source</th></tr>
          </thead>
          <tbody>
            {rows.map(row => (
              <tr key={row.engine}>
                <th scope="row">{row.engine}</th>
                <td>{row.input}</td>
                <td>{row.scope.replaceAll('_', ' ')}</td>
                <td>{row.signal}</td>
                <td><span className={`evidence-matrix__status evidence-matrix__status--${row.status}`}>{row.status}</span></td>
                <td>{row.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
