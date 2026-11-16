export type Translate = (key: string) => string
export type PositionView = { key?: string, symbol: string, side: string, category: string, qty: number, avgPrice: number, entryPrice?: number, markPrice: number, unrealizedPnlUsd: number, unrealizedPnlPct?: number, unrealizedPct?: number }
export type TradeView = { time: number, side: 'buy' | 'sell', symbol: string, qty: number, price: number }
export type CurvePoint = { t: number, e: number }
export type AiView = {
  lastDecision: null | { symbol: string, action: string, confidence?: number, horizonHours: number, status: string, thesis: string, result?: null | { pnlUsd: number, pnlPct: number, reason: string } }
  equityUsd: number
  totalReturnPct: number
  hitRatePct: number | null
  brier: number | null
  closed: number
  limits: { riskPerTradePct: number, maxOpenPositions: number }
  curve: CurvePoint[]
  openPositions: PositionView[]
}
export type PanelPayload = {
  ok?: boolean
  error?: string
  env?: 'live' | 'demo' | 'testnet'
  allowLiveTrading?: boolean
  hasKeys?: boolean
  ticker?: { last: number, change24hPct: number, high24h: number, low24h: number, turnover24h: number, fundingRate?: number }
  paper?: { balanceUsd: number, equityUsd: number, totalReturnPct: number, positions: PositionView[], recentTrades: TradeView[] }
  lastBacktest?: null | { strategy: string, symbol: string, interval: string, metrics: { bars: number, totalReturnPct: number, buyHoldReturnPct: number, maxDrawdownPct: number, winRatePct: number, trades: number, sharpe: number, feeDragPct: number }, curve: CurvePoint[] }
  lastSignal?: null | { target: string, time: string }
  ai?: AiView | null
  klines?: number[][]
  updatedAt?: number
}
export type SnapshotInitial = { data: PanelPayload | null, error: string | null, at: number }
export type PanelContext = {
  effect(effect: () => void | (() => void), label: string): void
  locale: { register(namespace: string, dictionaries: { zh: Record<string, string>, en: Record<string, string> }): void, bind(namespace: string): Translate }
  slots: {
    inject(name: string, callback: () => void): void
    register(definition: Record<string, unknown>, component: (props: Record<string, unknown>) => import('react').ReactNode): void
  }
}
export type PanelProps = { t?: Translate, initial?: SnapshotInitial }
