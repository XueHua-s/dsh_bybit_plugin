# @local/bybit-quant

Bybit quant toolkit for DeepSeek Harness (DSH): live market data, strategy backtests, an
**AI decision track** with a journal and a code-owned risk gate, a simulated USDT book, and
triple-gated live orders for the agent — plus a **Bybit** panel in the Web GUI.

Install: **Plugins → Add plugin** with this directory, or `plugin_manager` `install_bundle`
with the absolute path. The bundle inserts one Host+Client row, `bybit-quant`; the Host and
browser entries resolve from `dist/`, so run `npm run build` first (the repo ships `dist/`
after a build; the source is `src/`).

## Tools

| Tool | Purpose | Key needed |
|---|---|---|
| `bybit_market` | ticker, candles, order book, funding history, instrument rules | no |
| `bybit_account` | wallet balance, open positions, open orders | read key |
| `bybit_trade` | create / cancel / cancel_all / close | trade key + unlocks |
| `quant_backtest` | long-only backtest with metrics and the current signal | no |
| `quant_paper` | simulated book: status / buy / sell / reset | no |
| `quant_watchlist` | the user's symbol list: list / set / add / remove (exchange-verified) | no |
| `quant_signals` | Supertrend, Squeeze Momentum, Ichimoku, Donchian, ADX + consensus | no |
| `quant_brief` | multi-timeframe brief + risk limits for the AI track | no |
| `quant_decide` | validate, risk-gate, journal, and act on one AI decision | no |
| `quant_review` | score the journal: hit rate, expectancy, Brier, baseline | no |

## Live trading is off by default

`bybit_trade` sends a real order only when **all** of these hold:

1. the plugin config has `allowLiveTrading: true`;
2. an API key pair is configured (`BYBIT_API_KEY` / `BYBIT_API_SECRET`, or the config fields);
3. the call passes `confirm: "LIVE"` **and** `dryRun: false`.

Anything less returns the exact preview it would have sent. Every live order is also capped
by `maxOrderNotionalUsd` (default 200 USDT) and rounded to the instrument's quantity step;
`close` is exempt from the cap because it only reduces exposure. Start with `env: demo`.

## The AI decision loop

You pick the market; the agent works it. `quant_watchlist` stores the symbols you care about
(any Bybit spot or perpetual pair, verified against the exchange), and the brief, the signal
scan, and the decision path all follow that list.

`quant_signals` runs five attributed, re-implemented algorithms — Supertrend, Squeeze
Momentum, Ichimoku, Donchian, Wilder ADX — and returns a weighted consensus per timeframe,
so the model sees objective facts instead of journalling an eyeballed chart.

The model proposes, the code refuses. `quant_brief` builds the context; `quant_decide` takes
`{ action, sizePct, confidence, stopPct, takePct, horizonHours, thesis, invalidation }` and
runs a **code-side risk gate** before anything happens: a stop hit may cost at most
`aiRiskPerTradePct` of equity, a position may not exceed `aiMaxPositionPct`, trading stops at
`aiMaxDailyLossPct` daily loss or `aiMaxDrawdownPct` drawdown. Accepted decisions open a
simulated position; rejected ones are journaled without a fill.

`quant_review` reports hit rate, expectancy, average R, Brier calibration, drawdown, open
positions, and a buy-and-hold baseline over the same window. Each decision stores the brief
hash and a compact context snapshot so a review can replay what the model saw.

## The panel

The sidebar gains a **Bybit** row that opens a global panel: live ticker, candle chart with
MA20/MA50, the paper book (balance, equity, positions, recent fills), and the last backtest
with its metrics, equity sparkline, and current signal. It polls the authenticated bridge
route `GET /api/bybit-quant` every 5 seconds — the same Host/Origin fence and browser cookie
as the rest of the Web GUI, so no unauthenticated route is added. `GET /api/bybit-quant?view=health`
reports the environment, key presence, and state file for troubleshooting.

The panel never trades. Acting on a view is the agent's job through the tools, which keeps
every state change in the conversation log.

## State and privacy

The paper book, last backtest, and last signal live in
`$DSH_HOME/bybit-quant/state.json` (override with `stateFile`), never in your workspace.
Market data goes to `api.bybit.com`; signed calls go to the endpoint of the selected `env`
(`api-demo.bybit.com`, `api-testnet.bybit.com`, or `api.bybit.com`). No third-party server is
involved.

## Engineering

```sh
npm install
npm run build       # tsup -> dist/ (Host ESM modules + the browser client)
npm run lint        # oxlint (0 warnings, 0 errors enforced in CI)
npm run typecheck   # tsc --noEmit, strict
npm run test:unit   # signals, AI gate/accounting, client bundle, React render (no network)
npm run test:network# live Bybit public endpoints + the Host integration suite
npm run verify      # build + lint + typecheck + unit tests
```

- **Toolchain** — TypeScript, [tsup](https://tsup.egoist.dev/) (esbuild) for the build,
  [oxlint](https://oxc.rs/docs/guide/usage/linter) for linting, GitHub Actions for CI.
- **Artifacts** — `dist/` is the only thing the plugin ships. `dist/index.js` is the Host
  entry the dsh bundle row resolves; `dist/client.js` is the self-contained browser script
  (`require('react')` comes from the dsh module loader, so no React copy is bundled).
- **Build shape** — `bundle: false` keeps one readable output module per source file, so a
  stack trace names the file that failed instead of a generated chunk.
- **Layout**

```text
src/index.js        Host plugin: tools, prompt note, authenticated panel route
src/client.js       Browser panel: sidebar row + main panel
src/lib/signals.ts  Signal library (typed)
src/lib/strategies.ts  Indicators, 3 strategies, backtest engine (typed)
src/lib/bybit.js    REST client, signing, interval/symbol normalisation
src/lib/ai.js       AI decision track: brief, decision schema, risk gate, journal, scoring
src/lib/paper.js    Simulated USDT book
src/lib/state.js    Atomic JSON store
test/*.mjs          Unit + integration + render suites, run against dist/
```

### TypeScript migration status

The toolchain, strict `tsconfig`, and `dist/` pipeline are in place; modules move to
TypeScript one at a time, each landing with `npm run verify` green:

| Module | Status |
|---|---|
| `lib/signals.ts` | ✅ typed |
| `lib/strategies.ts` | ✅ typed |
| `lib/bybit.js` | ⏳ next |
| `lib/ai.js` | ⏳ next |
| `lib/paper.js`, `lib/state.js` | ⏳ next |
| `index.js`, `client.js` | ⏳ last (dynamic tool args and React props) |

Until a module is converted, `checkJs` stays off and `tsc` skips it; every JS file is still
built by tsup, linted by oxlint, and covered by the tests.

## Limitations

Single-asset, long-only, no leverage or funding cost in backtests; REST polling only; USDT
perpetuals and spot only. The signed endpoints follow Bybit's v5 documentation but cannot be
exercised without your keys, so only public endpoints are covered by the smoke test.
