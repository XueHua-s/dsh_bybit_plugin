export type ClientErrorCode = 'invalid_config' | 'invalid_symbol' | 'closed' | 'cancelled' | 'timeout' | 'network_error' | 'redirect_rejected' | 'response_too_large' | 'invalid_response' | 'not_found' | 'unavailable' | 'http_error' | 'authentication_required' | 'forbidden' | 'conflict' | 'invalid_request' | 'capability_unavailable';
export class TransportError extends Error {
  constructor(readonly code: ClientErrorCode) { super(code); }
}

export function localBaseUrl(value: string): string {
  let url: URL;
  try { url = new URL(value); } catch { throw new TransportError('invalid_config'); }
  const host = url.hostname;
  if (url.protocol !== 'http:' || !(/^(127)(\.\d{1,3}){3}$/u.test(host) || host === '[::1]') || url.username || url.password || url.search || url.hash || url.pathname !== '/') throw new TransportError('invalid_config');
  // URL normalizes exotic integer/octal forms; require the literal numeric host spelling.
  const authority = value.match(/^http:\/\/(\[[^\]]+\]|[^/:?#]+)(?::\d+)?\/?$/u)?.[1];
  if (authority !== host) throw new TransportError('invalid_config');
  return url.origin;
}

export function boundedInteger(value: number, minimum: number, maximum: number): number {
  if (!Number.isSafeInteger(value) || value < minimum || value > maximum) throw new TransportError('invalid_config');
  return value;
}

// Inspect decoded values and keys, rather than reserialized JSON: printable tokens may
// contain quotes/backslashes which JSON serialization would escape differently.
function containsCapability(value: unknown, capability: string, depth = 0): boolean {
  if (depth > 12) return true;
  if (typeof value === 'string') return value.includes(capability);
  if (Array.isArray(value)) return value.some((child: unknown) => containsCapability(child, capability, depth + 1));
  if (typeof value === 'object' && value !== null) return Object.entries(value).some(([key, child]) => key.includes(capability) || containsCapability(child, capability, depth + 1));
  return false;
}

/** Owns every in-flight request, including body reads; close is final and synchronous. */
export function createTransport(fetcher: typeof globalThis.fetch, timeoutMs: number, maxBytes: number) {
  const requests = new Set<AbortController>();
  let closed = false;
  return {
    close() { closed = true; for (const controller of requests) controller.abort(new TransportError('closed')); },
    async fetch(request: Request, authority?: { origin: string; capability: () => string | Promise<string> }): Promise<Response> {
      if (closed) throw new TransportError('closed');
      const controller = new AbortController();
      requests.add(controller);
      const cancel = () => controller.abort(new TransportError('cancelled'));
      if (request.signal.aborted) cancel();
      else request.signal.addEventListener('abort', cancel, { once: true });
      const timer = setTimeout(() => controller.abort(new TransportError('timeout')), timeoutMs);
      let abortListener: (() => void) | undefined;
      const aborted = new Promise<never>((_, reject) => {
        abortListener = () => reject(controller.signal.reason);
        if (controller.signal.aborted) abortListener();
        else controller.signal.addEventListener('abort', abortListener, { once: true });
      });
      try {
        const operation = async () => {
          let capability: string | undefined;
          const headers = new Headers(request.headers);
          if (authority) {
            if (localBaseUrl(new URL(request.url).origin) !== authority.origin) throw new TransportError('invalid_config');
            try { capability = await authority.capability(); } catch { throw new TransportError('capability_unavailable'); }
            if (typeof capability !== 'string' || !/^[\x21-\x7e]{32,128}$/u.test(capability)) throw new TransportError('capability_unavailable');
            headers.set('authorization', `Bearer ${capability}`);
          }
          // The provider may ignore cancellation; never send after our bounded wait expired.
          if (controller.signal.aborted) throw controller.signal.reason;
          const response = await fetcher(new Request(request, { headers, signal: controller.signal, redirect: 'manual' }));
          if (controller.signal.aborted) { void response.body?.cancel().catch(() => {}); throw controller.signal.reason; }
          if (response.redirected || (response.status >= 300 && response.status < 400)) { await response.body?.cancel(); throw new TransportError('redirect_rejected'); }
          const length = response.headers.get('content-length');
          if (length !== null && (!/^\d+$/u.test(length) || Number(length) > maxBytes)) { await response.body?.cancel(); throw new TransportError('response_too_large'); }
          const reader = response.body?.getReader();
          const cancelReader = () => { void reader?.cancel().catch(() => {}); };
          controller.signal.addEventListener('abort', cancelReader, { once: true });
          const chunks: Uint8Array[] = [];
          let total = 0;
          try {
            while (true) {
              if (!reader) break;
              const { done, value } = await reader.read();
              if (done) break;
              total += value.byteLength;
              if (total > maxBytes) { void reader.cancel().catch(() => {}); throw new TransportError('response_too_large'); }
              chunks.push(value);
            }
          } finally { controller.signal.removeEventListener('abort', cancelReader); reader?.releaseLock(); }
          const bytes = new Uint8Array(total);
          let offset = 0;
          for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
          if (capability) {
            let decoded: unknown;
            try { decoded = JSON.parse(new TextDecoder().decode(bytes)) as unknown; } catch { throw new TransportError('invalid_response'); }
            if (containsCapability(decoded, capability)) throw new TransportError('invalid_response');
          }
          if (!response.headers.get('content-type')?.toLowerCase().startsWith('application/json')) throw new TransportError('invalid_response');
          return new Response(bytes, { status: response.status, headers: response.headers });
        };
        return await Promise.race([operation(), aborted]);
      } catch (error: unknown) {
        if (controller.signal.aborted) throw controller.signal.reason;
        if (error instanceof TransportError) throw error;
        throw new TransportError('network_error');
      } finally {
        clearTimeout(timer);
        request.signal.removeEventListener('abort', cancel);
        if (abortListener) controller.signal.removeEventListener('abort', abortListener);
        requests.delete(controller);
      }
    },
  };
}
