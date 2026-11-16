/**
 * Unit tests for the AI track: indicator facts, the decision schema, the
 * code-owned risk gate, position accounting, stop/take/horizon settlement, and
 * the scorecard. Pure functions and synthetic candles only.
 *
 * Run from the bundle directory: `node test/ai.mjs`
 */
import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import {
  atr, bookPressure, briefHashOf, closePosition, createTrack, markedEquity, normalizeDecision,
  openPosition, recordDecision, riskGate, scoreTrack, settleTrack, trendState, volRegime,
} from '../dist/lib/ai.js'
import { createStore } from '../dist/lib/state.js'

let passed = 0
const check = (label, fn) => {
  fn()
  passed += 1
  console.log(`ok ${label}`)
}

/** Bars from a close series with a fixed 1% wick. */
function barsFrom(closes, start = 1_700_000_000_000, step = 3_600_000) {
  return closes.map((close, index) => ({
    t: start + index * step, o: close, h: close * 1.01, l: close * 0.99, c: close, v: 10,
  }))
}

const settings = {
  aiRiskPerTradePct: 1,
  aiMaxPositionPct: 50,
  aiMaxOpenPositions: 2,
  aiMaxDailyLossPct: 3,
  aiMaxDrawdownPct: 20,
}

check('trend state reads a rising market as up', () => {
  const closes = Array.from({ length: 120 }, (_, index) => 100 + index * 0.5)
  const state = trendState(barsFrom(closes))
  assert.equal(state.state, 'up')
  assert.ok(state.sma20 > state.sma50)
  assert.ok(state.atrPct > 0)
  assert.ok(state.rangePosPct >= 0 && state.rangePosPct <= 100)
})

check('trend state reads a falling market as down', () => {
  const closes = Array.from({ length: 120 }, (_, index) => 200 - index * 0.5)
  assert.equal(trendState(barsFrom(closes)).state, 'down')
})

check('volatility regime scales with the candles', () => {
  const quiet = barsFrom(Array.from({ length: 160 }, (_, index) => 100 + Math.sin(index / 5) * 0.05))
  const wild = barsFrom(Array.from({ length: 160 }, (_, index) => 100 + Math.sin(index / 5) * 8))
  assert.ok(['low', 'normal'].includes(volRegime(quiet).regime))
  assert.ok(['normal', 'high'].includes(volRegime(wild).regime))
  assert.ok(volRegime(wild).atrPct > volRegime(quiet).atrPct)
})

check('ATR is finite and positive', () => {
  const value = atr(barsFrom(Array.from({ length: 40 }, (_, index) => 100 + index)))
  assert.ok(Number.isFinite(value) && value > 0)
})

check('book pressure reports imbalance and spread', () => {
  const pressure = bookPressure({ bids: [[100, 3], [99.9, 2]], asks: [[100.1, 1], [100.2, 1]] })
  assert.ok(pressure.imbalancePct > 0)
  assert.ok(pressure.spreadBps > 0)
})

const baseDecision = {
  symbol: 'BTCUSDT', action: 'long', sizePct: 10, confidence: 0.62, stopPct: 1.5, takePct: 3,
  horizonHours: 24, thesis: 'higher timeframe trend up and funding is mild, buying the pullback',
  invalidation: 'a 4h close back below the 50 period average',
}

check('normalises a well-formed decision', () => {
  const decision = normalizeDecision(baseDecision, { symbols: ['BTCUSDT', 'ETHUSDT'] })
  assert.equal(decision.symbol, 'BTCUSDT')
  assert.equal(decision.action, 'long')
  assert.equal(decision.stopPct, 1.5)
})

