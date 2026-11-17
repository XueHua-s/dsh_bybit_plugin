# Bybit AI Quant

Bybit AI Quant is a DeepSeek Harness (DSH) Bundle implemented as a TypeScript Host/Client plugin. The repository is an Nx + pnpm workspace; the Python uv workspace contains `quant-data`, the independent read-only `quant-engine` market service and an optional native synthetic paper service. The current plugin provides Bybit REST market data, deterministic indicators and long-only backtests, a local paper book, a watchlist, an AI decision journal with code-owned risk gates, and a web panel with read-only market views and explicit native-paper controls.

The repository is an active development workspace. The full autonomous quant platform described in the SDD is not complete. The Python engine now consumes public Testnet WebSocket tickers through a bounded adapter and supervised consumer, independently of DSH. A generated, runtime-validated TypeScript SDK connects DSH engine tools and a read-only panel card to that service; existing candle/account/analysis views retain REST paths. An offline native Nautilus foundation now proves finite backtest fills and cancellation. Nautilus as sole exchange execution authority, the full quant/AI/research platform, Plugin Manager upgrade preservation, and real OAuth remain incomplete or unverified. See the [original-scope audit](sdd/reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md).

## Install the Bundle

Use the official DSH Plugin Manager `install_bundle` flow with this repository (or its built package). Do not edit managed Harness Profile files, `package.json`, or `cordis.patch.yml` by hand. Build the plugin before installation so the exported Host and browser entries exist:

```sh
pnpm install --frozen-lockfile
pnpm build
pnpm bundle:check
```

The Bundle patch inserts the `@bybit-quant/dsh-plugin` Host row and defaults to `[TESTNET]`. It contains no credentials. Upgrade and uninstall through the Plugin Manager; keep the user-owned state and credential files under `$DSH_HOME/bybit-quant/`.

## Available tools

- `bybit_market`, `bybit_instruments`, and `bybit_account` read public market/instrument data or authenticated account data.
- `quant_signals`, `quant_backtest`, and `quant_watchlist` provide deterministic indicators, long-only backtests, and an exchange-verified symbol list.
- `quant_paper` operates a local simulated USDT book.
- `quant_brief`, `quant_decide`, and `quant_review` build a market brief, apply code-side limits to an AI proposal, journal the decision, and score completed decisions.
- `quant_get_engine_status` and `quant_get_market_snapshot` read independent engine facts through the generated SDK; market readiness never implies account or execution readiness.
- `quant_get_paper_status`, `quant_start_paper`, `quant_stop_paper`, `quant_submit_paper_order` and `quant_get_paper_command` address the separate native synthetic service; mutations require explicit paper configuration and default-off control opt-in.
- `bybit_trade` previews or sends an order only after every configured safety check passes.

Backtests are single-asset and long-only. They do not model leverage, funding, or profitability guarantees.

## Trading safety

The Bundle defaults to `env: testnet`, `allowLiveTrading: false`, `allowTestnetTrading: true`, and a 24 USDT per-order notional ceiling. Mainnet is disabled by default. A real order also requires credentials, the correct environment switch, `confirm: "LIVE"`, and `dryRun: false`; account identity, balance, instrument precision, notional, and risk limits are checked in code. `allowMainAccount` is an additional explicit guard for a main-account key. Testnet authorization never authorizes Mainnet activity.

The panel provides REST views and demand-driven engine checks through the authenticated DSH bridge. Its separate native-paper card offers manual status, Start and Stop for the configured synthetic session, with no browser order-submission route or background polling. Python services remain loopback-only; authenticated remote deployment is not implemented. Installed carrier authentication and browser interaction acceptance remain pending.

## Testnet OAuth

The bundled PKCE client is a local Testnet OAuth flow. Bybit's public documentation does not confirm that this OAuth grant is available for Testnet, so this client remains unverified provider integration rather than a supported production login. Run the commands from the repository root:

```sh
pnpm --filter @bybit-quant/dsh-plugin oauth -- start
pnpm --filter @bybit-quant/dsh-plugin oauth -- exchange
pnpm --filter @bybit-quant/dsh-plugin oauth -- accounts
pnpm --filter @bybit-quant/dsh-plugin oauth -- select <sub_member_id>
```

Before clicking **Authorize**, review the agent name and requested scopes in Bybit yourself. Then review the returned accounts and explicitly select the intended AI sub-account. The client does not auto-select or create an account. Tokens are stored privately with restrictive permissions and are never printed. No real consent, revoke, or Testnet provider lifecycle has been verified; revoke access by removing the AI sub-account in Bybit. Mainnet OAuth is not supported by this flow.

