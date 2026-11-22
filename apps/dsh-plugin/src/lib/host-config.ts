import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { defaultStateDir } from './state.js'
import { normalizeCategory, normalizeInterval, normalizeSymbol } from './bybit.js'
import type { Candle } from './bybit.js'
import type { JournalDecision } from './ai-types.js'
import type { StrategyParams } from './strategies.js'
import { evidenceEnvelope } from './trust.js'

export type Settings = {
  env: 'live' | 'demo' | 'testnet'; apiKeyEnv: string; apiSecretEnv: string; fallbackApiKey: string; fallbackApiSecret: string; fallbackCredentialSource: string; credentialsFile: string; credentialsSource: string; maxOrderNotionalUsd: number; paperBalanceUsd: number; defaultSymbol: string; defaultCategory: ReturnType<typeof normalizeCategory>; stateFile: string; feeBps: number; recvWindow: number; timeoutMs: number; aiEnabled: boolean; aiStartEquity: number; aiRiskPerTradePct: number; aiMaxPositionPct: number; aiMaxOpenPositions: number; aiMaxDailyLossPct: number; aiMaxDrawdownPct: number; aiFeeBps: number; aiSymbols: string[]; aiTimeframes: string[]; aiBackgroundLoopEnabled: boolean; aiBackgroundLoopIntervalMs: number; aiBackgroundEnvironment: 'testnet' | 'internal_paper'; paperFixtureId: string; paperSessionId: string
}
type CredentialsDocument = { apiKey: string, apiSecret: string, env?: string }
export type CleanJson = null | boolean | string | number | CleanJson[] | { [key: string]: CleanJson }

/**
 * Normalise the plugin row's config into complete settings.
 * @param {Record<string, unknown>} config
 */
function resolveSettings(config: Record<string, unknown>): Settings {
  const env = config.env === 'live' || config.env === 'testnet' || config.env === 'demo' ? config.env : 'testnet'
  const defaultCredentialFile = env === 'live'
    ? join(defaultStateDir(), 'live', 'credentials.json')
    : join(defaultStateDir(), 'credentials.json')
  const credentialsFile = text(config.credentialsFile) || defaultCredentialFile
  const apiKeyEnv = text(config.apiKeyEnv) || (env === 'live' ? 'BYBIT_MAINNET_API_KEY' : 'BYBIT_API_KEY')
  const apiSecretEnv = text(config.apiSecretEnv) || (env === 'live' ? 'BYBIT_MAINNET_API_SECRET' : 'BYBIT_API_SECRET')
  if (env === 'live' && [apiKeyEnv, apiSecretEnv].some(name =>
    ['BYBIT_API_KEY', 'BYBIT_API_SECRET', 'BYBIT_TESTNET_API_KEY', 'BYBIT_TESTNET_API_SECRET'].includes(name))) {
    throw new Error('Mainnet credential environment variables must not reuse Testnet variable names')
  }
  const defaultStateFile = env === 'live'
    ? join(defaultStateDir(), 'live', 'state.json')
    : join(defaultStateDir(), 'state.json')
  const fromFile = readCredentialsFile(credentialsFile, env)
  const envKey = text(process.env[apiKeyEnv])
  const envSecret = text(process.env[apiSecretEnv])
  if ((envKey === '') !== (envSecret === '')) {
    throw new Error(`credential environment variables must be configured as a pair for ${env}`)
  }
  const filePair = fromFile.apiKey !== '' && fromFile.apiSecret !== ''
  const fallbackApiKey = envKey !== '' ? envKey : filePair ? fromFile.apiKey : ''
  const fallbackApiSecret = envSecret !== '' ? envSecret : filePair ? fromFile.apiSecret : ''
  const fallbackCredentialSource = envKey !== '' ? 'environment' : filePair ? 'legacy credentials file' : 'none'
  return {
    env,
    apiKeyEnv,
    apiSecretEnv,
    fallbackApiKey,
    fallbackApiSecret,
    fallbackCredentialSource,
    credentialsFile,
    credentialsSource: fallbackCredentialSource,
    maxOrderNotionalUsd: positive(config.maxOrderNotionalUsd, 200),
    paperBalanceUsd: positive(config.paperBalanceUsd, 10000),
    defaultSymbol: normalizeSymbol(config.defaultSymbol, 'BTCUSDT'),
    defaultCategory: normalizeCategory(config.defaultCategory ?? 'linear'),
    stateFile: text(config.stateFile) || defaultStateFile,
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
    aiBackgroundLoopEnabled: config.aiBackgroundLoopEnabled === true,
    aiBackgroundLoopIntervalMs: clamp(Number(config.aiBackgroundLoopIntervalMs), 60_000, 24 * 60 * 60_000, 15 * 60_000),
    aiBackgroundEnvironment: config.aiBackgroundEnvironment === 'internal_paper' ? 'internal_paper' : 'testnet',
    paperFixtureId: text(config.paperFixtureId) || 'paper-bundle',
    paperSessionId: text(config.paperSessionId),
  }
}

