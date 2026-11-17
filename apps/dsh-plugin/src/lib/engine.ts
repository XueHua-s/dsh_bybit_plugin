import { createQuantApiClient } from '@bybit-quant/quant-api-client'

/** Owns the read-only engine boundary; never receives account credentials or starts a process. */
export function createEngine(config: Record<string, unknown>) {
  if (config.engineBaseUrl !== undefined && typeof config.engineBaseUrl !== 'string') {
    throw new Error('engineBaseUrl must be a numeric loopback HTTP URL')
  }
  const baseUrl = config.engineBaseUrl ?? 'http://127.0.0.1:8765'
  const client = createQuantApiClient({ baseUrl, timeoutMs: 2000, maxResponseBytes: 262144 })
  const environmentMatches = config.env === undefined || config.env === 'testnet'
  const context = { source: 'quant-engine', environment: 'testnet', category: 'linear', executionReady: false } as const
  const mismatch = { ok: false, code: 'environment_mismatch' } as const
  return {
    /** Readiness describes public ingestion only, never account/execution readiness. */
    async status(signal?: AbortSignal) {
      const result = environmentMatches ? await client.health(signal === undefined ? {} : { signal }) : mismatch
      return { ...context, ...result }
    },
    /** Preserve partial/null ticker facts; never fill gaps with REST or chart data. */
    async market(symbol: string, signal?: AbortSignal) {
      const result = environmentMatches ? await client.market(symbol, signal === undefined ? {} : { signal }) : mismatch
      return { ...context, ...result }
    },
    close: () => client.close(),
  }
}

export type Engine = ReturnType<typeof createEngine>
