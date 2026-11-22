import type * as React from 'react'
import type { PanelPayload, Translate } from './client-types.js'

type ReactSubset = Pick<typeof React, 'createElement'>

/**
 * Makes the operating boundary visible in the panel. These facts are kept
 * separate from market data so a healthy ticker cannot imply an autonomous
 * trading loop or an account that passed pre-trade checks.
 */
export function readinessPanel(react: ReactSubset) {
  const h = react.createElement
  return function ReadinessPanel({ data, t }: { data: PanelPayload | null, t: Translate }) {
    const automation = data?.automation ?? 'conversation_only'
    const backgroundLoop = data?.backgroundLoop ?? 'disabled'
    const loopEnvironment = data?.backgroundLoopEnvironment ?? 'testnet'
    const loopIntervalMs = data?.backgroundLoopIntervalMs ?? 15 * 60_000
    const lastRun = data?.backgroundLoopLastRun
    const account = data?.accountReadiness ?? 'not_checked'
    const candidatePool = data?.aiCandidatePool
    const candidateStatus = candidatePool?.status === 'fresh'
      ? t('readinessCandidateFresh')
      : candidatePool?.status === 'stale' ? t('readinessCandidateStale') : t('readinessCandidateUnknown')
    const candidateObserved = candidatePool?.observedAt === null || candidatePool?.observedAt === undefined
      ? ''
      : ` · ${new Date(candidatePool.observedAt).toLocaleTimeString()}`
    const authorityLabel = t('readinessUnavailable')
    const accountLabel = account === 'zero_equity' ? t('readinessZeroEquity') : account === 'unknown' ? t('readinessUnknown') : t('readinessNotChecked')
    const loopLabels: Record<NonNullable<PanelPayload['backgroundLoop']>, string> = {
      disabled: t('readinessLoopDisabled'),
      not_configured: t('readinessLoopNotConfigured'),
      environment_rejected: t('readinessLoopEnvironmentRejected'),
      starting: t('readinessLoopStarting'),
      running: t('readinessLoopRunning'),
      idle: t('readinessLoopIdle'),
      backoff: t('readinessLoopBackoff'),
      blocked: t('readinessLoopBlocked'),
      stopping: t('readinessLoopStopping'),
    }
    const environmentLabels: Record<NonNullable<PanelPayload['backgroundLoopEnvironment']>, string> = {
      testnet: t('readinessEnvironmentTestnet'),
      internal_paper: t('readinessEnvironmentInternalPaper'),
      demo: t('readinessEnvironmentDemo'),
      live: t('readinessEnvironmentLive'),
    }
    const receiptStatus = lastRun?.latestDecisionStatus === 'open'
      ? t('readinessDecisionOpen')
      : lastRun?.latestDecisionStatus === 'flat' ? t('readinessDecisionFlat')
        : lastRun?.latestDecisionStatus === 'rejected' ? t('readinessDecisionRejected')
          : lastRun?.latestDecisionStatus === 'uncertain' ? t('readinessDecisionUncertain') : ''
    const lastRunText = lastRun === null || lastRun === undefined
      ? t('readinessNoCompletedCycle')
      : lastRun.decisionsRecorded === 0
        ? `${lastRun.outcome === 'failed' ? t('readinessCycleFailed') : t('readinessCycleCompleted')} · ${t('readinessNoDecisionReceipt')}`
        : `${lastRun.outcome === 'failed' ? t('readinessCycleFailed') : t('readinessCycleCompleted')} · ${lastRun.decisionsRecorded} · ${receiptStatus} · ${new Date(lastRun.completedAt).toLocaleString()}`
    return h('section', { className: 'bq-card bq-readiness', style: { marginTop: '12px' }, 'aria-label': t('readinessTitle') },
      h('h2', { className: 'bq-card-title' }, t('readinessTitle')),
      h('div', { className: 'bq-readiness-grid' },
        h('div', null, h('span', { className: 'bq-meta-label' }, t('readinessAutomation')), h('strong', null, automation === 'conversation_only' ? t('readinessConversationOnly') : t('readinessBackgroundSimulation'))),
        h('div', null, h('span', { className: 'bq-meta-label' }, t('readinessBackground')), h('strong', null, loopLabels[backgroundLoop])),
        h('div', null, h('span', { className: 'bq-meta-label' }, t('readinessAuthority')), h('strong', null, authorityLabel)),
        h('div', null, h('span', { className: 'bq-meta-label' }, t('readinessAccount')), h('strong', null, accountLabel)),
        h('div', null,
          h('span', { className: 'bq-meta-label' }, t('readinessCandidates')),
          h('strong', null, `${candidateStatus} · ${candidatePool?.eligibleCount ?? 0} · ${candidatePool?.category === 'spot' ? 'Spot' : 'USDT Perp'}${candidateObserved}`),
          candidatePool?.candidates.length
            ? h('span', { className: 'bq-meta-label' }, `${t('readinessCandidateSymbols')}: ${candidatePool.candidates.join(', ')}`)
            : null),
      ),
      h('p', { className: 'bq-hint' }, `${t('readinessLoopCadence')}: ${Math.round(loopIntervalMs / 60_000)} min · ${t('readinessLoopEnvironment')}: ${environmentLabels[loopEnvironment]}`),
      h('p', { className: 'bq-hint' }, `${t('readinessLastCycle')}: ${lastRunText}`),
      h('p', { className: 'bq-hint' }, t('readinessHint')),
    )
  }
}
