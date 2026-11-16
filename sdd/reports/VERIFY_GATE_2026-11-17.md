# Verify Gate Evidence — 2026-11-17

## Current rerun — 2026-11-17

This section records the final rerun after the earlier failures below. It is the sole current command status. Historical results remain useful as audit history and do not override this table.

The OAuth CLI local regression tests were added in the current follow-up. The `pnpm run verify` result below is the post-change rerun and its unit-test target includes `apps/dsh-plugin/test/oauth.ts`; the exact OAuth coverage and isolation limits are recorded in [`BUILD_REPORT_BYBIT_OAUTH_TESTS.md`](./BUILD_REPORT_BYBIT_OAUTH_TESTS.md).

| Check | Command / method | Exit | Current evidence and limits |
|---|---|---:|---|
| Defined root Verify Gate | `pnpm run verify` | 0 | Build, lint, strict production typecheck, unit tests, and bundle check completed sequentially. |
| TS test typecheck | `pnpm typecheck:tests` | 0 | Test source strict typecheck passed. |
| Corrected Nx Testnet market smoke | `pnpm exec nx run @bybit-quant/dsh-plugin:test:network --output-style=static` (run after the network target was corrected) | 0 | 8 checks passed against actual public Testnet market data; read-only, no credentials, account access, or orders, and no checks were skipped. This corrected run supersedes the earlier Mainnet-target network run below. |
| Python lint | `pnpm python:lint` | 0 | Ruff lint and format checks passed. |
| Python typecheck | `pnpm python:typecheck` | 0 | Pyright passed for current Python workspace projects. |
| Python tests | `pnpm python:test` | 0 | 7 passed. |
| Isolated Alembic round-trip | `uv run --project python --locked python -` (stdin script; temporary SQLite; `upgrade head`, assertions, `downgrade base`, assertions) | 0 | Temporary database only. The target/user database migration was **not applied**. |
| TS SBOM | `pnpm run sbom` | 0 | CycloneDX 1.6 generated. |
| Python SBOM | `pnpm exec nx run quant-data:sbom --output-style=static` | 0 | CycloneDX 1.6 generated. |
| Dependency audit | `pnpm security:deps` | 0 | No known findings reported; pip-audit skips two editable workspace packages. |
| Secret scan | `gitleaks dir . --redact --no-banner`; `gitleaks detect --redact --no-banner` | 0 | Worktree and one-commit history scans reported no leaks. |
| Handwritten source line cap | `find apps/dsh-plugin/src apps/dsh-plugin/test python/apps python/packages -type f \( -name '*.ts' -o -name '*.py' \) -print0 \| xargs -0 wc -l \| sort -nr \| head -20` | 0 | Maximum 494 lines (`apps/dsh-plugin/src/client.ts`). |
| Diff whitespace | `git diff --check` | 0 | No whitespace errors at the recorded run. |

**Current conclusion:** the local command gate and listed complementary checks passed. Product acceptance remains **PARTIAL**, not a production-ready verdict: official Plugin Manager upgrade and disposable-profile state-hash preservation are unverified; complete durable recovery and automatic restart recovery remain partial. The isolated Alembic round-trip proves migration reversibility in temporary SQLite only; no target database migration was applied. Plugin Manager install/enable/uninstall/reinstall evidence and its limits are in [`PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md`](./PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md).

The current recorded network smoke used the corrected Testnet endpoint and performed read-only public market-data checks. It did not use credentials, read account data, send orders, or skip checks. An earlier run of the same CLI command used `api.bybit.com` and is retained below as historical Mainnet public-market evidence; it is not the current network result. Mainnet trading remains disabled by default and requires separate explicit user authorization, and Testnet account/risk checks remain mandatory.

## OAuth support and authorization limits — read-only audit

The local CLI implements PKCE/state generation, authorization start, code exchange, token refresh, and explicit account selection. It has no OAuth revoke operation; local command capability does not establish that an OAuth flow completed successfully or that Bybit officially supports OAuth on Testnet. The official Bybit material reviewed lists separate API bases but does not confirm Testnet OAuth support. The README documents a manual flow; treat it as client guidance, not provider-support evidence.

