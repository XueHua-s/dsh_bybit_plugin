import assert from 'node:assert/strict'
import { BybitClient } from '../dist/lib/bybit.js'
import { buildAiUniverse, createAiUniverseService, decisionSymbols, selectAiSymbols } from '../dist/lib/ai-universe.js'
import { mapTicker } from '../dist/lib/bybit-format.js'
import type { Instrument, Ticker } from '../src/lib/bybit-types.ts'

function instrument(symbol: string, overrides: Partial<Instrument> = {}): Instrument {
  return {
    symbol, category: 'linear', status: 'Trading', baseCoin: symbol.replace('USDT', ''), quoteCoin: 'USDT',
    contractType: 'LinearPerpetual', qtyStep: '0.01', minOrderQty: 0.01, minNotionalUsd: 5,
    tickSize: '0.1', maxLeverage: 50, fundingIntervalMinutes: 480, ...overrides,
  }
}

function ticker(symbol: string, overrides: Partial<Ticker> = {}): Ticker {
  return {
    symbol, category: 'linear', last: 100, change24hPct: 2, high24h: 110, low24h: 90,
    volume24h: 1_000_000, turnover24h: 10_000_000, bid: 99.9, ask: 100.1,
    markPrice: 100, indexPrice: 100, fundingRate: 0.0001, openInterest: 500_000,
    time: 1_000, ...overrides,
  }
}

let passed = 0
const check = (label: string, fn: () => void | Promise<void>): Promise<void> => Promise.resolve(fn()).then(() => {
  passed += 1
  console.log(`ok ${label}`)
})

await check('normalizes Bybit ticker rows for analysis', () => {
  const value = mapTicker({
    symbol: 'ethusdt', lastPrice: '110', prevPrice24h: '100', highPrice24h: '120', lowPrice24h: '90',
    volume24h: '12', turnover24h: '1300000', bid1Price: '109.9', ask1Price: '110.1',
    markPrice: '110', indexPrice: '109.8', fundingRate: '0.0002', openInterest: '400', ts: '1234',
  }, 'linear')
  assert.deepEqual({ symbol: value.symbol, category: value.category, last: value.last, change: value.change24hPct, turnover: value.turnover24h, bid: value.bid, ask: value.ask, time: value.time }, {
    symbol: 'ETHUSDT', category: 'linear', last: 110, change: 10, turnover: 1_300_000, bid: 109.9, ask: 110.1, time: 1234,
  })
  assert.equal(value.fundingRate, 0.0002)
})

await check('filters status, quote, rules, liquidity, and spread before ranking', () => {
  const instruments = [
    instrument('LOWTURNUSDT'),
    instrument('WIDESPREADUSDT'),
    instrument('HALTEDUSDT', { status: 'PreLaunch' }),
    instrument('USDCUSDT', { quoteCoin: 'USDC' }),
    instrument('BADSTEPUSDT', { qtyStep: undefined }),
    instrument('BTCUSDT'),
    instrument('ETHUSDT'),
  ]
  const tickers = [
    ticker('LOWTURNUSDT', { turnover24h: 999_999 }),
    ticker('WIDESPREADUSDT', { bid: 98, ask: 102 }),
    ticker('HALTEDUSDT'), ticker('USDCUSDT'), ticker('BADSTEPUSDT'),
    ticker('BTCUSDT', { turnover24h: 8_000_000 }), ticker('ETHUSDT', { turnover24h: 12_000_000 }),
  ]
  const value = buildAiUniverse({ category: 'linear', instruments, tickers, now: 10_000 })
  assert.deepEqual(value.candidates.map((candidate: { symbol: string }) => candidate.symbol), ['ETHUSDT', 'BTCUSDT'])
  assert.equal(value.catalogueSize, instruments.length)
  assert.equal(value.candidates[0]?.spreadBps, 20)
  assert.equal(value.observedAt, 10_000)
})

await check('accepts only matching USDT Spot or linear perpetual contracts', () => {
  const value = buildAiUniverse({
    category: 'spot',
    instruments: [
      instrument('ETHUSDT', { category: 'spot', contractType: 'Spot' }),
      instrument('BTCUSDT', { category: 'spot', contractType: 'LinearPerpetual' }),
      instrument('SOLUSDC', { category: 'spot', contractType: 'Spot', quoteCoin: 'USDC' }),
    ],
    tickers: [ticker('ETHUSDT', { category: 'spot' }), ticker('BTCUSDT', { category: 'spot' }), ticker('SOLUSDC', { category: 'spot' })],
  })
  assert.deepEqual(value.candidates.map((candidate: { symbol: string }) => candidate.symbol), ['ETHUSDT'])
})

