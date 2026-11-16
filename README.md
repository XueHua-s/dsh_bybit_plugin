# Bybit AI Quant

Bybit AI Quant is a DeepSeek Harness (DSH) Bundle implemented as a TypeScript Host/Client plugin. The repository is an Nx + pnpm workspace; the Python uv workspace contains the `quant-data` package and `quant-engine` application scaffolds. The current plugin provides Bybit REST market data, deterministic indicators and long-only backtests, a local paper book, a watchlist, an AI decision journal with code-owned risk gates, and a read-only web panel.

The repository is an active development workspace. The full autonomous quant platform described in the SDD is not complete: WebSocket ingestion, reconnect wiring, long-running engine orchestration, Plugin Manager lifecycle receipts, and production readiness remain unverified. REST polling is the only market-data mode currently enabled.

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
python/apps/quant-engine/   Python engine scaffold
sdd/                   Brainstorm, Define, Design, and evidence reports
```

`dist/` is generated output and is the only plugin payload. Handwritten TypeScript is strict and kept at or below 500 lines per file. Python projects are managed by uv; Nx discovers `@bybit-quant/dsh-plugin`, `quant-data`, and `quant-engine` as independent projects.

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

## State and credentials

Paper state and journals default to `$DSH_HOME/bybit-quant/state.json`. API credentials come from the DSH credential store, the documented environment variables, or a local permission-restricted file; they must never be committed, logged, or placed in the Bundle patch. The Python Alembic schema and backup helpers are development components and require an explicit environment and backup plan before use against durable data.

## Limitations

This release does not claim WebSocket streaming, automatic reconnect/recovery, a production-grade long-running Python service, autonomous investment competence, or Mainnet readiness. Use Testnet, mocks, or public endpoints for development and review the SDD evidence before enabling any additional capability.
