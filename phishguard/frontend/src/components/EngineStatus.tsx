import { useEffect, useState } from 'react'
import './EngineStatus.css'

type StatusKind = 'healthy' | 'available' | 'unavailable' | 'unknown' | 'active'

interface HealthResponse {
  status?: string
  engines?: {
    ml_ready?: boolean
    nlp_ready?: boolean
    vision_ready?: boolean
    domain_ready?: boolean
    ensemble_ready?: boolean
  }
}

interface ThreatIntelResponse {
  status?: string
  is_syncing?: boolean
  last_sync_timestamp?: number
}

interface StatusItem {
  name: string
  value: string
  kind: StatusKind
  detail: string
}

function engineStatus(
  name: string,
  ready: boolean | undefined,
  detail: string,
): StatusItem {
  if (ready === true) return { name, value: 'Available', kind: 'available', detail }
  if (ready === false) return { name, value: 'Unavailable', kind: 'unavailable', detail }
  return { name, value: 'Status unavailable', kind: 'unknown', detail: 'Readiness field not returned.' }
}

function apiStatus(health: HealthResponse | null): StatusItem {
  if (health?.status?.toLowerCase() === 'ok' || health?.status?.toLowerCase() === 'healthy') {
    return {
      name: 'Backend API',
      value: 'Healthy',
      kind: 'healthy',
      detail: 'Verified by GET /api/health/.',
    }
  }
  return {
    name: 'Backend API',
    value: 'Status unavailable',
    kind: 'unknown',
    detail: 'Health endpoint did not return a supported status.',
  }
}

function threatIntelStatus(status: ThreatIntelResponse | null): StatusItem {
  if (status?.status?.toLowerCase() === 'active') {
    return {
      name: 'Threat Intelligence',
      value: status.is_syncing ? 'Active · syncing' : 'Active',
      kind: 'active',
      detail: 'Verified by GET /api/ti/status/.',
    }
  }
  return {
    name: 'Threat Intelligence',
    value: 'Status unavailable',
    kind: 'unknown',
    detail: 'Threat-feed status was not returned.',
  }
}

export default function EngineStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [threatIntel, setThreatIntel] = useState<ThreatIntelResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    const loadStatus = async () => {
      setLoading(true)
      const [healthResult, threatResult] = await Promise.allSettled([
        fetch('/api/health/'),
        fetch('/api/ti/status/'),
      ])

      if (cancelled) return

      if (healthResult.status === 'fulfilled' && healthResult.value.ok) {
        setHealth(await healthResult.value.json() as HealthResponse)
      } else {
        setHealth(null)
      }

      if (threatResult.status === 'fulfilled' && threatResult.value.ok) {
        setThreatIntel(await threatResult.value.json() as ThreatIntelResponse)
      } else {
        setThreatIntel(null)
      }

      setLoading(false)
    }

    void loadStatus()
    return () => {
      cancelled = true
    }
  }, [])

  const items: StatusItem[] = [
    apiStatus(health),
    engineStatus('URL Intelligence', health?.engines?.ml_ready, 'Backend ML readiness from GET /api/health/.'),
    engineStatus('NLP / Text Intelligence', health?.engines?.nlp_ready, 'Backend NLP readiness from GET /api/health/.'),
    engineStatus('Vision Intelligence', health?.engines?.vision_ready, 'Backend vision readiness from GET /api/health/.'),
    engineStatus('Domain Intelligence', health?.engines?.domain_ready, 'Backend domain readiness from GET /api/health/.'),
    threatIntelStatus(threatIntel),
    engineStatus('XAI', undefined, 'No XAI health field is provided by the backend.'),
    engineStatus('Local ONNX Model', undefined, 'Browser extension model loading is not exposed to the dashboard.'),
    engineStatus('HITL', undefined, 'No HITL health/status endpoint is provided.'),
    engineStatus('Database', undefined, 'Database connectivity is not exposed by a status endpoint.'),
  ]

  return (
    <section className="engine-status glass-card" aria-labelledby="engine-status-heading">
      <div className="engine-status__header">
        <div>
          <p className="engine-status__eyebrow">SYSTEM TELEMETRY</p>
          <h2 id="engine-status-heading" className="engine-status__title">ENGINE / SYSTEM STATUS</h2>
        </div>
        <span className="engine-status__legend">Verified status only</span>
      </div>

      {loading ? (
        <p className="engine-status__loading" role="status">Querying available status endpoints...</p>
      ) : (
        <div className="engine-status__grid">
          {items.map(item => (
            <article key={item.name} className={`engine-status__item engine-status__item--${item.kind}`}>
              <div className="engine-status__item-heading">
                <span className="engine-status__indicator" aria-hidden="true" />
                <h3>{item.name}</h3>
              </div>
              <strong>{item.value}</strong>
              <p>{item.detail}</p>
            </article>
          ))}
        </div>
      )}

      <p className="engine-status__note">
        “Status unavailable” means no reliable status signal is exposed; it does not indicate that the service is down.
      </p>
    </section>
  )
}
