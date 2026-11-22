# Bybit quant

A Bybit toolkit for DeepSeek Harness: the agent can read live market data, backtest a
strategy on real candles, record **AI simulated decisions and positions**, run a simulated
USDT book, and validate exchange-order intent as a preview. Exchange writes are unavailable in this Bundle. A
**Bybit** entry in the sidebar opens a read-only panel with the candle chart, the AI
decision card, the paper book, and the last backtest. Its symbol, market, and timeframe
controls change only the displayed market data; they never direct the AI's coin or decision.

- **Market data** — ticker, candles, order book, funding history, and instrument rules for
  USDT perpetuals (`linear`) and spot. Public data is always read from the live venue, so a
  demo or testnet account still sees real prices.
- **Backtests** — `ma_cross`, `rsi_reversion`, and `breakout`, single asset, long-only, full
  notional per trade, fees and slippage on both sides. Returns total return, buy & hold,
  max drawdown, win rate, profit factor, Sharpe, fee drag, and the strategy's current signal.
- **Paper book** — a simulated USDT account that fills at the live mark, tracks average
  price, realized and unrealized PnL, and keeps a trade journal. It never touches the
  exchange.
- **AI candidate universe** — `quant_watchlist` is an optional allow-list that can narrow the
  symbols the AI may analyze; it does not ask the AI to trade every listed symbol. With no
  configured or saved allow-list, the plugin discovers candidates from Bybit's complete
  Instrument Info catalogue and a current ticker snapshot. It keeps active USDT Spot or linear
  perpetual instruments with valid quantity/price rules, at least USD 1 million 24-hour
  turnover, and a spread no wider than 75 bps, then exposes up to 30 candidates ranked by
  turnover. The AI chooses up to four for detailed analysis at a time, may choose none, and may
  abstain. Dashboard filters affect only displayed market data.
- **Signal library** — `quant_signals` evaluates published, attributed algorithms on any
  symbol and timeframe: Supertrend, Squeeze Momentum (Bollinger inside Keltner), Ichimoku
  cloud state, Donchian breakout, and Wilder's ADX/DI regime. Each returns a directional
  score, and the weighted consensus is deliberately conservative: a squeeze that is still
  compressing casts no vote.
- **AI simulated decisions** — `quant_brief` assembles multi-timeframe trend, volatility regime,
  funding, order-book imbalance, and the risk limits; `quant_decide` records a strict
  decision (action, size, confidence, stop, take, horizon, thesis, invalidation) and opens a
  simulated position only when the **code-owned risk gate** accepts it; `quant_review` scores the journal
  (hit rate, expectancy, R, Brier calibration, drawdown, buy-and-hold baseline). The model
  supplies the thesis, the code supplies the arithmetic and the veto.
- **Exchange writes** — unavailable. `bybit_trade` validates create, cancel, cancel-all, and close
  intent as a local preview. `dryRun: false` returns `execution_authority_unavailable` before any
  Bybit request; only a separately reviewed native execution authority may add writes.

## Tools

| Tool | What it does | Needs a key |
|---|---|---|
| `bybit_market` | ticker / candles / order book / funding / instrument rules | no |
| `bybit_account` | wallet balance, open positions, open orders | yes, read |
| `bybit_trade` | create, cancel, cancel-all, close preview; exchange writes unavailable | optional, read-only previews |
| `quant_backtest` | backtest a strategy on real candles and return metrics plus the current signal | no |
| `quant_paper` | status, buy, sell, reset the simulated book | no |
| `bybit_instruments` | discover listed instruments (spot / USDT-USDC perpetuals), filter by quote, contract type, name | no |
| `quant_watchlist` | list / set / add / remove optional bounds for eligible AI candidates | no |
| `quant_signals` | Supertrend, Squeeze, Ichimoku, Donchian, ADX + consensus on eligible candidates | no |
| `quant_brief` | multi-timeframe brief plus the risk limits | no |
| `quant_decide` | journal one decision, risk-gate it, act on the AI track | no |
| `quant_review` | score the journal, calibration, and the baseline | no |

## Quick start

