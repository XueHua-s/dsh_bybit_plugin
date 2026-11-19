/**
 * The simulated (paper) book: USDT cash, long positions, and a trade journal.
 * Marks come from the live ticker, so this is a shadow book, never an exchange
 * balance. All mutations go through the store so the Web panel sees the same
 * numbers the agent just printed.
 */
import type { PaperPosition, StateDocument } from './state.js'

/** Taker fee charged on each simulated fill, in basis points. */
export const PAPER_FEE_BPS = 10

/** One marked paper position in the status view. */
export interface PaperStatusPosition {
  key: string
  category: string
  symbol: string
  qty: number
  avgPrice: number
  markPrice: number
  staleMark: boolean
  valueUsd: number
  unrealizedPnlUsd: number
  unrealizedPnlPct: number
}

/** Mark-to-market view of the paper book. */
export interface PaperStatus {
  currency: string
  balanceUsd: number
  positionsValueUsd: number
  equityUsd: number
  startingBalanceUsd: number
  totalReturnPct: number
  realizedPnlUsd: number
  unrealizedPnlUsd: number
  feesPaidUsd: number
  positions: PaperStatusPosition[]
  recentTrades: Array<Record<string, unknown>>
}

/** Result of a simulated entry. */
export interface PaperFill {
  key: string
  quantity: number
  cost: number
  fee: number
  balance: number
  position: PaperPosition
}

/** Result of a simulated exit. */
export interface PaperExit {
  key: string
  quantity: number
  proceeds: number
  fee: number
  realizedPnlUsd: number
  balance: number
}

/** Key used for a position: category and symbol. */
export function positionKey(category: string, symbol: string): string {
  return `${category}:${symbol}`
}

/** Mark-to-market view of the paper book. */
export function paperStatus(state: StateDocument, marks: Record<string, number> = {}): PaperStatus {
  const paper = state.paper
  const positions: PaperStatusPosition[] = Object.entries(paper.positions).map(([key, position]) => {
    const mark = marks[key] ?? position.avgPrice
    const value = position.qty * mark
    const cost = position.qty * position.avgPrice
    return {
      key,
      category: position.category,
      symbol: position.symbol,
      qty: round(position.qty, 8),
      avgPrice: round(position.avgPrice, 6),
      markPrice: round(mark, 6),
      staleMark: marks[key] === undefined,
      valueUsd: round(value, 2),
      unrealizedPnlUsd: round(value - cost, 2),
      unrealizedPnlPct: cost === 0 ? 0 : round(((value - cost) / cost) * 100, 2),
    }
  })
  const positionsValue = positions.reduce((sum, position) => sum + position.valueUsd, 0)
  const equity = paper.balance + positionsValue
  return {
    currency: paper.currency,
    balanceUsd: round(paper.balance, 2),
    positionsValueUsd: round(positionsValue, 2),
    equityUsd: round(equity, 2),
    startingBalanceUsd: round(paper.startingBalance, 2),
    totalReturnPct: paper.startingBalance === 0 ? 0 : round(((equity - paper.startingBalance) / paper.startingBalance) * 100, 2),
    realizedPnlUsd: round(paper.realizedPnlUsd, 2),
    unrealizedPnlUsd: round(positions.reduce((sum, position) => sum + position.unrealizedPnlUsd, 0), 2),
    feesPaidUsd: round(paper.feesPaidUsd, 2),
    positions,
    recentTrades: paper.trades.slice(-8).toReversed() as unknown as Array<Record<string, unknown>>,
  }
}