Before any authorization attempt, the user must review the agent identity and requested scopes, then manually click Authorize. Revocation is not implemented by this CLI; the documented provider-side revocation path is deleting the AI subaccount. The initial read-only audit found no OAuth-specific tests; a subsequent scoped test increment added fake-backed local regressions (exit 0) as documented in [`BUILD_REPORT_BYBIT_OAUTH_TESTS.md`](./BUILD_REPORT_BYBIT_OAUTH_TESTS.md). Those tests make no provider request and do not verify a real authorization grant. Do not mark OAuth integration complete or Testnet OAuth officially confirmed until provider support, real consent/revocation lifecycle behavior, and the relevant test evidence are established.

## Network target correction

The earlier network command result was incorrectly characterized as compliant: the client used a fixed Mainnet public market endpoint. The target was then changed to run the client smoke with an explicit Testnet market endpoint, with a local endpoint-selection assertion. The external Testnet smoke was later run successfully; its current receipt is in the table above. The integration harness remains excluded because host runtime currently creates the standard live-market client.

Correction verification on 2026-11-17: `pnpm exec nx run @bybit-quant/dsh-plugin:build` (exit 0), `pnpm exec nx run @bybit-quant/dsh-plugin:lint` (exit 0), `pnpm exec nx run @bybit-quant/dsh-plugin:typecheck` (exit 0), `pnpm exec nx run @bybit-quant/dsh-plugin:test:unit` (exit 0, including no-network endpoint-selection assertion), `pnpm exec nx run @bybit-quant/dsh-plugin:bundle:check` (exit 0), and `git diff --check` (exit 0). The subsequent Testnet smoke is recorded above with exit 0 and 8 checks.

## Historical observations — earlier 2026-11-17 audit

The following records the earlier pre-fix audit, not the current status. The old audit found build/type/test and Python issues that were subsequently repaired. Its exact historical commands and observed exit codes are preserved below.

| Check | Historical command | Exit | Historical observation |
|---|---|---:|---|
| Build | `pnpm build` | 1 | `tsdown: command not found`. |
| TS typecheck | `pnpm typecheck` | 1 | Missing `react` and `tsdown` types and implicit-any diagnostics. |
| TS test typecheck | `pnpm typecheck:tests` | 1 | Missing build declarations and strict test-source errors. |
| TS unit tests | `pnpm test:unit` | 1 | Build output `dist/lib/signals.js` absent after build failure. |
| Python full tests | `uv run --project python --locked pytest python` | 1 | Migration fixture/config failure; quant-engine tests passed. |
| Python lint | `pnpm python:lint` | 1 | Ruff findings (`UP017` and import ordering). |
| Python typecheck | `pnpm python:typecheck` | 4 | Then-current root script pointed at absent `python/src`. |
| Nx public market network run | `pnpm exec nx run @bybit-quant/dsh-plugin:test:network --output-style=static` | 0 | Earlier target used `api.bybit.com`; 7 smoke and 27 integration checks passed. This historical Mainnet public-market read was read-only, without credentials/account access/orders, and is superseded by the corrected Testnet run in the current table. |
| Nx discovery | `pnpm exec nx show projects` | 0 | Discovered `quant-data`, `quant-engine`, and `@bybit-quant/dsh-plugin`. |
| Isolated Alembic up/down | `uv run --project python --locked python -` (stdin script used a temporary SQLite file and root Alembic config) | 0 | Migration round-trip worked without touching a durable project database. |
| SBOM structure | Python parsed existing TS/Python SBOM JSON | 0 | Both parsed as CycloneDX 1.6; this historical check did not regenerate repository SBOMs. |
| Backup/restore checks | Node strip-types temporary-directory smoke | 0 | Checksum restore and tamper rejection worked; this was not complete durable recovery evidence. |
| Runtime monitor smoke | Node strip-types inline smoke | 0 | In-memory counters only. |
| Docker sandbox smoke | `node --experimental-strip-types apps/dsh-plugin/test/sandbox.ts` | 0 | Limited isolation smoke; oversized output, timeout, and pinned image digest were not covered. |

## Open acceptance work

## Migration protection increment — 2026-11-17

