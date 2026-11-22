import type * as React from 'react'
import type { Translate } from './client-types.js'

type ReactSubset = Pick<typeof React, 'createElement'>

type MarketViewProps = {
  draft: string
  category: string
  interval: string
  candidates: readonly string[]
  t: Translate
  onDraftChange(value: string): void
  onApplySymbol(): void
  onCategoryChange(value: string): void
  onIntervalChange(value: string): void
}

const CATEGORIES = ['linear', 'spot']
const INTERVALS = [
  ['1', '1m'], ['5', '5m'], ['15', '15m'], ['60', '1h'], ['240', '4h'], ['D', '1d'],
]

/** A read-only chart selector; it has no AI or execution command surface. */
export function marketViewControls(react: ReactSubset) {
  const h = react.createElement
  return function MarketViewControls({
    draft, category, interval, candidates, t, onDraftChange, onApplySymbol, onCategoryChange, onIntervalChange,
  }: MarketViewProps) {
    return h('section', { className: 'bq-card', style: { marginTop: '12px' }, 'aria-label': t('marketView') },
      h('h2', { className: 'bq-card-title' }, t('marketView')),
      h('p', { className: 'bq-hint', style: { marginTop: 0 } }, t('viewFiltersHint')),
      h('div', { className: 'bq-controls' },
        h('div', { className: 'bq-field' },
          h('label', { className: 'bq-label', htmlFor: 'bq-symbol' }, t('symbol')),
          h('input', {
            id: 'bq-symbol', className: 'bq-input', value: draft, list: 'bq-symbols', spellCheck: false,
            onChange: (event: React.ChangeEvent<HTMLInputElement>) => onDraftChange(event.target.value),
            onKeyDown: (event: React.KeyboardEvent<HTMLInputElement>) => { if (event.key === 'Enter') onApplySymbol() },
            onBlur: onApplySymbol,
          }),
          h('datalist', { id: 'bq-symbols' }, candidates.map(value => h('option', { key: value, value }))),
        ),
        h('div', { className: 'bq-field' },
          h('span', { className: 'bq-label' }, t('category')),
          h('div', { className: 'bq-tabs' }, CATEGORIES.map(value => h('button', {
            key: value, type: 'button', className: 'bq-tab', 'aria-pressed': category === value,
            onClick: () => onCategoryChange(value),
          }, value === 'linear' ? 'Perp' : 'Spot'))),
        ),
        h('div', { className: 'bq-field' },
          h('span', { className: 'bq-label' }, t('interval')),
          h('div', { className: 'bq-tabs' }, INTERVALS.map(([value = '60', label = '1h']) => h('button', {
            key: value, type: 'button', className: 'bq-tab', 'aria-pressed': interval === value,
            onClick: () => onIntervalChange(value),
          }, label))),
        ),
      ),
    )
  }
}
