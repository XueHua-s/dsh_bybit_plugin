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
 * Account tools are read-only and do not authorize exchange writes.
 *
 * Tool definitions are plain objects with raw JSON Schema parameters, so the
 * bundle imports nothing from the dsh installation and installs as a
 * dependency-free linked directory.
 */
import { intervalLabel, normalizeCategory, normalizeInterval, normalizeSymbol } from './lib/bybit.js'







import { pick, describeWindow } from './lib/host-config.js'


import type { HostRuntime } from './host-runtime.js'

export function registerTools(runtime: HostRuntime): void {
  const { ctx, tool, settings, client } = runtime

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
        const interval = normalizeInterval(typeof args.interval === 'string' ? args.interval : undefined)
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
        return { view, env: client.env, category, symbol: symbol ?? 'all', positions: await client.positions({ category, ...(symbol === undefined ? {} : { symbol }), ...(exec.signal === undefined ? {} : { signal: exec.signal }) }) }
      }
      return { view, env: client.env, category, symbol: symbol ?? 'all', orders: await client.openOrders({ category, ...(symbol === undefined ? {} : { symbol }), ...(exec.signal === undefined ? {} : { signal: exec.signal }) }) }
    },
  }))

}
