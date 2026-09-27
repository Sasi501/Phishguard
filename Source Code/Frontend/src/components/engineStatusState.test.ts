import assert from 'node:assert/strict'
import test from 'node:test'

import {
  databaseStatus,
  engineStatus,
  hitlStatus,
  localOnnxStatus,
  threatIntelStatus,
} from './engineStatusState.ts'

test('reports ready XAI as available', () => {
  assert.equal(engineStatus('XAI', { ready: true }, 'Backend XAI readiness.').value, 'Available')
})

test('reports missing XAI readiness as unknown, not unavailable', () => {
  const status = engineStatus('XAI', undefined, 'Backend XAI readiness.')
  assert.equal(status.value, 'Unknown')
  assert.equal(status.kind, 'unknown')
})

test('reports MongoDB dependency failures truthfully for HITL and database', () => {
  const unavailable = { ready: false, reason: 'MongoDB unavailable' }
  assert.deepEqual(hitlStatus(unavailable), {
    name: 'HITL',
    value: 'Dependency unavailable',
    kind: 'dependency-unavailable',
    detail: 'MongoDB unavailable',
  })
  assert.deepEqual(databaseStatus(unavailable), {
    name: 'Database',
    value: 'Unavailable',
    kind: 'dependency-unavailable',
    detail: 'MongoDB unavailable',
  })
})

test('preserves readiness states for NLP, vision, domain, TI, and browser-local ONNX', () => {
  for (const name of ['NLP / Text Intelligence', 'Vision Intelligence', 'Domain Intelligence']) {
    assert.equal(engineStatus(name, { ready: true }, 'Backend readiness.').kind, 'available')
  }
  assert.equal(threatIntelStatus({ status: 'active' }).kind, 'active')
  assert.deepEqual(localOnnxStatus(), {
    name: 'Local ONNX Model',
    value: 'Browser-local',
    kind: 'browser-local',
    detail: 'ONNX inference runs inside the browser extension; its load state is not reported to this dashboard.',
  })
})
