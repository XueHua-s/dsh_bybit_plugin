/** Stable data contracts shared by quant analysis and decision modules. */
export type DecisionAction = 'long' | 'short' | 'flat'
export interface AgentDecision {
  symbol: string
  action: DecisionAction
  sizePct: number
  confidence: number
  stopPct: number
  takePct: number
  horizonHours: number
  thesis: string
  invalidation: string
}
export interface TrackPosition {
  symbol: string
  side: 'long' | 'short'
  entryPrice: number
  notionalUsd: number
  qty: number
  stopPrice: number
  takePrice: number | null
  openedAt: number
  horizonHours: number
  decisionId: string
  entryFeeUsd: number
}
export interface DecisionResult {
  exitPrice: number
  exitTime: number
  reason: string
  pnlUsd: number
  pnlPct: number
  rMultiple: number | null
  bars: number
}
export interface JournalDecision extends AgentDecision {
  id: string
  time: number
  priceAtDecision: number
  briefHash: string
  context: unknown
  status: 'open' | 'closed' | 'flat' | 'rejected'
  gate: { allowed: boolean, reasons: string[] } | null
  result: DecisionResult | null
}
export interface DecisionTrack {
  version: 1
  createdAt: number
  startEquity: number
  equity: number
  peakEquity: number
  maxDrawdownPct: number
  feesPaidUsd: number
  dayKey: string
  dayStartEquity: number
  positions: Record<string, TrackPosition>
  decisions: JournalDecision[]
  equityCurve: Array<{ t: number, e: number }>
}
export interface RiskConfig {
  aiRiskPerTradePct: number
  aiMaxPositionPct: number
  aiMaxOpenPositions: number
  aiMaxDailyLossPct: number
  aiMaxDrawdownPct: number
}

export interface RiskGateResult {
  allowed: boolean
  checks: Array<{ name: string, ok: boolean, detail: string }>
  reasons: string[]
  notional?: number
  riskUsd?: number
}
export interface MarketBriefSymbol {
  symbol: string
  price: number
  primary: Record<string, unknown>
  fundingRatePct: number | null
  book?: { imbalancePct?: number, spreadBps?: number | null }
}
export interface MarketBrief {
  at: string
  symbols: MarketBriefSymbol[]
}
