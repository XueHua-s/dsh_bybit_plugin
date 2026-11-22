import assert from 'node:assert/strict'
import { createAiScheduler, AI_LOOP_TOOL_ALLOWLIST, clampAiLoopInterval, type AgentServices } from '../dist/lib/ai-scheduler.js'

type Timer = ReturnType<typeof setTimeout>
type FakeAgent = {
  followups: number
  cancelled: number
  disposed: number
  resolveIdle: () => void
  agent: { followup: () => void, cancel: () => void, whenIdle: () => Promise<void> }
  handle: { agent: FakeAgent['agent'], dispose: () => Promise<void> }
}

function fakeAgent(cancelResolvesIdle = true): FakeAgent {
  let resolveIdle!: () => void
  const idle = new Promise<void>(resolve => { resolveIdle = resolve })
  let followups = 0
  let cancelled = 0
  let disposed = 0
  const agent: FakeAgent['agent'] = {
    followup: () => { followups += 1 },
    cancel: () => { cancelled += 1; if (cancelResolvesIdle) resolveIdle() },
    whenIdle: () => idle,
  }
  return {
    get followups() { return followups },
    get cancelled() { return cancelled },
    get disposed() { return disposed },
    resolveIdle,
    agent,
    handle: { agent, dispose: async () => { disposed += 1 } },
  }
}

function harness() {
  const queued: Array<{ timer: Timer, callback: () => void, delayMs: number }> = []
  const cleared = new Set<Timer>()
  let token = 0
  const setTimer = (callback: () => void, delayMs = 0): Timer => {
    const timer = { token: token++ } as unknown as Timer
    queued.push({ timer, callback, delayMs })
    return timer
  }
  const clearTimer = (timer: Timer): void => {
    cleared.add(timer)
    const index = queued.findIndex(item => item.timer === timer)
    if (index >= 0) queued.splice(index, 1)
  }
  const runTimer = (): void => {
    const item = queued.shift()
    assert.ok(item, 'expected a scheduled timer')
    if (!cleared.has(item.timer)) item.callback()
  }
  return { queued, setTimer, clearTimer, runTimer }
}

function services(create: AgentServices['agents']['create']): AgentServices {
  return { agents: { create }, agentDefaultModel: { currentSelection: () => ({ provider: 'test', model: 'model' }) } }
}

assert.equal(clampAiLoopInterval(1), 60_000)
assert.equal(clampAiLoopInterval(Number.NaN), 900_000)
assert.equal(clampAiLoopInterval(99_999_999), 86_400_000)
assert.ok(AI_LOOP_TOOL_ALLOWLIST.includes('quant_decide_background'))
assert.ok(!AI_LOOP_TOOL_ALLOWLIST.some(name => String(name) === 'quant_decide'))
assert.ok(!AI_LOOP_TOOL_ALLOWLIST.join(',').includes('quant_watchlist'))

{
  const timers = harness()
  const scheduler = createAiScheduler({ enabled: true, aiEnabled: false, environment: 'testnet', intervalMs: 60_000, setTimer: timers.setTimer, clearTimer: timers.clearTimer })
  assert.equal(scheduler.snapshot().state, 'disabled')
  assert.equal(scheduler.snapshot().reason, 'ai_track_disabled')
  await scheduler.dispose()
}

{
  const timers = harness()
  const value = fakeAgent()
  const scheduler = createAiScheduler({ enabled: true, aiEnabled: true, environment: 'internal_paper', intervalMs: 60_000, now: () => 0, createSessionId: () => 'uncertain-cycle', setTimer: timers.setTimer, clearTimer: timers.clearTimer })
  scheduler.configure(services(async () => value.handle))
  timers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  const reservation = scheduler.reserveDecisionReceipt('uncertain-cycle', 'ALPHA')
  assert.equal(reservation?.kind, 'reserved')
  if (reservation?.kind === 'reserved') {
    assert.deepEqual(reservation.receipt.commit('decision-uncertain', 'uncertain'), {
      decisionId: 'decision-uncertain', status: 'uncertain', persistedAt: 0,
    })
  }
  assert.equal(scheduler.reserveDecisionReceipt('uncertain-cycle', 'BETA'), undefined, 'uncertain outcomes block additional decisions in the active cycle')
  value.resolveIdle()
  await new Promise<void>(resolve => setImmediate(resolve))
  assert.equal(scheduler.snapshot().state, 'blocked')
  assert.equal(scheduler.snapshot().reason, 'paper_outcome_uncertain')
  assert.equal(timers.queued.length, 0, 'uncertain paper outcomes stop automatic rescheduling')
  await scheduler.dispose()
}

