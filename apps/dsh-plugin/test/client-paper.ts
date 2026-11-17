import assert from 'node:assert/strict'
import * as React from 'react'
import { paperPanel } from '../src/client-paper.ts'
import type { PaperStatus } from '@bybit-quant/quant-api-client'
import type { PaperStatusResult } from '../src/lib/engine-paper.ts'

type Cleanup = void | (() => void)
type Effect = { deps: readonly unknown[] | undefined, cleanup: Cleanup }
type RequestRecord = { input: string, init: RequestInit, respond(value: unknown, status?: number): void, reject(): void }
const labels = { check: 'Check status / 检查状态', start: 'Start paper / 启动模拟', stop: 'Stop paper / 停止模拟' }
const context = { source: 'quant-engine-paper', environment: 'internal_paper', synthetic: true, configured: true, control_enabled: true } as const
const status = (patch: Partial<PaperStatus> = {}): PaperStatusResult => ({ ...context, ok: true, status: 200, data: {
  environment: 'internal_paper', synthetic: true, session_id: 'native-ui-test', generation: 0,
  pending_reservations: 0, state: 'idle', ready: false, native_process_alive: false, ...patch,
} })

function elements(value: unknown): React.ReactElement<Record<string, unknown>>[] {
  if (Array.isArray(value)) return value.flatMap(elements)
  if (!React.isValidElement<Record<string, unknown>>(value)) return []
  return [value, ...elements(value.props.children)]
}
function text(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (Array.isArray(value)) return value.map(text).join('')
  return React.isValidElement<Record<string, unknown>>(value) ? text(value.props.children) : ''
}

/** Executes the card's real effects with stable hook slots; only the browser transport is replaced. */
function harness() {
  const states: unknown[] = []
  const effects: Effect[] = []
  const scheduled: Array<() => void> = []
  const requests: RequestRecord[] = []
  let stateIndex = 0
  let effectIndex = 0
  let dirty = true
  let mounted = true
  let writesAfterUnmount = 0
  let tree: unknown
  const runtime: Parameters<typeof paperPanel>[0] = {
    createElement: React.createElement,
    useState: (<T>(initial?: T | (() => T)) => {
      const index = stateIndex++
      if (!(index in states)) states[index] = typeof initial === 'function' ? (initial as () => T)() : initial
      return [states[index] as T, (next: T | ((previous: T) => T)) => {
        if (!mounted) { writesAfterUnmount++; return }
        states[index] = typeof next === 'function' ? (next as (previous: T) => T)(states[index] as T) : next
        dirty = true
      }]
    }) as typeof React.useState,
    useEffect: (factory, deps) => {
      const index = effectIndex++
      const previous = effects[index]
      if (previous && deps && previous.deps && deps.length === previous.deps.length && deps.every((value, offset) => Object.is(value, previous.deps?.[offset]))) return
      scheduled.push(() => {
        previous?.cleanup?.()
        effects[index] = { deps, cleanup: factory() }
      })
    },
  }
  const Card = paperPanel(runtime)
  function render() {
    while (dirty) {
      dirty = false; stateIndex = 0; effectIndex = 0
      tree = Card()
      while (scheduled.length > 0) scheduled.shift()?.()
    }
  }
  globalThis.fetch = (input, init = {}) => new Promise<Response>((resolve, reject) => {
    assert.equal(typeof input, 'string')
    requests.push({ input: String(input), init, respond: (value, code = 200) => resolve(new Response(JSON.stringify(value), { status: code, headers: { 'content-type': 'application/json' } })), reject: () => reject(new Error('synthetic transport failure')) })
  })
  function button(action: keyof typeof labels) {
    render()
    const node = elements(tree).find(candidate => candidate.type === 'button' && text(candidate) === labels[action])
    assert.ok(node, 'expected card control')
    return node
  }
  function click(action: keyof typeof labels) {
    const node = button(action)
    assert.equal(node.props.disabled, false, `${action} must be enabled`)
    assert.equal(typeof node.props.onClick, 'function')
    const handler = node.props.onClick as () => void
    handler()
    return handler
  }
  async function settle() {
    // Response.json() reads a stream; allow its I/O task to complete before checking dependent state.
    await new Promise<void>(resolve => setImmediate(resolve))
    render()
  }
  render()
  return { requests, click, settle, render, button,
    summary: () => { render(); return text(tree) },
    disabled: (action: keyof typeof labels) => button(action).props.disabled,
    unmount() { mounted = false; for (const effect of effects) effect.cleanup?.() },
    writesAfterUnmount: () => writesAfterUnmount,
  }
}

