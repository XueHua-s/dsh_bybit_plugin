import { randomUUID } from 'node:crypto'
import { configureBackgroundAgent, isAgentServices, safeSelection, type Agent, type AgentHandle, type AgentServices } from './ai-agent-services.js'
export { AI_LOOP_TOOL_ALLOWLIST } from './ai-agent-services.js'
export type { AgentServices } from './ai-agent-services.js'

const MIN_INTERVAL_MS = 60_000
const MAX_INTERVAL_MS = 24 * 60 * 60_000
const MAX_BACKOFF_MS = 60 * 60_000
const MAX_CONSECUTIVE_FAILURES = 3
const MAX_DECISIONS_PER_CYCLE = 4
const DEFAULT_TURN_TIMEOUT_MS = 120_000
const MAX_CLEANUP_TIMEOUT_MS = 60_000
const DEFAULT_CLEANUP_TIMEOUT_MS = 10_000

export type AiLoopState = 'disabled' | 'not_configured' | 'environment_rejected' | 'starting' | 'running' | 'idle' | 'backoff' | 'blocked' | 'stopping'
export type AiLoopEnvironment = 'testnet' | 'internal_paper' | 'demo' | 'live'
export type AiLoopDecisionStatus = 'open' | 'flat' | 'rejected' | 'uncertain'
export type AiLoopLastRun = {
  outcome: 'completed' | 'failed'
  decisionsRecorded: number
  latestDecisionId: string | null
  latestDecisionStatus: AiLoopDecisionStatus | null
  completedAt: number
}
export type AiLoopSnapshot = {
  state: AiLoopState
  enabled: boolean
  environment: AiLoopEnvironment
  intervalMs: number
  consecutiveFailures: number
  nextRunAt: number | null
  lastStartedAt: number | null
  lastCompletedAt: number | null
  lastRun: AiLoopLastRun | null
  reason: string
}
export type DecisionReceipt = {
  commit(decisionId: string, status: AiLoopDecisionStatus): { decisionId: string, status: AiLoopDecisionStatus, persistedAt: number }
  release(): void
}
export type DecisionReceiptReservation =
  | { kind: 'reserved', receipt: DecisionReceipt }
  | { kind: 'duplicate', decisionId: string, status: AiLoopDecisionStatus, persistedAt: number }
  | { kind: 'pending' }

type DeadlineResult<T> = { timedOut: false, value: T } | { timedOut: true }

type SchedulerOptions = {
  enabled: boolean
  aiEnabled: boolean
  environment: AiLoopEnvironment
  intervalMs: number
  /** Hard wall-clock ceiling for one model turn; zero is only allowed in tests. */
  turnTimeoutMs?: number
  /** Bounded wait for cancellation and handle disposal; zero is only allowed in tests. */
  cleanupTimeoutMs?: number
  /** Monotonic clock used only for the hard cycle deadline. */
  deadlineNow?: () => number
  now?: () => number
  createSessionId?: () => string
  setTimer?: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>
  clearTimer?: (timer: ReturnType<typeof setTimeout>) => void
  setTurnTimer?: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>
  clearTurnTimer?: (timer: ReturnType<typeof setTimeout>) => void
  setCleanupTimer?: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>
  clearCleanupTimer?: (timer: ReturnType<typeof setTimeout>) => void
  onError?: (message: string) => void
}

/** Bound configuration to a quiet, cancellable cadence. */
export function clampAiLoopInterval(value: number): number {
  if (!Number.isFinite(value)) return 15 * 60_000
  return Math.min(Math.max(Math.trunc(value), MIN_INTERVAL_MS), MAX_INTERVAL_MS)
}

async function withDeadline<T>(
  work: Promise<T>,
  timeoutMs: number,
  setTimer: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>,
  clearTimer: (timer: ReturnType<typeof setTimeout>) => void,
): Promise<DeadlineResult<T>> {
  if (timeoutMs === 0) return { timedOut: false, value: await work }
  let timer: ReturnType<typeof setTimeout> | undefined
  const deadline = new Promise<DeadlineResult<T>>(resolve => {
    timer = setTimer(() => resolve({ timedOut: true }), timeoutMs)
  })
  try {
    return await Promise.race([
      work.then(value => ({ timedOut: false as const, value })),
      deadline,
    ])
  } finally {
    if (timer !== undefined) clearTimer(timer)
  }
}

async function withinCycleDeadline<T>(
  work: Promise<T>,
  deadlineAt: number | undefined,
  now: () => number,
  setTimer: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>,
  clearTimer: (timer: ReturnType<typeof setTimeout>) => void,
): Promise<DeadlineResult<T>> {
  if (deadlineAt === undefined) return { timedOut: false, value: await work }
  const remainingMs = deadlineAt - now()
  if (remainingMs <= 0) {
    void work.catch(() => undefined)
    return { timedOut: true }
  }
  return withDeadline(work, remainingMs, setTimer, clearTimer)
}

