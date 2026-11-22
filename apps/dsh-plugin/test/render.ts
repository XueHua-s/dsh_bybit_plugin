/**
 * Render test for the panel: server-renders the real components with real React
 * and a realistic snapshot, so a data-dependent crash (a bad table, a chart
 * division by zero, a missing field) fails here instead of blanking the slot in
 * the browser.
 *
 * React19 is a plugin build/test dependency; missing runtime fails this test.
 * BQ_REACT_MODULES optionally selects a different installed runtime directory.
 * SSR does not run effects: engine and native paper remain honestly unqueried.
 */
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { join } from 'node:path'
import { assertDefined, installBundleLoader, type ClientSnapshot, type LoadedBundle, type PluginContext, type Registration, type ReactRuntime } from './client-fixtures.ts'

const modules = process.env.BQ_REACT_MODULES
const require = createRequire(modules === undefined ? import.meta.url : join(modules, 'noop.js'))
const React = require('react') as ReactRuntime
const { renderToStaticMarkup } = require('react-dom/server') as { renderToStaticMarkup(node: unknown): string }

let loaded: LoadedBundle | undefined
installBundleLoader(bundle => { loaded = bundle })
// The bundle is generated JavaScript and is exercised through its declared test contract.
// @ts-expect-error generated client bundle intentionally has no declaration file
await import('../dist/client.js')

assertDefined(loaded, 'client bundle did not register with the module loader')
const plugin = loaded.factory((specifier) => {
  if (specifier !== 'react') throw new Error(`unexpected module ${specifier}`)
  return React
})

const registrations: Registration[] = []
const context: PluginContext = {
  effect: (factory) => { factory() },
  locale: { register: () => () => {}, bind: () => (key) => key },
  slots: {
    inject: (_key, factory) => factory(),
    register: (options, component) => { registrations.push({ options, component }); return () => {} },
  },
}
plugin.apply(context)

const main = registrations.find(entry => entry.options.name === 'main')
assertDefined(main, 'main panel was not registered')
const Panel = main.component

