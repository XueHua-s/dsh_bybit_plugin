import type { HostRuntime, PluginContext } from './host-runtime.js'

const PATH = '/api/bybit-quant/paper'
class InputFailure extends Error {
  constructor(readonly status: number, readonly code: string) { super(code) }
}

/** The supported carrier owns authentication/owner admission; this boundary adds strict tiny controls. */
export function registerPaperPanel(ctx: PluginContext, { paper }: HostRuntime): void {
  ctx.inject(['webServer', 'connection'], web => {
    web.effect(() => web.connection.fetch.register({
      path: PATH, methods: ['GET', 'HEAD', 'POST'], requestBody: 'streaming',
      async fetch(request) {
        const head = request.method === 'HEAD'
        const response = (value: unknown, status = 200) => new Response(head ? null : JSON.stringify(value), {
          status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
        })
        try {
          const url = new URL(request.url)
          if (url.pathname !== PATH || url.search || !['GET', 'HEAD', 'POST'].includes(request.method)) throw new InputFailure(400, 'invalid_arguments')
          const origin = request.headers.get('origin')
          const site = request.headers.get('sec-fetch-site')
          if ((origin !== null && origin !== url.origin) || (site !== null && !['same-origin', 'none'].includes(site))) throw new InputFailure(403, 'origin_refused')
          if (request.method !== 'POST') {
            if (request.body !== null) throw new InputFailure(400, 'invalid_arguments')
            return response(await paper.status(request.signal))
          }
          if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/iu.test(request.headers.get('content-type') ?? '')) throw new InputFailure(415, 'unsupported_media_type')
          const action = await readAction(request)
          return response(await paper[action](request.signal))
        } catch (error: unknown) {
          void request.body?.cancel().catch(() => {})
          return error instanceof InputFailure ? response({ ok: false, code: error.code }, error.status)
            : response({ ok: false, code: 'invalid_arguments' }, 400)
        }
      },
    }), 'bybit-quant: native paper panel route')
  })
}

/** A streaming carrier avoids its broad buffered limit; the read deadline also covers stalled peers. */
async function readAction(request: Request): Promise<'start' | 'stop'> {
  const length = request.headers.get('content-length')
  if (length !== null && (!/^\d+$/u.test(length) || Number(length) > 512)) throw new InputFailure(413, 'body_too_large')
  const reader = request.body?.getReader()
  if (reader === undefined) throw new InputFailure(400, 'invalid_arguments')
  let rejectWait: ((error: InputFailure) => void) | undefined
  const cancelled = new Promise<never>((_, reject) => { rejectWait = reject })
  const stop = (code: string) => {
    rejectWait?.(new InputFailure(400, code))
    void reader.cancel().catch(() => {})
  }
  const abort = () => stop('cancelled')
  const timer = setTimeout(() => stop('body_timeout'), 2000)
  request.signal.addEventListener('abort', abort, { once: true })
  if (request.signal.aborted) abort()
  const chunks: Uint8Array[] = []
  let bytes = 0
  try {
    while (true) {
      const { value, done } = await Promise.race([reader.read(), cancelled])
      if (done) break
      bytes += value.byteLength
      if (bytes > 512) { void reader.cancel().catch(() => {}); throw new InputFailure(413, 'body_too_large') }
      chunks.push(value)
    }
    const body = new Uint8Array(bytes)
    let offset = 0
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength }
    let value: unknown
    try { value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(body)) as unknown } catch { throw new InputFailure(400, 'invalid_arguments') }
    if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new InputFailure(400, 'invalid_arguments')
    const fields = value as Record<string, unknown>
    if (Object.keys(fields).length !== 1 || (fields.action !== 'start' && fields.action !== 'stop')) throw new InputFailure(400, 'invalid_arguments')
    return fields.action
  } finally {
    clearTimeout(timer)
    request.signal.removeEventListener('abort', abort)
    reader.releaseLock()
  }
}
