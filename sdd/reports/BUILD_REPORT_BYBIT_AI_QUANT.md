# BUILD REPORT: Bybit AI Quant

## Current SDK/DSH/native/hooks integration — 2026-11-17

Baseline `f535981` was committed and pushed with remote verification by root. The new uncommitted increment implements generated OpenAPI TypeScript SDK/runtime validation, actual DSH status/snapshot tools and authenticated bridge/card, offline native Nautilus BacktestEngine foundation, and safe monorepo hooks/CI wiring. See supplements/build reports `ENGINE_CLIENT`, `DSH_ENGINE`, `NAUTILUS_EXECUTION`, `GIT_HOOKS`; each has an independent scoped ACCEPT in `sdd/reviews/`.

SDK has 9 Vitest cases and positive/negative drift proof; DSH mock server integration and real React19 SSR now run without skip. SDK/private DTO packages are build-only dependencies, runtime is inlined, and extracted packed Host import outside the repository proves closure only. No official install/upgrade/auth or browser visual/interaction acceptance is inferred. Native stable 1.231.0 uses real events/fills/confirmed partial-cancel in 21 backtest-only tests; no live/Testnet executor, TS REST authority cutover, durable OMS/reconciliation or complete final risk is provided. Hooks have 9 isolated fixture scenarios, redacted scanner diagnostics and actual full TS/SDK/tooling gate composition. Hosted CI execution and hook installation remain unverified.

Initial Python workspace 132 tests passed, including 21 native tests and ten upstream Pandas deprecation warnings. New root aggregate initially failed exit1 at nested-pnpm ENOEXEC; corrected SDK Nx commands use installed root binaries. A second aggregate failed on child pnpm pack ENOEXEC; shared pnpm-environment helper fixed subprocess environment handling. Final root verify + test types + discovery now exit0 with daemon/plugin isolation disabled and task-local UV cache; fresh unit/pack/SDK/schema/tooling checks ran, some build/types cached, six projects discovered. Actual built DSH facade → SDK → real FastAPI public Testnet ETHUSDT probe exits0: health/market200, partial=true, executionReady=false; SDK close returns closed while service survives, then ordered server shutdown closes listener.

Initial dependency audit failed for fsspec 2026.2.0. Root uv override now uses patched 2026.6.0 and pip-audit exits0; the final run has 22 native / 133 full tests with a new catalog compatibility case. Nautilus metadata still exact-pins2026.2.0: uv pip check exits1 and standalone pip refuses the declared conflict. Root uv workspace is required; no fully metadata-compatible install claim. Independent native re-review ACCEPT confirms 22 native / 133 full tests, including catalog compatibility under override. Root final checks exit0: Python Ruff/format27 files, Pyright0,133 tests in6.67s with10 upstream Pandas warnings, schema/diff match; security:deps no known TS/Python vulnerabilities (three editables skipped), SBOM Python89/TS200, changed-file gitleaks68 files913521 bytes, full-history gitleaks7 commits~1.59MB,92 handwritten files max497. Metadata mismatch remains disclosed.

Latest final evidence belongs in Verify Gate. No new order/account call or target migration occurred; full original MUST scope remains active.

## Historical integrated service and original scope — 2026-11-17

The original complete architecture remains authoritative. `ORIGINAL_SCOPE_AUDIT_2026-11-17.md` restores independent engine and AI research/evolution MUST scope and DEFINE AT-010–031. Prior scaffold task completion does not certify that product. At that historical service-only snapshot SDK/DSH integration was incomplete; the latest increment above implements its read-only portion. Nautilus as sole exchange execution authority, full strategy/features/regime/portfolio/risk and AI/research/evolution remain incomplete. Existing direct TS REST order creation/cancellation is DRIFT-ORIGINAL-003; it has not been approved as an architectural substitute.

