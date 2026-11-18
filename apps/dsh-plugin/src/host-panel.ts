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
 * Safety: the panel reports read-only market/account state and the explicit
 * absence of an exchange execution authority.
 *
 * Tool definitions are plain objects with raw JSON Schema parameters, so the
 * bundle imports nothing from the dsh installation and installs as a
 * dependency-free linked directory.
 */
import { intervalLabel, normalizeCategory, normalizeInterval, normalizeSymbol } from './lib/bybit.js'











import type { HostRuntime, PluginContext } from './host-runtime.js'

const VERSION = '1.4.5'
const PANEL_PATH = '/api/bybit-quant'
const PANEL_CACHE_MS = 4_000

export function registerPanel(ctx: PluginContext, runtime: HostRuntime): void {
  const { settings, runtimeMonitor, client, store, panelCache, logger, statusOfPaper, aiSummary } = runtime
  // The panel reads through the connection bridge's exact Fetch route, so it
  // shares the Web GUI's Host/Origin fence and browser authentication instead
  // of exposing an unauthenticated webserver path.
  ctx.inject(['webServer', 'connection'], (webCtx) => {
    /** Snapshot for the Web panel: market, paper book, last backtest. */
    async function snapshot(request: Request): Promise<Response> {
      const url = new URL(request.url, 'http://localhost')
      const category = normalizeCategory(url.searchParams.get('category') ?? settings.defaultCategory)
      const symbol = normalizeSymbol(url.searchParams.get('symbol') ?? settings.defaultSymbol)
      const interval = normalizeInterval(url.searchParams.get('interval') ?? '60')
      const bars = Math.min(Math.max(Math.trunc(Number(url.searchParams.get('bars') ?? 160)), 40), 400)
      const key = `${category}:${symbol}:${interval}:${bars}`
      const cached = panelCache.get(key)
      const base = {
        ok: true,
        version: VERSION,
        env: client.env,
        hasKeys: client.hasCredentials,
        automation: 'conversation_only' as const,
        backgroundLoop: 'not_running' as const,
        executionAuthority: 'unavailable' as const,
        accountReadiness: 'unknown' as const,
        maxOrderNotionalUsd: settings.maxOrderNotionalUsd,
        symbol,
        category,
        interval: intervalLabel(interval),
        paper: await statusOfPaper(),
        lastBacktest: store.get().lastBacktest,
        lastSignal: store.get().lastSignal,
        ai: aiSummary(),
      }
      if (cached !== undefined && cached.expires > Date.now()) return Response.json({ ...base, ...cached.value, cached: true })
      try {
        const [ticker, candles] = await Promise.all([
          client.ticker({ category, symbol, signal: request.signal }),
          client.klines({ category, symbol, interval, limit: bars, signal: request.signal }),
        ])
        const value = {
          ticker,
          klines: candles.map(bar => [bar.t, bar.o, bar.h, bar.l, bar.c, bar.v]),
          updatedAt: Date.now(),
        }
        panelCache.set(key, { value, expires: Date.now() + PANEL_CACHE_MS })
        if (panelCache.size > 24) {
          const oldest = panelCache.keys().next().value
          if (oldest !== undefined) panelCache.delete(oldest)
        }
        return Response.json({ ...base, ...value })
      } catch (error) {
        return Response.json({ ...base, ok: false, error: error instanceof Error ? error.message : String(error) })
      }
    }

    /** Diagnostics the panel's error state and a human can read. */
    async function health(request: Request) {
      return {
        ok: true,
        engine: await runtime.engine.status(request.signal),
        version: VERSION,
        env: client.env,
        tradingBase: client.tradingBase,
        hasKeys: client.hasCredentials,
        automation: 'conversation_only' as const,
        backgroundLoop: 'not_running' as const,
        executionAuthority: 'unavailable' as const,
        accountReadiness: 'unknown' as const,
        maxOrderNotionalUsd: settings.maxOrderNotionalUsd,
        stateFile: store.file,
        credentialsFile: settings.credentialsFile,
        credentialsSource: settings.credentialsSource,
        paperStartingBalanceUsd: settings.paperBalanceUsd,
        tools: [
          'quant_get_engine_status', 'quant_get_market_snapshot', 'bybit_market', 'bybit_account', 'bybit_trade', 'bybit_instruments', 'quant_backtest', 'quant_paper',
          'quant_watchlist', 'quant_signals', 'quant_brief', 'quant_decide', 'quant_review',
        ],
        ai: { startEquityUsd: settings.aiStartEquity, riskPerTradePct: settings.aiRiskPerTradePct, maxOpenPositions: settings.aiMaxOpenPositions },
        runtime: {
          ...runtimeMonitor.snapshot(),
          uptimeSeconds: Math.floor(process.uptime()),
          marketDataLatencyMs: client.metrics.lastRequestLatencyMs,
          lastOrderLatencyMs: null,
          requests: client.metrics.requests,
          failures: client.metrics.failures,
          websocket: { ...runtimeMonitor.snapshot().websocket, note: 'REST polling is active; WebSocket reconnect counters remain zero until a WebSocket adapter is configured.' },
        },
      }
    }

    webCtx.effect(() => webCtx.connection.fetch.register({
      path: PANEL_PATH,
      methods: ['GET', 'HEAD'],
      requestBody: 'buffered',
      fetch: async (request) => {
        const view = new URL(request.url, 'http://localhost').searchParams.get('view')
        if (view === 'engine') {
          const symbol = new URL(request.url).searchParams.get('symbol')
          if (symbol !== null && !/^[A-Z0-9]{2,32}$/.test(symbol)) return Response.json({ ok: false, code: 'invalid_arguments' }, { status: 400 })
          return Response.json(symbol === null ? await runtime.engine.status(request.signal) : await runtime.engine.market(symbol, request.signal))
        }
        return view === 'health' ? Response.json(await health(request)) : snapshot(request)
      },
    }), 'bybit-quant: panel route')

    logger?.info(`panel route: ${PANEL_PATH}`)
  })
}
