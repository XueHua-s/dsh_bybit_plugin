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
    const backgroundLoop = data?.backgroundLoop ?? 'not_running'
    const account = data?.accountReadiness ?? 'not_checked'
    const authorityLabel = t('readinessUnavailable')
    const accountLabel = account === 'zero_equity' ? t('readinessZeroEquity') : account === 'unknown' ? t('readinessUnknown') : t('readinessNotChecked')
    return h('section', { className: 'bq-card bq-readiness', style: { marginTop: '12px' }, 'aria-label': t('readinessTitle') },
      h('h2', { className: 'bq-card-title' }, t('readinessTitle')),
      h('div', { className: 'bq-readiness-grid' },
        h('div', null, h('span', { className: 'bq-meta-label' }, t('readinessAutomation')), h('strong', null, automation === 'conversation_only' ? t('readinessConversationOnly') : automation)),
        h('div', null, h('span', { className: 'bq-meta-label' }, t('readinessBackground')), h('strong', null, backgroundLoop === 'not_running' ? t('readinessNotRunning') : backgroundLoop)),
        h('div', null, h('span', { className: 'bq-meta-label' }, t('readinessAuthority')), h('strong', null, authorityLabel)),
        h('div', null, h('span', { className: 'bq-meta-label' }, t('readinessAccount')), h('strong', null, accountLabel)),
      ),
      h('p', { className: 'bq-hint' }, t('readinessHint')),
    )
  }
}
