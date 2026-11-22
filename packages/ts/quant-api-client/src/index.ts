import { createPaperApi } from './paper.js';
import type { PaperApi } from './paper.js';
export type { PaperApi, PaperStatus, PaperSessionRequest, PaperSubmitRequest, PaperCommand, PaperFixtureSnapshot, PaperAiCycleRequest, PaperAiCycleReceipt, PaperResult, PaperFailure, PaperUncertain } from './paper.js';
import createClient from 'openapi-fetch';
import type { paths, components } from './generated/paths.js';
import { boundedInteger, createTransport, localBaseUrl, TransportError } from './transport.js';
import type { ClientErrorCode } from './transport.js';
import { validateResponse } from './validation.js';

export type HealthResponse = components['schemas']['HealthResponse'];
export type MarketResponse = components['schemas']['MarketResponse'];
export type StrategyEvidenceRequest = components['schemas']['StrategyEvidenceRequest'];
export type StrategyEvidenceResponse = components['schemas']['StrategyEvidenceResponse'];
export type { paths, components, ClientErrorCode };
export interface RequestOptions { signal?: AbortSignal }
export interface ClientOptions {
  baseUrl?: string;
  timeoutMs?: number;
  maxResponseBytes?: number;
  /** Injectable transport for deterministic tests; production defaults to global fetch. */
  fetch?: typeof globalThis.fetch;
  /** Trusted Host injection, resolved outside model tools. Never ordinary configuration or DTO data. */
  serviceCapability?: () => string | Promise<string>;
}
export interface ClientFailure { ok: false; code: ClientErrorCode; status?: number }
export type HealthResult = { ok: true; status: 200 | 503; data: HealthResponse } | ClientFailure;
export type MarketResult = { ok: true; status: 200; data: MarketResponse } | ClientFailure;
export type StrategyEvidenceResult = { ok: true; status: 200; data: StrategyEvidenceResponse } | ClientFailure;
export interface QuantApiClient {
  readonly paper: PaperApi;
  health(options?: RequestOptions): Promise<HealthResult>;
  market(symbol: string, options?: RequestOptions): Promise<MarketResult>;
  strategyEvidence(request: StrategyEvidenceRequest, options?: RequestOptions): Promise<StrategyEvidenceResult>;
  close(): void;
}

function failure(error: unknown): ClientFailure {
  return { ok: false, code: error instanceof TransportError ? error.code : 'invalid_response' };
}
function httpFailure(status: number): ClientFailure {
  return { ok: false, status, code: status === 404 ? 'not_found' : status === 503 ? 'unavailable' : 'http_error' };
}

const evidenceIntervals = new Set(['1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M']);

function validEvidenceRequest(request: StrategyEvidenceRequest): boolean {
  if (!/^[A-Z0-9]{2,32}$/u.test(request.symbol)
    || (request.market !== 'spot' && request.market !== 'linear')
    || !evidenceIntervals.has(request.interval)
    || request.bars.length > 1000
    || (request.funding_rate !== undefined && request.funding_rate !== null
      && (request.market !== 'linear' || !Number.isFinite(request.funding_rate) || Math.abs(request.funding_rate) > 0.1))) return false;
  let previousTimestamp = -1;
  for (const bar of request.bars) {
    if (!Number.isSafeInteger(bar.timestamp_ms) || bar.timestamp_ms < 0 || bar.timestamp_ms <= previousTimestamp
      || [bar.open, bar.high, bar.low, bar.close, bar.volume].some(value => !Number.isFinite(value))
      || Math.min(bar.open, bar.high, bar.low, bar.close) <= 0 || bar.volume < 0
      || bar.high < Math.max(bar.open, bar.close) || bar.low > Math.min(bar.open, bar.close)) return false;
    previousTimestamp = bar.timestamp_ms;
  }
  return true;
}

/** Read-only loopback engine access. Invalid configuration throws a fixed-code error.
 * Wire DTOs are generated; requests return safe outcomes and never provider exception text.
 */
export function createQuantApiClient(options: ClientOptions = {}): QuantApiClient {
  const baseUrl = localBaseUrl(options.baseUrl ?? 'http://127.0.0.1:8765');
  const transport = createTransport(options.fetch ?? globalThis.fetch, boundedInteger(options.timeoutMs ?? 3000, 1, 60000), boundedInteger(options.maxResponseBytes ?? 65536, 256, 1048576));
  const client = createClient<paths>({ baseUrl, fetch: (request) => transport.fetch(request), redirect: 'manual' });
  return {
    close: transport.close,
    paper: createPaperApi(baseUrl, transport, options.serviceCapability),
    async health(requestOptions = {}) {
      try {
        const result = await client.GET('/api/v1/health', requestOptions.signal ? { signal: requestOptions.signal } : {});
        const status = result.response.status;
        if (status !== 200 && status !== 503) return httpFailure(status);
        const value: unknown = status === 200 ? result.data : result.error;
        if (!validateResponse('HealthResponse', value)) return { ok: false, code: 'invalid_response', status };
        if ((status === 200 && (!value.ready || value.status !== 'ready')) || (status === 503 && (value.ready || value.status === 'ready'))) return { ok: false, code: 'invalid_response', status };
        // Never surface arbitrary local provider diagnostics to DSH/model callers.
        return { ok: true, status, data: { ...value, last_error: value.last_error === null ? null : 'engine_error' } };
      } catch (error: unknown) { return failure(error); }
    },
    async market(symbol, requestOptions = {}) {
      if (!/^[A-Z0-9]{1,32}$/u.test(symbol)) return { ok: false, code: 'invalid_symbol' };
      try {
        const result = await client.GET('/api/v1/market/{symbol}', { params: { path: { symbol } }, ...(requestOptions.signal ? { signal: requestOptions.signal } : {}) });
        const status = result.response.status;
        if (status !== 200) return httpFailure(status);
        const value: unknown = result.data;
        if (!validateResponse('MarketResponse', value) || value.symbol !== symbol || value.age_seconds < 0 || value.event_time_ms < 0 || [value.last_price, value.bid_price, value.ask_price].some(price => price !== null && price <= 0)) return { ok: false, code: 'invalid_response', status };
        return { ok: true, status: 200, data: value };
      } catch (error: unknown) { return failure(error); }
    },
    async strategyEvidence(request, requestOptions = {}) {
      if (!validEvidenceRequest(request)) return { ok: false, code: 'invalid_request' };
      try {
        const result = await client.POST('/api/v1/research/strategy-evidence', {
          body: request,
          ...(requestOptions.signal ? { signal: requestOptions.signal } : {}),
        });
        const status = result.response.status;
        if (status !== 200) return httpFailure(status);
        const value: unknown = result.data;
        const newestTimestamp = request.bars.at(-1)?.timestamp_ms ?? null;
        if (!validateResponse('StrategyEvidenceResponse', value)
          || value.symbol !== request.symbol || value.market !== request.market || value.interval !== request.interval
          || value.research_only !== true || value.deployment_eligible !== false
          || value.strategy_count !== value.strategies.length || value.newest_timestamp_ms !== newestTimestamp
          || (request.bars.length === 0 && value.snapshot_status !== 'empty')
          || (request.bars.length > 0 && value.snapshot_status === 'empty')
          || value.strategies.some(strategy => strategy.research_only !== true
            || strategy.deployment_eligible !== false
            || (strategy.ready !== (strategy.research_target_exposure !== null)))) {
          return { ok: false, code: 'invalid_response', status };
        }
        return { ok: true, status: 200, data: value };
      } catch (error: unknown) { return failure(error); }
    },
  };
}
