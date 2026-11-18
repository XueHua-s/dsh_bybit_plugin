/**
 * Bybit quant plugin, Host half.
 *
 * Registers five model-facing tools over one shared Bybit client and one shared
 * paper book, contributes a short prompt note, and serves one read-only JSON
 * route for the Web panel on the connection bridge, which carries the Web GUI's
 * Host/Origin fence and browser authentication:
 *
 *   GET /api/bybit-quant            ticker, candles, paper book, last backtest
 *   GET /api/bybit-quant?view=health  plugin and environment facts
 *
 * AI decisions update the simulated journal only; exchange writes are unavailable.
 *
 * Tool definitions are plain objects with raw JSON Schema parameters, so the
 * bundle imports nothing from the dsh installation and installs as a
 * dependency-free linked directory.
 */
import { normalizeCategory, normalizeSymbol } from './lib/bybit.js'







import type { Candle } from './lib/bybit.js'
import { compactDecision, round2 } from './lib/host-config.js'
import { buildBrief, buildSymbolBrief, closePosition, compactContext, DECISION_SCHEMA, briefHashOf, markedEquity, normalizeDecision, openPosition, recordDecision, riskGate, scoreTrack, settleTrack } from './lib/ai.js'
import { evidenceEnvelope } from './lib/trust.js'

import type { HostRuntime } from './host-runtime.js'

