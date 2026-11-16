/**
 * Indicators, three long-only strategies, and the backtest engine behind
 * `quant_backtest`. Everything here is pure: it takes oldest-first bars and
 * returns numbers, so the same code explains a signal to the agent and feeds
 * the panel's metrics.
 */
import type { Bar } from './signals.js'

/** Strategy ids the tool accepts. */
export const STRATEGIES = ['ma_cross', 'rsi_reversion', 'breakout'] as const

/** One strategy id. */
export type StrategyName = (typeof STRATEGIES)[number]

/** One-line explanation per strategy, used in tool output. */
export const STRATEGY_SUMMARY: Record<StrategyName, string> = {
  ma_cross: 'long while the fast SMA is above the slow SMA, flat otherwise',
  rsi_reversion: 'buy when RSI falls below the entry level, exit when it rises above the exit level',
  breakout: 'buy a close above the prior N-bar high, exit a close below the prior N-bar low',
}

/** Strategy parameters, all optional. */
export interface StrategyParams {
  fast?: number
  slow?: number
  period?: number
  entry?: number
  exit?: number
  lookback?: number
}

/** One evaluated strategy. */
export interface StrategyEvaluation {
  targets: number[]
  detail: Record<string, number | null>
  summary: string
}

/** One closed trade. */
export interface BacktestTrade {
  entryTime: number
  exitTime: number
  entryPrice: number
  exitPrice: number
  bars: number
  pnlPct: number
}

/** Backtest metrics reported to the model and the panel. */
export interface BacktestMetrics {
  bars: number
  finalEquity: number
  totalReturnPct: number
  buyHoldReturnPct: number
  maxDrawdownPct: number
  trades: number
  winRatePct: number
  avgTradePct: number
  bestTradePct: number
  worstTradePct: number
  profitFactor: number | null
  exposurePct: number
  feeDragPct: number
  sharpe: number
  from: string
  to: string
}

/** Backtest result. */
export interface BacktestResult {
  metrics: BacktestMetrics
  openPosition: { since: number, bars: number } | null
  trades: BacktestTrade[]
  curve: Array<{ t: number, e: number }>
}

/** Backtest options. */
export interface BacktestOptions {
  feeBps?: number
  slippageBps?: number
  barMs?: number
}

/**
 * Simple moving average aligned with the input.
 * @returns NaN before the window fills.
 */
export function sma(values: readonly number[], period: number): number[] {
  const out: number[] = Array.from({ length: values.length }, () => Number.NaN)
  if (period <= 0) return out
  let sum = 0
  for (let index = 0; index < values.length; index += 1) {
    sum += values[index] as number
    if (index >= period) sum -= values[index - period] as number
    if (index >= period - 1) out[index] = sum / period
  }
  return out
}

/**
 * Wilder's relative strength index aligned with the input.
 * @returns NaN before the first average is available.
 */
