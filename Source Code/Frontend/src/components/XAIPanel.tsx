import { useState } from 'react'
import { parseUrlAnatomy } from './URLAnatomy'
import type { AnalysisStatus, EngineAvailability, XaiEvidence } from '../types/api'
import { inputLabel } from './evidenceProvenance'
import './XAIPanel.css'

interface XAIPanelProps {
  summary?: string
  reasons?: string[]
  xai?: XaiEvidence | null
  ensembleScore?: number | null
  ensembleRiskLevel?: string
  submittedUrl?: string
  receivedAt?: Date
  submittedText?: boolean
  submittedImage?: boolean
  analysisStatus?: AnalysisStatus
  engineStatus?: Record<string, EngineAvailability>
}

type EvidenceRecord = Record<string, unknown>

function isRecord(value: unknown): value is EvidenceRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function records(value: unknown): EvidenceRecord[] {
  return Array.isArray(value) ? value.filter(isRecord) : []
}

function text(value: unknown, fallback = 'Not available'): string {
  return typeof value === 'string' && value.trim() ? value : fallback
}

function numeric(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function formatScope(scope: unknown): string {
  return typeof scope === 'string' && scope
    ? scope.replaceAll('_', ' ')
    : 'Not provided'
}

function signalStatus(signal: EvidenceRecord): string {
  if (typeof signal.status === 'string' && signal.status) return signal.status
  if (numeric(signal.score) !== null || typeof signal.match_status === 'string') return 'available'
  return 'unavailable'
}

function engineLabel(key: string): string {
  const labels: Record<string, string> = {
    url_ml: 'URL ML',
    nlp: 'NLP / Text Intelligence',
    vision: 'Vision Intelligence',
    domain_intelligence: 'Domain Intelligence',
    threat_intelligence: 'Threat Intelligence',
    redirect: 'Redirect Resolver',
  }
  return labels[key] ?? key.replaceAll('_', ' ')
}

function engineTitle(signal: EvidenceRecord): string {
  switch (signal.source) {
    case 'url_ml': return 'URL ML Signal'
    case 'nlp': return 'NLP Signal'
    case 'vision': return 'Vision Signal'
    case 'domain_intelligence': return 'Domain Risk Signal · Final URL'
    case 'threat_intelligence':
      return signal.url_scope === 'original_url'
        ? 'Threat Intelligence Signal · Submitted URL'
        : 'Threat Intelligence Signal · Final URL'
    default: return text(signal.engine, 'Engine Signal')
  }
}

function methodLabel(method: unknown, source: unknown): string {
  if (method === 'shap') return 'SHAP attribution'
  if (method === 'catboost_feature_importance') return 'CatBoost feature importance'
  if (method === 'grad_cam') return 'Grad-CAM activation'
  if (source === 'vision') return 'Attribution method unavailable'
  return 'Impact method unavailable'
}

function riskTone(level: unknown): string {
  if (typeof level !== 'string') return 'unknown'
  const normalized = level.toLowerCase()
  if (normalized === 'safe' || normalized === 'low') return 'safe'
  if (normalized === 'medium' || normalized === 'suspicious') return 'caution'
  if (normalized === 'high' || normalized === 'phishing') return 'danger'
  return 'unknown'
}

function EvidenceList({ items, emptyText }: { items: EvidenceRecord[]; emptyText: string }) {
  if (items.length === 0) {
    return <p className="xai-panel__empty">{emptyText}</p>
  }

  return (
    <ul className="xai-panel__factor-list">
      {items.map((item, index) => (
        <li key={`${text(item.title, 'evidence')}-${index}`}>
          <strong>{text(item.title, 'Evidence')}</strong>
          <p>{text(item.description, 'Description not provided.')}</p>
          {item.source === 'url' && (
            <p className="xai-panel__source-note">
              Individual URL ML evidence; this is not the final ensemble assessment.
            </p>
          )}
          {typeof item.source === 'string' && (
            <span className="xai-panel__source">Source: {item.source.replaceAll('_', ' ')}</span>
          )}
        </li>
      ))}
    </ul>
  )
}

export default function XAIPanel({
  summary,
  reasons = [],
  xai,
  ensembleScore,
  ensembleRiskLevel,
  submittedUrl,
  receivedAt,
  submittedText,
  submittedImage,
  analysisStatus,
  engineStatus: responseEngineStatus,
}: XAIPanelProps) {
  const [copyState, setCopyState] = useState('')
  const [viewMode, setViewMode] = useState<'user' | 'analyst'>('user')
  const [technicalExpanded, setTechnicalExpanded] = useState(false)
  const evidence = isRecord(xai) ? xai : null
  const riskFactors = records(evidence?.risk_factors)
  const safetyFactors = records(evidence?.safety_factors)
  const engineSignals = records(evidence?.engine_signals)
  const urlMlSignal = engineSignals.find(signal => signal.source === 'url_ml' && signal.score_type === 'engine_signal')
  const urlMlEvidence = isRecord(evidence?.url_ml_evidence) ? evidence.url_ml_evidence : null
  const urlMlSignalScore = numeric(urlMlSignal?.score)
  const rawUrlProbability = numeric(urlMlEvidence?.raw_model_probability_percent)
  const urlSignalAdjustment = text(urlMlEvidence?.engine_signal_adjustment, '')
  const featureImpacts = records(evidence?.feature_importance)
  const redirectEvidence = records(evidence?.redirect_evidence)
  const redirectAnalysis = isRecord(evidence?.redirect_analysis) ? evidence.redirect_analysis : null
  const redirectHops = records(redirectAnalysis?.redirect_chain)
  const redirectBlocked = redirectAnalysis?.resolution_state === 'blocked'
  const engineStatus = isRecord(responseEngineStatus)
    ? responseEngineStatus
    : isRecord(evidence?.engine_status)
      ? evidence.engine_status
      : {}
  const statusEntries = Object.entries(engineStatus).filter(([, value]) => isRecord(value))
  const finalUrl = text(redirectAnalysis?.final_url, '')
  const tiSignal = engineSignals.find(signal => signal.source === 'threat_intelligence')
  const threatUrl = tiSignal?.url_scope === 'original_url' ? text(submittedUrl) : finalUrl
  const scoreCandidate = numeric(ensembleScore)
  const validScore = scoreCandidate !== null && scoreCandidate >= 0 && scoreCandidate <= 100
    ? scoreCandidate
    : null
  const meterWidth = validScore === null ? 0 : Math.max(0, Math.min(100, validScore))
  const maxImpact = Math.max(0, ...featureImpacts.map(item => Math.abs(numeric(item.impact) ?? 0)))
  const anatomy = parseUrlAnatomy(submittedUrl)
  const domainStatus = isRecord(engineStatus.domain_intelligence) ? engineStatus.domain_intelligence : null
  const tiStatus = isRecord(engineStatus.threat_intelligence) ? engineStatus.threat_intelligence : null
  const domainDetails = isRecord(evidence?.domain_intelligence) ? evidence.domain_intelligence : null
  const domainMetadata = isRecord(domainDetails?.metadata) ? domainDetails.metadata : null
  const tiDetails = isRecord(evidence?.threat_intelligence) ? evidence.threat_intelligence : null
  const domainEvidence = [
    ...riskFactors,
    ...safetyFactors,
  ].filter(item => item.source === 'domain')
  const threatEvidence = [
    ...riskFactors,
    ...safetyFactors,
  ].filter(item => item.source === 'threat_intelligence')
  const limitations = statusEntries.flatMap(([key, value]) => {
    if (value.applicable === false || value.status === 'available') return []
    return [{
      key,
      label: engineLabel(key),
      status: text(value.status, 'unavailable'),
      reason: text(value.reason, 'No further limitation details were returned.'),
      unavailableSources: Array.isArray(value.unavailable_sources)
        ? value.unavailable_sources.filter((source): source is string => typeof source === 'string')
        : [],
    }]
  })
  const unavailableFeeds = Array.isArray(tiDetails?.unavailable_sources)
    ? tiDetails.unavailable_sources.filter((source): source is string => typeof source === 'string')
    : tiStatus && Array.isArray(tiStatus.unavailable_sources)
      ? tiStatus.unavailable_sources.filter((source): source is string => typeof source === 'string')
      : []
  const domainIsRestricted = redirectBlocked || domainStatus?.status === 'restricted' || domainDetails?.status === 'restricted'
  const engineStatusBySource = (source: unknown) => {
    const key = source === 'url_ml' ? 'url_ml'
      : source === 'nlp' ? 'nlp'
        : source === 'vision' ? 'vision'
          : source === 'domain_intelligence' ? 'domain_intelligence'
            : source === 'threat_intelligence' ? 'threat_intelligence'
              : null
    return key && isRecord(engineStatus[key]) ? text(engineStatus[key].status, 'unavailable') : null
  }

  const copySubmittedUrl = async () => {
    if (!submittedUrl || !navigator.clipboard?.writeText) {
      setCopyState('Copy is unavailable in this browser.')
      return
    }
    try {
      await navigator.clipboard.writeText(submittedUrl)
      setCopyState('Submitted URL copied.')
    } catch {
      setCopyState('Could not copy the submitted URL.')
    }
  }

  const receivedLabel = receivedAt instanceof Date && Number.isFinite(receivedAt.getTime())
    ? receivedAt.toLocaleString()
    : 'Not recorded'
  const explanation = text(evidence?.summary, text(summary, 'No explanation was returned for this scan.'))

  return (
    <section className="xai-panel glass-card" aria-labelledby="xai-panel-heading">
      <header className="xai-panel__header">
        <div>
          <p className="xai-panel__eyebrow">EXPLAINABLE AI</p>
          <h2 id="xai-panel-heading" className="xai-panel__heading">INVESTIGATION CENTER</h2>
          <p className="xai-panel__intro">
            Review the ensemble assessment separately from individual engine evidence and supporting signals.
          </p>
        </div>
        <div className="xai-panel__header-actions">
          <div className="xai-panel__view-toggle" role="group" aria-label="XAI detail view">
            <button
              type="button"
              aria-pressed={viewMode === 'user'}
              onClick={() => {
                setViewMode('user')
                setTechnicalExpanded(false)
              }}
            >
              User View
            </button>
            <button
              type="button"
              aria-pressed={viewMode === 'analyst'}
              onClick={() => {
                setViewMode('analyst')
                setTechnicalExpanded(true)
              }}
            >
              Analyst View
            </button>
          </div>
          {submittedUrl && (
            <button className="xai-panel__copy" type="button" onClick={copySubmittedUrl}>
              Copy submitted URL
            </button>
          )}
        </div>
      </header>
      {copyState && <p className="xai-panel__copy-state" role="status">{copyState}</p>}
      {analysisStatus && analysisStatus !== 'complete' && (
        <p className="xai-panel__availability-notice" role="status">
          {analysisStatus === 'failed'
            ? 'A final numerical assessment could not be produced from the available engine scores.'
            : 'Some applicable evidence was unavailable or restricted. Other engines continued, and network restriction is not itself evidence of phishing.'}
        </p>
      )}

      <section className="xai-panel__verdict" aria-label="Final ensemble assessment">
        <div className="xai-panel__verdict-main">
          <div>
            <span className="xai-panel__label">FINAL ENSEMBLE RISK SCORE</span>
            <p className="xai-panel__score">
              {validScore === null ? 'Unavailable' : `${validScore.toFixed(2)}%`}
            </p>
          </div>
          <span className={`xai-panel__risk xai-panel__risk--${riskTone(ensembleRiskLevel)}`}>
            {text(ensembleRiskLevel, 'Risk level unavailable').toUpperCase()}
          </span>
        </div>
        {validScore !== null && (
          <div
            className="xai-panel__ensemble-meter"
            role="meter"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={meterWidth}
            aria-label={`Final ensemble risk score ${validScore.toFixed(2)} percent`}
          >
            <span style={{ width: `${meterWidth}%` }} />
          </div>
        )}
        <dl className="xai-panel__scan-meta">
          <div>
            <dt>Submitted URL</dt>
            <dd>{text(submittedUrl)}</dd>
          </div>
          <div>
            <dt>Result received</dt>
            <dd>{receivedLabel}</dd>
          </div>
        </dl>
        {redirectAnalysis?.resolution_state === 'blocked' && (
          <p className="xai-panel__notice">
            {text(redirectAnalysis?.blocked_reason, 'Unsafe network destination blocked by URL safety validation.')} This is not the final phishing verdict.
          </p>
        )}
        <p className="xai-panel__separation-note">
          This is the backend-reported ensemble result. Engine signals below are individual inputs/evidence, not this score.
        </p>
        {urlMlSignal && (
          <div className="xai-panel__url-ml-evidence">
            <div>
              <span className="xai-panel__label">URL ML ENGINE SIGNAL</span>
              <strong>{urlMlSignalScore === null ? 'Unavailable' : `${urlMlSignalScore.toFixed(2)}%`}</strong>
              <p>The individual URL signal used as engine evidence; it is not the final ensemble risk score.</p>
            </div>
            {rawUrlProbability !== null && (
              <div>
                <span className="xai-panel__label">RAW URL-MODEL PROBABILITY</span>
                <strong>{rawUrlProbability.toFixed(2)}%</strong>
                <p>
                  Raw model inference before fusion preparation
                  {urlSignalAdjustment ? `; ${urlSignalAdjustment.replaceAll('_', ' ')} was applied to the engine signal` : ''}.
                  This is not a feature-importance or SHAP contribution.
                </p>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="xai-panel__section">
        <h3>Why This Result?</h3>
        <p className="xai-panel__summary">{explanation}</p>
        {!evidence && (
          <p className="xai-panel__notice">Structured XAI evidence is unavailable for this result.</p>
        )}
        {reasons.length > 0 && (
          <ul className="xai-panel__plain-list">
            {reasons.map((reason, index) => <li key={`${reason}-${index}`}>{reason}</li>)}
          </ul>
        )}
      </section>

      <div className="xai-panel__factor-grid">
        <section className="xai-panel__section">
          <h3>Risk Factors</h3>
          <EvidenceList items={riskFactors} emptyText={evidence ? 'No risk factors were reported.' : 'Risk factors unavailable.'} />
        </section>
        <section className="xai-panel__section">
          <h3>Safety / Supporting Factors</h3>
          <EvidenceList items={safetyFactors} emptyText={evidence ? 'No supporting factors were reported.' : 'Supporting factors unavailable.'} />
        </section>
      </div>

      {viewMode === 'analyst' && (
        <section className="xai-panel__advanced">
          <button
            className="xai-panel__advanced-toggle"
            type="button"
            aria-expanded={technicalExpanded}
            aria-controls="xai-technical-evidence"
            onClick={() => setTechnicalExpanded(expanded => !expanded)}
          >
            {technicalExpanded ? 'Collapse technical evidence' : 'Expand technical evidence'}
          </button>
          <div id="xai-technical-evidence" hidden={!technicalExpanded}>
        <div className="xai-panel__advanced-content">
          <section className="xai-panel__section">
            <h3>URL Forensics</h3>
            {anatomy.isValid ? (
              <>
                <p className="xai-panel__url-structure">
                  <span>{anatomy.protocol.toUpperCase()}</span>
                  <strong>{anatomy.subdomain ? `${anatomy.subdomain}.` : ''}{anatomy.domain}{anatomy.tld ? `.${anatomy.tld}` : ''}</strong>
                  <span>{anatomy.port !== 'none' ? `:${anatomy.port}` : ''}{anatomy.path}</span>
                  {anatomy.query !== 'none' && <span>{anatomy.query}</span>}
                  {anatomy.fragment !== 'none' && <span>#{anatomy.fragment}</span>}
                </p>
                <dl className="xai-panel__scan-meta">
                  <div><dt>Protocol</dt><dd>{anatomy.protocol.toUpperCase()}</dd></div>
                  <div><dt>Hostname</dt><dd>{new URL(anatomy.rawUrl).hostname}</dd></div>
                  <div><dt>Subdomain</dt><dd>{anatomy.subdomain || 'None'}</dd></div>
                  <div><dt>Domain</dt><dd>{anatomy.domain}</dd></div>
                  <div><dt>TLD</dt><dd>{anatomy.tld || 'None'}</dd></div>
                  <div><dt>Port</dt><dd>{anatomy.port}</dd></div>
                  <div><dt>Path</dt><dd>{anatomy.path}</dd></div>
                  <div><dt>Query</dt><dd>{anatomy.query}</dd></div>
                  <div><dt>Fragment</dt><dd>{anatomy.fragment}</dd></div>
                  <div><dt>URL length</dt><dd>{anatomy.urlLength}</dd></div>
                  <div><dt>Subdomain count</dt><dd>{anatomy.subdomainCount}</dd></div>
                  <div><dt>HTTPS</dt><dd>{anatomy.isHttps ? 'Yes' : 'No'}</dd></div>
                </dl>
              </>
            ) : (
              <p className="xai-panel__empty">{anatomy.error || 'URL structure unavailable.'}</p>
            )}
          </section>

          <section className="xai-panel__section">
            <h3>Individual Engine Signals</h3>
            <p className="xai-panel__section-note">
              Individual signals are shown as returned by the API; they are evidence inputs, not per-engine contributions to the final score.
            </p>
            {engineSignals.length === 0 ? (
              <p className="xai-panel__empty">Engine signal evidence unavailable.</p>
            ) : (
              <div className="xai-panel__signal-grid">
                {engineSignals.map((signal, index) => {
                  const source = signal.source
                  const score = numeric(signal.score)
                  const isMatch = signal.score_type === 'match_signal'
                  const omittedInput =
                    (source === 'nlp' && submittedText === false) ||
                    (source === 'vision' && submittedImage === false && signal.url_scope === 'not_submitted')
                  const matchStatus = text(signal.match_status, '')
                  const barWidth = score === null ? 0 : Math.max(0, Math.min(100, score))
                  const signalState = signalStatus(signal)
                  const signalStatusLabel = signalState.replaceAll('_', ' ')
                  return (
                    <article className="xai-panel__signal" key={`${text(signal.engine, 'signal')}-${index}`}>
                      <div className="xai-panel__signal-heading">
                        <h4>{engineTitle(signal)}</h4>
                        {isMatch ? (
                          <span className="xai-panel__signal-value">{matchStatus || 'Match status unavailable'}</span>
                        ) : omittedInput ? (
                          <span className="xai-panel__signal-value">Not submitted</span>
                        ) : signalState !== 'available' ? (
                          <span className="xai-panel__signal-value">{signalStatusLabel}</span>
                        ) : (
                          <span className="xai-panel__signal-value">
                            {score === null ? 'Status unavailable' : `${score.toFixed(2)}%`}
                          </span>
                        )}
                      </div>
                      {!isMatch && !omittedInput && score !== null && (
                        <div className="xai-panel__signal-meter" aria-hidden="true">
                          <span style={{ width: `${barWidth}%` }} />
                        </div>
                      )}
                      <dl className="xai-panel__signal-meta">
                        <div><dt>Status</dt><dd>{omittedInput ? 'Not submitted' : signalStatusLabel}</dd></div>
                        <div><dt>Input</dt><dd>{inputLabel(source, signal.url_scope)}</dd></div>
                        <div><dt>Reported risk level</dt><dd>{text(signal.risk_level)}</dd></div>
                        <div><dt>Source</dt><dd>{text(source)}</dd></div>
                        <div><dt>Input scope</dt><dd>{formatScope(signal.url_scope)}</dd></div>
                        {Array.isArray(signal.sources) && signal.sources.length > 0 && (
                          <div><dt>Reported sources</dt><dd>{signal.sources.filter(item => typeof item === 'string').join(', ') || 'Not provided'}</dd></div>
                        )}
                      </dl>
                      {omittedInput && (
                        <p className="xai-panel__notice">No {source === 'nlp' ? 'text' : 'image'} input was submitted for this scan.</p>
                      )}
                      {signalState !== 'available' && !omittedInput && (
                        <p className="xai-panel__notice">{text(signal.reason, 'No valid score was reported for this engine.')}</p>
                      )}
                      {signalState === 'available' && typeof signal.reason === 'string' && (
                        <p className="xai-panel__section-note">{signal.reason}</p>
                      )}
                      {isMatch && (
                        <p className="xai-panel__notice">
                          Match status is a threat-intelligence signal, not a phishing probability.
                        </p>
                      )}
                    </article>
                  )
                })}
              </div>
            )}
          </section>

          <section className="xai-panel__section">
            <h3>Feature Importance and Attribution</h3>
            <p className="xai-panel__section-note">
              Each value is labeled with its backend-reported method. Bar widths are scaled only for display; they are not percentages or ensemble contributions.
            </p>
            {featureImpacts.length === 0 ? (
              <p className="xai-panel__empty">Feature attribution evidence unavailable.</p>
            ) : (
              <>
                {featureImpacts.some(item => item.method === 'grad_cam') && (
                  <p className="xai-panel__notice">
                    Grad-CAM values are model activations. The current backend uses conceptual labels for highlighted areas; they do not confirm a detected logo, form, or specific webpage element.
                  </p>
                )}
                <ul className="xai-panel__feature-list">
                  {featureImpacts.map((item, index) => {
                    const impact = numeric(item.impact)
                    const width = impact === null || maxImpact === 0 ? 0 : Math.abs(impact) / maxImpact * 100
                    return (
                      <li key={`${text(item.feature, 'feature')}-${index}`}>
                        <div className="xai-panel__feature-head">
                          <strong>{text(item.feature, 'Feature')}</strong>
                          <span>{impact === null ? 'Value unavailable' : `${impact > 0 ? '+' : ''}${impact}`}</span>
                        </div>
                        <div className="xai-panel__feature-meter" aria-hidden="true">
                          <span style={{ width: `${width}%` }} />
                        </div>
                        <p>
                          {methodLabel(item.method, item.source)} · Source: {text(item.source)}
                          {typeof item.url_scope === 'string' ? ` · Input scope: ${formatScope(item.url_scope)}` : ''}
                          {item.value !== null && item.value !== undefined ? ` · Feature value: ${String(item.value)}` : ''}
                        </p>
                      </li>
                    )
                  })}
                </ul>
              </>
            )}
          </section>

          <section className="xai-panel__section">
            <h3>{domainIsRestricted ? 'Domain Intelligence · Network Evidence Restricted' : 'Domain Intelligence · Final URL'}</h3>
            <p className="xai-panel__url">
              {domainIsRestricted
                ? 'Network-based domain metadata was restricted for this scan; the response does not confirm that metadata was collected for the final URL.'
                : text(domainDetails?.final_url, finalUrl || 'Final URL unavailable in the response.')}
            </p>
            {domainIsRestricted && (
              <p className="xai-panel__notice">
                {text(domainStatus?.reason, text(domainDetails?.reason, 'Network-based domain inspection was restricted.'))}
                {' '}This restriction is not itself evidence of phishing.
              </p>
            )}
            {!domainIsRestricted && domainDetails && (
              <>
                <dl className="xai-panel__signal-meta">
                  <div><dt>Domain risk level</dt><dd>{text(domainDetails.domain_risk_level)}</dd></div>
                  <div><dt>Domain risk score (raw)</dt><dd>{numeric(domainDetails.domain_score)?.toString() ?? 'Unavailable'}</dd></div>
                </dl>
                {domainMetadata && (
                  <dl className="xai-panel__scan-meta">
                    <div><dt>Hostname</dt><dd>{text(domainMetadata.domain)}</dd></div>
                    <div><dt>Registrable domain</dt><dd>{text(domainMetadata.registrable_domain)}</dd></div>
                    <div><dt>WHOIS age</dt><dd>{numeric(domainMetadata.age_days) === null ? 'Unavailable' : `${numeric(domainMetadata.age_days)} days`}</dd></div>
                    <div><dt>SSL</dt><dd>{domainMetadata.ssl_valid === true ? 'Valid' : domainMetadata.ssl_valid === false ? 'Not valid / unavailable' : 'Unavailable'}</dd></div>
                    <div><dt>SSL issuer</dt><dd>{text(domainMetadata.ssl_issuer)}</dd></div>
                    <div><dt>Resolved IPs</dt><dd>{Array.isArray(domainMetadata.resolved_ips) ? domainMetadata.resolved_ips.join(', ') || 'None reported' : 'Unavailable'}</dd></div>
                    <div><dt>MX records</dt><dd>{Array.isArray(domainMetadata.mx_records) ? domainMetadata.mx_records.join(', ') || 'None reported' : 'Unavailable'}</dd></div>
                    <div><dt>Reverse DNS</dt><dd>{text(domainMetadata.rdns)}</dd></div>
                  </dl>
                )}
                {typeof domainMetadata?.error === 'string' && (
                  <p className="xai-panel__notice">Metadata lookup note: {domainMetadata.error}</p>
                )}
                {typeof domainMetadata?.ssl_error === 'string' && (
                  <p className="xai-panel__notice">SSL lookup note: {domainMetadata.ssl_error}</p>
                )}
              </>
            )}
            <EvidenceList
              items={domainEvidence}
              emptyText={domainIsRestricted ? 'Network evidence restricted.' : evidence ? 'No domain evidence factors were reported.' : 'Domain evidence unavailable.'}
            />
          </section>

          <section className="xai-panel__section">
            <h3>
              {tiSignal?.url_scope === 'original_url'
                ? 'Threat Intelligence · Submitted URL'
                : redirectBlocked
                  ? 'Threat Intelligence · Restricted'
                  : 'Threat Intelligence · Final URL'}
            </h3>
            <p className="xai-panel__url">{threatUrl || 'Threat-intelligence URL scope unavailable in the response.'}</p>
            <dl className="xai-panel__signal-meta">
              <div><dt>Lookup status</dt><dd>{text(tiDetails?.status, text(tiStatus?.status, 'unavailable'))}</dd></div>
              <div><dt>Reported matches</dt><dd>{numeric(tiDetails?.ti_hits)?.toString() ?? 'Unavailable'}</dd></div>
              <div><dt>Exact URL match</dt><dd>{typeof tiDetails?.is_exact_url_match === 'boolean' ? (tiDetails.is_exact_url_match ? 'Yes' : 'No') : 'Not reported'}</dd></div>
              <div><dt>Matched sources</dt><dd>{Array.isArray(tiDetails?.ti_sources) ? tiDetails.ti_sources.filter((source): source is string => typeof source === 'string').join(', ') || 'None reported' : 'Unavailable'}</dd></div>
            </dl>
            {text(tiDetails?.reason, text(tiStatus?.reason, '')) && (
              <p className="xai-panel__notice">{text(tiDetails?.reason, text(tiStatus?.reason, ''))}</p>
            )}
            {unavailableFeeds.length > 0 && (
              <p className="xai-panel__notice">
                Unavailable TI feeds: {unavailableFeeds.map(source => source.replaceAll('_', ' ')).join(', ')}.
              </p>
            )}
            <EvidenceList
              items={threatEvidence}
              emptyText={text(tiDetails?.status, text(tiStatus?.status, 'unavailable')) === 'unavailable'
                ? 'Threat intelligence unavailable for this scan.'
                : evidence ? 'No threat-intelligence evidence factors were reported.' : 'Threat-intelligence evidence unavailable.'}
            />
            {engineSignals.filter(signal => signal.source === 'threat_intelligence').map((signal, index) => (
              <p className="xai-panel__notice" key={`ti-status-${index}`}>
                API-reported match status: {text(signal.match_status, 'unavailable')}. This is not a probability score.
                {Array.isArray(signal.sources) && signal.sources.length > 0
                  ? ` Sources: ${signal.sources.filter(item => typeof item === 'string').join(', ')}.`
                  : ' Source availability is not separately reported.'}
              </p>
            ))}
          </section>

          <section className="xai-panel__section">
            <h3>Redirect Evidence · Supporting Only</h3>
            {redirectAnalysis ? (
              <>
                <p className="xai-panel__section-note">
                  Network analysis restriction is not proof of phishing. The sequence below preserves the resolver response.
                </p>
                <dl className="xai-panel__redirect-meta">
                  <div>
                    <dt>Resolution state</dt>
                    <dd>{redirectAnalysis.resolution_state === 'blocked' ? 'Redirect resolution restricted' : text(redirectAnalysis.resolution_state)}</dd>
                  </div>
                  <div><dt>Original URL</dt><dd>{text(redirectAnalysis.original_url)}</dd></div>
                  <div>
                    <dt>{redirectBlocked ? 'Last URL before resolution stopped' : 'Final URL'}</dt>
                    <dd>{text(redirectAnalysis.final_url)}</dd>
                  </div>
                  <div><dt>Redirect count</dt><dd>{numeric(redirectAnalysis.num_redirects) ?? 'Not available'}</dd></div>
                </dl>
                {redirectHops.length > 0 ? (
                  <ol className="xai-panel__redirect-chain">
                    {redirectHops.map((hop, index) => {
                      const hopUrl = text(hop.url, '')
                      const isOriginal = index === 0 && hopUrl === text(redirectAnalysis.original_url, '')
                      const isFinal = index === redirectHops.length - 1
                        && redirectAnalysis.resolution_state === 'completed'
                        && hopUrl === text(redirectAnalysis.final_url, '')
                      const hopLabel = isOriginal && isFinal
                        ? 'Original / final URL'
                        : isOriginal
                          ? 'Original URL'
                          : isFinal
                            ? 'Final URL'
                            : `Hop ${index}`
                      return (
                      <li key={`${text(hop.url, 'hop')}-${index}`}>
                        <span className="xai-panel__hop-index">{index + 1}</span>
                        <div>
                          <strong>{hopLabel}</strong>
                          <strong>{text(hop.url, 'URL unavailable')}</strong>
                          <span>{hop.status_code === null || hop.status_code === undefined ? 'Status code unavailable' : `HTTP ${String(hop.status_code)}`}</span>
                          {typeof hop.note === 'string' && <span>{hop.note.replaceAll('_', ' ')}</span>}
                        </div>
                      </li>
                      )
                    })}
                  </ol>
                ) : (
                  <p className="xai-panel__empty">No redirect hops were reported.</p>
                )}
                {Array.isArray(redirectAnalysis.errors) && redirectAnalysis.errors.length > 0 && (
                  <EvidenceList
                    items={redirectAnalysis.errors.filter((item): item is string => typeof item === 'string').map(description => ({ title: 'Resolver note', description }))}
                    emptyText="No resolver notes."
                  />
                )}
              </>
            ) : (
              <p className="xai-panel__empty">Redirect evidence unavailable.</p>
            )}
            <EvidenceList items={redirectEvidence} emptyText="No additional redirect factors were reported." />
            <p className="xai-panel__section-note">
              Redirect evidence describes URL resolution and does not independently determine the ensemble verdict.
            </p>
          </section>

          <section className="xai-panel__section">
            <h3>Evidence Provenance</h3>
            <h4 className="xai-panel__subheading">Evidence availability</h4>
            {statusEntries.length === 0 ? (
              <p className="xai-panel__empty">Per-engine availability was not provided by the analysis API.</p>
            ) : (
              <ul className="xai-panel__availability-list">
                {statusEntries.map(([key, value]) => (
                  <li key={key}>
                    <div>
                      <strong>{key.replaceAll('_', ' ')}</strong>
                      {typeof value.reason === 'string' && <p>{value.reason}</p>}
                    </div>
                    <span className={`xai-panel__availability-status xai-panel__availability-status--${String(value.status)}`}>
                      {value.applicable === false ? 'Not applicable' : text(value.status, 'Unavailable')}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {engineSignals.length === 0 ? (
              <p className="xai-panel__empty">Provenance metadata unavailable.</p>
            ) : (
              <div className="xai-panel__table-wrap">
                <table className="xai-panel__table">
                  <thead><tr><th>Engine</th><th>Input</th><th>Scope</th><th>Source</th><th>Status</th><th>Score type</th></tr></thead>
                  <tbody>
                    {engineSignals.map((signal, index) => (
                      <tr key={`provenance-${index}`}>
                        <td>{engineTitle(signal)}</td>
                        <td>{inputLabel(signal.source, signal.url_scope)}</td>
                        <td>{formatScope(signal.url_scope)}</td>
                        <td>{text(signal.source)}</td>
                        <td>{engineStatusBySource(signal.source) ?? signalStatus(signal)}</td>
                        <td>{text(signal.score_type)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="xai-panel__section">
            <h3>Analysis Limitations</h3>
            {limitations.length === 0 && unavailableFeeds.length === 0 ? (
              <p className="xai-panel__empty">No applicable engine limitations were reported for this scan.</p>
            ) : (
              <ul className="xai-panel__availability-list">
                {limitations.map(item => (
                  <li key={`limitation-${item.key}`}>
                    <div>
                      <strong>{item.label} · {item.status}</strong>
                      <p>{item.reason}</p>
                      {item.unavailableSources.length > 0 && (
                        <p>Unavailable sources: {item.unavailableSources.map(source => source.replaceAll('_', ' ')).join(', ')}</p>
                      )}
                    </div>
                  </li>
                ))}
                {limitations.length === 0 && unavailableFeeds.length > 0 && (
                  <li>
                    <div>
                      <strong>Threat Intelligence · Partial feed availability</strong>
                      <p>Unavailable feeds: {unavailableFeeds.map(source => source.replaceAll('_', ' ')).join(', ')}</p>
                    </div>
                  </li>
                )}
              </ul>
            )}
          </section>
        </div>
          </div>
        </section>
      )}
    </section>
  )
}
