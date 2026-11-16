import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { defaultStateDir } from './state.js'
import { normalizeCategory, normalizeInterval, normalizeSymbol } from './bybit.js'
import type { Candle } from './bybit.js'
import type { JournalDecision } from './ai-types.js'
import type { StrategyParams } from './strategies.js'

export type Settings = {
  env: 'live' | 'demo' | 'testnet'; apiKeyEnv: string; apiSecretEnv: string; fallbackApiKey: string; fallbackApiSecret: string; fallbackCredentialSource: string; credentialsFile: string; credentialsSource: string; allowLiveTrading: boolean; allowTestnetTrading: boolean; allowMainAccount: boolean; maxOrderNotionalPctOfEquity: number; maxOrderNotionalUsd: number; paperBalanceUsd: number; defaultSymbol: string; defaultCategory: ReturnType<typeof normalizeCategory>; stateFile: string; feeBps: number; recvWindow: number; timeoutMs: number; aiEnabled: boolean; aiStartEquity: number; aiRiskPerTradePct: number; aiMaxPositionPct: number; aiMaxOpenPositions: number; aiMaxDailyLossPct: number; aiMaxDrawdownPct: number; aiFeeBps: number; aiSymbols: string[]; aiTimeframes: string[]
}
type CredentialsDocument = { apiKey: string, apiSecret: string, env?: string }
export type CleanJson = null | boolean | string | number | CleanJson[] | { [key: string]: CleanJson }

/**
 * Normalise the plugin row's config into complete settings.
 * @param {Record<string, unknown>} config
 */
function resolveSettings(config: Record<string, unknown>): Settings {
  const env = config.env === 'live' || config.env === 'testnet' || config.env === 'demo' ? config.env : 'testnet'
  const credentialsFile = text(config.credentialsFile) || join(defaultStateDir(), 'credentials.json')
  const fromFile = readCredentialsFile(credentialsFile, env)
  const envKey = text(process.env.BYBIT_API_KEY)
  const envSecret = text(process.env.BYBIT_API_SECRET)
  const fallbackApiKey = envKey || fromFile.apiKey
  const fallbackApiSecret = envSecret || fromFile.apiSecret
  const fallbackCredentialSource = envKey && envSecret ? 'environment' : fromFile.apiKey && fromFile.apiSecret ? 'legacy credentials file' : 'none'
  return {
    env,
    apiKeyEnv: text(config.apiKeyEnv) || 'BYBIT_API_KEY',
    apiSecretEnv: text(config.apiSecretEnv) || 'BYBIT_API_SECRET',
    fallbackApiKey,
    fallbackApiSecret,
    fallbackCredentialSource,
    credentialsFile,
    credentialsSource: fallbackCredentialSource,
    allowLiveTrading: config.allowLiveTrading === true,
    allowTestnetTrading: config.allowTestnetTrading === true,
    // A main-account key can reach the whole balance; require a second explicit switch.
    allowMainAccount: config.allowMainAccount === true,
    maxOrderNotionalPctOfEquity: clamp(Number(config.maxOrderNotionalPctOfEquity), 1, 100, 25),
    maxOrderNotionalUsd: positive(config.maxOrderNotionalUsd, 200),
    paperBalanceUsd: positive(config.paperBalanceUsd, 10000),
    defaultSymbol: normalizeSymbol(config.defaultSymbol, 'BTCUSDT'),
    defaultCategory: normalizeCategory(config.defaultCategory ?? 'linear'),
    stateFile: text(config.stateFile) || join(defaultStateDir(), 'state.json'),
    feeBps: clamp(Number(config.backtestFeeBps), 0, 100, 6),
    recvWindow: clamp(Number(config.recvWindowMs), 1000, 60_000, 5000),
    timeoutMs: clamp(Number(config.timeoutMs), 2000, 120_000, 15_000),
    // AI decision track and the code-owned limits it must respect.
    aiEnabled: config.aiEnabled !== false,
    aiStartEquity: positive(config.aiStartEquity, positive(config.paperBalanceUsd, 10000)),
    aiRiskPerTradePct: clamp(Number(config.aiRiskPerTradePct), 0.1, 10, 1),
    aiMaxPositionPct: clamp(Number(config.aiMaxPositionPct), 5, 100, 50),
    aiMaxOpenPositions: Math.trunc(clamp(Number(config.aiMaxOpenPositions), 1, 6, 2)),
    aiMaxDailyLossPct: clamp(Number(config.aiMaxDailyLossPct), 0.5, 20, 3),
    aiMaxDrawdownPct: clamp(Number(config.aiMaxDrawdownPct), 2, 60, 20),
    aiFeeBps: clamp(Number(config.aiFeeBps), 0, 100, 6),
    aiSymbols: normalizeSymbolList(config.aiSymbols),
    aiTimeframes: normalizeTimeframes(config.aiTimeframes),
  }
}

