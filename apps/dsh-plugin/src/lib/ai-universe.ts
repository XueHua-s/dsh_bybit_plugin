import type { Category, Instrument, Ticker } from './bybit-types.js'

/** Hard limits keep model-visible discovery small and liquid. */
export const AI_UNIVERSE_LIMIT = 30
export const AI_MIN_TURNOVER_USD = 1_000_000
export const AI_MAX_SPREAD_BPS = 75
export const AI_UNIVERSE_TTL_MS = 30_000

export type AiCandidate = {
  symbol: string
  category: Category
  baseCoin: string
  quoteCoin: string
  contractType: string | undefined
  price: number
  change24hPct: number
  turnover24h: number
  spreadBps: number
  fundingRatePct: number | undefined
  openInterest: number | undefined
  rules: {
    qtyStep: string
    minimumQuantity: number
    minimumNotionalUsd: number | undefined
    tickSize: string
    maxLeverage: number | undefined
  }
}

export type AiUniverse = {
  category: Category
  observedAt: number
  expiresAt: number
  catalogueSize: number
  eligibleCount: number
  candidates: AiCandidate[]
}

export type AiUniverseView = {
  status: 'not_checked' | 'fresh' | 'stale'
  universe: AiUniverse | null
}

type RawSnapshot = {
  category: Category
  observedAt: number
  expiresAt: number
  instruments: Instrument[]
  tickers: Ticker[]
}

type UniverseSource = {
  instruments(input: { category: Category, signal?: AbortSignal }): Promise<Instrument[]>
  tickers(input: { category: Category, signal?: AbortSignal }): Promise<Ticker[]>
}

/**
 * Turn a complete Bybit catalogue and current ticker snapshot into a bounded,
 * deterministic candidate set. Undefined allow-list means unrestricted;
 * an explicitly empty list intentionally matches nothing.
 */
export function buildAiUniverse(input: {
  category: Category
  instruments: Instrument[]
  tickers: Ticker[]
  allowlist?: readonly string[]
  now?: number
  expiresAt?: number
  limit?: number
}): AiUniverse {
  const { category, instruments, tickers } = input
  const allowlist = input.allowlist === undefined ? undefined : new Set(input.allowlist)
  const tickerBySymbol = new Map(tickers
    .filter(ticker => ticker.category === category)
    .map(ticker => [ticker.symbol, ticker]))
  const uniqueInstruments = new Map(instruments.map(instrument => [instrument.symbol, instrument]))
  const eligible = [...uniqueInstruments.values()].flatMap((instrument): AiCandidate[] => {
    if (!isEligibleInstrument(instrument, category, allowlist)) return []
    const ticker = tickerBySymbol.get(instrument.symbol)
    if (ticker === undefined || !isEligibleTicker(ticker)) return []
    const mid = (ticker.bid + ticker.ask) / 2
    const spreadBps = ((ticker.ask - ticker.bid) / mid) * 10_000
    if (!Number.isFinite(spreadBps) || spreadBps < 0 || spreadBps > AI_MAX_SPREAD_BPS) return []
    return [{
      symbol: instrument.symbol,
      category,
      baseCoin: instrument.baseCoin,
      quoteCoin: instrument.quoteCoin,
      contractType: instrument.contractType,
      price: ticker.last,
      change24hPct: ticker.change24hPct,
      turnover24h: ticker.turnover24h,
      spreadBps: round2(spreadBps),
      fundingRatePct: ticker.fundingRate === undefined ? undefined : ticker.fundingRate * 100,
      openInterest: ticker.openInterest,
      rules: {
        qtyStep: instrument.qtyStep ?? '',
        minimumQuantity: instrument.minOrderQty,
        minimumNotionalUsd: instrument.minNotionalUsd,
        tickSize: instrument.tickSize ?? '',
        maxLeverage: instrument.maxLeverage,
      },
    }]
  })
  eligible.sort((left, right) => right.turnover24h - left.turnover24h || left.symbol.localeCompare(right.symbol))
  const limit = Math.min(Math.max(Math.trunc(input.limit ?? AI_UNIVERSE_LIMIT), 1), AI_UNIVERSE_LIMIT)
  const observedAt = input.now ?? Date.now()
  return {
    category,
    observedAt,
    expiresAt: input.expiresAt ?? observedAt + AI_UNIVERSE_TTL_MS,
    catalogueSize: uniqueInstruments.size,
    eligibleCount: eligible.length,
    candidates: eligible.slice(0, limit),
  }
}

/**
 * Owns a short-lived, category-scoped source snapshot. A refresh failure is
 * returned to decision callers; the last successful snapshot is exposed only
 * through `peek` for clearly stale, read-only panel status.
 */
