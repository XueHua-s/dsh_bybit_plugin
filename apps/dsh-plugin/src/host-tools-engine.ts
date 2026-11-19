import type { HostRuntime } from './host-runtime.js'

/** Read-only service tools remain separate from account, candles and execution. */
export function registerTools({ ctx, tool, engine }: HostRuntime): void {
  ctx.tools.register(tool({
    name: 'quant_get_engine_status',
    description: 'Read the independent public linear Testnet engine status. Market readiness does not imply account, reconciliation or execution readiness.',
    parameters: { type: 'object', additionalProperties: false, properties: {} },
    concurrent: true,
    async run(args, exec) {
      if (Object.keys(args).length !== 0) return { ok: false, code: 'invalid_arguments' }
      return engine.status(exec.signal)
    },
  }))
  ctx.tools.register(tool({
    name: 'quant_get_market_snapshot',
    description: 'Read one configured public linear Testnet ticker from the independent engine. May be partial with null prices; no candles, account data, execution permission or REST fallback.',
    parameters: {
      type: 'object', additionalProperties: false, required: ['symbol'],
      properties: { symbol: { type: 'string', pattern: '^[A-Z0-9]{2,32}$', minLength: 2, maxLength: 32 } },
    },
    concurrent: true,
    async run(args, exec) {
      if (Object.keys(args).some(key => key !== 'symbol') || typeof args.symbol !== 'string' || !/^[A-Z0-9]{2,32}$/.test(args.symbol)) {
        return { ok: false, code: 'invalid_arguments' }
      }
      return engine.market(args.symbol, exec.signal)
    },
  }))
}
