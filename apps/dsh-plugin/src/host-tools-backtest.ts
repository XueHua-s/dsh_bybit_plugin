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
import { intervalLabel, intervalMs, normalizeCategory, normalizeInterval, normalizeSymbol } from './lib/bybit.js'
import { evaluateStrategy, runBacktest, STRATEGIES } from './lib/strategies.js'
import type { StrategyParams } from './lib/strategies.js'

import { paperBuy, paperReset, paperSell, paperStatus } from './lib/paper.js'



import { pick, optionalParams, clamp, round2, round8, describeWindow } from './lib/host-config.js'

import type { HostRuntime } from './host-runtime.js'

export function registerTools(runtime: HostRuntime): void {
  const { ctx, tool, settings, client, store, markPrice, statusOfPaper } = runtime

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
      const interval = normalizeInterval(typeof args.interval === 'string' ? args.interval : '60')
      const bars = Math.min(Math.max(Math.trunc(Number(args.bars ?? 500)), 60), 1000)
      const feeBps = clamp(Number(args.feeBps), 0, 100, settings.feeBps)
      const slippageBps = clamp(Number(args.slippageBps), 0, 100, 2)
      const candles = await client.klines({ category, symbol, interval, limit: bars, signal: exec.signal })
      if (candles.length < 60) throw new Error(`only ${candles.length} candles returned for ${symbol}; try a longer history or another interval`)

      const params: StrategyParams = optionalParams(args)
      const { targets, detail, summary } = evaluateStrategy(candles, { strategy, params })
      const result = runBacktest(candles, targets, { feeBps, slippageBps, barMs: intervalMs(interval) })
      const lastCandle = candles.at(-1)
      if (lastCandle === undefined) throw new Error('backtest needs candle data')
      const signal = {
        time: new Date(lastCandle.t).toISOString(),
        target: targets.at(-1) === 1 ? 'long' : 'flat',
        close: lastCandle.c,
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
          ...(args.qty === undefined ? {} : { qty: Number(args.qty) }),
          notionalUsd: args.notionalUsd === undefined ? undefined : Number(args.notionalUsd),
          ...(typeof args.note === 'string' ? { note: args.note } : {}),
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
        ...(args.qty === undefined ? {} : { qty: Number(args.qty) }),
        ...(typeof args.note === 'string' ? { note: args.note } : {}),
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

}