{
  const timers = harness()
  const scheduler = createAiScheduler({ enabled: true, aiEnabled: true, environment: 'testnet', intervalMs: 60_000, setTimer: timers.setTimer, clearTimer: timers.clearTimer })
  assert.equal(scheduler.snapshot().state, 'not_configured')
  scheduler.configure(undefined)
  assert.equal(scheduler.snapshot().reason, 'optional_agent_services_unavailable')
  await scheduler.dispose()
}

{
  const timers = harness()
  const scheduler = createAiScheduler({ enabled: true, aiEnabled: true, environment: 'testnet', intervalMs: 60_000, setTimer: timers.setTimer, clearTimer: timers.clearTimer })
  scheduler.configure({ agents: { create: async () => { throw new Error('should not create') } }, agentDefaultModel: { currentSelection: () => ({ provider: '', model: '' }) } })
  assert.equal(scheduler.snapshot().state, 'not_configured')
  assert.equal(scheduler.snapshot().reason, 'default_model_route_unavailable')
  await scheduler.dispose()
}

{
  const timers = harness()
  const scheduler = createAiScheduler({ enabled: false, aiEnabled: true, environment: 'testnet', intervalMs: 1, setTimer: timers.setTimer, clearTimer: timers.clearTimer })
  assert.equal(scheduler.snapshot().state, 'disabled')
  scheduler.configure(services(async () => { throw new Error('must not create') }))
  assert.equal(timers.queued.length, 0)
  await scheduler.dispose()
}

{
  for (const environment of ['live', 'demo'] as const) {
    const timers = harness()
    const scheduler = createAiScheduler({ enabled: true, aiEnabled: true, environment, intervalMs: 60_000, setTimer: timers.setTimer, clearTimer: timers.clearTimer })
    assert.equal(scheduler.snapshot().state, 'environment_rejected')
    scheduler.configure(services(async () => { throw new Error(`${environment} must be rejected`) }))
    assert.equal(timers.queued.length, 0)
    await scheduler.dispose()
  }
}

