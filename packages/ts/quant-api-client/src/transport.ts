export type ClientErrorCode = 'invalid_config' | 'invalid_symbol' | 'closed' | 'cancelled' | 'timeout' | 'network_error' | 'redirect_rejected' | 'response_too_large' | 'invalid_response' | 'not_found' | 'unavailable' | 'http_error';
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

/** Owns every in-flight request, including body reads; close is final and synchronous. */
export function createTransport(fetcher: typeof globalThis.fetch, timeoutMs: number, maxBytes: number) {
  const requests = new Set<AbortController>();
  let closed = false;
  return {
    close() { closed = true; for (const controller of requests) controller.abort(new TransportError('closed')); },
    async fetch(request: Request): Promise<Response> {
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
          const response = await fetcher(new Request(request, { signal: controller.signal, redirect: 'manual' }));
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