export function createAiUniverseService(source: UniverseSource, options: { ttlMs?: number, now?: () => number } = {}) {
  const ttlMs = Math.max(1_000, Math.trunc(options.ttlMs ?? AI_UNIVERSE_TTL_MS))
  const now = options.now ?? Date.now
  const latest = new Map<Category, RawSnapshot>()
  const inFlight = new Map<Category, Promise<RawSnapshot>>()
  const lastFailure = new Set<Category>()

  async function load(category: Category, signal?: AbortSignal): Promise<RawSnapshot> {
    const cached = latest.get(category)
    if (cached !== undefined && cached.expiresAt > now() && !lastFailure.has(category)) return cached
    let pending = inFlight.get(category)
    if (pending === undefined) {
      pending = (async () => {
        const [instruments, tickers] = await Promise.all([
          source.instruments({ category, ...(signal === undefined ? {} : { signal }) }),
          source.tickers({ category, ...(signal === undefined ? {} : { signal }) }),
        ])
        if (instruments.length === 0 || tickers.length === 0) {
          throw new Error(`Bybit ${category} discovery returned an incomplete catalogue or ticker snapshot`)
        }
        const observedAt = now()
        const snapshot = { category, observedAt, expiresAt: observedAt + ttlMs, instruments, tickers }
        latest.set(category, snapshot)
        lastFailure.delete(category)
        return snapshot
      })()
      inFlight.set(category, pending)
    }
    try {
      return await pending
    } catch (error) {
      lastFailure.add(category)
      throw error
    } finally {
      if (inFlight.get(category) === pending) inFlight.delete(category)
    }
  }

  return {
    async get(category: Category, allowlist?: readonly string[], signal?: AbortSignal): Promise<AiUniverse> {
      const snapshot = await load(category, signal)
      return buildAiUniverse({
        category,
        instruments: snapshot.instruments,
        tickers: snapshot.tickers,
        ...(allowlist === undefined ? {} : { allowlist }),
        now: snapshot.observedAt,
        expiresAt: snapshot.expiresAt,
      })
    },
    peek(category: Category, allowlist?: readonly string[]): AiUniverseView {
      const snapshot = latest.get(category)
      if (snapshot === undefined) return { status: 'not_checked', universe: null }
      const status = snapshot.expiresAt > now() && !lastFailure.has(category) ? 'fresh' : 'stale'
      return {
        status,
        universe: buildAiUniverse({
          category,
          instruments: snapshot.instruments,
          tickers: snapshot.tickers,
          ...(allowlist === undefined ? {} : { allowlist }),
          now: snapshot.observedAt,
          expiresAt: snapshot.expiresAt,
        }),
      }
    },
  }
}

/** Resolve explicit AI analysis choices; no default ranking is treated as a decision. */
export function selectAiSymbols(requested: unknown, universe: AiUniverse, maximum = 4): string[] {
  if (!Array.isArray(requested)) throw new Error('symbols must be an array selected from the current AI candidate universe')
  if (requested.length > maximum) throw new Error(`select at most ${maximum} eligible symbols`)
  const eligible = new Set(universe.candidates.map(candidate => candidate.symbol))
  const selected: string[] = []
  for (const value of requested) {
    if (typeof value !== 'string') throw new Error('symbols must contain eligible symbol strings')
    const symbol = value.trim().toUpperCase()
    if (!eligible.has(symbol)) throw new Error(`${symbol} is outside the current AI eligible candidate universe`)
    if (!selected.includes(symbol)) selected.push(symbol)
  }
  return selected
}

/** Existing positions outside a refreshed universe are selectable only to flatten. */
export function decisionSymbols(universe: AiUniverse | null, action: unknown, openSymbols: readonly string[]): string[] {
  const symbols = universe?.candidates.map(candidate => candidate.symbol) ?? []
  const normalizedAction = typeof action === 'string' ? action.toLowerCase() : ''
  if (normalizedAction === 'flat') {
    for (const symbol of openSymbols) if (!symbols.includes(symbol)) symbols.push(symbol)
  }
  return symbols
}

function isEligibleInstrument(instrument: Instrument, category: Category, allowlist: ReadonlySet<string> | undefined): boolean {
  if (instrument.category !== category || instrument.status !== 'Trading' || instrument.quoteCoin !== 'USDT') return false
  if (allowlist !== undefined && !allowlist.has(instrument.symbol)) return false
  if (category === 'spot' && instrument.contractType !== 'Spot') return false
  if (category === 'linear' && instrument.contractType !== 'LinearPerpetual') return false
  return positive(instrument.minOrderQty) && positiveStep(instrument.qtyStep) && positiveStep(instrument.tickSize)
}

function isEligibleTicker(ticker: Ticker): boolean {
  return positive(ticker.last)
    && Number.isFinite(ticker.change24hPct)
    && Number.isFinite(ticker.turnover24h)
    && ticker.turnover24h >= AI_MIN_TURNOVER_USD
    && positive(ticker.bid)
    && positive(ticker.ask)
    && ticker.ask >= ticker.bid
}

function positive(value: number): boolean {
  return Number.isFinite(value) && value > 0
}

function positiveStep(value: string | undefined): value is string {
  return value !== undefined && Number.isFinite(Number(value)) && Number(value) > 0
}

function round2(value: number): number {
  return Math.round(value * 100) / 100
}
