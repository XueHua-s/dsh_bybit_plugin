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
 * Safety: live order tools require `allowLiveTrading: true` in the plugin
 * config, a configured API key pair, an explicit `confirm: 'LIVE'`, and an
 * explicit `dryRun: false`. Every live order is also capped by
 * `maxOrderNotionalUsd`.
 *
 * Tool definitions are plain objects with raw JSON Schema parameters, so the
 * bundle imports nothing from the dsh installation and installs as a
 * dependency-free linked directory.
 */
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import {
  BybitClient, BybitError, formatQuantity, intervalLabel, intervalMs,
  normalizeCategory, normalizeInterval, normalizeSymbol,
} from './lib/bybit.js'
import { evaluateStrategy, runBacktest, STRATEGIES, STRATEGY_SUMMARY } from './lib/strategies.js'
import { createStore, defaultStateDir } from './lib/state.js'
import { paperBuy, paperReset, paperSell, paperStatus, positionKey } from './lib/paper.js'
import { SIGNAL_SOURCES, evaluateSignals } from './lib/signals.js'
import {
  buildBrief, buildSymbolBrief, closePosition, compactContext, createTrack, DECISION_SCHEMA,
  briefHashOf, markedEquity, normalizeDecision, openPosition, recordDecision, riskGate, rollDay, scoreTrack,
  settleTrack,
} from './lib/ai.js'

/** Plugin version reported by the health route. */
const VERSION = '1.0.0'

/** Authenticated exact Fetch route the Web panel polls (`?view=health` for facts). */
const PANEL_PATH = '/api/bybit-quant'

/** Cooperative tool budget in ms. */
const TOOL_TIMEOUT_MS = 20_000

/** Panel market data is reused for this long so a 5s poll stays cheap. */
const PANEL_CACHE_MS = 4_000

/** Output declaration shared by every tool: one formatted JSON text block. */
const TEXT_OUTPUT = {
  schema: { type: 'object', additionalProperties: true },
  render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
}

/** Cordis plugin name used by loader diagnostics. */
export const name = 'bybit-quant'

/** Services the plugin needs; `webServer` is injected separately as optional. */
export const inject = ['tools', 'systemPrompt']

