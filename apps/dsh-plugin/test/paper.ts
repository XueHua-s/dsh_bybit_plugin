import assert from 'node:assert/strict'
import { chmodSync, mkdtempSync, rmSync } from 'node:fs'
import { createServer } from 'node:http'
import { createServer as createUnixServer } from 'node:net'
import type { Socket } from 'node:net'
import { join } from 'node:path'
import { apply } from '../dist/index.js'
import { createPaperEngine } from '../dist/lib/engine-paper.js'
import type { PaperCommand, PaperStatus } from '@bybit-quant/quant-api-client'
import type { PluginContext, ToolDefinition } from '../src/host-runtime.ts'
import type { PaperProposal } from '../src/lib/engine-paper.ts'

// No inherited exchange/environment values or real credential paths enter this synthetic process.
process.env = {}
const directory = mkdtempSync(`${process.platform === 'darwin' ? '/private/tmp' : '/tmp'}/bqht-`)
chmodSync(directory, 0o700)
const socketPath = join(directory, 's')
const capability = 'synthetic-host-only-capability-0123456789'
const sessionId = 'paper-test'
const status: PaperStatus = { environment: 'internal_paper', synthetic: true, session_id: sessionId, state: 'idle', ready: false, native_process_alive: false, generation: 0, pending_reservations: 0 }
const command: PaperCommand = { environment: 'internal_paper', session_id: sessionId, command_id: 'cmd-original', native_client_order_id: 'native-original', state: 'accepted', cumulative_filled: '0' }
const fixture = {
  schema_version: '1' as const, fixture_id: 'bundle-a', bundle_digest: 'a'.repeat(64), observed_at_ns: 1, expires_at_ns: 2_000_000,
  candidates: [{ symbol: 'ALPHA', snapshot_id: 'bundle-a:ALPHA:1', observed_at_ns: 1, expires_at_ns: 2_000_000, bid: '10', ask: '10.1', bid_size: '1', ask_size: '1', rules: { base_currency: 'ALPHA', price_increment: '0.1', size_increment: '0.01', min_quantity: '0.01', max_quantity: '100', min_notional: '1' }, bars: [{ timestamp_ns: 1, open: '10', high: '10.1', low: '9.9', close: '10', volume: '1' }], selector_evidence: [{ strategy_id: 'sma', version: '1.0.0', approval_ref: 'fixture-approval:sma', current_status: 'approved', validation_status: 'paper_passed', oos_score: 1, confidence: 0.8, expected_cost_bps: 1, evaluation_ref: 'fixture-evidence:sma', evaluated_at_ns: 1, expires_at_ns: 2_000_000, out_of_sample_samples: 30, supported_regimes: ['trend'], ready_signal: true, evidence_digest: 'b'.repeat(64), provenance: 'synthetic_fixture_only' }] }], correlations: [],
}
const cycle = { schema_version: '1' as const, request_id: 'cycle-request', payload_digest: 'c'.repeat(64), decision_id: 'decision-1', status: 'filled' as const, reason: null, command_id: 'cmd-cycle', native_client_order_id: 'native-cycle' }
let mode = 'normal'
let providerMode = 'normal'
let providerCalls = 0
let httpCalls = 0
let mutations = 0
let lastBody: Record<string, unknown> = {}
let arrived: (() => void) | undefined
const sockets = new Set<Socket>()
const captures: string[] = []
type Harness = { tools: Map<string, ToolDefinition>, routes: Map<string, Route>, close(): Promise<void> }
const hosts: Harness[] = []
const engines: ReturnType<typeof createPaperEngine>[] = []
const http = createServer((request, response) => {
  httpCalls++
  assert.ok(request.headers.authorization === `Bearer ${capability}`, 'HTTP receives only the private injected capability')
  assert.equal(request.headers.origin, undefined)
  assert.equal(request.headers.cookie, undefined)
  assert.equal(request.headers['x-bapi-api-key'], undefined)
  const chunks: Buffer[] = []
  request.on('data', chunk => chunks.push(chunk))
  request.on('end', () => {
    if (request.method === 'POST') {
      mutations++
      const decoded: unknown = JSON.parse(Buffer.concat(chunks).toString())
      assert.ok(decoded !== null && typeof decoded === 'object' && !Array.isArray(decoded))
      lastBody = decoded as Record<string, unknown>
      assert.equal(lastBody.environment, 'internal_paper')
      assert.equal(lastBody.session_id, sessionId)
    }
    if (mode === 'hold') { arrived?.(); return }
    if (mode === 'network') { request.socket.destroy(); return }
    response.setHeader('content-type', 'application/json')
    if (['503', '404', '409', '422', '401', '403'].includes(mode)) {
      response.statusCode = Number(mode)
      response.end(JSON.stringify({ detail: 'service_unavailable' }))
      return
    }
    const isCommand = request.url?.includes('/commands') === true
    const isFixture = request.url?.includes('/fixtures/') === true
    const isCycle = request.url?.includes('/ai-cycles') === true
    let value: Record<string, unknown> = { ...(isFixture ? fixture : isCycle ? cycle : isCommand ? command : status) }
    if (mode === 'wrong-session') value.session_id = 'another-session'
    if (mode === 'wrong-environment') value.environment = 'testnet'
    if (mode === 'missing-environment') delete value.environment
    if (mode === 'wrong-command') value.command_id = 'another-command'
    if (mode === 'secret-response') value[capability] = capability
    response.statusCode = (isCommand || isCycle) && request.method === 'POST' ? 202 : 200
    response.end(JSON.stringify(value))
  })
})
await new Promise<void>(resolve => http.listen(0, '127.0.0.1', resolve))
const address = http.address()
assert.ok(address !== null && typeof address !== 'string')
const origin = `http://127.0.0.1:${address.port}`
const broker = createUnixServer({ allowHalfOpen: true }, socket => {
  sockets.add(socket)
  socket.on('error', () => {})
  socket.on('close', () => sockets.delete(socket))
  const chunks: Buffer[] = []
  socket.on('data', chunk => chunks.push(chunk))
  socket.on('end', () => {
    providerCalls++
    assert.equal(Buffer.concat(chunks).toString(), JSON.stringify({ version: 1, environment: 'internal_paper', session_id: sessionId, origin }) + '\n')
    if (providerMode === 'hold') { arrived?.(); return }
    const answer = () => socket.end(JSON.stringify({ version: 1, environment: 'internal_paper', session_id: sessionId, origin, capability }) + '\n')
    if (providerMode === 'delay') { arrived?.(); setTimeout(answer, 30) }
    else answer()
  })
})
await new Promise<void>(resolve => broker.listen(socketPath, resolve))
chmodSync(socketPath, 0o600)