/**
 * Owns one opt-in, simulated-decision wake-up loop. Each wake-up gets a fresh
 * DSH session so prior market prose cannot grow without bound across cycles.
 * Receipt keys are normalized symbols: one decision per symbol per cycle.
 */
export function createAiScheduler(options: SchedulerOptions) {
  const now = options.now ?? Date.now
  const deadlineNow = options.deadlineNow ?? (() => performance.now())
  const setTimer = options.setTimer ?? setTimeout
  const clearTimer = options.clearTimer ?? clearTimeout
  const turnTimeoutMs = options.turnTimeoutMs === 0
    ? 0
    : Math.min(Math.max(Math.trunc(options.turnTimeoutMs ?? DEFAULT_TURN_TIMEOUT_MS), 5_000), 10 * 60_000)
  const cleanupTimeoutMs = options.cleanupTimeoutMs === 0
    ? 0
    : Math.min(Math.max(Math.trunc(options.cleanupTimeoutMs ?? DEFAULT_CLEANUP_TIMEOUT_MS), 1_000), MAX_CLEANUP_TIMEOUT_MS)
  const setTurnTimer = options.setTurnTimer ?? setTimeout
  const clearTurnTimer = options.clearTurnTimer ?? clearTimeout
  const setCleanupTimer = options.setCleanupTimer ?? setTurnTimer
  const clearCleanupTimer = options.clearCleanupTimer ?? clearTurnTimer
  const intervalMs = clampAiLoopInterval(options.intervalMs)
  const environmentAllowed = options.environment === 'testnet' || options.environment === 'internal_paper'
  let state: AiLoopState = !options.enabled || !options.aiEnabled ? 'disabled' : !environmentAllowed ? 'environment_rejected' : 'not_configured'
  let reason = !options.enabled ? 'disabled_by_default' : !options.aiEnabled ? 'ai_track_disabled' : !environmentAllowed ? 'environment_not_allowed' : 'waiting_for_optional_agent_services'
  let services: AgentServices | undefined
  let timer: ReturnType<typeof setTimeout> | undefined
  let activeHandle: AgentHandle | undefined
  let activeController: AbortController | undefined
  let activeRun: Promise<void> | undefined
  let disposed = false
  let consecutiveFailures = 0
  let nextRunAt: number | null = null
  let lastStartedAt: number | null = null
  let lastCompletedAt: number | null = null
  let lastRun: AiLoopLastRun | null = null
  let activeCycle: {
    id: string
    pendingReceipts: number
    decisions: Array<{ decisionId: string, status: AiLoopDecisionStatus }>
    receipts: Map<string, { state: 'pending' } | { state: 'committed', decisionId: string, status: AiLoopDecisionStatus, persistedAt: number }>
    closed: boolean
  } | undefined
  let disposal: Promise<void> | undefined
  let cleanupUncertain = false
  const cancelledHandles = new WeakSet<AgentHandle>()
  const handleCleanup = new WeakMap<AgentHandle, Promise<boolean>>()

  function cancel(handle: AgentHandle): void {
    if (cancelledHandles.has(handle)) return
    cancelledHandles.add(handle)
    try { handle.agent.cancel({ kind: 'disposed' }) } catch { /* active work is still awaited */ }
  }

  function clearScheduled(): void {
    if (timer !== undefined) clearTimer(timer)
    timer = undefined
    nextRunAt = null
  }

  async function waitForIdle(agent: Agent): Promise<boolean> {
    try {
      return !(await withDeadline(agent.whenIdle(), cleanupTimeoutMs, setCleanupTimer, clearCleanupTimer)).timedOut
    } catch { return false }
  }

  function disposeHandle(handle: AgentHandle, cancelFirst: boolean): Promise<boolean> {
    if (cancelFirst) cancel(handle)
    const previous = handleCleanup.get(handle)
    if (previous !== undefined) return previous
    const cleanup = (async () => {
      if (!await waitForIdle(handle.agent)) return false
      try {
        const result = await withDeadline(handle.dispose(), cleanupTimeoutMs, setCleanupTimer, clearCleanupTimer)
        return !result.timedOut
      } catch { return false }
    })()
    handleCleanup.set(handle, cleanup)
    return cleanup
  }

  function blockForUncertainCleanup(): void {
    cleanupUncertain = true
    if (disposed) return
    state = 'blocked'
    reason = 'agent_cleanup_unconfirmed'
    clearScheduled()
  }

  function recoverAfterLateCreate(delayMs: number): void {
    if (disposed) return
    cleanupUncertain = false
    if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
      state = 'blocked'
      reason = 'three_consecutive_agent_cycle_failures'
      return
    }
    state = 'backoff'
    reason = 'agent_creation_or_turn_failed'
    schedule(delayMs)
  }

  function snapshot(): AiLoopSnapshot {
    return {
      state, enabled: options.enabled, environment: options.environment, intervalMs,
      consecutiveFailures, nextRunAt, lastStartedAt, lastCompletedAt, reason,
      lastRun,
    }
  }

  /**
   * Reserve one normalized decision fingerprint for this cycle. The key is
   * supplied by the tool boundary, where the decision schema has already been
   * normalized. Keeping the set here makes concurrent tool calls idempotent
   * without leaking decision-shape knowledge into the scheduler.
   */
  function reserveDecisionReceipt(cycleId: string, decisionKey: string): DecisionReceiptReservation | undefined {
    const cycle = activeCycle
    if (cycle === undefined || cycle.id !== cycleId || cycle.closed || state === 'blocked') return undefined
    const previous = cycle.receipts.get(decisionKey)
    if (previous?.state === 'pending') return { kind: 'pending' }
    if (previous?.state === 'committed') {
      return {
        kind: 'duplicate',
        decisionId: previous.decisionId,
        status: previous.status,
        persistedAt: previous.persistedAt,
      }
    }
    if (cycle.decisions.length + cycle.pendingReceipts >= MAX_DECISIONS_PER_CYCLE) return undefined
    cycle.pendingReceipts += 1
    cycle.receipts.set(decisionKey, { state: 'pending' })
    let committedReceipt: { decisionId: string, status: AiLoopDecisionStatus, persistedAt: number } | undefined
    let released = false
    return { kind: 'reserved', receipt: {
      commit(decisionId, status) {
        if (committedReceipt !== undefined) return committedReceipt
        if (released) throw new Error('decision receipt reservation was released')
        const persistedAt = now()
        committedReceipt = { decisionId, status, persistedAt }
        cycle.pendingReceipts -= 1
        cycle.receipts.set(decisionKey, { state: 'committed', decisionId, status, persistedAt })
        cycle.decisions.push({ decisionId, status })
        // A paper dispatch that is admitted/protected/unknown is not a fill.
        // Stop the unattended loop until an operator can reconcile the
        // original request; scheduling another cycle could compound an
        // unknown position.
        if (status === 'uncertain') {
          state = 'blocked'
          reason = 'paper_outcome_uncertain'
          clearScheduled()
        }
        return committedReceipt
      },
      release() {
        if (committedReceipt !== undefined || released) return
        released = true
        cycle.pendingReceipts -= 1
        cycle.receipts.delete(decisionKey)
      },
    } }
  }

  function summarizeRun(cycle: NonNullable<typeof activeCycle>, outcome: AiLoopLastRun['outcome']): AiLoopLastRun {
    return {
      outcome,
      decisionsRecorded: cycle.decisions.length,
      latestDecisionId: cycle.decisions.at(-1)?.decisionId ?? null,
      latestDecisionStatus: cycle.decisions.at(-1)?.status ?? null,
      completedAt: now(),
    }
  }

  function schedule(delayMs: number): void {
    if (disposed || state === 'environment_rejected' || state === 'blocked' || !options.enabled || !options.aiEnabled || services === undefined) return
    if (timer !== undefined) clearTimer(timer)
    nextRunAt = now() + delayMs
    timer = setTimer(() => {
      timer = undefined
      nextRunAt = null
      if (activeRun !== undefined) return
      const run = tick()
      activeRun = run
      void run.finally(() => {
        if (activeRun === run) activeRun = undefined
      })
    }, delayMs)
  }

  function configure(value: unknown): void {
    if (disposed || !options.enabled || !environmentAllowed || !options.aiEnabled) return
    if (state === 'blocked') return
    if (!isAgentServices(value) || safeSelection(value) === undefined) {
      services = undefined
      clearScheduled()
      state = 'not_configured'
      reason = !isAgentServices(value) ? 'optional_agent_services_unavailable' : 'default_model_route_unavailable'
      return
    }
    services = value
    if (activeRun !== undefined) return
    state = 'idle'
    reason = 'configured'
    schedule(0)
  }

  async function tick(): Promise<void> {
    const configured = services
    if (disposed || configured === undefined || activeHandle !== undefined) return
    const selection = safeSelection(configured)
    if (selection === undefined) {
      state = 'not_configured'
      reason = 'default_model_route_unavailable'
      return
    }

    state = 'starting'
    reason = 'agent_session_starting'
    lastStartedAt = now()
    const cycle = {
      id: (options.createSessionId ?? randomUUID)(),
      pendingReceipts: 0,
      decisions: [] as Array<{ decisionId: string, status: AiLoopDecisionStatus }>,
      receipts: new Map(),
      closed: false,
    }
    activeCycle = cycle
    const controller = new AbortController()
    activeController = controller
    const cycleDeadlineAt = turnTimeoutMs === 0 ? undefined : deadlineNow() + turnTimeoutMs
    let handle: AgentHandle | undefined
    let creationTimedOut = false
    let nextDelay = intervalMs
    try {
      const creation = configured.agents.create({
        sessionId: cycle.id,
        agentOptions: { ...selection, maxTokens: 1600 },
        signal: controller.signal,
        setup(context) {
          configureBackgroundAgent(context, cycle.id)
        },
      })
      const created = await withinCycleDeadline(creation, cycleDeadlineAt, deadlineNow, setTurnTimer, clearTurnTimer)
      if (created.timedOut) {
        creationTimedOut = true
        controller.abort()
        blockForUncertainCleanup()
        void creation.then(async lateHandle => {
          if (await disposeHandle(lateHandle, true)) recoverAfterLateCreate(nextDelay)
          else blockForUncertainCleanup()
        }, () => recoverAfterLateCreate(nextDelay)).catch(() => blockForUncertainCleanup())
        throw new Error('agent_creation_timeout')
      }
      handle = created.value
      activeHandle = handle
      if (disposed) return
      state = 'running'
      reason = 'agent_turn_in_progress'
      handle.agent.followup({
        content: [{ type: 'text', text: 'Run the bounded simulated decision cycle using the fixed plugin instructions.' }],
        source: { kind: 'my-plugin' },
      })
      const turn = await withinCycleDeadline(handle.agent.whenIdle(), cycleDeadlineAt, deadlineNow, setTurnTimer, clearTurnTimer)
      if (turn.timedOut) {
        cancel(handle)
        throw new Error('agent_turn_timeout')
      }
      if (disposed) return
      consecutiveFailures = 0
      lastCompletedAt = now()
      lastRun = summarizeRun(cycle, 'completed')
      if (snapshot().state !== 'blocked') {
        state = 'idle'
        reason = cycle.decisions.length === 0
          ? 'agent_turn_completed_without_simulated_decision_receipt'
          : 'agent_turn_completed_with_simulated_decision_receipt'
      }
    } catch {
      if (disposed) return
      consecutiveFailures += 1
      lastCompletedAt = now()
      lastRun = summarizeRun(cycle, 'failed')
      if (cleanupUncertain) {
        state = 'blocked'
        reason = creationTimedOut ? 'agent_creation_timeout_cleanup_pending' : 'agent_cleanup_unconfirmed'
      } else if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
        state = 'blocked'
        reason = 'three_consecutive_agent_cycle_failures'
      } else {
        state = 'backoff'
      reason = 'agent_creation_or_turn_failed'
        const multiplier = 2 ** Math.min(consecutiveFailures - 1, 20)
        nextDelay = Math.min(intervalMs * multiplier, MAX_BACKOFF_MS)
      }
      try { options.onError?.(reason) } catch { /* reporting must not break scheduler cleanup */ }
    } finally {
      cycle.closed = true
      if (activeCycle === cycle) activeCycle = undefined
      if (handle !== undefined) {
        const cleaned = await disposeHandle(handle, disposed || creationTimedOut)
        if (!cleaned && !disposed) blockForUncertainCleanup()
      }
      if (activeHandle === handle) activeHandle = undefined
      if (activeController === controller) activeController = undefined
      const currentState = snapshot().state
      if (!disposed && !cleanupUncertain && currentState !== 'not_configured' && currentState !== 'blocked') schedule(nextDelay)
    }
  }

  function dispose(): Promise<void> {
    if (disposal !== undefined) return disposal
    disposed = true
    state = 'stopping'
    reason = 'plugin_unloading'
    clearScheduled()
    activeController?.abort()
    if (activeHandle !== undefined) cancel(activeHandle)
    disposal = (async () => {
      const shutdown = (async () => {
        await activeRun?.catch(() => undefined)
        const handle = activeHandle
        if (handle === undefined) return
        if (!await disposeHandle(handle, true)) blockForUncertainCleanup()
        if (activeHandle === handle) activeHandle = undefined
      })()
      const result = await withDeadline(shutdown, cleanupTimeoutMs, setCleanupTimer, clearCleanupTimer)
      if (result.timedOut) {
        cleanupUncertain = true
        try { options.onError?.('agent_shutdown_cleanup_unconfirmed') } catch { /* reporting must not block unload */ }
      }
    })()
    return disposal
  }

  return { configure, snapshot, reserveDecisionReceipt, dispose }
}