/** Build a registry definition with the shared output rendering. */
function tool(definition) {
  return {
    name: definition.name,
    description: definition.description,
    parameters: definition.parameters,
    output: TEXT_OUTPUT,
    timeoutMs: TOOL_TIMEOUT_MS,
    ...definition.concurrent === true ? { isConcurrencySafe: () => true } : {},
    async execute(args, exec) {
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
export function apply(ctx, config = {}) {
  const settings = resolveSettings(config)
  const client = new BybitClient({
    env: settings.env,
    apiKey: settings.apiKey,
    apiSecret: settings.apiSecret,
    recvWindow: settings.recvWindow,
    timeoutMs: settings.timeoutMs,
  })
  const store = createStore({ file: settings.stateFile, startingBalance: settings.paperBalanceUsd })
  /** Short-lived panel cache keyed by market and interval. */
  const panelCache = new Map()
  /** Instrument metadata cache keyed by category:symbol. */
  const instrumentCache = new Map()
  const logger = ctx.logger?.('bybit-quant')

  logger?.info(
    `loaded v${VERSION}: env=${settings.env}, keys=${client.hasCredentials ? 'yes' : 'no'}, `
    + `liveTrading=${settings.allowLiveTrading ? 'enabled' : 'disabled'}, state=${settings.stateFile}`,
  )

  ctx.systemPrompt.section({
    name: 'tool:bybit-quant',
    order: 620,
    text: 'Bybit market data is live. Prefer quant_paper to act on a view: it is a simulated USDT book, not an exchange balance. '
      + 'bybit_trade only sends a real order when live trading is enabled in the plugin config AND the call passes confirm: "LIVE" '
      + 'AND dryRun: false; without all three it is a preview. Never propose a live order unless the user explicitly asked for one, '
      + 'and always state the environment (demo/testnet/live), side, quantity, and notional value first. '
      + 'quant_backtest is single-asset and long-only, charges fees and slippage, and past performance is not a forecast. '
      + 'For an autonomous decision call quant_brief, then quant_decide once per symbol with confidence, stopPct, horizonHours, '
      + 'thesis, and invalidation; flat is a valid and free decision, and the code-side risk gate refuses anything that risks more '
      + 'than the per-trade budget. After decisions settle, call quant_review and compare the AI track with buy-and-hold; a positive '
      + 'delta over a few dozen decisions is noise, not skill.',
  })

  /** Cached API-key identity: which account it belongs to and what it may do. */
  let keyInfoCache
  async function keyAccount(signal) {
    if (keyInfoCache !== undefined && keyInfoCache.expires > Date.now()) return keyInfoCache.value
    const value = await client.apiKeyInfo({ signal })
    keyInfoCache = { value, expires: Date.now() + 10 * 60_000 }
    return value
  }

  /**
   * Every live order passes this second fence: a main-account key needs
   * `allowMainAccount: true`, and no single order may exceed the configured share
   * of the account's equity.
   * @param {{ notionalUsd: number, signal?: AbortSignal }} input
   */
  async function assertLiveAccount({ notionalUsd, signal }) {
    const keyInfo = await keyAccount(signal)
    if (!keyInfo.isSubAccount && !settings.allowMainAccount) {
      throw new Error(
        'this API key belongs to the main account (inviterID is empty). Trading the whole balance needs '
        + 'allowMainAccount: true in addition to allowLiveTrading, or use a key bound to a sub-account',
      )
    }
    const wallet = await client.walletBalance({ signal })
    const equity = wallet.totalEquityUsd > 0 ? wallet.totalEquityUsd : wallet.availableUsd
    if (equity <= 0) throw new Error('the account reports no equity; refusing to place a live order')
    const sharePct = (notionalUsd / equity) * 100
    if (sharePct > settings.maxOrderNotionalPctOfEquity) {
      throw new Error(
        `this order would be ${round2(sharePct)}% of account equity (${round2(equity)} USDT); `
        + `the configured ceiling is ${settings.maxOrderNotionalPctOfEquity}%`,
      )
    }
    return { keyInfo, equity, sharePct: round2(sharePct) }
  }

  /** Resolve one mark price for a symbol. */
  async function markPrice(category, symbol, signal) {
    const ticker = await client.ticker({ category, symbol, signal })
    return ticker.last
  }

  /** Cached instrument metadata (quantity step, minimums). */
  async function instrumentFor(category, symbol, signal) {
    const key = `${category}:${symbol}`
    const cached = instrumentCache.get(key)
    if (cached !== undefined && cached.expires > Date.now()) return cached.value
    const value = await client.instrument({ category, symbol, signal })
    instrumentCache.set(key, { value, expires: Date.now() + 10 * 60_000 })
    return value
  }

  /** Marks for every open paper position, best effort. */
  async function paperMarks() {
    const positions = Object.values(store.get().paper.positions)
    if (positions.length === 0) return {}
    const results = await Promise.allSettled(
      positions.map(position => client.ticker({ category: position.category, symbol: position.symbol })),
    )
    /** @type {Record<string, number>} */
    const marks = {}
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
  function saveWatchlist(symbols) {
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
  function aiTrack() {
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
  function aiSummary(marks) {
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

  ctx.tools.register(tool({
    name: 'bybit_market',
    description: 'Read Bybit market data: ticker, candles, order book, funding history, or instrument rules for one symbol.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['kind'],
      properties: {
        kind: {
          type: 'string', enum: ['ticker', 'kline', 'orderbook', 'funding', 'instrument'],
          description: 'What to read.',
        },
        symbol: { type: 'string', description: 'Trading pair such as BTCUSDT; defaults to the plugin default.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'USDT perpetual (linear, default) or spot.' },
        interval: { type: 'string', description: 'Candle interval for kind=kline: 1,3,5,15,30,60,120,240,360,720,D,W,M or 1m/5m/15m/1h/4h/1d.' },
        limit: { type: 'integer', description: 'Row cap: candles 2-1000 (default 60), order book 1-50 (default 10), funding 1-50 (default 8).' },
      },
    },
    concurrent: true,
    async run(args, exec) {
      const kind = pick(args.kind, ['ticker', 'kline', 'orderbook', 'funding', 'instrument'], 'kind')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const symbol = normalizeSymbol(args.symbol, settings.defaultSymbol)
      const limit = Number.isFinite(Number(args.limit)) ? Number(args.limit) : undefined
      if (kind === 'ticker') return { kind, ...(await client.ticker({ category, symbol, signal: exec.signal })) }
      if (kind === 'kline') {
        const interval = normalizeInterval(args.interval)
        const bars = await client.klines({ category, symbol, interval, limit: limit ?? 60, signal: exec.signal })
        return {
          kind,
          symbol,
          category,
          interval: intervalLabel(interval),
          barCount: bars.length,
          window: describeWindow(bars),
          lastBars: bars.slice(-12).map(bar => [new Date(bar.t).toISOString(), bar.o, bar.h, bar.l, bar.c, bar.v]),
        }
      }
      if (kind === 'orderbook') return { kind, ...(await client.orderbook({ category, symbol, limit: limit ?? 10, signal: exec.signal })) }
      if (kind === 'funding') {
        if (category === 'spot') throw new Error('funding only exists for perpetuals (category: linear)')
        return { kind, symbol, history: await client.funding({ category, symbol, limit: limit ?? 8, signal: exec.signal }) }
      }
      return { kind, ...(await client.instrument({ category, symbol, signal: exec.signal })) }
    },
  }))

  ctx.tools.register(tool({
    name: 'bybit_account',
    description: 'Read the configured Bybit account: wallet balance, open positions, or open orders. Needs an API key with read permission.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['view'],
      properties: {
        view: { type: 'string', enum: ['balance', 'positions', 'orders', 'key'], description: 'Which account view to read; key reports the API key\'s account, permissions, and expiry.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Position and order category; defaults to linear.' },
        symbol: { type: 'string', description: 'Restrict positions or orders to one symbol.' },
      },
    },
    concurrent: true,
    async run(args, exec) {
      const view = pick(args.view, ['balance', 'positions', 'orders', 'key'], 'view')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const symbol = args.symbol === undefined ? undefined : normalizeSymbol(args.symbol)
      if (view === 'balance') return { view, env: client.env, ...(await client.walletBalance({ signal: exec.signal })) }
      if (view === 'key') return { view, env: client.env, ...(await client.apiKeyInfo({ signal: exec.signal })) }
      if (view === 'positions') {
        return { view, env: client.env, category, symbol: symbol ?? 'all', positions: await client.positions({ category, symbol, signal: exec.signal }) }
      }
      return { view, env: client.env, category, symbol: symbol ?? 'all', orders: await client.openOrders({ category, symbol, signal: exec.signal }) }
    },
  }))

  ctx.tools.register(tool({
    name: 'bybit_trade',
    description:
      'Create, cancel, or close a real Bybit order. Disabled unless the plugin config enables live trading; '
      + 'sends only with confirm: "LIVE" and dryRun: false, and refuses any order above maxOrderNotionalUsd. '
      + 'Without both it returns the exact preview it would send.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['action'],
      properties: {
        action: { type: 'string', enum: ['create', 'cancel', 'cancel_all', 'close'], description: 'create places an order, cancel cancels one by id, cancel_all cancels a symbol or category, close market-closes the open position.' },
        symbol: { type: 'string', description: 'Trading pair; required except for cancel_all.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
        side: { type: 'string', enum: ['buy', 'sell'], description: 'Order side for action=create.' },
        orderType: { type: 'string', enum: ['Market', 'Limit'], description: 'Order type for action=create; defaults to Market.' },
        qty: { type: 'number', description: 'Base-asset quantity for action=create; rounded down to the instrument step.' },
        price: { type: 'number', description: 'Limit price; required for orderType=Limit.' },
        orderId: { type: 'string', description: 'Order id for action=cancel.' },
        reduceOnly: { type: 'boolean', description: 'Mark a linear order reduce-only.' },
        dryRun: { type: 'boolean', description: 'Defaults to true: validate and return the preview without sending.' },
        confirm: { type: 'string', description: 'Must be exactly "LIVE" to send a real order.' },
      },
    },
    async run(args, exec) {
      const action = pick(args.action, ['create', 'cancel', 'cancel_all', 'close'], 'action')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const symbol = args.symbol === undefined ? undefined : normalizeSymbol(args.symbol)
      const wantsSend = args.dryRun === false && args.confirm === 'LIVE'

      if (wantsSend) {
        if (!settings.allowLiveTrading) {
          throw new Error(
            'live trading is disabled for this plugin: set allowLiveTrading: true in the Bybit quant plugin config, '
            + 'prefer env: demo or testnet while learning, and restart the plugin row',
          )
        }
        if (!client.hasCredentials) {
          throw new Error('live trading needs a Bybit API key: set BYBIT_API_KEY and BYBIT_API_SECRET, or the plugin config apiKey/apiSecret fields')
        }
      }

      if (action === 'cancel') {
        if (!symbol || !args.orderId) throw new Error('cancel needs symbol and orderId')
        if (!wantsSend) return preview({ action, env: client.env, category, symbol, orderId: args.orderId })
        const result = await client.cancelOrder({ category, symbol, orderId: String(args.orderId), signal: exec.signal })
        return { action, sent: true, env: client.env, symbol, result }
      }

      if (action === 'cancel_all') {
        if (!wantsSend) return preview({ action, env: client.env, category, symbol: symbol ?? 'every symbol in the category' })
        const result = await client.cancelAll({ category, symbol, signal: exec.signal })
        return { action, sent: true, env: client.env, symbol: symbol ?? 'all', result }
      }

      if (action === 'close') {
        if (!symbol) throw new Error('close needs symbol')
        const positions = await client.positions({ category, symbol, signal: exec.signal })
        if (positions.length === 0) throw new Error(`no open ${symbol} position to close in ${category}`)
        const position = positions[0]
        const payload = {
          category,
          symbol,
          side: position.side === 'Buy' ? 'Sell' : 'Buy',
          orderType: 'Market',
          qty: formatQuantity(position.size, (await instrumentFor(category, symbol, exec.signal)).qtyStep),
          reduceOnly: true,
        }
        if (!wantsSend) return preview({ action, env: client.env, ...payload, position })
        await assertLiveAccount({ notionalUsd: Number(payload.qty) * (await markPrice(category, symbol, exec.signal)), signal: exec.signal })
        const result = await client.createOrder({ ...payload, signal: exec.signal })
        return { action, sent: true, env: client.env, ...payload, result }
      }

      if (!symbol) throw new Error('create needs symbol')
      if (args.side !== 'buy' && args.side !== 'sell') throw new Error('create needs side: buy or sell')
      const side = args.side
      const orderType = args.orderType === 'Limit' ? 'Limit' : 'Market'
      const qty = Number(args.qty)
      if (!Number.isFinite(qty) || qty <= 0) throw new Error('create needs a positive qty')
      if (orderType === 'Limit' && !(Number(args.price) > 0)) throw new Error('a Limit order needs a positive price')

      const instrument = await instrumentFor(category, symbol, exec.signal)
      const quantity = formatQuantity(qty, instrument.qtyStep)
      if (Number(quantity) <= 0) throw new Error(`qty ${qty} is below the ${symbol} step ${instrument.qtyStep}`)
      const referencePrice = orderType === 'Limit' ? Number(args.price) : await markPrice(category, symbol, exec.signal)
      const notional = Number(quantity) * referencePrice
      if (instrument.minOrderQty > 0 && Number(quantity) < instrument.minOrderQty) {
        throw new Error(`qty ${quantity} is below the ${symbol} minimum ${instrument.minOrderQty}`)
      }
      if (instrument.minNotionalUsd !== undefined && notional < instrument.minNotionalUsd) {
        throw new Error(`order notional ${round2(notional)} USDT is below the ${symbol} minimum ${instrument.minNotionalUsd} USDT`)
      }
      if (notional > settings.maxOrderNotionalUsd) {
        throw new Error(
          `order notional ${round2(notional)} USDT exceeds maxOrderNotionalUsd ${settings.maxOrderNotionalUsd}; `
          + 'lower qty or raise the cap deliberately in the plugin config',
        )
      }

      const payload = {
        category,
        symbol,
        side: side === 'buy' ? 'Buy' : 'Sell',
        orderType,
        qty: quantity,
        ...orderType === 'Limit' ? { price: trim(Number(args.price)), timeInForce: 'GTC' } : {},
        ...args.reduceOnly === true ? { reduceOnly: true } : {},
      }
      if (!wantsSend) return preview({ action, env: client.env, ...payload, notionalUsd: round2(notional), markPrice: round2(referencePrice) })
      const fence = await assertLiveAccount({ notionalUsd: notional, signal: exec.signal })
      const result = await client.createOrder({ ...payload, signal: exec.signal })
      return { action, sent: true, env: client.env, ...payload, notionalUsd: round2(notional), equityUsd: fence.equity, equitySharePct: fence.sharePct, result }
    },
  }))

  ctx.tools.register(tool({
    name: 'quant_backtest',
    description:
      'Backtest a long-only strategy on Bybit candles and return metrics plus the strategy\'s current signal. '
      + 'Charges fees and slippage on both sides; single asset, no leverage, no shorting.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['strategy'],
      properties: {
        strategy: { type: 'string', enum: STRATEGIES, description: 'ma_cross, rsi_reversion, or breakout.' },
        symbol: { type: 'string', description: 'Trading pair; defaults to the plugin default.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
        interval: { type: 'string', description: 'Candle interval, e.g. 60 (1h), 240 (4h), D (1d). Defaults to 60.' },
        bars: { type: 'integer', description: 'Candles to load, 60-1000; defaults to 500.' },
        feeBps: { type: 'number', description: 'Fee per side in basis points; defaults to the plugin setting (6).' },
        slippageBps: { type: 'number', description: 'Slippage per side in basis points; defaults to 2.' },
        fast: { type: 'integer', description: 'ma_cross fast SMA length; defaults to 20.' },
        slow: { type: 'integer', description: 'ma_cross slow SMA length; defaults to 50.' },
        period: { type: 'integer', description: 'rsi_reversion RSI length; defaults to 14.' },
        entry: { type: 'number', description: 'rsi_reversion entry level; defaults to 30.' },
        exit: { type: 'number', description: 'rsi_reversion exit level; defaults to 70.' },
        lookback: { type: 'integer', description: 'breakout lookback bars; defaults to 20.' },
      },
    },
    concurrent: true,
    async run(args, exec) {
      const strategy = pick(args.strategy, STRATEGIES, 'strategy')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const symbol = normalizeSymbol(args.symbol, settings.defaultSymbol)
      const interval = normalizeInterval(args.interval ?? '60')
      const bars = Math.min(Math.max(Math.trunc(Number(args.bars ?? 500)), 60), 1000)
      const feeBps = clamp(Number(args.feeBps), 0, 100, settings.feeBps)
      const slippageBps = clamp(Number(args.slippageBps), 0, 100, 2)
      const candles = await client.klines({ category, symbol, interval, limit: bars, signal: exec.signal })
      if (candles.length < 60) throw new Error(`only ${candles.length} candles returned for ${symbol}; try a longer history or another interval`)

      const params = { fast: args.fast, slow: args.slow, period: args.period, entry: args.entry, exit: args.exit, lookback: args.lookback }
      const { targets, detail, summary } = evaluateStrategy(candles, { strategy, params })
      const result = runBacktest(candles, targets, { feeBps, slippageBps, barMs: intervalMs(interval) })
      const signal = {
        time: new Date(candles.at(-1).t).toISOString(),
        target: targets.at(-1) === 1 ? 'long' : 'flat',
        close: candles.at(-1).c,
        detail,
      }
      store.mutate((state) => {
        state.lastBacktest = {
          time: Date.now(),
          strategy,
          summary,
          symbol,
          category,
          interval: intervalLabel(interval),
          params,
          metrics: result.metrics,
          openPosition: result.openPosition,
          trades: result.trades,
          curve: result.curve,
        }
        state.lastSignal = { ...signal, strategy, summary, symbol, category, interval: intervalLabel(interval) }
        return null
      })

      return {
        strategy,
        summary,
        symbol,
        category,
        interval: intervalLabel(interval),
        feeBps,
        slippageBps,
        dataWindow: describeWindow(candles),
        metrics: result.metrics,
        openPosition: result.openPosition,
        recentTrades: result.trades,
        signal,
        note: 'Long-only, single asset, full notional per trade. Metrics are historical and do not predict future returns.',
      }
    },
  }))

  ctx.tools.register(tool({
    name: 'quant_paper',
    description:
      'Read or change the simulated USDT book: buy or sell at the live Bybit mark, or reset to the starting balance. '
      + 'This never touches the exchange; use bybit_trade for real orders.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['action'],
      properties: {
        action: { type: 'string', enum: ['status', 'buy', 'sell', 'reset'], description: 'status shows the book, buy/sell fill at the live mark, reset restores the starting cash.' },
        symbol: { type: 'string', description: 'Trading pair for buy and sell.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
        qty: { type: 'number', description: 'Base-asset quantity; omit to size with notionalUsd.' },
        notionalUsd: { type: 'number', description: 'USDT amount to spend when qty is omitted (buy only).' },
        note: { type: 'string', description: 'Optional note stored with the trade.' },
      },
    },
    async run(args, exec) {
      const action = pick(args.action, ['status', 'buy', 'sell', 'reset'], 'action')
      if (action === 'status') return { action, env: client.env, book: await statusOfPaper() }
      if (action === 'reset') {
        const balance = store.mutate(state => paperReset(state, settings.paperBalanceUsd))
        return { action, book: paperStatus(store.get(), {}), note: `starting balance restored to ${balance} USDT` }
      }

      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const symbol = normalizeSymbol(args.symbol, settings.defaultSymbol)
      const price = await markPrice(category, symbol, exec.signal)
      if (action === 'buy') {
        const fill = store.mutate(state => paperBuy({
          state,
          category,
          symbol,
          price,
          qty: args.qty === undefined ? undefined : Number(args.qty),
          notionalUsd: args.notionalUsd === undefined ? undefined : Number(args.notionalUsd),
          note: args.note,
        }))
        return {
          action,
          filled: { symbol, category, qty: round8(fill.quantity), price: round2(price), notionalUsd: round2(fill.cost), feeUsd: round2(fill.fee) },
          book: paperStatus(store.get(), { [fill.key]: price }),
        }
      }

      const fill = store.mutate(state => paperSell({
        state,
        category,
        symbol,
        price,
        qty: args.qty === undefined ? undefined : Number(args.qty),
        note: args.note,
      }))
      return {
        action,
        filled: {
          symbol,
          category,
          qty: round8(fill.quantity),
          price: round2(price),
          proceedsUsd: round2(fill.proceeds),
          feeUsd: round2(fill.fee),
          realizedPnlUsd: round2(fill.realizedPnlUsd),
        },
        book: paperStatus(store.get(), {}),
      }
    },
  }))

  ctx.tools.register(tool({
    name: 'bybit_instruments',
    description:
      'Discover what Bybit actually lists instead of assuming a symbol: read the instrument catalogue for spot or USDT perpetuals, '
      + 'filter by quote coin, contract type, or a symbol substring, and get the trading rules (quantity step, minimum notional, leverage).',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        category: { type: 'string', enum: ['spot', 'linear'], description: 'spot or linear (USDT/USDC perpetuals); defaults to linear.' },
        quote: { type: 'string', description: 'Keep only this quote coin, e.g. USDT, USDC, or BTC.' },
        contractType: { type: 'string', description: 'Keep only this contract type, e.g. LinearPerpetual or LinearFutures.' },
        search: { type: 'string', description: 'Case-insensitive substring of the symbol, e.g. SOL or AAPL.' },
        status: { type: 'string', description: 'Keep only this status, e.g. Trading; defaults to every status.' },
        limit: { type: 'integer', description: 'Return at most this many rows, 1-200; defaults to 30.' },
      },
    },
    concurrent: true,
    async run(args, exec) {
      const category = normalizeCategory(args.category ?? 'linear')
      const limit = Math.min(Math.max(Math.trunc(Number(args.limit ?? 30)), 1), 200)
      const catalogue = await client.instruments({ category, signal: exec.signal })
      const quote = args.quote === undefined ? undefined : String(args.quote).toUpperCase()
      const contractType = args.contractType === undefined ? undefined : String(args.contractType)
      const search = args.search === undefined ? '' : String(args.search).toUpperCase()
      const status = args.status === undefined ? undefined : String(args.status)
      const matches = catalogue.filter(row =>
        row.status === 'Trading'
        && (status === undefined || row.status === status)
        && (quote === undefined || row.quoteCoin === quote)
        && (contractType === undefined || row.contractType === contractType)
        && (search === '' || String(row.symbol).includes(search)))
      const quotes = [...new Set(catalogue.map(row => row.quoteCoin))].sort()
      const contractTypes = [...new Set(catalogue.map(row => row.contractType).filter(Boolean))].sort()
      return {
        category,
        total: catalogue.length,
        matched: matches.length,
        returned: Math.min(matches.length, limit),
        quotes,
        contractTypes,
        instruments: matches.slice(0, limit).map(row => ({
          symbol: row.symbol,
          quote: row.quoteCoin,
          contractType: row.contractType,
          qtyStep: row.qtyStep,
          minNotionalUsd: row.minNotionalUsd ?? null,
          tickSize: row.tickSize,
          maxLeverage: row.maxLeverage ?? null,
        })),
        note: matches.length > limit
          ? `showing the first ${limit} of ${matches.length} matches; narrow with search, quote, or contractType`
          : 'the watchlist verifies every symbol against this same catalogue before storing it',
      }
    },
  }))

  ctx.tools.register(tool({
    name: 'quant_watchlist',
    description:
      'List or change the symbols the AI track follows. The list starts from the plugin config and belongs to the user: '
      + 'set/add/remove any Bybit pair, and every name is verified against the exchange before it is stored.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['action'],
      properties: {
        action: { type: 'string', enum: ['list', 'set', 'add', 'remove'], description: 'list reads the watchlist, set replaces it, add/remove changes one symbol.' },
        symbols: { type: 'array', items: { type: 'string' }, description: 'Symbols for set (1-6 entries).' },
        symbol: { type: 'string', description: 'Symbol for add or remove.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Category used to verify the symbol; defaults to linear.' },
      },
    },
    async run(args, exec) {
      const action = pick(args.action, ['list', 'set', 'add', 'remove'], 'action')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      if (action === 'list') {
        const stored = Array.isArray(store.get().watchlist) ? store.get().watchlist : null
        return {
          action,
          symbols: watchlist(),
          source: stored === null || stored.length === 0 ? 'plugin config default' : 'user list',
          note: 'quant_brief and quant_signals cover the first 4 symbols; quant_decide accepts any of them.',
        }
      }

      const verify = async (symbol) => {
        normalizeSymbol(symbol)
        await client.instrument({ category, symbol, signal: exec.signal })
        return symbol
      }

      if (action === 'set') {
        const input = Array.isArray(args.symbols) ? args.symbols : []
        if (input.length === 0) throw new Error('set needs at least one symbol')
        if (input.length > 6) throw new Error('keep the watchlist at six symbols or fewer')
        const symbols = []
        for (const item of input) {
          const symbol = normalizeSymbol(item)
          if (!symbols.includes(symbol)) symbols.push(symbol)
        }
        for (const symbol of symbols) await verify(symbol)
        saveWatchlist(symbols)
        return { action, symbols: watchlist(), verified: symbols }
      }

      if (args.symbol === undefined) throw new Error(`${action} needs symbol`)
      const symbol = normalizeSymbol(args.symbol)
      if (action === 'add') {
        const current = watchlist()
        if (current.includes(symbol)) return { action, symbols: current, note: `${symbol} is already on the watchlist` }
        if (current.length >= 6) throw new Error('the watchlist already holds six symbols; remove one first')
        await verify(symbol)
        saveWatchlist([...current, symbol])
        return { action, symbols: watchlist(), verified: symbol }
      }

      const current = watchlist()
      const next = current.filter(item => item !== symbol)
      if (next.length === current.length) throw new Error(`${symbol} is not on the watchlist`)
      saveWatchlist(next)
      return { action, symbols: watchlist(), removed: symbol, note: next.length === 0 ? 'the plugin config default applies again' : undefined }
    },
  }))

  ctx.tools.register(tool({
    name: 'quant_signals',
    description:
      'Evaluate the curated signal library (Supertrend, Squeeze Momentum, Ichimoku, Donchian, ADX) on one or more symbols '
      + 'and timeframes, and return each signal with a weighted consensus. Objective inputs for a decision, not a verdict.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        symbols: { type: 'array', items: { type: 'string' }, description: 'Symbols to evaluate, up to 4; defaults to the watchlist.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
        timeframes: { type: 'array', items: { type: 'string' }, description: 'Intervals such as 240, 60, D; defaults to the configured brief timeframes.' },
        bars: { type: 'integer', description: 'Candles per timeframe, 120-500; defaults to 300.' },
      },
    },
    concurrent: true,
    async run(args, exec) {
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const symbols = Array.isArray(args.symbols) && args.symbols.length > 0
        ? args.symbols.slice(0, 4).map(item => normalizeSymbol(item))
        : watchlist().slice(0, 4)
      const timeframes = Array.isArray(args.timeframes) && args.timeframes.length > 0
        ? args.timeframes.slice(0, 3).map(item => normalizeInterval(item))
        : settings.aiTimeframes.slice(0, 2)
      const bars = Math.min(Math.max(Math.trunc(Number(args.bars ?? 300)), 120), 500)
      const results = []
      for (const symbol of symbols) {
        const frames = []
        for (const interval of timeframes) {
          const candles = await client.klines({ category, symbol, interval, limit: bars, signal: exec.signal })
          if (candles.length < 80) {
            frames.push({ interval: intervalLabel(interval), error: `only ${candles.length} candles` })
            continue
          }
          const evaluated = evaluateSignals(candles)
          frames.push({
            interval: intervalLabel(interval),
            bias: evaluated.bias,
            score: evaluated.score,
            notes: evaluated.notes,
            supertrend: evaluated.signals.supertrend,
            squeeze: evaluated.signals.squeeze,
            ichimoku: evaluated.signals.ichimoku === null ? null : { state: evaluated.signals.ichimoku.state, tkCross: evaluated.signals.ichimoku.tkCross },
            donchian: evaluated.signals.donchian,
            adx: evaluated.signals.adx,
          })
        }
        const scored = frames.filter(frame => typeof frame.score === 'number')
        results.push({
          symbol,
          category,
          frames,
          consensus: scored.length === 0
            ? null
            : round2(scored.reduce((sum, frame) => sum + frame.score, 0) / scored.length),
        })
      }
      return {
        sources: SIGNAL_SOURCES,
        timeframes: timeframes.map(intervalLabel),
        symbols: results,
        note: 'Weighted consensus: Supertrend 0.30, Ichimoku 0.25, Donchian 0.15, Squeeze momentum 0.15, ADX 0.15. |score| >= 0.3 is a directional bias; otherwise flat.',
      }
    },
  }))

  ctx.tools.register(tool({
    name: 'quant_brief',
    description:
      'Build the AI decision brief: multi-timeframe trend and volatility for each symbol, funding, order-book imbalance, '
      + 'and the risk limits a decision must respect. Read this, then call quant_decide once per symbol you trade.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        symbols: { type: 'array', items: { type: 'string' }, description: 'Symbols to cover, up to 4; defaults to the configured AI symbols.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
      },
    },
    async run(args, exec) {
      if (!settings.aiEnabled) throw new Error('the AI track is disabled (aiEnabled: false)')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const symbols = Array.isArray(args.symbols) && args.symbols.length > 0
        ? args.symbols.slice(0, 4).map(item => normalizeSymbol(item))
        : watchlist().slice(0, 4)
      const brief = await buildBrief({
        client, symbols, category, timeframes: settings.aiTimeframes, signal: exec.signal, limits: aiLimits(),
      })
      const track = aiTrack()
      return {
        brief,
        decisionSchema: DECISION_SCHEMA,
        track: {
          equityUsd: markedEquity(track, {}).equity,
          openPositions: Object.keys(track.positions),
          decisions: track.decisions.length,
        },
        next: 'Call quant_decide once per symbol. Flat is a valid decision; size so a stop hit costs no more than the per-trade risk budget.',
      }
    },
  }))

  ctx.tools.register(tool({
    name: 'quant_decide',
    description:
      'Record and act on one AI decision. The risk gate checks per-trade risk, position cap, open positions, daily loss and drawdown; '
      + 'an accepted directional decision opens a simulated position on the AI track with the stop and horizon you declare, '
      + 'a flat decision closes the symbol\'s position, and a rejected decision is journaled without a fill.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['symbol', 'action', 'confidence', 'thesis', 'invalidation', 'horizonHours'],
      properties: {
        symbol: { type: 'string', description: 'One of the brief symbols.' },
        action: { type: 'string', enum: ['long', 'short', 'flat'], description: 'Directional view or no trade.' },
        sizePct: { type: 'number', description: 'Percent of AI equity used as notional, 1-100; ignored for flat.' },
        confidence: { type: 'number', description: 'Probability this decision makes money, 0-1. Used for calibration scoring.' },
        stopPct: { type: 'number', description: 'Stop distance from entry in percent, 0.2-20.' },
        takePct: { type: 'number', description: 'Take-profit distance in percent, 0-50; 0 means no take-profit.' },
        horizonHours: { type: 'integer', description: 'Hours the thesis stays valid, 1-240; the position closes at market when it expires.' },
        thesis: { type: 'string', description: 'One or two sentences a reviewer could falsify.' },
        invalidation: { type: 'string', description: 'The observable event that proves the thesis wrong.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
      },
    },
    async run(args, exec) {
      if (!settings.aiEnabled) throw new Error('the AI track is disabled (aiEnabled: false)')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const track = aiTrack()
      const now = Date.now()
      const decision = normalizeDecision({ ...args, symbol: normalizeSymbol(args.symbol) }, { symbols: tradableSymbols() })

      // Settle what is already open before taking a new view.
      const openSymbols = Object.keys(track.positions)
      const marks = {}
      const barsBySymbol = {}
      for (const symbol of new Set([...openSymbols, decision.symbol])) {
        const ticker = await client.ticker({ category, symbol, signal: exec.signal })
        marks[symbol] = ticker.last
        if (openSymbols.includes(symbol)) {
          barsBySymbol[symbol] = await client.klines({ category, symbol, interval: '60', limit: 500, signal: exec.signal })
        }
      }
      const settled = settleTrack({ track, barsBySymbol, marks, now, feeBps: settings.aiFeeBps })

      const price = marks[decision.symbol]
      const gate = riskGate({ decision, track, price, cfg: settings, now })
      const brief = await buildSymbolBrief({ client, symbol: decision.symbol, category, timeframes: settings.aiTimeframes, signal: exec.signal })
      const status = decision.action === 'flat' ? 'flat' : gate.allowed ? 'open' : 'rejected'
      const entry = recordDecision(track, decision, {
        price,
        now,
        briefHash: briefHashOf(brief),
        context: compactContext({ at: brief.at, symbols: [brief] }),
        gate,
        status,
      })
      let position = null
      let closed = null
      if (status === 'open') {
        position = openPosition({ track, decision: entry, price, now, feeBps: settings.aiFeeBps })
      } else if (status === 'flat') {
        closed = closePosition({ track, symbol: decision.symbol, price, reason: 'model-flat', now, feeBps: settings.aiFeeBps })
      }
      store.mutate(() => null)

      return {
        accepted: status === 'open' || status === 'flat',
        status,
        decision: {
          id: entry.id,
          symbol: entry.symbol,
          action: entry.action,
          sizePct: entry.sizePct,
          stopPct: entry.stopPct,
          takePct: entry.takePct,
          horizonHours: entry.horizonHours,
          confidence: entry.confidence,
          thesis: entry.thesis,
          invalidation: entry.invalidation,
        },
        price,
        gate: { allowed: gate.allowed, checks: gate.checks, reasons: gate.reasons },
        position,
        closed,
        settled,
        track: markedEquity(track, marks),
        limits: aiLimits(),
        note: status === 'rejected'
          ? 'The risk gate refused this decision and it was journaled without a fill. Reduce sizePct or tighten stopPct, or decide flat.'
          : 'The decision is journaled with its brief hash, thesis, and invalidation; quant_review scores it later.',
      }
    },
  }))

  ctx.tools.register(tool({
    name: 'quant_review',
    description:
      'Score the AI track: hit rate, expectancy, average R, confidence calibration (Brier), max drawdown, recent and worst '
      + 'decisions with their results, and a buy-and-hold baseline over the same window. Use it to decide whether the process is working.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
        decisions: { type: 'integer', description: 'How many recent decisions to include, 1-15; defaults to 6.' },
      },
    },
    async run(args, exec) {
      if (!settings.aiEnabled) throw new Error('the AI track is disabled (aiEnabled: false)')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const track = aiTrack()
      const now = Date.now()
      const marks = {}
      const barsBySymbol = {}
      for (const symbol of Object.keys(track.positions)) {
        const ticker = await client.ticker({ category, symbol, signal: exec.signal })
        marks[symbol] = ticker.last
        barsBySymbol[symbol] = await client.klines({ category, symbol, interval: '60', limit: 500, signal: exec.signal })
      }
      const settled = settleTrack({ track, barsBySymbol, marks, now, feeBps: settings.aiFeeBps })
      const scorecard = scoreTrack({ track, marks })
      const limit = Math.min(Math.max(Math.trunc(Number(args.decisions ?? 6)), 1), 15)
      const recent = track.decisions.slice(-limit).toReversed().map(compactDecision)
      const worst = track.decisions
        .filter(entry => entry.status === 'closed' && entry.result !== null && entry.result.pnlUsd < 0)
        .sort((left, right) => left.result.pnlUsd - right.result.pnlUsd)
        .slice(0, 3)
        .map(compactDecision)

      let baseline = null
      const reference = watchlist()[0] ?? settings.aiSymbols[0]
      if (reference !== undefined) {
        const bars = await client.klines({ category, symbol: reference, interval: '60', limit: 1000, signal: exec.signal })
        const window = bars.filter(bar => bar.t >= track.createdAt)
        if (window.length >= 2) {
          baseline = {
            symbol: reference,
            from: new Date(window[0].t).toISOString(),
            bars: window.length,
            buyHoldPct: round2(((window.at(-1).c - window[0].c) / window[0].c) * 100),
          }
        }
      }
      store.mutate(() => null)

      return {
        settled,
        scorecard,
        baseline,
        comparison: baseline === null ? null : {
          aiPct: scorecard.book.totalReturnPct,
          buyHoldPct: baseline.buyHoldPct,
          deltaPct: round2(scorecard.book.totalReturnPct - baseline.buyHoldPct),
        },
        recent,
        worst,
        limits: aiLimits(),
        note: 'A positive delta over a few dozen decisions is noise, not skill. Watch the Brier score fall and the per-decision expectancy rise before trusting it.',
      }
    },
  }))

  /** Reusable preview shape for `bybit_trade` when nothing is sent. */
  function preview(details) {
    return {
      sent: false,
      env: client.env,
      reason: settings.allowLiveTrading
        ? 'preview only: pass confirm: "LIVE" and dryRun: false to send'
        : 'preview only: live trading is disabled in the plugin config (allowLiveTrading: false)',
      ...details,
    }
  }

  // The panel reads through the connection bridge's exact Fetch route, so it
  // shares the Web GUI's Host/Origin fence and browser authentication instead
  // of exposing an unauthenticated webserver path.
  ctx.inject(['webServer', 'connection'], (webCtx) => {
    /** Snapshot for the Web panel: market, paper book, last backtest. */
    async function snapshot(request) {
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
        allowLiveTrading: settings.allowLiveTrading,
        maxOrderNotionalUsd: settings.maxOrderNotionalUsd,
        symbol,
        category,
        interval: intervalLabel(interval),
        paper: await statusOfPaper(),
        lastBacktest: store.get().lastBacktest,
        lastSignal: store.get().lastSignal,
        ai: aiSummary({ [symbol]: undefined }),
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
        if (panelCache.size > 24) panelCache.delete(panelCache.keys().next().value)
        return Response.json({ ...base, ...value })
      } catch (error) {
        return Response.json({ ...base, ok: false, error: error instanceof Error ? error.message : String(error) })
      }
    }

    /** Diagnostics the panel's error state and a human can read. */
    function health() {
      return {
        ok: true,
        version: VERSION,
        env: client.env,
        tradingBase: client.tradingBase,
        hasKeys: client.hasCredentials,
        allowLiveTrading: settings.allowLiveTrading,
        allowMainAccount: settings.allowMainAccount,
        maxOrderNotionalUsd: settings.maxOrderNotionalUsd,
        maxOrderNotionalPctOfEquity: settings.maxOrderNotionalPctOfEquity,
        stateFile: store.file,
        credentialsFile: settings.credentialsFile,
        credentialsSource: settings.credentialsSource,
        paperStartingBalanceUsd: settings.paperBalanceUsd,
        tools: [
          'bybit_market', 'bybit_account', 'bybit_trade', 'bybit_instruments', 'quant_backtest', 'quant_paper',
          'quant_watchlist', 'quant_signals', 'quant_brief', 'quant_decide', 'quant_review',
        ],
        ai: { startEquityUsd: settings.aiStartEquity, riskPerTradePct: settings.aiRiskPerTradePct, maxOpenPositions: settings.aiMaxOpenPositions },
      }
    }

    webCtx.effect(() => webCtx.connection.fetch.register({
      path: PANEL_PATH,
      methods: ['GET', 'HEAD'],
      requestBody: 'buffered',
      fetch: (request) => {
        const view = new URL(request.url, 'http://localhost').searchParams.get('view')
        return view === 'health' ? Response.json(health()) : snapshot(request)
      },
    }), 'bybit-quant: panel route')

    logger?.info(`panel route: ${PANEL_PATH}`)
  })
}

