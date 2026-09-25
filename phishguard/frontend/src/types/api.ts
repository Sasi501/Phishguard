export type RiskLevel = 'safe' | 'low' | 'medium' | 'high' | 'suspicious' | 'phishing'

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
  score: number
  risk_level: 'safe' | 'low' | 'medium' | 'high' | 'phishing' | 'suspicious'
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
}

export interface XaiEvidence {
  summary: string
  risk_factors: XaiFactor[]
  safety_factors: XaiFactor[]
  engine_signals: XaiEngineSignal[]
  feature_importance: XaiFeatureImpact[]
  redirect_analysis?: RedirectAnalysis
  redirect_evidence?: XaiFactor[]
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
}

export interface AnalyzeResponse {
  ensemble_risk_level: RiskLevel
  ensemble_score_percent: number          // 0–100
  xai_summary: string
  xai?: XaiEvidence
  individual_scores_percent: Record<string, number>
  reasons: string[]
  thumbnail_base64?: string
  redirect_analysis?: RedirectAnalysis
}

// Stored in ScanHistory state
export interface ScanEntry {
  id: string                              // crypto.randomUUID()
  timestamp: Date
  url: string
  result: AnalyzeResponse
}

// Shape returned by useAnalysis hook
export interface UseAnalysisState {
  loading: boolean
  result: AnalyzeResponse | null
  error: string | null
  analyze: (req: AnalyzeRequest) => Promise<void>
  reset: () => void
}
