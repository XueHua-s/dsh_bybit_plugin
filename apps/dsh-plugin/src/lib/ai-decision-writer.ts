import { isDeepStrictEqual } from 'node:util'
import type { DecisionTrack } from './ai-types.js'
import type { AiLoopDecisionStatus, DecisionReceipt } from './ai-scheduler.js'
import type { Store } from './state.js'

/**
 * Persist the simulated AI book before acknowledging its cycle receipt.
 * If storage fails after mutating its in-memory document, restore the previous
 * track so an Agent retry cannot observe an uncommitted decision.
 */
export function persistAiDecision(input: {
  store: Store
  previousTrack: DecisionTrack
  nextTrack: DecisionTrack
  decisionId: string
  status: AiLoopDecisionStatus
  receipt?: DecisionReceipt
}) {
  const { store, previousTrack, nextTrack, decisionId, status, receipt } = input
  let replacedTrack = false
  try {
    store.mutate(state => {
      if (!isDeepStrictEqual(state.ai, previousTrack)) {
        throw new Error('ai_track_changed_during_decision')
      }
      state.ai = nextTrack
      replacedTrack = true
      return null
    })
  } catch (error) {
    if (replacedTrack && store.get().ai === nextTrack) store.get().ai = previousTrack
    throw error
  }
  return receipt?.commit(decisionId, status)
}
