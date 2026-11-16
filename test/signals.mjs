/**
 * Unit tests for the curated signal library, using synthetic trends so each
 * algorithm's direction is known in advance.
 *
 * Run from the bundle directory: `node test/signals.mjs`
 */
import assert from 'node:assert/strict'
import { adx, atrSeries, donchian, evaluateSignals, ichimoku, sma, squeeze, stdev, supertrend } from '../dist/lib/signals.js'

let passed = 0
const check = (label, fn) => {
  fn()
  passed += 1
  console.log(`ok ${label}`)
}

/** Bar series from a close path with a small wick and a rising/falling shape. */
function barsFrom(closes, step = 3_600_000) {
  return closes.map((close, index) => ({
    t: 1_700_000_000_000 + index * step,
    o: close, h: close * 1.004, l: close * 0.996, c: close, v: 10,
  }))
}

const uptrend = barsFrom(Array.from({ length: 160 }, (_, index) => 100 + index * 2))
const downtrend = barsFrom(Array.from({ length: 160 }, (_, index) => 400 - index * 2))
const chop = barsFrom(Array.from({ length: 160 }, (_, index) => 100 + Math.sin(index / 2) * 1.5))

check('moving average and deviation basics', () => {
  assert.equal(sma([1, 2, 3, 4], 2).at(-1), 3.5)
  assert.ok(Math.abs(stdev([2, 4, 4, 4, 5, 5, 7, 9]) - 2) < 1e-9)
  const atr = atrSeries(uptrend, 14)
  assert.ok(Number.isFinite(atr.at(-1)) && atr.at(-1) > 0)
})

check('supertrend follows the trend direction', () => {
  assert.equal(supertrend(uptrend).dir, 1)
  assert.equal(supertrend(downtrend).dir, -1)
  assert.ok(supertrend(uptrend).distancePct > 0)
})

check('squeeze reports compression fields', () => {
  const quiet = barsFrom(Array.from({ length: 160 }, (_, index) => 100 + Math.sin(index / 8) * 0.2))
  const value = squeeze(quiet)
  assert.equal(typeof value.on, 'boolean')
  assert.ok(Number.isFinite(value.momentum))
  assert.ok(value.bbWidthPct > 0 && value.kcWidthPct > 0)
})

check('ichimoku reads price against the cloud', () => {
  assert.equal(ichimoku(uptrend).state, 'above')
  assert.equal(ichimoku(downtrend).state, 'below')
  assert.equal(ichimoku(uptrend).tkCross, 'bull')
})

check('donchian flags a breakout only past the prior window', () => {
  assert.equal(donchian(uptrend).breakout, 'up')
  assert.equal(donchian(downtrend).breakout, 'down')
  assert.ok(['up', 'down', 'none'].includes(donchian(chop).breakout))
})

check('ADX separates trend from chop', () => {
  const strong = adx(uptrend)
  assert.ok(strong.adx > 25)
  assert.equal(strong.trending, true)
  assert.ok(strong.plusDi > strong.minusDi)
  assert.equal(adx(downtrend).minusDi > adx(downtrend).plusDi, true)
  assert.equal(adx(chop).trending, false)
})

check('consensus is directional on trends and neutral in chop', () => {
  const up = evaluateSignals(uptrend)
  assert.ok(up.score >= 0.3, `score ${up.score}`)
  assert.equal(up.bias, 'long')
  assert.ok(up.notes.length > 0)

  const down = evaluateSignals(downtrend)
  assert.ok(down.score <= -0.3, `score ${down.score}`)
  assert.equal(down.bias, 'short')

  const flat = evaluateSignals(chop)
  assert.ok(Math.abs(flat.score) < 0.6)
  assert.ok(['long', 'short', 'flat'].includes(flat.bias))
})

check('signals are JSON-safe', () => {
  const value = evaluateSignals(uptrend)
  const walk = (item, path) => {
    if (item === null) return
    const type = typeof item
    if (type === 'number') {
      assert.ok(Number.isFinite(item), `${path} not finite`)
      assert.ok(!Object.is(item, -0), `${path} is -0`)
      return
    }
    if (type !== 'object') return
    for (const [key, member] of Object.entries(item)) walk(member, `${path}.${key}`)
  }
  walk(value, 'signals')
})

check('short series return null instead of throwing', () => {
  const short = barsFrom([100, 101, 102])
  assert.equal(supertrend(short), null)
  assert.equal(ichimoku(short), null)
  assert.equal(evaluateSignals(short).bias, 'flat')
})

console.log(`\n${passed} signal checks passed\n`)
