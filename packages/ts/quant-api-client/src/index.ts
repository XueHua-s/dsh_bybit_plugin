import { createPaperApi } from './paper.js';
import type { PaperApi } from './paper.js';
export type { PaperApi, PaperStatus, PaperSessionRequest, PaperSubmitRequest, PaperCommand, PaperResult, PaperFailure, PaperUncertain } from './paper.js';
import createClient from 'openapi-fetch';
import type { paths, components } from './generated/paths.js';
import { boundedInteger, createTransport, localBaseUrl, TransportError } from './transport.js';
import type { ClientErrorCode } from './transport.js';
import { validateResponse } from './validation.js';

export type HealthResponse = components['schemas']['HealthResponse'];
export type MarketResponse = components['schemas']['MarketResponse'];
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
export interface QuantApiClient {
  readonly paper: PaperApi;
  health(options?: RequestOptions): Promise<HealthResult>;
  market(symbol: string, options?: RequestOptions): Promise<MarketResult>;
  close(): void;
}

function failure(error: unknown): ClientFailure {
  return { ok: false, code: error instanceof TransportError ? error.code : 'invalid_response' };
}
function httpFailure(status: number): ClientFailure {
  return { ok: false, status, code: status === 404 ? 'not_found' : status === 503 ? 'unavailable' : 'http_error' };
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
  };
}