check('rejects malformed decisions', () => {
  const bad = [
    { ...baseDecision, symbol: 'DOGEUSDT' },
    { ...baseDecision, action: 'buy' },
    { ...baseDecision, sizePct: 0 },
    { ...baseDecision, stopPct: 0.01 },
    { ...baseDecision, confidence: 1.4 },
    { ...baseDecision, horizonHours: 0 },
    { ...baseDecision, thesis: 'up' },
    { ...baseDecision, invalidation: 'nope' },
  ]
  for (const candidate of bad) {
    assert.throws(() => normalizeDecision(candidate, { symbols: ['BTCUSDT'] }), /decision rejected/)
  }
})

check('risk gate allows a decision inside every limit', () => {
  const track = createTrack(10_000)
  const gate = riskGate({ decision: normalizeDecision(baseDecision, { symbols: ['BTCUSDT'] }), track, price: 60_000, cfg: settings })
  assert.equal(gate.allowed, true, gate.reasons.join('; '))
  assert.ok(gate.checks.find(check => check.name === 'perTradeRisk').ok)
})

check('risk gate refuses too much size or too wide a stop', () => {
  const track = createTrack(10_000)
  const wide = normalizeDecision({ ...baseDecision, sizePct: 100, stopPct: 3 }, { symbols: ['BTCUSDT'] })
  const gate = riskGate({ decision: wide, track, price: 60_000, cfg: settings })
  assert.equal(gate.allowed, false)
  assert.ok(gate.reasons.length >= 2, 'both per-trade risk and position cap should fail')
})

check('risk gate stops trading after the daily loss limit', () => {
  const track = createTrack(10_000)
  track.equity = 9_600
  const gate = riskGate({ decision: normalizeDecision(baseDecision, { symbols: ['BTCUSDT'] }), track, price: 60_000, cfg: settings })
  assert.equal(gate.allowed, false)
  assert.ok(gate.reasons.some(reason => /today/.test(reason)))
})

check('risk gate stops trading after the drawdown limit', () => {
  const track = createTrack(10_000)
  track.equity = 7_000
  const gate = riskGate({ decision: normalizeDecision(baseDecision, { symbols: ['BTCUSDT'] }), track, price: 60_000, cfg: settings })
  assert.equal(gate.allowed, false)
  assert.ok(gate.reasons.some(reason => /drawdown/.test(reason)))
})

check('flat is always allowed and costs nothing', () => {
  const track = createTrack(1_000)
  track.equity = 200
  const gate = riskGate({ decision: normalizeDecision({ ...baseDecision, action: 'flat', sizePct: 0, stopPct: 0 }, { symbols: ['BTCUSDT'] }), track, price: 60_000, cfg: settings })
  assert.equal(gate.allowed, true)
})

check('opening and closing a position keeps the books consistent', () => {
  const track = createTrack(10_000)
  const decision = normalizeDecision(baseDecision, { symbols: ['BTCUSDT'] })
  const entry = recordDecision(track, decision, { price: 100, briefHash: 'abc', context: { at: 'x', symbols: [] }, gate: { allowed: true, reasons: [] }, status: 'open' })
  const position = openPosition({ track, decision: entry, price: 100, feeBps: 6 })
  assert.equal(position.notionalUsd, 1_000)
  assert.equal(position.stopPrice, 98.5)
  assert.equal(position.takePrice, 103)
  const before = markedEquity(track, { BTCUSDT: 110 })
  assert.ok(before.unrealizedPnlUsd > 0)
  const result = closePosition({ track, symbol: 'BTCUSDT', price: 110, reason: 'take', feeBps: 6 })
  assert.ok(result.pnlUsd > 90 && result.pnlUsd < 100, `pnl ${result.pnlUsd}`)
  assert.equal(track.positions.BTCUSDT, undefined)
  assert.equal(track.decisions[0].status, 'closed')
  assert.equal(track.decisions[0].result.reason, 'take')
})

