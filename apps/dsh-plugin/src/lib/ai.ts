/**
 * The AI decision track: a structured market brief, a strict decision schema, a
 * code-owned risk gate, and a journal of every verdict with its outcome.
 *
 * The model supplies the thesis; this module supplies the arithmetic. It never
 * trusts a decision: position size is bounded by the risk budget, a stop must
 * exist, and every accepted decision is written to the journal so a later
 * review can check whether the confidence was earned.
 */
import { round } from './numeric.js'
import { markedEquity } from './ai-accounting.js'
import { normalizeUntrustedText } from './trust.js'
export { atr, trendState, volRegime, bookPressure, buildSymbolBrief, buildBrief } from './ai-market.js'

/** Fee charged on each side of a simulated AI fill, in basis points. */
/** Actions the decision schema accepts. */
export const AI_ACTIONS = ['long', 'short', 'flat'] as const

/** Retained journal entries. */
export type DecisionAction = 'long' | 'short' | 'flat'
export interface AgentDecision {
  symbol: string
  action: DecisionAction
  sizePct: number
  confidence: number
  stopPct: number
  takePct: number
  horizonHours: number
  thesis: string
  invalidation: string
}
export interface TrackPosition {
  symbol: string
  side: 'long' | 'short'
  entryPrice: number
  notionalUsd: number
  qty: number
  stopPrice: number
  takePrice: number | null
  openedAt: number
  horizonHours: number
  decisionId: string
  entryFeeUsd: number
}
export interface DecisionResult {
  exitPrice: number
  exitTime: number
  reason: string
  pnlUsd: number
  pnlPct: number
  rMultiple: number | null
  bars: number
}
export interface JournalDecision extends AgentDecision {
  id: string
  time: number
  priceAtDecision: number
  briefHash: string
  context: unknown
  status: 'open' | 'closed' | 'flat' | 'rejected'
  gate: { allowed: boolean, reasons: string[] } | null
  result: DecisionResult | null
}
export interface DecisionTrack {
  version: 1
  createdAt: number
  startEquity: number
  equity: number
  peakEquity: number
  maxDrawdownPct: number
  feesPaidUsd: number
  dayKey: string
  dayStartEquity: number
  positions: Record<string, TrackPosition>
  decisions: JournalDecision[]
  equityCurve: Array<{ t: number, e: number }>
}
export interface RiskConfig {
  aiRiskPerTradePct: number
  aiMaxPositionPct: number
  aiMaxOpenPositions: number
  aiMaxDailyLossPct: number
  aiMaxDrawdownPct: number
}

export interface RiskGateResult {
  allowed: boolean
  checks: Array<{ name: string, ok: boolean, detail: string }>
  reasons: string[]
  notional?: number
  riskUsd?: number
}
export interface MarketBriefSymbol {
  symbol: string
  price: number
  primary: Record<string, unknown>
  fundingRatePct: number | null
  book?: { imbalancePct?: number, spreadBps?: number | null }
}
export interface MarketBrief {
  at: string
  symbols: MarketBriefSymbol[]
}

/** Fresh track for one configuration. */
export function createTrack(startEquity: number, now = Date.now()): DecisionTrack {
  return {
    version: 1,
    createdAt: now,
    startEquity,
    equity: startEquity,
    peakEquity: startEquity,
    maxDrawdownPct: 0,
    feesPaidUsd: 0,
    dayKey: dayKeyOf(now),
    dayStartEquity: startEquity,
    positions: {},
    decisions: [],
    equityCurve: [{ t: now, e: startEquity }],
  }
}

/** Day bucket used for the daily loss limit. */
export function dayKeyOf(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10)
}

/** Schema the model must satisfy, echoed to the tool caller. */
export const DECISION_SCHEMA = {
  symbol: 'one of the brief symbols',
  action: 'long | short | flat',
  sizePct: '1-100: percent of AI equity used as notional',
  confidence: '0-1: probability this decision makes money',
  stopPct: '0.2-20: stop distance from entry, percent',
  takePct: '0-50: take-profit distance, 0 for none',
  horizonHours: '1-240: how long the thesis stays valid',
  thesis: 'one or two sentences a reviewer could falsify',
  invalidation: 'the observable event that proves the thesis wrong',
}

/**
 * Validate and normalise one model decision.
 * @param {Record<string, unknown>} raw
 * @param {{ symbols: string[] }} context
 */
