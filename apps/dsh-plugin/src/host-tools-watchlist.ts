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
 * Watchlist tools only validate symbols and never submit exchange orders.
 *
 * Tool definitions are plain objects with raw JSON Schema parameters, so the
 * bundle imports nothing from the dsh installation and installs as a
 * dependency-free linked directory.
 */
import { intervalLabel, normalizeCategory, normalizeInterval, normalizeSymbol } from './lib/bybit.js'




import { SIGNAL_SOURCES, evaluateSignals } from './lib/signals.js'


import { pick, round2 } from './lib/host-config.js'
import { selectAiSymbols } from './lib/ai-universe.js'


import type { HostRuntime } from './host-runtime.js'

export function registerTools(runtime: HostRuntime): void {
  const { ctx, tool, settings, client, store, watchlist, saveWatchlist, getAiUniverse } = runtime

  ctx.tools.register(tool({
    name: 'quant_watchlist',
    description:
      'List or change the AI eligible candidate universe. This defines which symbols the AI may analyze or choose; it is not a trade command '
      + 'and does not require trading every listed symbol. The dashboard market-view filters are separate.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['action'],
      properties: {
        action: { type: 'string', enum: ['list', 'set', 'add', 'remove'], description: 'list reads the watchlist, set replaces it, add/remove changes one symbol.' },
        symbols: { type: 'array', items: { type: 'string' }, description: 'Symbols for set (1-6 entries).' },
        symbol: { type: 'string', description: 'Symbol for add or remove.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Category used to verify the symbol; defaults to linear.' },
      },
    },
    async run(args, exec) {
      const action = pick(args.action, ['list', 'set', 'add', 'remove'], 'action')
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      if (action === 'list') {
        const stored = store.get().watchlist ?? []
        const universe = await getAiUniverse(category, exec.signal)
        return {
          action,
          symbols: watchlist(),
          source: stored.length > 0 ? 'user allow-list' : settings.aiSymbols.length > 0 ? 'plugin config allow-list' : 'dynamic discovery',
          candidateUniverse: universe,
          note: 'This allow-list only narrows dynamic discovery; an empty list means no symbol restriction. The AI chooses among eligible candidates or abstains. Dashboard filters never change this universe.',
        }
      }

      const verify = async (symbol: string): Promise<string> => {
        normalizeSymbol(symbol)
        await client.instrument({ category, symbol, signal: exec.signal })
        return symbol
      }

      if (action === 'set') {
        const input = Array.isArray(args.symbols) ? args.symbols : []
        if (input.length === 0) throw new Error('set needs at least one symbol')
        if (input.length > 6) throw new Error('keep the watchlist at six symbols or fewer')
        const symbols: string[] = []
        for (const item of input) {
          const symbol = normalizeSymbol(item)
          if (!symbols.includes(symbol)) symbols.push(symbol)
        }
        for (const symbol of symbols) await verify(symbol)
        saveWatchlist(symbols)
        return { action, symbols: watchlist(), verified: symbols }
      }

      if (args.symbol === undefined) throw new Error(`${action} needs symbol`)
      const symbol = normalizeSymbol(args.symbol)
      if (action === 'add') {
        const current = watchlist()
        if (current.includes(symbol)) return { action, symbols: current, note: `${symbol} is already on the watchlist` }
        if (current.length >= 6) throw new Error('the watchlist already holds six symbols; remove one first')
        await verify(symbol)
        saveWatchlist([...current, symbol])
        return { action, symbols: watchlist(), verified: symbol }
      }

      const current = watchlist()
      const next = current.filter(item => item !== symbol)
      if (next.length === current.length) throw new Error(`${symbol} is not on the watchlist`)
      saveWatchlist(next)
      return { action, symbols: watchlist(), removed: symbol, note: next.length === 0 ? 'dynamic discovery or the plugin config allow-list applies again' : undefined }
    },
  }))


  ctx.tools.register(tool({
    name: 'quant_signals',
    description:
      'Evaluate the curated signal library (Supertrend, Squeeze Momentum, Ichimoku, Donchian, ADX) on one or more symbols '
      + 'and timeframes, and return each signal with a weighted consensus. Objective inputs for a decision, not a verdict.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        symbols: { type: 'array', items: { type: 'string' }, description: 'Optional AI-selected subset of eligible candidates, up to 4; defaults to the candidate universe.' },
        category: { type: 'string', enum: ['linear', 'spot'], description: 'Defaults to linear.' },
        timeframes: { type: 'array', items: { type: 'string' }, description: 'Intervals such as 240, 60, D; defaults to the configured brief timeframes.' },
        bars: { type: 'integer', description: 'Candles per timeframe, 120-500; defaults to 300.' },
      },
    },
    concurrent: true,
    async run(args, exec) {
      const category = normalizeCategory(args.category ?? settings.defaultCategory)
      const universe = await getAiUniverse(category, exec.signal)
      const symbols = args.symbols === undefined ? [] : selectAiSymbols(args.symbols, universe)
      const timeframes = Array.isArray(args.timeframes) && args.timeframes.length > 0
        ? args.timeframes.slice(0, 3).map(item => normalizeInterval(item))
        : settings.aiTimeframes.slice(0, 2)
      const bars = Math.min(Math.max(Math.trunc(Number(args.bars ?? 300)), 120), 500)
      const results = []
      for (const symbol of symbols) {
        const frames = []
        for (const interval of timeframes) {
          const candles = await client.klines({ category, symbol, interval, limit: bars, signal: exec.signal })
          if (candles.length < 80) {
            frames.push({ interval: intervalLabel(interval), error: `only ${candles.length} candles` })
            continue
          }
          const evaluated = evaluateSignals(candles)
          frames.push({
            interval: intervalLabel(interval),
            bias: evaluated.bias,
            score: evaluated.score,
            notes: evaluated.notes,
            supertrend: evaluated.signals.supertrend,
            squeeze: evaluated.signals.squeeze,
            ichimoku: evaluated.signals.ichimoku === null ? null : { state: evaluated.signals.ichimoku.state, tkCross: evaluated.signals.ichimoku.tkCross },
            donchian: evaluated.signals.donchian,
            adx: evaluated.signals.adx,
          })
        }
        const scored = frames.filter(frame => typeof frame.score === 'number')
        results.push({
          symbol,
          category,
          frames,
          consensus: scored.length === 0
            ? null
            : round2(scored.reduce((sum, frame) => sum + frame.score, 0) / scored.length),
        })
      }
      return {
        sources: SIGNAL_SOURCES,
        timeframes: timeframes.map(intervalLabel),
        symbols: results,
        candidateUniverse: universe,
        note: symbols.length === 0
          ? 'No signals were requested. Choose up to four symbols from candidateUniverse and call again; the AI decides whether evidence justifies an action.'
          : 'Weighted consensus: Supertrend 0.30, Ichimoku 0.25, Donchian 0.15, Squeeze momentum 0.15, ADX 0.15. |score| >= 0.3 is a directional bias; otherwise flat.',
      }
    },
  }))

}
