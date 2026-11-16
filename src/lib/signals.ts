/**
 * A curated signal library, re-implemented from published, widely used
 * algorithms rather than copied from a repository:
 *
 * - Supertrend: ATR band trend, popularised on TradingView and re-implemented
 *   in most freqtrade strategies.
 * - Squeeze Momentum: LazyBear's Bollinger-inside-Keltner compression with a
 *   momentum histogram (TradingView).
 * - Ichimoku Kinko Hyo: Goichi Hosoda's cloud state.
 * - Donchian breakout: the Turtle channel rule.
 * - ADX/DI regime: J. Welles Wilder's directional movement.
 *
 * Every function returns a small, JSON-safe fact set plus a directional score in
 * [-1, 1]. The consensus is a weighted sum, deliberately conservative: signals
 * only vote when their own condition holds (a squeeze that is still on has no
 * momentum to trade).
 */

/** One OHLCV candle, oldest-first in every series here. */
export interface Bar {
  t: number
  o: number
  h: number
  l: number
  c: number
  v: number
}

/** Attribution shown by the panel and the tool result. */
export const SIGNAL_SOURCES = {
  supertrend: 'Supertrend (ATR bands, TradingView / freqtrade strategies)',
  squeeze: 'Squeeze Momentum (LazyBear, TradingView)',
  ichimoku: 'Ichimoku Kinko Hyo cloud state (Goichi Hosoda)',
  donchian: 'Donchian channel breakout (Turtle system)',
  adx: 'ADX / DI directional regime (J. Welles Wilder)',
} as const

/** Supertrend output. */
export interface SupertrendResult {
  dir: 1 | -1
  value: number
  distancePct: number
}

/** Squeeze Momentum output. */
export interface SqueezeResult {
  on: boolean
  momentum: number
  bbWidthPct: number
  kcWidthPct: number
}

/** Ichimoku cloud state. */
export interface IchimokuResult {
  state: 'above' | 'below' | 'inside'
  tenkan: number
  kijun: number
  cloudTop: number
  cloudBottom: number
  tkCross: 'bull' | 'bear'
}

/** Donchian channel state. */
export interface DonchianResult {
  breakout: 'up' | 'down' | 'none'
  high: number
  low: number
  posPct: number
}

/** ADX / directional movement state. */
export interface AdxResult {
  adx: number
  plusDi: number
  minusDi: number
  trending: boolean
}

/** What one evaluated bar series yields. */
export interface SignalEvaluation {
  signals: {
    supertrend: SupertrendResult | null
    squeeze: SqueezeResult | null
    ichimoku: IchimokuResult | null
    donchian: DonchianResult | null
    adx: AdxResult | null
  }
  score: number
  bias: 'long' | 'short' | 'flat'
  notes: string[]
}

/** Simple moving average aligned with the input. */
export function sma(values: readonly number[], period: number): number[] {
  const out: number[] = Array.from({ length: values.length }, () => Number.NaN)
  let sum = 0
  for (let index = 0; index < values.length; index += 1) {
    sum += values[index] as number
    if (index >= period) sum -= values[index - period] as number
    if (index >= period - 1) out[index] = sum / period
  }
  return out
}

/** Population standard deviation. */
export function stdev(values: readonly number[]): number {
  if (values.length === 0) return Number.NaN
  const average = values.reduce((sum, value) => sum + value, 0) / values.length
  const variance = values.reduce((sum, value) => sum + (value - average) ** 2, 0) / values.length
  return Math.sqrt(variance)
}

/** Wilder's average true range series (NaN before it is available). */
export function atrSeries(bars: readonly Bar[], period = 14): number[] {
  const trs = bars.map((bar, index) => index === 0
    ? bar.h - bar.l
    : Math.max(bar.h - bar.l, Math.abs(bar.h - (bars[index - 1] as Bar).c), Math.abs(bar.l - (bars[index - 1] as Bar).c)))
  const out: number[] = Array.from({ length: bars.length }, () => Number.NaN)
  if (bars.length <= period) return out
  let sum = 0
  for (let index = 1; index <= period; index += 1) sum += trs[index] as number
  let value = sum / period
  out[period] = value
  for (let index = period + 1; index < bars.length; index += 1) {
    value = (value * (period - 1) + (trs[index] as number)) / period
    out[index] = value
  }
  return out
}

/**
 * Supertrend: direction flips when the close crosses the trailing ATR band.
 */