/** Symbols the AI track watches; two by default, at most four. */
function normalizeSymbolList(value: unknown): string[] {
  const list = Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string').map(item => normalizeSymbol(item)).filter((symbol, index, all) => all.indexOf(symbol) === index).slice(0, 4)
    : []
  return list.length > 0 ? list : ['BTCUSDT', 'ETHUSDT']
}

/** Timeframes the brief covers, primary first. */
function normalizeTimeframes(value: unknown): string[] {
  const list = Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string').map(item => normalizeInterval(item)).slice(0, 4) : []
  return list.length > 0 ? list : ['240', '60', 'D']
}

/** Journal entry trimmed for a tool result. */
function compactDecision(entry: JournalDecision) {
  return {
    time: new Date(entry.time).toISOString(),
    symbol: entry.symbol,
    action: entry.action,
    sizePct: entry.sizePct,
    confidence: entry.confidence,
    status: entry.status,
    thesis: entry.thesis,
    result: entry.result,
  }
}

/** Require one of a fixed set of values. */
function pick<const Values extends readonly string[]>(value: unknown, allowed: Values, label: string): Values[number] {
  if (typeof value === 'string' && allowed.includes(value)) return value
  throw new Error(`${label} must be one of: ${allowed.join(', ')}`)
}

function optionalNumber(value: unknown): number | undefined {
  if (value === undefined || value === null || value === '') return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

function optionalParams(args: Record<string, unknown>): StrategyParams {
  const params: StrategyParams = {}
  const fields = ['fast', 'slow', 'period', 'entry', 'exit', 'lookback'] as const
  for (const field of fields) {
    const value = optionalNumber(args[field])
    if (value !== undefined) params[field] = value
  }
  return params
}

/**
 * Read an optional key file so credentials never have to sit in the profile patch
 * or in a chat message. Accepts `{ apiKey, apiSecret }` or `{ key, secret }`.
 * @param {string} file
 * @returns {{ apiKey: string, apiSecret: string }}
 */
function readCredentialsFile(file: string, expectedEnv?: string): CredentialsDocument {
  try {
    if (!existsSync(file)) return { apiKey: '', apiSecret: '' }
    const parsed: unknown = JSON.parse(readFileSync(file, 'utf8'))
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return { apiKey: '', apiSecret: '' }
    const values = parsed as Record<string, unknown>
    if (typeof values.env === 'string' && expectedEnv !== undefined && values.env !== expectedEnv) return { apiKey: '', apiSecret: '' }
    return {
      apiKey: text(values.apiKey ?? values.key),
      apiSecret: text(values.apiSecret ?? values.secret),
    }
  } catch {
    return { apiKey: '', apiSecret: '' }
  }
}

/** Trimmed string or empty. */
function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : ''
}

/** Positive finite number or the fallback. */
function positive(value: unknown, fallback: number): number {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : fallback
}

/** Clamp a possibly absent number. */
function clamp(value: number, min: number, max: number, fallback: number): number {
  if (!Number.isFinite(value)) return fallback
  return Math.min(Math.max(value, min), max)
}

/** Compact price text without float noise. */
function trim(value: number): string {
  return Number.isFinite(value) ? String(Number(value.toFixed(8))) : '0'
}

/** Round for display. */
function round2(value: number): number {
  return Math.round(value * 100) / 100
}

/** Round eight decimals for base quantities. */
function round8(value: number): number {
  return Math.round(value * 1e8) / 1e8
}

/** First/last bar facts for a fetched window. */
function describeWindow(bars: Candle[]) {
  if (bars.length === 0) return { bars: 0 }
  const first = bars[0]
  const last = bars.at(-1)
  if (first === undefined || last === undefined) return { bars: 0 }
  const high = Math.max(...bars.map(bar => bar.h))
  const low = Math.min(...bars.map(bar => bar.l))
  return {
    bars: bars.length,
    from: new Date(first.t).toISOString(),
    to: new Date(last.t).toISOString(),
    firstClose: first.c,
    lastClose: last.c,
    high,
    low,
    changePct: round2(((last.c - first.c) / first.c) * 100),
  }
}

/** Drop undefined members and non-finite numbers so a tool value is lossless JSON. */
function clean(value: unknown): CleanJson {
  if (Array.isArray(value)) return value.map(clean)
  if (value !== null && typeof value === 'object') {
    const out: Record<string, CleanJson> = {}
    for (const [key, member] of Object.entries(value)) {
      if (member === undefined) continue
      out[key] = clean(member)
    }
    return out
  }
  if (typeof value === 'number') {
    // The pipeline rejects NaN, Infinity, and negative zero as non-lossless JSON.
    if (!Number.isFinite(value)) return null
    return Object.is(value, -0) ? 0 : value
  }
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value
  return null
}

export { resolveSettings, normalizeSymbolList, normalizeTimeframes, compactDecision, pick, optionalNumber, optionalParams, readCredentialsFile, text, positive, clamp, trim, round2, round8, describeWindow, clean }