/** Symbols the AI track watches; two by default, at most four. */
function normalizeSymbolList(value: unknown): string[] {
  const list = Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string').map(item => normalizeSymbol(item)).filter((symbol, index, all) => all.indexOf(symbol) === index).slice(0, 4)
    : []
  return list
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
    evidence: {
      thesis: evidenceEnvelope(entry.thesis, 'agent'),
      invalidation: evidenceEnvelope(entry.invalidation, 'agent'),
    },
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
  let content: string
  try {
    content = readFileSync(file, 'utf8')
  } catch (error) {
    if (isMissingFile(error)) return { apiKey: '', apiSecret: '' }
    throw new Error('Could not safely read the configured Bybit credentials file', { cause: error })
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(content)
  } catch (error) {
    throw new Error('The configured Bybit credentials file contains invalid JSON', { cause: error })
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('The configured Bybit credentials file must contain a JSON object')
  }
  const values = parsed as Record<string, unknown>
  const rawKey = values.apiKey ?? values.key
  const rawSecret = values.apiSecret ?? values.secret
  if ((rawKey !== undefined && typeof rawKey !== 'string') || (rawSecret !== undefined && typeof rawSecret !== 'string')) {
    throw new Error('The configured Bybit credentials file must contain string key fields')
  }
  const apiKey = text(rawKey)
  const apiSecret = text(rawSecret)
  if ((apiKey === '') !== (apiSecret === '')) {
    throw new Error('The configured Bybit credentials file must contain a complete key pair')
  }
  const hasEnvironment = values.env !== undefined
  if (hasEnvironment && (typeof values.env !== 'string' || (expectedEnv !== undefined && values.env !== expectedEnv))) {
    throw new Error('The configured Bybit credentials file belongs to a different environment')
  }
  if (expectedEnv === 'live' && apiKey !== '' && values.env !== 'live') {
    throw new Error('Mainnet credentials must include an explicit live environment marker')
  }
  return { apiKey, apiSecret, ...(typeof values.env === 'string' ? { env: values.env } : {}) }
}

/** Resolve one complete credential source without combining key halves. */
export function selectCredentialPair(
  keyValue: unknown,
  secretValue: unknown,
  fallback: { apiKey: string, apiSecret: string, source: string },
): { apiKey: string, apiSecret: string, source: string } {
  const hasKey = keyValue !== undefined && keyValue !== null
  const hasSecret = secretValue !== undefined && secretValue !== null
  if (hasKey !== hasSecret) throw new Error('a credential source must provide both the API key and API secret')
  if (!hasKey) return fallback
  const apiKey = text(keyValue)
  const apiSecret = text(secretValue)
  if (apiKey === '' || apiSecret === '') throw new Error('a credential source must provide a non-empty API key pair')
  return { apiKey, apiSecret, source: 'harness credential store' }
}

function isMissingFile(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'code' in error && error.code === 'ENOENT'
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
