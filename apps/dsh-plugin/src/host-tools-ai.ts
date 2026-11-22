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
import type { PaperAiCycleReceipt, PaperAiCycleRequest } from '@bybit-quant/quant-api-client'
import { compactDecision, round2 } from './lib/host-config.js'
import { buildBrief, buildSymbolBrief, closePosition, compactContext, DECISION_SCHEMA, briefHashOf, markedEquity, normalizeDecision, openPosition, recordDecision, riskGate, scoreTrack, settleTrack } from './lib/ai.js'
import { evidenceEnvelope } from './lib/trust.js'
import { decisionSymbols, selectAiSymbols } from './lib/ai-universe.js'
import { persistAiDecision } from './lib/ai-decision-writer.js'
import type { DecisionReceipt } from './lib/ai-scheduler.js'
import { createPaperDecisionRequest, paperUniverse, selectPaperCandidate } from './lib/paper-ai-cycle.js'

import type { HostRuntime } from './host-runtime.js'

export function registerTools(runtime: HostRuntime): void {
  const { ctx, tool, settings, client, engine, paper, store, getAiUniverse, getPaperFixture, aiTrack, aiLimits, aiScheduler } = runtime

  ctx.tools.register(tool({
    name: 'quant_brief',
    description:
      'Build the AI decision brief: multi-timeframe trend and volatility for each symbol, funding, order-book imbalance, '
      + 'and the risk limits a decision must respect. First call without symbols to inspect the fresh candidate snapshot; then select up to four symbols for detailed evidence. Dashboard filters are not inputs.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        symbols: { type: 'array', items: { type: 'string' }, description: 'AI-selected candidate subset to analyze, up to 4. Omit this on the first call to get the candidate snapshot.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
      },
    },
    async run(args, exec) {
      if (!settings.aiEnabled) throw new Error('the AI track is disabled (aiEnabled: false)')
      if (settings.aiBackgroundEnvironment === 'internal_paper') {
        const fixture = await getPaperFixture(exec.signal)
        const selected = args.symbols === undefined
          ? []
          : (Array.isArray(args.symbols)
            ? args.symbols.length <= 4
              ? args.symbols.map(value => selectPaperCandidate(fixture, value))
              : (() => { throw new Error('at most four paper candidates may be selected per cycle') })()
            : (() => { throw new Error('symbols must be an array selected from the current paper fixture universe') })())
        return {
          brief: null,
          candidateUniverse: paperUniverse(fixture),
          decisionSchema: DECISION_SCHEMA,
          selectedSymbols: selected.map(candidate => candidate.symbol),
          selectedCandidates: selected,
          next: selected.length === 0
            ? 'Choose zero to four candidates from the Python-owned paper fixture snapshot, then call quant_brief again with those symbols; abstaining is valid.'
            : 'Use selector_evidence from each selected candidate and submit a strategy-bound simulated decision, or abstain.',
        }
      }
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const universe = await getAiUniverse(category, exec.signal)
      const symbols = args.symbols === undefined ? [] : selectAiSymbols(args.symbols, universe)
      const brief = symbols.length === 0 ? null : await buildBrief({
        client, symbols, category, timeframes: settings.aiTimeframes, signal: exec.signal, limits: aiLimits(),
        researchEvidence: async ({ symbol, category: selectedCategory, interval, bars, fundingRate }) => {
          const result = await engine.strategyEvidence({
            symbol,
            market: selectedCategory,
            interval,
            bars: bars.map(bar => ({
              timestamp_ms: bar.t,
              open: bar.o,
              high: bar.h,
              low: bar.l,
              close: bar.c,
              volume: bar.v,
            })),
            ...(selectedCategory === 'linear' && fundingRate !== undefined ? { funding_rate: fundingRate } : {}),
          }, exec.signal)
          return result.ok
            ? { status: 'available', ...result.data }
            : { status: 'unavailable', code: result.code }
        },
      })
      const track = aiTrack()
      return {
        brief,
        candidateUniverse: universe,
        decisionSchema: DECISION_SCHEMA,
        track: {
          equityUsd: markedEquity(track, {}).equity,
          openPositions: Object.keys(track.positions),
          decisions: track.decisions.length,
        },
        selectedSymbols: symbols,
        next: symbols.length === 0
          ? 'Choose zero to four candidates based on your own analysis, then call quant_brief again with those symbols; abstaining is valid.'
          : 'Decide from the detailed evidence whether any selected symbol merits a simulated decision, or abstain.',
      }
    },
  }))


  const decisionRequired = ['symbol', 'action', 'confidence', 'thesis', 'invalidation', 'horizonHours']
  const decisionProperties: Record<string, unknown> = {
    symbol: { type: 'string', description: 'One of the brief symbols.' },
    action: { type: 'string', enum: ['long', 'short', 'flat'], description: 'Directional view or no trade.' },
    sizePct: { type: 'number', description: 'Percent of AI equity used as notional, 1-100; ignored for flat.' },
    stopPct: { type: 'number', description: 'Stop distance from entry in percent, 0.2-20.' },
    takePct: { type: 'number', description: 'Take-profit distance in percent, 0-50; 0 means no take-profit.' },
    confidence: { type: 'number', description: 'Probability this decision makes money, 0-1. Used for calibration scoring.' },
    horizonHours: { type: 'integer', description: 'Hours the thesis stays valid, 1-240; the position closes at market when it expires.' },
    thesis: { type: 'string', description: 'One or two sentences a reviewer could falsify.' },
    invalidation: { type: 'string', description: 'The observable event that proves the thesis wrong.' },
    category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
    strategyId: { type: 'string', description: 'Internal-paper selector strategy identity from the selected fixture evidence.' },
    strategyVersion: { type: 'string', description: 'Internal-paper selector strategy version from the selected fixture evidence.' },
    evidenceDigest: { type: 'string', description: 'Internal-paper selector evidence digest from the selected fixture evidence.' },
    targetExposure: { type: 'number', description: 'Internal-paper signed target exposure in [-1, 1].' },
  }

  function decisionParameters(backgroundCycleRequired: boolean): Record<string, unknown> {
    const internalPaper = backgroundCycleRequired && settings.aiBackgroundEnvironment === 'internal_paper'
    return {
      type: 'object',
      additionalProperties: false,
      required: internalPaper
        ? ['symbol', 'action', 'strategyId', 'strategyVersion', 'evidenceDigest', 'targetExposure', 'cycleId']
        : backgroundCycleRequired ? [...decisionRequired, 'cycleId'] : decisionRequired,
      properties: {
        ...decisionProperties,
        ...(backgroundCycleRequired
          ? { cycleId: { type: 'string', description: 'Exact current background-cycle receipt correlation id.' } }
          : {}),
      },
    }
  }

  async function runDecision(
    args: Record<string, unknown>,
    exec: { signal?: AbortSignal },
    backgroundCycleRequired: boolean,
  ): Promise<unknown> {
    if (!settings.aiEnabled) throw new Error('the AI track is disabled (aiEnabled: false)')
    let cycleId: string | undefined
    if (backgroundCycleRequired) {
      if (typeof args.cycleId !== 'string' || args.cycleId.trim() === '') {
        throw new Error('cycleId is required for background decisions')
      }
      cycleId = args.cycleId
    } else if (args.cycleId !== undefined) {
      throw new Error('cycleId is accepted only by quant_decide_background')
    }

    if (backgroundCycleRequired && settings.aiBackgroundEnvironment === 'internal_paper') {
      return runInternalPaperDecision(args, exec, cycleId as string)
    }

    let receipt: DecisionReceipt | undefined
    try {
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const currentTrack = aiTrack()
      // Stage accounting on an isolated copy so a failed disk write can retry safely.
      const track = structuredClone(currentTrack)
      const now = Date.now()
      const symbol = normalizeSymbol(args.symbol)
      const action = typeof args.action === 'string' ? args.action.toLowerCase() : ''
      const hasOpenPosition = track.positions[symbol] !== undefined
      let universe = null
      try {
        universe = await getAiUniverse(category, exec.signal)
      } catch (error) {
        if (action !== 'flat' || !hasOpenPosition) throw error
      }
      const decision = normalizeDecision({
        symbol,
        action: args.action,
        sizePct: args.sizePct,
        stopPct: args.stopPct,
        takePct: args.takePct,
        confidence: args.confidence,
        horizonHours: args.horizonHours,
        thesis: args.thesis,
        invalidation: args.invalidation,
      }, {
        symbols: decisionSymbols(universe, action, Object.keys(track.positions)),
      })
      if (cycleId !== undefined) {
        const reservation = aiScheduler.reserveDecisionReceipt(cycleId, decision.symbol)
        if (reservation === undefined) throw new Error('background decision cycle is stale or its receipt limit is reached')
        if (reservation.kind === 'pending') throw new Error('a decision for this symbol is already being persisted in this background cycle')
        if (reservation.kind === 'duplicate') {
          return {
            accepted: reservation.status === 'open' || reservation.status === 'flat',
            status: reservation.status,
            duplicate: true,
            decisionReceipt: {
              cycleId,
              decisionId: reservation.decisionId,
              status: reservation.status,
              persistedAt: reservation.persistedAt,
            },
            note: 'This symbol already has a persisted simulated decision in this cycle; this retry performed no new journal write.',
          }
        }
        receipt = reservation.receipt
      }

      // Settle what is already open before taking a new view.
      const openSymbols = Object.keys(track.positions)
      const marks: Record<string, number> = {}
      const barsBySymbol: Record<string, Candle[]> = {}
      for (const settleSymbol of new Set([...openSymbols, decision.symbol])) {
        const ticker = await client.ticker({ category, symbol: settleSymbol, signal: exec.signal })
        marks[settleSymbol] = ticker.last
        if (openSymbols.includes(settleSymbol)) {
          barsBySymbol[settleSymbol] = await client.klines({ category, symbol: settleSymbol, interval: '60', limit: 500, signal: exec.signal })
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
      const committedReceipt = persistAiDecision({
        store,
        previousTrack: currentTrack,
        nextTrack: track,
        decisionId: entry.id,
        status,
        ...(receipt === undefined ? {} : { receipt }),
      })

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
        ...(committedReceipt === undefined || cycleId === undefined ? {} : { decisionReceipt: { cycleId, ...committedReceipt } }),
        note: status === 'rejected'
          ? 'The risk gate refused this decision and it was journaled without a fill. Reduce sizePct or tighten stopPct, or decide flat.'
          : 'The decision is journaled with its brief hash, thesis, and invalidation; quant_review scores it later.',
      }
    } catch (error) {
      receipt?.release()
      throw error
    }
  }

  async function runInternalPaperDecision(args: Record<string, unknown>, exec: { signal?: AbortSignal }, cycleId: string): Promise<unknown> {
    const reservation = aiScheduler.reserveDecisionReceipt(cycleId, typeof args.symbol === 'string' ? args.symbol.trim().toUpperCase() : '')
    if (reservation === undefined) throw new Error('background decision cycle is stale or its receipt limit is reached')
    if (reservation.kind === 'pending') throw new Error('a decision for this symbol is already being submitted in this background cycle')
    if (reservation.kind === 'duplicate') {
      return { accepted: reservation.status === 'open' || reservation.status === 'flat', status: reservation.status, duplicate: true, decisionReceipt: { cycleId, decisionId: reservation.decisionId, status: reservation.status, persistedAt: reservation.persistedAt } }
    }
    let request: PaperAiCycleRequest | undefined
    let dispatchStarted = false
    const recordUncertainOutcome = (original: PaperAiCycleRequest) => {
      const committed = reservation.receipt.commit(original.decision.decision_id, 'uncertain')
      return {
        accepted: false,
        status: 'uncertain',
        decision: { id: original.decision.decision_id, symbol: original.decision.symbol, action: original.decision.action, targetExposure: original.decision.target_exposure },
        decisionReceipt: { cycleId, ...committed },
        recovery: { action: 'query_request', request_id: original.request_id },
        note: 'The original Python paper-cycle outcome could not be reconciled. The background loop is blocked; do not create a replacement request.',
      }
    }
    try {
      const fixture = await getPaperFixture(exec.signal)
      const action = args.action
      if (action !== 'long' && action !== 'short' && action !== 'flat') throw new Error('internal paper action must be long, short, or flat')
      const strategyId = args.strategyId
      const strategyVersion = args.strategyVersion
      const evidenceDigest = args.evidenceDigest
      const targetExposure = args.targetExposure
      if (typeof targetExposure !== 'number') throw new Error('targetExposure is required for internal paper decisions')
      request = createPaperDecisionRequest({
        sessionId: settings.paperSessionId,
        fixture,
        cycleId,
        symbol: typeof args.symbol === 'string' ? args.symbol : '',
        action,
        targetExposure,
        strategyId: typeof strategyId === 'string' ? strategyId : '',
        strategyVersion: typeof strategyVersion === 'string' ? strategyVersion : '',
        evidenceDigest: typeof evidenceDigest === 'string' ? evidenceDigest : '',
      })
      dispatchStarted = true
      const submitted = await paper.cycle(request, exec.signal)
      let resultData: PaperAiCycleReceipt | undefined
      if (!submitted.ok && submitted.code === 'outcome_uncertain' && submitted.recovery.action === 'query_request') {
        // Resolve only the original identity after an ambiguous transport result.
        // Never create a second request or silently resubmit the model decision.
        const recovered = await paper.cycleRequest(submitted.recovery.request_id, exec.signal)
        if (!recovered.ok) return recordUncertainOutcome(request)
        resultData = recovered.data
      }
      if (!submitted.ok && submitted.code !== 'outcome_uncertain') {
        // A typed, non-ambiguous failure is not a fill. Release the
        // reservation so the same symbol can be retried safely; only
        // transport ambiguity may become an `uncertain` receipt.
        dispatchStarted = false
        throw new Error(`paper cycle unavailable: ${submitted.code}`)
      }
      if (resultData === undefined) {
        if (!submitted.ok) throw new Error(`paper cycle unavailable: ${submitted.code}`)
        resultData = submitted.data
      }
      // An admission/accepted receipt is not a fill and must not be shown as an
      // open position. Only terminal synthetic fills receive an accepted
      // scheduler receipt; all other states stay fail-closed and observable in
      // the raw paper receipt.
      const acceptedStatuses = new Set(['filled'])
      const uncertainStatuses = new Set(['admitted', 'accepted', 'partially_filled', 'protected', 'unknown', 'claimed', 'selected'])
      const accepted = acceptedStatuses.has(resultData.status)
      const uncertain = uncertainStatuses.has(resultData.status)
      const status = accepted ? action === 'flat' ? 'flat' : 'open' : uncertain ? 'uncertain' : 'rejected'
      const committed = reservation.receipt.commit(resultData.decision_id, status)
      return {
        accepted: accepted && !uncertain,
        status,
        decision: { id: resultData.decision_id, symbol: request.decision.symbol, action: request.decision.action, targetExposure: request.decision.target_exposure },
        paperReceipt: resultData,
        decisionReceipt: { cycleId, ...committed },
        note: uncertain
          ? `The Python-owned synthetic cycle returned an uncertain terminal state (${resultData.status}); no retry or Bybit action occurred.`
          : 'The Python-owned synthetic fixture/cycle service is authoritative; no Bybit or local AI journal write occurred.',
      }
    } catch (error) {
      if (dispatchStarted && request !== undefined) return recordUncertainOutcome(request)
      reservation.receipt.release()
      throw error
    }
  }

  ctx.tools.register(tool({
    name: 'quant_decide',
    description:
      'Record one simulated AI decision. The code-owned risk gate checks per-trade risk, position cap, open positions, daily loss and drawdown. Use quant_decide_background only inside the scheduled loop.',
    parameters: decisionParameters(false),
    run: (args, exec) => runDecision(args, exec, false),
  }))

  ctx.tools.register(tool({
    name: 'quant_decide_background',
    description:
      'Scheduled-loop-only simulated decision tool. Requires the exact current cycleId and returns an idempotent write receipt after persistence.',
    parameters: decisionParameters(true),
    run: (args, exec) => runDecision(args, exec, true),
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
      const reference = track.decisions.at(-1)?.symbol
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