/** Build the snapshot shape the Host route returns. */
function snapshot({ withPosition = true }: { withPosition?: boolean } = {}): ClientSnapshot['data'] {
  const start = 1_794_000_000_000
  const klines = Array.from({ length: 120 }, (_, index) => {
    const close = 100 + Math.sin(index / 7) * 6 + index * 0.1
    return [start + index * 3_600_000, close - 0.4, close + 0.9, close - 1.1, close, 12.5]
  })
  return {
    ok: true,
    version: '1.0.0',
    env: 'demo',
    hasKeys: false,
    automation: 'conversation_only',
    backgroundLoop: 'disabled',
    executionAuthority: 'unavailable',
    accountReadiness: 'unknown',
    maxOrderNotionalUsd: 200,
    symbol: 'BTCUSDT',
    category: 'linear',
    interval: '1h',
    ticker: {
      symbol: 'BTCUSDT', category: 'linear', last: 64321.5, change24hPct: -1.23, high24h: 65777.6,
      low24h: 64100, volume24h: 61595.4, turnover24h: 3_996_595_651.9, bid: 64321.4, ask: 64321.6,
      markPrice: 64325.1, fundingRate: 0.0025, openInterest: 70490.8, time: start,
    },
    klines,
    paper: {
      currency: 'USDT',
      balanceUsd: 9599.6,
      positionsValueUsd: 400.04,
      equityUsd: 9999.64,
      startingBalanceUsd: 10000,
      totalReturnPct: -0.0,
      realizedPnlUsd: 0,
      unrealizedPnlUsd: 0.04,
      feesPaidUsd: 0.4,
      positions: withPosition
        ? [{
          key: 'linear:ETHUSDT', category: 'linear', symbol: 'ETHUSDT', qty: 0.22280399,
          avgPrice: 1795.299982, markPrice: 1795.48, staleMark: false, valueUsd: 400.04,
          unrealizedPnlUsd: 0.04, unrealizedPnlPct: 0.01,
        }]
        : [],
      recentTrades: withPosition
        ? [{
          time: start, side: 'buy', category: 'linear', symbol: 'ETHUSDT', qty: 0.1114,
          price: 1795.48, feeUsd: 0.2, note: '',
        }]
        : [],
    },
    lastBacktest: {
      time: start, strategy: 'ma_cross', summary: 'long while fast above slow',
      symbol: 'ETHUSDT', category: 'linear', interval: '4h', params: {},
      metrics: {
        bars: 800, finalEquity: 1.0212, totalReturnPct: 2.12, buyHoldReturnPct: 1.26,
        maxDrawdownPct: 19.81, trades: 17, winRatePct: 17.6, avgTradePct: 0.347,
        bestTradePct: 27.938, worstTradePct: -5.141, profitFactor: 1.22, exposurePct: 46.1,
        feeDragPct: 2.24, sharpe: 0.34, from: '2026-07-06T04:00:00.000Z', to: '2026-11-16T08:00:00.000Z',
      },
      openPosition: null,
      trades: [],
      curve: Array.from({ length: 120 }, (_, index) => ({
        t: start + index * 14_400_000,
        e: 1 + Math.sin(index / 9) * 0.02 + index * 0.0002,
      })),
    },
    lastSignal: {
      time: '2026-11-16T08:00:00.000Z', target: 'flat', close: 1794.96,
      detail: { fast: 10, slow: 30, fastSma: 1810.04, slowSma: 1916.14 },
      strategy: 'ma_cross', summary: 'long while fast above slow', symbol: 'ETHUSDT',
      category: 'linear', interval: '4h',
    },
    ai: {
      startEquityUsd: 10000,
      equityUsd: 10099.34,
      totalReturnPct: 0.99,
      maxDrawdownPct: 2.1,
      feesPaidUsd: 1.2,
      openPositions: [{
        symbol: 'BTCUSDT', side: 'long', entryPrice: 64000, markPrice: 64500, qty: 0.0156,
        notionalUsd: 1000, unrealizedPnlUsd: 7.81, unrealizedPct: 0.78, stopPrice: 63360, takePrice: 65280,
        openedAt: start, horizonHours: 4, decisionId: 'd1', entryFeeUsd: 0.6,
      }],
      closed: 3,
      hitRatePct: 66.7,
      avgRMultiple: 0.9,
      brier: 0.21,
      calibration: [{ range: '60-70%', count: 2, avgConfidence: 0.65, hitRate: 0.5 }],
      curve: Array.from({ length: 40 }, (_, index) => ({ t: start + index * 3_600_000, e: 10000 + index * 2.5 })),
      lastDecision: {
        id: 'd1', time: start, symbol: 'BTCUSDT', action: 'long', sizePct: 10, confidence: 0.62,
        stopPct: 1, takePct: 2, horizonHours: 4, status: 'open',
        thesis: 'higher timeframe trend up and funding is mild, buying a small pullback',
        invalidation: 'a 1h close below the prior swing low', result: null,
      },
      limits: { riskPerTradePct: 1, maxOpenPositions: 2, symbols: ['BTCUSDT', 'ETHUSDT'] },
    },
    aiCandidatePool: {
      category: 'linear', status: 'fresh', observedAt: start, eligibleCount: 2,
      candidates: ['XRPUSDT', 'ADAUSDT'],
    },
    updatedAt: start,
  }
}

/** Render the panel with one injected snapshot. */
function render(initial: ClientSnapshot): string {
  return renderToStaticMarkup(React.createElement(Panel, {
    t: testTranslate,
    initial,
  }))
}

