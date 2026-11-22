# Build report: AI decision and dashboard boundary

## Result

Implemented the screenshot follow-up in the DSH workspace source. Market symbol/category/timeframe controls are explicitly display-only; the AI candidate universe is separate. The native internal-paper dashboard card and its route are observation-only. AI tool inputs are checked against the eligible universe, including the distinction between a watched candidate and a chart selection.

This completes the scoped UI/decision-boundary increment. It does not complete the architecture book's full autonomous platform; that remains **PARTIAL**.

## Requirements and design

- Source request: `sdd/features/DEFINE_BYBIT_AI_QUANT.md` and the user-supplied architecture book at `/Users/litlesnow/.codex/attachments/886f3b36-5cab-4ba1-bb1c-7ef525af0e6e/pasted-text-1.txt`.
- Design decision: Decision 5 in `sdd/features/DESIGN_BYBIT_AI_QUANT.md`.
- Scoped manifest: entries 39–45 in that design.
- UI review: `sdd/reports/UX_REVIEW_DSH_BYBIT_UI_2026-11-19.md`.

## Changes

| Area | Change | Evidence |
|---|---|---|
| Dashboard | Added a “Market view / 行情查看” heading and copy stating that chart filters do not direct AI decisions; renamed fields to chart/view terms. | `apps/dsh-plugin/src/client.ts`, `client-assets.ts`, `test/render.ts` |
| Paper status | Removed browser Start/Stop controls and limited the dashboard route to GET/HEAD status reads. | `src/client-paper.ts`, `src/host-paper-panel.ts`, `test/client-paper.ts`, `test/paper.ts` |
| AI candidate boundary | Candidate selection is independent from the dashboard query. Requested candidates are normalized, bounded to four, and rejected if outside watchlist/config eligibility. Prompt permits selecting eligible candidates or abstaining. | `src/host-runtime.ts`, `host-tools-ai.ts`, `host-tools-watchlist.ts`, `prompts/bybit-quant/v2.ts`, `test/integration.ts` |
| User-facing documentation | Clarified candidate-universe semantics and current product limits. | `apps/dsh-plugin/docs/DETAIL.md`, UX review above |

The eligible universe is discovered dynamically from every Bybit Instrument Info page plus a current ticker snapshot. `aiSymbols` and the AI watchlist are optional narrowing bounds; an empty configuration does not fall back to BTC/ETH. Eligibility applies Trading status, USDT quote, category/contract type, positive lot and price rules, minimum turnover and maximum spread, then exposes at most 30 stable-ranked candidates. Brief and signal calls accept at most four AI-selected symbols. The AI chooses which candidates merit a decision or abstains. Chart filters do not alter that boundary.

## GitHub algorithm adoption status

The architecture book's reference libraries have **not** been integrated as complete frameworks. Current code contains a small, independently testable subset:

- The DSH TypeScript signal library includes Supertrend, Squeeze Momentum, Ichimoku, Donchian, and ADX/DI. These are signal evaluators, not a dynamically selected production portfolio.
- `python/packages/quant-strategies` implements bounded target-exposure research families: SMA/EMA cross, Donchian breakout, ADX trend, time-series momentum, Bollinger and Z-score reversion, RSI reversion, ATR breakout, funding carry, and a small five-formula Alpha158 subset independently rewritten from a pinned Qlib revision. Built-ins are registered as `research` / `not_started`.
- NautilusTrader is used by an offline finite-simulation foundation, but it is not yet the sole live execution authority or integrated with the AI strategy selector.
- TradingAgents, RD-Agent, FreqAI, VectorBT, FinRL-X/FinRL variants, ElegantRL, and Hummingbot are audited references only; their runtimes/models are not integrated. No RL or ML prediction strategy, autonomous factor-research loop, regime selector, ensemble allocator, or full strategy-validation pipeline is implemented.

See `docs/research/github-repository-audit.md`, `sdd/features/DESIGN_STRATEGY_FAMILIES.md`, and `sdd/reports/BUILD_REPORT_STRATEGY_FAMILIES.md` for source/commit, license, and package-scope evidence. Research-family unit tests establish deterministic local behavior only; they do not establish profitability, out-of-sample robustness, paper approval, or deployment readiness.

## Verification

The first full-workspace `pnpm run verify` attempt in this increment failed before tests because the configured registry could not resolve the private DSH host package. That historical failure was later cleared after the workspace manifest and lockfile were restored; the successful rerun is recorded below. It is not the current Verify Gate status.

