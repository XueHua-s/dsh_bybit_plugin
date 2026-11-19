/**
 * Bybit quant plugin, Host half.
 *
 * Registers five model-facing tools over one shared Bybit client and one shared
 * paper book, contributes a short prompt note, and serves one read-only JSON
 * route for the Web panel on the connection bridge, which carries the Web GUI's
 * Host/Origin fence and browser authentication:
 *
 *   GET /api/bybit-quant            ticker, candles, paper book, last backtest
 *   GET /api/bybit-quant?view=health  plugin and environment facts
 *
 * Safety: exchange writes are unavailable until the engine-owned native
 * execution authority is connected. The conversation tools keep previews and
 * the panel reports that no exchange writer is active.
 *
 * Tool definitions are plain objects with raw JSON Schema parameters, so the
 * bundle imports nothing from the dsh installation and installs as a
 * dependency-free linked directory.
 */
import { createEngine } from './lib/engine.js'
import { createPaperEngine } from './lib/engine-paper.js'
import { BybitClient, normalizeCategory } from './lib/bybit.js'


import { createStore } from './lib/state.js'
import { paperStatus, positionKey } from './lib/paper.js'

import { createRuntimeMonitor } from './lib/monitor.js'
import type { DecisionTrack } from './lib/ai-types.js'
import type { Category, Instrument } from './lib/bybit.js'
import { resolveSettings, clean, selectCredentialPair } from './lib/host-config.js'
import { createTrack, markedEquity, rollDay, scoreTrack } from './lib/ai.js'
import { BYBIT_QUANT_SYSTEM_PROMPT_V2 } from './prompts/bybit-quant/v2.js'

/** Plugin version reported by the health route. */
const VERSION = '1.4.5'

/** Authenticated exact Fetch route the Web panel polls (`?view=health` for facts). */

/** Cooperative tool budget in ms. */
const TOOL_TIMEOUT_MS = 20_000

/** Panel market data is reused for this long so a 5s poll stays cheap. */

/** Output declaration shared by every tool: one formatted JSON text block. */
const TEXT_OUTPUT = {
  schema: { type: 'object', additionalProperties: true as const },
  render: (_args: Record<string, unknown>, value: unknown) => [{ type: 'text' as const, text: JSON.stringify(value, null, 2) }],
}

type ToolExecution = { signal?: AbortSignal }
type ToolRun = (args: Record<string, unknown>, exec: ToolExecution) => Promise<unknown>
export type ToolSpec = {
  name: string
  description: string
  parameters: Record<string, unknown>
  run: ToolRun
  concurrent?: boolean
}
export type ToolDefinition = Omit<ToolSpec, 'run' | 'concurrent'> & {
  output: typeof TEXT_OUTPUT
  timeoutMs: number
  isConcurrencySafe?: () => true
  execute(args: Record<string, unknown> | undefined, exec: ToolExecution): Promise<unknown>
}
type PluginLogger = { info(message: string): void, warn?(message: string): void, error?(message: string): void }
type WebRoute = {
  path: string
  methods: string[]
  requestBody: 'buffered' | 'streaming'
  fetch(request: Request): Response | Promise<Response>
}
type WebContext = {
  effect(effect: () => void | (() => void | Promise<void>), label?: string): void
  connection: { fetch: { register(route: WebRoute): void | (() => void | Promise<void>) } }
}
export type PluginContext = {
  logger?(name: string): PluginLogger | undefined
  credentials?: { resolve(name: string): Promise<{ value?: string } | undefined> }
  systemPrompt: { section(section: { name: string, order: number, text: string }): void }
  tools: { register(definition: ToolDefinition): void }
  effect(effect: () => void | (() => void | Promise<void>), label?: string): void
  inject(dependencies: string[], callback: (context: WebContext) => void): void
}

/** Cordis plugin name used by loader diagnostics. */
export const name = 'bybit-quant'

/** Services the plugin needs; `webServer` is injected separately as optional. */
export const inject = ['tools', 'systemPrompt', 'credentials']

