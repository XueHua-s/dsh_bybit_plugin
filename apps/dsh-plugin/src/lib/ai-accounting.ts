/** Deterministic AI book accounting and journal scoring. */
import { createHash } from 'node:crypto'
import type { Candle } from './bybit.js'
import type {
  AgentDecision, DecisionResult, DecisionTrack, JournalDecision, MarketBrief, RiskGateResult, TrackPosition,
} from './ai-types.js'

export const AI_FEE_BPS = 6
const MAX_DECISIONS = 800
const BUCKETS = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001] as const

function dayKeyOf(timestamp: number): string {
  return new Date(timestamp).toISOString().slice(0, 10)
}

function mean(values: number[]): number {
  if (values.length === 0) return Number.NaN
  return values.reduce((sum, value) => sum + value, 0) / values.length
}
function round(value: number, digits: number): number {
  if (!Number.isFinite(value)) return 0
  const factor = 10 ** digits
  const rounded = Math.round(value * factor) / factor
  return Object.is(rounded, -0) ? 0 : rounded
}

/** Mark-to-market view of the AI track. */
export function markedEquity(track: DecisionTrack, marks: Record<string, number>) {
  let unrealized = 0
  const positions = Object.values(track.positions).map((position) => {
    const mark = marks[position.symbol] ?? position.entryPrice
    const pnl = position.notionalUsd * ((mark - position.entryPrice) / position.entryPrice) * (position.side === 'long' ? 1 : -1)
    unrealized += pnl
    return {
      ...position,
      markPrice: round(mark, 6),
      unrealizedPnlUsd: round(pnl, 2),
      unrealizedPct: round(((mark - position.entryPrice) / position.entryPrice) * 100 * (position.side === 'long' ? 1 : -1), 2),
    }
  })
  const equity = track.equity + unrealized
  return {
    equity: round(equity, 2),
    realizedEquity: round(track.equity, 2),
    unrealizedPnlUsd: round(unrealized, 2),
    totalReturnPct: track.startEquity > 0 ? round(((equity - track.startEquity) / track.startEquity) * 100, 2) : 0,
    maxDrawdownPct: round(track.maxDrawdownPct, 2),
    feesPaidUsd: round(track.feesPaidUsd, 2),
    positions,
  }
}

/**
 * Open a position for one accepted decision; an opposite position on the same
 * symbol is closed first.
 * @param {{ track: object, decision: object, price: number, now?: number, feeBps?: number }} input
 */
export function openPosition({ track, decision, price, now = Date.now(), feeBps = AI_FEE_BPS }: {
  track: DecisionTrack, decision: JournalDecision, price: number, now?: number, feeBps?: number,
}): TrackPosition {
  if (decision.action === 'flat') throw new Error('cannot open a position for a flat decision')
  if (track.positions[decision.symbol] !== undefined) {
    closePosition({ track, symbol: decision.symbol, price, reason: 'replaced', now, feeBps })
  }
  const equity = markedEquity(track, {}).equity
  const notional = (equity * decision.sizePct) / 100
  const fee = (notional * feeBps) / 10_000
  track.equity -= fee
  track.feesPaidUsd += fee
  const direction = decision.action === 'long' ? 1 : -1
  const position = {
    symbol: decision.symbol,
    side: decision.action,
    entryPrice: round(price, 6),
    notionalUsd: round(notional, 2),
    qty: round(notional / price, 8),
    stopPrice: round(price * (1 - (direction * decision.stopPct) / 100), 6),
    takePrice: decision.takePct > 0 ? round(price * (1 + (direction * decision.takePct) / 100), 6) : null,
    openedAt: now,
    horizonHours: decision.horizonHours,
    decisionId: decision.id,
    entryFeeUsd: round(fee, 4),
  }
  track.positions[decision.symbol] = position
  track.equityCurve.push({ t: now, e: round(markedEquity(track, {}).equity, 2) })
  return position
}

/**
 * Close one symbol's position at `price` and attach the outcome to its decision.
 * @param {{ track: object, symbol: string, price: number, reason: string, now?: number, feeBps?: number }} input
 */