await check('treats empty allow-lists as no candidates and non-empty lists as a narrowing bound', () => {
  const instruments = [instrument('BTCUSDT'), instrument('ETHUSDT')]
  const tickers = [ticker('BTCUSDT'), ticker('ETHUSDT')]
  assert.equal(buildAiUniverse({ category: 'linear', instruments, tickers }).eligibleCount, 2)
  assert.equal(buildAiUniverse({ category: 'linear', instruments, tickers, allowlist: [] }).eligibleCount, 0)
  assert.deepEqual(buildAiUniverse({ category: 'linear', instruments, tickers, allowlist: ['ETHUSDT'] }).candidates.map((item: { symbol: string }) => item.symbol), ['ETHUSDT'])
})

await check('bounds the list and applies a stable turnover ranking', () => {
  const instruments = Array.from({ length: 40 }, (_, index) => instrument(`COIN${String(index).padStart(2, '0')}USDT`))
  const tickers = instruments.map((item, index) => ticker(item.symbol, { turnover24h: 2_000_000 + index }))
  const value = buildAiUniverse({ category: 'linear', instruments, tickers, limit: 40 })
  assert.equal(value.eligibleCount, 40)
  assert.equal(value.candidates.length, 30)
  assert.equal(value.candidates[0]?.symbol, 'COIN39USDT')
})

await check('does not infer an AI symbol from rank and limits flat to an existing position', () => {
  const universe = buildAiUniverse({ category: 'linear', instruments: [instrument('BTCUSDT')], tickers: [ticker('BTCUSDT')] })
  assert.deepEqual(selectAiSymbols([], universe), [])
  assert.deepEqual(selectAiSymbols(['BTCUSDT'], universe), ['BTCUSDT'])
  assert.throws(() => selectAiSymbols(['ETHUSDT'], universe), /outside the current AI eligible candidate universe/)
  assert.deepEqual(decisionSymbols(universe, 'long', ['OUTSIDEUSDT']), ['BTCUSDT'])
  assert.deepEqual(decisionSymbols(universe, 'flat', ['OUTSIDEUSDT']), ['BTCUSDT', 'OUTSIDEUSDT'])
})

await check('refreshes a short-lived source cache and never returns expired candidates after failure', async () => {
  let now = 1_000
  let failures = false
  let calls = 0
  const source = {
    async instruments() {
      calls += 1
      if (failures) throw new Error('catalogue unavailable')
      return [instrument('BTCUSDT')]
    },
    async tickers() {
      return [ticker('BTCUSDT')]
    },
  }
  const service = createAiUniverseService(source, { ttlMs: 5_000, now: () => now })
  assert.equal((await service.get('linear')).eligibleCount, 1)
  assert.equal((await service.get('linear')).eligibleCount, 1)
  assert.equal(calls, 1)
  now += 5_001
  failures = true
  await assert.rejects(() => service.get('linear'), /catalogue unavailable/)
  assert.equal(service.peek('linear').status, 'stale')
  assert.equal(service.peek('linear').universe?.eligibleCount, 1)
  await assert.rejects(() => service.get('linear'), /catalogue unavailable/)
  assert.equal(calls, 3)
  failures = false
  assert.equal((await service.get('linear')).eligibleCount, 1)
  assert.equal(service.peek('linear').status, 'fresh')
})

await check('reads every instrument catalogue cursor page', async () => {
  const originalFetch = globalThis.fetch
  const cursors: string[] = []
  globalThis.fetch = async (input) => {
    const url = new URL(String(input))
    const cursor = url.searchParams.get('cursor') ?? ''
    cursors.push(cursor)
    const row = cursor === '' ? 'BTCUSDT' : 'ETHUSDT'
    const nextPageCursor = cursor === '' ? 'next-page' : ''
    return Response.json({ retCode: 0, result: { list: [{
      symbol: row, status: 'Trading', baseCoin: row.slice(0, -4), quoteCoin: 'USDT', contractType: 'LinearPerpetual',
      lotSizeFilter: { qtyStep: '0.01', minOrderQty: '0.01' }, priceFilter: { tickSize: '0.1' },
    }], nextPageCursor } })
  }
  try {
    const client = new BybitClient({ marketEndpoint: 'https://mock.invalid' })
    const rows = await client.instruments({ category: 'linear' })
    assert.deepEqual(rows.map(row => row.symbol), ['BTCUSDT', 'ETHUSDT'])
    assert.deepEqual(cursors, ['', 'next-page'])
  } finally {
    globalThis.fetch = originalFetch
  }
})

console.log(`\n${passed} AI universe checks passed\n`)
