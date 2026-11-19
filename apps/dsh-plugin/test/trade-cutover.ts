import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { BybitClient } from '../dist/lib/bybit.js'
import { createRuntimeMonitor } from '../dist/lib/monitor.js'
import { apply } from '../dist/index.js'
import type { PluginContext } from '../src/host-runtime.js'

type Tool = { name: string, execute(args: Record<string, unknown>, exec: { signal?: AbortSignal }): Promise<unknown> }

function createContext(tools: Map<string, Tool>): { context: PluginContext, disposers: Array<() => void> } {
  const disposers: Array<() => void> = []
  const context: PluginContext = {
    logger: () => ({ info() {}, warn() {}, error() {} }),
    systemPrompt: { section() {} },
    tools: { register: (definition: Tool) => { tools.set(definition.name, definition) } },
    effect: (effect: () => void | (() => void)) => {
      const disposer = effect()
      if (typeof disposer === 'function') disposers.push(disposer)
      return disposer
    },
    inject: (_dependencies, callback) => {
      callback({ effect: context.effect, connection: { fetch: { register: () => {} } } })
    },
  }
  return { context, disposers }
}

const matrix = ['create', 'cancel', 'cancel_all', 'close'] as const
const environments = ['demo', 'testnet', 'live'] as const
const legacyConfigs = Array.from({ length: 8 }, (_, flags) => ({
  allowLiveTrading: (flags & 1) !== 0,
  allowTestnetTrading: (flags & 2) !== 0,
  allowMainAccount: (flags & 4) !== 0,
}))
let passed = 0
const previousHome = process.env.DSH_HOME
const temporaryHome = mkdtempSync(join(tmpdir(), 'bybit-trade-cutover-'))
process.env.DSH_HOME = temporaryHome
try {
  for (const env of environments) {
    for (const legacy of legacyConfigs) {
      const tools = new Map<string, Tool>()
      const { context, disposers } = createContext(tools)
      apply(context, {
        env, ...legacy,
        stateFile: join(temporaryHome, `state-${env}-${passed}.json`),
        credentialsFile: join(temporaryHome, `credentials-${env}-${passed}.json`),
      })
      const trade = tools.get('bybit_trade')
      assert.ok(trade, `trade tool registered for ${env}`)
      for (const action of matrix) {
        const result = await trade.execute({ action, dryRun: false }, {}) as Record<string, unknown>
        assert.equal(result.sent, false)
        assert.equal(result.unavailable, true)
        assert.equal(result.code, 'execution_authority_unavailable')
        assert.equal(result.action, action)
        passed += 1
      }
      for (const disposer of disposers) disposer()
    }
  }
} finally {
  if (previousHome === undefined) delete process.env.DSH_HOME
  else process.env.DSH_HOME = previousHome
  rmSync(temporaryHome, { recursive: true, force: true })
}

const methodNames = Object.getOwnPropertyNames(BybitClient.prototype)
for (const forbidden of ['createOrder', 'cancelOrder', 'cancelAll', 'signedRequest']) {
  assert.equal(methodNames.includes(forbidden), false, `BybitClient must not expose ${forbidden}`)
}

const monitor = createRuntimeMonitor()
monitor.observeRequest({ operation: '/v5/order/realtime', signed: true, ok: true, latencyMs: 42 })
const readOnlyMetrics = monitor.snapshot()
assert.equal(readOnlyMetrics.lastOrderLatencyMs, null)
assert.equal(readOnlyMetrics.orderCount, 0)
assert.equal(readOnlyMetrics.rejectedOrderCount, 0)
passed += 1

const originalFetch = globalThis.fetch
const requests: Array<{ method: string | undefined, url: string, body: unknown }> = []
globalThis.fetch = async (input, init) => {
  requests.push({ method: init?.method, url: String(input), body: init?.body })
  return new Response(JSON.stringify({ retCode: 0, result: { list: [{ totalEquity: '0', totalAvailableBalance: '0', coin: [] }] } }), { status: 200 })
}
try {
  const client = new BybitClient({ env: 'testnet', apiKey: 'key-fixture', apiSecret: 'secret-fixture' })
  await client.walletBalance({ accountType: 'UNIFIED' })
  assert.equal(requests.length, 1)
  assert.equal(requests[0]?.method, 'GET')
  assert.equal(requests[0]?.body, undefined)
  assert.match(requests[0]?.url ?? '', /\/v5\/account\/wallet-balance\?accountType=UNIFIED/u)
  assert.equal(requests.some(request => /\/v5\/order\/(create|cancel|cancel-all)/u.test(request.url)), false)
  passed += 1
} finally {
  globalThis.fetch = originalFetch
}

console.log(`trade cutover tests: ${passed} passed; no exchange mutation request was sent`)
