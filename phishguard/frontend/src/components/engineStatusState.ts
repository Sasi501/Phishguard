export type StatusKind =
  | 'healthy'
  | 'available'
  | 'unavailable'
  | 'unknown'
  | 'active'
  | 'dependency-unavailable'
  | 'browser-local'

export interface ComponentReadiness {
  ready?: boolean
  reason?: string
}

export interface HealthResponse {
  status?: string
  engines?: {
    url_ml?: ComponentReadiness
    nlp?: ComponentReadiness
    vision?: ComponentReadiness
    domain?: ComponentReadiness
    xai?: ComponentReadiness
    hitl?: ComponentReadiness
    database?: ComponentReadiness
    ml_ready?: boolean
    nlp_ready?: boolean
    vision_ready?: boolean
    domain_ready?: boolean
    ensemble_ready?: boolean
  }
}

export interface ThreatIntelResponse {
  status?: string
  is_syncing?: boolean
  last_sync_timestamp?: number
}

export interface StatusItem {
  name: string
  value: string
  kind: StatusKind
  detail: string
}

export function engineStatus(
  name: string,
  readiness: ComponentReadiness | boolean | undefined,
  detail: string,
): StatusItem {
  const ready = typeof readiness === 'boolean' ? readiness : readiness?.ready
  const reason = typeof readiness === 'object' ? readiness.reason : undefined
  if (ready === true) return { name, value: 'Available', kind: 'available', detail }
  if (ready === false) {
    return {
      name,
      value: reason ? `Unavailable · ${reason}` : 'Unavailable',
      kind: 'unavailable',
      detail,
    }
  }
  return { name, value: 'Unknown', kind: 'unknown', detail: 'Backend readiness was not reported.' }
}

export function databaseStatus(readiness: ComponentReadiness | undefined): StatusItem {
  if (readiness?.ready === false) {
    return {
      name: 'Database',
      value: 'Unavailable',
      kind: 'dependency-unavailable',
      detail: readiness.reason || 'MongoDB connection unavailable.',
    }
  }
  return engineStatus('Database', readiness, 'MongoDB connection status from GET /api/health/.')
}

export function hitlStatus(readiness: ComponentReadiness | undefined): StatusItem {
  if (readiness?.ready === false) {
    return {
      name: 'HITL',
      value: 'Dependency unavailable',
      kind: 'dependency-unavailable',
      detail: readiness.reason || 'Requires MongoDB for analyst workflow.',
    }
  }
  return engineStatus('HITL', readiness, 'Requires MongoDB for analyst workflow.')
}

export function threatIntelStatus(status: ThreatIntelResponse | null): StatusItem {
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

export function localOnnxStatus(): StatusItem {
  return {
    name: 'Local ONNX Model',
    value: 'Browser-local',
    kind: 'browser-local',
    detail: 'ONNX inference runs inside the browser extension; its load state is not reported to this dashboard.',
  }
}