Ask in the conversation:

- 「BTC 现在多少钱？资金费率多少？」 → `bybit_market`
- 「用 ma_cross 快 10 慢 30 在 ETHUSDT 4h 上回测 800 根」 → `quant_backtest`
- 「按刚才的信号，模拟盘买 500 USDT 的 ETH」 → `quant_paper`
- 「出一份简报然后你自己决定」 → `quant_brief` → `quant_decide`
- 「这套 AI 决策现在表现如何？」 → `quant_review`
- 「看一眼我的模拟盘」 → `quant_paper` status；或点侧边栏的 **Bybit**

## Configuration

Set values in the plugin row's `config` (**Plugins → Bybit quant → Configure**, or the
profile's `cordis.patch.yml`).

| Field | Default | Meaning |
|---|---|---|
| `env` | `testnet` in the Bundle patch | `demo`, `testnet`, or `live` (real money) |
| `apiKey` / `apiSecret` | — | Prefer `BYBIT_API_KEY` / `BYBIT_API_SECRET` in the environment; config is plain text |
| `maxOrderNotionalUsd` | `24` in the Bundle patch | Preview-only ceiling for one proposed order (`price × quantity`) |
| `paperBalanceUsd` | `10000` | Starting cash of the simulated book |
| `defaultSymbol` | `BTCUSDT` | Symbol used when a tool call omits one |
| `defaultCategory` | `linear` | `linear` (USDT perpetual) or `spot` |
| `backtestFeeBps` | `6` | Default fee per side used by `quant_backtest` |
| `recvWindowMs` | `5000` | Signed-request receive window |
| `timeoutMs` | `15000` | Per-request HTTP timeout |
| `stateFile` | `$DSH_HOME/bybit-quant/state.json` | Where the paper book and last backtest live |
| `aiEnabled` | `true` | Turns the AI decision track on or off |
| `aiStartEquity` | `paperBalanceUsd` | Starting equity of the AI track |
| `aiRiskPerTradePct` | `1` | A stop hit may cost at most this share of equity; enforced in code |
| `aiMaxPositionPct` | `50` | Largest single position as a share of AI equity |
| `aiMaxOpenPositions` | `2` | Concurrent AI positions |
| `aiMaxDailyLossPct` | `3` | Trading stops for the day after this loss |
| `aiMaxDrawdownPct` | `20` | Trading stops after this drawdown from peak equity |
| `aiSymbols` | `[]` | Empty enables dynamic discovery; a non-empty list narrows AI candidates |
| `aiTimeframes` | `[240, 60, D]` | Brief timeframes, primary first |
| `aiBackgroundLoopEnabled` | `false` | Opt in to periodic simulated-decision Agent cycles; never enables exchange orders |
| `aiBackgroundLoopIntervalMs` | `900000` | Cycle cadence, clamped to 1 minute–24 hours |
| `aiBackgroundEnvironment` | `testnet` | `testnet` or `internal_paper`; Demo and Mainnet are rejected |

Existing profiles may retain former allowLiveTrading, allowTestnetTrading, or allowMainAccount
keys after an update. The plugin ignores those keys; no configuration option enables exchange writes.

## Safety

- Trading state lives under `$DSH_HOME/bybit-quant/`, never in your workspace.
- The panel is **read-only**: no browser path can place an order or move the paper book.
- The plugin validates preview quantities against the instrument step, minimum quantity,
  minimum notional, and `maxOrderNotionalUsd`; this ceiling is preview-only and grants no
  exchange execution capability.
- The shipped Bundle uses `[TESTNET]`; Testnet credentials and read requests stay on the Testnet host.
  Mainnet reads require separate environment-scoped credentials; exchange writes remain unavailable.

## AI decision workflow

1. The model first calls `quant_brief` without symbols to receive a fresh candidate snapshot,
   then chooses up to four eligible candidates for detailed `quant_brief` and `quant_signals`
   evidence. It decides which symbols merit a decision, or abstains; panel filters never enter
   this choice.
