import assert from 'node:assert/strict'
import test from 'node:test'

import { normalizeAnalyzeResponse } from './analysisResponse.ts'

test('rejects empty and malformed successful API payloads', () => {
  assert.equal(normalizeAnalyzeResponse({}), null)
  assert.equal(normalizeAnalyzeResponse({ ensemble_score_percent: '70', ensemble_risk_level: 'phishing' }), null)
  assert.equal(normalizeAnalyzeResponse({ ensemble_score_percent: null, ensemble_risk_level: 'safe' }), null)
  assert.equal(normalizeAnalyzeResponse({ ensemble_score_percent: 70, ensemble_risk_level: 'unavailable' }), null)
})

test('preserves an explicit unavailable final result without inventing a score', () => {
  const result = normalizeAnalyzeResponse({
    ensemble_score_percent: null,
    ensemble_risk_level: 'unavailable',
    engine_status: { url_ml: { status: 'unavailable' } },
  })

  assert.equal(result?.ensemble_score_percent, null)
  assert.equal(result?.ensemble_risk_level, 'unavailable')
})

test('normalizes optional evidence fields so malformed evidence cannot crash the UI', () => {
  const result = normalizeAnalyzeResponse({
    ensemble_score_percent: 42,
    ensemble_risk_level: 'suspicious',
    xai: { engine_signals: 'not-an-array', risk_factors: null },
    individual_scores_percent: { ml: 42, vision: 'not-a-score' },
  })

  assert.deepEqual(result?.xai?.engine_signals, [])
  assert.deepEqual(result?.individual_scores_percent, { ml: 42 })
})