export function rsi(values: readonly number[], period = 14): number[] {
  const out: number[] = Array.from({ length: values.length }, () => Number.NaN)
  if (values.length <= period) return out
  let gain = 0
  let loss = 0
  for (let index = 1; index <= period; index += 1) {
    const change = (values[index] as number) - (values[index - 1] as number)
    if (change >= 0) gain += change
    else loss -= change
  }
  let avgGain = gain / period
  let avgLoss = loss / period
  out[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
  for (let index = period + 1; index < values.length; index += 1) {
    const change = (values[index] as number) - (values[index - 1] as number)
    const up = change > 0 ? change : 0
    const down = change < 0 ? -change : 0
    avgGain = (avgGain * (period - 1) + up) / period
    avgLoss = (avgLoss * (period - 1) + down) / period
    out[index] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
  }
  return out
}

/** Rolling extreme of a window that ends before the current index. */
function priorExtreme(values: readonly number[], lookback: number, pick: 'max' | 'min'): number[] {
  const out: number[] = Array.from({ length: values.length }, () => Number.NaN)
  for (let index = lookback; index < values.length; index += 1) {
    let best = pick === 'max' ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY
    for (let cursor = index - lookback; cursor < index; cursor += 1) {
      const value = values[cursor] as number
      best = pick === 'max' ? Math.max(best, value) : Math.min(best, value)
    }
    out[index] = best
  }
  return out
}

/**
 * Evaluate one strategy over a bar series.
 */
export function evaluateStrategy(
  bars: readonly Bar[],
  { strategy, params = {} }: { strategy: StrategyName, params?: StrategyParams },
): StrategyEvaluation {
  const closes = bars.map(bar => bar.c)
  const highs = bars.map(bar => bar.h)
  const lows = bars.map(bar => bar.l)
  const targets: number[] = Array.from({ length: bars.length }, () => 0)
  const last = bars.length - 1

  if (strategy === 'ma_cross') {
    const fast = clampInt(params.fast, 5, 200, 20)
    const slow = clampInt(params.slow, fast + 1, 400, 50)
    const fastSma = sma(closes, fast)
    const slowSma = sma(closes, slow)
    for (let index = 0; index < bars.length; index += 1) {
      const fastValue = fastSma[index] as number
      const slowValue = slowSma[index] as number
      if (Number.isNaN(fastValue) || Number.isNaN(slowValue)) continue
      targets[index] = fastValue > slowValue ? 1 : 0
    }
    return {
      targets,
      detail: last < 0 ? {} : { fast, slow, fastSma: round2(fastSma[last]), slowSma: round2(slowSma[last]) },
      summary: `${STRATEGY_SUMMARY.ma_cross} (fast ${fast}, slow ${slow})`,
    }
  }

  if (strategy === 'rsi_reversion') {
    const period = clampInt(params.period, 2, 100, 14)
    const entry = clampNumber(params.entry, 1, 49, 30)
    const exit = clampNumber(params.exit, 51, 99, 70)
    const series = rsi(closes, period)
    let holding = 0
    for (let index = 0; index < bars.length; index += 1) {
      const value = series[index] as number
      if (!Number.isNaN(value)) {
        if (holding === 0 && value < entry) holding = 1
        else if (holding === 1 && value > exit) holding = 0
      }
      targets[index] = holding
    }
    return {
      targets,
      detail: last < 0 ? {} : { period, entry, exit, rsi: round2(series[last]) },
      summary: `${STRATEGY_SUMMARY.rsi_reversion} (RSI ${period}, entry ${entry}, exit ${exit})`,
    }
  }

  if (strategy === 'breakout') {
    const lookback = clampInt(params.lookback, 5, 200, 20)
    const priorHigh = priorExtreme(highs, lookback, 'max')
    const priorLow = priorExtreme(lows, lookback, 'min')
    let holding = 0
    for (let index = 0; index < bars.length; index += 1) {
      const high = priorHigh[index] as number
      if (Number.isNaN(high)) continue
      const close = closes[index] as number
      if (holding === 0 && close > high) holding = 1
      else if (holding === 1 && close < (priorLow[index] as number)) holding = 0
      targets[index] = holding
    }
    return {
      targets,
      detail: last < 0 ? {} : { lookback, priorHigh: round2(priorHigh[last]), priorLow: round2(priorLow[last]) },
      summary: `${STRATEGY_SUMMARY.breakout} (lookback ${lookback})`,
    }
  }

  throw new Error(`unknown strategy "${String(strategy)}"; use one of ${STRATEGIES.join(', ')}`)
}

/**
 * Long-only backtest: full notional per trade, fees and slippage on both sides.
 */
export function runBacktest(bars: readonly Bar[], targets: readonly number[], options: BacktestOptions = {}): BacktestResult {
  const feeRate = (options.feeBps ?? 6) / 10_000
  const slippage = (options.slippageBps ?? 2) / 10_000
  const barMs = options.barMs ?? 3_600_000
  if (bars.length < 2) throw new Error('need at least two bars to backtest')

  let cash = 1
  let units = 0
  let holding = 0
  let barsHeld = 0
  let barsInMarket = 0
  let peak = 1
  let maxDrawdown = 0
  let feesPaid = 0
  let entry: { time: number, price: number, fee: number, capital: number } | null = null
  const equityCurve: Array<{ t: number, e: number }> = []
  const trades: BacktestTrade[] = []

  for (let index = 0; index < bars.length; index += 1) {
    const bar = bars[index] as Bar
    const wanted = targets[index] ?? 0
    if (wanted !== holding) {
      if (wanted === 1) {
        const price = bar.c * (1 + slippage)
        const fee = cash * feeRate
        feesPaid += fee
        const capital = cash
        units = (cash - fee) / price
        cash = 0
        holding = 1
        barsHeld = 0
        entry = { time: bar.t, price, fee, capital }
      } else {
        const price = bar.c * (1 - slippage)
        const proceeds = units * price
        const fee = proceeds * feeRate
        feesPaid += fee
        cash = proceeds - fee
        units = 0
        holding = 0
        if (entry !== null) {
          // The trade's return is measured against the capital committed to it,
          // not the original unit, so compounding does not inflate trade wins.
          const pnlPct = (cash / entry.capital - 1) * 100
          trades.push({
            entryTime: entry.time,
            exitTime: bar.t,
            entryPrice: round(entry.price, 6),
            exitPrice: round(price, 6),
            bars: barsHeld,
            pnlPct: round(pnlPct, 3),
          })
          entry = null
        }
      }
    }
    if (holding === 1) {
      barsHeld += 1
      barsInMarket += 1
    }
    const equity = cash + units * bar.c
    equityCurve.push({ t: bar.t, e: equity })
    peak = Math.max(peak, equity)
    maxDrawdown = Math.max(maxDrawdown, (peak - equity) / peak)
  }

  const finalEquity = (equityCurve.at(-1) as { t: number, e: number }).e
  const first = bars[0] as Bar
  const lastBar = bars.at(-1) as Bar
  const buyHold = (lastBar.c / first.c) * (1 - feeRate) - 1
  const returns: number[] = []
  for (let index = 1; index < equityCurve.length; index += 1) {
    returns.push((equityCurve[index] as { e: number }).e / (equityCurve[index - 1] as { e: number }).e - 1)
  }
  const cleanTrades = trades.filter(trade => Number.isFinite(trade.pnlPct))
  const wins = cleanTrades.filter(trade => trade.pnlPct > 0)
  const grossWin = wins.reduce((sum, trade) => sum + trade.pnlPct, 0)
  const grossLoss = cleanTrades.filter(trade => trade.pnlPct <= 0).reduce((sum, trade) => sum + Math.abs(trade.pnlPct), 0)
  const barsPerYear = (365 * 24 * 60 * 60 * 1000) / barMs

  return {
    metrics: {
      bars: bars.length,
      finalEquity: round(finalEquity, 4),
      totalReturnPct: round((finalEquity - 1) * 100, 2),
      buyHoldReturnPct: round(buyHold * 100, 2),
      maxDrawdownPct: round(maxDrawdown * 100, 2),
      trades: cleanTrades.length,
      winRatePct: cleanTrades.length === 0 ? 0 : round((wins.length / cleanTrades.length) * 100, 1),
      avgTradePct: cleanTrades.length === 0 ? 0 : round(cleanTrades.reduce((sum, trade) => sum + trade.pnlPct, 0) / cleanTrades.length, 3),
      bestTradePct: cleanTrades.length === 0 ? 0 : round(Math.max(...cleanTrades.map(trade => trade.pnlPct)), 3),
      worstTradePct: cleanTrades.length === 0 ? 0 : round(Math.min(...cleanTrades.map(trade => trade.pnlPct)), 3),
      profitFactor: grossLoss === 0 ? null : round(grossWin / grossLoss, 2),
      exposurePct: round((barsInMarket / bars.length) * 100, 1),
      feeDragPct: round(feesPaid * 100, 2),
      sharpe: round(annualisedSharpe(returns, barsPerYear), 2),
      from: new Date(first.t).toISOString(),
      to: new Date(lastBar.t).toISOString(),
    },
    openPosition: holding === 1 ? { since: entry?.time ?? lastBar.t, bars: barsHeld } : null,
    trades: cleanTrades.slice(-8),
    curve: downsample(equityCurve, 120),
  }
}

/** Annualised Sharpe ratio of per-bar returns, zero when variance is absent. */
function annualisedSharpe(returns: readonly number[], barsPerYear: number): number {
  if (returns.length < 2) return 0
  const mean = returns.reduce((sum, value) => sum + value, 0) / returns.length
  const variance = returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (returns.length - 1)
  const deviation = Math.sqrt(variance)
  if (deviation === 0) return 0
  return (mean / deviation) * Math.sqrt(barsPerYear)
}

/**
 * Keep at most `limit` evenly spaced points, always including both ends.
 */
export function downsample(points: readonly { t: number, e: number }[], limit: number): Array<{ t: number, e: number }> {
  if (points.length <= limit) return [...points]
  const step = (points.length - 1) / (limit - 1)
  const out: Array<{ t: number, e: number }> = []
  for (let index = 0; index < limit; index += 1) out.push(points[Math.round(index * step)] as { t: number, e: number })
  return out
}

/** Constrain an integer parameter to a range with a default. */
function clampInt(value: number | undefined, min: number, max: number, fallback: number): number {
  const number = Number(value)
  if (!Number.isFinite(number)) return fallback
  return Math.min(Math.max(Math.trunc(number), min), max)
}

/** Constrain a float parameter to a range with a default. */
function clampNumber(value: number | undefined, min: number, max: number, fallback: number): number {
  const number = Number(value)
  if (!Number.isFinite(number)) return fallback
  return Math.min(Math.max(number, min), max)
}

/** Round for display, normalising negative zero. */
export function round(value: number, digits: number): number {
  if (!Number.isFinite(value)) return 0
  const factor = 10 ** digits
  const rounded = Math.round(value * factor) / factor
  return Object.is(rounded, -0) ? 0 : rounded
}

/** Two-decimal rounding used in indicator details. */
function round2(value: number | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? round(value, 2) : null
}