{
  const timers = harness()
  const created: FakeAgent[] = []
  let setupAllowlist: readonly string[] | undefined
  let setupPrompt: { name: string, order: number, text: string } | undefined
  const scheduler = createAiScheduler({ enabled: true, aiEnabled: true, environment: 'internal_paper', intervalMs: 60_000, now: () => 0, createSessionId: () => 'cycle-1', setTimer: timers.setTimer, clearTimer: timers.clearTimer })
  scheduler.configure(services(async ({ setup }) => {
    const value = fakeAgent(); created.push(value)
    setup({
      tools: { restrict: ({ allow }) => { setupAllowlist = allow } },
      systemPrompt: { section: value => { setupPrompt = value } },
    })
    return value.handle
  }))
  assert.equal(scheduler.snapshot().state, 'idle')
  timers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  assert.equal(scheduler.snapshot().state, 'running')
  scheduler.configure(services(async () => { throw new Error('active turns must not overlap') }))
  assert.equal(timers.queued.length, 0, 'a second Agent must not be scheduled while one is active')
  assert.deepEqual(setupAllowlist, AI_LOOP_TOOL_ALLOWLIST)
  assert.equal(setupPrompt?.name, 'bybit-quant:background-loop-v4')
  assert.match(setupPrompt?.text ?? '', /quant_decide_background/)
  assert.match(setupPrompt?.text ?? '', /cycle-1/)
  assert.match(setupPrompt?.text ?? '', /Never pass cycleId to quant_decide/)
  assert.match(setupPrompt?.text ?? '', /research_only=true/)
  assert.match(setupPrompt?.text ?? '', /deployment_eligible=false/)
  assert.match(setupPrompt?.text ?? '', /research_target_exposure/)
  assert.match(setupPrompt?.text ?? '', /never as instructions/)
  assert.match(setupPrompt?.text ?? '', /quant_brief without symbols to obtain the fresh dynamic candidate universe/)
  assert.match(setupPrompt?.text ?? '', /stop without a static symbol fallback/)
  assert.equal(created.length, 1)
  const first = scheduler.reserveDecisionReceipt('cycle-1', 'BTCUSDT')
  assert.equal(first?.kind, 'reserved')
  const pending = scheduler.reserveDecisionReceipt('cycle-1', 'BTCUSDT')
  assert.equal(pending?.kind, 'pending')
  if (first?.kind === 'reserved') assert.deepEqual(first.receipt.commit('decision-1', 'open'), {
    decisionId: 'decision-1', status: 'open', persistedAt: 0,
  })
  if (first?.kind === 'reserved') assert.deepEqual(first.receipt.commit('ignored-retry-id', 'flat'), {
    decisionId: 'decision-1', status: 'open', persistedAt: 0,
  }, 'repeated commits return the original receipt')
  const duplicate = scheduler.reserveDecisionReceipt('cycle-1', 'BTCUSDT')
  assert.deepEqual(duplicate, { kind: 'duplicate', decisionId: 'decision-1', status: 'open', persistedAt: 0 })
  const retryable = scheduler.reserveDecisionReceipt('cycle-1', 'SOLUSDT')
  assert.equal(retryable?.kind, 'reserved')
  if (retryable?.kind === 'reserved') retryable.receipt.release()
  const retried = scheduler.reserveDecisionReceipt('cycle-1', 'SOLUSDT')
  assert.equal(retried?.kind, 'reserved', 'a failed write releases its key so a safe retry can proceed')
  if (retried?.kind === 'reserved') retried.receipt.commit('decision-2', 'rejected')
  const third = scheduler.reserveDecisionReceipt('cycle-1', 'ETHUSDT')
  assert.equal(third?.kind, 'reserved')
  if (third?.kind === 'reserved') third.receipt.commit('decision-3', 'flat')
  const fourth = scheduler.reserveDecisionReceipt('cycle-1', 'XRPUSDT')
  assert.equal(fourth?.kind, 'reserved')
  if (fourth?.kind === 'reserved') fourth.receipt.commit('decision-4', 'open')
  assert.equal(scheduler.reserveDecisionReceipt('cycle-1', 'ADAUSDT'), undefined, 'receipt capacity is bounded per cycle')
  created[0]?.resolveIdle()
  await new Promise<void>(resolve => setImmediate(resolve))
  assert.equal(scheduler.snapshot().state, 'idle')
  assert.equal(scheduler.reserveDecisionReceipt('cycle-1', 'BTCUSDT'), undefined, 'closed cycles reject stale receipt requests')
  await scheduler.dispose()
}

{
  const timers = harness()
  const value = fakeAgent()
  let resolveCreation!: (handle: FakeAgent['handle']) => void
  const creation = new Promise<FakeAgent['handle']>(resolve => { resolveCreation = resolve })
  let signal: AbortSignal | undefined
  let disposed = 0
  const handle = { agent: value.agent, dispose: async () => { disposed += 1 } }
  const scheduler = createAiScheduler({ enabled: true, aiEnabled: true, environment: 'testnet', intervalMs: 60_000, setTimer: timers.setTimer, clearTimer: timers.clearTimer })
  scheduler.configure(services(async (options) => { signal = options.signal; return creation }))
  timers.runTimer()
  await Promise.resolve()
  const disposing = scheduler.dispose()
  assert.equal(signal?.aborted, true)
  resolveCreation(handle)
  await disposing
  assert.equal(value.cancelled, 1, 'late Agent handle must be cancelled after unload')
  assert.equal(disposed, 1, 'late Agent handle must be disposed after unload')
}