| Check | Command | Exit | Evidence |
|---|---|---:|---|
| Quant-data migration/backup/concurrency/path regression | `uv run --project python --locked pytest python/packages/quant-data/tests/test_migrations.py -q` | 0 | 9 isolated temporary SQLite tests passed: fixture rows survive upgrade, backup checksum/integrity verified, non-empty downgrade rejected, failed revision leaves source unchanged, sidecars/WAL/active writers refused, source race detected before replacement, special-character path preserved |
| Quant-data lint | `uv run --project python --locked ruff check python/packages/quant-data` | 0 | no findings |
| Quant-data format | `uv run --project python --locked ruff format --check python/packages/quant-data` | 0 | all files formatted |
| Quant-data typecheck | `uv run --project python --locked pyright python/packages/quant-data/src` | 0 | 0 errors |
| Defined Verify Gate | `pnpm run verify` | 0 | build, lint, strict typecheck, unit tests and bundle check passed |
| Python workspace checks | `pnpm python:lint`; `pnpm python:typecheck`; `pnpm python:test` | 0 each | Ruff+format, Pyright, and 15 pytest tests passed |
| Diff whitespace | `git diff --check` | 0 | no whitespace errors |

The protected wrapper is SQLite-only and requires an explicit database path;
no durable project database or external service was migrated.

## Durable recovery increment — 2026-11-17

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| TS isolated backup/restore and tamper refusal | `pnpm build && pnpm --filter @bybit-quant/dsh-plugin exec node test/backup.ts && pnpm typecheck:tests` | 0 | Temporary state retained watchlist, paper trade, AI track and audit marker; modified backup was rejected by SHA-256 validation. |
| TS crash/restart rehearsal | Inline Node child writer, `SIGKILL`, then reopen `createStore` | 0 | Temporary JSON reopened with strategy/watchlist, paper trade and audit marker. This is not a service supervisor. |
| SQLite restore rehearsal | Inline `uv run --project python python - <<'PY'` fixture with temporary SQLite and `upgrade_sqlite` backup | 0 | Strategy config, trade and risk audit rows restored; `PRAGMA integrity_check=ok`; no target DB or credentials touched. |
| Full Verify Gate after test addition | `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test` | 0 | TS and Python checks passed; 15 pytest tests passed. |

`quant_engine.EngineRuntime` remains in-memory and has no durable checkpoint or process supervisor. Automatic restart, exchange reconciliation and production WebSocket durability remain unproven; no target database migration was applied.

The first SQLite rehearsal command exited 1 because an inline JSON literal was parsed by SQLAlchemy as a bind parameter; it mutated no project file or database. The rerun used explicit bound parameters and exited 0 as recorded above.

## Nx unit target coverage correction — 2026-11-17

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| Nx unit target with cache disabled | `pnpm exec nx run @bybit-quant/dsh-plugin:test:unit --skip-nx-cache --output-style=static` | 0 | Target output includes `node apps/dsh-plugin/test/backup.ts` and the backup restore/checksum tamper `PASS` line. |
| Defined root Verify Gate after target correction | `pnpm run verify` | 0 | Root build, lint, production typecheck, Nx unit target (including backup test), and bundle check passed. |
| TS test typecheck | `pnpm typecheck:tests` | 0 | Strict test-source typecheck passed. |
| Diff whitespace | `git diff --check` | 0 | No whitespace errors. |

The correction changes Nx target coverage only; backup implementation and trading safety behavior were not changed.

- Obtain a disposable Harness profile or official manager upgrade flow; verify upgrade and compare before/after state hashes without exposing credential contents.
- Complete durable state preservation and restart recovery tests, including graceful shutdown and reconciliation. Current full persistence/automatic recovery remains partial.
- Apply migrations only after the target database is identified and a traceable backup/rollback or restore plan is proven. No target migration has been applied.
- Keep generated SBOMs and audits within their stated coverage: pip-audit omits editable workspace packages.

## Sandbox bounded output increment — 2026-11-17

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| Nx unit target | `pnpm exec nx run @bybit-quant/dsh-plugin:test:unit --output-style=static` | 0 | Added `sandbox-output.ts`; 100 chunks of 2 MB retain only a fixed 400 KB stdout buffer, while multibyte stderr is byte-bounded. No Docker, network, Bybit or credentials used by this unit test. |
| TS test typecheck | `pnpm typecheck:tests` | 0 | Strict test-source typecheck passed. |
| Defined root Verify Gate | `pnpm run verify` | 0 | Build, lint, strict production typecheck, unit target including bounded-output regression, and Bundle check passed. |
| Diff whitespace | `git diff --check` | 0 | No whitespace errors. |

Sandbox stdout/stderr are now captured in fixed-capacity byte buffers sized to four times their existing character return limits, then sliced to the same 100,000/10,000 character limits. Excess child output is discarded while streams remain drained. This bounds retained host buffers; the existing Docker image tag remains tag-pinned rather than digest-pinned, so supply-chain pinning is still open.