type Route = Parameters<Parameters<PluginContext['inject']>[1]>[0]['connection']['fetch'] extends { register(route: infer R): unknown } ? R : never
function harness(extra: Record<string, unknown> = {}): Harness {
  const tools = new Map<string, ToolDefinition>()
  const routes = new Map<string, Route>()
  const disposers: Array<() => void | Promise<void>> = []
  const effect: PluginContext['effect'] = factory => { const close = factory(); if (close) disposers.push(close) }
  const ctx: PluginContext = {
    tools: { register: definition => { tools.set(definition.name, definition) } },
    systemPrompt: { section: () => {} }, effect,
    credentials: { resolve: async () => { throw new Error('native paper must not resolve exchange credentials') } },
    logger: () => ({ info: value => captures.push(value), warn: value => captures.push(value), error: value => captures.push(value) }),
    inject: (_deps, callback) => callback({ effect, connection: { fetch: { register: value => { routes.set(value.path, value); return async () => { routes.delete(value.path) } } } } }),
  }
  apply(ctx, {
    paperBaseUrl: origin, paperSessionId: sessionId, paperCapabilitySocket: socketPath, paperControlEnabled: true,
    credentialsFile: join(directory, 'missing-credentials.json'), stateFile: join(directory, `state-${hosts.length}.json`), ...extra,
  })
  const host = { tools, routes, async close() { for (const close of disposers.toReversed()) await close() } }
  hosts.push(host)
  return host
}
async function call(host: ReturnType<typeof harness>, name: string, args: Record<string, unknown> = {}, signal?: AbortSignal) {
  const tool = host.tools.get(name)
  assert.ok(tool)
  const result = await tool.execute(args, signal === undefined ? {} : { signal }) as Record<string, unknown>
  assert.ok(!JSON.stringify(result).includes(capability), 'Tool result must not expose capability content')
  return result
}
const proposal = { request_id: 'request-original', symbol: 'BTCUSDT', side: 'buy', quantity: '0.001', limit_price: '100' } as const
function assertContext(value: Record<string, unknown>, configured = true, control = true) {
  assert.equal(value.source, 'quant-engine-paper')
  assert.equal(value.environment, 'internal_paper')
  assert.equal(value.synthetic, true)
  assert.equal(value.configured, configured)
  assert.equal(value.control_enabled, control)
}
try {
  const host = harness()
  assert.equal(providerCalls, 0)
  assert.equal(httpCalls, 0, 'loading does not contact independent service')
  const names = ['quant_get_paper_status', 'quant_start_paper', 'quant_stop_paper', 'quant_submit_paper_order', 'quant_get_paper_command']
  for (const name of names) assert.equal(host.tools.get(name)?.parameters.additionalProperties, false)
  for (const name of ['quant_start_paper', 'quant_stop_paper', 'quant_submit_paper_order']) assert.equal(host.tools.get(name)?.isConcurrencySafe, undefined)
  assert.equal(host.tools.get('quant_get_paper_status')?.isConcurrencySafe?.(), true)
  let result = await call(host, names[0]!)
  assertContext(result)
  assert.equal((result.data as PaperStatus).ready, false)
  assert.equal((result.data as PaperStatus).state, 'idle')
  for (const name of names.slice(1, 3)) { result = await call(host, name); assertContext(result); assert.equal(result.ok, true) }
  result = await call(host, 'quant_submit_paper_order', proposal)
  assert.equal(result.status, 202)
  assert.equal((result.data as PaperCommand).native_client_order_id, command.native_client_order_id)
  assert.equal(lastBody.order_type, 'limit')
  result = await call(host, 'quant_get_paper_command', { request_id: proposal.request_id })
  assert.equal(result.ok, true)
  const beforeInvalid = [providerCalls, httpCalls, mutations]
  for (const input of [null, [], 1, '']) assert.equal((await host.tools.get('quant_start_paper')!.execute(input as unknown as Record<string, unknown>, {}) as Record<string, unknown>).code, 'invalid_arguments')
  for (const name of names.slice(0, 3)) assert.equal((await call(host, name, { session_id: 'spoof' })).code, 'invalid_arguments')
  for (const input of [
    { ...proposal, environment: 'testnet' }, { ...proposal, source: 'exchange' }, { ...proposal, session_id: 'spoof' },
    { ...proposal, request_id: '_bad' }, { ...proposal, request_id: 'a'.repeat(129) }, { ...proposal, symbol: 'ETHUSDT' },
    { ...proposal, side: 'BUY' }, { ...proposal, quantity: '0' }, { ...proposal, limit_price: '0.00000000' },
    { ...proposal, quantity: '1e-3' }, { ...proposal, quantity: '0001' }, { ...proposal, limit_price: '1.000000001' },
  ]) assert.equal((await call(host, 'quant_submit_paper_order', input)).code, 'invalid_arguments')
  assert.equal((await call(host, 'quant_get_paper_command', { request_id: '_bad' })).code, 'invalid_arguments')
  assert.deepEqual([providerCalls, httpCalls, mutations], beforeInvalid)
  const disabled = harness({ paperBaseUrl: undefined, paperSessionId: undefined, paperCapabilitySocket: undefined, paperControlEnabled: false })
  result = await call(disabled, 'quant_get_paper_status')
  assert.equal(result.code, 'paper_disabled'); assertContext(result, false, false)
  const noControl = harness({ paperControlEnabled: false })
  const beforeDenied = providerCalls
  for (const name of names.slice(1, 4)) {
    result = await call(noControl, name, name.includes('submit') ? proposal : {})
    assert.equal(result.code, 'control_disabled'); assertContext(result, true, false)
  }
  assert.equal(providerCalls, beforeDenied)
  const deniedCycleEngine = createPaperEngine({ paperBaseUrl: origin, paperSessionId: sessionId, paperCapabilitySocket: socketPath, paperControlEnabled: false })
  engines.push(deniedCycleEngine)
  const beforeDeniedCycle = [providerCalls, httpCalls, mutations]
  const deniedCycle = await deniedCycleEngine.cycle({
    schema_version: '1', environment: 'internal_paper', request_id: 'cycle-denied', payload_digest: 'd'.repeat(64),
    session_id: sessionId, fixture_id: 'bundle-a', bundle_digest: 'a'.repeat(64), cycle_id: 'cycle-denied',
    universe_digest: 'a'.repeat(64), expires_at_ns: 2_000_000,
    decision: { decision_id: 'decision-denied', symbol: 'ALPHA', strategy_id: 'sma', strategy_version: '1.0.0', action: 'long', target_exposure: 0.1, evidence_digest: 'b'.repeat(64) },
  })
  assert.ok(!deniedCycle.ok && deniedCycle.code === 'control_disabled')
  assert.deepEqual([providerCalls, httpCalls, mutations], beforeDeniedCycle, 'a local control denial cannot dispatch or become transport-uncertain')
  for (const extra of [{ paperSessionId: undefined }, { paperBaseUrl: 'https://example.com' }, { paperControlEnabled: 'true' }]) assert.throws(() => harness(extra), /^Error: invalid_config$/u)

  const engine = createPaperEngine({ paperBaseUrl: origin, paperSessionId: sessionId, paperCapabilitySocket: socketPath, paperControlEnabled: true })
  engines.push(engine)
  for (const invalid of ['wrong-session', 'wrong-environment', 'missing-environment', 'secret-response']) {
    mode = invalid
    for (const observe of [() => engine.status(), () => engine.request(proposal.request_id), () => engine.command(command.command_id)]) {
      const value = await observe()
      assert.equal(value.ok, false); assert.ok(!value.ok && value.code === 'invalid_response')
    }
    for (const mutate of [() => engine.start(), () => engine.stop(), () => engine.submit(proposal)]) {
      const value = await mutate()
      assert.ok(!value.ok && value.code === 'outcome_uncertain' && value.cause === 'invalid_response')
    }
  }
  mode = '503'
  const before503 = mutations
  for (const mutate of [() => engine.start(), () => engine.stop(), () => engine.submit(proposal)]) {
    const value = await mutate()
    assert.ok(!value.ok && value.code === 'outcome_uncertain' && value.cause === 'unavailable')
    if (!value.ok && value.code === 'outcome_uncertain') assert.deepEqual(value.recovery, 'request_id' in value.recovery ? { action: 'query_request', request_id: proposal.request_id } : { action: 'query_status' })
  }
  assert.equal(mutations, before503 + 3, '503 mutation results are never retried')
  const unavailable = await engine.status()
  assert.ok(!unavailable.ok && unavailable.code === 'unavailable')
  mode = 'wrong-session'; providerMode = 'delay'
  const mutable: PaperProposal = { ...proposal }
  const mutation = engine.submit(mutable)
  mutable.request_id = 'replacement'
  const uncertain = await mutation
  assert.ok(!uncertain.ok && uncertain.code === 'outcome_uncertain' && uncertain.recovery.action === 'query_request' && uncertain.recovery.request_id === proposal.request_id)
  assert.equal(lastBody.request_id, proposal.request_id)
  providerMode = 'normal'; mode = '404'
  const missing = await engine.request(proposal.request_id)
  assert.ok(!missing.ok && missing.code === 'not_found')
  mode = 'normal'
  assert.equal((await engine.request(proposal.request_id)).ok, true)
  const fixtureResult = await engine.fixture('bundle-a')
  assert.equal(fixtureResult.ok, true)
  if (fixtureResult.ok) assert.equal(fixtureResult.data.fixture_id, 'bundle-a')
  const cycleResult = await engine.cycle({
    schema_version: '1', environment: 'internal_paper', request_id: cycle.request_id,
    payload_digest: cycle.payload_digest, session_id: sessionId, fixture_id: 'bundle-a', bundle_digest: fixture.bundle_digest,
    cycle_id: 'cycle-1', universe_digest: fixture.bundle_digest, expires_at_ns: fixture.expires_at_ns,
    decision: { decision_id: cycle.decision_id, symbol: 'ALPHA', strategy_id: 'sma', strategy_version: '1.0.0', action: 'long', target_exposure: 0.1, evidence_digest: 'b'.repeat(64) },
  })
  assert.equal(cycleResult.ok, true)
  if (cycleResult.ok) assert.equal(cycleResult.data.request_id, cycle.request_id)
  const cycleLookup = await engine.cycleRequest(cycle.request_id)
  assert.equal(cycleLookup.ok, true)
  const invalidCycle = await engine.cycle({
    schema_version: '1', environment: 'internal_paper', request_id: 'cycle-invalid', payload_digest: 'c'.repeat(64),
    session_id: 'spoof', fixture_id: 'bundle-a', bundle_digest: fixture.bundle_digest, cycle_id: 'cycle-1', universe_digest: fixture.bundle_digest,
    expires_at_ns: fixture.expires_at_ns, decision: { decision_id: 'decision-1', symbol: 'ALPHA', strategy_id: 'sma', strategy_version: '1.0.0', action: 'abstain', target_exposure: null, evidence_digest: 'b'.repeat(64) },
  })
  assert.equal(invalidCycle.ok, false)
  if (!invalidCycle.ok) assert.equal(invalidCycle.code, 'invalid_arguments')

  const route = host.routes.get('/api/bybit-quant/paper')
  assert.ok(route)
  assert.equal(route.requestBody, 'buffered')
  assert.deepEqual(route.methods, ['GET', 'HEAD'])
  let reply = await route.fetch(new Request('http://localhost/api/bybit-quant/paper'))
  assert.equal(reply.status, 200); assert.equal(reply.headers.get('cache-control'), 'no-store')
  assertContext(await reply.json() as Record<string, unknown>)
  reply = await route.fetch(new Request('http://localhost/api/bybit-quant/paper', { method: 'HEAD' }))
  assert.equal(await reply.text(), '')
  const beforeRejected = [providerCalls, httpCalls]
  assert.equal((await route.fetch(new Request('http://localhost/api/bybit-quant/paper', { method: 'POST', body: JSON.stringify({ action: 'start' }) }))).status, 405)
  assert.equal((await route.fetch(new Request('http://localhost/api/bybit-quant/paper?session=x'))).status, 400)
  assert.equal((await route.fetch(new Request('http://localhost/api/bybit-quant/paper', { method: 'DELETE' }))).status, 405)
  assert.deepEqual([providerCalls, httpCalls], beforeRejected, 'invalid browser inputs never reach broker or HTTP')

  providerMode = 'delay'
  const providerAbort = new AbortController()
  let arrival = new Promise<void>(resolve => { arrived = resolve })
  const beforeProviderAbort = httpCalls
  const cancelledProvider = engine.status(providerAbort.signal)
  await arrival; providerAbort.abort()
  const cancelledBeforeHttp = await cancelledProvider
  assert.ok(!cancelledBeforeHttp.ok && cancelledBeforeHttp.code === 'cancelled')
  await new Promise<void>(resolve => setTimeout(resolve, 60))
  assert.equal(httpCalls, beforeProviderAbort, 'cancelled SDK request cannot send after a late private provider callback')
  providerMode = 'normal'; mode = 'hold'
  const cancel = new AbortController()
  arrival = new Promise<void>(resolve => { arrived = resolve })
  const pending = engine.status(cancel.signal)
  await arrival; cancel.abort()
  const cancelled = await pending
  assert.ok(!cancelled.ok && cancelled.code === 'cancelled')
  providerMode = 'hold'
  arrival = new Promise<void>(resolve => { arrived = resolve })
  const pendingClose = engine.submit(proposal)
  await arrival; engine.close()
  const closed = await pendingClose
  assert.ok(!closed.ok && closed.code === 'outcome_uncertain' && closed.cause === 'closed' && closed.recovery.action === 'query_request' && closed.recovery.request_id === proposal.request_id)
  const callsAtClose = httpCalls
  await new Promise<void>(resolve => setTimeout(resolve, 550))
  assert.equal(httpCalls, callsAtClose, 'late or closed provider cannot send HTTP')
  mode = 'normal'; providerMode = 'normal'
  await host.close()
  assert.equal(host.routes.size, 0, 'async exact-route disposer is retained')
  assert.ok(!captures.join('\n').includes(capability), 'captured logs contain no private capability')
  const closedStatus = await engine.status()
  assert.ok(!closedStatus.ok && closedStatus.code === 'closed')
  const independent = createPaperEngine({ paperBaseUrl: origin, paperSessionId: sessionId, paperCapabilitySocket: socketPath })
  engines.push(independent)
  assert.equal((await independent.status()).ok, true, 'Host close leaves independently owned service available')
  console.log('ok native paper Host: private provider/SDK, strict Tools, fixed session, opt-in, 503 uncertainty/original IDs, streaming panel guards, abort and independent lifetime')
} finally {
  for (const engine of engines) engine.close()
  for (const host of hosts) await host.close()
  for (const socket of sockets) socket.destroy()
  await new Promise<void>(resolve => broker.close(() => resolve()))
  http.closeAllConnections()
  await new Promise<void>(resolve => http.close(() => resolve()))
  rmSync(directory, { recursive: true, force: true })
}
