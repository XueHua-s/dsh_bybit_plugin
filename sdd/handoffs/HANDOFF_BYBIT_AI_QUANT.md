# HANDOFF: BYBIT_AI_QUANT

## Ficha

| Attribute | Value |
|---|---|
| Feature | BYBIT_AI_QUANT |
| Objective | Complete the original architecture MUSTs through independently verified increments; a scaffold is not the product. |
| Status | IN PROGRESS / PARTIAL. SDK/DSH/native/hooks accepted locally; final aggregate/security/scoped checks passed; declared Nautilus/fsspec metadata mismatch remains. |
| Date | 2026-11-17 |
| Branch / folder | `codex/bybit-ai-quant-sdd` · `/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant` |
| Published code | `4360381c86df468c1eb35a04c9eb880d515cb514`, pushed; `ls-remote` exact match verified. Earlier baseline `f535981` is historical. |
| Authority | `AGENTS.md`, `sdd/features/DEFINE_BYBIT_AI_QUANT.md`, main DESIGN and `sdd/reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md` |

## Current delivered state

- Real Nx/pnpm/uv monorepo: DSH plugin, contracts, generated API client, engine, data and native execution projects; preserve actual graph evidence. Root owns orchestration.
- Independent loopback-only FastAPI Testnet process owns bounded WebSocket ingestion, a continuous consumer and finite in-process supervisor. Health readiness is market ingestion only; execution/reconciliation unknown. Two read-only routes, no credentials/private API/order endpoint. Checkpoint v2 restores reconnect count only. Full snapshot/persistence/OS restart/account recovery remain open.
- Generated `quant-api-client` uses Python OpenAPI authority, openapi-typescript/openapi-fetch and Ajv runtime validation, loopback-only origin, total deadline/byte limits/cancellation and safe errors. Nine Vitest tests and deliberate drift failure pass.
- Actual DSH tools `quant_get_engine_status` / `quant_get_market_snapshot`, authenticated `?view=engine` bridge and explicit engine card use SDK. Existing REST candle/account/analysis remains. No background polling; Host unload cancels SDK calls without stopping the independent service. Non-Testnet Hosts fail closed, no credential is passed to engine.
- Private TS packages are build-only dependencies and their runtime is inlined. Packed archive imported outside repo with no node_modules proves bundle closure only. Real React19 SSR runs without skip; it cannot prove effects/browser fetching/visual interaction or installed authentication/upgrade.
- `quant-execution` uses real pinned stable Nautilus1.231.0 BacktestEngine, finite native fills/resting cancel/partial-cancel, IDs, run-local deduplication and disposal. Only literal backtest accepted. Twenty-two native/catalog tests pass. No live/Testnet executor, complete final risk, durable OMS/reconciliation or TS REST cutover.
- Hooks have nine isolated fixtures: nested sensitive-path refusal, redacted scanner diagnostics, unchanged index/partial-staging refusal, filename argv safety and monorepo task gates. CI configuration includes root all-TS/SDK/tooling, Python/native and security/schema gates. Actual pre-commit/pre-push hooks ran exit0 during code commit/push. Hosted run44076026205 succeeded for exact code SHA4360381, blocking verify and public Testnet jobs both passed.
- Four new scoped ACCEPT reviews: `REVIEW_ENGINE_CLIENT`, `REVIEW_DSH_ENGINE`, `REVIEW_NAUTILUS_EXECUTION`, `REVIEW_GIT_HOOKS` under `sdd/reviews/`, suffix `_2026-11-17.md`. Previous transport/supervisor/service ACCEPTs remain scoped.

## Current gate and failures