function testTranslate(key: string): string {
  return {
    writesUnavailable: 'Exchange writes unavailable',
    systemDetails: 'System and runtime status',
    readinessTitle: 'Operating boundary',
    readinessConversationOnly: 'Conversation-triggered only',
    readinessBackgroundSimulation: 'Background simulated decisions',
    readinessNotRunning: 'Not running',
    readinessLoopDisabled: 'Disabled (default)',
    readinessLoopNotConfigured: 'Agent service not configured',
    readinessLoopEnvironmentRejected: 'Environment rejects background loop',
    readinessLoopStarting: 'Starting Agent',
    readinessLoopRunning: 'AI decision cycle (simulated only)',
    readinessLoopBackoff: 'Backing off after failure',
    readinessLoopBlocked: 'Stopped after repeated failures',
    readinessLoopStopping: 'Stopping',
    readinessLoopIdle: 'Waiting for next cycle',
    readinessLoopCadence: 'Cycle interval',
    readinessLoopEnvironment: 'Loop environment',
    readinessLastCycle: 'Last cycle receipt',
    readinessNoCompletedCycle: 'No completed cycle yet',
    readinessCycleCompleted: 'Cycle completed',
    readinessCycleFailed: 'Cycle failed',
    readinessNoDecisionReceipt: 'No decision write receipt (does not prove abstention)',
    readinessDecisionOpen: 'Simulated position opened',
    readinessDecisionFlat: 'Simulated position closed',
    readinessDecisionRejected: 'Rejected by risk gate and recorded',
    readinessDecisionUncertain: 'Outcome uncertain; background loop stopped',
    readinessEnvironmentTestnet: 'Bybit Testnet',
    readinessEnvironmentInternalPaper: 'Internal paper',
    readinessEnvironmentDemo: 'Bybit Demo (rejected)',
    readinessEnvironmentLive: 'Mainnet (rejected)',
    readinessAuthority: 'Execution authority',
    readinessUnavailable: 'Exchange writes unavailable (executor not implemented)',
    readinessUnknown: 'Unknown',
    readinessHint: 'The background loop is disabled by default. When enabled, it records simulated decisions only and never submits exchange orders. The latest cycle receipt reports whether the simulated journal was written; no receipt is not the same as abstention. Account state, reconciliation, execution, and recovery are incomplete.',
    marketView: 'Market view (display only)',
    symbol: 'Chart symbol',
    category: 'Chart market',
    interval: 'Chart candle interval',
    viewFiltersHint: 'These controls only change displayed market data and candles. They do not affect AI trading decisions. The AI independently chooses whether to trade, the symbol, direction, size, exits, and holding horizon.',
    aiTitle: 'AI simulated decisions',
    aiSub: 'Simulated track only; no exchange orders are submitted',
    aiEquity: 'AI simulated equity',
  }[key] ?? key
}

const populated = render({ data: snapshot(), error: null, at: Date.now() })
assert.ok(populated.includes('bq-root'), 'panel root is missing')
assert.ok(populated.includes('64,321'), 'last price is not rendered')
assert.ok(populated.includes('bq-up') || populated.includes('bq-down'), 'change tone class is missing')
assert.ok(populated.includes('<svg'), 'chart is not rendered')
assert.ok(populated.includes('<polyline'), 'moving averages are not rendered')
assert.ok(populated.includes('bq-table'), 'paper book table is missing')
assert.ok(populated.includes('ETHUSDT'), 'paper position is missing')
assert.ok(populated.includes('ma_cross'), 'backtest strategy is missing')
assert.ok(populated.includes('19.81'), 'max drawdown is missing')
assert.ok(!populated.includes('NaN'), 'markup contains NaN')
assert.ok(!populated.includes('undefined'), 'markup contains undefined')
assert.ok(!populated.includes('Infinity'), 'markup contains Infinity')
assert.ok(populated.includes('AI simulated decisions'), 'AI card title is missing or not labeled as simulated')
assert.ok(populated.includes('higher timeframe trend up'), 'AI thesis is missing')
assert.ok(populated.includes('66.7'), 'AI hit rate is missing')
assert.ok(populated.includes('0.21'), 'AI Brier score is missing')
assert.ok(populated.includes('Quant engine / 量化引擎'), 'engine status card is missing')
assert.ok(populated.includes('Operating boundary'), 'operating boundary card is missing')
assert.ok(populated.includes('Exchange writes unavailable'), 'exchange execution boundary is not visible')
assert.ok(populated.includes('AI simulated decisions'), 'AI track is not labeled as simulated')
assert.ok(populated.includes('Conversation-triggered only'), 'conversation-only automation state is missing')
assert.ok(populated.includes('The background loop is disabled by default.'), 'background loop boundary is missing')
assert.ok(!populated.includes('approval-card'), 'unavailable exchange writes must not look like a missing toggle or setup step')
assert.ok(populated.includes('Linear Testnet'), 'engine environment/category label is missing')
assert.ok(populated.includes('Not checked / 尚未检查'), 'SSR must not invent a completed engine request')
assert.ok(populated.includes('account, reconciliation and execution readiness unknown'), 'unknown execution boundary is missing')
assert.ok(!populated.includes('Unavailable / 无法连接'), 'SSR must not claim the unqueried engine is unavailable')
assert.ok(populated.includes('Native internal paper / 原生内部模拟'), 'native-paper card is missing')
assert.ok(populated.includes('<details class="bq-system-details"><summary>System and runtime status</summary>'), 'runtime diagnostics should be grouped in a collapsed details section')
assert.ok(populated.indexOf('Market view (display only)') < populated.indexOf('Operating boundary'), 'market analytics should precede runtime diagnostics')
assert.ok(populated.includes('Market view (display only)'), 'display-only market filters need a clear heading')
assert.ok(populated.includes('Chart candle interval'), 'chart interval must be distinguished from the AI holding horizon')
assert.ok(populated.includes('The AI independently chooses whether to trade'), 'AI decision ownership must be clear beside display controls')
assert.ok(populated.includes('value="XRPUSDT"') && populated.includes('value="ADAUSDT"'), 'chart suggestions must reflect the fresh AI-discovered candidate set')
assert.ok(!populated.includes('value="DOGEUSDT"'), 'chart suggestions must not invent a fixed starter universe')
assert.ok(populated.includes('Synthetic · no exchange connection'), 'native synthetic identity is missing')
assert.ok(populated.includes('Separate from legacy paper/AI books and Linear Testnet.'), 'native/legacy/Testnet distinction is missing')
assert.ok(populated.includes('source: quant-engine-paper · environment: internal_paper'), 'native-paper source/environment must be explicit')
assert.ok(populated.includes('Status is observation-only'), 'native-paper status must be explicitly read-only')
assert.ok(!populated.includes('Start paper / 启动模拟'), 'dashboard must not expose Start')
assert.ok(!populated.includes('Stop paper / 停止模拟'), 'dashboard must not expose Stop')
assert.ok(!populated.includes('Session / 会话:'), 'SSR must not invent native session state')

