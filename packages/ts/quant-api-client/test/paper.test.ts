import assert from 'node:assert/strict';
import { test } from 'vitest';
import { createQuantApiClient } from '../dist/index.js';
import type { PaperCommand, PaperStatus, PaperSubmitRequest } from '../src/index.ts';

// Synthetic fixture only. Never load Host state, environment credentials or configuration.
const syntheticCapability = 'synthetic-paper-test-capability-000001';
const input: PaperSubmitRequest = { environment: 'internal_paper', session_id: 'session-1', request_id: 'request-1', symbol: 'BTCUSDT', side: 'buy', order_type: 'limit', quantity: '0.001', limit_price: '50000' };
const status: PaperStatus = { environment: 'internal_paper', synthetic: true, session_id: 'session-1', state: 'running', ready: true, native_process_alive: true, generation: 1, pending_reservations: 0 };
const command: PaperCommand = { command_id: 'command-1', environment: 'internal_paper', session_id: 'session-1', native_client_order_id: 'native-1', state: 'admitted', cumulative_filled: '0' };
const json = (value: unknown, code = 200) => new Response(JSON.stringify(value), { status: code, headers: { 'content-type': 'application/json' } });
const client = (fetch: typeof globalThis.fetch, extra: { timeoutMs?: number; maxResponseBytes?: number } = {}) => createQuantApiClient({ fetch, serviceCapability: () => syntheticCapability, ...extra });

test('readonly constructor remains usable without capability; paper fails closed', async () => {
  let calls = 0;
  const api = createQuantApiClient({ fetch: async () => { calls++; return json(status); } });
  assert.deepEqual(await api.paper.status(), { ok: false, code: 'capability_unavailable' });
  assert.equal(calls, 0);
});

test('synthetic auth lives only in header; correct methods and stable lookup route', async () => {
  const requests: Request[] = [];
  const api = client(async raw => {
    const request = raw as Request;
    requests.push(request);
    assert.equal(request.headers.get('authorization'), `Bearer ${syntheticCapability}`);
    assert.equal(request.redirect, 'manual');
    const body = await request.clone().text();
    assert.equal(body.includes(syntheticCapability), false);
    return json(request.url.endsWith('/commands') ? command : request.url.includes('/commands/') ? command : status, request.url.endsWith('/commands') ? 202 : 200);
  });
  assert.equal((await api.paper.status()).ok, true);
  assert.equal((await api.paper.start({ environment: 'internal_paper', session_id: 'session-1' })).ok, true);
  assert.deepEqual(await api.paper.submit(input), { ok: true, status: 202, data: command });
  assert.equal((await api.paper.command('command-1')).ok, true);
  assert.equal((await api.paper.request('request-1')).ok, true);
  assert.equal((await api.paper.stop({ environment: 'internal_paper', session_id: 'session-1' })).ok, true);
  assert.deepEqual(requests.map(value => [new URL(value.url).pathname, value.method]), [
    ['/api/v1/trading/status', 'GET'], ['/api/v1/trading/start', 'POST'], ['/api/v1/trading/commands', 'POST'],
    ['/api/v1/trading/commands/command-1', 'GET'], ['/api/v1/trading/commands/by-request/request-1', 'GET'], ['/api/v1/trading/stop', 'POST'],
  ]);
});

test('untrusted input rejects extra risk truth and invalid IDs before capability resolution', async () => {
  let resolved = 0;
  const api = createQuantApiClient({ serviceCapability: () => { resolved++; return syntheticCapability; }, fetch: async () => json(command, 202) });
  for (const value of [{ ...input, equity: '10000' }, { ...input, policy: {} }, { ...input, quantity: 1 }, { ...input, environment: 'mainnet' }, { ...input, quantity: '1e4' }, { ...input, request_id: '.' }, { ...input, request_id: '..' }]) {
    assert.deepEqual(await api.paper.submit(value as PaperSubmitRequest), { ok: false, code: 'invalid_request' });
  }
  assert.deepEqual(await api.paper.start({ environment: 'internal_paper', session_id: 'session-1', cash: '1' } as never), { ok: false, code: 'invalid_request' });
  assert.deepEqual(await api.paper.command('../bad'), { ok: false, code: 'invalid_request' });
  assert.deepEqual(await api.paper.request('x'.repeat(129)), { ok: false, code: 'invalid_request' });
  assert.deepEqual(await api.paper.request('.'), { ok: false, code: 'invalid_request' });
  assert.deepEqual(await api.paper.request('..'), { ok: false, code: 'invalid_request' });
  assert.equal(resolved, 0);
});