Delivered and independently accepted slices: hardened public Testnet transport, cancellation-safe finite-budget in-process supervisor, and independent read-only FastAPI service with real bounded consumer. Pydantic owns schema; `/api/v1/health` and `/api/v1/market/{symbol}` are loopback-only, expose fresh validated market updates and honest partial/null semantics. No credentials, account or order API exists in this service. The DSH panel remains on REST polling. See the three `sdd/reviews/REVIEW_ENGINE_*_2026-11-17.md` reports, `BUILD_REPORT_ENGINE_SERVICE.md`, generated `contracts/openapi/quant-engine.v1.json` and `docs/runbooks/engine-service.md`.

Root verification receipts: `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify && NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm typecheck:tests` exit 0 under approved loopback permissions; `pnpm python:lint`, `pnpm python:typecheck`, `pnpm python:test` exit 0, 21 formatted files, 0 type errors and **111 tests passed**. Schema `--check` and source diff check exit 0. TS/Python SBOM generation exit 0 (241/78 components); `pnpm run security:deps` exit 0, no known vulnerabilities, two editable workspace packages skipped. Exact failures and reruns are preserved in Verify Gate, including Nx sandbox callback-bind failure and test-only optional-Task narrowing correction.

Root's approved live public Testnet subprocess probe returned health 200 (`ready=true`, connected, execution unknown), then verified ordered uvicorn shutdown/lifespan completion markers and listener closure after SIGTERM. Probe exit 0; child -15 is uvicorn's documented-in-source signal re-raise after cleanup. Fixture lifecycle tests separately verify task/socket cleanup. This proves the bounded read-only process slice, not OS restart, trading readiness, complete market reconstruction or full original MUST acceptance. No real order or target migration was run. Official upgrade/state hashes and provider OAuth remain unverified. Git publication is separately owned by root; this report does not claim an unperformed commit/push.

## Historical in-process worker supervisor increment — 2026-11-17

Added `quant_engine.EngineSupervisor`, which owns one adapter/runtime pair, gracefully closes it, restarts a worker reporting `stopped`/`failed` up to a finite configured count, and exposes typed `SupervisorSnapshot` status. Fake-only pytest coverage checks restart, exhausted budget, close, and invalid configuration. The supervisor is in-process; it does not supervise processes, detect silent hangs, recover orders, reconcile exchange state, or establish live trading safety.

Verification: `uv run --project python --locked pytest python/apps/quant-engine/tests/test_supervisor.py -q` → exit 0 (3 passed); `uv run --project python --locked ruff check python/apps/quant-engine/src/quant_engine/supervisor.py python/apps/quant-engine/tests/test_supervisor.py` → exit 0; `uv run --project python --locked pyright python/apps/quant-engine/src` → exit 0 (0 diagnostics). One initial pytest run exited 1 because `pytest-asyncio` is not installed; tests were converted to standard-library `asyncio.run` and rerun successfully. Workspace-wide Python suite and root Verify Gate were pending at that historical increment; current integration receipts below supersede that pending status.

## Metadata

| Attribute | Value |
|---|---|
| Feature | BYBIT_AI_QUANT |
| Date | 2026-11-17 |
| Author | SDD Build |
| BRAINSTORM | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| DEFINE | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| DESIGN | `sdd/features/DESIGN_BYBIT_AI_QUANT.md` |
| Status | In Progress |

## Durable recovery increment — 2026-11-17

Added `apps/dsh-plugin/test/backup.ts` for isolated checksum-backed restore and tamper rejection, covering strategy/watchlist, paper trade, AI track and audit marker data. It is included in the plugin unit command.

Evidence: the targeted backup test and complete local chain `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test` exited 0. Separate temporary `SIGKILL` and SQLite restore rehearsals also exited 0. At that historical increment recovery was bounded to existing TS state, SQLite backup and the Python health checkpoint. The subsequent read-only service now has in-process supervision; order-state recovery, OS process recovery and reconciliation remain open.

## Nx unit target coverage correction — 2026-11-17

The Nx `@bybit-quant/dsh-plugin:test:unit` target was missing `apps/dsh-plugin/test/backup.ts` even though the package-level script already listed it. The target now invokes the backup test, so root `pnpm run verify` exercises the same regression.

