/**
 * The AI decision track: a structured market brief, a strict decision schema, a
 * code-owned risk gate, and a journal of every verdict with its outcome.
 *
 * The model supplies the thesis; this module supplies the arithmetic. It never
 * trusts a decision: position size is bounded by the risk budget, a stop must
 * exist, and every accepted decision is written to the journal so a later
 * review can check whether the confidence was earned.
 */
import { createHash } from 'node:crypto'
import { evaluateSignals } from './signals.js'

/** Fee charged on each side of a simulated AI fill, in basis points. */
export const AI_FEE_BPS = 6

/** Actions the decision schema accepts. */
export const AI_ACTIONS = ['long', 'short', 'flat']

/** Retained journal entries. */
const MAX_DECISIONS = 800
/** Confidence buckets for calibration. */
const BUCKETS = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]

/** Fresh track for one configuration. */
export function createTrack(startEquity, now = Date.now()) {
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
export function dayKeyOf(ms) {
  return new Date(ms).toISOString().slice(0, 10)
}

/** Mean of a numeric slice, NaN when empty. */
function mean(values) {
  if (values.length === 0) return Number.NaN
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

/** True range of one bar against the previous close. */
function trueRange(bar, previousClose) {
  return Math.max(bar.h - bar.l, Math.abs(bar.h - previousClose), Math.abs(bar.l - previousClose))
}

/**
 * Wilder's average true range, or NaN without enough history.
 * @param {Array<{ h: number, l: number, c: number }>} bars oldest-first
 * @param {number} period
 */
export function atr(bars, period = 14) {
  if (bars.length < period + 1) return Number.NaN
  let sum = 0
  for (let index = 1; index <= period; index += 1) sum += trueRange(bars[index], bars[index - 1].c)
  let value = sum / period
  for (let index = period + 1; index < bars.length; index += 1) {
    value = (value * (period - 1) + trueRange(bars[index], bars[index - 1].c)) / period
  }
  return value
}

/** Percentage change over `bars` bars, NaN when the window is short. */
function changePct(closes, bars) {
  const last = closes.at(-1)
  const then = closes.at(-1 - bars)
  if (last === undefined || then === undefined || then === 0) return Number.NaN
  return ((last - then) / then) * 100
}

/**
 * Trend and structure facts for one timeframe.
 * @param {Array<{ o: number, h: number, l: number, c: number }>} bars oldest-first
 */
export function trendState(bars) {
  if (bars.length < 25) return { bars: bars.length, state: 'range', note: 'not enough bars' }
  const closes = bars.map(bar => bar.c)
  const last = closes.at(-1)
  const sma20 = mean(closes.slice(-20))
  const sma50 = closes.length >= 50 ? mean(closes.slice(-50)) : Number.NaN
  const sma200 = closes.length >= 200 ? mean(closes.slice(-200)) : Number.NaN
  const window = bars.slice(-20)
  const high20 = Math.max(...window.map(bar => bar.h))
  const low20 = Math.min(...window.map(bar => bar.l))
  const atrValue = atr(bars)
  const state = Number.isNaN(sma50)
    ? 'range'
    : last > sma50 && sma20 > sma50 ? 'up'
      : last < sma50 && sma20 < sma50 ? 'down'
        : 'range'
  return {
    bars: bars.length,
    state,
    close: round(last, 6),
    sma20: round(sma20, 6),
    sma50: Number.isNaN(sma50) ? null : round(sma50, 6),
    sma200: Number.isNaN(sma200) ? null : round(sma200, 6),
    atrPct: round((atrValue / last) * 100, 3),
    rangePosPct: high20 === low20 ? 50 : round(((last - low20) / (high20 - low20)) * 100, 1),
    high20: round(high20, 6),
    low20: round(low20, 6),
    retPct: {
      bars5: round(changePct(closes, 5), 2),
      bars20: round(changePct(closes, 20), 2),
      bars60: round(changePct(closes, 60), 2),
    },
  }
}

/**
 * Current volatility against its own recent average.
 * @param {Array<{ h: number, l: number, c: number }>} bars oldest-first
 */
export function volRegime(bars) {
  if (bars.length < 80) return { regime: 'unknown', atrPct: null, ratio: null }
  const last = bars.at(-1)
  const current = atr(bars) / last.c
  const samples = []
  for (let index = bars.length - 60; index < bars.length; index += 10) {
    const slice = bars.slice(0, index + 1)
    const value = atr(slice)
    if (Number.isFinite(value)) samples.push(value / slice.at(-1).c)
  }
  const baseline = mean(samples)
  const ratio = baseline > 0 ? current / baseline : Number.NaN
  const regime = ratio > 1.4 ? 'high' : ratio < 0.7 ? 'low' : 'normal'
  return { regime, atrPct: round(current * 100, 3), ratio: round(ratio, 2) }
}

/**
 * Order-flow imbalance and spread from a top-of-book snapshot.
 * @param {{ bids: number[][], asks: number[][] }} book
 */
export function bookPressure(book) {
  const bidVolume = book.bids.reduce((sum, level) => sum + level[1], 0)
  const askVolume = book.asks.reduce((sum, level) => sum + level[1], 0)
  const total = bidVolume + askVolume
  const bestBid = book.bids[0]?.[0]
  const bestAsk = book.asks[0]?.[0]
  return {
    bidVolume: round(bidVolume, 3),
    askVolume: round(askVolume, 3),
    imbalancePct: total === 0 ? 0 : round(((bidVolume - askVolume) / total) * 100, 1),
    spreadBps: bestBid > 0 && bestAsk > 0 ? round(((bestAsk - bestBid) / bestBid) * 10_000, 2) : null,
  }
}

/**
 * One symbol's multi-timeframe brief.
 * @param {{ client: any, symbol: string, category: string, timeframes?: string[], signal?: AbortSignal }} input
 */
export async function buildSymbolBrief({ client, symbol, category, timeframes = ['240', '60', 'D'], signal }) {
  const [ticker, book, funding, instrument] = await Promise.all([
    client.ticker({ category, symbol, signal }),
    client.orderbook({ category, symbol, limit: 20, signal }),
    category === 'linear' ? client.funding({ category, symbol, limit: 3, signal }) : Promise.resolve([]),
    client.instrument({ category, symbol, signal }).catch(() => null),
  ])
  const frames = {}
  let primaryBars = []
  for (const interval of timeframes) {
    const bars = await client.klines({ category, symbol, interval, limit: 240, signal })
    if (interval === timeframes[0]) primaryBars = bars
    frames[interval] = {
      ...trendState(bars),
      vol: volRegime(bars),
    }
  }
  const signals = primaryBars.length >= 80 ? evaluateSignals(primaryBars) : null
  const primary = frames[timeframes[0]] ?? {}
  return {
    symbol,
    category,
    price: ticker.last,
    change24hPct: round(ticker.change24hPct, 2),
    high24h: ticker.high24h,
    low24h: ticker.low24h,
    turnover24hUsd: Math.round(ticker.turnover24h ?? 0),
    fundingRatePct: ticker.fundingRate === undefined ? null : round(ticker.fundingRate, 4),
    fundingHistoryPct: funding.map(row => round(row.ratePct, 4)),
    openInterest: ticker.openInterest ?? null,
    book: bookPressure(book),
    qtyStep: instrument?.qtyStep ?? null,
    minNotionalUsd: instrument?.minNotionalUsd ?? null,
    frames,
    primary: {
      interval: timeframes[0],
      state: primary.state ?? 'range',
      atrPct: primary.atrPct ?? null,
      volRegime: primary.vol?.regime ?? 'unknown',
      rangePosPct: primary.rangePosPct ?? null,
      signals: signals === null ? null : { bias: signals.bias, score: signals.score, notes: signals.notes },
    },
    signals,
    roundTripCostBps: AI_FEE_BPS * 2,
  }
}

/**
 * Whole-book brief plus the risk limits the decision must respect.
 * @param {{ client: any, symbols: string[], category: string, timeframes?: string[], signal?: AbortSignal, limits: object }} input
 */
export async function buildBrief({ client, symbols, category, timeframes, signal, limits }) {
  const items = []
  for (const symbol of symbols) {
    items.push(await buildSymbolBrief({ client, symbol, category, timeframes, signal }))
  }
  return {
    at: new Date().toISOString(),
    category,
    timeframes: timeframes ?? ['240', '60', 'D'],
    symbols: items,
    limits,
    instruction: 'Pick at most one action per symbol from long/short/flat. Size so that a stop hit costs no more than the per-trade risk budget. Every decision needs a falsifiable invalidation. Flat is a valid decision and costs nothing.',
  }
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
export function normalizeDecision(raw, { symbols }) {
  const problems = []
  const symbol = String(raw.symbol ?? '').toUpperCase()
  if (!symbols.includes(symbol)) problems.push(`symbol must be one of ${symbols.join(', ')}`)
  const action = String(raw.action ?? '').toLowerCase()
  if (!AI_ACTIONS.includes(action)) problems.push('action must be long, short, or flat')

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

  const thesis = String(raw.thesis ?? '').trim()
  if (thesis.length < 20) problems.push('thesis must be at least 20 characters so it can be reviewed')
  if (thesis.length > 800) problems.push('thesis must be at most 800 characters')

  const invalidation = String(raw.invalidation ?? '').trim()
  if (invalidation.length < 8) problems.push('invalidation must state the observable that proves the thesis wrong')
  if (invalidation.length > 400) problems.push('invalidation must be at most 400 characters')

  if (problems.length > 0) {
    const error = new Error(`decision rejected: ${problems.join('; ')}`)
    error.problems = problems
    throw error
  }

  return {
    symbol,
    action,
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
export function riskGate({ decision, track, price, cfg }) {
  const checks = []
  const add = (name, ok, detail) => checks.push({ name, ok, detail })
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

/** Mark-to-market view of the AI track. */
export function markedEquity(track, marks) {
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
export function openPosition({ track, decision, price, now = Date.now(), feeBps = AI_FEE_BPS }) {
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
export function closePosition({ track, symbol, price, reason, now = Date.now(), feeBps = AI_FEE_BPS }) {
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
export function settleTrack({ track, barsBySymbol, marks, now = Date.now(), feeBps = AI_FEE_BPS }) {
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
export function scoreTrack({ track, marks = {} }) {
  const directional = track.decisions.filter(entry => entry.action !== 'flat')
  const closed = directional.filter(entry => entry.status === 'closed' && entry.result !== undefined)
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
export function downsampleCurve(points, limit) {
  if (points.length <= limit) return points
  const step = (points.length - 1) / (limit - 1)
  return Array.from({ length: limit }, (_, index) => points[Math.round(index * step)])
}

/** Append a decision to the journal and return it with an id. */
export function recordDecision(track, decision, { price, now = Date.now(), briefHash, context, gate, status }) {
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
export function rollDay(track, equity, now = Date.now()) {
  const key = dayKeyOf(now)
  if (track.dayKey === key) return
  track.dayKey = key
  track.dayStartEquity = equity
}

/** Stable short hash of the brief a decision was made from. */
export function briefHashOf(brief) {
  return createHash('sha256').update(JSON.stringify(brief)).digest('hex').slice(0, 12)
}

/** Compact per-symbol context stored in the journal. */
export function compactContext(brief) {
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

/** Round for display. */
function round(value, digits) {
  if (!Number.isFinite(value)) return 0
  const factor = 10 ** digits
  const rounded = Math.round(value * factor) / factor
  return Object.is(rounded, -0) ? 0 : rounded
}
