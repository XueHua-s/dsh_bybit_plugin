/** Input normalization, signed query encoding and response parsing for Bybit V5. */
import { BybitError } from './bybit-error.js'
import type { Category, Instrument } from './bybit-types.js'
import { INTERVALS, INTERVAL_ALIASES, INTERVAL_MS } from './bybit-constants.js'

export function normalizeInterval(value: string | undefined): string {
  const raw = (value ?? '').trim()
  if (raw === '') return '60'
  if ((INTERVALS as readonly string[]).includes(raw)) return raw
  const alias = INTERVAL_ALIASES[raw] ?? INTERVAL_ALIASES[raw.toLowerCase()]
  if (alias !== undefined) return alias
  throw new BybitError(`unsupported interval "${raw}"; use one of ${INTERVALS.join(', ')} or 1m/5m/15m/1h/4h/1d`)
}

export function intervalMs(interval: string): number {
  return INTERVAL_MS[interval] ?? INTERVAL_MS['60'] ?? 3_600_000
}

export function intervalLabel(interval: string): string {
  for (const [alias, code] of Object.entries(INTERVAL_ALIASES)) if (code === interval) return alias
  return interval
}

export function normalizeCategory(value: unknown): Category {
  const raw = (value ?? 'linear').toString().trim().toLowerCase()
  if (raw === 'spot' || raw === 'linear') return raw
  throw new BybitError(`category must be "linear" (USDT perpetual) or "spot", received "${raw}"`)
}

export function normalizeSymbol(value: unknown, fallback = 'BTCUSDT'): string {
  const raw = (value ?? fallback).toString().trim().toUpperCase()
  if (!/^[A-Z0-9]{2,20}$/.test(raw)) throw new BybitError(`invalid symbol "${raw}"`)
  return raw
}

export function formatQuantity(value: number, step: string | undefined): string {
  const increment = Number(step)
  if (!Number.isFinite(increment) || increment <= 0) return trimNumber(value)
  const dot = step?.indexOf('.') ?? -1
  const decimals = dot < 0 || step === undefined ? 0 : step.length - dot - 1
  const rounded = Math.floor(value / increment + 1e-9) * increment
  return rounded.toFixed(decimals)
}

export function trimNumber(value: number): string {
  if (!Number.isFinite(value)) return '0'
  return value.toFixed(8).replace(/\.?0+$/, '') || '0'
}

export function toQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.append(key, String(value))
  }
  return search.toString()
}

export function mapLevels(rows: unknown): Array<[number, number]> {
  if (!Array.isArray(rows)) return []
  return rows.map((row: unknown) => {
    const levels = Array.isArray(row) ? row : []
    return [number(levels[0]), number(levels[1])]
  })
}

export function mapInstrument(row: Record<string, unknown>, category: Category): Instrument {
  const lot = record(row.lotSizeFilter)
  const price = record(row.priceFilter)
  const leverage = record(row.leverageFilter)
  return {
    symbol: String(row.symbol), category, status: String(row.status ?? ''),
    baseCoin: String(row.baseCoin ?? ''), quoteCoin: String(row.quoteCoin ?? ''),
    contractType: typeof row.contractType === 'string' ? row.contractType : category === 'spot' ? 'Spot' : undefined,
    qtyStep: stringValue(lot.qtyStep ?? lot.basePrecision),
    minOrderQty: number(lot.minOrderQty ?? lot.minOrderAmt),
    minNotionalUsd: number(lot.minNotionalValue) || undefined,
    tickSize: stringValue(price.tickSize),
    maxLeverage: number(leverage.maxLeverage) || undefined,
    fundingIntervalMinutes: number(row.fundingInterval) || undefined,
  }
}

export function number(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined
}
