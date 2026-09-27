import type { AnalyzeResponse, RiskLevel } from '../types/api'
import './BasicDetectionSummary.css'

interface BasicDetectionSummaryProps {
  result: AnalyzeResponse
  onViewDetails: () => void
}

interface EngineItem {
  id: string
  name: string
  type: string
  scoreText: string
  riskLevel: RiskLevel
  statusText: string
  isAvailable: boolean
  detail?: string
}

function normalizeRisk(level?: string): RiskLevel {
  const l = (level || '').toLowerCase()
  if (l === 'safe') return 'safe'
  if (l === 'suspicious') return 'suspicious'
  if (l === 'phishing') return 'phishing'
  if (l === 'low') return 'low'
  if (l === 'medium') return 'medium'
  if (l === 'high') return 'high'
  return 'unavailable'
}

export default function BasicDetectionSummary({ result, onViewDetails }: BasicDetectionSummaryProps) {
  const engineSignals = result.xai?.engine_signals ?? []
  const engineStatus = result.engine_status ?? result.xai?.engine_status ?? {}

  // 1. URL ML
  const urlSignal = engineSignals.find(s => s.source === 'url_ml' || s.engine?.toLowerCase().includes('url'))
  const urlAvail = engineStatus.url_ml?.status !== 'unavailable'
  const urlScore = typeof urlSignal?.score === 'number' ? `${urlSignal.score.toFixed(1)}%` : null

  // 2. Domain Analysis
  const domainSignal = engineSignals.find(s => s.source === 'domain_intelligence' || s.engine?.toLowerCase().includes('domain'))
  const domainAvail = engineStatus.domain_intelligence?.status !== 'unavailable'
  const domainScore = typeof domainSignal?.score === 'number' ? `${domainSignal.score.toFixed(1)}%` : null

  // 3. Threat Intelligence
  const tiSignal = engineSignals.find(s => s.source === 'threat_intelligence' || s.engine?.toLowerCase().includes('threat'))
  const tiAvail = engineStatus.threat_intelligence?.status !== 'unavailable'
  const tiMatch = tiSignal?.match_status ? (tiSignal.match_status === 'MATCH' ? 'Match Found' : 'No Match') : null

  // 4. Redirect Analysis
  const redirectData = result.redirect_analysis
  const redirectSignal = engineSignals.find(s => s.source === 'redirect' || s.engine?.toLowerCase().includes('redirect'))
  const redirectAvail = Boolean(redirectData && redirectData.resolution_state !== 'unavailable')

  // 5. NLP
  const nlpSignal = engineSignals.find(s => s.source === 'nlp' || s.engine?.toLowerCase().includes('nlp') || s.engine?.toLowerCase().includes('text'))
  const nlpApplicable = Boolean(nlpSignal && nlpSignal.status !== 'unavailable' && (typeof nlpSignal.score === 'number' || nlpSignal.reason !== 'No page text submitted'))

  // 6. Vision
  const visionSignal = engineSignals.find(s => s.source === 'vision' || s.engine?.toLowerCase().includes('vision') || s.engine?.toLowerCase().includes('screenshot'))
  const visionApplicable = Boolean(visionSignal && visionSignal.status !== 'unavailable' && typeof visionSignal.score === 'number')

  const engines: EngineItem[] = [
    {
      id: 'url_ml',
      name: 'URL Feature Analysis',
      type: 'CatBoost ML',
      scoreText: urlScore ?? 'Active',
      riskLevel: normalizeRisk(urlSignal?.risk_level),
      statusText: urlAvail ? (urlScore ? `Risk: ${urlScore}` : 'Evaluated') : 'Unavailable',
      isAvailable: urlAvail,
    },
    {
      id: 'domain_intelligence',
      name: 'Domain Intelligence',
      type: 'WHOIS & DNS Heuristics',
      scoreText: domainScore ?? 'Active',
      riskLevel: normalizeRisk(domainSignal?.risk_level),
      statusText: domainAvail ? (domainScore ? `Score: ${domainScore}` : 'Verified') : 'Unavailable',
      isAvailable: domainAvail,
    },
    {
      id: 'threat_intelligence',
      name: 'Threat Feeds',
      type: 'OpenPhish / URLhaus / PhishTank',
      scoreText: tiMatch ?? (tiSignal?.risk_level?.toUpperCase() ?? 'Checked'),
      riskLevel: normalizeRisk(tiSignal?.risk_level),
      statusText: tiAvail ? (tiMatch ?? 'Feeds Checked') : 'Unavailable',
      isAvailable: tiAvail,
    },
    {
      id: 'redirect_analysis',
      name: 'Redirect Analysis',
      type: 'Chain Forensics & Unwrapping',
      scoreText: redirectData ? `${redirectData.num_redirects} hop${redirectData.num_redirects === 1 ? '' : 's'}` : 'Direct',
      riskLevel: normalizeRisk(redirectSignal?.risk_level),
      statusText: redirectAvail ? (redirectData?.suspicious_redirects ? 'Suspicious Chain' : 'Resolved') : 'Not Applicable',
      isAvailable: redirectAvail,
    },
  ]

  // Add NLP only if applicable
  if (nlpApplicable && nlpSignal) {
    engines.push({
      id: 'nlp',
      name: 'NLP Text Intelligence',
      type: 'DistilBERT Transformer',
      scoreText: typeof nlpSignal.score === 'number' ? `${nlpSignal.score.toFixed(1)}%` : 'Analyzed',
      riskLevel: normalizeRisk(nlpSignal.risk_level),
      statusText: typeof nlpSignal.score === 'number' ? `Risk: ${nlpSignal.score.toFixed(1)}%` : 'Analyzed',
      isAvailable: true,
    })
  }

  // Add Vision only if applicable
  if (visionApplicable && visionSignal) {
    engines.push({
      id: 'vision',
      name: 'Vision Intelligence',
      type: 'EfficientNet-B3 Classifier',
      scoreText: typeof visionSignal.score === 'number' ? `${visionSignal.score.toFixed(1)}%` : 'Analyzed',
      riskLevel: normalizeRisk(visionSignal.risk_level),
      statusText: typeof visionSignal.score === 'number' ? `Risk: ${visionSignal.score.toFixed(1)}%` : 'Analyzed',
      isAvailable: true,
    })
  }

  // Extract clean reasons
  const reasons = (result.reasons && result.reasons.length > 0)
    ? result.reasons.slice(0, 4)
    : result.xai_summary
      ? [result.xai_summary]
      : ['No specific risk factors triggered during multi-modal scan.']

  return (
    <section className="basic-summary glass-card" aria-label="Detection Summary and Explanation">
      <div className="basic-summary__header">
        <h2 className="basic-summary__title">Detection Summary</h2>
        <span className="basic-summary__subtitle">Multi-Modal Intelligence Engine Breakdown</span>
      </div>

      <div className="basic-summary__grid">
        {engines.map(engine => (
          <div key={engine.id} className={`basic-engine-card basic-engine-card--${engine.riskLevel}`}>
            <div className="basic-engine-card__info">
              <span className="basic-engine-card__name">{engine.name}</span>
              <span className="basic-engine-card__type">{engine.type}</span>
            </div>
            <div className="basic-engine-card__badge-wrapper">
              <span className={`basic-engine-card__badge basic-engine-card__badge--${engine.riskLevel}`}>
                {engine.riskLevel.toUpperCase()}
              </span>
              <span className="basic-engine-card__status">{engine.statusText}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="basic-why-section">
        <h3 className="basic-why-section__title">
          <svg className="basic-why-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          Why this result?
        </h3>
        <ul className="basic-why-list">
          {reasons.map((reason, idx) => (
            <li key={idx} className="basic-why-item">
              <span className="basic-why-bullet" aria-hidden="true">▸</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="basic-summary__action">
        <button
          type="button"
          className="basic-view-details-btn"
          onClick={onViewDetails}
          aria-label="View Detailed Forensic Analysis and Evidence"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          View Advanced Forensic Analysis &amp; Evidence
        </button>
      </div>
    </section>
  )
}
