# Verify Gate Evidence — 2026-11-17

## Current DSH paper integration receipt — 2026-11-17 (local current tree)

This section records the latest local evidence after integrating the DSH
native-paper manifest items 19–25 around the frozen broker, Host, UI, SDK and
process E2E slices. These are actual command results for the current worktree;
they do not create a hosted CI receipt or upgrade the complete product beyond
its scoped acceptance.

| Check | Actual command / method | Exit / result | Evidence and limits |
|---|---|---:|---|
| Nx discovery | `pnpm exec nx show projects` | 0; 7 projects | All seven workspace projects are discoverable; discovery does not prove installed DSH behavior. |
| Root Verify | `pnpm run verify` | 0 | Build, lint, TypeScript typecheck, unit, Bundle, SDK and tooling checks passed. |
| TypeScript test types | `pnpm typecheck:tests` | 0 | Strict test-source typecheck passed. |
| Built Host → native-paper process | `pnpm exec nx run @bybit-quant/dsh-plugin:test:paper-process --skip-nx-cache` | 0; uncached | Real temporary Host→private broker→SDK→CLI→native process path; synthetic only, no exchange request/order. |
| Python lint / format | `pnpm python:lint` | 0 | Ruff and formatting checks passed. |
| Python typecheck | `pnpm python:typecheck` | 0 | Pyright passed with no diagnostics. |
| Python workspace tests | `pnpm python:test` | 0; 289 passed, 11 warnings | Warnings remain recorded; this is workspace evidence, not full original-product acceptance. |
| Dependency security | `pnpm run security:deps` | 0 | No known findings within the command's stated editable-workspace scope. |
| TypeScript SBOM | `pnpm run sbom` | 0 | SBOM generation passed for its documented scope; it is not a runtime or release receipt. |

The scoped integration report is
[`BUILD_REPORT_DSH_PAPER_INTEGRATION.md`](./BUILD_REPORT_DSH_PAPER_INTEGRATION.md).
Host and UI have scoped build reports and local tests, but no independent
post-build implementation review receipt yet. Official Plugin Manager
install/upgrade/uninstall in a disposable Harness profile, before/after state
preservation, and real authenticated browser owner/cross-origin/non-owner
interaction remain pending. The full original quant scope remains pending,
including Nautilus as sole exchange authority, native Testnet and TS write-path
cutover, complete recovery/reconciliation, strategies, AI, isolated research
and the remaining dashboard/control requirements.

No hosted CI result is inferred from these local commands. The earlier
documentation/governance CI `44091570414` remains a historical failure
(engine114 passed/1 failed on immediate descendant PID absence; later schema,
security and SBOM steps were skipped); it is not reclassified here. The earlier
published code CI `44089248505` remains a separate historical success.

## Documentation publication and CI regression — 2026-11-17

