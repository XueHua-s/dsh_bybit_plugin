/**
 * Minimal Bybit v5 REST client for the Bybit quant plugin.
 *
 * Public market data defaults to the live endpoint so demo/testnet accounts
 * still see real prices; network tests can bind it to their public environment.
 * Signed calls go to `env`. No dependency ships with this module: it uses the
 * runtime's global `fetch`, `node:crypto`, and `AbortSignal`.
 */
import { createHmac } from 'node:crypto'
import type { Env, Category, Candle, Ticker, OrderBookSnapshot, FundingRate, Instrument, WalletBalance, ApiKeyInfo, Position, OpenOrder, CreateOrderInput } from './bybit-types.js'
import { ENDPOINTS, MARKET_ENDPOINT } from './bybit-constants.js'
import { BybitError } from './bybit-error.js'
import { mapInstrument, mapLevels, number as num, toQuery } from './bybit-format.js'
export { formatQuantity, intervalLabel, intervalMs, normalizeCategory, normalizeInterval, normalizeSymbol, trimNumber } from './bybit-format.js'
export { BybitError } from './bybit-error.js'
export { ENDPOINTS, INTERVALS, MARKET_ENDPOINT, MARKET_ENDPOINTS } from './bybit-constants.js'
export type { Env, Category, Candle, Ticker, OrderBookSnapshot, FundingRate, Instrument, WalletBalance, ApiKeyInfo, Position, OpenOrder, CreateOrderInput } from './bybit-types.js'

/** Split a fetch failure into a readable message. */
function describeTransportError(error: unknown, endpoint: string): string {
  const named = error as { name?: string, message?: string, cause?: { code?: string, message?: string } }
  if (named?.name === 'AbortError' || named?.name === 'TimeoutError') {
    return `request to ${endpoint} was cancelled or timed out`
  }
  const cause = named?.cause?.code ?? named?.cause?.message ?? named?.message
  return `cannot reach ${endpoint} (${cause ?? 'unknown network error'})`
}

/** Bybit REST client bound to one environment and one API key pair. */
export class BybitClient {
  #options: { env: Env, marketEndpoint: string, apiKey: string | undefined, apiSecret: string | undefined, recvWindow: number, timeoutMs: number }
  #resolveCredentials: (() => Promise<{ apiKey?: string | undefined, apiSecret?: string | undefined }>) | undefined
  #observeRequest: ((metric: { operation: string, signed: boolean, ok: boolean, latencyMs: number, status?: number }) => void) | undefined
  #observeQueue: ((depth: number) => void) | undefined
  #inFlight = 0
  #metrics = { requests: 0, failures: 0, orderLatencyMs: null as number | null, lastRequestLatencyMs: null as number | null, lastSuccessAt: null as number | null, lastErrorAt: null as number | null }

