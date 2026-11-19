import assert from 'node:assert/strict';
import { test } from 'vitest';
import { createQuantApiClient } from '../dist/index.js';
import type { HealthResponse, MarketResponse } from '../src/index.ts';

const health: HealthResponse = { environment: 'testnet', status: 'ready', ready: true, supervisor_state: 'running', restart_count: 0, max_restarts: 2, last_error: null, process: { rss_bytes: 1024, cpu_user_seconds: 0, cpu_system_seconds: 0 }, market: null, execution: { status: 'unknown', reconciliation: 'unknown' } };
const market: MarketResponse = { environment: 'testnet', symbol: 'BTCUSDT', last_price: 100, ask_price: null, bid_price: null, event_time_ms: 123, received_at: '2026-11-17T00:00:00Z', partial: true, exchange_lag_seconds: 0, age_seconds: 0 };
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json' } });
const withResponse = (response: () => Response) => createQuantApiClient({ fetch: async () => response() });

test('generated health DTOs validate 200 and 503 without exposing diagnostic text', async () => {
  assert.deepEqual(await withResponse(() => json(health)).health(), { ok: true, status: 200, data: health });
  const unavailable = { ...health, status: 'unavailable', ready: false, last_error: 'private upstream detail' };
  const result = await withResponse(() => json(unavailable, 503)).health();
  assert.equal(result.ok, true);
  if (result.ok) assert.equal(result.data.last_error, 'engine_error');
  for (const [body, status] of [[health, 503], [unavailable, 200]] as const) assert.equal((await withResponse(() => json(body, status)).health()).ok, false);
});

test('wire validation rejects malformed, extra, huge, nonfinite and mismatched DTOs', async () => {
  for (const value of [{ ...market, last_price: '100' }, { ...market, extra: true }, { ...market, event_time_ms: 1e100 }, { ...market, symbol: 'ETHUSDT' }, { ...market, age_seconds: -1 }, { ...market, last_price: 0 }]) {
    assert.deepEqual(await withResponse(() => json(value)).market('BTCUSDT'), { ok: false, code: 'invalid_response', status: 200 });
  }
  assert.deepEqual(await withResponse(() => new Response('{"last_price":1e999}', { headers: { 'content-type': 'application/json' } })).market('BTCUSDT'), { ok: false, code: 'invalid_response', status: 200 });
  assert.deepEqual(await withResponse(() => json(market)).market('BTCUSDT'), { ok: true, status: 200, data: market });
  assert.deepEqual(await withResponse(() => json({ ...health, process: { ...health.process, cpu_user_seconds: -1e100 } })).health(), { ok: false, code: 'invalid_response', status: 200 });
});

test('only literal numeric loopback HTTP origins and bounded config accepted', () => {
  for (const baseUrl of ['https://127.0.0.1', 'http://localhost', 'http://example.com', 'http://127.0.0.1/?x=1', 'http://user:pass@127.0.0.1', 'http://127.0.0.1/#x', 'http://127.0.0.1/api', 'http://2130706433', 'http://0177.0.0.1']) assert.throws(() => createQuantApiClient({ baseUrl }), /invalid_config/u);
  createQuantApiClient({ baseUrl: 'http://[::1]:8765' }).close();
  assert.throws(() => createQuantApiClient({ timeoutMs: 0 }), /invalid_config/u);
  assert.throws(() => createQuantApiClient({ maxResponseBytes: Infinity }), /invalid_config/u);
});

test('symbol errors and provider failures are safe result codes', async () => {
  const client = withResponse(() => json({ detail: 'sensitive provider text' }, 503));
  assert.deepEqual(await client.market('../private'), { ok: false, code: 'invalid_symbol' });
  assert.deepEqual(await client.market('BTCUSDT'), { ok: false, code: 'unavailable', status: 503 });
  assert.deepEqual(await withResponse(() => json({}, 404)).market('BTCUSDT'), { ok: false, code: 'not_found', status: 404 });
  assert.deepEqual(await createQuantApiClient({ fetch: async () => { throw new Error('secret text'); } }).health(), { ok: false, code: 'network_error' });
});

test('redirect, oversized and malformed body blocked', async () => {
  assert.deepEqual(await withResponse(() => new Response(null, { status: 302, headers: { location: 'http://example.com' } })).health(), { ok: false, code: 'redirect_rejected' });
  assert.deepEqual(await createQuantApiClient({ maxResponseBytes: 256, fetch: async () => json('x'.repeat(300)) }).health(), { ok: false, code: 'response_too_large' });
  assert.deepEqual(await withResponse(() => new Response('invalid', { headers: { 'content-type': 'application/json' } })).health(), { ok: false, code: 'invalid_response' });
  assert.deepEqual(await withResponse(() => new Response('{}')).health(), { ok: false, code: 'invalid_response' });
});

test('deadline resolves even when injected fetch ignores abort', async () => {
  const client = createQuantApiClient({ timeoutMs: 15, fetch: async () => new Promise<Response>(() => {}) });
  assert.deepEqual(await client.health(), { ok: false, code: 'timeout' });
});

test('caller cancellation and close cancel in-flight and reject future work', async () => {
  const client = createQuantApiClient({ fetch: async () => new Promise<Response>(() => {}) });
  const controller = new AbortController();
  const pending = client.health({ signal: controller.signal });
  controller.abort('arbitrary private reason');
  assert.deepEqual(await pending, { ok: false, code: 'cancelled' });
  const second = client.health();
  client.close();
  assert.deepEqual(await second, { ok: false, code: 'closed' });
  assert.deepEqual(await client.health(), { ok: false, code: 'closed' });
});

test('deadline includes stalled streaming body and releases reader', async () => {
  let cancelled = false;
  const client = createQuantApiClient({ timeoutMs: 15, fetch: async request => {
    assert.equal((request as Request).redirect, 'manual');
    return new Response(new ReadableStream<Uint8Array>({ start(controller) { controller.enqueue(new TextEncoder().encode('{')); }, cancel() { cancelled = true; } }), { headers: { 'content-type': 'application/json' } });
  } });
  assert.deepEqual(await client.health(), { ok: false, code: 'timeout' });
  assert.equal(cancelled, true);
});

test('engine-accepted future event lag is preserved', async () => {
  const data = { ...market, exchange_lag_seconds: -4.5 };
  assert.deepEqual(await withResponse(() => json(data)).market('BTCUSDT'), { ok: true, status: 200, data });
});
