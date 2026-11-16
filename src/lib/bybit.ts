/**
 * Minimal Bybit v5 REST client for the Bybit quant plugin.
 *
 * Public market data always comes from the live endpoint so a demo or testnet
 * account still sees real prices; signed account and order calls go to the
 * endpoint selected by `env`. No dependency ships with this module: it uses the
 * runtime's global `fetch`, `node:crypto`, and `AbortSignal`.
 */
import { createHmac } from 'node:crypto'

/** Trading environment selected in the plugin config. */
export type Env = 'live' | 'demo' | 'testnet'

/** Instrument categories this client supports. */
export type Category = 'spot' | 'linear'

/** One OHLCV candle, oldest-first in every returned series. */
export interface Candle {
  t: number
  o: number
  h: number
  l: number
  c: number
  v: number
}

/** Endpoint per trading environment. */
export const ENDPOINTS = {
  live: 'https://api.bybit.com',
  demo: 'https://api-demo.bybit.com',
  testnet: 'https://api-testnet.bybit.com',
} as const

/** Market data is read from the live venue even when orders go elsewhere. */
export const MARKET_ENDPOINT = 'https://api.bybit.com'

/** Bybit kline interval codes, in ascending order. */
export const INTERVALS = ['1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M'] as const

/** Human spellings accepted in tool arguments. */
const INTERVAL_ALIASES: Record<string, string> = {
  '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
  '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
  '1d': 'D', '1w': 'W', '1M': 'M',
}

/** Bar duration in ms for lookups that need annualisation. */
const INTERVAL_MS: Record<string, number> = {
  '1': 60_000, '3': 180_000, '5': 300_000, '15': 900_000, '30': 1_800_000,
  '60': 3_600_000, '120': 7_200_000, '240': 14_400_000, '360': 21_600_000,
  '720': 43_200_000, D: 86_400_000, W: 604_800_000, M: 2_592_000_000,
}

/** Error carrying Bybit's business code so callers can report it verbatim. */
export class BybitError extends Error {
  readonly retCode: number | undefined
  readonly retMsg: string | undefined
  readonly endpoint: string | undefined
  readonly status: number | undefined

  constructor(message: string, detail: { retCode?: number, retMsg?: string, endpoint?: string, status?: number } = {}) {
    super(message)
    this.name = 'BybitError'
    this.retCode = detail.retCode
    this.retMsg = detail.retMsg
    this.endpoint = detail.endpoint
    this.status = detail.status
  }
}

/** 24h ticker snapshot. */
export interface Ticker {
  symbol: string
  category: Category
  last: number
  change24hPct: number
  high24h: number
  low24h: number
  volume24h: number
  turnover24h: number
  bid: number
  ask: number
  markPrice: number | undefined
  indexPrice: number | undefined
  fundingRate: number | undefined
  openInterest: number | undefined
  time: number
}

/** Top-of-book depth. */
export interface OrderBookSnapshot {
  symbol: string
  category: Category
  bids: Array<[number, number]>
  asks: Array<[number, number]>
  time: number
}

/** One funding settlement. */
export interface FundingRate {
  symbol: string
  ratePct: number
  time: number
}

/** One tradable instrument and its rules. */
export interface Instrument {
  symbol: string
  category: Category
  status: string
  baseCoin: string
  quoteCoin: string
  contractType: string | undefined
  qtyStep: string | undefined
  minOrderQty: number
  minNotionalUsd: number | undefined
  tickSize: string | undefined
  maxLeverage: number | undefined
  fundingIntervalMinutes: number | undefined
}

/** Wallet balance, with the account type that answered. */
export interface WalletBalance {
  accountType: string
  totalEquityUsd: number
  availableUsd: number
  coins: Array<{ coin: string, walletBalance: number, usdValue: number }>
  time: number
}

