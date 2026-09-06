export type RiskLevel = 'safe' | 'suspicious' | 'phishing'

export interface AnalyzeRequest {
  url: string
  text?: string
  image?: File
}

export interface AnalyzeResponse {
  ensemble_risk_level: RiskLevel
  ensemble_score_percent: number          // 0–100
  xai_summary: string
  individual_scores_percent: Record<string, number>
  reasons: string[]
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