/** Simulate a long entry. */
export function paperBuy({ state, category, symbol, price, qty, notionalUsd, note }: {
  state: StateDocument
  category: string
  symbol: string
  price: number
  qty?: number | undefined
  notionalUsd?: number | undefined
  note?: string
}): PaperFill {
  assertPrice(price)
  const paper = state.paper
  const quantity = resolveQuantity({ price, qty, notionalUsd })
  const cost = quantity * price
  const fee = cost * (PAPER_FEE_BPS / 10_000)
  if (cost + fee > paper.balance + 1e-9) {
    throw new Error(
      `insufficient paper balance: this buy costs ${String(round(cost + fee, 2))} USDT but only ${String(round(paper.balance, 2))} is free; `
      + 'size it with notionalUsd or reset the book',
    )
  }
  const key = positionKey(category, symbol)
  const existing = paper.positions[key]
  paper.balance -= cost + fee
  paper.feesPaidUsd += fee
  if (existing === undefined) {
    paper.positions[key] = { category, symbol, qty: quantity, avgPrice: price, openedAt: Date.now() }
  } else {
    const totalQty = existing.qty + quantity
    existing.avgPrice = (existing.qty * existing.avgPrice + cost) / totalQty
    existing.qty = totalQty
  }
  paper.trades.push({
    time: Date.now(), side: 'buy', category, symbol, qty: quantity, price, feeUsd: fee, note: note ?? '',
  })
  return { key, quantity, cost, fee, balance: paper.balance, position: paper.positions[key] as PaperPosition }
}

/** Simulate a long exit. */
export function paperSell({ state, category, symbol, price, qty, note }: {
  state: StateDocument
  category: string
  symbol: string
  price: number
  qty?: number
  note?: string
}): PaperExit {
  assertPrice(price)
  const paper = state.paper
  const key = positionKey(category, symbol)
  const position = paper.positions[key]
  if (position === undefined) throw new Error(`no paper position in ${symbol} (${category}) to sell`)
  const quantity = qty === undefined ? position.qty : Number(qty)
  if (!Number.isFinite(quantity) || quantity <= 0) throw new Error('qty must be a positive number')
  if (quantity > position.qty + 1e-9) {
    throw new Error(`cannot sell ${String(quantity)} ${symbol}: the paper position holds only ${String(round(position.qty, 8))}`)
  }
  const proceeds = quantity * price
  const fee = proceeds * (PAPER_FEE_BPS / 10_000)
  const realized = quantity * (price - position.avgPrice) - fee
  paper.balance += proceeds - fee
  paper.feesPaidUsd += fee
  paper.realizedPnlUsd += realized
  position.qty -= quantity
  if (position.qty <= 1e-9) delete paper.positions[key]
  paper.trades.push({
    time: Date.now(), side: 'sell', category, symbol, qty: quantity, price, feeUsd: fee, realizedPnlUsd: realized, note: note ?? '',
  })
  return { key, quantity, proceeds, fee, realizedPnlUsd: realized, balance: paper.balance }
}

/** Restore the starting cash and drop every position and trade. */
export function paperReset(state: StateDocument, startingBalance: number): number {
  state.paper = {
    currency: 'USDT',
    balance: startingBalance,
    startingBalance,
    realizedPnlUsd: 0,
    feesPaidUsd: 0,
    positions: {},
    trades: [],
  }
  return startingBalance
}

/** Reject a mark that cannot price a fill. */
function assertPrice(price: number): void {
  if (!Number.isFinite(price) || price <= 0) throw new Error('a positive mark price is required')
}

/** Accept either an explicit quantity or a USDT notional. */
function resolveQuantity({ price, qty, notionalUsd }: { price: number, qty?: number | undefined, notionalUsd?: number | undefined }): number {
  if (qty !== undefined) {
    const quantity = Number(qty)
    if (!Number.isFinite(quantity) || quantity <= 0) throw new Error('qty must be a positive number')
    return quantity
  }
  const notional = Number(notionalUsd)
  if (!Number.isFinite(notional) || notional <= 0) {
    throw new Error('pass qty (base units) or notionalUsd (quote currency) to size the paper trade')
  }
  return notional / price
}

/** Round for display, normalising negative zero. */
function round(value: number, digits: number): number {
  if (!Number.isFinite(value)) return 0
  const factor = 10 ** digits
  const rounded = Math.round(value * factor) / factor
  return Object.is(rounded, -0) ? 0 : rounded
}
