/**
 * End-to-end integration test for the Host half.
 *
 * `index.js` imports nothing from the dsh installation, so a plain Node process
 * can mount it with a stand-in Cordis context: the tools register, the panel
 * routes register, and every call runs against the real Bybit public API and a
 * throwaway paper book. No credentials, no orders.
 *
 * Run from the bundle directory: `node test/integration.ts`
 */
import assert from 'node:assert/strict'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { apply } from '../dist/index.js'

/** Recursive check mirroring the harness rule for lossless tool values. */
function assertLossless(value: unknown, path = 'value'): void {
  if (value === null) return
  const type = typeof value
  if (type === 'boolean' || type === 'string') return
  if (type === 'number') {
    assert.ok(Number.isFinite(value), `${path} is not finite: ${value}`)
    assert.ok(!Object.is(value, -0), `${path} is negative zero`)
    return
  }
  assert.equal(type, 'object', `${path} is not JSON (${type})`)
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertLossless(item, `${path}[${index}]`))
    return
  }
  assert.equal(Object.getPrototypeOf(value), Object.prototype, `${path} is not a plain object`)
  assert.ok(value !== undefined && value !== null, `${path} is not an object`)
  for (const [key, member] of Object.entries(value)) assertLossless(member, `${path}.${key}`)
}

const directory = mkdtempSync(join(tmpdir(), 'bybit-quant-it-'))
const stateFile = join(directory, 'state.json')
const tools = new Map()
const routes = new Map()
const disposers: Array<() => void> = []
let sectionText = ''

type TestRoute = { path: string, methods: string[], fetch(request: Request): Response | Promise<Response> }
type InjectedContext = { effect(effect: () => void | (() => void)): void, webServer: object, connection: { fetch: { register(route: TestRoute): void | (() => void) } } }

const ctx = {
  logger: () => ({ info() {}, warn() {}, error() {} }),
  systemPrompt: { section: ({ text }: { text: string }) => { sectionText = text } },
  tools: { register: (definition: { name: string }) => { tools.set(definition.name, definition); return () => {} } },
  effect: (fn: () => void | (() => void)) => {
    const disposer = fn()
    if (typeof disposer === 'function') disposers.push(disposer)
    return disposer
  },
  inject: (_deps: string[], callback: (context: InjectedContext) => void) => callback({
    effect: (fn: () => void | (() => void)) => {
    const disposer = fn()
    if (typeof disposer === 'function') disposers.push(disposer)
    return disposer
  },
    webServer: {},
    connection: {
      fetch: {
        register: (route: TestRoute) => {
          routes.set(route.path, route)
          return () => routes.delete(route.path)
        },
      },
    },
  }),
}

let passed = 0
const check = async (label: string, fn: () => void | Promise<void>): Promise<void> => {
  await fn()
  passed += 1
  console.log(`ok ${label}`)
}

/** Run one registered tool and assert its value is lossless JSON. */
async function call(name: string, args: Record<string, unknown>) {
  const definition = tools.get(name)
  assert.ok(definition !== undefined, `tool ${name} is not registered`)
  const value = await definition.execute(args, { signal: undefined })
  assertLossless(value, name)
  return value
}

apply(ctx, {
  env: 'demo',
  paperBalanceUsd: 1000,
  defaultSymbol: 'BTCUSDT',
  defaultCategory: 'linear',
  maxOrderNotionalUsd: 200,
  stateFile,
  credentialsFile: join(directory, 'credentials.json'),
})

check('registers the expected tools and a prompt note', () => {
  assert.deepEqual([...tools.keys()].sort(), [
    'bybit_account', 'bybit_instruments', 'bybit_market', 'bybit_trade', 'quant_backtest', 'quant_brief',
    'quant_decide', 'quant_get_engine_status', 'quant_get_market_snapshot', 'quant_get_paper_command',
    'quant_get_paper_status', 'quant_paper', 'quant_review', 'quant_signals', 'quant_start_paper',
    'quant_stop_paper', 'quant_submit_paper_order', 'quant_watchlist',
  ])
  assert.match(sectionText, /preview-only/)
  assert.match(sectionText, /execution_authority_unavailable/)
  for (const definition of tools.values()) {
    assert.equal(definition.parameters.type, 'object')
    assert.ok(definition.parameters.properties !== undefined)
    assert.equal(definition.output.schema.type, 'object')
  }
})

await check('reads a live ticker', async () => {
  const value = await call('bybit_market', { kind: 'ticker', symbol: 'BTCUSDT' })
  assert.equal(value.symbol, 'BTCUSDT')
  assert.ok(value.last > 0)
  assert.ok(value.time > 0)
})

