import type * as React from 'react'
import type { PaperStatus } from '@bybit-quant/quant-api-client'
import type { PaperStatusResult } from './lib/engine-paper.js'

type Context = Pick<PaperStatusResult, 'source' | 'environment' | 'synthetic' | 'configured' | 'control_enabled'>
type FailureCode = Extract<PaperStatusResult, { ok: false }>['code']
type Observation = Context & { data: PaperStatus | null, code: FailureCode | null }
type View = { observation: Observation | null, issue: 'unavailable' | 'invalid_response' | null, pending: boolean, checked: boolean }
type Owner = { pending: boolean, closed: boolean, controller: AbortController | null, sessionId: string | null, observation: Observation | null }
const failureCodes: readonly FailureCode[] = [
  'paper_disabled', 'control_disabled', 'invalid_config', 'closed', 'cancelled', 'timeout', 'network_error',
  'redirect_rejected', 'response_too_large', 'invalid_response', 'not_found', 'unavailable', 'http_error',
  'authentication_required', 'forbidden', 'conflict', 'invalid_request', 'invalid_arguments', 'invalid_symbol', 'capability_unavailable',
]
const record = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)
const count = (value: unknown): value is number => Number.isSafeInteger(value) && Number(value) >= 0

/** Consume only safe Host context and generated status fields; never display raw bridge errors. */
function observation(value: unknown): Observation | null {
  if (!record(value) || value.source !== 'quant-engine-paper' || value.environment !== 'internal_paper'
    || value.synthetic !== true || typeof value.configured !== 'boolean' || typeof value.control_enabled !== 'boolean') return null
  const context: Context = { source: value.source, environment: value.environment, synthetic: value.synthetic, configured: value.configured, control_enabled: value.control_enabled }
  if (value.ok === false) {
    const code = failureCodes.find(candidate => candidate === value.code)
    return code === undefined ? null : { ...context, data: null, code }
  }
  if (value.ok !== true || !value.configured || !record(value.data)) return null
  const data = value.data
  const states: readonly PaperStatus['state'][] = ['idle', 'running', 'protected', 'stopping', 'stopped']
  const state = states.find(candidate => candidate === data.state)
  if (state === undefined || data.environment !== 'internal_paper' || data.synthetic !== true
    || typeof data.session_id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/u.test(data.session_id)
    || typeof data.native_process_alive !== 'boolean' || typeof data.ready !== 'boolean'
    || !count(data.generation) || !count(data.pending_reservations)) return null
  return { ...context, code: null, data: {
    environment: 'internal_paper', synthetic: true, session_id: data.session_id, state,
    native_process_alive: data.native_process_alive, ready: data.ready,
    generation: data.generation, pending_reservations: data.pending_reservations,
  } }
}

function consistent(data: PaperStatus): boolean {
  if ((data.state === 'idle' || data.state === 'stopped') && (data.native_process_alive || data.ready)) return false
  if (data.state === 'running' && !data.native_process_alive) return false
  return !(data.state === 'protected' && data.ready)
}

/** Owns one demand-driven request at a time; unmount aborts observation, never the paper service. */
export function paperPanel(react: Pick<typeof React, 'createElement' | 'useState' | 'useEffect'>) {
  const h = react.createElement
  return function PaperPanel() {
    const [owner] = react.useState<Owner>(() => ({ pending: false, closed: false, controller: null, sessionId: null, observation: null }))
    const [request, setRequest] = react.useState<boolean | null>(null)
    const [view, setView] = react.useState<View>({ observation: null, issue: null, pending: false, checked: false })
    react.useEffect(() => {
      owner.closed = false
      return () => { owner.closed = true; owner.controller?.abort() }
    }, [owner])
    react.useEffect(() => {
      if (request === null) return
      const controller = new AbortController()
      owner.controller = controller
      async function run() {
        try {
          const response = await fetch('/api/bybit-quant/paper', { method: 'GET', signal: controller.signal, cache: 'no-store', credentials: 'same-origin', redirect: 'error', headers: { accept: 'application/json' } })
          if (!response.ok) throw new Error('unavailable')
          const parsed = observation(await response.json() as unknown)
          if (controller.signal.aborted || owner.closed) return
          if (parsed === null || (parsed.data !== null && owner.sessionId !== null && owner.sessionId !== parsed.data.session_id)) throw new Error('invalid_response')
          if (parsed.data !== null) owner.sessionId = parsed.data.session_id
          owner.observation = parsed
          setView({ observation: parsed, issue: null, pending: false, checked: true })
        } catch (error: unknown) {
          if (controller.signal.aborted || owner.closed) return
          owner.observation = null
          const issue = error instanceof Error && error.message === 'invalid_response' ? 'invalid_response' : 'unavailable'
          setView({ observation: null, issue, pending: false, checked: true })
        } finally {
          if (owner.controller === controller) { owner.controller = null; owner.pending = false }
        }
      }
      void run()
      return () => controller.abort()
    }, [request, owner])
    function check() {
      if (owner.closed || owner.pending) return
      owner.pending = true
      setView(previous => ({ ...previous, pending: true }))
      setRequest(previous => previous === null ? true : !previous)
    }
    const current = view.observation
    const data = current?.data
    const issue = view.issue ?? current?.code
    const summary = view.pending ? 'Checking status / 正在检查状态'
      : issue ?? (data ? consistent(data) ? data.state : 'invalid_response · inconsistent state/liveness / 状态与进程不一致'
        : view.checked ? 'Unavailable / 无法连接' : 'Not checked / 尚未检查')
    return h('section', { className: 'bq-card', style: { marginTop: '12px' }, 'aria-label': 'Native internal paper / 原生内部模拟' },
      h('h2', { className: 'bq-card-title' }, 'Native internal paper / 原生内部模拟'),
      h('p', { className: 'bq-hint' }, 'Synthetic · no exchange connection / 合成模拟 · 不连接交易所 · source: quant-engine-paper · environment: internal_paper'),
      h('p', { className: 'bq-hint' }, 'Separate from legacy paper/AI books and Linear Testnet. / 独立于旧版模拟账本、AI 账本和 Linear Testnet。'),
      h('div', { role: 'status', 'aria-live': 'polite' }, summary),
      current ? h('p', null, `Configured / 已配置: ${String(current.configured)} · Controls enabled / 控制已启用: ${String(current.control_enabled)}`) : null,
      data ? h('p', null, `Session / 会话: ${data.session_id} · State / 状态: ${data.state} · Native process alive / 原生进程存活: ${String(data.native_process_alive)} · Execution ready / 执行就绪: ${String(data.ready)}`) : null,
      data ? h('p', null, `Generation / 代次: ${data.generation} · Pending reservations / 待处理预留: ${data.pending_reservations}`) : null,
      data?.state === 'protected' ? h('p', { className: 'bq-hint' }, 'protected · Check status; execution is not ready. / 受保护，请检查状态；执行未就绪。') : null,
      data?.state === 'stopping' ? h('p', { className: 'bq-hint' }, 'Stop is in progress; cleanup is not confirmed. / 正在停止，尚未确认清理完成。') : null,
      data?.state === 'stopped' ? h('p', { className: 'bq-hint' }, 'A new session requires operator setup. / 新会话需要操作员配置。') : null,
      h('p', { className: 'bq-hint' }, 'Status is observation-only. Start, stop, and order controls belong to the separately governed execution service. / 此处仅查看状态；启动、停止和订单控制属于独立治理的执行服务。'),
      h('button', { type: 'button', className: 'bq-button', disabled: view.pending, onClick: check }, 'Check status / 检查状态'),
    )
  }
}
