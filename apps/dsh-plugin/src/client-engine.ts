import type * as React from 'react'
import type { Engine } from './lib/engine.js'

type EngineStatus = Awaited<ReturnType<Engine['status']>>

/** Keeps the separately operated engine visible without coupling it to chart polling. */
export function enginePanel(react: Pick<typeof React, 'createElement' | 'useState' | 'useEffect'>) {
  const h = react.createElement
  return function EnginePanel() {
    const [status, setStatus] = react.useState<EngineStatus | null>(null)
    const [loading, setLoading] = react.useState(false)
    const [requested, setRequested] = react.useState(0)
    react.useEffect(() => {
      if (requested === 0) return
      const controller = new AbortController()
      setLoading(true)
      fetch('/api/bybit-quant?view=engine', { signal: controller.signal, headers: { accept: 'application/json' } })
        .then(async response => {
          if (!response.ok) throw new Error('engine_unavailable')
          const result = await response.json() as EngineStatus
          if (!controller.signal.aborted) setStatus(result)
        })
        .catch(() => {
          if (!controller.signal.aborted) setStatus(null)
        })
        .finally(() => { if (!controller.signal.aborted) setLoading(false) })
      return () => controller.abort()
    }, [requested])
    const summary = loading ? 'Checking… / 检查中…'
      : status === null ? (requested === 0 ? 'Not checked / 尚未检查' : 'Unavailable / 无法连接')
      : status.ok ? `${status.data.status} · ${status.data.supervisor_state}` : status.code
    return h('section', { className: 'bq-card', style: { marginTop: '12px' } },
      h('h2', { className: 'bq-card-title' }, 'Quant engine / 量化引擎 · Linear Testnet'),
      h('div', { role: 'status' }, summary),
      h('p', { className: 'bq-hint' }, 'Public market ingestion only; account, reconciliation and execution readiness unknown. / 仅公共行情采集；账户、对账和执行状态未知。'),
      status?.ok ? h('div', null, `Market ready / 行情就绪: ${String(status.data.ready)} · Execution / 执行: ${status.data.execution.status}`) : null,
      h('button', { type: 'button', className: 'bq-button', disabled: loading, onClick: () => setRequested(value => value + 1) }, 'Check engine / 检查引擎'),
    )
  }
}
