/** Formatting and chart math shared by panel components. */
const pad = (number: number): string => String(number).padStart(2, '0')
/** Format a price with a sensible number of decimals. */
export function fmtPrice(value: number): string {
  if (!Number.isFinite(value)) return '—'
  const abs = Math.abs(value)
  const digits = abs >= 1000 ? 1 : abs >= 10 ? 2 : abs >= 1 ? 3 : abs >= 0.01 ? 5 : 7
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

/** Format a signed percentage. */
export function fmtPct(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(digits)}%`
}

/** Format a USD amount with grouping. */
export function fmtUsd(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return '—'
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

/** Format a compact quantity. */
export function fmtQty(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return value.toLocaleString(undefined, { maximumFractionDigits: 6 })
}

/** Tone class for a signed number. */
export function tone(value: number): string {
  if (!Number.isFinite(value) || value === 0) return ''
  return value > 0 ? 'bq-up' : 'bq-down'
}

/** Time of day or date, depending on the candle interval. */
export function fmtBarTime(ms: number, intraday: boolean): string {
  const date = new Date(ms)
  const month = pad(date.getMonth() + 1)
  const day = pad(date.getDate())
  if (!intraday) return `${month}-${day}`
  return `${month}-${day} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** Simple moving average aligned with the input. */
export function sma(values: number[], period: number): number[] {
  const out = Array.from({ length: values.length }, () => Number.NaN)
  let sum = 0
  for (let index = 0; index < values.length; index += 1) {
    sum += values[index] ?? 0
    if (index >= period) sum -= values[index - period] ?? 0
    if (index >= period - 1) out[index] = sum / period
  }
  return out
}

/** Axis text for a price. */
export function axisPrice(value: number, span: number): string {
  if (span >= 1000) return value.toFixed(0)
  if (span >= 10) return value.toFixed(1)
  if (span >= 1) return value.toFixed(2)
  if (span >= 0.01) return value.toFixed(4)
  return value.toFixed(6)
}