export function closePosition({ track, symbol, price, reason, now = Date.now(), feeBps = AI_FEE_BPS }: {
  track: DecisionTrack, symbol: string, price: number, reason: string, now?: number, feeBps?: number,
}) {
  const position = track.positions[symbol]
  if (position === undefined) return null
  const exitNotional = position.qty * price
  const fee = (exitNotional * feeBps) / 10_000
  const gross = position.notionalUsd * ((price - position.entryPrice) / position.entryPrice) * (position.side === 'long' ? 1 : -1)
  const net = gross - fee
  track.equity += net
  track.feesPaidUsd += fee
  delete track.positions[symbol]
  const pnlPct = (net / position.notionalUsd) * 100
  track.peakEquity = Math.max(track.peakEquity, track.equity)
  const drawdown = track.peakEquity > 0 ? ((track.peakEquity - track.equity) / track.peakEquity) * 100 : 0
  track.maxDrawdownPct = Math.max(track.maxDrawdownPct, drawdown)
  track.equityCurve.push({ t: now, e: round(track.equity, 2) })
  const decision = track.decisions.find(entry => entry.id === position.decisionId)
  if (decision !== undefined) {
    decision.status = 'closed'
    decision.result = {
      exitPrice: round(price, 6),
      exitTime: now,
      reason,
      pnlUsd: round(net, 2),
      pnlPct: round(pnlPct, 3),
      rMultiple: decision.stopPct > 0 ? round(pnlPct / decision.stopPct, 2) : null,
      bars: Math.round((now - position.openedAt) / 3_600_000),
    }
  }
  return { symbol, side: position.side, entryPrice: position.entryPrice, exitPrice: round(price, 6), pnlUsd: round(net, 2), pnlPct: round(pnlPct, 3), reason }
}

/**
 * Settle open positions against fresh 1h candles: stop first, then take, then
 * the decision's horizon.
 * @param {{ track: object, barsBySymbol: Record<string, Array<object>>, marks: Record<string, number>, now?: number, feeBps?: number }} input
 */
export function settleTrack({ track, barsBySymbol, marks, now = Date.now(), feeBps = AI_FEE_BPS }: {
  track: DecisionTrack, barsBySymbol: Record<string, Candle[]>, marks: Record<string, number>, now?: number, feeBps?: number,
}) {
  const closed = []
  for (const [symbol, position] of Object.entries({ ...track.positions })) {
    const bars = (barsBySymbol[symbol] ?? []).filter(bar => bar.t > position.openedAt)
    let exit = null
    for (const bar of bars) {
      if (position.side === 'long') {
        if (bar.l <= position.stopPrice) { exit = { price: position.stopPrice, reason: 'stop', at: bar.t }; break }
        if (position.takePrice !== null && bar.h >= position.takePrice) { exit = { price: position.takePrice, reason: 'take', at: bar.t }; break }
      } else {
        if (bar.h >= position.stopPrice) { exit = { price: position.stopPrice, reason: 'stop', at: bar.t }; break }
        if (position.takePrice !== null && bar.l <= position.takePrice) { exit = { price: position.takePrice, reason: 'take', at: bar.t }; break }
      }
    }
    if (exit === null) {
      const deadline = position.openedAt + position.horizonHours * 3_600_000
      if (now >= deadline) {
        const lastBar = bars.at(-1)
        exit = { price: lastBar?.c ?? marks[symbol] ?? position.entryPrice, reason: 'horizon', at: now }
      }
    }
    if (exit === null) continue
    const result = closePosition({ track, symbol, price: exit.price, reason: exit.reason, now: Math.min(now, exit.at), feeBps })
    if (result !== null) closed.push(result)
  }
  return closed
}

/**
 * Scorecard over the journal: hit rate, expectancy, calibration, and the equity
 * curve's drawdown.
 * @param {{ track: object, marks?: Record<string, number> }} input
 */
