export type RiskLevel = 'safe' | 'low' | 'medium' | 'high' | 'suspicious' | 'phishing' | 'unavailable'
export type EvidenceStatus = 'available' | 'unavailable' | 'restricted' | 'error'
export type AnalysisStatus = 'complete' | 'partial' | 'restricted' | 'failed'

export interface EngineAvailability {
  status: EvidenceStatus
  reason?: string
  applicable?: boolean
  unavailable_sources?: string[]
}

export interface AnalyzeRequest {
  url: string
  text?: string
  image?: File
}

export interface XaiFactor {
  title: string
  description: string
  severity?: 'high' | 'medium' | 'low'
  source?: string
}

export interface XaiEngineSignal {
  engine: string
  score?: number | null
  risk_level: RiskLevel
  status?: EvidenceStatus
  reason?: string
  match_status?: 'MATCH' | 'NO MATCH'
  sources?: string[]
  source?: 'url_ml' | 'nlp' | 'vision' | 'domain_intelligence' | 'threat_intelligence' | string
  score_type?: 'engine_signal' | 'match_signal' | string
  url_scope?: 'original_url' | 'final_url' | 'submitted_text' | 'submitted_image' | string
}

export interface XaiFeatureImpact {
  feature: string
  value: string | number | null
  impact: number
  source?: string
  method?: 'shap' | 'catboost_feature_importance' | 'grad_cam' | string
  url_scope?: string
}

export interface XaiUrlMlEvidence {
  raw_model_probability_percent?: number | null
  engine_signal_percent?: number | null
  engine_signal_adjustment?: string | null
}

export interface XaiEvidence {
  summary: string
  risk_factors: XaiFactor[]
  safety_factors: XaiFactor[]
  engine_signals: XaiEngineSignal[]
  url_ml_evidence?: XaiUrlMlEvidence | null
  feature_importance: XaiFeatureImpact[]
  redirect_analysis?: RedirectAnalysis
  redirect_evidence?: XaiFactor[]
  engine_status?: Record<string, EngineAvailability>
  domain_intelligence?: XaiDomainEvidence | null
  threat_intelligence?: XaiThreatEvidence | null
}

export interface XaiDomainEvidence {
  status?: EvidenceStatus
  reason?: string
  final_url?: string
  domain_score?: number | null
  domain_risk_level?: RiskLevel
  metadata?: {
    domain?: string | null
    registrable_domain?: string | null
    age_days?: number | null
    ssl_valid?: boolean
    ssl_issuer?: string | null
    ssl_error?: string | null
    resolved_ips?: string[]
    mx_records?: string[] | null
    rdns?: string | null
    error?: string | null
  }
}

export interface XaiThreatEvidence {
  status?: EvidenceStatus
  reason?: string
  url_scope?: string
  ti_hits?: number
  ti_sources?: string[]
  is_exact_url_match?: boolean
  unavailable_sources?: string[]
}

export interface RedirectHop {
  url: string
  status_code?: number | string | null
  note?: string
}

export type RedirectResolutionState =
  | 'completed'
  | 'blocked'
  | 'failed'
  | 'loop'
  | 'limit_exceeded'
  | 'unavailable'

export interface RedirectAnalysis {
  original_url: string
  final_url: string
  redirect_chain: RedirectHop[]
  num_redirects: number
  loop_detected: boolean
  suspicious_redirects: boolean
  has_meta_refresh: boolean
  resolution_state: RedirectResolutionState | string
  errors: string[]
  blocked_reason?: string | null
}

export interface AnalyzeResponse {
  ensemble_risk_level: RiskLevel
  ensemble_score_percent: number | null   // 0–100 when a numerical result is available
  xai_summary: string
  xai?: XaiEvidence
  individual_scores_percent: Record<string, number>
  reasons: string[]
  analysis_status?: AnalysisStatus
  engine_status?: Record<string, EngineAvailability>
  fusion_method?: string
  thumbnail_base64?: string
  redirect_analysis?: RedirectAnalysis
}

// Stored in ScanHistory state
export interface ScanEntry {
  id: string                              // crypto.randomUUID()
  timestamp: Date
  url: string
  result: AnalyzeResponse
  hasText?: boolean
  hasImage?: boolean
}

// Shape returned by useAnalysis hook
export interface UseAnalysisState {
  loading: boolean
  result: AnalyzeResponse | null
  error: string | null
  analyze: (req: AnalyzeRequest) => Promise<void>
  reset: () => void
}