Documentation/governance commit `ed1aaa5511f2060a4ab0507e7e2e3292367259ff`
was pushed to the existing feature branch; `git ls-remote` verified the exact
SHA. Actual pre-push checks passed, including252 Python tests/11warnings in33.60s.
However, [CI44091570414](https://github.com/XueHua-s/dsh_bybit_plugin/actions/runs/44091570414)
**failed** in quant-engine:test:114 passed/1failed. The graceful SIGTERM process
test observed one descendant PID still present immediately after service exit.
The CI log does not identify that PID's role. Root TS checks and public Testnet
smoke succeeded; downstream schema/security/SBOM steps were skipped, not passed.
This is a current regression under investigation; earlier code CI success does
not override it. Log: `/private/tmp/bybit-paper-docs-ci-failed.log` (local receipt).
No merge, deployment, exchange order or user-database migration occurred.

### Scoped shutdown-observation correction (local verification)

`REVIEW_PAPER_SHUTDOWN_OBSERVATION_2026-11-17.md` independently ACCEPTS
the final234-line test source, SHA256
`eabc56743dac53e3569d81fa6ba6adec6c15734cd3e4051d0214cecb57ff1fab`.
Application behavior is unchanged. The unmodified eight-cycle probe reproduced
a tracker lingering1.438ms while the native worker was already reaped; it does
not identify the historical CI PID. Final tests require immediate native reaping
on SIGTERM, bounded tracker inactivity, identity-aware SIGKILL containment, and
deliberately pause/resume the tracker to reproduce exit ordering. Independent
review rejected the initial broad tracker matcher; the exact invocation matcher
and adversarial unknown-process/failure-cleanup probes now pass.

Final independent process4/native11 checks, Ruff/format/Pyright all exit0.
Parent `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` exits0
(`/private/tmp/bybit-shutdown-root-verify.log`); unchanged deterministic TS tasks
may use Nx cache and hook safety9 ran. Author's earlier repeated20 process cases
and engine116 suite preceded the final matcher refinement and remain attributed
to that snapshot in the Build report. Final repair commit/push/hosted CI are
pending; no failed or skipped hosted step above is reclassified as passed.

## Published continuous paper increment — 2026-11-17 (verified scoped / overall PARTIAL)

Code `b75d73cb677e4c7beef82c9182ef6c955568f455` was committed and pushed. Actual pre-commit/pre-push hooks passed (252 Python tests in33.54s during push); exact remote SHA verified. [CI44089248505](https://github.com/XueHua-s/dsh_bybit_plugin/actions/runs/44089248505) completed success for both jobs; parent inspected every step, including blocking root verification, four Python projects, native tests, both actual schemas, security/SBOM/history checks and the public Testnet smoke. No merge, deployment or exchange order occurred.

All local/scoped receipts below remain attributed to their inspected source. The later documentation/governance update incorporates the user's conditional Astra→GPT-6.1 Sol xhigh rule; it has a separate commit and CI. Full original platform acceptance remains PARTIAL.

| Check | Actual receipt / method | Exit / result | Limits |
|---|---|---|---|
| Native runtime delta | `REVIEW_PAPER_NATIVE_2026-11-17.md` | Scoped ACCEPT | 33 execution tests plus actual derivative wallet/net-realized/unrealized/equity/available checks; owner death removes child even with blocked native loop. Containment is not graceful SIGKILL recovery. |
| Optional admission/API | `REVIEW_PAPER_ADMISSION_2026-11-17.md` | Scoped ACCEPT | 15 combined tests and seven independent final expiry/economic/persistence/native-fault probes. |
| Authenticated generated SDK | `REVIEW_PAPER_SDK_2026-11-17.md` | Scoped ACCEPT | 21 tests; canonical separate paper schema, private bounded capability transport, no mutation retry. |
| True compiled SDK/process E2E | `PAPER_SDK_PROCESS_E2E_2026-11-17.md` | 0 | 31 allowlisted checks, actual built SDK→real CLI→risk/store→spawned Nautilus; stable IDs, fills/later command continuity, replay/conflict, SDK close, clean stop/reap/listener closure and protected restart; no capability output. |
| Exact runbook launcher | Independent extracted heredoc AST parse and locked-environment execution | 0 | No-submit native start/stop, only allowlisted synthetic_native_start_stop_ok output; protocol/temporary upgrade verified. External PID/listener checks remain separate E2E scope. |
| Data accounting / metadata | `REVIEW_ADMISSION_STORE_2026-11-17.md` | Scoped ACCEPT | 43 tests, real Alembic command.check produces no new operations; perpetual economics, backup and independent probes. |
| Parent root Verify | `pnpm run verify` | 0 | New SDK21 cases included; hooks9. |
| TS test types | `pnpm typecheck:tests` | 0 | Strict test-source types. |
| Python lint / format / types | `pnpm python:lint`; `pnpm python:typecheck` | 0 | Final59 formatted files, Pyright0 after the tiny metadata fix. |
| Handwritten source / whitespace | Parent audit; `git diff --check` | 0 | 125 handwritten files, maximum497, none>500; final metadata-fix diff0. |
| Full Python workspace | `pnpm python:test` | 0 | 252 passed,11 warnings,35.43s after economic/expiry/metadata fixes: service115/native33/risk61/data43. |
| Actual schema contracts | Parent uncached Nx composite OpenAPI target | 0 | Both actual market and separate paper contracts match. |
| Dependency scan | `pnpm run security:deps` | 0 | No known findings; four local editables skipped. Existing fsspec metadata mismatch unchanged. |
| Initial SBOM command | `pnpm sbom` | 2 | pnpm12 builtin required its own format argument; command-name collision, not application code failure. |
| Corrected TS SBOM | `pnpm run sbom` | 0 | 200 components. |
| Python SBOM | Parent existing quant-data SBOM target | 0 | 91 components; quant-execution records MIT AND LGPL-3.0-only expression. |
| Changed-file secrets | Parent isolated redacted gitleaks scan | 0 | 71 files/1,136,198 bytes; snapshot before latest report append, not a claim that future text was scanned. |
| Full history secrets | Parent redacted gitleaks history scan | 0 | 11 commits/about2.25MB. |
| Native license artifacts | Parent independent final wheel/sdist inspection | PASS | Exact bytes of four assets MIT/LGPL/GPL/NOTICE in each archive, adapted source and SPDX MIT AND LGPL-3.0-only expression verified. |
| Remote baseline | Parent fetch plus HEAD versus origin/main and origin/feature | 0 | Both ahead/behind0/0 at pre-publication inspection; actual publication is recorded above. |

Initial actual SDK E2E used an incorrect root `.venv` path (127, no test), then
sandbox socket creation failed (1); approved loopback rerun0 is the passing
receipt. Native/service reviews retain the earlier spot-notional accounting,
raw-free-margin, expiry-protection and orphan-cleanup findings and corrections.
No pre-fix economic acceptance is implied. Native net realized includes fees;
durable gross realized minus cumulative fees reconciles it. Public paper status
does not expose wallet/equity; E2E claims no such wire field.

Default market app stays two read-only paths. Optional separate paper app uses
only server-configured finite synthetic BTC LIMITs and inherited private pipeFD;
actual protocol/temporary database recipe is in `docs/runbooks/paper-service.md`.
No exchange connection/orders/trades, target DB migration, DSH mutation cutover
or full original-platform acceptance. Mandatory authenticated DSH controls,
native Testnet plus TS exchange-write cutover, full replay/reconciliation,
strategies/AI/generated-code/isolated research remain incomplete. LGPL adapted
source and companion GPLv3 base terms accompany mixed-license package artifacts;
root MIT does not relicense the adapted source or original MIT files.

## Published risk / command ledger increment — 2026-11-17 (verified scoped, overall PARTIAL)

Code `411de43f07984f8d2af163c6e95abd53c3d98dc9`
(`feat: add deterministic risk and durable command ledger`) was committed and
pushed. Actual pre-commit0 and pre-push0 (213 tests in6.88s), push0, and exact
`git ls-remote` SHA match were verified by parent. [Hosted CI44081030699](https://github.com/XueHua-s/dsh_bybit_plugin/actions/runs/44081030699)
completed **success** for that exact code SHA; `gh run watch` exited0 and parent
inspected all jobs and steps: blocking verify, four Python projects, risk wheel,
schema, dependency/SBOM/history scans all passed; nonblocking public Testnet job
also succeeded. PR1 remains draft; no merge, deployment or order is claimed.

Earlier published baseline566092a/CI44077034140 is historical. This four-file
documentation follow-up is separate and is **not covered** by code411de43's CI;
parent will commit/push it after checks and watch its exact-SHA CI. Older local
receipts below retain their exact source/count scope.

| Check | Command / method | Exit | Evidence / limits |
|---|---|---:|---|
| Root aggregate | Parent `pnpm run verify` | 0 | `/private/tmp/bybit-risk-root-verify.log`; TS Nx cache hits included, nine hook fixtures fresh. Python semantics are evidenced separately below. |
| Strict TS test types | Parent `pnpm typecheck:tests` | 0 | `/private/tmp/bybit-risk-root-testtypes.log`. |
| Independent command ledger review | `sdd/reviews/REVIEW_COMMAND_LEDGER_2026-11-17.md` | ACCEPT | Scoped: 28 unit tests plus independent 15×8 dispatch races, crash/audit/migration/restore probes; no exchange or account transaction acceptance. |
| Independent risk review | `sdd/reviews/REVIEW_QUANT_RISK_2026-11-17.md` | ACCEPT | 61 tests, including four properties; 501 independent adversarial assertions. Decimal discovery, full-price-envelope slippage and lower-envelope SELL minimum-notional findings corrected. Final seed-only follow-up independently verified61 tests0 in0.19s/Ruff0/Pyright0: four seed20261117/databaseNone decorators preserve property assertions, test file455lines; current hashes and Build report checked in review, ACCEPT unchanged. |
| Final parent Python workspace | `pnpm python:lint`; `pnpm python:typecheck`; `pnpm python:test` | 0 each | Ruff/format36 files, Pyright0; 213 passed in6.83s, ten existing Nautilus/Pandas warnings. Seed-only follow-up is tracked separately. |
| OpenAPI drift | Parent uncached Nx engine OpenAPI target | 0 | Existing read-only schema matches; no command route added. |
| Actual workspace integration | Commands in `BUILD_REPORT_RISK_WORKSPACE.md`: locked sync/import, `pnpm exec nx graph --file=/private/tmp/bybit-risk-workspace-graph.json`, risk CI targets and wheel build | 0 | Seven real nodes; actual existing edges retained, no invented engine→risk edge. Fresh risk lint/typecheck/test61 and wheel build passed. |
| Nx discovery | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx show projects --json` | 0 | Seven independent projects: risk/data/engine/execution and three TS projects. |
| Dependency audit | `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache pnpm run security:deps` | 0 | pnpm audit/pip-audit report no known vulnerabilities; four local editable Python packages skipped. |
| Declared metadata compatibility | `uv pip check --python python/.venv/bin/python` | 1 | Sole known incompatibility: Nautilus1.231.0 requires fsspec2026.2.0, explicit security override installs2026.6.0; no metadata-compatible install claim. |
| TS SBOM | `pnpm run sbom` | 0 | 200 components, JSON count confirmed by parent. |
| Python SBOM | `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx run quant-data:sbom` | 0 | 91 components, JSON count confirmed by parent. |
| Changed-file secrets | Parent isolated redacted gitleaks scan | 0 | 34 files /833069 bytes; parent will rescan final docs before commit. |
| Repository history secrets | Parent redacted history gitleaks scan | 0 | Nine commits /about1.98MB. |
| Handwritten source cap | Parent source audit | 0 | 101 files, maximum497 lines, none>500. |
| Remote baseline | Parent fetch and ahead/behind checks | 0 | HEAD versus origin/main and origin/feature both0/0 at inspection; recheck before publication if baseline moves. |
| Diff whitespace | Parent `git diff --check` | 0 | Rerun after final documentation/seed edits. |

**Retained failures and superseded counts:** initial Python lint exited1 on
`test_migrations.py` formatting; author corrected that file and the final
aggregate36-file check passed. Intermediate Python212/typecheck0 preceded the
final SELL minimum-notional correction; Python213 above supersedes that source
receipt. Risk review originally withheld acceptance for malformed Decimal field
discovery and unsafe price envelopes; corrected regressions/reviewer probes now
pass. uv metadata failure remains unresolved explicitly, not counted as green.

The risk package is a pure deterministic veto foundation; the data package adds
local durable commands/audit. Final account locks, atomic risk reservations,
sole Nautilus submission, TS REST cutover, long-lived paper/private state,
uncertain-order reconciliation and full strategy/AI/research remain incomplete.
`DESIGN_EXECUTION_CUTOVER.md` is a future integration contract, not runtime
acceptance. Only disposable SQLite test databases are in scope; target DB is not
migrated. Engine HTTP remains two read-only routes. Mainnet is untested; no
exchange order or private account access is authorized by these fixtures.

## Historical published code and hosted CI receipt — 2026-11-17

Code commit `4360381c86df468c1eb35a04c9eb880d515cb514` was committed and pushed; root verified an exact `git ls-remote` SHA match. [Draft PR #1](https://github.com/XueHua-s/dsh_bybit_plugin/pull/1) has `isDraft=true`; no main merge or production deployment is claimed.

[GitHub Actions run44076026205](https://github.com/XueHua-s/dsh_bybit_plugin/actions/runs/44076026205) completed **success** for that exact head. `gh run watch` exited0 and detailed `gh run view` verified actual executed steps, not just overall status:

- Blocking verify job134014150086: success, every step success, including root verification, Python/native checks, generated schema and security/SBOM.
- Nonblocking public Testnet job134014149576: success.
- Actual repository pre-commit and pre-push hooks ran successfully (exit0) during the code commit/push; this supersedes earlier installation/execution uncertainty.

This receipt covers the exact code commit4360381. The following documentation-only update is a separate delta; do not attribute that earlier CI result to a future documentation commit. Full original platform MUSTs and remaining installed Harness/UI/auth/upgrade gates stay incomplete.

## Current SDK/DSH/native/hooks rerun — 2026-11-17 (final integrated receipts)

Committed/pushed baseline `f535981` precedes this new increment. Old green security/111-test results below belong to that earlier snapshot. SDK, DSH, native execution and hooks have independent scoped ACCEPT reviews; this is not a complete original-product PASS.

| Check | Actual command / method | Exit | Current evidence / limits |
|---|---|---:|---|
| Initial aggregate | Root `pnpm run verify` | 1 | SDK Nx build invoked nested pnpm shim and failed ENOEXEC. Targets changed to direct installed tsc/node/oxlint/Vitest; never count this failure as pass. |
| Corrected SDK scoped gate | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx run-many -t build,typecheck,test,lint,generate:check --projects=@bybit-quant/quant-api-client --skip-nx-cache` | 0 | Five tasks passed fresh; 9 Vitest cases. Aggregate later passed as recorded below. |
| Second aggregate | Root corrected `pnpm run verify` | 1 | Child pnpm pack hit the same ENOEXEC. Shared sanitized pnpm environment helper added; real Nx bundle check passes afterward. |
| Final aggregate after correction | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache pnpm run verify && NX_DAEMON=false NX_ISOLATE_PLUGINS=false UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache pnpm typecheck:tests && NX_DAEMON=false NX_ISOLATE_PLUGINS=false UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache pnpm exec nx show projects` | 0 | Fresh unit/pack/schema/SDK Vitest/tooling tasks ran; some build/type tasks cached. Six real projects include SDK/native. |
| Python workspace | `pnpm python:lint`; `pnpm python:typecheck`; `pnpm python:test`; OpenAPI export `--check`; `git diff --check` | 0 | Ruff/format27 files; Pyright0 errors; 133 passed in6.67s including22 native/catalog cases, ten upstream Pandas deprecation warnings. Schema/diff match. Initial132/21 is historical. |
| Real React19 SSR | `node apps/dsh-plugin/test/render.ts` | 0 | Real renderer, no skip; server render cannot prove browser effects/fetch/visual interaction. |
| Hook fixture suite | `node scripts/test-git-hooks.ts` | 0 | Nine isolated fixtures, sensitive-path/partial staging/scanner redaction and monorepo failure guards. Subsequent actual pre-commit/pre-push execution during commit/push exits0, recorded below. |
| Native execution | `uv run --project python --locked pytest python/packages/quant-execution/tests -q` | 0 | Final22 native BacktestEngine/catalog tests, no live/Testnet executor or exchange request. |
| Initial dependency audit | Root dependency scan | 1 | fsspec 2026.2.0 vulnerability, fixed 2026.6.0, while Nautilus exact-pins vulnerable version. |
| Patched environment scan | Explicit root uv fsspec 2026.6.0 override; pip-audit | 0 | Independent native re-review confirmed 22 native / 133 full and catalog compatibility; limited tested API scope, no blanket compatibility. |
| Declared metadata compatibility | `uv pip check`; standalone pip resolution | 1 | Nautilus exact pin conflicts with patched override; use root uv workspace, no metadata-compatible/standalone install claim. |
| Final dependency audit | `pnpm run security:deps` | 0 | No known TS/Python vulnerabilities; pip-audit skips three editable workspace packages. Patched override and metadata incompatibility remain explicit. |
| Final SBOM generation | `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache uv run --project python --locked cyclonedx-py environment --output-reproducible --output-file sbom.python.cdx.json && pnpm run sbom` | 0 | Python89 / TS200 components; recursive workspace SDK/runtime edges retained. |
| Changed-file secrets | Root isolated `gitleaks dir` scan | 0 | 68 changed files,913521 bytes, no leaks. |
| Repository history secrets | Root `gitleaks git` full-history scan | 0 | Seven commits, about1.59MB, no leaks. |
| Source line cap | Root handwritten-source audit, generated artifacts excluded | 0 | 92 files, maximum497 lines, none>500. |
| Root SDK/DSH real-service smoke | Bounded separate-process probe: built DSH engine facade → generated SDK → actual FastAPI public Testnet ETHUSDT service | 0 | health200/market200, partial=true, executionReady=false. Client close returns closed; independent server remains alive. Ordered SIGTERM/lifespan shutdown, listener closed; child -15 expected Uvicorn signal re-raise. No credentials/private account/order calls. |

Final root aggregate, six-project discovery, Python/schema, dependency scan, SBOMs, secret/line/diff and SDK real-service smoke passed. Declared Nautilus/fsspec metadata mismatch remains an explicitly tested security override, not fully compatible package metadata. Code commit/push, exact remote SHA and actual hosted CI success are recorded above; earlier static-only CI status is superseded for that commit. The subsequent documentation delta has its own diff check, not that earlier CI coverage. Full original MUSTs, sole exchange execution authority, complete risk/OMS/portfolio/AI/research, official upgrade preservation/auth and browser UI remain unaccepted.

## Historical integrated-service rerun — 2026-11-17

Root integration receipts after supervisor/transport/service review fixes. The accepted slice reports are `sdd/reviews/REVIEW_ENGINE_SUPERVISOR_2026-11-17.md`, `REVIEW_ENGINE_TRANSPORT_2026-11-17.md` and `REVIEW_ENGINE_SERVICE_2026-11-17.md`. Prior counts and command outcomes below describe earlier source snapshots, not current totals.

| Check | Actual command / method | Exit | Current evidence and limits |
|---|---|---:|---|
| Root TS gate + test types | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify && NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm typecheck:tests` | 0 | Build/lint/strict types/unit/Bundle and test-source checks passed. Run with approved escalation because mock OAuth callback requires loopback binding; no provider OAuth request. |
| Python workspace lint/format | `pnpm python:lint` | 0 | Ruff passed; 21 files formatted. |
| Python workspace typecheck | `pnpm python:typecheck` | 0 | 0 errors after explicit non-None task assertions in supervisor tests. |
| Python workspace tests | `pnpm python:test` | 0 | 111 passed in 5.70s. Fixtures use temporary state and fake sockets; no orders. |
| OpenAPI drift | `uv run --project python --locked quant-engine-openapi --output contracts/openapi/quant-engine.v1.json --check` | 0 | Deterministic Python-generated schema matches. Export does not start ingestion. |
| TS/Python SBOM | `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache uv run --project python --locked cyclonedx-py environment --output-reproducible --output-file sbom.python.cdx.json && pnpm run sbom` | 0 | CycloneDX component counts: TS 241, Python 78. |
| Dependency scan | `pnpm run security:deps` | 0 | No known vulnerabilities; two editable Python workspace packages skipped. |
| Live public Testnet process smoke | Bounded Python subprocess probe launching `quant-engine --symbols ETHUSDT` on ephemeral loopback; read health; send one SIGTERM; capture logs and verify listener closes | 0 (probe) | HTTP 200, `ready=true`, Testnet connected; execution unknown. Ordered `Shutting down` → `Waiting for application shutdown` → `Application shutdown complete` → `Finished server process`; listener closed. Child return -15 is uvicorn 0.54.0 intentionally re-raising SIGTERM **after** lifespan shutdown, not a standalone success/failure signal. No credentials/private API/orders. |
| Changed-file secret scan | Root temporary-directory `gitleaks` scan of 36 changed files (about 797 KB); latest-commit `gitleaks git --log-opts=-1` | 0 | No leaks reported in the scoped worktree scan or latest commit; not a claim of full remote-history scan. |
| Source line cap | Root audit of 74 handwritten sources | 0 | Maximum 494 lines; no source exceeds 500. |
| Remote baseline | Root `git fetch` and ahead/behind inspection | 0 | 0/0 at inspection; inspect again if baseline changes before push. |
| Whitespace | `git diff --check` | 0 | No whitespace errors at integrated-source verification; rerun after final documentation integration. |

**Failures and environment limits retained:** the initial default Nx socket/daemon attempt hung and was cancelled (130). Daemon-disabled sandbox verification exited 1 when the fake OAuth loopback callback could not bind; the approved escalated rerun above passed. The first Python chain exited 1 at Pyright because two new supervisor-test `Task | None` values needed explicit non-None assertions (lines 306/344 at that snapshot); implementation owner fixed test narrowing and the full chain passed. A child agent's logged-smoke approval attempt encountered transient HTTP403 quota infrastructure failure; root's subsequent reviewed and approved probe executed successfully as recorded above. The earlier root live probe had health 200 but no captured shutdown logs and alone did not prove ordered shutdown. No code or safety check was bypassed.

**Acceptance remains PARTIAL.** Live public ingestion and clean process shutdown are now observed, with three independent scoped ACCEPT reviews. Generated TS SDK/DSH service integration, authenticated remote control, full snapshot reconstruction/persistence, OS process restart and complete order/account recovery are not accepted. Required Nautilus sole execution authority remains missing; the direct TS REST order path is open original-scope drift. Full strategy/portfolio/risk/AI/research MUSTs, official upgrade/state preservation and real OAuth remain incomplete or unverified. No target database migration or real order occurred. See `ORIGINAL_SCOPE_AUDIT_2026-11-17.md` and restored DEFINE AT-010–031; local gate success is not full product completion.

## Historical post-OAuth rerun — 2026-11-17

This table is the earlier post-OAuth snapshot. The integrated-service table above is the current command status; older commands/counts below remain historical receipts.

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

**Conclusion at that snapshot:** the local command gate and listed complementary checks passed. Product acceptance remains **PARTIAL**, not a production-ready verdict: official Plugin Manager upgrade and disposable-profile state-hash preservation are unverified; complete durable recovery and automatic restart recovery remain partial. The isolated Alembic round-trip proves migration reversibility in temporary SQLite only; no target database migration was applied. Plugin Manager install/enable/uninstall/reinstall evidence and its limits are in [`PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md`](./PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md).

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
| Python workspace checks | `pnpm python:lint`; `pnpm python:typecheck`; `pnpm python:test` | 0 each | Historical pre-checkpoint run: Ruff+format, Pyright, and 15 pytest tests passed |
| Diff whitespace | `git diff --check` | 0 | no whitespace errors |

The protected wrapper is SQLite-only and requires an explicit database path;
no durable project database or external service was migrated.

## Durable recovery increment — 2026-11-17

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| TS isolated backup/restore and tamper refusal | `pnpm build && pnpm --filter @bybit-quant/dsh-plugin exec node test/backup.ts && pnpm typecheck:tests` | 0 | Temporary state retained watchlist, paper trade, AI track and audit marker; modified backup was rejected by SHA-256 validation. |
| TS crash/restart rehearsal | Inline Node child writer, `SIGKILL`, then reopen `createStore` | 0 | Temporary JSON reopened with strategy/watchlist, paper trade and audit marker. This is not a service supervisor. |
| SQLite restore rehearsal | Inline `uv run --project python python - <<'PY'` fixture with temporary SQLite and `upgrade_sqlite` backup | 0 | Strategy config, trade and risk audit rows restored; `PRAGMA integrity_check=ok`; no target DB or credentials touched. |
| Full Verify Gate after test addition | `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test` | 0 | Historical pre-checkpoint run: TS and Python checks passed; 15 pytest tests passed. |

`quant_engine.EngineRuntime` now supports a bounded versioned checkpoint of reconnect count on graceful stop. Queue depth and timestamps are process-local: restart sets queue depth to zero, creates a fresh `started_at`, and clears `stopped_at`. Legacy v1 checkpoints validate historical queue/timestamp fields but ignore their values, retaining only reconnect continuity. This is not a process supervisor, order-state recovery, exchange reconciliation or production WebSocket durability; no target database migration was applied.

## Runtime checkpoint follow-up — 2026-11-17

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| Root Verify Gate | `pnpm run verify` | 0 | Nx build/lint/typecheck, unit target and bundle check passed; unchanged TS tasks were served from cache. |
| Python lint and formatting | `pnpm python:lint` | 0 | Ruff checks passed; 13 Python files already formatted. |
| Python typecheck | `pnpm python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| Python workspace tests | `pnpm python:test` | 0 | 21 tests passed, including eight runtime checkpoint cases. |
| Diff whitespace | `git diff --check` | 0 | No whitespace errors at checkpoint implementation verification. |

Checkpoint v2 persists only reconnect count. Startup initializes backlog depth to zero and creates fresh lifecycle timestamps; legacy v1 queue depth and timestamps are validated then ignored. Tests use temporary paths only. This local verification does not establish a managed service lifecycle, crash-consistent order recovery, exchange reconciliation or production WebSocket recovery.

### Checkpoint timestamp-contract review correction — 2026-11-17

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| Focused runtime checkpoint suite | `uv run --project python --locked pytest python/apps/quant-engine/tests/test_runtime.py -q` | 0 | 8 passed; tests assert v2 stores only reconnects, restart sets a fresh `started_at` and `stopped_at=None`, and v1 timestamps/queue are validated then ignored. |
| Defined root Verify Gate, TS test types and diff check | `pnpm run verify && pnpm typecheck:tests && git diff --check` | 0 | Build/lint/typecheck/unit/bundle checks passed; Nx build/lint/typecheck were cache hits, unit and bundle tasks ran. |
| Workspace Python lint/format | `pnpm python:lint` | 0 | Ruff passed; 13 files formatted. |
| Workspace Python typecheck | `pnpm python:typecheck` | 0 | Pyright: 0 errors, warnings or information messages. |
| Workspace Python tests | `pnpm python:test` | 0 | 21 passed. |

At this historical checkpoint snapshot, only the reconnect counter survived process restart and the service supervisor was absent. The later integrated service/supervisor above supersedes that absence claim; order-state recovery and exchange reconciliation remain missing.

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

## Prompt trust boundary increment — 2026-11-17

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| Fresh plugin build | `pnpm exec nx run @bybit-quant/dsh-plugin:build --skip-nx-cache --output-style=static` | 0 | Rebuilt trust boundary and Host tools from source. |
| Fresh unit target | `pnpm exec nx run @bybit-quant/dsh-plugin:test:unit --skip-nx-cache --output-style=static` | 0 | Includes `trust.ts`; injection-like prose remains an untrusted envelope and risk output is unchanged when only prose changes. |
| Test typecheck | `pnpm typecheck:tests` | 0 | Strict test-source typecheck passed. |
| Diff whitespace | `git diff --check` | 0 | No whitespace errors at the time of this increment. |

The runtime now uses a typed, bounded provenance envelope for agent-provided decision prose. The helper does not claim to detect every prompt injection; code-owned action fields and risk checks remain authoritative, while the envelope communicates that prose is data only. No external news/GitHub connector, credentials, network request, or order path was used by this increment.

### Full verification after trust-boundary lint correction

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| Defined root Verify Gate | `pnpm run verify` | 0 | Fresh build, lint, strict production typecheck, Nx unit target (including trust test), and Bundle check. |
| TS test typecheck | `pnpm typecheck:tests` | 0 | Strict test-source typecheck passed. |
| Python lint/format | `pnpm python:lint` | 0 | Ruff and formatting check passed; 13 files already formatted. |
| Python typecheck | `pnpm python:typecheck` | 0 | Pyright reported 0 errors, warnings, or information diagnostics. |
| Python tests | `pnpm python:test` | 0 | 15 tests passed. |
| Diff whitespace | `git diff --check` | 0 | No whitespace errors. |

The first full Verify attempt exited 1 because oxlint rejected a control-character regex in `trust.ts` (`no-control-regex`). The implementation was changed to code-point checks and the complete command sequence above then passed.

`apps/dsh-plugin/test/integration.ts` also asserts the `quant_decide` and `quant_review` envelope fields. `pnpm typecheck:tests` covers that source; the integration suite itself is network-backed and was not run in this local-only gate.

## In-process supervisor increment — 2026-11-17

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| Supervisor focused tests | `uv run --project python --locked pytest python/apps/quant-engine/tests/test_supervisor.py -q` | 0 | 3 fake-only tests passed; no network, secrets or orders. |
| Supervisor Ruff | `uv run --project python --locked ruff check python/apps/quant-engine/src/quant_engine/supervisor.py python/apps/quant-engine/tests/test_supervisor.py` | 0 | No findings. |
| Quant-engine Pyright | `uv run --project python --locked pyright python/apps/quant-engine/src` | 0 | 0 diagnostics. |

The supervisor is an in-process async worker boundary with finite restart budget and graceful close. This evidence does not establish OS process supervision, hung-worker detection, order recovery, exchange reconciliation, or live trading readiness. An initial async-test command exited 1 because `pytest-asyncio` is not installed; tests use `asyncio.run` and the recorded rerun passed.

## Supervisor lifecycle hardening — 2026-11-17

| Check | Command | Exit | Evidence / limits |
|---|---|---:|---|
| Supervisor regression suite | `uv run --project python --locked pytest python/apps/quant-engine/tests/test_supervisor.py -q` | 0 | 5 fake-only tests cover bounded restart cleanup, cancellation-safe close/restart race, unexpected factory failure, and configuration validation. |
| Python workspace gate | `pnpm python:lint`; `pnpm python:typecheck`; `pnpm python:test` | 0 each | Ruff/format, Pyright, and 26 tests passed. |
| Root TS Verify Gate | `pnpm run verify` | 0 | Build, lint, typecheck, unit, and bundle checks passed. |
| TS test typecheck | `pnpm typecheck:tests` | 0 | Strict test-source typecheck passed. |
| Diff whitespace | `git diff --check` | 0 | No whitespace errors. |

Review fixes make cleanup cancellation-safe and convert unexpected restart exceptions to terminal failure. This still does not establish process supervision, hung-worker detection, order recovery, exchange reconciliation, or production trading readiness.
