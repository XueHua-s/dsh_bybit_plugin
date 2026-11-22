import { createQuantApiClient } from '@bybit-quant/quant-api-client'
import type { PaperAiCycleReceipt, PaperAiCycleRequest, PaperCommand, PaperFixtureSnapshot, PaperResult, PaperStatus, PaperSubmitRequest, PaperUncertain } from '@bybit-quant/quant-api-client'
import { createPaperCapabilityProvider, paperConfiguration } from './paper-capability.js'

export type PaperProposal = Pick<PaperSubmitRequest, 'request_id' | 'symbol' | 'side' | 'quantity' | 'limit_price'>
type LocalFailure = { ok: false, code: 'paper_disabled' | 'control_disabled' | 'invalid_arguments' }
type Context = { source: 'quant-engine-paper', environment: 'internal_paper', synthetic: true, configured: boolean, control_enabled: boolean }
type PaperData = PaperStatus | PaperCommand | PaperFixtureSnapshot | PaperAiCycleReceipt
type Result<T extends PaperData, S extends number = 200> = Context & (PaperResult<T, S> | PaperUncertain | LocalFailure)
const ID = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/u
const DECIMAL = /^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?$/u
const options = (signal?: AbortSignal) => signal === undefined ? {} : { signal }

export function isPaperId(value: unknown): value is string { return typeof value === 'string' && ID.test(value) }
export function isPaperProposal(value: unknown): value is PaperProposal {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false
  const fields = value as Record<string, unknown>
  return Object.keys(fields).length === 5 && Object.keys(fields).every(key => ['request_id', 'symbol', 'side', 'quantity', 'limit_price'].includes(key))
    && isPaperId(fields.request_id) && fields.symbol === 'BTCUSDT' && (fields.side === 'buy' || fields.side === 'sell')
    && [fields.quantity, fields.limit_price].every(number => typeof number === 'string' && number.length <= 21 && DECIMAL.test(number) && /[1-9]/u.test(number))
}