check('settle closes on a stop, on a take, and at the horizon', () => {
  const entryTime = 1_700_000_000_000
  const build = (bars, now = entryTime + 6 * 3_600_000) => {
    const track = createTrack(10_000)
    const decision = normalizeDecision(baseDecision, { symbols: ['BTCUSDT'] })
    const entry = recordDecision(track, decision, { price: 100, briefHash: 'h', context: null, gate: null, status: 'open' })
    openPosition({ track, decision: entry, price: 100, now: entryTime, feeBps: 6 })
    return { track, closed: settleTrack({ track, barsBySymbol: { BTCUSDT: bars }, marks: { BTCUSDT: 100 }, now, feeBps: 6 }) }
  }
  const stop = build([{ t: entryTime + 3_600_000, o: 100, h: 101, l: 94, c: 95, v: 1 }])
  assert.equal(stop.closed[0].reason, 'stop')
  const take = build([{ t: entryTime + 3_600_000, o: 100, h: 112, l: 99, c: 111, v: 1 }])
  assert.equal(take.closed[0].reason, 'take')
  const horizon = build([{ t: entryTime + 3_600_000, o: 100, h: 101, l: 99, c: 100.5, v: 1 }], entryTime + 25 * 3_600_000)
  assert.equal(horizon.closed[0].reason, 'horizon')
})

check('scorecard reports hit rate, calibration, and drawdown', () => {
  const track = createTrack(10_000)
  const entries = [
    { confidence: 0.8, pnlUsd: 120, pnlPct: 1.2, rMultiple: 0.8, status: 'closed' },
    { confidence: 0.7, pnlUsd: -50, pnlPct: -0.5, rMultiple: -0.33, status: 'closed' },
    { confidence: 0.55, pnlUsd: 30, pnlPct: 0.3, rMultiple: 0.3, status: 'closed' },
    { confidence: 0.9, pnlUsd: 0, pnlPct: 0, rMultiple: 0, status: 'open' },
  ]
  for (const [index, item] of entries.entries()) {
    track.decisions.push({
      id: `d${index}`, time: Date.now(), symbol: 'BTCUSDT', action: 'long', sizePct: 10,
      confidence: item.confidence, stopPct: 1.5, takePct: 3, horizonHours: 24,
      thesis: 't', invalidation: 'i', priceAtDecision: 100, briefHash: 'h', context: null,
      status: item.status,
      result: item.status === 'closed' ? { pnlUsd: item.pnlUsd, pnlPct: item.pnlPct, rMultiple: item.rMultiple, reason: 'take' } : null,
    })
  }
  track.equity = 10_100
  track.maxDrawdownPct = 4.2
  const score = scoreTrack({ track })
  assert.equal(score.closed, 3)
  assert.equal(score.open, 0)
  assert.ok(score.hitRatePct > 60 && score.hitRatePct < 70)
  assert.ok(score.brier > 0 && score.brier < 1)
  assert.equal(score.calibration.length >= 2, true)
  assert.equal(score.book.totalReturnPct, 1)
})

check('brief hash is stable and short', () => {
  const hash = briefHashOf({ a: 1, b: [2, 3] })
  assert.equal(hash, briefHashOf({ a: 1, b: [2, 3] }))
  assert.equal(hash.length, 12)
})

check('the state file keeps the AI track and watchlist across a reload', () => {
  const directory = mkdtempSync(join(tmpdir(), 'bybit-quant-state-'))
  try {
    const file = join(directory, 'state.json')
    const store = createStore({ file, startingBalance: 1000 })
    store.mutate((state) => {
      state.ai = createTrack(1000)
      state.watchlist = ['BTCUSDT', 'AAPLUSDT']
      return null
    })
    const reopened = createStore({ file, startingBalance: 1000 })
    assert.equal(reopened.get().ai?.version, 1)
    assert.equal(reopened.get().ai?.startEquity, 1000)
    assert.deepEqual(reopened.get().watchlist, ['BTCUSDT', 'AAPLUSDT'])
  } finally {
    rmSync(directory, { recursive: true, force: true })
  }
})

console.log(`\n${passed} AI track checks passed\n`)