## Workspace layout

```text
apps/dsh-plugin/       DSH Host, browser client, tools, scripts, tests
python/packages/quant-data/  Alembic data package and local durable command ledger
python/packages/quant-risk/  Pure deterministic risk veto foundation
packages/ts/quant-contracts/ Shared market DTOs
packages/ts/quant-api-client/ Generated engine SDK + runtime validation
python/packages/quant-execution/ Offline native Nautilus foundation
python/apps/quant-engine/   Independent read-only Testnet service
sdd/                   Brainstorm, Define, Design, and evidence reports
```

`dist/` is generated output and is the only plugin payload. Handwritten TypeScript is strict and kept at or below 500 lines per file. Python projects are managed by uv; Nx discovers `@bybit-quant/dsh-plugin`, `quant-data`, `@bybit-quant/quant-contracts`, `@bybit-quant/quant-api-client`, `quant-execution`, `quant-risk`, and `quant-engine` as seven independent projects (discovery and actual dependency graph verified).

## Development and verification

```sh
pnpm install --frozen-lockfile
pnpm build
pnpm lint
pnpm typecheck
pnpm test:unit
pnpm exec nx run @bybit-quant/dsh-plugin:test:paper-process --skip-nx-cache
pnpm bundle:check
pnpm sdk:check
pnpm sdk:test
pnpm typecheck:tooling
pnpm test:tooling
pnpm python:lint
pnpm python:typecheck
pnpm python:test
pnpm run security:deps
pnpm run sbom
```

`pnpm test:network` is not a root script; the read-only public Testnet smoke is run with `pnpm exec nx run @bybit-quant/dsh-plugin:test:network`. It binds market reads to `api-testnet.bybit.com`, uses no credentials, and never sends orders; it may be unavailable when the network is offline. Host integration tests remain separate and are not part of this network target. The release Verify Gate is `pnpm run verify`; a green documentation or CI job does not replace official Plugin Manager lifecycle evidence.

## Independent Testnet engine

Run from the repository root with an explicit symbol set:

```sh
uv sync --project python --locked
uv run --project python --locked quant-engine --symbols BTCUSDT ETHUSDT
```

The loopback-only service exposes read-only `/api/v1/health` and `/api/v1/market/{symbol}` at `127.0.0.1:8765`. It uses no credentials or order APIs. Health readiness describes fresh market ingestion; execution/reconciliation remain unknown. Partial ticker updates retain null fields. See the [engine runbook](docs/runbooks/engine-service.md) for readiness, shutdown, Nx commands and offline OpenAPI verification. DSH defaults `engineBaseUrl` to `http://127.0.0.1:8765`; only numeric loopback HTTP origins are accepted. The two engine tools and authenticated `?view=engine` bridge view use this SDK. The panel offers an explicit engine check, with no background polling; unloading DSH cancels its requests while the independent process continues. Partial prices stay null and failures use bounded safe codes.

## Offline native execution and verification limits

`uv run --project python --locked pytest python/packages/quant-execution/tests -q` runs actual NautilusTrader 1.231.0 `BacktestEngine` fixtures, including market fills, resting cancellation and partial fill then cancellation. The offline simulation API accepts only literal `backtest`; the separate synthetic paper runtime is described below. It provides no live/Testnet executor, durable order recovery or complete final risk engine; the existing TS REST order path has not yet been cut over to Nautilus.

Use the locked root `uv` workspace for native tests. It explicitly overrides fsspec to patched2026.6.0 while Nautilus1.231.0 still declares an exact2026.2.0 pin. The patched environment passes vulnerability scanning and compatibility fixtures, but `uv pip check` reports that declared mismatch and standalone pip resolution rejects it; metadata compatibility is not claimed.

