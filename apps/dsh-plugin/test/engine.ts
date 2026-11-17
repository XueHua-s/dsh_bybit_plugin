import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { apply } from '../dist/index.js'
import type { PluginContext, ToolDefinition } from '../src/host-runtime.ts'
import type { HealthResponse, MarketResponse } from '@bybit-quant/quant-api-client'

const directory = mkdtempSync(join(tmpdir(), 'bybit-engine-host-'))
const health: HealthResponse = {
  status: 'ready', ready: true, environment: 'testnet', supervisor_state: 'running', restart_count: 0,
  max_restarts: 3, last_error: null, process: { rss_bytes: 100, cpu_user_seconds: 0, cpu_system_seconds: 0 },
  market: { state: 'connected', queue_depth: 0, received: 1, parsed: 1, discarded: 0, reconnects: 0, last_event_at: null,
    freshness_seconds: { BTCUSDT: 0 }, exchange_lag_seconds: { BTCUSDT: 0 } },
  execution: { status: 'unknown', order_latency_ms: null, order_rejection_rate: null, reconciliation: 'unknown' },
}
const market: MarketResponse = { environment: 'testnet', symbol: 'BTCUSDT', last_price: 100, bid_price: null, ask_price: null,
  event_time_ms: Date.now(), received_at: new Date().toISOString(), partial: true, exchange_lag_seconds: 0, age_seconds: 0 }
let mode = 'ready'
let requests = 0
let arrived: (() => void) | undefined
const server = createServer((request, response) => {
  requests++
  assert.equal(request.headers.authorization, undefined)
  assert.equal(request.headers['x-bapi-api-key'], undefined)
  if (mode === 'offline') { request.socket.destroy(); return }
  if (mode === 'hold') { arrived?.(); return }
  response.setHeader('content-type', 'application/json')
  if (request.url?.includes('/market/')) {
    response.statusCode = mode === 'missing' ? 404 : 200
    response.end(JSON.stringify(mode === 'missing' ? { detail: 'not configured' } : mode === 'invalid' ? { ...market, environment: 'live' } : market))
  } else {
    response.statusCode = mode === 'degraded' ? 503 : 200
    response.end(JSON.stringify(mode === 'degraded' ? { ...health, ready: false, status: 'degraded' } : health))
  }
})
await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
const address = server.address()
assert.ok(address && typeof address !== 'string')
const engineBaseUrl = `http://127.0.0.1:${address.port}`
type Route = Parameters<Parameters<PluginContext['inject']>[1]>[0]['connection']['fetch'] extends { register(route: infer R): unknown } ? R : never
function harness(env = 'testnet', extra: Record<string, unknown> = {}) {
  const tools = new Map<string, ToolDefinition>()
  const disposers: Array<() => void> = []
  let route: Route | undefined
  const effect: PluginContext['effect'] = factory => { const dispose = factory(); if (dispose) disposers.push(dispose) }
  const ctx: PluginContext = {
    tools: { register: definition => { tools.set(definition.name, definition) } },
    systemPrompt: { section: () => {} }, effect,
    credentials: { resolve: async () => { throw new Error('engine must not resolve credentials') } },
    inject: (_deps, callback) => callback({ effect, connection: { fetch: { register: value => { route = value } } } }),
  }
  apply(ctx, { env, engineBaseUrl, credentialsFile: join(directory, 'missing-credentials.json'), stateFile: join(directory, `${env}.json`), ...extra })
  return { tools, route, close: () => { for (const dispose of disposers.toReversed()) dispose() } }
}
async function call(host: ReturnType<typeof harness>, name: string, args: Record<string, unknown> = {}, signal?: AbortSignal) {
  const tool = host.tools.get(name)
  assert.ok(tool)
  return await tool.execute(args, signal ? { signal } : {}) as Record<string, unknown>
}
try {
  const host = harness()
  assert.equal(requests, 0, 'no background service requests')
  assert.equal(host.tools.get('quant_get_market_snapshot')?.parameters.additionalProperties, false)
  let result = await call(host, 'quant_get_engine_status')
  assert.equal(result.ok, true)
  assert.equal(result.executionReady, false)
  assert.equal((result.data as HealthResponse).execution.status, 'unknown')
  mode = 'degraded'
  result = await call(host, 'quant_get_engine_status')
  assert.equal(result.ok, true)
  assert.equal(result.status, 503)
  assert.equal((result.data as HealthResponse).ready, false)
  mode = 'ready'
  result = await call(host, 'quant_get_market_snapshot', { symbol: 'BTCUSDT' })
  assert.equal((result.data as MarketResponse).partial, true)
  assert.equal((result.data as MarketResponse).bid_price, null)
  assert.equal(result.category, 'linear')
  const count = requests
  for (const args of [{ symbol: '../bad' }, { symbol: 'BTCUSDT', category: 'spot' }, { symbol: 'btc' }]) {
    assert.equal((await call(host, 'quant_get_market_snapshot', args)).code, 'invalid_arguments')
  }
  assert.equal((await call(host, 'quant_get_engine_status', { apiKey: 'not-a-real-key' })).code, 'invalid_arguments')
  assert.equal(requests, count)
  mode = 'missing'
  assert.equal((await call(host, 'quant_get_market_snapshot', { symbol: 'BTCUSDT' })).code, 'not_found')
  mode = 'invalid'
  assert.equal((await call(host, 'quant_get_market_snapshot', { symbol: 'BTCUSDT' })).code, 'invalid_response')
  mode = 'offline'
  assert.equal((await call(host, 'quant_get_engine_status')).code, 'network_error')
  mode = 'hold'
  assert.equal((await call(host, 'quant_get_engine_status')).code, 'timeout')
  mode = 'ready'
  assert.ok(host.route)
  const view = await (await host.route.fetch(new Request('http://localhost/api/bybit-quant?view=engine'))).json() as { ok: boolean }
  assert.equal(view.ok, true)
  const facts = await (await host.route.fetch(new Request('http://localhost/api/bybit-quant?view=health'))).json() as { engine: { ok: boolean } }
  assert.equal(facts.engine.ok, true)
  const mismatch = harness('demo')
  const before = requests
  assert.equal((await call(mismatch, 'quant_get_engine_status')).code, 'environment_mismatch')
  assert.equal((await call(mismatch, 'quant_get_market_snapshot', { symbol: 'BTCUSDT' })).code, 'environment_mismatch')
  assert.equal(requests, before)
  mismatch.close()
  assert.throws(() => harness('testnet', { engineBaseUrl: 'https://example.com' }), /invalid_config/)
  mode = 'hold'
  const controller = new AbortController()
  let start = new Promise<void>(resolve => { arrived = resolve })
  const pending = call(host, 'quant_get_engine_status', {}, controller.signal)
  await start
  controller.abort()
  assert.equal((await pending).code, 'cancelled')
  start = new Promise<void>(resolve => { arrived = resolve })
  const closing = call(host, 'quant_get_engine_status')
  await start
  host.close()
  assert.equal((await closing).code, 'closed')
  assert.equal((await call(host, 'quant_get_engine_status')).code, 'closed')
  mode = 'ready'
  const independent = await fetch(`${engineBaseUrl}/api/v1/health`)
  assert.equal(independent.status, 200, 'Host unload must not kill service')
  console.log('ok engine Host: strict tools, authenticated route, partial/degraded data, env fence, abort/unload, independent service')
} finally {
  server.closeAllConnections()
  await new Promise<void>(resolve => server.close(() => resolve()))
  rmSync(directory, { recursive: true, force: true })
}