export function supertrend(bars: readonly Bar[], { period = 10, multiplier = 3 }: { period?: number, multiplier?: number } = {}): SupertrendResult | null {
  if (bars.length < period + 3) return null
  const atr = atrSeries(bars, period)
  let finalUpper = Number.NaN
  let finalLower = Number.NaN
  let direction: 1 | -1 = 1
  for (let index = period; index < bars.length; index += 1) {
    const bar = bars[index] as Bar
    const mid = (bar.h + bar.l) / 2
    const basicUpper = mid + multiplier * (atr[index] as number)
    const basicLower = mid - multiplier * (atr[index] as number)
    if (!Number.isFinite(finalUpper)) {
      finalUpper = basicUpper
      finalLower = basicLower
      direction = bar.c > mid ? 1 : -1
      continue
    }
    const previousClose = (bars[index - 1] as Bar).c
    finalUpper = basicUpper < finalUpper || previousClose > finalUpper ? basicUpper : finalUpper
    finalLower = basicLower > finalLower || previousClose < finalLower ? basicLower : finalLower
    if (direction === 1 && bar.c < finalLower) direction = -1
    else if (direction === -1 && bar.c > finalUpper) direction = 1
  }
  const last = bars.at(-1) as Bar
  const value = direction === 1 ? finalLower : finalUpper
  return {
    dir: direction,
    value: round(value, 6),
    distancePct: round(((last.c - value) / last.c) * 100, 2),
  }
}

/**
 * Squeeze Momentum: Bollinger Bands inside Keltner Channels means compression;
 * the momentum histogram's sign only matters once the squeeze releases.
 */
export function squeeze(bars: readonly Bar[], { bbPeriod = 20, kcPeriod = 20, kcMult = 1.5, momPeriod = 12 }: { bbPeriod?: number, kcPeriod?: number, kcMult?: number, momPeriod?: number } = {}): SqueezeResult | null {
  const needed = Math.max(bbPeriod, kcPeriod, momPeriod) + 2
  if (bars.length < needed) return null
  const closes = bars.map(bar => bar.c)
  const basis = sma(closes, bbPeriod).at(-1) as number
  const deviation = stdev(closes.slice(-bbPeriod))
  const bbUpper = basis + 2 * deviation
  const bbLower = basis - 2 * deviation
  const kcMid = sma(closes, kcPeriod).at(-1) as number
  const atr = atrSeries(bars, kcPeriod).at(-1) as number
  if (!Number.isFinite(atr)) return null
  const kcUpper = kcMid + kcMult * atr
  const kcLower = kcMid - kcMult * atr
  const window = bars.slice(-momPeriod)
  const highest = Math.max(...window.map(bar => bar.h))
  const lowest = Math.min(...window.map(bar => bar.l))
  const close = closes.at(-1) as number
  const momentum = close - ((highest + lowest) / 2 + (kcMid + basis) / 2) / 2
  return {
    on: bbUpper < kcUpper && bbLower > kcLower,
    momentum: round(momentum, 6),
    bbWidthPct: round(((bbUpper - bbLower) / close) * 100, 3),
    kcWidthPct: round(((kcUpper - kcLower) / close) * 100, 3),
  }
}

/**
 * Ichimoku cloud state at the current bar.
 */
export function ichimoku(bars: readonly Bar[]): IchimokuResult | null {
  if (bars.length < 52 + 26) return null
  const midline = (length: number, offset: number): number => {
    const slice = bars.slice(bars.length - offset - length, bars.length - offset)
    return (Math.max(...slice.map(bar => bar.h)) + Math.min(...slice.map(bar => bar.l))) / 2
  }
  const tenkan = midline(9, 0)
  const kijun = midline(26, 0)
  const senkouA = (midline(9, 26) + midline(26, 26)) / 2
  const senkouB = midline(52, 26)
  const close = (bars.at(-1) as Bar).c
  const top = Math.max(senkouA, senkouB)
  const bottom = Math.min(senkouA, senkouB)
  const state = close > top ? 'above' : close < bottom ? 'below' : 'inside'
  return {
    state,
    tenkan: round(tenkan, 6),
    kijun: round(kijun, 6),
    cloudTop: round(top, 6),
    cloudBottom: round(bottom, 6),
    tkCross: tenkan > kijun ? 'bull' : 'bear',
  }
}

/**
 * Donchian channel breakout against the prior window (the channel excludes the
 * current bar, as the Turtle rule does).
 */
export function donchian(bars: readonly Bar[], { lookback = 20 }: { lookback?: number } = {}): DonchianResult | null {
  if (bars.length < lookback + 2) return null
  const prior = bars.slice(-lookback - 1, -1)
  const high = Math.max(...prior.map(bar => bar.h))
  const low = Math.min(...prior.map(bar => bar.l))
  const close = (bars.at(-1) as Bar).c
  return {
    breakout: close > high ? 'up' : close < low ? 'down' : 'none',
    high: round(high, 6),
    low: round(low, 6),
    posPct: high === low ? 50 : round(((close - low) / (high - low)) * 100, 1),
  }
}

/**
 * Wilder's ADX with directional indicators: trend strength and side.
 */
