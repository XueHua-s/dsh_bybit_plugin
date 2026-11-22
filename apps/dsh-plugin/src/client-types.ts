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
  hasKeys?: boolean
  ticker?: { last: number, change24hPct: number, high24h: number, low24h: number, turnover24h: number, fundingRate?: number }
  paper?: { balanceUsd: number, equityUsd: number, totalReturnPct: number, positions: PositionView[], recentTrades: TradeView[] }
  lastBacktest?: null | { strategy: string, symbol: string, interval: string, metrics: { bars: number, totalReturnPct: number, buyHoldReturnPct: number, maxDrawdownPct: number, winRatePct: number, trades: number, sharpe: number, feeDragPct: number }, curve: CurvePoint[] }
  lastSignal?: null | { target: string, time: string }
  ai?: AiView | null
  klines?: number[][]
  updatedAt?: number
  automation?: 'conversation_only' | 'background_simulated_decisions'
  backgroundLoop?: 'disabled' | 'not_configured' | 'environment_rejected' | 'starting' | 'running' | 'idle' | 'backoff' | 'blocked' | 'stopping'
  backgroundLoopIntervalMs?: number
  backgroundLoopEnvironment?: 'testnet' | 'internal_paper' | 'demo' | 'live'
  backgroundLoopReason?: string
  backgroundLoopLastRun?: null | {
    outcome: 'completed' | 'failed'
    decisionsRecorded: number
    latestDecisionId: string | null
    latestDecisionStatus: 'open' | 'flat' | 'rejected' | 'uncertain' | null
    completedAt: number
  }
  backgroundLoopMode?: 'simulated_decisions_only'
  executionAuthority?: 'unavailable'
  accountReadiness?: 'unknown' | 'zero_equity' | 'not_checked'
  aiCandidatePool?: { category: 'spot' | 'linear', status: 'not_checked' | 'fresh' | 'stale', observedAt: number | null, eligibleCount: number, candidates: string[] }
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
