# Bybit AI Quant

Bybit AI Quant is a DeepSeek Harness (DSH) Bundle implemented as a TypeScript Host/Client plugin. The repository is an Nx + pnpm workspace; the Python uv workspace contains the `quant-data` package and the independent read-only `quant-engine` market service. The current plugin provides Bybit REST market data, deterministic indicators and long-only backtests, a local paper book, a watchlist, an AI decision journal with code-owned risk gates, and a read-only web panel.

The repository is an active development workspace. The full autonomous quant platform described in the SDD is not complete. The Python engine now consumes public Testnet WebSocket tickers through a bounded adapter and supervised consumer, independently of DSH. The DSH panel still uses REST polling. Generated TypeScript SDK/DSH integration, Nautilus as sole execution authority, the full quant/AI/research platform, Plugin Manager upgrade preservation, and real OAuth remain incomplete or unverified. See the [original-scope audit](sdd/reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md).

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
- `bybit_trade` previews or sends an order only after every configured safety check passes.

Backtests are single-asset and long-only. They do not model leverage, funding, or profitability guarantees.

## Trading safety

The Bundle defaults to `env: testnet`, `allowLiveTrading: false`, `allowTestnetTrading: true`, and a 24 USDT per-order notional ceiling. Mainnet is disabled by default. A real order also requires credentials, the correct environment switch, `confirm: "LIVE"`, and `dryRun: false`; account identity, balance, instrument precision, notional, and risk limits are checked in code. `allowMainAccount` is an additional explicit guard for a main-account key. Testnet authorization never authorizes Mainnet activity.

The panel never places orders. It uses the authenticated DSH bridge and REST polling; it does not add an unauthenticated route.

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
python/packages/quant-data/  Alembic data package
packages/ts/quant-contracts/ Shared market DTOs
python/apps/quant-engine/   Independent read-only Testnet service
sdd/                   Brainstorm, Define, Design, and evidence reports
```

`dist/` is generated output and is the only plugin payload. Handwritten TypeScript is strict and kept at or below 500 lines per file. Python projects are managed by uv; Nx discovers `@bybit-quant/dsh-plugin`, `quant-data`, `@bybit-quant/quant-contracts`, and `quant-engine` as independent projects.

## Development and verification

```sh
pnpm install --frozen-lockfile
pnpm build
pnpm lint
pnpm typecheck
pnpm test:unit
pnpm bundle:check
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

The loopback-only service exposes read-only `/api/v1/health` and `/api/v1/market/{symbol}` at `127.0.0.1:8765`. It uses no credentials or order APIs. Health readiness describes fresh market ingestion; execution/reconciliation remain unknown. Partial ticker updates retain null fields. See the [engine runbook](docs/runbooks/engine-service.md) for readiness, shutdown, Nx commands and offline OpenAPI verification. The service is not yet connected to DSH through a generated TypeScript SDK.

## State and credentials

Paper state and journals default to `$DSH_HOME/bybit-quant/state.json`. API credentials come from the DSH credential store, the documented environment variables, or a local permission-restricted file; they must never be committed, logged, or placed in the Bundle patch. The Python Alembic schema and backup helpers are development components and require an explicit environment and backup plan before use against durable data.

## Limitations

The independent service supports bounded public Testnet streaming/reconnect and in-process worker restart. OS process recovery, complete snapshot reconstruction/persistence, account/order recovery, reconciliation, autonomous investment competence, and Mainnet readiness remain unverified or unimplemented. Use Testnet, mocks, or public endpoints for development and review the SDD evidence before enabling any additional capability.