await check('reads candles oldest-first and bounded', async () => {
  const value = await call('bybit_market', { kind: 'kline', symbol: 'ETHUSDT', interval: '1h', limit: 30 })
  assert.equal(value.interval, '1h')
  assert.equal(value.lastBars.length, 12)
  assert.ok(value.window.high >= value.window.low)
})

await check('rejects an unknown kind', async () => {
  await assert.rejects(() => call('bybit_market', { kind: 'nope' }), /kind must be one of/)
})

await check('backtests a strategy with consistent accounting', async () => {
  const value = await call('quant_backtest', {
    strategy: 'ma_cross', symbol: 'BTCUSDT', interval: '60', bars: 400, fast: 10, slow: 30,
  })
  assert.equal(value.metrics.bars, 400)
  assert.ok(value.metrics.exposurePct >= 0 && value.metrics.exposurePct <= 100, `exposure ${value.metrics.exposurePct}`)
  assert.ok(Number.isFinite(value.metrics.sharpe))
  for (const trade of value.recentTrades) {
    const move = trade.exitPrice - trade.entryPrice
    if (Math.abs(move) < trade.entryPrice * 0.01) continue
    assert.equal(Math.sign(trade.pnlPct), Math.sign(move), `trade ${trade.entryPrice} -> ${trade.exitPrice} reported ${trade.pnlPct}%`)
  }
  assert.ok(['long', 'flat'].includes(value.signal.target))
})

await check('rejects an unknown strategy', async () => {
  await assert.rejects(() => call('quant_backtest', { strategy: 'magic' }), /strategy must be one of/)
})

await check('opens a paper book at the configured balance', async () => {
  const value = await call('quant_paper', { action: 'status' })
  assert.equal(value.book.equityUsd, 1000)
  assert.equal(value.book.positions.length, 0)
})

await check('buys at the live mark without losing JSON fidelity', async () => {
  const value = await call('quant_paper', { action: 'buy', symbol: 'ETHUSDT', notionalUsd: 100 })
  assert.ok(value.filled.qty > 0)
  assert.ok(value.filled.notionalUsd > 0)
  assert.equal(value.book.positions.length, 1)
  assert.ok(value.book.balanceUsd < 1000)
})

await check('marks the position and sells it back', async () => {
  const status = await call('quant_paper', { action: 'status' })
  assert.equal(status.book.positions.length, 1)
  assert.ok(status.book.equityUsd > 900)
  const sold = await call('quant_paper', { action: 'sell', symbol: 'ETHUSDT' })
  assert.ok(sold.filled.qty > 0)
  assert.equal(sold.book.positions.length, 0)
})

await check('resets the paper book', async () => {
  const value = await call('quant_paper', { action: 'reset' })
  assert.equal(value.book.balanceUsd, 1000)
  const persisted = JSON.parse(readFileSync(stateFile, 'utf8'))
  assert.equal(persisted.paper.balance, 1000)
  assert.equal(persisted.lastBacktest.strategy, 'ma_cross')
})

await check('previews a real order instead of sending it', async () => {
  const value = await call('bybit_trade', { action: 'create', symbol: 'BTCUSDT', side: 'buy', orderType: 'Market', qty: 0.001 })
  assert.equal(value.sent, false)
  assert.match(value.reason, /exchange writes are unavailable/)
  assert.ok(value.notionalUsd > 0)
})

await check('refuses every exchange write before any request', async () => {
  for (const action of ['create', 'cancel', 'cancel_all', 'close']) {
    const value = await call('bybit_trade', {
      action, symbol: 'BTCUSDT', side: 'buy', qty: 0.001, orderId: 'legacy-order', confirm: 'LIVE', dryRun: false,
    })
    assert.equal(value.sent, false)
    assert.equal(value.unavailable, true)
    assert.equal(value.code, 'execution_authority_unavailable')
  }
})

await check('caps an oversized order', async () => {
  await assert.rejects(
    () => call('bybit_trade', { action: 'create', symbol: 'BTCUSDT', side: 'buy', qty: 10 }),
    /exceeds maxOrderNotionalUsd/,
  )
})

await check('requires a valid side and quantity', async () => {
  await assert.rejects(() => call('bybit_trade', { action: 'create', symbol: 'BTCUSDT', qty: 0.001 }), /needs side/)
  await assert.rejects(() => call('bybit_trade', { action: 'create', symbol: 'BTCUSDT', side: 'buy', qty: 0 }), /positive qty/)
  await assert.rejects(() => call('bybit_trade', { action: 'create', symbol: 'BTCUSDT', side: 'buy', orderType: 'Limit', qty: 0.001 }), /needs a positive price/)
})

