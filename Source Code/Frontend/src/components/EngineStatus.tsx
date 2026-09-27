import { useEffect, useState } from 'react'
import './EngineStatus.css'
import {
  databaseStatus,
  engineStatus,
  hitlStatus,
  localOnnxStatus,
  threatIntelStatus,
  type HealthResponse,
  type StatusItem,
  type ThreatIntelResponse,
} from './engineStatusState'

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

export default function EngineStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [threatIntel, setThreatIntel] = useState<ThreatIntelResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    const loadStatus = async () => {
      setLoading(true)
      const readJson = async <T,>(path: string): Promise<T | null> => {
        try {
          const response = await fetch(path)
          if (!response.ok) return null
          return await response.json() as T
        } catch {
          return null
        }
      }

      const [healthData, threatData] = await Promise.all([
        readJson<HealthResponse>('/api/health/'),
        readJson<ThreatIntelResponse>('/api/ti/status/'),
      ])

      if (!cancelled) {
        setHealth(healthData)
        setThreatIntel(threatData)
        setLoading(false)
      }
    }

    void loadStatus()
    return () => {
      cancelled = true
    }
  }, [])

  const items: StatusItem[] = [
    apiStatus(health),
    engineStatus('URL Intelligence', health?.engines?.url_ml ?? health?.engines?.ml_ready, 'Backend ML readiness from GET /api/health/.'),
    engineStatus('NLP / Text Intelligence', health?.engines?.nlp ?? health?.engines?.nlp_ready, 'Backend NLP readiness from GET /api/health/.'),
    engineStatus('Vision Intelligence', health?.engines?.vision ?? health?.engines?.vision_ready, 'Backend vision readiness from GET /api/health/.'),
    engineStatus('Domain Intelligence', health?.engines?.domain ?? health?.engines?.domain_ready, 'Backend domain readiness from GET /api/health/.'),
    threatIntelStatus(threatIntel),
    engineStatus('XAI', health?.engines?.xai, 'Backend XAI readiness from GET /api/health/.'),
    localOnnxStatus(),
    hitlStatus(health?.engines?.hitl),
    databaseStatus(health?.engines?.database),
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
        Browser-local model state is not observable by this dashboard. Unknown means the backend did not report a readiness state.
      </p>
    </section>
  )
}
