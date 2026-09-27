import type { AnalyzeResponse, RiskLevel } from '../types/api'

const RISK_LEVELS = new Set<RiskLevel>([
  'safe',
  'low',
  'medium',
  'high',
  'suspicious',
  'phishing',
  'unavailable',
])

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * Accept only a response that can safely drive the result UI.
 * A successful HTTP status alone is not evidence of a completed analysis.
 */
export function normalizeAnalyzeResponse(value: unknown): AnalyzeResponse | null {
  if (!isRecord(value)) return null

  const score = value.ensemble_score_percent
  const riskLevel = value.ensemble_risk_level
  if ((score !== null && (typeof score !== 'number' || !Number.isFinite(score))) ||
      typeof riskLevel !== 'string' || !RISK_LEVELS.has(riskLevel as RiskLevel)) {
    return null
  }
  if ((score === null && riskLevel !== 'unavailable') || (typeof score === 'number' && riskLevel === 'unavailable')) {
    return null
  }

  const rawXai = isRecord(value.xai) ? value.xai : null
  const xai = rawXai
    ? {
        ...rawXai,
        engine_signals: Array.isArray(rawXai.engine_signals) ? rawXai.engine_signals : [],
        risk_factors: Array.isArray(rawXai.risk_factors) ? rawXai.risk_factors : [],
        safety_factors: Array.isArray(rawXai.safety_factors) ? rawXai.safety_factors : [],
        feature_importance: Array.isArray(rawXai.feature_importance) ? rawXai.feature_importance : [],
      }
    : undefined

  const individualScores: Record<string, number> = isRecord(value.individual_scores_percent)
    ? Object.fromEntries(
        Object.entries(value.individual_scores_percent).filter(([, item]) =>
          typeof item === 'number' && Number.isFinite(item),
        ),
      ) as Record<string, number>
    : {}

  return {
    ...value,
    ensemble_score_percent: score === null ? null : Math.min(100, Math.max(0, score)),
    ensemble_risk_level: riskLevel as RiskLevel,
    xai_summary: typeof value.xai_summary === 'string' ? value.xai_summary : '',
    reasons: Array.isArray(value.reasons)
      ? value.reasons.filter((reason): reason is string => typeof reason === 'string')
      : [],
    individual_scores_percent: individualScores,
    engine_status: isRecord(value.engine_status) ? value.engine_status as AnalyzeResponse['engine_status'] : {},
    xai: xai as AnalyzeResponse['xai'],
    redirect_analysis: isRecord(value.redirect_analysis)
      ? value.redirect_analysis as unknown as AnalyzeResponse['redirect_analysis']
      : undefined,
  }
}