await check('builds the AI brief for the configured symbols', async () => {
  const value = await call('quant_brief', {})
  assert.equal(value.brief.symbols.length, 2)
  for (const item of value.brief.symbols) {
    assert.ok(item.price > 0)
    assert.ok(['up', 'down', 'range'].includes(item.primary.state))
    assert.ok(item.frames['240'] !== undefined)
    assert.ok(Number.isFinite(item.frames['240'].atrPct))
  }
  assert.equal(value.brief.limits.riskPerTradePct, 1)
  assert.ok(typeof value.decisionSchema.action === 'string')
})

await check('records a flat decision without touching the book', async () => {
  const value = await call('quant_decide', {
    symbol: 'BTCUSDT', action: 'flat', confidence: 0.5, horizonHours: 4,
    thesis: 'no clean edge right now, standing aside until the range resolves',
    invalidation: 'a 4h close above the range high',
  })
  assert.equal(value.status, 'flat')
  assert.equal(value.accepted, true)
  assert.equal(value.position, null)
  assert.equal(value.track.positions.length, 0)
})

await check('refuses an oversized decision and journals the rejection', async () => {
  const value = await call('quant_decide', {
    symbol: 'BTCUSDT', action: 'long', sizePct: 100, stopPct: 3, takePct: 6,
    confidence: 0.7, horizonHours: 8,
    thesis: 'momentum continuation after the range break, aggressive sizing for the test',
    invalidation: 'a close back inside the range',
  })
  assert.equal(value.status, 'rejected')
  assert.equal(value.accepted, false)
  assert.ok(value.gate.reasons.length >= 1)
  assert.equal(value.position, null)
})

await check('accepts a sized decision and opens a simulated position', async () => {
  const value = await call('quant_decide', {
    symbol: 'BTCUSDT', action: 'long', sizePct: 10, stopPct: 1, takePct: 2,
    confidence: 0.62, horizonHours: 4,
    thesis: 'higher timeframe trend up and funding is mild, buying a small pullback',
    invalidation: 'a 1h close below the prior swing low',
  })
  assert.equal(value.status, 'open')
  assert.equal(value.accepted, true)
  assert.ok(value.position.notionalUsd > 50)
  assert.ok(value.position.stopPrice < value.position.entryPrice)
  assert.equal(value.decision.evidence.thesis.kind, 'untrusted-evidence')
  assert.equal(value.decision.evidence.thesis.source, 'agent')
  assert.equal(value.decision.evidence.thesis.trusted, false)
  assert.equal(value.decision.evidence.invalidation.trusted, false)
  assert.equal(value.track.positions.length, 1)
})

await check('reviews the AI track with a baseline', async () => {
  const value = await call('quant_review', { decisions: 5 })
  assert.equal(value.scorecard.open, 1)
  assert.ok(Array.isArray(value.recent) && value.recent.length >= 3)
  assert.equal(value.recent[0].evidence.thesis.kind, 'untrusted-evidence')
  assert.equal(value.recent[0].evidence.invalidation.source, 'agent')
  assert.ok(value.baseline === null || typeof value.baseline.buyHoldPct === 'number')
  assert.ok(value.limits.symbols.length === 2)
})

await check('flattens the AI position and scores the closed decision', async () => {
  const flat = await call('quant_decide', {
    symbol: 'BTCUSDT', action: 'flat', confidence: 0.55, horizonHours: 2,
    thesis: 'closing the test position to exercise the closing path',
    invalidation: 'not applicable, this is a close',
  })
  assert.equal(flat.status, 'flat')
  assert.ok(flat.closed !== null)
  const review = await call('quant_review', {})
  assert.equal(review.scorecard.open, 0)
  assert.equal(review.scorecard.closed, 1)
  assert.ok(review.scorecard.hitRatePct === 0 || review.scorecard.hitRatePct === 100)
})

await check('discovers what Bybit lists, including USDC perpetuals', async () => {
  const linear = await call('bybit_instruments', { category: 'linear', limit: 200 })
  assert.ok(linear.total > 100, `linear catalogue ${linear.total}`)
  assert.ok(linear.quotes.includes('USDT'))
  const usdc = await call('bybit_instruments', { category: 'linear', quote: 'USDC', limit: 50 })
  assert.ok(usdc.matched > 0, 'no USDC perpetuals found')
  for (const row of usdc.instruments as Array<{ quote: string }>) assert.equal(row.quote, 'USDC')
  const equity = await call('bybit_instruments', { category: 'linear', search: 'AAPL', limit: 20 })
  assert.ok(equity.matched > 0 && equity.instruments.some((row: { symbol: string }) => row.symbol === 'AAPLUSDT'), 'stock perpetual AAPLUSDT missing')
  const spot = await call('bybit_instruments', { category: 'spot', search: 'TSLAX', limit: 10 })
  assert.ok(spot.matched > 0, 'tokenised stock TSLAXUSDT missing')
  assert.ok(equity.instruments[0].qtyStep !== undefined)
})