test('actual HTTP semantics stay distinct and server diagnostics never leave SDK', async () => {
  for (const [http, code] of [[401, 'authentication_required'], [403, 'forbidden'], [409, 'conflict'], [422, 'invalid_request']] as const) {
    const result = await client(async () => json({ detail: 'private server diagnostic' }, http)).paper.submit(input);
    assert.deepEqual(result, { ok: false, code, status: http });
    assert.equal(JSON.stringify(result).includes('private'), false);
  }
  assert.deepEqual(await client(async () => json({ detail: 'unknown_command' }, 404)).paper.request('request-1'), { ok: false, code: 'not_found', status: 404 });
  assert.deepEqual(await client(async () => json({ detail: 'paper_unavailable' }, 503)).paper.status(), { ok: false, code: 'unavailable', status: 503 });
  assert.equal((await client(async () => json({ detail: 'bad', extra: true }, 422)).paper.status()).ok, false);
});

test('503 after a mutation preserves uncertainty and original recovery without retry', async () => {
  let calls = 0;
  const api = client(async raw => {
    calls++;
    assert.equal((raw as Request).method, 'POST');
    return json({ detail: 'paper_unavailable' }, 503);
  });
  const session = { environment: 'internal_paper', session_id: 'session-1' } as const;
  const statusRecovery = { ok: false, code: 'outcome_uncertain', cause: 'unavailable', recovery: { action: 'query_status' } };
  assert.deepEqual(await api.paper.start(session), statusRecovery);
  assert.equal(calls, 1);
  assert.deepEqual(await api.paper.stop(session), statusRecovery);
  assert.equal(calls, 2);
  assert.deepEqual(await api.paper.submit(input), { ok: false, code: 'outcome_uncertain', cause: 'unavailable', recovery: { action: 'query_request', request_id: input.request_id } });
  assert.equal(calls, 3);
});

test('strict generated response boundary rejects extra fields, wrong schema and status', async () => {
  for (const value of [{ ...status, equity: '1' }, { ...status, environment: 'mainnet' }, { ...status, ready: 'true' }]) {
    assert.deepEqual(await client(async () => json(value)).paper.status(), { ok: false, code: 'invalid_response', status: 200 });
  }
  for (const value of [{ ...command, state: 'invented' }, { ...command, session_id: 'other' }, command]) {
    const result = await client(async () => json(value, value === command ? 200 : 202)).paper.submit(input);
    assert.equal(result.ok, false);
    if (!result.ok) assert.equal(result.code, 'outcome_uncertain');
  }
});

test('capability provider failures and reflected escaped capability cannot leak', async () => {
  const unavailable = createQuantApiClient({ serviceCapability: () => { throw new Error(syntheticCapability); } });
  assert.deepEqual(await unavailable.paper.status(), { ok: false, code: 'capability_unavailable' });
  for (const body of [JSON.stringify({ ...command, native_client_order_id: syntheticCapability }), JSON.stringify({ ...command, native_client_order_id: syntheticCapability }).replaceAll('s', '\\u0073')]) {
    const result = await client(async () => new Response(body, { status: 202, headers: { 'content-type': 'application/json' } })).paper.submit(input);
    assert.equal(JSON.stringify(result).includes(syntheticCapability), false);
    assert.equal(result.ok, false);
  }
});

