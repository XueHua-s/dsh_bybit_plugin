# BUILD REPORT: Bybit AI Quant

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

Evidence: the targeted backup test and complete local chain `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test` exited 0 (15 Python tests passed). Separate temporary `SIGKILL` and SQLite restore rehearsals also exited 0. Recovery remains bounded to existing TS state and SQLite backup behavior; Python runtime lacks durable checkpoint/supervisor/reconciliation.

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
| Tasks completed | 14/16 implementation groups |
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
| 7 | Add Alembic, backup/restore, sandbox and trust boundaries | Partial for current scaffold | Python tests and isolated checks; prompt trust helper is not wired to runtime call sites |
| 8 | Add runtime metrics and health route | Complete for current scaffold | monitor/integration checks |
| 9 | Update bilingual README and CI | Complete | docs review, YAML parse, diff check |
| 10 | Pin and audit GitHub references | Complete for stated audit scope | `docs/research/github-repository-audit.md` |
| 11 | Strictly type test sources and repair test fixtures | Complete | `pnpm typecheck:tests` exit 0 |
| 12 | Generate TS/Python SBOM and dependency/secret evidence | Complete | SBOM, audit and gitleaks commands |
| 13 | Official Harness install/uninstall/reinstall/enable smoke | Partial | receipt in `PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md` |
| 14 | Upgrade smoke in disposable profile | Blocked | no local standalone manager; local UI did not expose a version upgrade |
| 15 | Real WebSocket/reconnect and durable engine recovery | Blocked | current implementation documents REST polling and scaffold lifecycle |
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
| Complementary | `pnpm typecheck:tests`, Python lint/typecheck/test, isolated Alembic up/down, network smoke (7 + 27 checks), SBOM generation, dependency audit, gitleaks and line-count checks passed |

## Acceptance Test Verification

| ID | Status | Evidence |
|---|---|---|
| AT-001 | Pass | Nx discovers `@bybit-quant/dsh-plugin`, `@bybit-quant/quant-contracts`, `quant-data`, `quant-engine`; graph contains plugin → contracts and engine → data |
| AT-002 | Pass | strict TS checks and line cap; max handwritten source is 494 lines |
| AT-003 | Partial | official Harness install, enable, uninstall, reinstall and re-enable recorded; upgrade and disposable-profile preservation remain unverified |
| AT-004 | Pass for tested guards | 27 integration checks include disabled-live, missing-key, cap and paper/test paths; no order was sent |
| AT-005 | Partial | queue, memory/CPU, reconnect and latency metrics exist; WebSocket adapter is disabled and reconnect wiring is not production-complete |
| AT-006 | Pass for isolated scaffold | Alembic upgrade/downgrade and checksum backup/restore tests pass; full user-history migration across versions remains unproven |
| AT-007 | Partial | Docker runs with no network/read-only root/resource limits, and bounded stdout/stderr capture is tested; trust helper is not wired to runtime call sites, provider image is not digest-pinned, and full isolation review remains open |
| AT-008 | Pass | CycloneDX 1.6 TS (241 components) and Python (62 components), pnpm audit, pip-audit and gitleaks pass; editable Python packages are excluded by pip-audit |
| AT-009 | Pass | bilingual READMEs describe current verified behavior and contain no credentials |

## Drift Detected

| Drift | Decision | Action |
|---|---|---|
| Legacy Client ID `@local/bybit-quant` differed from Bundle manifest | Corrected | Client and test now use `@bybit-quant/dsh-plugin` |
| Detail file was outside Bundle package path | Corrected | Added `apps/dsh-plugin/docs/DETAIL.md` and fail-closed locale checks |
| pnpm SBOM command triggered package-manager shim under Nx | Corrected | Root `sbom` script runs the TypeScript generator directly with Corepack guard variables |

## Security and Operations Limits

Mainnet remained disabled; no real order was sent. API credentials were never written to repository files, logs, reports or README. External news, GitHub content and agent inputs remain untrusted. The current Python engine is a lifecycle scaffold, and the plugin uses REST polling; production WebSocket, automatic recovery, upgrade migration preservation and upgrade receipt still require a later phase.

## Official Plugin Manager Receipt

See [PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md](./PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md). The Harness UI install/detail/enable/uninstall/reinstall flow passed. The receipt explicitly does not claim upgrade because the installed version stayed 1.4.5 and the active profile was not disposable.

## Blockers

### Sandbox output bound and OAuth documentation correction — 2026-11-17

`apps/dsh-plugin/src/lib/sandbox.ts` now retains stdout/stderr in fixed-capacity byte buffers while draining child streams; the new `sandbox-output.ts` regression floods the helper with 100 × 2 MB chunks and verifies it retains only 400 KB. The regression is wired into both the Nx and package unit targets. Both READMEs now state that Bybit Testnet OAuth support and real consent/revoke lifecycle are unverified, and require the user to inspect the agent/scopes before authorizing. Verification: `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test && git diff --check` → exit 0; 15 Python tests passed. This does not run Docker or establish image digest provenance. Prompt trust runtime wiring, image digest pinning, Plugin Manager upgrade, durable recovery, and Testnet order E2E remain open.

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
2. Implement and verify a real WebSocket adapter, reconnect policy, graceful shutdown and durable restart checkpoint.
3. Complete funded Testnet sub-account identity and balance verification before any order E2E; never bypass the guard.

## Final Status

**IN PROGRESS / NOT READY FOR PRODUCTION.**

The repository is structurally buildable and the defined local Verify Gate is green, but the unresolved lifecycle-upgrade, WebSocket/recovery and account-state gates prevent claiming the full autonomous quant platform is complete.