The generated SDK, DSH integration, native execution and admission layers have independent scoped ACCEPT reviews. Published code `b75d73c` includes the authenticated continuous paper service, transactional risk reservations and generated paper SDK. Its [hosted CI](https://github.com/XueHua-s/dsh_bybit_plugin/actions/runs/44089248505) passed both jobs; blocking verification, four Python projects, both actual OpenAPI contracts, security scans and SBOM steps were inspected. Actual commit/push hooks passed, including 252 Python tests. [Draft PR #1](https://github.com/XueHua-s/dsh_bybit_plugin/pull/1) remains unmerged. This receipt covers the code commit; this documentation/governance follow-up is verified separately. Browser interaction, installed Harness authentication and official upgrade preservation remain incomplete. See the [Verify Gate](sdd/reports/VERIFY_GATE_2026-11-17.md) for evidence and limits.

## Risk and durable command foundations

The new `quant-risk` package provides a pure independent veto over engine-owned snapshots, pending reservations and explicit policy, using conservative Decimal gross-exposure arithmetic after validation. `quant-data` adds a local SQLite command ledger for idempotency, lifecycle transitions, single dispatch claims and append-only audit events. Both have independent scoped ACCEPT reviews; the published risk/ledger baseline passed 213 Python tests, typing and lint/format checks; the current paper-integrated workspace passes 252. This verifies the foundations; neither is yet the integrated final execution gate.

Risk approval grants no trading authority, and the ledger sends or automatically resends no orders. The optional synthetic paper service below now integrates serialized account ownership, atomic risk reservations and durable native submission evidence. Sole exchange execution authority, TS REST cutover, complete long-lived private state and uncertain-order reconciliation remain incomplete. The new Alembic migration is limited to isolated tests; no user database has been migrated. See the [risk design](sdd/features/DESIGN_QUANT_RISK.md), [command ledger design](sdd/features/DESIGN_COMMAND_LEDGER.md) and [Verify Gate](sdd/reports/VERIFY_GATE_2026-11-17.md).

## Continuous native internal paper

An optional separate paper application runs Nautilus `TradingNode` in a spawned process. Engine-owned admission serializes real risk evaluation, durable commands and reservations before native dispatch. It supports only an explicit synthetic BTC fixture with finite depth and LIMIT commands. The default market application retains its two read-only routes; paper has a separate `quant-paper.v1` OpenAPI contract and generated SDK. A private Unix broker provisions its in-memory capability to the DSH Host for a fixed session and origin; the independent trusted-launcher FD mode remains supported. No token is configured, passed in argv/environment, persisted to a file or exposed to the browser/model.

Native runtime, optional service and SDK have independent scoped ACCEPT reviews. The [DSH native-paper process receipt](sdd/reports/DSH_PAPER_PROCESS_E2E_2026-11-17.md) exercises the actual built Host→private broker→SDK→CLI→native process, including risk veto, native fills, original-identity recovery after an injected post-dispatch503, Host-close independence and bounded cleanup. The native-paper card has explicit Check/Start/Stop controls and a permanent synthetic/no-exchange identity; configuration and control default off. This blocking process target is a current working-tree check and does not create a hosted CI receipt. Installed Harness authentication, real browser interaction and official upgrade preservation remain pending. Legacy `quant_paper`, AI books and the TS exchange trading path remain separate; Nautilus-only exchange execution, TS write cutover, full recovery, strategies, AI and isolated research remain incomplete. The full product remains PARTIAL. The [paper service runbook](docs/runbooks/paper-service.md) provides the explicit temporary migrated-DB broker workflow and retained FD mode.

## License scope

The repository root license is MIT. `quant-execution` is a mixed-license package with metadata `MIT AND LGPL-3.0-only`: [paper_sandbox.py](python/packages/quant-execution/src/quant_execution/paper_sandbox.py) adapts pinned NautilusTrader 1.231.0 source and retains LGPL-3.0-only; other original execution code is MIT. Its [NOTICE](python/packages/quant-execution/NOTICE.md) and `LICENSES/` ship with source and wheel distributions, including LGPLv3 and its incorporated GPLv3 base terms; accompanying GPL text does not change original MIT file licenses. The root MIT license does not relicense that adapted file or third-party dependencies as MIT.

## State and credentials

Legacy paper state and journals default to `$DSH_HOME/bybit-quant/state.json`; native paper uses the explicitly selected migrated SQLite database and service-owned session. Exchange API credentials come from the DSH credential store, the documented environment variables, or a local permission-restricted file; they must never be committed, logged, or placed in the Bundle patch. The native-paper capability uses only private in-memory provisioning, with no exchange-credential fallback. The Python Alembic schema and backup helpers require an explicit environment and backup plan before use against durable data.

## Limitations

The independent service supports bounded public Testnet streaming/reconnect and in-process worker restart. OS process recovery, complete snapshot reconstruction/persistence, account/order recovery, reconciliation, autonomous investment competence, and Mainnet readiness remain unverified or unimplemented. Use Testnet, mocks, or public endpoints for development and review the SDD evidence before enabling any additional capability.
