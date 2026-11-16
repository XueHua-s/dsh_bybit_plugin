import type { Candle, Category, Instrument, Ticker } from '../src/index.js'

const category: Category = 'linear'
const candle: Candle = { t: 1, o: 100, h: 102, l: 99, c: 101, v: 10 }
const ticker: Ticker = {
  symbol: 'BTCUSDT', category, last: 101, change24hPct: 1, high24h: 102,
  low24h: 99, volume24h: 10, turnover24h: 1010, bid: 100.9, ask: 101.1,
  markPrice: 101, indexPrice: 100.8, fundingRate: 0.0001, openInterest: 50,
  time: 2,
}
const instrument: Instrument = {
  symbol: 'BTCUSDT', category, status: 'Trading', baseCoin: 'BTC', quoteCoin: 'USDT',
  contractType: 'LinearPerpetual', qtyStep: '0.001', minOrderQty: 0.001,
  minNotionalUsd: 5, tickSize: '0.1', maxLeverage: 100, fundingIntervalMinutes: 480,
}

void [candle, ticker, instrument]

// These errors are deliberate: unsupported venue categories and string-valued
// normalized market prices must not leak through the shared boundary.
// @ts-expect-error categories are intentionally limited to normalized markets
const unsupportedCategory: Category = 'inverse'
// @ts-expect-error prices crossing this contract are normalized numbers
const malformedTicker: Ticker = { ...ticker, last: '101' }
void [unsupportedCategory, malformedTicker]