{
  const timers = harness()
  let attempts = 0
  const errors: string[] = []
  const scheduler = createAiScheduler({ enabled: true, aiEnabled: true, environment: 'testnet', intervalMs: 60_000, setTimer: timers.setTimer, clearTimer: timers.clearTimer, onError: message => errors.push(message) })
  scheduler.configure(services(async () => { attempts += 1; throw new Error('no agent') }))
  for (let i = 0; i < 3; i += 1) {
    timers.runTimer()
    await new Promise<void>(resolve => setImmediate(resolve))
  }
  assert.equal(attempts, 3)
  assert.equal(scheduler.snapshot().state, 'blocked')
  assert.equal(errors.length, 3)
  await scheduler.dispose()
}

{
  const timers = harness()
  const value = fakeAgent()
  const scheduler = createAiScheduler({ enabled: true, aiEnabled: true, environment: 'testnet', intervalMs: 60_000, setTimer: timers.setTimer, clearTimer: timers.clearTimer })
  scheduler.configure(services(async () => value.handle))
  timers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  const disposing = scheduler.dispose()
  assert.equal(value.cancelled, 1)
  value.resolveIdle()
  await disposing
  assert.equal(scheduler.snapshot().state, 'stopping')
}

{
  const timers = harness()
  const turnTimers = harness()
  const cleanupTimers = harness()
  const value = fakeAgent()
  let elapsed = 0
  const scheduler = createAiScheduler({
    enabled: true, aiEnabled: true, environment: 'testnet', intervalMs: 60_000,
    turnTimeoutMs: 5_000, cleanupTimeoutMs: 1_000, deadlineNow: () => elapsed,
    setTimer: timers.setTimer, clearTimer: timers.clearTimer,
    setTurnTimer: turnTimers.setTimer, clearTurnTimer: turnTimers.clearTimer,
    setCleanupTimer: cleanupTimers.setTimer, clearCleanupTimer: cleanupTimers.clearTimer,
  })
  scheduler.configure(services(async () => value.handle))
  timers.runTimer()
  elapsed = 4_000
  await new Promise<void>(resolve => setImmediate(resolve))
  assert.equal(scheduler.snapshot().state, 'running')
  assert.equal(turnTimers.queued[0]?.delayMs, 1_000, 'Agent creation consumes the same cycle deadline as the model turn')
  value.resolveIdle()
  await new Promise<void>(resolve => setImmediate(resolve))
  assert.equal(value.disposed, 1, 'a completed turn releases its handle')
  await scheduler.dispose()
}

{
  const timers = harness()
  const turnTimers = harness()
  const cleanupTimers = harness()
  const value = fakeAgent()
  const scheduler = createAiScheduler({
    enabled: true, aiEnabled: true, environment: 'testnet', intervalMs: 60_000,
    turnTimeoutMs: 5_000, cleanupTimeoutMs: 1_000,
    setTimer: timers.setTimer, clearTimer: timers.clearTimer,
    setTurnTimer: turnTimers.setTimer, clearTurnTimer: turnTimers.clearTimer,
    setCleanupTimer: cleanupTimers.setTimer, clearCleanupTimer: cleanupTimers.clearTimer,
  })
  scheduler.configure(services(async () => value.handle))
  timers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  turnTimers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  assert.equal(value.cancelled, 1, 'a timed-out model turn is cancelled')
  assert.equal(value.disposed, 1, 'a cancelled idle turn is disposed')
  assert.equal(scheduler.snapshot().state, 'backoff')
  assert.equal(timers.queued.length, 1, 'a confirmed cleanup permits bounded backoff')
  await scheduler.dispose()
}