New root verify first FAILED1 at nested pnpm ENOEXEC; SDK Nx targets corrected to direct installed commands, fresh scoped five-task SDK rerun exit0. Second root aggregate also failed1 at child pnpm pack ENOEXEC; shared sanitized pnpm environment helper fixes nested execution and actual Nx bundle check now passes. Final root verify/test-types/discovery exit0: fresh unit/pack/schema/SDK/tooling checks, some cached build/types; six projects. Cross-process built DSH facade/SDK → actual FastAPI public Testnet ETHUSDT health/market200, partial=true/executionReady=false, SDKclose does not stop server; ordered SIGTERM/listener closure probe0. SDK 9 Vitest, hooks9 fixtures and real SSR pass locally.

Initial dependency audit FAILED for fsspec 2026.2.0. Explicit root uv override now installs patched 2026.6.0, pip-audit exits0, and native author reports 22 native / 133 full passing including catalog compatibility. However Nautilus metadata exact-pins2026.2.0: uv pip check exits1 and standalone pip correctly refuses conflicting metadata. Use the root uv workspace; do not claim full declared dependency compatibility. Independent native reviewer ACCEPT confirms 22 native / 133 full plus catalog round-trip. Final root Python lint27 files/typecheck0/133 tests6.67s/schema/diff0; security:deps0 no known vulnerabilities (three editables skipped), SBOM Python89/TS200, changed-files gitleaks68/913521bytes and full-history7commits~1.59MB scans0;92 handwritten sources max497. Earlier111-test/securitygreen receipts belong to f535981-era source and do not certify new lock.

Historical Verify Gate receipts cover Testnet ingestion/shutdown, restore/SIGKILL and isolated SQLite protection. Uvicorn re-raises SIGTERM after shutdown; -15 alone proves neither success nor failure. Target DB **not migrated**. Official install/reinstall receipts do not prove upgrade/state hashes. OAuth fake tests do not prove provider support/consent/revoke; CLI has no revoke.

## Remaining original MUSTs / Definition of Done

- [x] Preserve complete original MUST/AT-010–031 and audit initial snapshot plus latest delta.
- [x] Accepted read-only service, generated SDK/DSH, native backtest foundation and safe tooling increments.
- [ ] Final current root/security/schema/SBOM/secret/line/diff/real-service receipts complete, failures addressed or explicitly unresolved.
- [ ] Nautilus sole exchange order authority and direct TS REST cutover. DRIFT-ORIGINAL-003 remains OPEN; offline native tests do not resolve live authority.
- [ ] Full features/strategies/regime/portfolio/final-risk, AI team, isolated research/controlled evolution, durable uncertain orders/reconciliation and recovery.
- [ ] Complete market snapshot/history/provenance/persistence, authenticated remote control/events, OTel and OS process recovery.
- [x] Hosted CI for code4360381: blocking verify and public Testnet jobs successful; real hooks executed exit0.
- [ ] Official upgrade/state preservation, installed Harness auth, browser visual/interaction, provider OAuth and authorized target migration evidence.

## Landmines

No credential/.env reads or logging; no managed Harness profile edits. Mainnet defaults off and real trading requires separate explicit authorization. Testnet retains identity/balance/precision/notional/risk checks. No private account/order request was made this increment. Temporary SQLite is not deployed migration, SSR/pack import is not installed UI, fixtures are not provider consent. Do not create empty packages or claim profits/full platform from directories or local green tests.

## Events

- 2026-11-17: monorepo migration, corrected Testnet8 public smoke and migration/backup/checkpoint/trust/sandbox/supervisor hardening; historical receipts retained in Build/Verify.
- 2026-11-17: original scope audit restored independent engine/AI research MUSTs; no approved reduction to scaffold.
- 2026-11-17: independent service/transport/supervisor accepted, baseline f535981 committed/pushed verified.
- 2026-11-17: new generated SDK/DSH/native/hooks accepted; root ENOEXEC fixed and new dependency audit finding requires remediation.
- 2026-11-17: user already authorizes feature branch commit/push; old blanket prohibition is not additional policy. Run sdd-release checks first, never force or infer deployment.