export function normalizeDecision(raw: Record<string, unknown>, { symbols }: { symbols: string[] }): AgentDecision {
  const problems: string[] = []
  const symbol = String(raw.symbol ?? '').toUpperCase()
  if (!symbols.includes(symbol)) problems.push(`symbol must be one of ${symbols.join(', ')}`)
  const action = String(raw.action ?? '').toLowerCase()
  if (!(AI_ACTIONS as readonly string[]).includes(action)) problems.push('action must be long, short, or flat')

  const confidence = Number(raw.confidence)
  if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) problems.push('confidence must be between 0 and 1')

  const sizePct = action === 'flat' ? 0 : Number(raw.sizePct)
  if (action !== 'flat' && (!Number.isFinite(sizePct) || sizePct <= 0 || sizePct > 100)) {
    problems.push('sizePct must be between 1 and 100 for a directional decision')
  }

  const stopPct = action === 'flat' ? 0 : Number(raw.stopPct)
  if (action !== 'flat' && (!Number.isFinite(stopPct) || stopPct < 0.2 || stopPct > 20)) {
    problems.push('stopPct must be between 0.2 and 20 for a directional decision')
  }

  const takePct = Number(raw.takePct ?? 0)
  if (!Number.isFinite(takePct) || takePct < 0 || takePct > 50) problems.push('takePct must be between 0 and 50')

  const horizonHours = Number(raw.horizonHours)
  if (!Number.isFinite(horizonHours) || horizonHours < 1 || horizonHours > 240) problems.push('horizonHours must be between 1 and 240')

  const thesisInput = raw.thesis
  let thesis = ''
  try { thesis = normalizeUntrustedText(thesisInput, 800) } catch (error) {
    problems.push(typeof thesisInput === 'string' && error instanceof Error ? error.message : 'thesis must be a string')
  }
  if (thesis.length < 20) problems.push('thesis must be at least 20 characters so it can be reviewed')

  const invalidationInput = raw.invalidation
  let invalidation = ''
  try { invalidation = normalizeUntrustedText(invalidationInput, 400) } catch (error) {
    problems.push(typeof invalidationInput === 'string' && error instanceof Error ? error.message : 'invalidation must be a string')
  }
  if (invalidation.length < 8) problems.push('invalidation must state the observable that proves the thesis wrong')

  if (problems.length > 0) {
    throw Object.assign(new Error(`decision rejected: ${problems.join('; ')}`), { problems })
  }

  return {
    symbol,
    action: action as DecisionAction,
    sizePct: round(sizePct, 2),
    confidence: round(confidence, 3),
    stopPct: round(stopPct, 2),
    takePct: round(takePct, 2),
    horizonHours: Math.round(horizonHours),
    thesis,
    invalidation,
  }
}

/**
 * Code-owned risk gate. Every limit is checked; the decision is accepted only
 * when all of them pass.
 * @param {{ decision: object, track: object, price: number, cfg: object, now?: number }} input
 */
export function riskGate({ decision, track, price, cfg }: { decision: AgentDecision, track: DecisionTrack, price: number, cfg: RiskConfig, now?: number }): RiskGateResult {
  const checks: RiskGateResult['checks'] = []
  const add = (name: string, ok: boolean, detail: string) => checks.push({ name, ok, detail })
  const equity = markedEquity(track, {}).equity

  if (decision.action === 'flat') {
    add('flatIsFree', true, 'flat closes any open position and costs nothing')
    return { allowed: true, checks, reasons: [] }
  }

  const riskPct = (decision.sizePct / 100) * (decision.stopPct / 100) * 100
  add(
    'perTradeRisk',
    riskPct <= cfg.aiRiskPerTradePct + 1e-9,
    `a stop hit would cost ${round(riskPct, 2)}% of equity (limit ${cfg.aiRiskPerTradePct}%)`,
  )

  add('positionCap', decision.sizePct <= cfg.aiMaxPositionPct, `size ${decision.sizePct}% (limit ${cfg.aiMaxPositionPct}%)`)

  const notional = (equity * decision.sizePct) / 100
  add('minNotional', notional >= 5, `notional ${round(notional, 2)} USDT (minimum 5)`)

  const otherOpen = Object.values(track.positions).filter(position => position.symbol !== decision.symbol)
  add(
    'openPositions',
    otherOpen.length + 1 <= cfg.aiMaxOpenPositions,
    `${otherOpen.length + 1} open (limit ${cfg.aiMaxOpenPositions})`,
  )

  const dayPnlPct = track.dayStartEquity > 0 ? ((equity - track.dayStartEquity) / track.dayStartEquity) * 100 : 0
  add('dailyLoss', dayPnlPct > -cfg.aiMaxDailyLossPct, `today ${round(dayPnlPct, 2)}% (limit -${cfg.aiMaxDailyLossPct}%)`)

  const drawdownPct = track.peakEquity > 0 ? ((track.peakEquity - equity) / track.peakEquity) * 100 : 0
  add('drawdown', drawdownPct < cfg.aiMaxDrawdownPct, `drawdown ${round(drawdownPct, 2)}% (limit ${cfg.aiMaxDrawdownPct}%)`)

  add('price', Number.isFinite(price) && price > 0, `mark ${price}`)

  return {
    allowed: checks.every(check => check.ok),
    checks,
    reasons: checks.filter(check => !check.ok).map(check => check.detail),
    notional: round(notional, 2),
    riskUsd: round((equity * riskPct) / 100, 2),
  }
}


export { AI_FEE_BPS, markedEquity, openPosition, closePosition, settleTrack, scoreTrack, downsampleCurve, recordDecision, rollDay, briefHashOf, compactContext } from './ai-accounting.js'