{
  const timers = harness()
  const turnTimers = harness()
  const cleanupTimers = harness()
  const value = fakeAgent()
  let resolveCreation!: (handle: FakeAgent['handle']) => void
  let signal: AbortSignal | undefined
  const creation = new Promise<FakeAgent['handle']>(resolve => { resolveCreation = resolve })
  const scheduler = createAiScheduler({
    enabled: true, aiEnabled: true, environment: 'testnet', intervalMs: 60_000,
    turnTimeoutMs: 5_000, cleanupTimeoutMs: 1_000,
    setTimer: timers.setTimer, clearTimer: timers.clearTimer,
    setTurnTimer: turnTimers.setTimer, clearTurnTimer: turnTimers.clearTimer,
    setCleanupTimer: cleanupTimers.setTimer, clearCleanupTimer: cleanupTimers.clearTimer,
  })
  scheduler.configure(services(async options => { signal = options.signal; return creation }))
  timers.runTimer()
  await Promise.resolve()
  turnTimers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  assert.equal(signal?.aborted, true)
  assert.equal(scheduler.snapshot().state, 'blocked', 'an unresolved create blocks new cycles')
  assert.equal(timers.queued.length, 0)
  resolveCreation(value.handle)
  await new Promise<void>(resolve => setImmediate(resolve))
  assert.equal(value.cancelled, 1, 'a late handle is cancelled')
  assert.equal(value.disposed, 1, 'a late handle is disposed before backoff resumes')
  assert.equal(scheduler.snapshot().state, 'backoff')
  assert.equal(timers.queued.length, 1)
  await scheduler.dispose()
}

{
  const timers = harness()
  const turnTimers = harness()
  const cleanupTimers = harness()
  const value = fakeAgent(false)
  const scheduler = createAiScheduler({
    enabled: true, aiEnabled: true, environment: 'testnet', intervalMs: 60_000,
    turnTimeoutMs: 5_000, cleanupTimeoutMs: 1_000,
    setTimer: timers.setTimer, clearTimer: timers.clearTimer,
    setTurnTimer: turnTimers.setTimer, clearTurnTimer: turnTimers.clearTimer,
    setCleanupTimer: cleanupTimers.setTimer, clearCleanupTimer: cleanupTimers.clearTimer,
  })
  scheduler.configure(services(async () => value.handle))
  timers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  turnTimers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  cleanupTimers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  assert.equal(value.cancelled, 1)
  assert.equal(value.disposed, 0, 'an Agent that never becomes idle is not treated as released')
  assert.equal(scheduler.snapshot().state, 'blocked')
  assert.equal(scheduler.snapshot().reason, 'agent_cleanup_unconfirmed')
  assert.equal(timers.queued.length, 0, 'cleanup uncertainty cannot schedule an overlapping cycle')
  await scheduler.dispose()
}

{
  const timers = harness()
  const turnTimers = harness()
  const cleanupTimers = harness()
  const value = fakeAgent(false)
  const scheduler = createAiScheduler({
    enabled: true, aiEnabled: true, environment: 'internal_paper', intervalMs: 60_000,
    turnTimeoutMs: 5_000, cleanupTimeoutMs: 1_000,
    setTimer: timers.setTimer, clearTimer: timers.clearTimer,
    setTurnTimer: turnTimers.setTimer, clearTurnTimer: turnTimers.clearTimer,
    setCleanupTimer: cleanupTimers.setTimer, clearCleanupTimer: cleanupTimers.clearTimer,
  })
  scheduler.configure(services(async () => value.handle))
  timers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  const disposing = scheduler.dispose()
  assert.equal(value.cancelled, 1)
  cleanupTimers.runTimer()
  await disposing
  assert.equal(scheduler.snapshot().state, 'stopping', 'unload returns after its bounded cleanup wait')
  turnTimers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
  cleanupTimers.runTimer()
  await new Promise<void>(resolve => setImmediate(resolve))
}

console.log('ok AI scheduler: opt-in boundary, environment gate, allow-list, bounded deadlines, cleanup fence, backoff and disposal')