await check('lists the configured watchlist before the user sets one', async () => {
  const value = await call('quant_watchlist', { action: 'list' })
  assert.equal(value.source, 'plugin config default')
  assert.deepEqual(value.symbols, ['BTCUSDT', 'ETHUSDT'])
})

await check("sets, extends, and trims the user's watchlist", async () => {
  const set = await call('quant_watchlist', { action: 'set', symbols: ['BTCUSDT', 'SOLUSDT'], category: 'linear' })
  assert.deepEqual(set.symbols, ['BTCUSDT', 'SOLUSDT'])
  const added = await call('quant_watchlist', { action: 'add', symbol: 'XRPUSDT' })
  assert.deepEqual(added.symbols, ['BTCUSDT', 'SOLUSDT', 'XRPUSDT'])
  const removed = await call('quant_watchlist', { action: 'remove', symbol: 'SOLUSDT' })
  assert.deepEqual(removed.symbols, ['BTCUSDT', 'XRPUSDT'])
})

await check('rejects an unknown symbol on the watchlist', async () => {
  await assert.rejects(
    () => call('quant_watchlist', { action: 'add', symbol: 'NOTACOIN' }),
    /unknown|invalid/i,
  )
})

await check('the brief and decisions follow the user watchlist', async () => {
  const brief = await call('quant_brief', {})
  assert.deepEqual(brief.brief.symbols.map((item: { symbol: string }) => item.symbol), ['BTCUSDT', 'XRPUSDT'])
  assert.ok(brief.brief.limits.watchlist.includes('XRPUSDT'))
  const decision = await call('quant_decide', {
    symbol: 'XRPUSDT', action: 'flat', confidence: 0.5, horizonHours: 4,
    thesis: 'watchlist wiring check: standing aside while the range resolves',
    invalidation: 'a 4h close outside the range',
  })
  assert.equal(decision.status, 'flat')
})

await check('evaluates the curated signals on the watchlist', async () => {
  const value = await call('quant_signals', { symbols: ['BTCUSDT'], timeframes: ['240', '60'] })
  assert.equal(value.symbols.length, 1)
  const frames = value.symbols[0]!.frames
  assert.equal(frames.length, 2)
  for (const frame of frames) {
    assert.ok(['long', 'short', 'flat'].includes(frame.bias))
    assert.ok(Number.isFinite(frame.score))
    assert.ok(frame.supertrend === null || [1, -1].includes(frame.supertrend.dir))
    assert.ok(frame.adx === null || Number.isFinite(frame.adx.adx))
  }
  assert.ok(value.sources.supertrend.includes('Supertrend'))
  assert.ok(Number.isFinite(value.symbols[0].consensus))
  const brief = await call('quant_brief', { symbols: ['BTCUSDT'] })
  assert.ok(brief.brief.symbols[0].primary.signals !== null)
})

await check('serves the panel snapshot and health views on the bridge route', async () => {
  const route = routes.get('/api/bybit-quant')
  assert.ok(route !== undefined, 'panel route is not registered')
  assert.deepEqual([...route.methods].sort(), ['GET', 'HEAD'])
  const response = await route.fetch(new Request('http://localhost/api/bybit-quant?symbol=ETHUSDT&interval=60&bars=60'))
  const payload = await response.json()
  assert.equal(payload.ok, true)
  assert.equal(payload.symbol, 'ETHUSDT')
  assert.equal(payload.klines.length, 60)
  assert.ok(payload.ticker.last > 0)
  assert.ok(Array.isArray(payload.paper.positions))
  assert.ok(payload.ai === null || typeof payload.ai.equityUsd === 'number')
  if (payload.ai !== null) assert.ok(typeof payload.ai.limits.riskPerTradePct === 'number')
  const healthPayload = await (await route.fetch(new Request('http://localhost/api/bybit-quant?view=health'))).json()
  assert.equal(healthPayload.version, '1.4.5')
  assert.equal(healthPayload.executionAuthority, 'unavailable')
  assert.equal(healthPayload.stateFile, stateFile)
})

for (const dispose of disposers.reverse()) dispose()
rmSync(directory, { recursive: true, force: true })
console.log(`\n${passed} integration checks passed\n`)