export function registerTools(runtime: HostRuntime): void {
  const { ctx, tool, settings, client, store, watchlist, tradableSymbols, aiTrack, aiLimits } = runtime

  ctx.tools.register(tool({
    name: 'quant_brief',
    description:
      'Build the AI decision brief: multi-timeframe trend and volatility for each symbol, funding, order-book imbalance, '
      + 'and the risk limits a decision must respect. Read this, then call quant_decide once per symbol you trade.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        symbols: { type: 'array', items: { type: 'string' }, description: 'Symbols to cover, up to 4; defaults to the configured AI symbols.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
      },
    },
    async run(args, exec) {
      if (!settings.aiEnabled) throw new Error('the AI track is disabled (aiEnabled: false)')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const symbols = Array.isArray(args.symbols) && args.symbols.length > 0
        ? args.symbols.slice(0, 4).map(item => normalizeSymbol(item))
        : watchlist().slice(0, 4)
      const brief = await buildBrief({
        client, symbols, category, timeframes: settings.aiTimeframes, signal: exec.signal, limits: aiLimits(),
      })
      const track = aiTrack()
      return {
        brief,
        decisionSchema: DECISION_SCHEMA,
        track: {
          equityUsd: markedEquity(track, {}).equity,
          openPositions: Object.keys(track.positions),
          decisions: track.decisions.length,
        },
        next: 'Call quant_decide once per symbol. Flat is a valid decision; size so a stop hit costs no more than the per-trade risk budget.',
      }
    },
  }))


  ctx.tools.register(tool({
    name: 'quant_decide',
    description:
      'Record and act on one AI decision. The risk gate checks per-trade risk, position cap, open positions, daily loss and drawdown; '
      + 'an accepted directional decision opens a simulated position on the AI track with the stop and horizon you declare, '
      + 'a flat decision closes the symbol\'s position, and a rejected decision is journaled without a fill.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['symbol', 'action', 'confidence', 'thesis', 'invalidation', 'horizonHours'],
      properties: {
        symbol: { type: 'string', description: 'One of the brief symbols.' },
        action: { type: 'string', enum: ['long', 'short', 'flat'], description: 'Directional view or no trade.' },
        sizePct: { type: 'number', description: 'Percent of AI equity used as notional, 1-100; ignored for flat.' },
        confidence: { type: 'number', description: 'Probability this decision makes money, 0-1. Used for calibration scoring.' },
        stopPct: { type: 'number', description: 'Stop distance from entry in percent, 0.2-20.' },
        takePct: { type: 'number', description: 'Take-profit distance in percent, 0-50; 0 means no take-profit.' },
        horizonHours: { type: 'integer', description: 'Hours the thesis stays valid, 1-240; the position closes at market when it expires.' },
        thesis: { type: 'string', description: 'One or two sentences a reviewer could falsify.' },
        invalidation: { type: 'string', description: 'The observable event that proves the thesis wrong.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
      },
    },
    async run(args, exec) {
      if (!settings.aiEnabled) throw new Error('the AI track is disabled (aiEnabled: false)')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const track = aiTrack()
      const now = Date.now()
      const decision = normalizeDecision({ ...args, symbol: normalizeSymbol(args.symbol) }, { symbols: tradableSymbols() })

      // Settle what is already open before taking a new view.
      const openSymbols = Object.keys(track.positions)
      const marks: Record<string, number> = {}
      const barsBySymbol: Record<string, Candle[]> = {}
      for (const symbol of new Set([...openSymbols, decision.symbol])) {
        const ticker = await client.ticker({ category, symbol, signal: exec.signal })
        marks[symbol] = ticker.last
        if (openSymbols.includes(symbol)) {
          barsBySymbol[symbol] = await client.klines({ category, symbol, interval: '60', limit: 500, signal: exec.signal })
        }
      }
      const settled = settleTrack({ track, barsBySymbol, marks, now, feeBps: settings.aiFeeBps })

      const price = marks[decision.symbol]
      if (price === undefined) throw new Error(`no market price available for ${decision.symbol}`)
      const gate = riskGate({ decision, track, price, cfg: settings, now })
      const brief = await buildSymbolBrief({ client, symbol: decision.symbol, category, timeframes: settings.aiTimeframes, signal: exec.signal })
      const status = decision.action === 'flat' ? 'flat' : gate.allowed ? 'open' : 'rejected'
      const entry = recordDecision(track, decision, {
        price,
        now,
        briefHash: briefHashOf(brief),
        context: compactContext({ at: new Date(now).toISOString(), symbols: [brief] }),
        gate,
        status,
      })
      let position = null
      let closed = null
      if (status === 'open') {
        position = openPosition({ track, decision: entry, price, now, feeBps: settings.aiFeeBps })
      } else if (status === 'flat') {
        closed = closePosition({ track, symbol: decision.symbol, price, reason: 'model-flat', now, feeBps: settings.aiFeeBps })
      }
      store.mutate(() => null)

      return {
        accepted: status === 'open' || status === 'flat',
        status,
        decision: {
          id: entry.id,
          symbol: entry.symbol,
          action: entry.action,
          sizePct: entry.sizePct,
          stopPct: entry.stopPct,
          takePct: entry.takePct,
          horizonHours: entry.horizonHours,
          confidence: entry.confidence,
          evidence: {
            thesis: evidenceEnvelope(entry.thesis, 'agent'),
            invalidation: evidenceEnvelope(entry.invalidation, 'agent'),
          },
        },
        price,
        gate: { allowed: gate.allowed, checks: gate.checks, reasons: gate.reasons },
        position,
        closed,
        settled,
        track: markedEquity(track, marks),
        limits: aiLimits(),
        note: status === 'rejected'
          ? 'The risk gate refused this decision and it was journaled without a fill. Reduce sizePct or tighten stopPct, or decide flat.'
          : 'The decision is journaled with its brief hash, thesis, and invalidation; quant_review scores it later.',
      }
    },
  }))


  ctx.tools.register(tool({
    name: 'quant_review',
    description:
      'Score the AI track: hit rate, expectancy, average R, confidence calibration (Brier), max drawdown, recent and worst '
      + 'decisions with their results, and a buy-and-hold baseline over the same window. Use it to decide whether the process is working.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
        decisions: { type: 'integer', description: 'How many recent decisions to include, 1-15; defaults to 6.' },
      },
    },
    async run(args, exec) {
      if (!settings.aiEnabled) throw new Error('the AI track is disabled (aiEnabled: false)')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const track = aiTrack()
      const now = Date.now()
      const marks: Record<string, number> = {}
      const barsBySymbol: Record<string, Candle[]> = {}
      for (const symbol of Object.keys(track.positions)) {
        const ticker = await client.ticker({ category, symbol, signal: exec.signal })
        marks[symbol] = ticker.last
        barsBySymbol[symbol] = await client.klines({ category, symbol, interval: '60', limit: 500, signal: exec.signal })
      }
      const settled = settleTrack({ track, barsBySymbol, marks, now, feeBps: settings.aiFeeBps })
      const scorecard = scoreTrack({ track, marks })
      const limit = Math.min(Math.max(Math.trunc(Number(args.decisions ?? 6)), 1), 15)
      const recent = track.decisions.slice(-limit).toReversed().map(compactDecision)
      const worst = track.decisions
        .filter(entry => entry.status === 'closed' && entry.result !== null && entry.result.pnlUsd < 0)
        .sort((left, right) => (left.result?.pnlUsd ?? 0) - (right.result?.pnlUsd ?? 0))
        .slice(0, 3)
        .map(compactDecision)

      let baseline = null
      const reference = watchlist()[0] ?? settings.aiSymbols[0]
      if (reference !== undefined) {
        const bars = await client.klines({ category, symbol: reference, interval: '60', limit: 1000, signal: exec.signal })
        const history = bars.filter(bar => bar.t >= track.createdAt)
        const first = history[0]
        const last = history.at(-1)
        if (first !== undefined && last !== undefined && history.length >= 2) {
          baseline = {
            symbol: reference,
            from: new Date(first.t).toISOString(),
            bars: history.length,
            buyHoldPct: round2(((last.c - first.c) / first.c) * 100),
          }
        }
      }
      store.mutate(() => null)

      return {
        settled,
        scorecard,
        baseline,
        comparison: baseline === null ? null : {
          aiPct: scorecard.book.totalReturnPct,
          buyHoldPct: baseline.buyHoldPct,
          deltaPct: round2(scorecard.book.totalReturnPct - baseline.buyHoldPct),
        },
        recent,
        worst,
        limits: aiLimits(),
        note: 'A positive delta over a few dozen decisions is noise, not skill. Watch the Brier score fall and the per-decision expectancy rise before trusting it.',
      }
    },
  }))

}
