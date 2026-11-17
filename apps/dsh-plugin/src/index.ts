/** DSH Host entry: compose runtime services and atomized tool registrars. */
import { BybitError } from './lib/bybit.js'
import { STRATEGY_SUMMARY } from './lib/strategies.js'
import { createHostRuntime } from './host-runtime.js'
import { registerTools as registerAccountTools } from './host-tools-account.js'
import { registerTools as registerTradeTools } from './host-tools-trade.js'
import { registerTools as registerBacktestTools } from './host-tools-backtest.js'
import { registerTools as registerWatchlistTools } from './host-tools-watchlist.js'
import { registerTools as registerAiTools } from './host-tools-ai.js'
import { registerTools as registerEngineTools } from './host-tools-engine.js'
import { registerPanel } from './host-panel.js'
import type { PluginContext } from './host-runtime.js'

export const name = 'bybit-quant'
export const inject = ['tools', 'systemPrompt', 'credentials']

export function apply(ctx: PluginContext, config: Record<string, unknown> = {}): void {
  const runtime = createHostRuntime(ctx, config)
  registerEngineTools(runtime)
  registerAccountTools(runtime)
  registerTradeTools(runtime)
  registerBacktestTools(runtime)
  registerWatchlistTools(runtime)
  registerAiTools(runtime)
  registerPanel(ctx, runtime)
}

export { BybitError, STRATEGY_SUMMARY }