2. For each symbol it selects, the model may call `quant_decide` with a falsifiable
   thesis and an invalidation. `quant_signals` gives it objective signal facts (which signal
   says what, and why the consensus is flat) instead of raw candles to eyeball.
3. The risk gate checks per-trade risk, position cap, open positions, daily loss, and
   drawdown. A rejected decision is journaled without a fill — the model can shrink its size
   or decide flat.
4. Accepted decisions open a simulated position with the declared stop, take, and horizon.
   `quant_decide` and `quant_review` settle open positions against fresh 1h candles first
   (stop, then take, then horizon at market).
5. Every decision stores the brief hash and a compact context snapshot, so a later review can
   replay what the model saw.

These steps run in a conversation or an explicitly enabled, bounded background simulation
cycle. The scheduler is disabled by default, only records simulated decisions, and does not
prove that a completed Agent turn wrote a decision. It does not make the Bundle an unattended
exchange trader.

## Supported instruments

Nothing is hard-coded: `bybit_instruments` reads Bybit's live catalogue
(`/v5/market/instruments-info`) and the watchlist verifies every symbol against it.
AI candidate discovery also reads the complete catalogue and current ticker snapshot, applies
the eligibility and liquidity rules above, and fails closed if discovery is unavailable. A
configured or saved allow-list only narrows candidates; an empty list does not fall back to fixed
symbols. The AI chooses the instruments it analyzes or decides on.

| Type | Category | Status |
|---|---|---|
| Spot | `spot` | supported (incl. tokenised stocks such as `AAPLXUSDT`) |
| USDT perpetual | `linear` | supported |
| USDC perpetual | `linear` | supported (`BTCUSDC` and friends) |
| Equity perpetual | `linear` | supported (e.g. `AAPLUSDT`, `MSFTUSDT`, `SPYUSDT`) |
| Inverse contract (`BTCUSD`) | `inverse` | later — quantity is in USD contracts, not base coin |
| Options | `option` | later — different pricing and settlement model |

## Signal attribution

The library re-implements published methods rather than importing a repository, so every
formula is readable and testable here:

| Signal | Origin |
|---|---|
| Supertrend | ATR band trend, popularised on TradingView and re-implemented across freqtrade strategies |
| Squeeze Momentum | LazyBear's TradingView indicator (Bollinger inside Keltner + momentum histogram) |
| Ichimoku | Goichi Hosoda's cloud; standard TradingView drawing |
| Donchian | The Turtle channel rule |
| ADX / DI | J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) |

Public strategy repositories (`freqtrade/freqtrade-strategies`, `microsoft/qlib`,
`AI4Finance-Foundation/FinRL`) are useful as ideas and for factor lists, but copying them
wholesale imports their overfitting and their stack. If a specific method is worth adopting,
it belongs here as a readable, tested function with its own backtest.

## Limitations

- Backtests are single-asset, long-only, no leverage, no funding cost, and fill at the next
  close with configured fees and slippage. They are research, not a forecast.
- The AI track fills at the live mark with a flat fee, models no funding cost and no
  slippage beyond the fee, and settles stops against 1h candles — a real stop would fill
  worse in a gap.
- The AI track is a paper book. It is not evidence of skill until the journal has enough
  closed decisions and the Brier score and expectancy hold up out of sample.
- Market data is REST polling; the panel polls every 5 seconds and the Host caches a
  snapshot for 4 seconds. The panel reads the authenticated bridge route
  `GET /api/bybit-quant` (`?view=health` for diagnostics), so it answers only a signed-in
  browser of this Host, exactly like the rest of the Web GUI.
- The signed read endpoints (account, open orders, balances) use Bybit's v5
  documentation but cannot be exercised without your API keys, so only public endpoints are
  covered by the bundle's own smoke test.
- The plugin supports USDT perpetuals and spot only; no options, no inverse contracts, no
  copy trading, no WebSocket streams.
- Verification covered in this bundle: public market data, the panel route over the
  authenticated connection bridge, every tool through a stand-in Host context, and the panel
  components server-rendered with real data. The signed account and order endpoints follow
  Bybit v5 but need your keys, so they are not exercised by the bundle's tests.
