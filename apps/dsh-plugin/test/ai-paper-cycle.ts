import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import type { PaperFixtureSnapshot } from '@bybit-quant/quant-api-client'
import {
  canonicalJson,
  createPaperDecisionRequest,
  paperUniverse,
  selectPaperCandidate,
  selectPaperEvidence,
} from '../dist/lib/paper-ai-cycle.js'

const fixture: PaperFixtureSnapshot = {
  schema_version: '1',
  fixture_id: 'fixture-contract-a',
  bundle_digest: 'a'.repeat(64),
  observed_at_ns: 1_000_000,
  expires_at_ns: 2_000_000,
  candidates: [{
    symbol: 'ALPHAUSDT',
    snapshot_id: 'fixture-contract-a:ALPHAUSDT:1',
    observed_at_ns: 1_000_000,
    expires_at_ns: 2_000_000,
    bid: '100.0',
    ask: '100.1',
    bid_size: '10',
    ask_size: '10',
    rules: {
      base_currency: 'ALPHA',
      price_increment: '0.1',
      size_increment: '0.01',
      min_quantity: '0.01',
      max_quantity: '100',
      min_notional: '1',
    },
    bars: [{
      timestamp_ns: 1_000_000,
      open: '99',
      high: '101',
      low: '98',
      close: '100',
      volume: '12',
    }],
    selector_evidence: [{
      strategy_id: 'sma-cross',
      version: '1.2.0',
      approval_ref: 'fixture-approval:sma-cross',
      current_status: 'approved',
      validation_status: 'paper_passed',
      oos_score: 0.7,
      confidence: 0.8,
      expected_cost_bps: 2,
      evaluation_ref: 'fixture-evaluation:sma-cross',
      evaluated_at_ns: 1_000_000,
      expires_at_ns: 2_000_000,
      out_of_sample_samples: 60,
      supported_regimes: ['trend'],
      ready_signal: true,
      provenance: 'synthetic_fixture_only',
      evidence_digest: 'b'.repeat(64),
    }],
  }],
  correlations: [],
}

const evidence = fixture.candidates[0]!.selector_evidence[0]!

assert.deepEqual(paperUniverse(fixture), {
  status: 'fresh',
  category: 'linear',
  observedAt: fixture.observed_at_ns,
  expiresAt: fixture.expires_at_ns,
  catalogueSize: 1,
  eligibleCount: 1,
  candidates: fixture.candidates,
})
assert.equal(selectPaperCandidate(fixture, ' alphAusdt ').symbol, 'ALPHAUSDT')
assert.equal(selectPaperEvidence(fixture.candidates[0]!, 'sma-cross', '1.2.0', evidence.evidence_digest), evidence)
assert.throws(() => selectPaperCandidate(fixture, 'BTCUSDT'), /outside the current paper fixture universe/)
assert.throws(() => selectPaperEvidence(fixture.candidates[0]!, 'sma-cross', '1.1.0', evidence.evidence_digest), /does not match/)

const request = createPaperDecisionRequest({
  sessionId: 'paper-session',
  fixture,
  cycleId: 'cycle-001',
  symbol: 'ALPHAUSDT',
  action: 'long',
  targetExposure: 0.25,
  strategyId: evidence.strategy_id,
  strategyVersion: evidence.version,
  evidenceDigest: evidence.evidence_digest,
})
assert.equal(request.schema_version, '1')
assert.equal(request.environment, 'internal_paper')
assert.equal(request.session_id, 'paper-session')
assert.equal(request.fixture_id, fixture.fixture_id)
assert.equal(request.bundle_digest, fixture.bundle_digest)
assert.equal(request.universe_digest, fixture.bundle_digest)
assert.equal(request.cycle_id, 'cycle-001')
assert.ok(request.expires_at_ns > fixture.observed_at_ns)
assert.ok(request.expires_at_ns < fixture.expires_at_ns)
assert.match(request.request_id, /^cycle-001:ALPHAUSDT:/u)
assert.equal(request.decision.symbol, 'ALPHAUSDT')
assert.equal(request.decision.action, 'long')
assert.equal(request.decision.target_exposure, 0.25)
const { payload_digest: _digest, ...unsigned } = request
assert.equal(request.payload_digest, createHash('sha256').update(canonicalJson(unsigned), 'utf8').digest('hex'))

assert.throws(() => createPaperDecisionRequest({
  sessionId: 'paper-session', fixture, cycleId: 'cycle-002', symbol: 'ALPHAUSDT', action: 'short', targetExposure: 0.2,
  strategyId: evidence.strategy_id, strategyVersion: evidence.version, evidenceDigest: evidence.evidence_digest,
}), /action and targetExposure do not agree/)
assert.throws(() => createPaperDecisionRequest({
  sessionId: 'paper-session', fixture, cycleId: 'cycle-003', symbol: 'ALPHAUSDT', action: 'long', targetExposure: 0,
  strategyId: evidence.strategy_id, strategyVersion: evidence.version, evidenceDigest: evidence.evidence_digest,
}), /action and targetExposure do not agree/)
assert.throws(() => createPaperDecisionRequest({
  sessionId: 'paper-session', fixture, cycleId: 'cycle-004', symbol: 'ALPHAUSDT', action: 'long', targetExposure: 0.25,
  strategyId: evidence.strategy_id, strategyVersion: evidence.version, evidenceDigest: 'c'.repeat(64),
}), /does not match/)

assert.equal(canonicalJson({ z: 1, a: [true, null, 'x'] }), '{"a":[true,null,"x"],"z":1}')
assert.throws(() => canonicalJson(Number.NaN), /non_finite_payload/)

console.log('ai paper cycle: fixture identity, evidence binding, digest, and fail-closed checks passed')
