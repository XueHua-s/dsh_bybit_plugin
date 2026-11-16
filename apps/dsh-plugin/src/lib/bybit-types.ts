/** Shared Bybit REST domain types. */
import type { Category } from '@bybit-quant/quant-contracts'
export type { Candle, Category, Instrument, Ticker } from '@bybit-quant/quant-contracts'

/** Trading environment selected in the plugin config. */
export type Env = 'live' | 'demo' | 'testnet'

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
  signal?: AbortSignal | undefined
}
