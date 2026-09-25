import './URLAnatomy.css'

export interface UrlAnatomyData {
  isValid: boolean
  protocol: string
  subdomain: string
  domain: string
  tld: string
  port: string
  path: string
  query: string
  fragment: string
  queryParams: Array<{ key: string; value: string }>
  urlLength: number
  subdomainCount: number
  hasQueryParameters: boolean
  hasFragment: boolean
  isHttps: boolean
  rawUrl: string
  error?: string
}

function getParsedHostParts(hostname: string): { subdomain: string; domain: string; tld: string } {
  const parts = hostname.split('.').filter(Boolean)

  if (parts.length === 0) {
    return { subdomain: '', domain: '', tld: '' }
  }

  if (parts.length === 1) {
    return { subdomain: '', domain: parts[0], tld: '' }
  }

  if (parts.length === 2) {
    return { subdomain: '', domain: parts[0], tld: parts[1] }
  }

  const commonTwoPartTlds = new Set([
    'ac', 'ai', 'co', 'com', 'edu', 'gov', 'io', 'net', 'org', 'uk', 'us', 'jp', 'au', 'de', 'fr', 'ca', 'in', 'it', 'eu'
  ])

  const secondLast = parts[parts.length - 2]
  const hasMultiPartTld = commonTwoPartTlds.has(secondLast)

  if (hasMultiPartTld) {
    const domain = parts[parts.length - 3] ?? parts[0]
    const subdomain = parts.slice(0, Math.max(0, parts.length - 3)).join('.')
    const tld = parts.slice(-2).join('.')
    return { subdomain, domain, tld }
  }

  const domain = parts[parts.length - 2] ?? parts[0]
  const subdomain = parts.slice(0, Math.max(0, parts.length - 2)).join('.')
  const tld = parts[parts.length - 1] ?? ''
  return { subdomain, domain, tld }
}

export function parseUrlAnatomy(rawUrl?: string | null): UrlAnatomyData {
  const normalized = rawUrl?.trim() ?? ''

  if (!normalized) {
    return {
      isValid: false,
      protocol: '',
      subdomain: '',
      domain: '',
      tld: '',
      port: '',
      path: '',
      query: '',
      fragment: '',
      queryParams: [],
      urlLength: 0,
      subdomainCount: 0,
      hasQueryParameters: false,
      hasFragment: false,
      isHttps: false,
      rawUrl: '',
      error: 'No URL available for this scan.'
    }
  }

  try {
    const parsed = new URL(normalized)
    const { subdomain, domain, tld } = getParsedHostParts(parsed.hostname)
    const queryParams = Array.from(parsed.searchParams.entries()).map(([key, value]) => ({ key, value }))

    return {
      isValid: true,
      protocol: parsed.protocol.replace(':', ''),
      subdomain,
      domain,
      tld,
      port: parsed.port || 'none',
      path: parsed.pathname || '/',
      query: parsed.search || 'none',
      fragment: parsed.hash ? parsed.hash.replace('#', '') : 'none',
      queryParams,
      urlLength: normalized.length,
      subdomainCount: subdomain ? subdomain.split('.').filter(Boolean).length : 0,
      hasQueryParameters: parsed.searchParams.size > 0,
      hasFragment: parsed.hash.length > 0,
      isHttps: parsed.protocol === 'https:',
      rawUrl: normalized,
    }
  } catch {
    return {
      isValid: false,
      protocol: '',
      subdomain: '',
      domain: '',
      tld: '',
      port: '',
      path: '',
      query: '',
      fragment: '',
      queryParams: [],
      urlLength: normalized.length,
      subdomainCount: 0,
      hasQueryParameters: false,
      hasFragment: false,
      isHttps: false,
      rawUrl: normalized,
      error: 'Malformed or incomplete URL — structure unavailable.'
    }
  }
}

interface URLAnatomyProps {
  url?: string | null
}

function AnatomyToken({ label, value }: { label: string; value: string }) {
  return (
    <div className="url-anatomy__token">
      <span className="url-anatomy__token-label">{label}</span>
      <strong className="url-anatomy__token-value">{value}</strong>
    </div>
  )
}

export default function URLAnatomy({ url }: URLAnatomyProps) {
  const anatomy = parseUrlAnatomy(url)

  if (!anatomy.isValid) {
    return (
      <section className="url-anatomy glass-card" aria-label="URL anatomy unavailable">
        <div className="url-anatomy__header">
          <h2 className="url-anatomy__title">URL ANATOMY</h2>
        </div>
        <p className="url-anatomy__empty">{anatomy.error ?? 'No URL structure available for this scan.'}</p>
      </section>
    )
  }

  return (
    <section className="url-anatomy glass-card" aria-label="URL anatomy breakdown">
      <div className="url-anatomy__header">
        <h2 className="url-anatomy__title">URL ANATOMY</h2>
      </div>

      <div className="url-anatomy__cards">
        <AnatomyToken label="Protocol" value={anatomy.protocol || 'unknown'} />
        <AnatomyToken label="Subdomain" value={anatomy.subdomain || 'none'} />
        <AnatomyToken label="Domain" value={anatomy.domain || 'unknown'} />
        <AnatomyToken label="TLD" value={anatomy.tld || 'none'} />
        <AnatomyToken label="Port" value={anatomy.port === 'none' ? 'none' : anatomy.port} />
        <AnatomyToken label="Path" value={anatomy.path || '/'} />
      </div>

      <div className="url-anatomy__meta">
        <div className="url-anatomy__meta-block">
          <span className="url-anatomy__meta-label">Query parameters</span>
          <strong>{anatomy.hasQueryParameters ? anatomy.queryParams.length.toString() : 'none'}</strong>
        </div>
        <div className="url-anatomy__meta-block">
          <span className="url-anatomy__meta-label">Fragment</span>
          <strong>{anatomy.hasFragment ? 'present' : 'none'}</strong>
        </div>
        <div className="url-anatomy__meta-block">
          <span className="url-anatomy__meta-label">URL length</span>
          <strong>{anatomy.urlLength}</strong>
        </div>
        <div className="url-anatomy__meta-block">
          <span className="url-anatomy__meta-label">Subdomains</span>
          <strong>{anatomy.subdomainCount}</strong>
        </div>
        <div className="url-anatomy__meta-block">
          <span className="url-anatomy__meta-label">Protocol</span>
          <strong>{anatomy.isHttps ? 'HTTPS' : 'HTTP'}</strong>
        </div>
      </div>

      {anatomy.hasQueryParameters && (
        <div className="url-anatomy__list-section">
          <h3 className="url-anatomy__list-title">Query Parameters</h3>
          <ul className="url-anatomy__list">
            {anatomy.queryParams.map((param, index) => (
              <li key={`${param.key}-${index}`} className="url-anatomy__list-item">
                <span>{param.key}</span>
                <strong>{param.value}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}

      {anatomy.hasFragment && (
        <div className="url-anatomy__list-section">
          <h3 className="url-anatomy__list-title">Fragment</h3>
          <p className="url-anatomy__fragment">#{anatomy.fragment}</p>
        </div>
      )}
    </section>
  )
}
