import { createHash, randomUUID } from 'node:crypto'
import type { PaperAiCycleRequest, PaperFixtureSnapshot } from '@bybit-quant/quant-api-client'

export type PaperCandidate = PaperFixtureSnapshot['candidates'][number]

/** The model-visible universe is owned by the authenticated paper service. */
export type PaperUniverseView = {
  status: 'fresh'
  category: 'linear'
  observedAt: number
  expiresAt: number
  catalogueSize: number
  eligibleCount: number
  candidates: PaperCandidate[]
}

export function paperUniverse(snapshot: PaperFixtureSnapshot): PaperUniverseView {
  return {
    status: 'fresh',
    category: 'linear',
    observedAt: snapshot.observed_at_ns,
    expiresAt: snapshot.expires_at_ns,
    catalogueSize: snapshot.candidates.length,
    eligibleCount: snapshot.candidates.length,
    candidates: snapshot.candidates,
  }
}

export function selectPaperCandidate(snapshot: PaperFixtureSnapshot, value: unknown): PaperCandidate {
  if (typeof value !== 'string' || value.trim() === '') throw new Error('symbol is required')
  const symbol = value.trim().toUpperCase()
  const candidate = snapshot.candidates.find(item => item.symbol === symbol)
  if (candidate === undefined) throw new Error(`${symbol} is outside the current paper fixture universe`)
  return candidate
}

export function selectPaperEvidence(candidate: PaperCandidate, strategyId: unknown, strategyVersion: unknown, evidenceDigest: unknown) {
  if (typeof strategyId !== 'string' || typeof strategyVersion !== 'string' || typeof evidenceDigest !== 'string') {
    throw new Error('strategyId, strategyVersion, and evidenceDigest are required for internal paper decisions')
  }
  const evidence = candidate.selector_evidence.find(item =>
    item.strategy_id === strategyId && item.version === strategyVersion && item.evidence_digest === evidenceDigest)
  if (evidence === undefined) throw new Error('strategy evidence does not match the selected paper candidate')
  return evidence
}

export function createPaperDecisionRequest(input: {
  sessionId: string
  fixture: PaperFixtureSnapshot
  cycleId: string
  symbol: string
  action: 'long' | 'short' | 'flat'
  targetExposure: number
  strategyId: string
  strategyVersion: string
  evidenceDigest: string
}): PaperAiCycleRequest {
  const candidate = selectPaperCandidate(input.fixture, input.symbol)
  selectPaperEvidence(candidate, input.strategyId, input.strategyVersion, input.evidenceDigest)
  if (!Number.isFinite(input.targetExposure) || Math.abs(input.targetExposure) > 1) throw new Error('targetExposure must be between -1 and 1')
  if ((input.action === 'long' && input.targetExposure <= 0) || (input.action === 'short' && input.targetExposure >= 0)
    || (input.action === 'flat' && input.targetExposure !== 0)) throw new Error('action and targetExposure do not agree')
  const decision = {
    decision_id: randomUUID(),
    symbol: candidate.symbol,
    strategy_id: input.strategyId,
    strategy_version: input.strategyVersion,
    action: input.action,
    target_exposure: input.targetExposure,
    evidence_digest: input.evidenceDigest,
  } as const
  const requestWithoutDigest = {
    schema_version: '1' as const,
    environment: 'internal_paper' as const,
    request_id: `${input.cycleId}:${candidate.symbol}:${decision.decision_id}`.slice(0, 128),
    session_id: input.sessionId,
    fixture_id: input.fixture.fixture_id,
    bundle_digest: input.fixture.bundle_digest,
    cycle_id: input.cycleId,
    universe_digest: input.fixture.bundle_digest,
    expires_at_ns: input.fixture.expires_at_ns,
    decision,
  }
  return { ...requestWithoutDigest, payload_digest: sha256(canonicalJson(requestWithoutDigest)) }
}

/** Python and TypeScript must hash the same sorted, compact JSON representation. */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value)
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('non_finite_payload')
    return JSON.stringify(value)
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>
    return `{${Object.keys(record).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(record[key])}`).join(',')}}`
  }
  throw new Error('unsupported_payload_value')
}

function sha256(value: string): string {
  return createHash('sha256').update(value, 'utf8').digest('hex')
}