Evidence after the configuration change: `pnpm exec nx run @bybit-quant/dsh-plugin:test:unit --skip-nx-cache --output-style=static` exited 0 and printed the backup test `PASS`; `pnpm run verify` exited 0; `pnpm typecheck:tests` exited 0; `git diff --check` exited 0. No backup or trading safety behavior was changed.

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 16 design work items plus workspace and evidence artifacts |
| Cross-file coupling | High: Nx, DSH Bundle, Python uv/Alembic, safety and CI contracts |
| Security surface | Credentials, untrusted prompts/code, sandbox, trading guards, state preservation |
| LLM prompt items | Present; model output remains proposal data behind typed trust/risk boundaries |
| Runtime capabilities | Default sequential execution with parallel Sol review agents |
| Recommendation | Sequential integration with independent architecture/test/research reviews |
| User decision | Proceeded under the supplied SDD/AGENTS.md requirements; child agents used GPT-6.1-Sol |

## Summary

| Metric | Value |
|---|---:|
| Scope | Phased implementation; original MUST acceptance AT-010–031 remains incomplete |
| Files created | Monorepo projects, SDD artifacts, reports, docs, SBOMs and tests |
| Files modified | Workspace, DSH plugin, CI, READMEs and tests |
| Files deleted/moved | Legacy root plugin sources moved under `apps/dsh-plugin` |
| Verify Gate | Green for `pnpm run verify`; complementary checks green |
| Execution mode | Sequential integration with parallel reviews |

## Task Execution

| # | Task | Status | Verification |
|---:|---|---|---|
| 1 | Read architecture brief and install SDD/software-design skills | Complete | Skill lock and `AGENTS.md` present |
| 2 | Establish Brainstorm → Define → Design artifacts | Complete | Files under `sdd/features/` |
| 3 | Migrate to Nx + pnpm + uv monorepo | Complete | `nx show projects` and graph |
| 4 | Add reusable `@bybit-quant/quant-contracts` deep package | Complete | package build/typecheck and app dependency edge |
| 5 | Implement DSH Bundle metadata, patch, Host/Client and lifecycle wiring | Complete | build, strict typecheck, bundle check |
| 6 | Fix packaged detail resource and fail-closed bundle check | Complete | Harness detail rendered; bundle check exit 0 |
| 7 | Add Alembic, backup/restore, sandbox and trust boundaries | Partial for bounded implementation | Python tests, bounded sandbox capture and runtime trust-envelope checks; provider image digest, full Docker review and service recovery remain open |
| 8 | Add runtime metrics and health route | Complete for read-only scope | monitor/integration checks |
| 9 | Update bilingual README and CI | Complete | docs review, YAML parse, diff check |
| 10 | Pin and audit GitHub references | Complete for stated audit scope | `docs/research/github-repository-audit.md` |
| 11 | Strictly type test sources and repair test fixtures | Complete | `pnpm typecheck:tests` exit 0 |
| 12 | Generate TS/Python SBOM and dependency/secret evidence | Complete | SBOM, audit and gitleaks commands |
| 13 | Official Harness install/uninstall/reinstall/enable smoke | Partial | receipt in `PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md` |
| 14 | Upgrade smoke in disposable profile | Blocked | no local standalone manager; local UI did not expose a version upgrade |
| 15 | Real WebSocket/reconnect and durable engine recovery | Partial | `EngineRuntime` now persists and validates a bounded health checkpoint; real WebSocket durability, process supervision and exchange reconciliation remain open |
| 16 | Full Testnet order E2E | Blocked by account state | prior read-only account had zero equity/main-account identity; guards correctly reject |

## Files Changed

The working tree contains the Nx workspace, `apps/dsh-plugin`, `packages/ts/quant-contracts`, Python uv projects, SDD artifacts, CI, READMEs, tests and SBOM outputs. Legacy root plugin files are intentionally removed after the staged migration. Credentials and Harness-managed profile files are not part of the change.