- 2026-11-17: code4360381 committed/pushed, exact remote SHA verified; [Draft PR #1](https://github.com/XueHua-s/dsh_bybit_plugin/pull/1) created. [CI44076026205](https://github.com/XueHua-s/dsh_bybit_plugin/actions/runs/44076026205) completed success; detailed steps executed, `gh run watch` exit0. This documentation delta is separate and has not been tested by that earlier run.

## Setup / next tasks

```sh
cd /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant
pnpm install --frozen-lockfile
uv sync --project python --locked
uv run --project python --locked quant-engine --symbols BTCUSDT ETHUSDT
```

Service runbook: `docs/runbooks/engine-service.md`, loopback8765. Design supplements: `DESIGN_ENGINE_CLIENT.md`, `DESIGN_DSH_ENGINE.md`, `DESIGN_NAUTILUS_EXECUTION.md`, `DESIGN_GIT_HOOKS.md` under `sdd/features/`.

1. Continue from pushed code4360381 / Draft PR1. Record this separate documentation commit honestly; the code CI run does not test future documentation. Current aggregate/Python/security/schema/SBOM/secrets/source/SDK-real-service checks passed; retain two ENOEXEC and initial vulnerability failures plus metadata conflict.
2. Continue dependency-ordered original MUST implementation, next resolving sole execution/risk authority and durable state. New design/manifest before code, independent review before integration.
3. Before authorized feature-branch commit/push run `.agents/skills/sdd-release/SKILL.md`, inspect diff/staging/secret/history/baseline. No force, no main merge or deployment claim. Root records actual SHA/remote result. No worktree cleanup without user instruction.

## Resume prompt

```text
Continue BYBIT_AI_QUANT in /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant, branch codex/bybit-ai-quant-sdd. Read this handoff, AGENTS, DEFINE/main DESIGN, ORIGINAL_SCOPE_AUDIT and VERIFY_GATE_2026-11-17 first. Code4360381c86df468c1eb35a04c9eb880d515cb514 pushed and remote exact SHA verified; Draft PR https://github.com/XueHua-s/dsh_bybit_plugin/pull/1. CI44076026205 exacthead success: blocking verify and Testnet smoke, all detailed steps executed; actual hooks0. Subsequent documentation delta has separate verification, not covered by this code CI.
SDK uses generated Python schema and runtime validation; actual DSH tools/bridge/card use it. Native1.231.0 BacktestEngine tests real fills/partialcancel, backtest only; full sole live authority/TSREST cutover/risk/AI/research remain open. Reviews ACCEPT scoped only. SDK 9 Vitest, hooks 9 fixtures, SSR19 no skip, Python 133 passed with10 upstream warnings. Initial root ENOEXEC fixed; second aggregate pack ENOEXEC fixed with shared pnpm environment helper; final aggregate/testtypes/discovery0, sixprojects; realSDK→Testnetservice health/market200 and lifecycle probe0. Initial audit failed fsspec 2026.2.0; explicit uv override installs patched 2026.6.0 and pip-audit0. Native metadata mismatch remains (uv pip check1; standalone pip conflict), root uv workspace required. Independent review confirms 22 native / 133 full/catalog compatibility; final security0 (3editables skipped), SBOM89/200, secret/history/source/diff0.
Inspect git status --short --branch. Root gates: NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify, same prefix pnpm typecheck:tests; pnpm python:lint, python:typecheck, python:test; pnpm sdk:check; OpenAPI --check, updated SBOM/security/secret/line/diff. Preserve real exits; mocks need loopback permission. Runbook has service command and readiness/SIGTERM semantics.
Do not read/print credentials, send unauthorized orders, enable Mainnet, edit managed profiles or apply target migration. Target DB not migrated. Existing TSREST direct order path remains architectural drift. User authorizes feature branch commit/push after sdd-release checks; root must record actual result, not infer deployment. Continue full original MUSTs, no scaffold scope reduction.
```