/** What the API key itself may do, and which account it belongs to. */
export interface ApiKeyInfo {
  apiKeyTail: string | undefined
  isSubAccount: boolean
  note: string
  userID: number | undefined
  inviterID: number | undefined
  readOnly: boolean
  unified: boolean
  uta: boolean
  ips: string[]
  permissions: Record<string, unknown>
  expiredAt: number | undefined
  deadlineDay: number | undefined
}

/** One open position. */
export interface Position {
  symbol: string
  side: string
  size: number
  avgPrice: number
  markPrice: number
  leverage: number
  unrealizedPnlUsd: number
  liquidationPrice: number | undefined
  takeProfit: number | undefined
  stopLoss: number | undefined
}

/** One open order. */
export interface OpenOrder {
  orderId: string
  symbol: string
  side: string
  orderType: string
  qty: number
  price: number | undefined
  triggerPrice: number | undefined
  orderStatus: string
  createdTime: number
}

/** Input for one order. */
export interface CreateOrderInput {
  category: Category
  symbol: string
  side: string
  orderType: string
  qty: string
  price?: string
  timeInForce?: string
  reduceOnly?: boolean
  signal?: AbortSignal
}

/** Normalise a user-supplied interval to a Bybit code. */
export function normalizeInterval(value: string | undefined): string {
  const raw = (value ?? '').toString().trim()
  if (raw === '') return '60'
  if ((INTERVALS as readonly string[]).includes(raw)) return raw
  const alias = INTERVAL_ALIASES[raw] ?? INTERVAL_ALIASES[raw.toLowerCase()]
  if (alias !== undefined) return alias
  throw new BybitError(`unsupported interval "${raw}"; use one of ${INTERVALS.join(', ')} or 1m/5m/15m/1h/4h/1d`)
}

/** Bar duration for an interval code. */
export function intervalMs(interval: string): number {
  return INTERVAL_MS[interval] ?? (INTERVAL_MS['60'] as number)
}

/** Human label of an interval code. */
export function intervalLabel(interval: string): string {
  for (const [alias, code] of Object.entries(INTERVAL_ALIASES)) {
    if (code === interval) return alias
  }
  return interval
}

/** Spot and linear perpetual are the two categories this plugin supports. */
export function normalizeCategory(value: unknown): Category {
  const raw = (value ?? 'linear').toString().trim().toLowerCase()
  if (raw === 'spot' || raw === 'linear') return raw
  throw new BybitError(`category must be "linear" (USDT perpetual) or "spot", received "${raw}"`)
}

/** A symbol is a plain uppercase ticker such as BTCUSDT. */
export function normalizeSymbol(value: unknown, fallback = 'BTCUSDT'): string {
  const raw = (value ?? fallback).toString().trim().toUpperCase()
  if (!/^[A-Z0-9]{2,20}$/.test(raw)) throw new BybitError(`invalid symbol "${raw}"`)
  return raw
}

/**
 * Round a quantity down to the instrument's step and render it without trailing
 * zeros, which Bybit rejects for some symbols.
 */
export function formatQuantity(value: number, step: string | undefined): string {
  const stepNumber = Number(step)
  if (!Number.isFinite(stepNumber) || stepNumber <= 0) return trimNumber(value)
  const decimals = decimalsOf(step)
  const rounded = Math.floor(value / stepNumber + 1e-9) * stepNumber
  return rounded.toFixed(decimals)
}

/** Decimal places a step string carries. */
function decimalsOf(step: string | undefined): number {
  const text = String(step)
  const dot = text.indexOf('.')
  return dot === -1 ? 0 : text.length - dot - 1
}

/** Compact number text without trailing zeros. */
export function trimNumber(value: number): string {
  if (!Number.isFinite(value)) return '0'
  const text = value.toFixed(8)
  return text.replace(/\.?0+$/, '') || '0'
}