const completedCycle = render({
  data: {
    ...snapshot(),
    automation: 'background_simulated_decisions',
    backgroundLoop: 'idle',
    backgroundLoopEnvironment: 'testnet',
    backgroundLoopIntervalMs: 60_000,
    backgroundLoopLastRun: {
      outcome: 'completed', decisionsRecorded: 1, latestDecisionId: 'd1',
      latestDecisionStatus: 'open', completedAt: Date.now(),
    },
  },
  error: null,
  at: Date.now(),
})
assert.ok(completedCycle.includes('Last cycle receipt'), 'background cycle receipt needs a clear label')
assert.ok(completedCycle.includes('Cycle completed · 1 · Simulated position opened'), 'persisted simulated decision status is not visible')
assert.ok(completedCycle.includes('no receipt is not the same as abstention'), 'cycle hint must distinguish abstention from a missing receipt')

const noDecisionReceipt = render({
  data: {
    ...snapshot(),
    backgroundLoopLastRun: {
      outcome: 'completed', decisionsRecorded: 0, latestDecisionId: null,
      latestDecisionStatus: null, completedAt: Date.now(),
    },
  },
  error: null,
  at: Date.now(),
})
assert.ok(noDecisionReceipt.includes('No decision write receipt (does not prove abstention)'), 'empty cycle must not be presented as an explicit abstention')

const empty = render({ data: { ...snapshot({ withPosition: false }), klines: [], lastBacktest: null, lastSignal: null, ai: null }, error: null, at: 0 })
assert.ok(empty.includes('noPositions'), 'empty paper book is not reported')
assert.ok(empty.includes('noBacktest'), 'missing backtest is not reported')
assert.ok(empty.includes('aiNoDecision'), 'missing AI track is not reported')
assert.ok(!empty.includes('NaN'), 'empty markup contains NaN')

const staleCandidates = render({
  data: {
    ...snapshot(),
    aiCandidatePool: { category: 'linear', status: 'stale', observedAt: Date.now(), eligibleCount: 2, candidates: ['XRPUSDT', 'ADAUSDT'] },
  },
  error: null,
  at: Date.now(),
})
assert.ok(!staleCandidates.includes('value="ADAUSDT"'), 'stale AI candidates must not be shown as current chart suggestions')

const failed = render({ data: null, error: 'HTTP 401', at: 0 })
assert.ok(failed.includes('HTTP 401'), 'error detail is not shown')
assert.ok(failed.includes('errorRoute'), 'error hint is not shown')
assert.ok(failed.includes('Not checked / 尚未检查'), 'chart failure must not fabricate engine state')
assert.ok(!failed.includes('Unavailable / 无法连接'), 'chart failure is not engine unavailability evidence')

const loading = renderToStaticMarkup(React.createElement(Panel, {
  t: testTranslate,
}))
assert.ok(loading.includes('bq-root'), 'loading state did not render')
assert.ok(!loading.includes('NaN'), 'loading markup contains NaN')

console.log('ok real React19 panel render: populated, empty, failed, loading, display-only filters and observation-only paper status (SSR effects do not run)\n')
