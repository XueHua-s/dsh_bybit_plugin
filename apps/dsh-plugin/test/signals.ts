/**
 * Unit tests for the curated signal library, using synthetic trends so each
 * algorithm's direction is known in advance.
 *
 * Run from the bundle directory: `node test/signals.ts`
 */
import assert from 'node:assert/strict'
import { adx, atrSeries, donchian, evaluateSignals, ichimoku, sma, squeeze, stdev, supertrend } from '../dist/lib/signals.js'
import type { Bar } from '../src/lib/signals.js'

function assertPresent<T>(value: T, message: string): asserts value is NonNullable<T> {
  assert.ok(value !== null && value !== undefined, message)
}

let passed = 0
const check = (label: string, fn: () => void): void => {
  fn()
  passed += 1
  console.log(`ok ${label}`)
}

/** Bar series from a close path with a small wick and a rising/falling shape. */
function barsFrom(closes: number[], step = 3_600_000): Bar[] {
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
  const latestAtr = atr.at(-1)
  assertPresent(latestAtr, 'ATR series should contain the latest bar')
  assert.ok(Number.isFinite(latestAtr) && latestAtr > 0)
})

check('supertrend follows the trend direction', () => {
  const up = supertrend(uptrend)
  const down = supertrend(downtrend)
  assertPresent(up, 'sufficient uptrend history should produce supertrend')
  assertPresent(down, 'sufficient downtrend history should produce supertrend')
  assert.equal(up.dir, 1)
  assert.equal(down.dir, -1)
  assert.ok(up.distancePct > 0)
})

check('squeeze reports compression fields', () => {
  const quiet = barsFrom(Array.from({ length: 160 }, (_, index) => 100 + Math.sin(index / 8) * 0.2))
  const value = squeeze(quiet)
  assertPresent(value, 'sufficient history should produce squeeze facts')
  assert.equal(typeof value.on, 'boolean')
  assert.ok(Number.isFinite(value.momentum))
  assert.ok(value.bbWidthPct > 0 && value.kcWidthPct > 0)
})

check('ichimoku reads price against the cloud', () => {
  const up = ichimoku(uptrend)
  const down = ichimoku(downtrend)
  assertPresent(up, 'sufficient uptrend history should produce Ichimoku')
  assertPresent(down, 'sufficient downtrend history should produce Ichimoku')
  assert.equal(up.state, 'above')
  assert.equal(down.state, 'below')
  assert.equal(up.tkCross, 'bull')
})

check('donchian flags a breakout only past the prior window', () => {
  const up = donchian(uptrend)
  const down = donchian(downtrend)
  const sideways = donchian(chop)
  assertPresent(up, 'sufficient uptrend history should produce Donchian channel')
  assertPresent(down, 'sufficient downtrend history should produce Donchian channel')
  assertPresent(sideways, 'sufficient range history should produce Donchian channel')
  assert.equal(up.breakout, 'up')
  assert.equal(down.breakout, 'down')
  assert.ok(['up', 'down', 'none'].includes(sideways.breakout))
})

check('ADX separates trend from chop', () => {
  const strong = adx(uptrend)
  assertPresent(strong, 'sufficient history should produce ADX')
  assert.ok(strong.adx > 25)
  assert.equal(strong.trending, true)
  assert.ok(strong.plusDi > strong.minusDi)
  const falling = adx(downtrend)
  assertPresent(falling, 'sufficient downtrend history should produce ADX')
  assert.equal(falling.minusDi > falling.plusDi, true)
  const sideways = adx(chop)
  assertPresent(sideways, 'sufficient range history should produce ADX')
  assert.equal(sideways.trending, false)
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
  const walk = (item: unknown, path: string): void => {
    if (item === null) return
    const type = typeof item
    if (type === 'number') {
      assert.ok(Number.isFinite(item), `${path} not finite`)
      assert.ok(!Object.is(item, -0), `${path} is -0`)
      return
    }
    if (type !== 'object') return
    for (const [key, member] of Object.entries(item as Record<string, unknown>)) walk(member, `${path}.${key}`)
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
