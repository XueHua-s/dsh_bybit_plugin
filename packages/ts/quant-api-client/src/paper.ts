import type { components, paths } from './generated/paper-paths.js';
import { TransportError } from './transport.js';
import type { ClientErrorCode, createTransport } from './transport.js';
import { validateRequestId, validateResponse } from './validation.js';

export type PaperStatus = components['schemas']['PaperStatus'];
export type PaperSessionRequest = components['schemas']['SessionRequest'];
export type PaperSubmitRequest = components['schemas']['SubmitRequest'];
export type PaperCommand = components['schemas']['CommandResponse'];
export interface PaperFailure { ok: false; code: ClientErrorCode; status?: number }
export interface PaperUncertain {
  ok: false;
  code: 'outcome_uncertain';
  cause: ClientErrorCode;
  /** Query this original identity; do not resubmit or invent another request ID. */
  recovery: { action: 'query_request'; request_id: string } | { action: 'query_status' };
}
export type PaperResult<T, S extends number = 200> = { ok: true; status: S; data: T } | PaperFailure;
export interface PaperApi {
  status(options?: { signal?: AbortSignal }): Promise<PaperResult<PaperStatus>>;
  start(input: PaperSessionRequest, options?: { signal?: AbortSignal }): Promise<PaperResult<PaperStatus> | PaperUncertain>;
  stop(input: PaperSessionRequest, options?: { signal?: AbortSignal }): Promise<PaperResult<PaperStatus> | PaperUncertain>;
  submit(input: PaperSubmitRequest, options?: { signal?: AbortSignal }): Promise<PaperResult<PaperCommand, 202> | PaperUncertain>;
  command(commandId: string, options?: { signal?: AbortSignal }): Promise<PaperResult<PaperCommand>>;
  request(requestId: string, options?: { signal?: AbortSignal }): Promise<PaperResult<PaperCommand>>;
}

function httpCode(status: number): ClientErrorCode {
  switch (status) {
    case 401: return 'authentication_required';
    case 403: return 'forbidden';
    case 404: return 'not_found';
    case 409: return 'conflict';
    case 422: return 'invalid_request';
    case 503: return 'unavailable';
    default: return 'http_error';
  }
}

function uncertain<T, S extends number>(result: PaperResult<T, S>, recovery: PaperUncertain['recovery']): PaperResult<T, S> | PaperUncertain {
  // A missing/malformed response may follow a committed dispatch. Failures never authorize retry.
  if (!result.ok && ['timeout', 'network_error', 'cancelled', 'closed', 'response_too_large', 'invalid_response', 'redirect_rejected'].includes(result.code)) {
    return { ok: false, code: 'outcome_uncertain', cause: result.code, recovery };
  }
  return result;
}

/** Owns the paper wire boundary and ambiguity policy. No mutation is ever retried. */
export function createPaperApi(baseUrl: string, transport: ReturnType<typeof createTransport>, capability?: () => string | Promise<string>): PaperApi {
  async function send<T extends 'PaperStatus' | 'CommandResponse', S extends 200 | 202>(
    path: keyof paths, schema: T, expectedStatus: S, signal?: AbortSignal, body?: PaperSessionRequest, pathId?: string,
  ): Promise<PaperResult<components['schemas'][T], S>> {
    if (!capability) return { ok: false, code: 'capability_unavailable' };
    try {
      const response = await transport.fetch(new Request(`${baseUrl}${path.replace(/\{[^}]+\}/u, () => encodeURIComponent(pathId ?? ''))}`, {
        method: body ? 'POST' : 'GET',
        headers: { accept: 'application/json', ...(body ? { 'content-type': 'application/json' } : {}) },
        ...(body ? { body: JSON.stringify(body) } : {}),
        ...(signal ? { signal } : {}),
      }), { origin: baseUrl, capability });
      const value: unknown = await response.json();
      if (response.status !== expectedStatus) {
        if (![401, 403, 404, 409, 422, 503].includes(response.status) || !validateResponse('PaperError', value)) return { ok: false, code: 'invalid_response', status: response.status };
        // Never return supplied validation inputs or server error strings to a caller.
        return { ok: false, code: httpCode(response.status), status: response.status };
      }
      if (!validateResponse(schema, value)) return { ok: false, code: 'invalid_response', status: response.status };
      return { ok: true, status: expectedStatus, data: value };
    } catch (error: unknown) {
      return { ok: false, code: error instanceof TransportError ? error.code : 'invalid_response' };
    }
  }
  return {
    status: (options = {}) => send('/api/v1/trading/status', 'PaperStatus', 200, options.signal),
    async start(input, options = {}) {
      if (!validateResponse('SessionRequest', input)) return { ok: false, code: 'invalid_request' };
      const sessionId = input.session_id;
      const result = await send('/api/v1/trading/start', 'PaperStatus', 200, options.signal, input);
      if (result.ok && result.data.session_id !== sessionId) return uncertain({ ok: false, code: 'invalid_response' }, { action: 'query_status' });
      return uncertain(result, { action: 'query_status' });
    },
    async stop(input, options = {}) {
      if (!validateResponse('SessionRequest', input)) return { ok: false, code: 'invalid_request' };
      const sessionId = input.session_id;
      const result = await send('/api/v1/trading/stop', 'PaperStatus', 200, options.signal, input);
      if (result.ok && result.data.session_id !== sessionId) return uncertain({ ok: false, code: 'invalid_response' }, { action: 'query_status' });
      return uncertain(result, { action: 'query_status' });
    },
    async submit(input, options = {}) {
      if (!validateResponse('SubmitRequest', input)) return { ok: false, code: 'invalid_request' };
      // Capture identity before awaiting a private provider; callers can mutate their DTO.
      const requestId = input.request_id;
      const sessionId = input.session_id;
      const result = await send('/api/v1/trading/commands', 'CommandResponse', 202, options.signal, input);
      if (result.ok && result.data.session_id !== sessionId) return uncertain({ ok: false, code: 'invalid_response' }, { action: 'query_request', request_id: requestId });
      return uncertain(result, { action: 'query_request', request_id: requestId });
    },
    async command(commandId, options = {}) {
      if (!validateRequestId(commandId)) return Promise.resolve({ ok: false, code: 'invalid_request' });
      const result = await send('/api/v1/trading/commands/{command_id}', 'CommandResponse', 200, options.signal, undefined, commandId);
      return result.ok && result.data.command_id !== commandId ? { ok: false, code: 'invalid_response', status: 200 } : result;
    },
    request(requestId, options = {}) {
      if (!validateRequestId(requestId)) return Promise.resolve({ ok: false, code: 'invalid_request' });
      return send('/api/v1/trading/commands/by-request/{request_id}', 'CommandResponse', 200, options.signal, undefined, requestId);
    },
  };
}
