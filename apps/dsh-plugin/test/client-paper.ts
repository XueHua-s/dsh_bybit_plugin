import assert from 'node:assert/strict'
import * as React from 'react'
import { paperPanel } from '../src/client-paper.ts'
import type { PaperStatus } from '@bybit-quant/quant-api-client'
import type { PaperStatusResult } from '../src/lib/engine-paper.js'

type Cleanup = void | (() => void)
type Effect = { deps: readonly unknown[] | undefined, cleanup: Cleanup }
type RequestRecord = { input: string, init: RequestInit, respond(value: unknown, status?: number): void }
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

/** Runs the real observation effect with stable hook slots and a controlled browser transport. */
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
  globalThis.fetch = (input, init = {}) => new Promise<Response>(resolve => {
    assert.equal(typeof input, 'string')
    requests.push({ input: String(input), init, respond: (value, code = 200) => resolve(new Response(JSON.stringify(value), { status: code, headers: { 'content-type': 'application/json' } })) })
  })
  function check(repeat = false) {
    render()
    const node = elements(tree).find(candidate => candidate.type === 'button' && text(candidate) === 'Check status / 检查状态')
    assert.ok(node, 'read-only status button is present')
    assert.equal(node.props.disabled, false)
    const handler = node.props.onClick as () => void
    handler()
    if (repeat) handler()
    return node
  }
  async function settle() {
    await new Promise<void>(resolve => setImmediate(resolve))
    render()
  }
  render()
  return { requests, check, settle, render, summary: () => { render(); return text(tree) },
    unmount() { mounted = false; for (const effect of effects) effect.cleanup?.() },
    writesAfterUnmount: () => writesAfterUnmount }
}

const originalFetch = globalThis.fetch
try {
  const card = harness()
  assert.equal(card.requests.length, 0, 'mount is passive and does not start or poll a service')
  assert.ok(card.summary().includes('Not checked / 尚未检查'))
  assert.ok(card.summary().includes('Synthetic · no exchange connection'))
  assert.ok(card.summary().includes('Status is observation-only'))
  assert.ok(!card.summary().includes('Start paper'))
  assert.ok(!card.summary().includes('Stop paper'))
  card.check(true); card.render()
  assert.equal(card.requests.length, 1, 'rapid repeated status checks share one request')
  const request = card.requests[0]!
  assert.equal(request.input, '/api/bybit-quant/paper')
  assert.equal(request.init.method, 'GET')
  assert.equal(request.init.credentials, 'same-origin')
  assert.equal(request.init.cache, 'no-store')
  assert.equal(request.init.body, undefined)
  request.respond(status())
  await card.settle()
  assert.ok(card.summary().includes('Execution ready / 执行就绪: false'))
  assert.ok(!card.summary().includes('Start paper'))
  assert.ok(!card.summary().includes('Stop paper'))

  card.check(); card.render()
  card.requests.at(-1)!.respond(status({ session_id: 'another-session' }))
  await card.settle()
  assert.ok(card.summary().includes('invalid_response'))

  card.check(); card.render()
  card.requests.at(-1)!.respond({ ...context, ok: false, code: 'unavailable' })
  await card.settle()
  assert.ok(card.summary().includes('unavailable'))
  card.unmount()

  const closing = harness()
  closing.check(); closing.render()
  const inFlight = closing.requests[0]!
  assert.equal(inFlight.init.signal?.aborted, false)
  closing.unmount()
  assert.equal(inFlight.init.signal?.aborted, true, 'unmount aborts only the status request')
  inFlight.respond(status())
  await closing.settle()
  assert.equal(closing.writesAfterUnmount(), 0)
  assert.equal(closing.requests.length, 1, 'unmount cannot send Stop')
  console.log('ok native-paper Client: observation-only GET, no controls or auto-poll, bounded status validation and unmount abort')
} finally { globalThis.fetch = originalFetch }
