/** Runtime health metrics kept in memory and exposed through the Host health view. */
export interface RuntimeMetrics {
  startedAt: number
  lastMarketDataAt: number | null
  lastSuccessfulRequestAt: number | null
  lastErrorAt: number | null
  lastOrderLatencyMs: number | null
  requestCount: number
  failedRequestCount: number
  orderCount: number
  rejectedOrderCount: number
  websocket: {
    enabled: boolean
    connected: boolean
    reconnects: number
    lastConnectedAt: number | null
    lastDisconnectedAt: number | null
  }
  queueDepth: number
  memoryRssBytes: number
  cpuUserMicros: number
  cpuUsagePercent: number
  recoveryAttempts: number
}

export interface RequestMetric {
  operation: string
  signed: boolean
  ok: boolean
  latencyMs: number
  status?: number
}

export interface RuntimeMonitor {
  observeRequest(metric: RequestMetric): void
  observeQueue(depth: number): void
  observeWebSocket(state: 'connected' | 'disconnected' | 'reconnect'): void
  observeRecovery(): void
  snapshot(): RuntimeMetrics
  start(intervalMs?: number): () => void
}

/**
 * Create a process-local monitor. It intentionally contains no credentials or
 * payloads; only counters, timestamps and resource gauges are retained.
 */
export function createRuntimeMonitor({ websocketEnabled = false }: { websocketEnabled?: boolean } = {}): RuntimeMonitor {
  const startedAt = Date.now()
  let metrics: RuntimeMetrics = initialMetrics(startedAt, websocketEnabled)
  let timer: ReturnType<typeof setInterval> | undefined
  let lastCpuSample = process.cpuUsage()
  let lastCpuSampleAt = Date.now()

  function sampleResources(): void {
    const memory = process.memoryUsage()
    const now = Date.now()
    const cpu = process.cpuUsage(lastCpuSample)
    const elapsedMicros = Math.max(1, now - lastCpuSampleAt) * 1000
    const cpuUsagePercent = ((cpu.user + cpu.system) / elapsedMicros) * 100
    lastCpuSample = process.cpuUsage()
    lastCpuSampleAt = now
    metrics = {
      ...metrics,
      memoryRssBytes: memory.rss,
      cpuUserMicros: process.cpuUsage().user,
      cpuUsagePercent: Math.min(cpuUsagePercent, 100 * (process.env.UV_THREADPOOL_SIZE ? Number(process.env.UV_THREADPOOL_SIZE) : 1)),
    }
  }

  return {
    observeRequest(metric) {
      const now = Date.now()
      const isOrder = metric.operation.toLowerCase().includes('order')
      metrics = {
        ...metrics,
        requestCount: metrics.requestCount + 1,
        failedRequestCount: metrics.failedRequestCount + (metric.ok ? 0 : 1),
        lastSuccessfulRequestAt: metric.ok ? now : metrics.lastSuccessfulRequestAt,
        lastErrorAt: metric.ok ? metrics.lastErrorAt : now,
        lastMarketDataAt: metric.ok && !metric.signed ? now : metrics.lastMarketDataAt,
        lastOrderLatencyMs: isOrder ? metric.latencyMs : metrics.lastOrderLatencyMs,
        orderCount: metrics.orderCount + (isOrder && metric.ok ? 1 : 0),
        rejectedOrderCount: metrics.rejectedOrderCount + (isOrder && !metric.ok ? 1 : 0),
      }
    },
    observeQueue(depth) {
      metrics = { ...metrics, queueDepth: Number.isFinite(depth) && depth >= 0 ? Math.trunc(depth) : 0 }
    },
    observeWebSocket(state) {
      const now = Date.now()
      if (state === 'connected') {
        metrics = { ...metrics, websocket: { ...metrics.websocket, connected: true, lastConnectedAt: now } }
      } else if (state === 'disconnected') {
        metrics = { ...metrics, websocket: { ...metrics.websocket, connected: false, lastDisconnectedAt: now } }
      } else {
        metrics = {
          ...metrics,
          websocket: { ...metrics.websocket, reconnects: metrics.websocket.reconnects + 1, connected: true, lastConnectedAt: now },
        }
      }
    },
    observeRecovery() {
      metrics = { ...metrics, recoveryAttempts: metrics.recoveryAttempts + 1 }
    },
    snapshot() {
      sampleResources()
      return JSON.parse(JSON.stringify(metrics)) as RuntimeMetrics
    },
    start(intervalMs = 5000) {
      timer = setInterval(sampleResources, intervalMs)
      sampleResources()
      return () => {
        if (timer !== undefined) clearInterval(timer)
        timer = undefined
      }
    },
  }
}

function initialMetrics(startedAt: number, websocketEnabled: boolean): RuntimeMetrics {
  return {
    startedAt,
    lastMarketDataAt: null,
    lastSuccessfulRequestAt: null,
    lastErrorAt: null,
    lastOrderLatencyMs: null,
    requestCount: 0,
    failedRequestCount: 0,
    orderCount: 0,
    rejectedOrderCount: 0,
    websocket: {
      enabled: websocketEnabled,
      connected: false,
      reconnects: 0,
      lastConnectedAt: null,
      lastDisconnectedAt: null,
    },
    queueDepth: 0,
    memoryRssBytes: 0,
    cpuUserMicros: 0,
    cpuUsagePercent: 0,
    recoveryAttempts: 0,
  }
}
