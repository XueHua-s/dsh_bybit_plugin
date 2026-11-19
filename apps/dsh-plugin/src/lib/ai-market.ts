/** Market features and structured briefs, independent from order and ledger state. */
import { evaluateSignals } from './signals.js'
import type { BybitClient, Candle, Category, OrderBookSnapshot } from './bybit.js'
import { AI_FEE_BPS } from './ai-config.js'
import { round } from './numeric.js'

/** Mean of a numeric slice, NaN when empty. */
function mean(values: number[]): number {
  if (values.length === 0) return Number.NaN
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

/** True range of one bar against the previous close. */
function trueRange(bar: Pick<Candle, 'h' | 'l'>, previousClose: number): number {
  return Math.max(bar.h - bar.l, Math.abs(bar.h - previousClose), Math.abs(bar.l - previousClose))
}

/**
 * Wilder's average true range, or NaN without enough history.
 */
export function atr(bars: Array<Pick<Candle, 'h' | 'l' | 'c'>>, period = 14): number {
  if (bars.length < period + 1) return Number.NaN
  let sum = 0
  for (let index = 1; index <= period; index += 1) {
    const bar = bars[index]
    const previous = bars[index - 1]
    if (bar !== undefined && previous !== undefined) sum += trueRange(bar, previous.c)
  }
  let value = sum / period
  for (let index = period + 1; index < bars.length; index += 1) {
    const bar = bars[index]
    const previous = bars[index - 1]
    if (bar !== undefined && previous !== undefined) value = (value * (period - 1) + trueRange(bar, previous.c)) / period
  }
  return value
}

/** Percentage change over `bars` bars, NaN when the window is short. */
function changePct(closes: number[], bars: number): number {
  const last = closes.at(-1) ?? 0
  const then = closes.at(-1 - bars)
  if (last === undefined || then === undefined || then === 0) return Number.NaN
  return ((last - then) / then) * 100
}

/**
 * Trend and structure facts for one timeframe.
 */
export function trendState(bars: Array<Pick<Candle, 'o' | 'h' | 'l' | 'c'>>) {
  if (bars.length < 25) return { bars: bars.length, state: 'range', note: 'not enough bars' }
  const closes = bars.map(bar => bar.c)
  const last = closes.at(-1) ?? 0
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
export function volRegime(bars: Array<Pick<Candle, 'h' | 'l' | 'c'>>) {
  if (bars.length < 80) return { regime: 'unknown', atrPct: null, ratio: null }
  const last = bars.at(-1)
  if (last === undefined) return { regime: 'unknown', atrPct: null, ratio: null }
  const current = atr(bars) / last.c
  const samples = []
  for (let index = bars.length - 60; index < bars.length; index += 10) {
    const slice = bars.slice(0, index + 1)
    const value = atr(slice)
    const lastSliceBar = slice.at(-1)
    if (Number.isFinite(value) && lastSliceBar !== undefined) samples.push(value / lastSliceBar.c)
  }
  const baseline = mean(samples)
  const ratio = baseline > 0 ? current / baseline : Number.NaN
  const regime = ratio > 1.4 ? 'high' : ratio < 0.7 ? 'low' : 'normal'
  return { regime, atrPct: round(current * 100, 3), ratio: round(ratio, 2) }
}

/**
 * Order-flow imbalance and spread from a top-of-book snapshot.
 */
export function bookPressure(book: OrderBookSnapshot) {
  const bidVolume = book.bids.reduce((sum, level) => sum + level[1], 0)
  const askVolume = book.asks.reduce((sum, level) => sum + level[1], 0)
  const total = bidVolume + askVolume
  const bestBid = book.bids[0]?.[0] ?? 0
  const bestAsk = book.asks[0]?.[0] ?? 0
  return {
    bidVolume: round(bidVolume, 3),
    askVolume: round(askVolume, 3),
    imbalancePct: total === 0 ? 0 : round(((bidVolume - askVolume) / total) * 100, 1),
    spreadBps: bestBid > 0 && bestAsk > 0 ? round(((bestAsk - bestBid) / bestBid) * 10_000, 2) : null,
  }
}

/**
 * One symbol's multi-timeframe brief.
 * @param {{ client: BybitClient, symbol: string, category: string, timeframes?: string[], signal?: AbortSignal }} input
 */
export async function buildSymbolBrief({ client, symbol, category, timeframes = ['240', '60', 'D'], signal }: {
  client: BybitClient, symbol: string, category: Category, timeframes?: string[], signal?: AbortSignal | undefined,
}) {
  const [ticker, book, funding, instrument] = await Promise.all([
    client.ticker({ category, symbol, ...(signal === undefined ? {} : { signal }) }),
    client.orderbook({ category, symbol, limit: 20, ...(signal === undefined ? {} : { signal }) }),
    category === 'linear' ? client.funding({ category, symbol, limit: 3, ...(signal === undefined ? {} : { signal }) }) : Promise.resolve([]),
    client.instrument({ category, symbol, ...(signal === undefined ? {} : { signal }) }).catch(() => null),
  ])
  const frames: Record<string, ReturnType<typeof trendState> & { vol: ReturnType<typeof volRegime> }> = {}
  let primaryBars: Candle[] = []
  for (const interval of timeframes) {
    const bars = await client.klines({ category, symbol, interval, limit: 240, ...(signal === undefined ? {} : { signal }) })
    if (interval === timeframes[0]) primaryBars = bars
    frames[interval] = {
      ...trendState(bars),
      vol: volRegime(bars),
    }
  }
  const signals = primaryBars.length >= 80 ? evaluateSignals(primaryBars) : null
  const primary = frames[timeframes[0] ?? '']
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
      state: primary?.state ?? 'range',
      atrPct: primary?.atrPct ?? null,
      volRegime: primary?.vol.regime ?? 'unknown',
      rangePosPct: primary?.rangePosPct ?? null,
      signals: signals === null ? null : { bias: signals.bias, score: signals.score, notes: signals.notes },
    },
    signals,
    roundTripCostBps: AI_FEE_BPS * 2,
  }
}

/**
 * Whole-book brief plus the risk limits the decision must respect.
 * @param {{ client: BybitClient, symbols: string[], category: string, timeframes?: string[], signal?: AbortSignal | undefined, limits: object }} input
 */
export async function buildBrief({ client, symbols, category, timeframes, signal, limits }: {
  client: BybitClient, symbols: string[], category: Category, timeframes?: string[], signal?: AbortSignal | undefined, limits: object,
}) {
  const items: Awaited<ReturnType<typeof buildSymbolBrief>>[] = []
  for (const symbol of symbols) {
    items.push(await buildSymbolBrief({ client, symbol, category, ...(timeframes === undefined ? {} : { timeframes }), ...(signal === undefined ? {} : { signal }) }))
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