/** Fixed native-paper authority. Hides provisioning, opt-in, scoped response trust and query-only recovery. */
export function createPaperEngine(config: Record<string, unknown>) {
  const settings = paperConfiguration(config)
  const provider = settings === undefined ? undefined : createPaperCapabilityProvider(settings)
  const client = settings === undefined ? undefined : createQuantApiClient({
    baseUrl: settings.origin, timeoutMs: 2000, maxResponseBytes: 65536, serviceCapability: () => provider!.resolve(),
  })
  const context: Context = {
    source: 'quant-engine-paper', environment: 'internal_paper', synthetic: true,
    configured: settings !== undefined, control_enabled: settings?.controlEnabled === true,
  }
  const disabled = (control: boolean): LocalFailure | undefined => settings === undefined
    ? { ok: false, code: 'paper_disabled' } : control && !settings.controlEnabled ? { ok: false, code: 'control_disabled' } : undefined
  function scoped<T extends PaperStatus | PaperCommand, S extends number>(result: PaperResult<T, S> | PaperUncertain, recovery?: PaperUncertain['recovery']): Result<T, S> {
    if (result.ok && (result.data.session_id !== settings?.sessionId || result.data.environment !== 'internal_paper')) {
      return { ...context, ...recovery === undefined ? { ok: false, code: 'invalid_response' } as const
        : { ok: false, code: 'outcome_uncertain', cause: 'invalid_response', recovery } as const }
    }
    return { ...context, ...result }
  }
  function scopedCycle(result: PaperResult<PaperAiCycleReceipt, 202> | PaperUncertain, request: PaperAiCycleRequest): Result<PaperAiCycleReceipt, 202> {
    const recovery = { action: 'query_request', request_id: request.request_id } as const
    if (result.ok && (result.data.request_id !== request.request_id || result.data.payload_digest !== request.payload_digest)) {
      return { ...context, ok: false, code: 'outcome_uncertain', cause: 'invalid_response', recovery }
    }
    if (!result.ok && result.code === 'outcome_uncertain') return { ...context, ...result, recovery }
    return { ...context, ...result }
  }
  return {
    async status(signal?: AbortSignal): Promise<Result<PaperStatus>> {
      const denied = disabled(false)
      return denied ? { ...context, ...denied } : scoped(await client!.paper.status(options(signal)))
    },
    async start(signal?: AbortSignal): Promise<Result<PaperStatus>> {
      const denied = disabled(true)
      return denied ? { ...context, ...denied } : scoped(await client!.paper.start({ environment: 'internal_paper', session_id: settings!.sessionId }, options(signal)), { action: 'query_status' })
    },
    async stop(signal?: AbortSignal): Promise<Result<PaperStatus>> {
      const denied = disabled(true)
      return denied ? { ...context, ...denied } : scoped(await client!.paper.stop({ environment: 'internal_paper', session_id: settings!.sessionId }, options(signal)), { action: 'query_status' })
    },
    async submit(proposal: PaperProposal, signal?: AbortSignal): Promise<Result<PaperCommand, 202>> {
      if (!isPaperProposal(proposal)) return { ...context, ok: false, code: 'invalid_arguments' }
      // Copy before asynchronous work so recovery and wire body retain the original identity.
      const input = { ...proposal, environment: 'internal_paper', session_id: settings?.sessionId ?? '', order_type: 'limit' } as const
      const denied = disabled(true)
      return denied ? { ...context, ...denied } : scoped(await client!.paper.submit(input, options(signal)), { action: 'query_request', request_id: input.request_id })
    },
    async request(requestId: string, signal?: AbortSignal): Promise<Result<PaperCommand>> {
      if (!isPaperId(requestId)) return { ...context, ok: false, code: 'invalid_arguments' }
      const denied = disabled(false)
      return denied ? { ...context, ...denied } : scoped(await client!.paper.request(requestId, options(signal)))
    },
    async command(commandId: string, signal?: AbortSignal): Promise<Result<PaperCommand>> {
      if (!isPaperId(commandId)) return { ...context, ok: false, code: 'invalid_arguments' }
      const denied = disabled(false)
      return denied ? { ...context, ...denied } : scoped(await client!.paper.command(commandId, options(signal)))
    },
    async fixture(fixtureId: string, signal?: AbortSignal): Promise<Result<PaperFixtureSnapshot>> {
      if (!isPaperId(fixtureId)) return { ...context, ok: false, code: 'invalid_arguments' }
      const denied = disabled(false)
      if (denied) return { ...context, ...denied }
      const result = await client!.paper.fixture(fixtureId, options(signal))
      return result.ok && result.data.fixture_id !== fixtureId
        ? { ...context, ok: false, code: 'invalid_response' }
        : { ...context, ...result }
    },
    async cycle(request: PaperAiCycleRequest, signal?: AbortSignal): Promise<Result<PaperAiCycleReceipt, 202>> {
      if (!isPaperId(request.request_id) || request.session_id !== settings?.sessionId || request.environment !== 'internal_paper') {
        return { ...context, ok: false, code: 'invalid_arguments' }
      }
      const denied = disabled(true)
      return denied ? { ...context, ...denied } : scopedCycle(await client!.paper.cycle(request, options(signal)), request)
    },
    async cycleRequest(requestId: string, signal?: AbortSignal): Promise<Result<PaperAiCycleReceipt>> {
      if (!isPaperId(requestId)) return { ...context, ok: false, code: 'invalid_arguments' }
      const denied = disabled(false)
      if (denied) return { ...context, ...denied }
      const result = await client!.paper.cycleRequest(requestId, options(signal))
      return result.ok && result.data.request_id !== requestId
        ? { ...context, ok: false, code: 'invalid_response' }
        : { ...context, ...result }
    },
    /** Only Host requests and provider sockets close; independent service/native ownership remains external. */
    close() { client?.close(); provider?.close() },
  }
}

export type PaperEngine = ReturnType<typeof createPaperEngine>
export type PaperStatusResult = Awaited<ReturnType<PaperEngine['status']>>
export type PaperMutationResult = Awaited<ReturnType<PaperEngine['start']>>
