/**
 * Stable, transport-independent market data shared by DSH surfaces and the
 * quant engine boundary. Numeric values are normalized by the producer; venue
 * response formats and parsing rules stay inside exchange adapters.
 */
export type Category = 'spot' | 'linear'

/** One OHLCV candle, oldest-first in every returned series. */
export interface Candle {
  t: number
  o: number
  h: number
  l: number
  c: number
  v: number
}

/** Normalized 24-hour market snapshot; unavailable derivatives fields are undefined. */
export interface Ticker {
  symbol: string
  category: Category
  last: number
  change24hPct: number
  high24h: number
  low24h: number
  volume24h: number
  turnover24h: number
  bid: number
  ask: number
  markPrice: number | undefined
  indexPrice: number | undefined
  fundingRate: number | undefined
  openInterest: number | undefined
  time: number
}

/** Tradable instrument constraints normalized from venue metadata. */
export interface Instrument {
  symbol: string
  category: Category
  status: string
  baseCoin: string
  quoteCoin: string
  contractType: string | undefined
  qtyStep: string | undefined
  minOrderQty: number
  minNotionalUsd: number | undefined
  tickSize: string | undefined
  maxLeverage: number | undefined
  fundingIntervalMinutes: number | undefined
}