## Verify Gate

| Attribute | Value |
|---|---|
| Kind | test |
| Command | `pnpm run verify` |
| Result | exit 0 |
| Evidence | build, lint, strict production typecheck, unit tests and Bundle checks passed sequentially |
| Complementary | Current service integration: 111 Python tests; TS test types, Python lint/types, schema, SBOM/dependency checks passed. Earlier 7+27 network result is historical Mainnet public data; corrected Testnet smoke had 8 checks. See timestamped Verify Gate for exact coverage. |

## Acceptance Test Verification

| ID | Status | Evidence |
|---|---|---|
| AT-001 | Pass | Nx discovers `@bybit-quant/dsh-plugin`, `@bybit-quant/quant-contracts`, `quant-data`, `quant-engine`; graph contains plugin → contracts and engine → data |
| AT-002 | Pass | strict TS checks and line cap; max handwritten source is 494 lines |
| AT-003 | Partial | official Harness install, enable, uninstall, reinstall and re-enable recorded; upgrade and disposable-profile preservation remain unverified |
| AT-004 | Pass for tested guards | 27 integration checks include disabled-live, missing-key, cap and paper/test paths; no order was sent |
| AT-005 | Partial | Independent public Testnet WebSocket service consumes through a bounded queue with supervised worker restart; actual RSS/CPU/freshness are exposed. OS restart, complete data/order recovery, heartbeat hardening, reconciliation and execution metrics remain open. |
| AT-006 | Pass for isolated scaffold | Alembic upgrade/downgrade and checksum backup/restore tests pass; full user-history migration across versions remains unproven |
| AT-007 | Partial | Docker runs with no network/read-only root/resource limits and an immutable image digest; bounded stdout/stderr and runtime untrusted-evidence envelopes are tested. Full isolation review remains open |
| AT-008 | Pass | CycloneDX 1.6 TS (241 components) and Python (78 components), pnpm audit, pip-audit and gitleaks pass; editable Python packages are excluded by pip-audit |
| AT-009 | Pass | bilingual READMEs describe current verified behavior and contain no credentials |

## Drift Detected

| Drift | Decision | Action |
|---|---|---|
| Legacy Client ID `@local/bybit-quant` differed from Bundle manifest | Corrected | Client and test now use `@bybit-quant/dsh-plugin` |
| Detail file was outside Bundle package path | Corrected | Added `apps/dsh-plugin/docs/DETAIL.md` and fail-closed locale checks |
| pnpm SBOM command triggered package-manager shim under Nx | Corrected | Root `sbom` script runs the TypeScript generator directly with Corepack guard variables |

## Security and Operations Limits

Mainnet remained disabled; no real order was sent. API credentials were never written to repository files, logs, reports or README. External news, GitHub content and agent inputs remain untrusted. The Python engine now runs an independent read-only Testnet ingestion service with bounded worker restart; the DSH plugin still uses REST polling. OS recovery, complete data/order recovery, reconciliation, upgrade preservation and real upgrade evidence remain open.

## Official Plugin Manager Receipt

See [PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md](./PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md). The Harness UI install/detail/enable/uninstall/reinstall flow passed. The receipt explicitly does not claim upgrade because the installed version stayed 1.4.5 and the active profile was not disposable.

## Blockers

### Sandbox output bound and OAuth documentation correction — 2026-11-17

`apps/dsh-plugin/src/lib/sandbox.ts` now retains stdout/stderr in fixed-capacity byte buffers while draining child streams; the new `sandbox-output.ts` regression floods the helper with 100 × 2 MB chunks and verifies it retains only 400 KB. The regression is wired into both the Nx and package unit targets. Both READMEs now state that Bybit Testnet OAuth support and real consent/revoke lifecycle are unverified, and require the user to inspect the agent/scopes before authorizing. The 2026-11-19 follow-up pins the provider image to `node:22.20.0-alpine@sha256:dbcedd8aeab47fbc0f4dd4bffa55b7c3c729a707875968d467aaaea42d6225af` and runs the Docker smoke; see `SANDBOX_DIGEST_PIN_2026-11-19.md`. Prompt trust runtime wiring, Plugin Manager upgrade, durable recovery, and Testnet order E2E remain open.

