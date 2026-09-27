import assert from 'node:assert/strict'
import test from 'node:test'

import { inputLabel } from './evidenceProvenance.ts'

test('labels each signal with its actual evidence input', () => {
  assert.equal(inputLabel('url_ml', 'original_url'), 'Submitted/original URL')
  assert.equal(inputLabel('nlp', 'submitted_text'), 'Submitted text')
  assert.equal(inputLabel('vision', 'submitted_image'), 'Submitted image')
  assert.equal(inputLabel('vision', 'captured_screenshot'), 'Server-captured screenshot')
  assert.equal(inputLabel('domain_intelligence', 'final_url'), 'Final resolved URL')
  assert.equal(inputLabel('threat_intelligence', 'final_url'), 'Final resolved URL')
  assert.equal(inputLabel('redirect', 'original_to_final'), 'Original → intermediate → final URLs')
})

test('does not mislabel original-scope or missing TI evidence as resolved evidence', () => {
  assert.equal(inputLabel('threat_intelligence', 'original_url'), 'Submitted/original URL')
  assert.equal(inputLabel('threat_intelligence', 'not_collected'), 'No threat-intelligence URL collected')
  assert.equal(inputLabel('nlp', 'not_submitted'), 'No text submitted')
  assert.equal(inputLabel('vision', 'not_collected'), 'No screenshot collected')
})
