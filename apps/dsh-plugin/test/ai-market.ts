import assert from 'node:assert/strict'
import { buildSymbolBrief } from '../dist/lib/ai-market.js'
import type { Candle, Ticker, OrderBookSnapshot } from '../src/lib/bybit.js'

const newest = Date.now() - 60_000
const candles: Candle[] = Array.from({ length: 90 }, (_, index) => {
  const close = 100 + index * 0.1
  return { t: newest - ((89 - index) * 60_000), o: close, h: close + 1, l: close - 1, c: close, v: index + 10 }
})
const ticker: Ticker = {
  symbol: 'BTCUSDT', category: 'linear', last: 109, change24hPct: 1, high24h: 110, low24h: 99,
  volume24h: 1000, turnover24h: 100_000, bid: 108.9, ask: 109.1, markPrice: undefined,
  indexPrice: undefined, fundingRate: 0.0001, openInterest: undefined, time: newest,
}
const book: OrderBookSnapshot = { symbol: 'BTCUSDT', category: 'linear', bids: [[108.9, 2]], asks: [[109.1, 1]], time: newest }
let klineCalls = 0
const client = {
  async ticker() { return ticker },
  async orderbook() { return book },
  async funding() { return [] },
  async instrument() { return null },
  async klines() { klineCalls += 1; return candles },
}
const briefClient = client as unknown as Parameters<typeof buildSymbolBrief>[0]['client']

const requests: Array<{ symbol: string, category: string, interval: string, bars: Candle[], fundingRate: number | undefined }> = []
const brief = await buildSymbolBrief({
  client: briefClient,
  symbol: 'BTCUSDT',
  category: 'linear',
  timeframes: ['60', '240'],
  researchEvidence: async request => {
    requests.push(request)
    return { status: 'available', research_only: true, deployment_eligible: false }
  },
})
assert.equal(requests.length, 1)
assert.equal(requests[0]?.bars, candles, 'evidence must reuse the already fetched primary bars')
assert.equal(requests[0]?.interval, '60')
assert.equal(requests[0]?.fundingRate, ticker.fundingRate)
assert.equal(klineCalls, 2, 'strategy evidence must not fetch duplicate candles')
assert.deepEqual(brief.strategyEvidence, { status: 'available', research_only: true, deployment_eligible: false })

const failed = await buildSymbolBrief({
  client: briefClient,
  symbol: 'BTCUSDT',
  category: 'linear',
  timeframes: ['60'],
  researchEvidence: async () => { throw new Error('private engine detail') },
})
assert.deepEqual(failed.strategyEvidence, { status: 'unavailable', code: 'research_evidence_unavailable' })

const ordinary = await buildSymbolBrief({ client: briefClient, symbol: 'BTCUSDT', category: 'linear', timeframes: ['60'] })
assert.equal(Object.hasOwn(ordinary, 'strategyEvidence'), false, 'no research evidence is requested unless the caller explicitly opts in')
console.log('ok AI market brief reuses primary bars and labels unavailable research evidence')