### Prompt trust boundary increment — 2026-11-17

`normalizeDecision` now accepts only string thesis/invalidation values, normalizes NFKC and control characters, enforces 800/400-character limits, and keeps the persisted fields as strings for state compatibility. `quant_decide` and `quant_review` expose the prose through `{ kind: "untrusted-evidence", source: "agent", trusted: false, text }` envelopes; prose never enters the numerical risk gate. `apps/dsh-plugin/test/trust.ts` covers injection-like text, Unicode/control normalization, non-string and oversize rejection, envelope provenance, and identical risk results when only prose changes.

Verification: `pnpm exec nx run @bybit-quant/dsh-plugin:build --skip-nx-cache --output-style=static` → exit 0; `pnpm exec nx run @bybit-quant/dsh-plugin:lint --skip-nx-cache --output-style=static` → exit 0 after replacing control-character regex matching with code-point filtering; `pnpm exec nx run @bybit-quant/dsh-plugin:test:unit --skip-nx-cache --output-style=static` → exit 0; `pnpm typecheck:tests` → exit 0. The envelope is a containment and provenance boundary, not a claim that arbitrary LLM behavior is immune to prompt injection; no news/GitHub ingestion connector exists yet.

`apps/dsh-plugin/test/integration.ts` now contains assertions for the `quant_decide` and `quant_review` result envelope fields. That suite was not run in this slice because its host uses external market APIs; the local unit test covers envelope construction/provenance and the inspected call sites use that helper. The added integration assertions were typechecked only.

### Migration/backup protection increment — 2026-11-17

| Task | Status | Verification |
|---|---|---|
| Add explicit SQLite Alembic upgrade wrapper | Complete | `quant_data.migrations.upgrade_sqlite` takes an exclusive SQLite lock, rejects journal/WAL/SHM sidecars, snapshots a verified backup, checks the target is a forward descendant, upgrades a candidate and atomically installs it |
| Preserve user rows across migration | Complete for isolated fixture | strategy configuration, two trade-history/audit rows survive `0001_initial` → `head` |
| Refuse unsafe downgrade | Complete | non-empty `strategy_versions`/`trade_events` downgrade raises `RuntimeError`; empty-schema downgrade remains available |
| Failure recovery/concurrency boundary | Complete for tested SQLite boundary | failed candidate migrations retain source and backup; active writers, WAL mode, and all three sidecars are refused; source hash is rechecked immediately before replace; raw writers still require a maintenance window |
| Target database migration | Not run | only temporary SQLite fixtures were used; `bybit_quant.db`, `.env`, credentials and Harness state were not touched |

Commands and results: `uv run --project python --locked pytest python/packages/quant-data/tests/test_migrations.py -q` → exit 0 (9 passed); `uv run --project python --locked pytest python -q` → exit 0 (15 passed after concurrency/path fixtures); `uv run --project python --locked ruff check python/packages/quant-data` → exit 0; `uv run --project python --locked ruff format --check python/packages/quant-data` → exit 0; `uv run --project python --locked pyright python/packages/quant-data/src` → exit 0; `pnpm run verify` → exit 0; `pnpm python:lint`, `pnpm python:typecheck`, `pnpm python:test` → each exit 0; `git diff --check` → exit 0. An initial migration regression run exited 1 because literal JSON `:20` was parsed as a bind parameter and the assertion expected a different first guarded table; fixtures/assertion were corrected. Concurrency fixtures now cover all sidecars, active SQLite writer refusal, refusal of WAL journal mode without changing it, and an out-of-band source-file race; URL handling covers `?`, `#`, and spaces. Initial Ruff runs reported import ordering/formatting issues; these were corrected and final lint/format checks passed. No test command migrated a non-temporary database. The design rationale is recorded in [`ADR_MIGRATION_BACKUP.md`](./ADR_MIGRATION_BACKUP.md).