const originalFetch = globalThis.fetch
try {
  const card = harness()
  assert.equal(card.requests.length, 0, 'mount must not query')
  assert.ok(card.summary().includes('Not checked / 尚未检查'))
  assert.ok(card.summary().includes('Synthetic · no exchange connection'))
  assert.ok(card.summary().includes('Separate from legacy paper/AI books and Linear Testnet.'))
  assert.equal(card.disabled('start'), true)
  assert.equal(card.disabled('stop'), true)
  const clickAgain = card.click('check')
  clickAgain()
  card.render()
  assert.equal(card.requests.length, 1, 'same-turn repeated clicks must own one request')
  for (const action of ['check', 'start', 'stop'] as const) assert.equal(card.disabled(action), true)
  const check = card.requests[0]!
  assert.equal(check.input, '/api/bybit-quant/paper')
  assert.equal(check.init.method, 'GET')
  assert.equal(check.init.credentials, 'same-origin')
  assert.equal(check.init.cache, 'no-store')
  assert.equal(check.init.body, undefined)
  check.respond(status())
  await card.settle()
  assert.equal(card.disabled('start'), false, 'idle ready:false must permit first Start')
  assert.equal(card.disabled('stop'), true)
  assert.ok(card.summary().includes('Execution ready / 执行就绪: false'))

  const startAgain = card.click('start')
  startAgain()
  card.render()
  assert.equal(card.requests.length, 2)
  const start = card.requests[1]!
  assert.equal(start.init.method, 'POST')
  assert.equal(start.init.body, '{"action":"start"}')
  assert.deepEqual(start.init.headers, { accept: 'application/json', 'content-type': 'application/json' })
  start.respond(status({ state: 'protected', native_process_alive: true }))
  await card.settle()
  assert.equal(card.disabled('start'), true)
  assert.equal(card.disabled('stop'), false, 'protected/unready native-alive must retain Stop')
  assert.ok(card.summary().includes('protected · Check status'))
  card.click('stop'); card.render()
  assert.equal(card.requests[2]!.init.body, '{"action":"stop"}')
  card.requests[2]!.respond({ ...context, ok: false, code: 'outcome_uncertain', cause: 'unavailable', recovery: { action: 'query_status' } })
  await card.settle()
  assert.ok(card.summary().includes('outcome_uncertain · Check status'))
  assert.equal(card.disabled('start'), true)
  assert.equal(card.disabled('stop'), true)
  await card.settle()
  assert.equal(card.requests.length, 3, 'uncertainty must not retry or poll')
  card.click('check'); card.render()
  assert.equal(card.requests[3]!.init.method, 'GET', 'recovery observes status')
  card.requests[3]!.respond(status({ state: 'stopping', native_process_alive: true }))
  await card.settle()
  assert.ok(card.summary().includes('cleanup is not confirmed'))
  assert.equal(card.disabled('stop'), true)

  async function observe(value: unknown) {
    card.click('check'); card.render()
    card.requests.at(-1)!.respond(value)
    await card.settle()
  }
  await observe(status({ state: 'stopped' }))
  assert.equal(card.disabled('start'), true, 'stopped service cannot restart the same session')
  assert.equal(card.disabled('stop'), true)
  await observe(status({ state: 'protected' }))
  assert.equal(card.disabled('start'), true)
  assert.equal(card.disabled('stop'), true, 'protected without native owner cannot stop or start')
  await observe(status({ state: 'running', native_process_alive: true, ready: false }))
  assert.equal(card.disabled('stop'), false, 'running unready still permits Stop')
  await observe(status({ state: 'running', native_process_alive: false }))
  assert.ok(card.summary().includes('inconsistent state/liveness'))
  assert.equal(card.disabled('start'), true)
  assert.equal(card.disabled('stop'), true)
  await observe({ ...status(), control_enabled: false })
  assert.ok(card.summary().includes('Controls enabled / 控制已启用: false'))
  assert.equal(card.disabled('start'), true)
  await observe({ ...context, configured: false, control_enabled: false, ok: false, code: 'paper_disabled' })
  assert.ok(card.summary().includes('paper_disabled'))
  assert.ok(card.summary().includes('Configured / 已配置: false'))
  assert.equal(card.disabled('start'), true)
  await observe({ ...context, ok: false, code: 'unavailable' })
  assert.equal(card.disabled('stop'), true, 'unavailable clears prior actionable state')
  await observe(status({ session_id: 'another-session' }))
  assert.ok(card.summary().includes('invalid_response'))
  assert.equal(card.disabled('start'), true, 'runtime session change must fail closed')
  await observe({ ...status(), source: 'legacy-paper' })
  assert.ok(card.summary().includes('invalid_response'))
  await observe({ ...context, ok: false, code: 'untrusted arbitrary text' })
  assert.ok(!card.summary().includes('untrusted arbitrary text'))
  await observe(status())
  card.click('start'); card.render()
  card.requests.at(-1)!.reject()
  await card.settle()
  assert.ok(card.summary().includes('outcome_uncertain'), 'lost mutation response cannot prove no side effects')
  const count = card.requests.length
  await card.settle()
  assert.equal(card.requests.length, count)
  assert.equal(card.disabled('start'), true)
  card.unmount()

  const closing = harness()
  closing.click('check'); closing.render()
  const inFlight = closing.requests[0]!
  assert.equal(inFlight.init.signal?.aborted, false)
  closing.unmount()
  assert.equal(inFlight.init.signal?.aborted, true, 'unmount must abort the owned HTTP request')
  inFlight.respond(status())
  await closing.settle()
  assert.equal(closing.writesAfterUnmount(), 0)
  assert.equal(closing.requests.length, 1, 'unmount must not send Stop')
  assert.ok(!closing.summary().includes('Session / 会话:'), 'late response must not update closed card')
  console.log('ok native-paper Client effects: demand only, scoped status, action table, one request, query-only uncertainty and unmount abort; installed browser/auth not exercised')
} finally { globalThis.fetch = originalFetch }