/** Query string in insertion order; Bybit signs this exact text. */
function toQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.append(key, String(value))
  }
  return search.toString()
}

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
  #options: { env: Env, apiKey?: string, apiSecret?: string, recvWindow: number, timeoutMs: number }

  constructor(options: { env?: Env, apiKey?: string, apiSecret?: string, recvWindow?: number, timeoutMs?: number } = {}) {
    const env = options.env ?? 'demo'
    if (!Object.hasOwn(ENDPOINTS, env)) throw new BybitError(`unknown env "${env}"; use live, demo, or testnet`)
    this.#options = {
      env,
      apiKey: options.apiKey,
      apiSecret: options.apiSecret,
      recvWindow: options.recvWindow ?? 5000,
      timeoutMs: options.timeoutMs ?? 15000,
    }
  }

  /** Selected trading environment. */
  get env(): Env {
    return this.#options.env
  }

  /** Base URL used for account and order endpoints. */
  get tradingBase(): string {
    return ENDPOINTS[this.#options.env]
  }

  /** Whether an API key pair is configured. */
  get hasCredentials(): boolean {
    return Boolean(this.#options.apiKey && this.#options.apiSecret)
  }

  /** Perform one request and unwrap Bybit's envelope. */
  async #request({ method, base, path, params = {}, signed = false, signal }: {
    method: 'GET' | 'POST'
    base: string
    path: string
    params?: Record<string, unknown>
    signed?: boolean
    signal?: AbortSignal
  }): Promise<Record<string, any>> {
    const query = method === 'GET' ? toQuery(params) : ''
    const body = method === 'GET' ? '' : JSON.stringify(params)
    const url = `${base}${path}${query === '' ? '' : `?${query}`}`
    const headers: Record<string, string> = { accept: 'application/json' }
    if (body !== '') headers['content-type'] = 'application/json'
    if (signed) {
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
      throw new BybitError(describeTransportError(error, base), { endpoint: path })
    }

    const text = await response.text()
    let payload: Record<string, any>
    try {
      payload = JSON.parse(text) as Record<string, any>
    } catch {
      throw new BybitError(`Bybit returned a non-JSON response (HTTP ${String(response.status)})`, {
        endpoint: path, status: response.status,
      })
    }
    if (payload.retCode !== 0) {
      throw new BybitError(`Bybit ${path} failed: ${String(payload.retMsg ?? 'unknown error')} (retCode ${String(payload.retCode)})`, {
        retCode: Number(payload.retCode), retMsg: String(payload.retMsg ?? ''), endpoint: path, status: response.status,
      })
    }
    return (payload.result ?? {}) as Record<string, any>
  }

  /** Public market request on the live venue. */
  async publicRequest(path: string, params: Record<string, unknown>, signal?: AbortSignal): Promise<Record<string, any>> {
    return this.#request({ method: 'GET', base: MARKET_ENDPOINT, path, params, signal })
  }

  /** Signed request on the selected environment. */
  async signedRequest(method: 'GET' | 'POST', path: string, params: Record<string, unknown>, signal?: AbortSignal): Promise<Record<string, any>> {
    return this.#request({ method, base: this.tradingBase, path, params, signed: true, signal })
  }

  /** 24h ticker snapshot for one symbol. */
  async ticker({ category, symbol, signal }: { category: Category, symbol: string, signal?: AbortSignal }): Promise<Ticker> {
    const result = await this.publicRequest('/v5/market/tickers', { category, symbol }, signal)
    const row = (result.list as Array<Record<string, any>> | undefined)?.[0]
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
    signal?: AbortSignal
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
    signal?: AbortSignal
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
    signal?: AbortSignal
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
  async instrument({ category, symbol, signal }: { category: Category, symbol: string, signal?: AbortSignal }): Promise<Instrument> {
    const result = await this.publicRequest('/v5/market/instruments-info', { category, symbol }, signal)
    const row = (result.list as Array<Record<string, any>> | undefined)?.[0]
    if (row === undefined) throw new BybitError(`unknown ${category} symbol ${symbol}`)
    return mapInstrument(row, category)
  }

  /**
   * Full instrument catalogue for one category. Bybit returns at most 1000 rows
   * per page; both supported categories fit today.
   */
  async instruments({ category, limit = 1000, signal }: { category: Category, limit?: number, signal?: AbortSignal }): Promise<Instrument[]> {
    const result = await this.publicRequest('/v5/market/instruments-info', { category, limit }, signal)
    const rows = Array.isArray(result.list) ? (result.list as Array<Record<string, any>>) : []
    return rows.map(row => mapInstrument(row, category))
  }

  /**
   * Wallet balance. A key belongs to either a Unified Trading Account or a
   * classic one, so the unified view is tried first and the answer reports which
   * account type replied.
   */
  async walletBalance({ accountType, signal }: { accountType?: string, signal?: AbortSignal } = {}): Promise<WalletBalance> {
    const candidates = accountType === undefined ? ['UNIFIED', 'CONTRACT', 'SPOT'] : [accountType]
    let lastError: unknown
    for (const type of candidates) {
      try {
        const result = await this.signedRequest('GET', '/v5/account/wallet-balance', { accountType: type }, signal)
        const account = (result.list as Array<Record<string, any>> | undefined)?.[0]
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
  async apiKeyInfo({ signal }: { signal?: AbortSignal } = {}): Promise<ApiKeyInfo> {
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
  async positions({ category = 'linear', symbol, signal }: { category?: Category, symbol?: string, signal?: AbortSignal } = {}): Promise<Position[]> {
    const result = await this.signedRequest('GET', '/v5/position/list', { category, symbol }, signal)
    const rows = Array.isArray(result.list) ? (result.list as Array<Record<string, any>>) : []
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
  async openOrders({ category = 'linear', symbol, signal }: { category?: Category, symbol?: string, signal?: AbortSignal } = {}): Promise<OpenOrder[]> {
    const result = await this.signedRequest('GET', '/v5/order/realtime', { category, symbol }, signal)
    const rows = Array.isArray(result.list) ? (result.list as Array<Record<string, any>>) : []
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
  async createOrder(input: CreateOrderInput): Promise<Record<string, any>> {
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
    signal?: AbortSignal
  }): Promise<Record<string, any>> {
    return this.signedRequest('POST', '/v5/order/cancel', { category, symbol, orderId }, signal)
  }

  /** Cancel every open order for a symbol or category. */
  async cancelAll({ category, symbol, signal }: { category: Category, symbol?: string, signal?: AbortSignal }): Promise<Record<string, any>> {
    return this.signedRequest('POST', '/v5/order/cancel-all', { category, symbol }, signal)
  }
}

/** Map raw price levels to `[price, size]` pairs. */
function mapLevels(rows: unknown): Array<[number, number]> {
  return Array.isArray(rows) ? (rows as string[][]).map(row => [num(row[0]), num(row[1])]) : []
}

/** Map one raw instrument row to the shared shape. */
function mapInstrument(row: Record<string, any>, category: Category): Instrument {
  const lot = (row.lotSizeFilter ?? {}) as Record<string, unknown>
  const price = (row.priceFilter ?? {}) as Record<string, unknown>
  const leverage = (row.leverageFilter ?? {}) as Record<string, unknown>
  return {
    symbol: String(row.symbol),
    category,
    status: String(row.status ?? ''),
    baseCoin: String(row.baseCoin ?? ''),
    quoteCoin: String(row.quoteCoin ?? ''),
    contractType: row.contractType ?? (category === 'spot' ? 'Spot' : undefined),
    qtyStep: (lot.qtyStep ?? lot.basePrecision) as string | undefined,
    minOrderQty: num(lot.minOrderQty ?? lot.minOrderAmt),
    minNotionalUsd: num(lot.minNotionalValue) || undefined,
    tickSize: price.tickSize as string | undefined,
    maxLeverage: num(leverage.maxLeverage) || undefined,
    fundingIntervalMinutes: num(row.fundingInterval) || undefined,
  }
}

/** Parse a Bybit numeric string, treating absent values as 0. */
function num(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}
