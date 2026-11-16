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
import { formatQuantity, normalizeCategory, normalizeSymbol } from './lib/bybit.js'








import { pick, trim, round2 } from './lib/host-config.js'


import type { HostRuntime } from './host-runtime.js'

export function registerTools(runtime: HostRuntime): void {
  const { ctx, tool, settings, client, assertLiveAccount, markPrice, instrumentFor, preview } = runtime

  ctx.tools.register(tool({
    name: 'bybit_trade',
    description:
      'Create, cancel, or close a Bybit order on the configured environment. Testnet requires allowTestnetTrading; '
      + 'Mainnet requires allowLiveTrading. Sending also requires confirm: "LIVE" and dryRun: false. '
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
        if (client.env === 'testnet' && !settings.allowTestnetTrading) {
          throw new Error('Testnet trading is disabled: set allowTestnetTrading: true in the Testnet plugin config')
        }
        if (client.env === 'live' && !settings.allowLiveTrading) {
          throw new Error(
            'Mainnet trading is disabled for this plugin: explicitly set allowLiveTrading: true in the plugin config',
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
        const result = await client.cancelAll({ category, ...(symbol === undefined ? {} : { symbol }), ...(exec.signal === undefined ? {} : { signal: exec.signal }) })
        return { action, sent: true, env: client.env, symbol: symbol ?? 'all', result }
      }

      if (action === 'close') {
        if (!symbol) throw new Error('close needs symbol')
        const positions = await client.positions({ category, symbol, signal: exec.signal })
        if (positions.length === 0) throw new Error(`no open ${symbol} position to close in ${category}`)
        const position = positions[0]
        if (position === undefined) throw new Error(`no open ${symbol} position to close in ${category}`)
        const payload = {
          category,
          symbol,
          side: position.side === 'Buy' ? 'Sell' : 'Buy',
          orderType: 'Market',
          qty: formatQuantity(position.size, (await instrumentFor(category, symbol, exec.signal)).qtyStep),
          reduceOnly: true,
        }
        if (!wantsSend) return preview({ action, env: client.env, ...payload, position })
        await assertLiveAccount({ notionalUsd: Number(payload.qty) * (await markPrice(category, symbol, exec.signal)), ...(exec.signal === undefined ? {} : { signal: exec.signal }) })
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
      const fence = await assertLiveAccount({ notionalUsd: notional, ...(exec.signal === undefined ? {} : { signal: exec.signal }) })
      const result = await client.createOrder({ ...payload, signal: exec.signal })
      return { action, sent: true, env: client.env, ...payload, notionalUsd: round2(notional), equityUsd: fence.equity, equitySharePct: fence.sharePct, result }
    },
  }))

}