| Command | Exit | Result |
|---|---:|---|
| Initial `pnpm run verify` | 1 | Typecheck found that the DSH route contract requires a `requestBody` declaration even for GET/HEAD-only routes. Added `'buffered'`; the route still rejects request bodies and non-GET/HEAD methods. |
| `pnpm --filter @bybit-quant/dsh-plugin run typecheck && pnpm --filter @bybit-quant/dsh-plugin run test:unit` | 1 | Typecheck passed; unit test read stale `dist` and did not see the new required route declaration. Rebuilt before continuing. |
| `pnpm --filter @bybit-quant/dsh-plugin run build && pnpm --filter @bybit-quant/dsh-plugin run test:unit` | 1 | Exposed a client test that expected an enabled button while a request was pending. Corrected the test to repeat the captured handler and assert single-request ownership. |
| Initial `pnpm run verify` (before workspace manifest/lockfile restoration) | 1 | Historical `ERR_PNPM_FETCH_404` for private `@deepseek-ai/dsh-desktop-host`; the repository test matrix did not start. Later rerun passed. |
| `./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/tsc -p tsconfig.tests.json --noEmit && ./node_modules/.bin/tsdown && ./node_modules/.bin/oxlint . && node scripts/check-bundle.ts && node test/signals.ts && node test/ai.ts && node test/ai-universe.ts && node test/ai-scheduler.ts && node test/client.ts && node test/render.ts && node test/network-endpoint.ts && node test/oauth.ts && node test/trade-cutover.ts && node test/backup.ts && node test/sandbox-output.ts && node test/trust.ts && node test/engine.ts && node test/paper-capability.ts && node test/paper.ts && node test/client-paper.ts` | 0 | Existing plugin toolchain passed source/test typecheck, build, lint, bundle check and all unit tests; Oxlint emitted five non-blocking style warnings. |
| `python/.venv/bin/pytest -q python/apps/quant-engine/tests/test_builtin_strategies.py python/apps/quant-engine/tests/test_strategy_registry.py python/packages/quant-strategies/tests/test_families.py python/packages/quant-strategies/tests/test_alpha158.py` | 0 | 61 strategy-family, registry and Alpha158 tests passed. |
| `./node_modules/.bin/nx show projects` and `nx show project quant-engine --json` | 0 | Nx discovered 8 projects and the quant-engine dependency edges. |
| `gitleaks git --redact --no-banner --ignore-gitleaks-allow` | 0 | 29 commits scanned; no leaks found. |
| `pnpm typecheck:tests` | 0 | DSH test TypeScript check passed. |
| `pnpm python:lint` | 0 | Ruff checks passed; 84 files formatted. |
| `pnpm python:typecheck` | 0 | Pyright passed with 0 errors/warnings. |
| `pnpm python:test` | 0 | 400 passed; 11 upstream/deprecation warnings. |
| `pnpm exec nx show projects` | 0 | Nx discovers `quant-strategies`, `quant-engine`, the DSH plugin, and the remaining workspace projects. |
| `pnpm exec nx show project quant-engine --json` | 0 | The engine project graph declares `quant-strategies` as an implicit dependency. |
| `git diff --check` | 0 | Rerun after the final report edit; no whitespace errors in tracked changes. |
| Python trailing-whitespace/final-newline check for this untracked report | 0 | Passed after the final report edit. |
| `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | 0 | Rerun after the final report edit; scanned the whole 28.85 MB worktree, including untracked files, and found no leaks. |
| React SSR and AI-boundary assertions | included in `pnpm run verify` | Render test covers the view-only label; integration test confirms a chart-symbol query does not change the AI candidate set and an ineligible symbol cannot be decided. |

## Unverified and remaining scope

- The active DSH Bundle was not updated or visually checked in Chrome; source-level SSR and integration tests are the evidence for the new copy and behavior.
- Dynamic candidate discovery and a default-off Testnet/internal-paper scheduler are implemented and locally verified. Process recovery, strategy/regime selection, persistent portfolio allocation, complete account/order reconciliation, and unified Nautilus execution authority remain unimplemented or unverified.
- Mainnet trading remains disabled in the Bundle. No Testnet or Mainnet order was sent in this increment.

## Final status

The scoped UI/AI candidate-boundary changes are implemented. The recorded full-workspace checks passed on the later rerun, while official Plugin Manager installation and live visual verification were still pending at the time of this report. The product does not yet meet the architecture book's end-to-end unattended quantitative-trading acceptance criteria.

## 2026-11-20 dynamic chart suggestion follow-up

The chart symbol input no longer presents a fixed BTC/ETH/SOL/XRP/DOGE/BNB
starter list. `client.ts` passes suggestions only from the most recent
`aiCandidatePool` when its status is `fresh`; `client-market-view.ts` renders
those values as chart suggestions and labels the controls as display-only.
When discovery is stale, not checked, empty, or failed, the suggestion list is
empty. Entering a symbol still changes only the displayed snapshot and never
changes the AI candidate universe or a decision.

The render regression suite covers a fresh dynamic pool (`XRPUSDT` and
`ADAUSDT`), a stale pool with no suggestions, and the absence of the old
`DOGEUSDT` starter value. The current-worktree verification on 2026-11-20
passed: `CI=1 NX_DAEMON=false pnpm run verify` (exit 0) and
`pnpm --dir apps/dsh-plugin run verify` (exit 0, as recorded by the UI task).
This closes the screenshot follow-up within the UI boundary; it does not add
strategy-runtime, exchange execution, reconciliation, or unattended-trading
authority.

## Live panel recheck (2026-11-20)

The active DeepSeek Harness panel was re-read through Cua Driver after the
Bundle reload. Its accessibility tree and screenshot now show the current
`运行边界` and `行情查看` copy, including the independent AI candidate-pool
status, default-closed simulated scheduler, unavailable exchange writer, and
unknown account readiness. The chart symbol/market/interval controls are
explicitly view-only, and the internal-paper card exposes status inspection
without start/stop/order controls. This is a presentation and boundary receipt
only; it does not add evidence for exchange writes, reconciliation, restart
recovery, or end-to-end unattended trading. The earlier statement that live
visual verification was pending applies to the pre-reload snapshot and is
superseded by this receipt. At the captured 1280×820 size, a companion overlay
covered part of the candidate/status text, so readability should be checked at
other sizes and with that overlay hidden.

## 2026-11-21 analysis-first panel order

The supplied screenshot placed engine, native-paper, and runtime-readiness
cards before the market chart and profit/analysis sections. To match the
user-facing purpose of a read-only analysis dashboard, `client.ts` now renders
market data, the chart, paper/backtest analysis, and AI simulated PnL before a
default-collapsed “System and runtime status” section. Environment, API-key
presence, and the unavailable exchange-write badge remain in the header.
Runtime diagnostics are still available on demand; AI universe and decision
inputs are unchanged.

`pnpm --dir apps/dsh-plugin run verify` exited 0 on 2026-11-21, including the
SSR order assertion, build, lint, source/test typechecks, unit tests, and Bundle
check. Oxlint reported five non-blocking warnings. The live Bundle was not
reinstalled for this layout change, so collapsed-section discovery and
accessibility still need visual review in the active Host.

## 2026-11-21 active Bundle receipt after Plugin Manager restart

According to the handoff receipt, the plugin was re-enabled through the
official Harness Plugin Manager and the Harness was restarted. A fresh Cua
Driver accessibility-tree read of the active panel confirms that the
analysis-first layout is installed: market view, paper ledger, backtest, and AI
simulated PnL precede the default-collapsed “System and runtime status”
disclosure. The active copy states that chart symbol, market, and candle
interval are display-only and that AI independently chooses whether to trade,
symbol, direction, size, exits, and holding horizon. The header still reports
Testnet, exchange writes unavailable, and API-key presence; no order controls
or unattended live-execution control is exposed.

This receipt supersedes the preceding “live Bundle was not reinstalled” note
for the current active window. It is a UI installation and accessibility
receipt only: no scheduler, account action, exchange request, order,
reconciliation, or recovery test was performed. The architecture-book
end-to-end unattended quant-trading acceptance therefore remains **PARTIAL**.

## Reverification update (2026-11-19)

After restoring the Bybit workspace root manifest and lockfile, the full gate was rerun successfully:

```text
pnpm run verify                         exit 0
pnpm run python:lint                    exit 0
pnpm run python:typecheck               exit 0
pnpm run python:test                    exit 0 (405 passed, 11 warnings)
pnpm run security:deps                  exit 0
gitleaks dir --redact --no-banner       exit 0
pnpm run sbom                           exit 0
nx show projects                        exit 0 (8 projects)
```

The earlier registry 404 remains historical evidence for the previous root manifest state; it is not the current Verify Gate result. This update does not change the product scope: Testnet/Mainnet exchange writes, complete reconciliation, and the architecture book's end-to-end unattended trading remain unimplemented.