1. Obtain a disposable Harness profile or standalone official `plugin_manager` capable of an actual version upgrade and record before/after state hashes.
2. Verify production WebSocket restart behavior and implement process supervision plus exchange reconciliation; current checkpoint stores health counters only.
3. Complete funded Testnet sub-account identity and balance verification before any order E2E; never bypass the guard.

## Runtime checkpoint increment — 2026-11-17

`python/apps/quant-engine/src/quant_engine/runtime.py` now supports an optional versioned JSON checkpoint for graceful lifecycle restart. Version 2 persists only reconnect count. Queue depth and lifecycle timestamps are process-local: a new process starts with an empty queue, a new `started_at`, and `stopped_at=None`. Restore validates the compact v2 schema; legacy v1 files validate their historical running flag, timestamps and queue field, then ignore those values and retain only reconnect continuity. Writes use a flushed/fsynced temporary file with atomic replacement. Missing, malformed or unsupported checkpoints fail closed to zero health counters and expose `checkpoint_error` in `RuntimeSnapshot`; credentials, strategy configuration, orders and trade history are never serialized.

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| Runtime checkpoint tests | `uv run --project python --locked pytest python/apps/quant-engine/tests/test_runtime.py -q` | 0 | 8 tests passed, including compact v2 persistence, fresh restart timestamps, zeroed backlog, corrupted JSON, schema tampering, missing fields and legacy v1 compatibility. |
| Workspace Python lint/format | `pnpm python:lint` | 0 | Ruff passed; 13 Python files already formatted. The first post-schema run exited 1 on Ruff TRY004; changed the payload type error to `TypeError` and reran successfully. |
| Workspace Python typecheck | `pnpm python:typecheck` | 0 | Pyright reported 0 errors, warnings or information messages. |
| Workspace Python tests | `pnpm python:test` | 0 | 21 tests passed across quant-data, market-data and runtime checkpoint suites. |
| Diff whitespace | `git diff --check` | 0 | No whitespace errors. |

After review found that Python treats `True` as equal to integer `1`, version parsing was tightened to require an exact `int`; checkpoint restore also rejects missing required fields, validates legacy v1 fields for compatibility, and deliberately ignores all v1 lifecycle/queue values. A focused pytest run initially exited 1 because the v2 decoder still required the legacy `running` field; the validator was corrected. Final command `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test && git diff --check` exited 0; pytest reported 21 passed, and Nx's unchanged build/lint/typecheck tasks were cache hits.

This increment is a bounded health-state checkpoint only. It does not provide a process supervisor, crash-consistent order recovery, exchange reconciliation, or production WebSocket restart guarantee; those remain unresolved operational work.

## Final Status

**IN PROGRESS / NOT READY FOR PRODUCTION.**

The repository is structurally buildable and the defined local Verify Gate is green, but the unresolved lifecycle-upgrade, WebSocket/recovery and account-state gates prevent claiming the full autonomous quant platform is complete.

## Supervisor lifecycle hardening — 2026-11-17

Closed three review gaps: restart-budget exhaustion now closes the failed adapter and stops its runtime; cleanup is serialized and cancellation-safe while close waits for adapter/runtime cleanup; unexpected ordinary factory/start failures become terminal `failed` status while `CancelledError` propagates. Regression coverage expanded to five fake-only tests, including cleanup leak checks, a close/restart race, and unexpected factory failure.

Verification: focused supervisor pytest exit 0 (5 passed); workspace `pnpm python:lint` exit 0; `pnpm python:typecheck` exit 0; `pnpm python:test` exit 0 (26 passed); `pnpm run verify` exit 0; `pnpm typecheck:tests` exit 0; `git diff --check` exit 0. Limits remain unchanged: in-process lifecycle only, no OS process supervision, silent-hang detection, order recovery, exchange reconciliation, or live trading readiness.