  constructor(options: { env?: Env, marketEndpoint?: string, apiKey?: string | undefined, apiSecret?: string | undefined, recvWindow?: number, timeoutMs?: number, resolveCredentials?: () => Promise<{ apiKey?: string | undefined, apiSecret?: string | undefined }>, observeRequest?: (metric: { operation: string, signed: boolean, ok: boolean, latencyMs: number, status?: number }) => void, observeQueue?: (depth: number) => void } = {}) {
    const env = options.env ?? 'demo'
    if (!Object.hasOwn(ENDPOINTS, env)) throw new BybitError(`unknown env "${env}"; use live, demo, or testnet`)
    this.#options = {
      env,
      marketEndpoint: options.marketEndpoint ?? MARKET_ENDPOINT,
      apiKey: options.apiKey,
      apiSecret: options.apiSecret,
      recvWindow: options.recvWindow ?? 5000,
      timeoutMs: options.timeoutMs ?? 15000,
    }
    this.#resolveCredentials = options.resolveCredentials
    this.#observeRequest = options.observeRequest
    this.#observeQueue = options.observeQueue
  }

  /** Selected trading environment. */
  get env(): Env {
    return this.#options.env
  }

  /** Base URL used for account and order endpoints. */
  get tradingBase(): string {
    return ENDPOINTS[this.#options.env]
  }

  /** Base URL used for read-only public market calls. */
  get marketBase(): string {
    return this.#options.marketEndpoint
  }

  /** Whether an API key pair is configured. */
  get hasCredentials(): boolean {
    return Boolean(this.#options.apiKey && this.#options.apiSecret)
  }

  /** Replace in-memory credentials resolved for the current operation. */
  setCredentials(apiKey: string | undefined, apiSecret: string | undefined): void {
    this.#options.apiKey = apiKey
    this.#options.apiSecret = apiSecret
  }

  /** Read-only operational metrics; never contains key material or payloads. */
  get metrics() {
    return { ...this.#metrics }
  }

  /** Perform one request and unwrap Bybit's envelope. */
  async #request(input: {
    method: 'GET' | 'POST'
    base: string
    path: string
    params?: Record<string, unknown>
    signed?: boolean
    signal?: AbortSignal | undefined
  }): Promise<Record<string, unknown>> {
    this.#inFlight += 1
    this.#observeQueue?.(this.#inFlight)
    try {
      return await this.#performRequest(input)
    } finally {
      this.#inFlight = Math.max(0, this.#inFlight - 1)
      this.#observeQueue?.(this.#inFlight)
    }
  }

  async #performRequest({ method, base, path, params = {}, signed = false, signal }: {
    method: 'GET' | 'POST'
    base: string
    path: string
    params?: Record<string, unknown>
    signed?: boolean
    signal?: AbortSignal | undefined | undefined
  }): Promise<Record<string, unknown>> {
    const startedAt = Date.now()
    const recordMetric = (ok: boolean) => {
      const latencyMs = Date.now() - startedAt
      this.#metrics = {
        requests: this.#metrics.requests + 1,
        failures: this.#metrics.failures + (ok ? 0 : 1),
        orderLatencyMs: path.includes('/order/') ? latencyMs : this.#metrics.orderLatencyMs,
        lastRequestLatencyMs: latencyMs,
        lastSuccessAt: ok ? Date.now() : this.#metrics.lastSuccessAt,
        lastErrorAt: ok ? this.#metrics.lastErrorAt : Date.now(),
      }
      this.#observeRequest?.({ operation: path, signed, ok, latencyMs })
    }
    const query = method === 'GET' ? toQuery(params) : ''
    const body = method === 'GET' ? '' : JSON.stringify(params)
    const url = `${base}${path}${query === '' ? '' : `?${query}`}`
    const headers: Record<string, string> = { accept: 'application/json' }
    if (body !== '') headers['content-type'] = 'application/json'
    if (signed) {
      const resolved = await this.#resolveCredentials?.()
      if (resolved !== undefined) this.setCredentials(resolved.apiKey, resolved.apiSecret)
      if (!this.hasCredentials) {
        throw new BybitError('this call needs a Bybit API key; set BYBIT_API_KEY and BYBIT_API_SECRET or the plugin config fields')
      }
      const timestamp = Date.now().toString()
      const signature = createHmac('sha256', this.#options.apiSecret as string)
        .update(`${timestamp}${String(this.#options.apiKey)}${String(this.#options.recvWindow)}${query}${body}`)
        .digest('hex')
      headers['X-BAPI-API-KEY'] = this.#options.apiKey as string
      headers['X-BAPI-SIGN'] = signature
      headers['X-BAPI-TIMESTAMP'] = timestamp
      headers['X-BAPI-RECV-WINDOW'] = String(this.#options.recvWindow)
    }

    const timeout = AbortSignal.timeout(this.#options.timeoutMs)
    const composed = signal === undefined ? timeout : AbortSignal.any([signal, timeout])
    let response: Response
    try {
      response = await fetch(url, { method, headers, ...body === '' ? {} : { body }, signal: composed, redirect: 'error' })
    } catch (error) {
      recordMetric(false)
      throw new BybitError(describeTransportError(error, base), { endpoint: path })
    }

    const text = await response.text()
    let payload: Record<string, unknown>
    try {
      payload = JSON.parse(text) as Record<string, unknown>
    } catch {
      recordMetric(false)
      throw new BybitError(`Bybit returned a non-JSON response (HTTP ${String(response.status)})`, {
        endpoint: path, status: response.status,
      })
    }
    if (payload.retCode !== 0) {
      recordMetric(false)
      throw new BybitError(`Bybit ${path} failed: ${String(payload.retMsg ?? 'unknown error')} (retCode ${String(payload.retCode)})`, {
        retCode: Number(payload.retCode), retMsg: String(payload.retMsg ?? ''), endpoint: path, status: response.status,
      })
    }
    recordMetric(true)
    return (payload.result ?? {}) as Record<string, unknown>
  }

  /** Public market request on the live venue. */
  async publicRequest(path: string, params: Record<string, unknown>, signal?: AbortSignal | undefined | undefined): Promise<Record<string, unknown>> {
    return this.#request({ method: 'GET', base: this.#options.marketEndpoint, path, params, signal })
  }

  /** Signed request on the selected environment. */
  async signedRequest(method: 'GET' | 'POST', path: string, params: Record<string, unknown>, signal?: AbortSignal | undefined | undefined): Promise<Record<string, unknown>> {
    return this.#request({ method, base: this.tradingBase, path, params, signed: true, signal })
  }

  /** 24h ticker snapshot for one symbol. */
  async ticker({ category, symbol, signal }: { category: Category, symbol: string, signal?: AbortSignal | undefined }): Promise<Ticker> {
    const result = await this.publicRequest('/v5/market/tickers', { category, symbol }, signal)
    const row = (result.list as Array<Record<string, unknown>> | undefined)?.[0]
    if (row === undefined) throw new BybitError(`Bybit returned no ticker for ${symbol}`)
    return {
      symbol: String(row.symbol),
      category,
      last: num(row.lastPrice),
      change24hPct: num(row.price24hPcnt) * 100,
      high24h: num(row.highPrice24h),
      low24h: num(row.lowPrice24h),
      volume24h: num(row.volume24h),
      turnover24h: num(row.turnover24h),
      bid: num(row.bid1Price),
      ask: num(row.ask1Price),
      markPrice: num(row.markPrice) || undefined,
      indexPrice: num(row.indexPrice) || undefined,
      fundingRate: row.fundingRate === undefined ? undefined : num(row.fundingRate) * 100,
      openInterest: row.openInterest === undefined ? undefined : num(row.openInterest),
      time: Date.now(),
    }
  }

  /** Candles as oldest-first bars. Bybit returns newest first; this reverses it. */
  async klines({ category, symbol, interval, limit = 200, signal }: {
    category: Category
    symbol: string
    interval: string
    limit?: number
    signal?: AbortSignal | undefined | undefined
  }): Promise<Candle[]> {
    const result = await this.publicRequest(
      '/v5/market/kline',
      { category, symbol, interval, limit: Math.min(Math.max(Math.trunc(limit), 2), 1000) },
      signal,
    )
    const rows = Array.isArray(result.list) ? (result.list as string[][]) : []
    const bars: Candle[] = rows.map(row => ({
      t: Number(row[0]), o: num(row[1]), h: num(row[2]), l: num(row[3]), c: num(row[4]), v: num(row[5]),
    }))
    bars.sort((left, right) => left.t - right.t)
    return bars
  }

  /** Top-of-book depth for one symbol. */
  async orderbook({ category, symbol, limit = 10, signal }: {
    category: Category
    symbol: string
    limit?: number
    signal?: AbortSignal | undefined
  }): Promise<OrderBookSnapshot> {
    const result = await this.publicRequest(
      '/v5/market/orderbook',
      { category, symbol, limit: Math.min(Math.max(Math.trunc(limit), 1), 50) },
      signal,
    )
    return {
      symbol,
      category,
      bids: mapLevels(result.b),
      asks: mapLevels(result.a),
      time: Number(result.ts ?? Date.now()),
    }
  }

  /** Recent funding settlements for a perpetual. */
  async funding({ category, symbol, limit = 8, signal }: {
    category: Category
    symbol: string
    limit?: number
    signal?: AbortSignal | undefined
  }): Promise<FundingRate[]> {
    const result = await this.publicRequest(
      '/v5/market/funding/history',
      { category, symbol, limit: Math.min(Math.max(Math.trunc(limit), 1), 50) },
      signal,
    )
    const rows = Array.isArray(result.list) ? (result.list as Array<Record<string, unknown>>) : []
    return rows.map(row => ({
      symbol: String(row.symbol),
      ratePct: num(row.fundingRate) * 100,
      time: Number(row.fundingRateTimestamp),
    }))
  }

  /** Contract or spot instrument metadata, including quantity and price steps. */
  async instrument({ category, symbol, signal }: { category: Category, symbol: string, signal?: AbortSignal | undefined }): Promise<Instrument> {
    const result = await this.publicRequest('/v5/market/instruments-info', { category, symbol }, signal)
    const row = (result.list as Array<Record<string, unknown>> | undefined)?.[0]
    if (row === undefined) throw new BybitError(`unknown ${category} symbol ${symbol}`)
    return mapInstrument(row, category)
  }

  /**
   * Full instrument catalogue for one category. Bybit returns at most 1000 rows
   * per page; both supported categories fit today.
   */
  async instruments({ category, limit = 1000, signal }: { category: Category, limit?: number, signal?: AbortSignal | undefined }): Promise<Instrument[]> {
    const result = await this.publicRequest('/v5/market/instruments-info', { category, limit }, signal)
    const rows = Array.isArray(result.list) ? (result.list as Array<Record<string, unknown>>) : []
    return rows.map(row => mapInstrument(row, category))
  }

  /**
   * Wallet balance. A key belongs to either a Unified Trading Account or a
   * classic one, so the unified view is tried first and the answer reports which
   * account type replied.
   */
  async walletBalance({ accountType, signal }: { accountType?: string, signal?: AbortSignal | undefined } = {}): Promise<WalletBalance> {
    const candidates = accountType === undefined ? ['UNIFIED', 'CONTRACT', 'SPOT'] : [accountType]
    let lastError: unknown
    for (const type of candidates) {
      try {
        const result = await this.signedRequest('GET', '/v5/account/wallet-balance', { accountType: type }, signal)
        const account = (result.list as Array<Record<string, unknown>> | undefined)?.[0]
        if (account === undefined) {
          return { accountType: type, totalEquityUsd: 0, availableUsd: 0, coins: [], time: Date.now() }
        }
        const coins = Array.isArray(account.coin) ? (account.coin as Array<Record<string, unknown>>) : []
        return {
          accountType: type,
          totalEquityUsd: num(account.totalEquity),
          availableUsd: num(account.totalAvailableBalance),
          coins: coins
            .filter(coin => num(coin.walletBalance) !== 0)
            .map(coin => ({
              coin: String(coin.coin),
              walletBalance: num(coin.walletBalance),
              usdValue: num(coin.usdValue),
            })),
          time: Date.now(),
        }
      } catch (error) {
        lastError = error
      }
    }
    throw lastError instanceof Error ? lastError : new BybitError('wallet-balance failed for every account type')
  }

  /**
   * Facts about the API key itself: which account and sub-account it belongs to,
   * its permissions, its IP bind, and when it expires.
   */
  async apiKeyInfo({ signal }: { signal?: AbortSignal | undefined } = {}): Promise<ApiKeyInfo> {
    const result = await this.signedRequest('GET', '/v5/user/query-api', {}, signal)
    const permissions = (result.permissions ?? {}) as Record<string, unknown>
    return {
      apiKeyTail: typeof result.apiKey === 'string' ? (result.apiKey as string).slice(-4) : undefined,
      isSubAccount: Number(result.inviterID ?? 0) > 0,
      note: String(result.note ?? ''),
      userID: result.userID === undefined ? undefined : Number(result.userID),
      inviterID: result.inviterID === undefined ? undefined : Number(result.inviterID),
      readOnly: Number(result.readOnly ?? 0) === 1,
      unified: result.unified === 1 || result.unified === true,
      uta: result.uta === 1 || result.uta === true,
      ips: result.ips === undefined || result.ips === '' ? [] : String(result.ips).split(','),
      permissions: Object.fromEntries(
        Object.entries(permissions).filter(([, value]) => Array.isArray(value) && value.length > 0),
      ),
      expiredAt: result.expiredAt === undefined ? undefined : Number(result.expiredAt),
      deadlineDay: result.deadlineDay === undefined ? undefined : Number(result.deadlineDay),
    }
  }

  /** Open perpetual positions. */
  async positions({ category = 'linear', symbol, signal }: { category?: Category, symbol?: string, signal?: AbortSignal | undefined } = {}): Promise<Position[]> {
    const scope = symbol === undefined ? { settleCoin: 'USDT' } : { symbol }
    const result = await this.signedRequest('GET', '/v5/position/list', { category, ...scope }, signal)
    const rows = Array.isArray(result.list) ? (result.list as Array<Record<string, unknown>>) : []
    return rows
      .filter(position => num(position.size) !== 0)
      .map(position => ({
        symbol: String(position.symbol),
        side: String(position.side),
        size: num(position.size),
        avgPrice: num(position.avgPrice),
        markPrice: num(position.markPrice),
        leverage: num(position.leverage),
        unrealizedPnlUsd: num(position.unrealisedPnl),
        liquidationPrice: num(position.liqPrice) || undefined,
        takeProfit: num(position.takeProfit) || undefined,
        stopLoss: num(position.stopLoss) || undefined,
      }))
  }

  /** Open orders. */
  async openOrders({ category = 'linear', symbol, signal }: { category?: Category, symbol?: string, signal?: AbortSignal | undefined } = {}): Promise<OpenOrder[]> {
    const scope = symbol === undefined
      ? category === 'linear' ? { settleCoin: 'USDT' } : { baseCoin: 'USDT' }
      : { symbol }
    const result = await this.signedRequest('GET', '/v5/order/realtime', { category, ...scope }, signal)
    const rows = Array.isArray(result.list) ? (result.list as Array<Record<string, unknown>>) : []
    return rows.map(order => ({
      orderId: String(order.orderId),
      symbol: String(order.symbol),
      side: String(order.side),
      orderType: String(order.orderType),
      qty: num(order.qty),
      price: num(order.price) || undefined,
      triggerPrice: num(order.triggerPrice) || undefined,
      orderStatus: String(order.orderStatus),
      createdTime: Number(order.createdTime),
    }))
  }

  /** Create one order. */
  async createOrder(input: CreateOrderInput): Promise<Record<string, unknown>> {
    const { category, symbol, side, orderType, qty, price, timeInForce, reduceOnly, signal } = input
    const params: Record<string, unknown> = { category, symbol, side, orderType, qty }
    if (price !== undefined) params.price = price
    if (timeInForce !== undefined) params.timeInForce = timeInForce
    if (reduceOnly === true && category === 'linear') params.reduceOnly = true
    return this.signedRequest('POST', '/v5/order/create', params, signal)
  }

  /** Cancel one order. */
  async cancelOrder({ category, symbol, orderId, signal }: {
    category: Category
    symbol: string
    orderId: string
    signal?: AbortSignal | undefined
  }): Promise<Record<string, unknown>> {
    return this.signedRequest('POST', '/v5/order/cancel', { category, symbol, orderId }, signal)
  }

  /** Cancel every open order for a symbol or category. */
  async cancelAll({ category, symbol, signal }: { category: Category, symbol?: string, signal?: AbortSignal | undefined }): Promise<Record<string, unknown>> {
    return this.signedRequest('POST', '/v5/order/cancel-all', { category, symbol }, signal)
  }
}
