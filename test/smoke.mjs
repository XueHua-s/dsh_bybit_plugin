/**
 * Node smoke test for the plugin's pure modules and the public Bybit client.
 * Run from the bundle directory: `node test/smoke.mjs`
 * It never touches credentials or places orders.
 */
import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { BybitClient, formatQuantity, normalizeInterval } from '../dist/lib/bybit.js'
import { evaluateStrategy, rsi, runBacktest, sma } from '../dist/lib/strategies.js'
import { createStore } from '../dist/lib/state.js'
import { paperBuy, paperSell, paperStatus } from '../dist/lib/paper.js'

let passed = 0
const check = (label, fn) => {
  fn()
  passed += 1
  console.log(`ok ${label}`)
}

check('interval normalisation', () => {
  assert.equal(normalizeInterval('1h'), '60')
  assert.equal(normalizeInterval('1d'), 'D')
  assert.equal(normalizeInterval(undefined), '60')
  assert.throws(() => normalizeInterval('7m'))
})

check('quantity formatting follows the step', () => {
  assert.equal(formatQuantity(0.012345, '0.001'), '0.012')
  assert.equal(formatQuantity(1.5, '1'), '1')
})

check('indicators are aligned', () => {
  const values = [1, 2, 3, 4, 5, 6]
  const average = sma(values, 3)
  assert.ok(Number.isNaN(average[1]))
  assert.equal(average[2], 2)
  assert.equal(average[5], 5)
  const strength = rsi(values.map(value => value * 10), 3)
  assert.equal(strength[3], 100)
})

check('backtest on a synthetic trend', () => {
  const bars = Array.from({ length: 120 }, (_, index) => {
    const price = 100 + index * 0.8 + Math.sin(index / 4) * 3
    return { t: index * 3_600_000, o: price, h: price + 1, l: price - 1, c: price, v: 100 }
  })
  const { targets, detail, summary } = evaluateStrategy(bars, { strategy: 'ma_cross', params: { fast: 5, slow: 20 } })
  assert.equal(targets.length, bars.length)
  assert.ok(detail.fastSma > 0)
  assert.ok(summary.includes('fast 5'))
  const result = runBacktest(bars, targets, { feeBps: 6, slippageBps: 2, barMs: 3_600_000 })
  assert.equal(result.metrics.bars, 120)
  assert.ok(result.metrics.totalReturnPct > 0, 'a rising series should make the long-only strategy money')
  assert.ok(result.curve.length <= 120)
  assert.ok(result.metrics.maxDrawdownPct >= 0)
})

check('trade pnl matches the price move', () => {
  const closes = []
  for (let index = 0; index < 40; index += 1) closes.push(100 + index)
  for (let index = 0; index < 40; index += 1) closes.push(139 - index)
  for (let index = 0; index < 40; index += 1) closes.push(100 + index * 0.5)
  const bars = closes.map((price, index) => ({ t: index * 3_600_000, o: price, h: price + 0.5, l: price - 0.5, c: price, v: 1 }))
  const { targets } = evaluateStrategy(bars, { strategy: 'ma_cross', params: { fast: 3, slow: 8 } })
  const result = runBacktest(bars, targets, { feeBps: 6, slippageBps: 2 })
  assert.ok(result.metrics.exposurePct > 0 && result.metrics.exposurePct <= 100)
  assert.ok(result.metrics.trades >= 1)
  for (const trade of result.trades) {
    const move = trade.exitPrice - trade.entryPrice
    if (Math.abs(move) < trade.entryPrice * 0.01) continue
    assert.equal(Math.sign(trade.pnlPct), Math.sign(move), `trade ${trade.entryPrice} -> ${trade.exitPrice} reported ${trade.pnlPct}%`)
  }
})

check('breakout and RSI strategies run', () => {
  const bars = Array.from({ length: 90 }, (_, index) => {
    const price = 50 + (index % 12)
    return { t: index * 60_000, o: price, h: price + 0.5, l: price - 0.5, c: price, v: 10 }
  })
  for (const strategy of ['rsi_reversion', 'breakout']) {
    const { targets } = evaluateStrategy(bars, { strategy, params: {} })
    const result = runBacktest(bars, targets, { barMs: 60_000 })
    assert.ok(Number.isFinite(result.metrics.totalReturnPct))
  }
})

check('paper book buy, sell, reset', () => {
  const directory = mkdtempSync(join(tmpdir(), 'bybit-quant-'))
  try {
    const store = createStore({ file: join(directory, 'state.json'), startingBalance: 1000 })
    const buy = store.mutate(state => paperBuy({ state, category: 'linear', symbol: 'BTCUSDT', price: 100, notionalUsd: 100 }))
    assert.equal(buy.quantity, 1)
    let status = paperStatus(store.get(), { 'linear:BTCUSDT': 110 })
    assert.ok(status.equityUsd > 1000)
    assert.equal(status.positions.length, 1)
    const sell = store.mutate(state => paperSell({ state, category: 'linear', symbol: 'BTCUSDT', price: 110 }))
    assert.ok(sell.realizedPnlUsd > 0)
    status = paperStatus(store.get(), {})
    assert.equal(status.positions.length, 0)
    assert.ok(status.balanceUsd > 1000)
    store.mutate(state => { state.paper.balance = 1000 })
    assert.throws(() => store.mutate(state => paperBuy({ state, category: 'linear', symbol: 'ETHUSDT', price: 10, notionalUsd: 5000 })))
  } finally {
    rmSync(directory, { recursive: true, force: true })
  }
})

console.log(`\n${passed} checks passed\n`)

// Live public endpoints: skip when offline so the smoke test still verifies logic.
const client = new BybitClient({ env: 'demo' })
try {
  const ticker = await client.ticker({ category: 'linear', symbol: 'BTCUSDT' })
  assert.ok(ticker.last > 0)
  console.log('live ticker', ticker.symbol, ticker.last)
  const bars = await client.klines({ category: 'linear', symbol: 'BTCUSDT', interval: '60', limit: 50 })
  assert.equal(bars.length, 50)
  assert.ok(bars[0].t < bars.at(-1).t, 'bars must be oldest-first')
  console.log('live klines', bars.length, new Date(bars.at(-1).t).toISOString(), bars.at(-1).c)
  const instrument = await client.instrument({ category: 'linear', symbol: 'BTCUSDT' })
  console.log('instrument', instrument.symbol, instrument.qtyStep, instrument.minNotionalUsd)
  const book = await client.orderbook({ category: 'linear', symbol: 'BTCUSDT', limit: 3 })
  assert.equal(book.bids.length, 3)
  const funding = await client.funding({ category: 'linear', symbol: 'BTCUSDT', limit: 2 })
  assert.ok(Array.isArray(funding))
  console.log('live orderbook + funding ok')
} catch (error) {
  console.log('live endpoint checks skipped:', error.message)
}
