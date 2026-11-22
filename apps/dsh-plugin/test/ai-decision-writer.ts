import assert from 'node:assert/strict'
import { createTrack } from '../dist/lib/ai.js'
import { persistAiDecision } from '../dist/lib/ai-decision-writer.js'
import { initialState, type StateDocument, type Store } from '../dist/lib/state.js'
import type { DecisionReceipt } from '../src/lib/ai-scheduler.js'

function makeStore(shouldFail: () => boolean, events: string[]): { store: Store, state: StateDocument } {
  const state = initialState(1000, 1)
  const store: Store = {
    get: () => state,
    file: 'memory://decision-writer-test',
    mutate<T>(change: (document: StateDocument) => T): T {
      const result = change(state)
      events.push('store-write')
      if (shouldFail()) throw new Error('simulated state-file write failure')
      return result
    },
  }
  return { store, state }
}

function receipt(events: string[]): DecisionReceipt {
  return {
    commit(decisionId, status) {
      events.push('receipt-commit')
      return { decisionId, status, persistedAt: 2 }
    },
    release() {
      events.push('receipt-release')
    },
  }
}

{
  const events: string[] = []
  const { store, state } = makeStore(() => true, events)
  const previousTrack = createTrack(1000, 1)
  state.ai = previousTrack
  const nextTrack = createTrack(900, 2)

  assert.throws(
    () => persistAiDecision({
      store, previousTrack, nextTrack, decisionId: 'decision-failed', status: 'open', receipt: receipt(events),
    }),
    /simulated state-file write failure/,
  )
  assert.strictEqual(state.ai, previousTrack, 'failed persistence restores the shared AI track')
  assert.deepEqual(events, ['store-write'], 'a receipt is not committed when the store write fails')
}

{
  const state = initialState(1000, 1)
  const previousTrack = createTrack(1000, 1)
  const nextTrack = createTrack(900, 2)
  const newerTrack = createTrack(1100, 3)
  state.ai = previousTrack
  const store: Store = {
    get: () => state,
    file: 'memory://decision-writer-concurrent-failure',
    mutate<T>(change: (document: StateDocument) => T): T {
      change(state)
      state.ai = newerTrack
      throw new Error('simulated concurrent state-file failure')
    },
  }

  assert.throws(
    () => persistAiDecision({ store, previousTrack, nextTrack, decisionId: 'decision-race', status: 'open' }),
    /simulated concurrent state-file failure/,
  )
  assert.strictEqual(state.ai, newerTrack, 'rollback does not overwrite a newer state')
}

{
  const events: string[] = []
  const { store, state } = makeStore(() => false, events)
  const previousTrack = createTrack(1000, 1)
  const newerTrack = createTrack(1100, 3)
  state.ai = newerTrack

  assert.throws(
    () => persistAiDecision({
      store,
      previousTrack,
      nextTrack: createTrack(900, 2),
      decisionId: 'decision-stale',
      status: 'open',
      receipt: receipt(events),
    }),
    /ai_track_changed_during_decision/,
  )
  assert.strictEqual(state.ai, newerTrack, 'a stale decision cannot overwrite a newer track')
  assert.deepEqual(events, [], 'a stale decision is rejected before the store write')
}

{
  const events: string[] = []
  const { store, state } = makeStore(() => false, events)
  const previousTrack = createTrack(1000, 1)
  state.ai = previousTrack
  const nextTrack = createTrack(900, 2)
  const committed = persistAiDecision({
    store, previousTrack, nextTrack, decisionId: 'decision-saved', status: 'open', receipt: receipt(events),
  })

  assert.strictEqual(state.ai, nextTrack)
  assert.deepEqual(committed, { decisionId: 'decision-saved', status: 'open', persistedAt: 2 })
  assert.deepEqual(events, ['store-write', 'receipt-commit'], 'receipt acknowledgement follows persistence')
}

{
  const events: string[] = []
  const { store, state } = makeStore(() => false, events)
  const firstTrack = createTrack(1000, 1)
  const committedTrack = createTrack(900, 2)
  state.ai = firstTrack

  const committed = persistAiDecision({
    store,
    previousTrack: firstTrack,
    nextTrack: committedTrack,
    decisionId: 'decision-first',
    status: 'open',
    receipt: receipt(events),
  })
  assert.deepEqual(committed, { decisionId: 'decision-first', status: 'open', persistedAt: 2 })

  assert.throws(
    () => persistAiDecision({
      store,
      previousTrack: firstTrack,
      nextTrack: createTrack(800, 3),
      decisionId: 'decision-stale-after-success',
      status: 'open',
      receipt: receipt(events),
    }),
    /ai_track_changed_during_decision/,
  )
  assert.strictEqual(state.ai, committedTrack, 'a later stale write preserves the committed track')
  assert.deepEqual(
    events,
    ['store-write', 'receipt-commit'],
    'a stale write after success adds no receipt event',
  )
}

console.log('ai decision writer: 5 persistence/receipt checks passed')