export function adx(bars: readonly Bar[], { period = 14 }: { period?: number } = {}): AdxResult | null {
  if (bars.length < period * 2 + 2) return null
  const plusDm: number[] = [0]
  const minusDm: number[] = [0]
  const tr: number[] = [(bars[0] as Bar).h - (bars[0] as Bar).l]
  for (let index = 1; index < bars.length; index += 1) {
    const bar = bars[index] as Bar
    const previous = bars[index - 1] as Bar
    const up = bar.h - previous.h
    const down = previous.l - bar.l
    plusDm.push(up > down && up > 0 ? up : 0)
    minusDm.push(down > up && down > 0 ? down : 0)
    tr.push(Math.max(bar.h - bar.l, Math.abs(bar.h - previous.c), Math.abs(bar.l - previous.c)))
  }
  const smooth = (values: readonly number[]): number[] => {
    const out: number[] = Array.from({ length: values.length }, () => Number.NaN)
    let sum = values.slice(1, period + 1).reduce((total, value) => total + value, 0)
    out[period] = sum
    for (let index = period + 1; index < values.length; index += 1) {
      sum = sum - sum / period + (values[index] as number)
      out[index] = sum
    }
    return out
  }
  const trSmoothed = smooth(tr)
  const plusSmoothed = smooth(plusDm)
  const minusSmoothed = smooth(minusDm)
  const dx: number[] = []
  let adxValue = Number.NaN
  for (let index = period; index < bars.length; index += 1) {
    const trValue = trSmoothed[index] as number
    const plusDi = trValue === 0 ? 0 : ((plusSmoothed[index] as number) / trValue) * 100
    const minusDi = trValue === 0 ? 0 : ((minusSmoothed[index] as number) / trValue) * 100
    const sum = plusDi + minusDi
    const value = sum === 0 ? 0 : (Math.abs(plusDi - minusDi) / sum) * 100
    dx.push(value)
    if (dx.length === period) adxValue = dx.reduce((total, item) => total + item, 0) / period
    else if (dx.length > period && Number.isFinite(adxValue)) adxValue = (adxValue * (period - 1) + value) / period
  }
  const last = bars.length - 1
  const lastTr = trSmoothed[last] as number
  const plusDi = lastTr === 0 ? 0 : ((plusSmoothed[last] as number) / lastTr) * 100
  const minusDi = lastTr === 0 ? 0 : ((minusSmoothed[last] as number) / lastTr) * 100
  return {
    adx: round(adxValue, 1),
    plusDi: round(plusDi, 1),
    minusDi: round(minusDi, 1),
    trending: Number.isFinite(adxValue) && adxValue >= 25,
  }
}

/**
 * Evaluate every signal on one bar series and combine them into a conservative
 * consensus.
 */
export function evaluateSignals(bars: readonly Bar[]): SignalEvaluation {
  const st = supertrend(bars)
  const sq = squeeze(bars)
  const ich = ichimoku(bars)
  const dc = donchian(bars)
  const trend = adx(bars)
  const notes: string[] = []
  let score = 0

  if (st !== null) {
    score += st.dir * 0.3
    notes.push(`supertrend ${st.dir === 1 ? 'up' : 'down'} (${st.distancePct}% away)`)
  }
  if (ich !== null) {
    if (ich.state === 'above') score += 0.25
    else if (ich.state === 'below') score -= 0.25
    notes.push(`price ${ich.state} the cloud, tenkan/kijun ${ich.tkCross}`)
  }
  if (dc !== null) {
    if (dc.breakout === 'up') score += 0.15
    else if (dc.breakout === 'down') score -= 0.15
    if (dc.breakout !== 'none') notes.push(`donchian breakout ${dc.breakout}`)
  }
  if (sq !== null) {
    if (sq.on) notes.push('squeeze on: compression, wait for the release')
    else {
      score += Math.sign(sq.momentum) * 0.15
      notes.push(`momentum ${sq.momentum > 0 ? 'positive' : 'negative'} after the squeeze`)
    }
  }
  if (trend !== null) {
    if (trend.trending) {
      score += trend.plusDi > trend.minusDi ? 0.15 : -0.15
      notes.push(`adx ${trend.adx} trending ${trend.plusDi > trend.minusDi ? 'up' : 'down'}`)
    } else {
      notes.push(`adx ${trend.adx}: no trend`)
    }
  }

  const clamped = Math.max(-1, Math.min(1, round(score, 3)))
  return {
    signals: { supertrend: st, squeeze: sq, ichimoku: ich, donchian: dc, adx: trend },
    score: clamped,
    bias: clamped >= 0.3 ? 'long' : clamped <= -0.3 ? 'short' : 'flat',
    notes,
  }
}

/** Round for display, normalising negative zero. */
export function round(value: number, digits: number): number {
  if (!Number.isFinite(value)) return 0
  const factor = 10 ** digits
  const rounded = Math.round(value * factor) / factor
  return Object.is(rounded, -0) ? 0 : rounded
}
