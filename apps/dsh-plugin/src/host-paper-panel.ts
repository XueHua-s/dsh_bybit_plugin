import type { HostRuntime, PluginContext } from './host-runtime.js'

const PATH = '/api/bybit-quant/paper'
class InputFailure extends Error {
  constructor(readonly status: number, readonly code: string) { super(code) }
}

/** The supported carrier owns authentication/owner admission; this dashboard route is observation-only. */
export function registerPaperPanel(ctx: PluginContext, { paper }: HostRuntime): void {
  ctx.inject(['webServer', 'connection'], web => {
    web.effect(() => web.connection.fetch.register({
      path: PATH, methods: ['GET', 'HEAD'], requestBody: 'buffered',
      async fetch(request) {
        const head = request.method === 'HEAD'
        const response = (value: unknown, status = 200) => new Response(head ? null : JSON.stringify(value), {
          status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
        })
        try {
          const url = new URL(request.url)
          if (url.pathname !== PATH || url.search) throw new InputFailure(400, 'invalid_arguments')
          if (!['GET', 'HEAD'].includes(request.method)) throw new InputFailure(405, 'method_not_allowed')
          const origin = request.headers.get('origin')
          const site = request.headers.get('sec-fetch-site')
          if ((origin !== null && origin !== url.origin) || (site !== null && !['same-origin', 'none'].includes(site))) throw new InputFailure(403, 'origin_refused')
          if (request.body !== null) throw new InputFailure(400, 'invalid_arguments')
          return response(await paper.status(request.signal))
        } catch (error: unknown) {
          void request.body?.cancel().catch(() => {})
          return error instanceof InputFailure ? response({ ok: false, code: error.code }, error.status)
            : response({ ok: false, code: 'invalid_arguments' }, 400)
        }
      },
    }), 'bybit-quant: native paper panel route')
  })
}
