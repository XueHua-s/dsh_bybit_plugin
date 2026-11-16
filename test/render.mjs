/**
 * Render test for the panel: server-renders the real components with real React
 * and a realistic snapshot, so a data-dependent crash (a bad table, a chart
 * division by zero, a missing field) fails here instead of blanking the slot in
 * the browser.
 *
 * React is not shipped with dsh, so point `BQ_REACT_MODULES` at a directory that
 * has `react` and `react-dom` installed; without it this test reports that it
 * was skipped. Example:
 *
 *   mkdir -p /tmp/bq-react && (cd /tmp/bq-react && npm i react@18 react-dom@18)
 *   BQ_REACT_MODULES=/tmp/bq-react/node_modules node test/render.mjs
 */
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { join } from 'node:path'

const modules = process.env.BQ_REACT_MODULES
if (modules === undefined) {
  console.log('skipped: set BQ_REACT_MODULES to a node_modules directory with react and react-dom\n')
  process.exit(0)
}

const require = createRequire(join(modules, 'noop.js'))
const React = require('react')
const { renderToStaticMarkup } = require('react-dom/server')

let loaded
globalThis.window = { __ModuleLoader__: { load: (bundle) => { loaded = bundle } } }
await import('../dist/client.js')

const plugin = loaded.factory((specifier) => {
  if (specifier !== 'react') throw new Error(`unexpected module ${specifier}`)
  return React
})

const registrations = []
plugin.apply({
  effect: (factory) => { factory() },
  locale: { register: () => () => {}, bind: () => (key) => key },
  slots: {
    inject: (_key, factory) => factory(),
    register: (options, component) => { registrations.push({ options, component }); return () => {} },
  },
})

const Panel = registrations.find(entry => entry.options.name === 'main').component

/** Build the snapshot shape the Host route returns. */
function snapshot({ withPosition = true } = {}) {
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
    allowLiveTrading: false,
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
    updatedAt: start,
  }
}

/** Render the panel with one injected snapshot. */
function render(initial) {
  return renderToStaticMarkup(React.createElement(Panel, { t: (key) => key, initial }))
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
assert.ok(populated.includes('aiTitle'), 'AI card title is missing')
assert.ok(populated.includes('higher timeframe trend up'), 'AI thesis is missing')
assert.ok(populated.includes('66.7'), 'AI hit rate is missing')
assert.ok(populated.includes('0.21'), 'AI Brier score is missing')

const empty = render({ data: { ...snapshot({ withPosition: false }), klines: [], lastBacktest: null, lastSignal: null, ai: null }, error: null, at: 0 })
assert.ok(empty.includes('noPositions'), 'empty paper book is not reported')
assert.ok(empty.includes('noBacktest'), 'missing backtest is not reported')
assert.ok(empty.includes('aiNoDecision'), 'missing AI track is not reported')
assert.ok(!empty.includes('NaN'), 'empty markup contains NaN')

const failed = render({ data: null, error: 'HTTP 401', at: 0 })
assert.ok(failed.includes('HTTP 401'), 'error detail is not shown')
assert.ok(failed.includes('errorRoute'), 'error hint is not shown')

const loading = renderToStaticMarkup(React.createElement(Panel, { t: (key) => key }))
assert.ok(loading.includes('bq-root'), 'loading state did not render')
assert.ok(!loading.includes('NaN'), 'loading markup contains NaN')

console.log('ok panel render: populated, empty, failed, and loading states\n')