/**
 * Normalise the plugin row's config into complete settings.
 * @param {Record<string, unknown>} config
 */
function resolveSettings(config) {
  const env = ['live', 'demo', 'testnet'].includes(config.env) ? config.env : 'demo'
  const credentialsFile = text(config.credentialsFile) || join(defaultStateDir(), 'credentials.json')
  const fromFile = readCredentialsFile(credentialsFile)
  const configKey = text(config.apiKey)
  const envKey = text(process.env.BYBIT_API_KEY)
  const apiKey = configKey || envKey || fromFile.apiKey
  const apiSecret = text(config.apiSecret) || text(process.env.BYBIT_API_SECRET) || fromFile.apiSecret
  const credentialsSource = configKey ? 'plugin config' : envKey ? 'environment' : fromFile.apiKey ? 'credentials file' : 'none'
  return {
    env,
    apiKey,
    apiSecret,
    credentialsFile,
    credentialsSource,
    allowLiveTrading: config.allowLiveTrading === true,
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
function normalizeSymbolList(value) {
  const list = Array.isArray(value)
    ? value.map(item => normalizeSymbol(item)).filter((symbol, index, all) => all.indexOf(symbol) === index).slice(0, 4)
    : []
  return list.length > 0 ? list : ['BTCUSDT', 'ETHUSDT']
}

/** Timeframes the brief covers, primary first. */
function normalizeTimeframes(value) {
  const list = Array.isArray(value) ? value.map(item => normalizeInterval(item)).slice(0, 4) : []
  return list.length > 0 ? list : ['240', '60', 'D']
}

/** Journal entry trimmed for a tool result. */
function compactDecision(entry) {
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
function pick(value, allowed, label) {
  if (typeof value === 'string' && allowed.includes(value)) return value
  throw new Error(`${label} must be one of: ${allowed.join(', ')}`)
}

/**
 * Read an optional key file so credentials never have to sit in the profile patch
 * or in a chat message. Accepts `{ apiKey, apiSecret }` or `{ key, secret }`.
 * @param {string} file
 * @returns {{ apiKey: string, apiSecret: string }}
 */
function readCredentialsFile(file) {
  try {
    if (!existsSync(file)) return { apiKey: '', apiSecret: '' }
    const parsed = JSON.parse(readFileSync(file, 'utf8'))
    return {
      apiKey: text(parsed.apiKey ?? parsed.key),
      apiSecret: text(parsed.apiSecret ?? parsed.secret),
    }
  } catch {
    return { apiKey: '', apiSecret: '' }
  }
}

/** Trimmed string or empty. */
function text(value) {
  return typeof value === 'string' ? value.trim() : ''
}

/** Positive finite number or the fallback. */
function positive(value, fallback) {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : fallback
}

/** Clamp a possibly absent number. */
function clamp(value, min, max, fallback) {
  if (!Number.isFinite(value)) return fallback
  return Math.min(Math.max(value, min), max)
}

/** Compact price text without float noise. */
function trim(value) {
  return Number.isFinite(value) ? String(Number(value.toFixed(8))) : '0'
}

/** Round for display. */
function round2(value) {
  return Math.round(value * 100) / 100
}

/** Round eight decimals for base quantities. */
function round8(value) {
  return Math.round(value * 1e8) / 1e8
}

/** First/last bar facts for a fetched window. */
function describeWindow(bars) {
  if (bars.length === 0) return { bars: 0 }
  const first = bars[0]
  const last = bars.at(-1)
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
function clean(value) {
  if (Array.isArray(value)) return value.map(clean)
  if (value !== null && typeof value === 'object') {
    const out = {}
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
  return value
}

export { BybitError, STRATEGY_SUMMARY }
