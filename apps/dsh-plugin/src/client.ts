type ReactRuntime = typeof import('react')
import type { AiView, CurvePoint, PanelContext, PanelPayload, PanelProps, SnapshotInitial, Translate } from './client-types.js'

declare global {
  interface Window {
    __ModuleLoader__: {
      load(entry: { id: string, factory: (require: (name: string) => ReactRuntime) => void }): void
    }
  }
}

/**
 * Bybit quant panel, browser half.
 *
 * Contributes a "Bybit" row to the sidebar and a global main panel that polls
 * the Host's authenticated bridge route (`/api/bybit-quant`): live ticker,
 * candles with two SMAs, the simulated paper book, and the last backtest. The
 * panel is read-only by design; acting on a view is the agent's job through the
 * plugin's tools, so no browser path can move money.
 */
import { CSS, en, zh } from './client-assets.js'
import { axisPrice, fmtBarTime, fmtPct, fmtPrice, fmtQty, fmtUsd, sma, tone } from './client-format.js'

window.__ModuleLoader__.load({
  id: '@bybit-quant/dsh-plugin',
  factory(require) {
    const React = require('react')
    const h = React.createElement
    const { useCallback, useEffect, useMemo, useState } = React

    /** Dictionary namespace owned by this plugin. */
    const NS = 'bybitQuant'
    /** Sidebar entry id; also the key of the main panel it opens. */
    const PANEL_ID = 'bybit-quant'
    /** Poll interval for the snapshot. */
    const POLL_MS = 5000
    /** Ticker-only favourites offered in the symbol datalist. */
    const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'BNBUSDT']
    /** Interval choices the panel exposes. */
    const INTERVALS = [
      ['1', '1m'], ['5', '5m'], ['15', '15m'], ['60', '1h'], ['240', '4h'], ['D', '1d'],
    ]



    /**
     * Candlestick chart with two SMAs, drawn as plain SVG with theme tokens.
     * @param {{ klines: number[][], interval: string, t: Function, aria: string }} props
     */
    function CandleChart({ klines, interval, t, aria }: { klines: number[][], interval: string, t: Translate, aria: string }) {
      const model = useMemo(() => {
        if (!Array.isArray(klines) || klines.length < 2) return null
        const width = 1000
        const height = 340
        const pad = { left: 6, right: 62, top: 12, bottom: 22 }
        const plotWidth = width - pad.left - pad.right
        const plotHeight = height - pad.top - pad.bottom
        const closes = klines.map(bar => bar[4] ?? 0)
        const lows = klines.map(bar => bar[3] ?? 0)
        const highs = klines.map(bar => bar[2] ?? 0)
        const min = Math.min(...lows)
        const max = Math.max(...highs)
        const span = max - min || 1
        const step = plotWidth / klines.length
        const bodyWidth = Math.max(step * 0.62, 1)
        const x = (index: number): number => pad.left + step * (index + 0.5)
        const y = (price: number): number => pad.top + ((max - price) / span) * plotHeight
        const fast = sma(closes, 20)
        const slow = sma(closes, 50)
        const line = (series: number[]): string => series
          .map((value, index) => (Number.isNaN(value) ? null : `${x(index).toFixed(1)},${y(value).toFixed(1)}`))
          .filter((point): point is string => point !== null)
          .join(' ')
        const grid = [0, 0.25, 0.5, 0.75, 1].map(ratio => ({
          y: pad.top + plotHeight * ratio,
          price: max - span * ratio,
        }))
        const ticks = [0, Math.floor(klines.length / 2), klines.length - 1].map(index => ({
          x: x(index),
          label: fmtBarTime(klines[index]?.[0] ?? 0, interval !== 'D'),
        }))
        return {
          width, height, pad, step, bodyWidth, span, x, y, grid, ticks,
          candles: klines.map((bar, index) => {
            const open = bar[1] ?? 0
            const high = bar[2] ?? 0
            const low = bar[3] ?? 0
            const close = bar[4] ?? 0
            return {
              index,
              up: close >= open,
              x: x(index),
              bodyTop: y(Math.max(open, close)),
              bodyHeight: Math.max(Math.abs(y(open) - y(close)), 1),
              wickTop: y(high),
              wickBottom: y(low),
            }
          }),
          fastLine: line(fast),
          slowLine: line(slow),
        }
      }, [klines, interval])

      if (model === null) return h('div', { className: 'bq-empty' }, t('empty'))
      const { width, height, pad, bodyWidth, span, grid, ticks, candles, fastLine, slowLine } = model
      return h('svg', {
        className: 'bq-chart',
        viewBox: `0 0 ${width} ${height}`,
        role: 'img',
        'aria-label': aria,
        preserveAspectRatio: 'none',
      },
      h('g', null, grid.map((line, index) => h('g', { key: `grid-${index}` },
        h('line', {
          x1: pad.left, x2: width - pad.right, y1: line.y, y2: line.y, className: 'bq-grid-line',
        }),
        h('text', { x: width - pad.right + 6, y: line.y + 3, className: 'bq-axis-text' }, axisPrice(line.price, span)),
      ))),
      h('g', null, candles.map(candle => h('g', { key: `c-${candle.index}` },
        h('line', {
          x1: candle.x, x2: candle.x, y1: candle.wickTop, y2: candle.wickBottom,
          className: candle.up ? 'bq-up' : 'bq-down', stroke: 'currentColor', strokeWidth: 1,
        }),
        h('rect', {
          x: candle.x - bodyWidth / 2, y: candle.bodyTop, width: bodyWidth, height: candle.bodyHeight,
          className: candle.up ? 'bq-up' : 'bq-down', fill: 'currentColor',
        }),
      ))),
      fastLine === '' ? null : h('polyline', {
        points: fastLine, fill: 'none', stroke: 'var(--dsw-alias-brand-primary)', strokeWidth: 1.4, strokeLinejoin: 'round',
      }),
      slowLine === '' ? null : h('polyline', {
        points: slowLine, fill: 'none', stroke: 'var(--dsw-alias-state-warn-primary)', strokeWidth: 1.4, strokeLinejoin: 'round',
      }),
      h('g', null, ticks.map((tick, index) => h('text', {
        key: `tick-${index}`, x: tick.x, y: height - 6, textAnchor: index === 0 ? 'start' : index === ticks.length - 1 ? 'end' : 'middle',
        className: 'bq-axis-text',
      }, tick.label))),
      )
    }

    /** Tiny equity sparkline for the last backtest. */
    function Sparkline({ curve }: { curve: CurvePoint[] }) {
      const geometry = useMemo(() => {
        if (!Array.isArray(curve) || curve.length < 2) return null
        const values = curve.map(point => point.e)
        const min = Math.min(...values)
        const max = Math.max(...values)
        const span = max - min || 1
        return values.map((value, index) => `${(index / (values.length - 1) * 300).toFixed(1)},${(38 - ((value - min) / span) * 34).toFixed(1)}`).join(' ')
      }, [curve])
      if (geometry === null) return null
      return h('svg', { className: 'bq-spark', viewBox: '0 0 300 40', preserveAspectRatio: 'none', 'aria-hidden': true },
        h('polyline', { points: geometry, fill: 'none', stroke: 'var(--dsw-alias-state-success-primary)', strokeWidth: 1.5, strokeLinejoin: 'round' }))
    }

    /** The AI decision card: book, scorecard, and the latest verdict. */
    function AiPanel({ ai, t }: { ai: AiView | null, t: Translate }) {
      if (ai === null || ai === undefined) return h('div', { className: 'bq-empty' }, t('aiNoDecision'))
      const last = ai.lastDecision
      const actionLabel = last === null
        ? ''
        : last.action === 'long' ? t('aiActionLong') : last.action === 'short' ? t('aiActionShort') : t('aiActionFlat')
      const statusLabel = last === null
        ? ''
        : last.status === 'open' ? t('aiStatusOpen') : last.status === 'closed' ? t('aiStatusClosed') : last.status === 'flat' ? t('aiStatusFlat') : t('aiStatusRejected')
      return h('div', null,
        h('div', { className: 'bq-kv' },
              h(Stat, { label: t('aiEquity'), value: `${fmtUsd(ai.equityUsd)} USDT`, valueClass: '' }),
          h(Stat, { label: t('aiReturn'), value: fmtPct(ai.totalReturnPct), valueClass: tone(ai.totalReturnPct) }),
          h(Stat, { label: t('aiHitRate'), value: ai.hitRatePct === null ? '—' : `${fmtUsd(ai.hitRatePct, 1)}%`, valueClass: '' }),
          h(Stat, { label: t('aiBrier'), value: ai.brier === null ? '—' : String(ai.brier), valueClass: '' }),
          h(Stat, { label: t('aiClosed'), value: String(ai.closed), valueClass: '' }),
          h(Stat, { label: t('aiLimits'), value: `${ai.limits.riskPerTradePct}% · ${ai.limits.maxOpenPositions}`, valueClass: '' }),
        ),
        h(Sparkline, { curve: ai.curve }),
        last === null
          ? null
          : h('div', { className: 'bq-ai-last' },
            h('div', { className: 'bq-meta-label' }, t('aiLast')),
            h('div', null,
              h('span', { className: 'bq-meta-value' }, `${last.symbol} · ${actionLabel}`),
              h('span', { className: 'bq-meta-label' },
                ` · ${t('aiConfidence')} ${Math.round((last.confidence ?? 0) * 100)}% · ${last.horizonHours}h · ${statusLabel}`),
            ),
            h('div', { className: 'bq-ai-thesis' }, last.thesis),
            last.result === null || last.result === undefined
              ? null
              : h('div', { className: `bq-meta-value ${tone(last.result.pnlUsd)}` },
                `${fmtUsd(last.result.pnlUsd)} USDT · ${fmtPct(last.result.pnlPct)} · ${last.result.reason}`),
          ),
        (ai.openPositions ?? []).length === 0
          ? h('div', { className: 'bq-empty' }, t('aiNoOpen'))
          : h('table', { className: 'bq-table' },
            h('thead', null, h('tr', null,
              h('th', null, t('colSymbol')),
              h('th', { className: 'bq-num' }, t('colQty')),
              h('th', { className: 'bq-num' }, t('colAvg')),
              h('th', { className: 'bq-num' }, t('colMark')),
              h('th', { className: 'bq-num' }, t('colPnl')))),
            h('tbody', null, ai.openPositions.map(position => h('tr', { key: `${position.symbol}-${position.side}` },
              h('td', null, position.symbol, h('span', { className: 'bq-meta-label' }, ` ${position.side}`)),
              h('td', { className: 'bq-num' }, fmtQty(position.qty)),
              h('td', { className: 'bq-num' }, fmtPrice(position.entryPrice ?? position.avgPrice)),
              h('td', { className: 'bq-num' }, fmtPrice(position.markPrice ?? position.entryPrice ?? position.avgPrice)),
              h('td', { className: `bq-num ${tone(position.unrealizedPnlUsd)}` },
                `${fmtUsd(position.unrealizedPnlUsd)} (${fmtPct(position.unrealizedPct ?? 0)})`),
            )))),
      )
    }

    /** One label/value pair. */
    function Stat({ label, value, valueClass }: { label: string, value: import('react').ReactNode, valueClass?: string }) {
      return h('div', { className: 'bq-kv-item' },
        h('span', { className: 'bq-meta-label' }, label),
        h('span', { className: `bq-meta-value ${valueClass ?? ''}` }, value))
    }

    /**
     * Poll the Host snapshot for one market selection.
     * `initial` supplies a first snapshot for the server-rendered tests; the
     * browser never passes it, so the panel starts in its loading state.
     */
    function useSnapshot({ symbol, category, interval, nonce, initial }: { symbol: string, category: string, interval: string, nonce: number, initial?: SnapshotInitial }): SnapshotInitial & { loading: boolean } {
      const [state, setState] = useState({
        data: initial?.data ?? null,
        error: initial?.error ?? null,
        loading: initial === undefined,
        at: initial?.at ?? 0,
      })
      const key = `${symbol}|${category}|${interval}|${nonce}`
      useEffect(() => {
        let cancelled = false
        let timer: ReturnType<typeof setTimeout> | null = null
        const query = `symbol=${encodeURIComponent(symbol)}&category=${encodeURIComponent(category)}&interval=${encodeURIComponent(interval)}&bars=180`
        async function tick() {
          try {
            const response = await fetch(`/api/bybit-quant?${query}`, { headers: { accept: 'application/json' } })
            if (!response.ok) throw new Error(`HTTP ${response.status}`)
            const data = await response.json() as PanelPayload
            if (cancelled) return
            setState({ data, error: data.ok ? null : data.error ?? 'unknown error', loading: false, at: Date.now() })
          } catch (error) {
            if (cancelled) return
            setState(previous => ({ data: previous.data, error: error instanceof Error ? error.message : String(error), loading: false, at: previous.at }))
          }
          if (!cancelled) timer = setTimeout(tick, POLL_MS)
        }
        setState(previous => ({ ...previous, loading: true }))
        tick()
        return () => {
          cancelled = true
          if (timer !== null) clearTimeout(timer)
        }
      }, [key])
      return state
    }

    /** The panel itself. */
    function Panel(props: PanelProps) {
      const t: Translate = props.t ?? (key => key)
      const [symbol, setSymbol] = useState('BTCUSDT')
      const [draft, setDraft] = useState('BTCUSDT')
      const [category, setCategory] = useState('linear')
      const [interval, setIntervalValue] = useState('60')
      const [nonce, setNonce] = useState(0)
      const snapshot = useSnapshot({ symbol, category, interval, nonce, ...(props.initial === undefined ? {} : { initial: props.initial }) })
      const data = snapshot.data
      const ticker = data?.ticker
      const paper = data?.paper
      const backtest = data?.lastBacktest
      const signal = data?.lastSignal
      const klines = data?.klines ?? []
      const ai = data?.ai ?? null
      const envLabel = data?.env === 'live' ? t('envLive') : data?.env === 'testnet' ? t('envTestnet') : t('envDemo')

      const applySymbol = useCallback(() => {
        const next = draft.trim().toUpperCase()
        if (next !== '' && next !== symbol) setSymbol(next)
      }, [draft, symbol])

      return h('div', { className: 'bq-root' },
        h('style', { dangerouslySetInnerHTML: { __html: CSS } }),

        h('div', { className: 'bq-head' },
          h('h1', { className: 'bq-title' }, t('title')),
          h('div', { className: 'bq-badges' },
            h('span', { className: `bq-badge ${data?.env === 'live' ? 'bq-badge-warn' : ''}` }, envLabel),
            h('span', { className: `bq-badge ${data?.allowLiveTrading ? 'bq-badge-warn' : ''}` }, data?.allowLiveTrading ? t('liveOn') : t('liveOff')),
            h('span', { className: 'bq-badge' }, data?.hasKeys ? t('keysOn') : t('keysOff')),
            h('button', { type: 'button', className: 'bq-button', onClick: () => setNonce(value => value + 1) }, t('refresh')),
          ),
        ),
        h('p', { className: 'bq-sub' }, `${t('subtitle')}${snapshot.at > 0 ? ` · ${t('updated')} ${new Date(snapshot.at).toLocaleTimeString()}` : ''}`),

        snapshot.error !== null && h('div', { className: 'bq-error', role: 'alert' },
          h('div', { className: 'bq-error-title' }, t('errorFetch')),
          h('div', null, snapshot.error),
          h('div', { className: 'bq-hint' }, t('errorRoute')),
        ),

        h('div', { className: 'bq-controls' },
          h('div', { className: 'bq-field' },
            h('label', { className: 'bq-label', htmlFor: 'bq-symbol' }, t('symbol')),
            h('input', {
              id: 'bq-symbol',
              className: 'bq-input',
              value: draft,
              list: 'bq-symbols',
              spellCheck: false,
              onChange: event => setDraft(event.target.value),
              onKeyDown: event => { if (event.key === 'Enter') applySymbol() },
              onBlur: applySymbol,
            }),
            h('datalist', { id: 'bq-symbols' }, SYMBOLS.map(value => h('option', { key: value, value }))),
          ),
          h('div', { className: 'bq-field' },
            h('span', { className: 'bq-label' }, t('category')),
            h('div', { className: 'bq-tabs' },
              ['linear', 'spot'].map(value => h('button', {
                key: value, type: 'button', className: 'bq-tab', 'aria-pressed': category === value,
                onClick: () => setCategory(value),
              }, value === 'linear' ? 'Perp' : 'Spot')),
            ),
          ),
          h('div', { className: 'bq-field' },
            h('span', { className: 'bq-label' }, t('interval')),
            h('div', { className: 'bq-tabs' },
              INTERVALS.map(([value = '60', label = '1h']) => h('button', {
                key: value, type: 'button', className: 'bq-tab', 'aria-pressed': interval === value,
                onClick: () => setIntervalValue(value),
              }, label)),
            ),
          ),
        ),

        ticker !== undefined
          ? h('div', { className: 'bq-price-row' },
            h('div', { className: 'bq-price' }, fmtPrice(ticker.last)),
            h('div', { className: 'bq-price-meta' },
              h('div', { className: 'bq-meta-item' },
                h('span', { className: 'bq-meta-label' }, t('change24h')),
                h('span', { className: `bq-meta-value ${tone(ticker.change24hPct)}` }, fmtPct(ticker.change24hPct))),
              h('div', { className: 'bq-meta-item' },
                h('span', { className: 'bq-meta-label' }, t('high24h')),
                h('span', { className: 'bq-meta-value' }, fmtPrice(ticker.high24h))),
              h('div', { className: 'bq-meta-item' },
                h('span', { className: 'bq-meta-label' }, t('low24h')),
                h('span', { className: 'bq-meta-value' }, fmtPrice(ticker.low24h))),
              h('div', { className: 'bq-meta-item' },
                h('span', { className: 'bq-meta-label' }, t('volume24h')),
                h('span', { className: 'bq-meta-value' }, `${fmtUsd(ticker.turnover24h / 1e6, 1)}M`)),
              ticker.fundingRate === undefined ? null : h('div', { className: 'bq-meta-item' },
                h('span', { className: 'bq-meta-label' }, t('funding')),
                h('span', { className: `bq-meta-value ${tone(ticker.fundingRate)}` }, fmtPct(ticker.fundingRate, 4))),
            ))
          : h('div', { className: 'bq-empty' }, snapshot.loading ? t('loading') : t('empty')),

        h('div', { className: 'bq-card', style: { marginTop: '12px' } },
          h('div', { className: 'bq-legend' },
            h('span', null, 'MA20'),
            h('span', null, 'MA50'),
            h('span', null, `${klines.length} ${t('captionBars')}`)),
          h(CandleChart, { klines, interval, t, aria: t('chartAria') }),
        ),

        h('div', { className: 'bq-grid' },
          h('div', { className: 'bq-card' },
            h('h2', { className: 'bq-card-title' }, t('paper')),
            h('div', { className: 'bq-kv' },
              h(Stat, { label: t('balance'), value: `${fmtUsd(paper?.balanceUsd ?? 0)} USDT` }),
              h(Stat, { label: t('equity'), value: `${fmtUsd(paper?.equityUsd ?? 0)} USDT` }),
              h(Stat, {
                label: t('totalReturn'),
                value: fmtPct(paper?.totalReturnPct ?? 0),
                valueClass: tone(paper?.totalReturnPct ?? 0),
              }),
            ),
            (paper?.positions ?? []).length === 0
              ? h('div', { className: 'bq-empty' }, t('noPositions'))
              : h('table', { className: 'bq-table' },
                h('thead', null, h('tr', null,
                  h('th', null, t('colSymbol')),
                  h('th', { className: 'bq-num' }, t('colQty')),
                  h('th', { className: 'bq-num' }, t('colAvg')),
                  h('th', { className: 'bq-num' }, t('colMark')),
                  h('th', { className: 'bq-num' }, t('colPnl')))),
              h('tbody', null, (paper?.positions ?? []).map((position, positionIndex) => h('tr', { key: position.key ?? `${position.symbol}-${positionIndex}` },
                  h('td', null, position.symbol, h('span', { className: 'bq-meta-label' }, ` ${position.category}`)),
                  h('td', { className: 'bq-num' }, fmtQty(position.qty)),
                  h('td', { className: 'bq-num' }, fmtPrice(position.avgPrice)),
                  h('td', { className: 'bq-num' }, fmtPrice(position.markPrice)),
                  h('td', { className: `bq-num ${tone(position.unrealizedPnlUsd)}` },
                    `${fmtUsd(position.unrealizedPnlUsd)} (${fmtPct(position.unrealizedPnlPct ?? 0)})`),
                )))),
            h('div', { className: 'bq-hint', style: { marginTop: '10px' } }, t('recentTrades')),
            (paper?.recentTrades ?? []).length === 0
              ? h('div', { className: 'bq-empty' }, t('noTrades'))
              : h('table', { className: 'bq-table' },
                h('tbody', null, (paper?.recentTrades ?? []).map((trade, index) => h('tr', { key: `${trade.time}-${index}` },
                  h('td', { className: trade.side === 'buy' ? 'bq-up' : 'bq-down' }, trade.side === 'buy' ? t('sideBuy') : t('sideSell')),
                  h('td', null, trade.symbol),
                  h('td', { className: 'bq-num' }, fmtQty(trade.qty)),
                  h('td', { className: 'bq-num' }, fmtPrice(trade.price)),
                  h('td', { className: 'bq-num' }, new Date(trade.time).toLocaleTimeString()),
                )))),
          ),

          h('div', { className: 'bq-card' },
            h('h2', { className: 'bq-card-title' }, t('backtest')),
            backtest === null || backtest === undefined
              ? h('div', { className: 'bq-empty' }, t('noBacktest'))
              : h('div', null,
                h('div', { className: 'bq-legend', style: { marginTop: 0, marginBottom: '8px' } },
                  h('span', null, `${backtest.strategy} · ${backtest.symbol} · ${backtest.interval}`),
                  h('span', null, `${backtest.metrics.bars} ${t('captionBars')}`)),
                h('div', { className: 'bq-kv' },
                  h(Stat, {
                    label: t('mReturn'),
                    value: fmtPct(backtest.metrics.totalReturnPct),
                    valueClass: tone(backtest.metrics.totalReturnPct),
                  }),
                  h(Stat, {
                    label: t('mBuyHold'),
                    value: fmtPct(backtest.metrics.buyHoldReturnPct),
                    valueClass: tone(backtest.metrics.buyHoldReturnPct),
                  }),
                  h(Stat, { label: t('mDrawdown'), value: `-${fmtUsd(backtest.metrics.maxDrawdownPct, 2)}%`, valueClass: '' }),
                  h(Stat, { label: t('mWinRate'), value: `${fmtUsd(backtest.metrics.winRatePct, 1)}%`, valueClass: '' }),
                  h(Stat, { label: t('mTrades'), value: String(backtest.metrics.trades), valueClass: '' }),
                  h(Stat, { label: t('mSharpe'), value: String(backtest.metrics.sharpe), valueClass: '' }),
                  h(Stat, { label: t('mFees'), value: `${fmtUsd(backtest.metrics.feeDragPct, 2)}%`, valueClass: '' }),
                ),
                h(Sparkline, { curve: backtest.curve }),
                signal === null || signal === undefined
                  ? null
                  : h('div', { style: { marginTop: '6px' } },
                    h('span', { className: 'bq-meta-label' }, `${t('signal')}: `),
                    h('span', { className: signal.target === 'long' ? 'bq-up' : 'bq-meta-value' },
                      signal.target === 'long' ? t('long') : t('flat')),
                    h('span', { className: 'bq-meta-label' }, ` · ${signal.time}`)),
              ),
          ),
        ),

        h('div', { className: 'bq-card', style: { marginTop: '12px' } },
          h('h2', { className: 'bq-card-title' }, t('aiTitle'), h('span', null, t('aiSub'))),
          h(AiPanel, { ai, t }),
        ),

        h('p', { className: 'bq-hint' }, t('hint')),
      )
    }

    /** Sidebar glyph: three ascending candles in the current text color. */
    function PanelIcon({ size }: { size?: number }) {
      const edge = Number.isFinite(size) ? size : 20
      return h('svg', { width: edge, height: edge, viewBox: '0 0 20 20', 'aria-hidden': true, style: { display: 'block' } },
        h('g', { fill: 'currentColor' },
          h('rect', { x: 3, y: 9, width: 3, height: 6, rx: 0.8 }),
          h('rect', { x: 8.5, y: 6.5, width: 3, height: 8.5, rx: 0.8 }),
          h('rect', { x: 14, y: 4, width: 3, height: 11, rx: 0.8 }),
        ),
        h('g', { stroke: 'currentColor', strokeWidth: 1.2, strokeLinecap: 'round', opacity: 0.55 },
          h('line', { x1: 4.5, y1: 3, x2: 4.5, y2: 9 }),
          h('line', { x1: 10, y1: 2, x2: 10, y2: 6.5 }),
          h('line', { x1: 15.5, y1: 2, x2: 15.5, y2: 4 }),
        ))
    }

    return {
      inject: ['slots', 'locale'],
      apply(ctx: PanelContext) {
        ctx.effect(() => ctx.locale.register(NS, { zh, en }), 'bybit-quant: panel dictionaries')
        const t = ctx.locale.bind(NS)

        ctx.slots.inject('main', () => ctx.slots.register({
          name: 'main',
          key: PANEL_ID,
          locale: NS,
          inject: () => ({}),
        }, Panel))

        ctx.slots.inject('sidebar.panellist', () => ctx.slots.register({
          name: 'sidebar.panellist',
          id: PANEL_ID,
          order: 40,
          label: () => t('panel'),
          locale: NS,
        }, PanelIcon))
      },
    }
  },
})