export function scoreTrack({ track, marks = {} }: { track: DecisionTrack, marks?: Record<string, number> }) {
  const directional = track.decisions.filter(entry => entry.action !== 'flat')
  const closed = directional.filter((entry): entry is JournalDecision & { result: DecisionResult } => entry.status === 'closed' && entry.result !== null)
  const wins = closed.filter(entry => entry.result.pnlUsd > 0)
  const losses = closed.filter(entry => entry.result.pnlUsd <= 0)
  const grossWin = wins.reduce((sum, entry) => sum + entry.result.pnlUsd, 0)
  const grossLoss = losses.reduce((sum, entry) => sum + Math.abs(entry.result.pnlUsd), 0)
  const rMultiples = closed.map(entry => entry.result.rMultiple).filter(value => typeof value === 'number')
  const brierSamples = closed.filter(entry => typeof entry.confidence === 'number')
  const brier = brierSamples.length === 0
    ? null
    : round(mean(brierSamples.map(entry => (entry.confidence - (entry.result.pnlUsd > 0 ? 1 : 0)) ** 2)), 4)

  const calibration = []
  for (let index = 0; index < BUCKETS.length - 1; index += 1) {
    const low = BUCKETS[index]
    const high = BUCKETS[index + 1]
    if (low === undefined || high === undefined) continue
    const bucket = brierSamples.filter(entry => entry.confidence >= low && entry.confidence < high)
    if (bucket.length === 0) continue
    calibration.push({
      range: `${Math.round(low * 100)}-${Math.round(Math.min(high, 1) * 100)}%`,
      count: bucket.length,
      avgConfidence: round(mean(bucket.map(entry => entry.confidence)), 3),
      hitRate: round(bucket.filter(entry => entry.result.pnlUsd > 0).length / bucket.length, 3),
    })
  }

  return {
    decisions: track.decisions.length,
    directional: directional.length,
    flat: track.decisions.length - directional.length,
    closed: closed.length,
    open: Object.keys(track.positions).length,
    hitRatePct: closed.length === 0 ? null : round((wins.length / closed.length) * 100, 1),
    avgPnlPct: closed.length === 0 ? null : round(mean(closed.map(entry => entry.result.pnlPct)), 3),
    avgRMultiple: rMultiples.length === 0 ? null : round(mean(rMultiples), 2),
    expectancyUsd: closed.length === 0 ? null : round(mean(closed.map(entry => entry.result.pnlUsd)), 3),
    // null means "no losing trade yet", so the ratio is undefined rather than infinite.
    profitFactor: grossLoss === 0 ? null : round(grossWin / grossLoss, 2),
    brier,
    calibration,
    book: markedEquity(track, marks),
    curve: downsampleCurve(track.equityCurve, 120),
  }
}

/** Keep the equity curve readable in a tool result. */
export function downsampleCurve<T>(points: T[], limit: number): T[] {
  if (points.length <= limit) return points
  const step = (points.length - 1) / (limit - 1)
  const result: T[] = []
  for (let index = 0; index < limit; index += 1) {
    const point = points[Math.round(index * step)]
    if (point !== undefined) result.push(point)
  }
  return result
}

/** Append a decision to the journal and return it with an id. */
export function recordDecision(track: DecisionTrack, decision: AgentDecision, { price, now = Date.now(), briefHash, context, gate, status }: {
  price: number, now?: number, briefHash: string, context: unknown, gate: RiskGateResult | null, status: JournalDecision['status'],
}): JournalDecision {
  const entry = {
    id: `${now.toString(36)}-${(track.decisions.length + 1).toString(36)}`,
    time: now,
    ...decision,
    priceAtDecision: round(price, 6),
    briefHash,
    context,
    status,
    gate: gate === undefined || gate === null ? null : { allowed: gate.allowed, reasons: gate.reasons },
    result: null,
  }
  track.decisions.push(entry)
  if (track.decisions.length > MAX_DECISIONS) track.decisions.splice(0, track.decisions.length - MAX_DECISIONS)
  return entry
}

/** Reset the daily loss anchor when the UTC day changes. */
export function rollDay(track: DecisionTrack, equity: number, now = Date.now()): void {
  const key = dayKeyOf(now)
  if (track.dayKey === key) return
  track.dayKey = key
  track.dayStartEquity = equity
}

/** Stable short hash of the brief a decision was made from. */
export function briefHashOf(brief: unknown): string {
  return createHash('sha256').update(JSON.stringify(brief)).digest('hex').slice(0, 12)
}

/** Compact per-symbol context stored in the journal. */
export function compactContext(brief: MarketBrief) {
  return {
    at: brief.at,
    symbols: brief.symbols.map(item => ({
      symbol: item.symbol,
      price: item.price,
      primary: item.primary,
      fundingRatePct: item.fundingRatePct,
      bookImbalancePct: item.book?.imbalancePct ?? null,
      spreadBps: item.book?.spreadBps ?? null,
    })),
  }
}