/** Build a registry definition with the shared output rendering. */
function tool(definition: ToolSpec): ToolDefinition {
  return {
    name: definition.name,
    description: definition.description,
    parameters: definition.parameters,
    output: TEXT_OUTPUT,
    timeoutMs: TOOL_TIMEOUT_MS,
    ...definition.concurrent === true ? { isConcurrencySafe: () => true } : {},
    async execute(args, exec) {
      if (args !== undefined && (args === null || typeof args !== 'object' || Array.isArray(args))) return { ok: false, code: 'invalid_arguments' }
      const value = await definition.run(args ?? {}, exec)
      return clean(value)
    },
  }
}

/**
 * Register the tools, prompt note, and panel routes.
 * @param {import('@deepseek-ai/cordis').Context} ctx
 * @param {Record<string, unknown>} [config]
 */
export function createHostRuntime(ctx: PluginContext, config: Record<string, unknown> = {}) {
  // Validate the service destination before resolving any legacy credential source.
  const paper = createPaperEngine(config)
  const engine = createEngine(config)
  const settings = resolveSettings(config)
  ctx.effect(() => () => paper.close(), 'bybit-quant: native paper client shutdown')
  ctx.effect(() => () => engine.close(), 'bybit-quant: engine client shutdown')
  const runtimeMonitor = createRuntimeMonitor({ websocketEnabled: false })
  const client = new BybitClient({
    env: settings.env,
    apiKey: settings.fallbackApiKey,
    apiSecret: settings.fallbackApiSecret,
    recvWindow: settings.recvWindow,
    timeoutMs: settings.timeoutMs,
    observeRequest: metric => runtimeMonitor.observeRequest(metric),
    observeQueue: depth => runtimeMonitor.observeQueue(depth),
    resolveCredentials: async () => {
      const credentialStore = ctx.credentials
      if (credentialStore !== undefined && typeof credentialStore.resolve === 'function') {
        const [key, secret] = await Promise.all([
          credentialStore.resolve(settings.apiKeyEnv),
          credentialStore.resolve(settings.apiSecretEnv),
        ])
        const selected = selectCredentialPair(key?.value, secret?.value, {
          apiKey: settings.fallbackApiKey,
          apiSecret: settings.fallbackApiSecret,
          source: settings.fallbackCredentialSource,
        })
        settings.credentialsSource = selected.source
        return { apiKey: selected.apiKey, apiSecret: selected.apiSecret }
      }
      return { apiKey: settings.fallbackApiKey, apiSecret: settings.fallbackApiSecret }
    },
  })
  const store = createStore({ file: settings.stateFile, startingBalance: settings.paperBalanceUsd })
  /** Short-lived panel cache keyed by market and interval. */
  const panelCache = new Map<string, { value: Record<string, unknown>, expires: number }>()
  /** Instrument metadata cache keyed by category:symbol. */
  const instrumentCache = new Map<string, { value: Instrument, expires: number }>()
  const logger = ctx.logger?.('bybit-quant')
  ctx.effect(() => runtimeMonitor.start(5000), 'bybit-quant: runtime monitor')
  ctx.effect(() => () => {
    panelCache.clear()
    instrumentCache.clear()
  }, 'bybit-quant: cache shutdown')

  logger?.info(
    `loaded v${VERSION}: env=${settings.env}, keys=${client.hasCredentials ? 'yes' : 'no'}, `
    + `exchangeWrites=unavailable, state=${settings.stateFile}`,
  )

  ctx.systemPrompt.section({
    name: 'tool:bybit-quant',
    order: 620,
    text: BYBIT_QUANT_SYSTEM_PROMPT_V2,
  })

  /** Resolve one mark price for a symbol. */
  async function markPrice(category: Category, symbol: string, signal?: AbortSignal): Promise<number> {
    const ticker = await client.ticker({ category, symbol, signal })
    return ticker.last
  }

  /** Cached instrument metadata (quantity step, minimums). */
  async function instrumentFor(category: Category, symbol: string, signal?: AbortSignal): Promise<Instrument> {
    const key = `${category}:${symbol}`
    const cached = instrumentCache.get(key)
    if (cached !== undefined && cached.expires > Date.now()) return cached.value
    const value = await client.instrument({ category, symbol, signal })
    instrumentCache.set(key, { value, expires: Date.now() + 10 * 60_000 })
    return value
  }

  /** Marks for every open paper position, best effort. */
  async function paperMarks(): Promise<Record<string, number>> {
    const positions = Object.values(store.get().paper.positions)
    if (positions.length === 0) return {}
    const results = await Promise.allSettled(
      positions.map(position => client.ticker({ category: normalizeCategory(position.category), symbol: position.symbol })),
    )
    /** @type {Record<string, number>} */
    const marks: Record<string, number> = {}
    results.forEach((result, index) => {
      if (result.status !== 'fulfilled') return
      const position = positions[index]
      if (position === undefined) return
      marks[positionKey(position.category, position.symbol)] = result.value.last
    })
    return marks
  }

  /** The current paper book, marked to live prices where available. */
  async function statusOfPaper() {
    return paperStatus(store.get(), await paperMarks())
  }

  /** Symbols the user watches; the configured default applies until they set one. */
  function watchlist() {
    const stored = store.get().watchlist
    const list = Array.isArray(stored) ? stored.filter(symbol => typeof symbol === 'string' && symbol !== '') : []
    return list.length > 0 ? list : settings.aiSymbols
  }

  /** Persist a watchlist (empty clears back to the configured default). */
  function saveWatchlist(symbols: string[]): void {
    store.mutate((state) => {
      state.watchlist = symbols
      return null
    })
  }

  /** Symbols a decision may trade: the watchlist plus the configured defaults. */
  function tradableSymbols() {
    return [...new Set([...watchlist(), ...settings.aiSymbols])]
  }

  /** The AI track, created from the configured starting equity on first use. */
  function aiTrack(): DecisionTrack {
    const state = store.get()
    if (state.ai === undefined || state.ai?.version !== 1) {
      state.ai = createTrack(settings.aiStartEquity)
      store.mutate(() => null)
    }
    rollDay(state.ai, markedEquity(state.ai, {}).equity)
    return state.ai
  }

  /** Limits echoed to the model and the panel. */
  function aiLimits() {
    return {
      startEquityUsd: settings.aiStartEquity,
      riskPerTradePct: settings.aiRiskPerTradePct,
      maxPositionPct: settings.aiMaxPositionPct,
      maxOpenPositions: settings.aiMaxOpenPositions,
      maxDailyLossPct: settings.aiMaxDailyLossPct,
      maxDrawdownPct: settings.aiMaxDrawdownPct,
      feeBps: settings.aiFeeBps,
      symbols: settings.aiSymbols,
      watchlist: watchlist(),
      timeframes: settings.aiTimeframes,
    }
  }

  /** Journal + book view for the panel. */
  function aiSummary(marks: Record<string, number> = {}) {
    const track = store.get().ai
    if (track === undefined || track?.version !== 1) return null
    const score = scoreTrack({ track, marks: marks ?? {} })
    return {
      startEquityUsd: track.startEquity,
      equityUsd: score.book.equity,
      totalReturnPct: score.book.totalReturnPct,
      maxDrawdownPct: score.book.maxDrawdownPct,
      feesPaidUsd: score.book.feesPaidUsd,
      openPositions: score.book.positions,
      closed: score.closed,
      hitRatePct: score.hitRatePct,
      avgRMultiple: score.avgRMultiple,
      brier: score.brier,
      calibration: score.calibration,
      curve: score.curve,
      lastDecision: track.decisions.at(-1) ?? null,
      limits: aiLimits(),
    }
  }

  /** Reusable preview shape for `bybit_trade` when nothing is sent. */
  function preview(details: Record<string, unknown>) {
    return {
      sent: false,
      env: client.env,
      reason: 'preview only: exchange writes are unavailable until the engine-owned native execution authority is connected',
      ...details,
    }
  }

  return { ctx, tool, engine, paper, settings, runtimeMonitor, client, store, panelCache, instrumentCache, logger, markPrice, instrumentFor, paperMarks, statusOfPaper, watchlist, saveWatchlist, tradableSymbols, aiTrack, aiLimits, aiSummary, preview }
}

export type HostRuntime = ReturnType<typeof createHostRuntime>