test('no retry after timeout; original stable request ID is query recovery', async () => {
  let calls = 0;
  const api = client(async () => { calls++; return new Promise<Response>(() => {}); }, { timeoutMs: 10 });
  assert.deepEqual(await api.paper.submit(input), { ok: false, code: 'outcome_uncertain', cause: 'timeout', recovery: { action: 'query_request', request_id: 'request-1' } });
  assert.equal(calls, 1);
});

test('provider shares deadline and cancellation; late provider cannot send', async () => {
  let resolve: ((value: string) => void) | undefined;
  let calls = 0;
  const api = createQuantApiClient({ timeoutMs: 10, serviceCapability: () => new Promise<string>(done => { resolve = done; }), fetch: async () => { calls++; return json(status); } });
  assert.deepEqual(await api.paper.status(), { ok: false, code: 'timeout' });
  assert.ok(resolve);
  resolve(syntheticCapability);
  await Promise.resolve();
  assert.equal(calls, 0);
  const cancelled = new AbortController();
  const pending = api.paper.start({ environment: 'internal_paper', session_id: 'session-1' }, { signal: cancelled.signal });
  cancelled.abort(syntheticCapability);
  assert.deepEqual(await pending, { ok: false, code: 'outcome_uncertain', cause: 'cancelled', recovery: { action: 'query_status' } });
  api.close();
});

test('close aborts authenticated work, redirects never follow and body remains bounded', async () => {
  const api = client(async () => new Promise<Response>(() => {}));
  const pending = api.paper.stop({ environment: 'internal_paper', session_id: 'session-1' });
  api.close();
  assert.deepEqual(await pending, { ok: false, code: 'outcome_uncertain', cause: 'closed', recovery: { action: 'query_status' } });
  assert.deepEqual(await api.paper.status(), { ok: false, code: 'closed' });
  assert.deepEqual(await client(async () => new Response(null, { status: 302, headers: { location: 'https://example.com' } })).paper.status(), { ok: false, code: 'redirect_rejected' });
  assert.deepEqual(await client(async () => json('x'.repeat(300)), { maxResponseBytes: 256 }).paper.status(), { ok: false, code: 'response_too_large' });
});


test('rejects remote origins before resolving capability and bounds authenticated streaming body', async () => {
  let resolved = 0;
  assert.throws(() => createQuantApiClient({ baseUrl: 'http://example.com', serviceCapability: () => { resolved++; return syntheticCapability; } }), /invalid_config/u);
  assert.equal(resolved, 0);
  let cancelled = false;
  const api = client(async () => new Response(new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(new TextEncoder().encode('{')); },
    cancel() { cancelled = true; },
  }), { headers: { 'content-type': 'application/json' } }), { timeoutMs: 10 });
  assert.deepEqual(await api.paper.status(), { ok: false, code: 'timeout' });
  assert.equal(cancelled, true);
});


test('printable quote and backslash capability reflections are rejected after decoding JSON', async () => {
  const capability = 'synthetic-quote-"-slash-\\-fixture-000001';
  const api = createQuantApiClient({ serviceCapability: () => capability, fetch: async () => json({ detail: capability }, 403) });
  assert.deepEqual(await api.paper.status(), { ok: false, code: 'invalid_response' });
});


test('uncertain recovery identity is immutable even when caller mutates DTO during provider wait', async () => {
  let resolve: ((value: string) => void) | undefined;
  let sent: unknown;
  const api = createQuantApiClient({
    serviceCapability: () => new Promise<string>(done => { resolve = done; }),
    fetch: async raw => { sent = await (raw as Request).json(); throw new Error('synthetic lost response'); },
  });
  const mutable = { ...input };
  const pending = api.paper.submit(mutable);
  mutable.request_id = 'request-mutated';
  mutable.session_id = 'session-mutated';
  assert.ok(resolve);
  resolve(syntheticCapability);
  assert.deepEqual(await pending, { ok: false, code: 'outcome_uncertain', cause: 'network_error', recovery: { action: 'query_request', request_id: input.request_id } });
  assert.deepEqual(sent, input);
});
