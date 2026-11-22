# BUILD REPORT: Native Bybit Testnet Execution

> Implementation report for the first authenticated Bybit Testnet execution slice.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | NATIVE_TESTNET_EXECUTION |
| **Date** | 2026-11-22 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **DESIGN** | `sdd/features/DESIGN_NATIVE_TESTNET_EXECUTION.md` |
| **Status** | Blocked — durable admission/dispatch foundation and offline verification recorded; exchange execution not implemented |

---

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 36, spanning data, execution, engine, OpenAPI, generated SDK, plugin, packaging and tests |
| Cross-file coupling | High; account identity, ledger, Nautilus runtime, reconciliation and UI boundaries must agree |
| Security surface | High; credentials, account binding, order identity, risk admission and Testnet/Mainnet isolation |
| LLM prompt items | Existing background-loop prompts remain simulation-only; this slice adds no prompt |
| Independent volume | Requires process lifecycle, reconciliation and external Testnet evidence |
| Context-rot risk | High for a 35-file transaction boundary; only the persistence foundation was safe to implement independently |
| Runtime capabilities | `default` continuation is available; no separate Build worker was authorized for this slice |

**Recommendation:** `default`, because the repository is writable and the work requires one accountable integrator, but stop before any exchange write until the pinned Nautilus API and secure account session are verified.

**User decision:** `default` continuation under the user's prior unattended-work authorization. No Mainnet authorization was inferred.

**Pre-build review:** Not available as a formal external review. Existing architecture and independent audit notes were used as read-only evidence.

---

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 11/36 manifest entries complete (persistence, local admission/claim, packaging, report and regression entries); items 6–7 are offline boundaries only; remaining execution path blocked |
| **Files Created** | 8 created files in this continuation: migration/store/ledger, account boundary, order mapper and regression tests |
| **Files Modified** | 12 existing files in this Build scope, including source, tests, lockfile, TS/Python SBOMs and audit receipts |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 20+ |
| **Verify Gate** | Blocked at product scope; local gates green |
| **Execution Mode** | default |

---

## Task Execution

The manifest now contains 36 entries. This Build implements an additive persistence and local admission foundation: schema models, migration 0007, a Testnet-Linear-only account-session and redacted reconciliation store, an explicit activation fence requiring the latest complete snapshot, durable native risk decisions/reservations with one-shot dispatch claims, an offline-only explicit Nautilus Testnet Linear config boundary, and the packaging edge that makes the typed mapper dependency discoverable. The ledger and config boundary perform no exchange IO. The Build still does not implement an exchange writer, Nautilus account/runtime, private event projector, execution API, or DSH execution capability. The Bybit HTTP provider remains GET-only and the paper runtime remains synthetic. Therefore the local foundation is verified, while the product-level Testnet execution gate remains blocked.

| # | Manifest IDs | Task group | Status | Evidence |
|---:|---|---|---|---|
| 1 | 1 | Durable account/session and execution projection models | Complete (foundation only) | Added account session, reconciliation snapshot, native event, reservation, admission decision and emergency state/event ORM models. The model layer still has no venue event projector. |
| 2 | 2 | Emergency and command states | Partial | Added the durable emergency state enum; legal command transitions and native submit/cancel/reduce-only/close states are not implemented. |
| 3 | 3 | Additive persistence migration | Complete | `0007_native_execution_state.py` creates seven tables and SQLite append-only triggers; downgrade refuses to drop populated tables. |
| 4 | 4, 34 | Atomic native intent/reservation/dispatch ledger | Complete (local ledger only) | Persists a generation/revision-bound risk decision and exposure reservation and grants one READY→DISPATCHING claim after revalidation. No exchange IO, independent risk evaluation, aggregate balance check or recovery projector is connected. |
| 5 | 5 | Account generation and reconciliation store | Complete (store only) | Adds Testnet Linear account binding, generation fencing, contiguous/idempotent evidence revisions, secret-key rejection, protected incomplete evidence and explicit activation requiring a complete, fresh snapshot; it does not fetch or reconcile venue reports. |
| 6–9 | 6–9 | Nautilus Bybit Testnet account, mapper, reconciliation and runtime | Partial / blocked | Items 6–7 now have offline boundaries: explicit Testnet + Linear config construction and a mapper that accepts only a READY, fingerprint-verified ledger record, exact Bybit catalog instrument and ledger-owned ClientOrderId. No live client, factory, private event projector or runtime exists; exact runtime behavior remains unverified in a disposable account. |
| 10–16 | 10–16 | Engine session, admission, emergency state and lifecycle | Blocked | A local quant-data admission/claim primitive exists, but it is not called by the engine; existing preflight remains read-only and returns `order_submission_allowed=false`. |
| 17–20 | 17–20 | OpenAPI and generated TypeScript client | Blocked | No execution contract was generated because the authoritative engine command surface is not implemented. |
| 21–24 | 21–24 | DSH AI bridge, trade boundary and readiness projection | Blocked | Dashboard/AI boundary is read-only and simulation-only; no engine execution capability is exposed. |
| 25–29 | 25–29 | Native, process, contract and DSH boundary tests | Blocked | Tests for the missing runtime cannot provide evidence until implementation exists. |
| 30 | 30 | This Build report | Complete | This report records actual implementation, verification and blockers. |
| 31 | 31 | Reconciliation store regression tests | Complete | Tests cover identity/config binding, generation fences, revision idempotency, incomplete evidence protection, forbidden credential keys, stale/future timestamps and emergency projection synchronization. |
| 32 | 32 | Migration preservation tests | Complete | Isolated SQLite migration tests assert the new tables, schema head, existing data preservation and backup behavior. |
| 33 | 33 | Ledger fixture migration-head update | Complete | Existing ledger fixture now expects migration head `0007_native_execution_state`; local native admission/claim cases now cover protected/incomplete, expiry, generation/revision drift, emergency fence, risk rejection, replay and concurrent claim. |
| 34 | 34 | Native admission/dispatch module | Complete (no venue IO) | Isolates native admission and claim rules from the general command-ledger implementation; uses the same durable database transaction and strict fail-closed checks. |
| 35 | 35 | Execution package dependency declaration | Complete | Declares the existing `bybit-quant-data` workspace dependency required by the typed mapper boundary. |
| 36 | 36 | Locked workspace dependency edge | Complete | `python/uv.lock` records the editable workspace edge; no external package or live capability was added. |

---

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `sdd/reports/BUILD_REPORT_NATIVE_TESTNET_EXECUTION.md` | Modify | 30 | Yes | Updated the existing blocked Build receipt with current implementation, verification and blockers. |
| `python/packages/quant-data/src/quant_data/models.py` | Modify | 1 | Yes | Added persistence projections for account sessions, reconciliation, native events, reservations and emergency state/history. |
| `python/packages/quant-data/src/quant_data/commands.py` | Modify | 2 | Yes | Added `EmergencyState`; command transition graph remains future work. |
| `python/packages/quant-data/src/quant_data/ledger.py` | Modify | 4 | Yes | Exposes the separate native admission/claim module through the existing ledger API. |
| `python/packages/quant-data/alembic/versions/0007_native_execution_state.py` | Create | 3 | Yes | Additive schema and SQLite append-only protections; downgrade refuses populated data. |
| `python/packages/quant-data/src/quant_data/reconciliation_store.py` | Create | 5 | Yes | Redacted evidence persistence, account-generation fence, freshness window and fail-closed incomplete/future-dated evidence. |
| `python/packages/quant-data/src/quant_data/native_ledger.py` | Create | 34 | Yes | Durable Testnet-only admission decision/reservation and revalidated one-shot dispatch claim; no venue IO; missing emergency projection fails closed. |
| `python/packages/quant-execution/src/quant_execution/bybit_account.py` | Create | 6 | Yes | Offline-only trusted profile binding and opaque credential handoff; constructs explicit `BybitEnvironment.TESTNET` + `BybitProductType.LINEAR` configs and never creates a client or submits an order. |
| `python/packages/quant-execution/src/quant_execution/bybit_order_mapper.py` | Create | 7 | Yes | Maps only a READY, fingerprint-verified ledger record to an exact Nautilus MarketOrder/LimitOrder; rejects non-Testnet, non-Bybit, symbol mismatch, invalid ledger IDs and any precision/step rounding. |
| `python/packages/quant-data/tests/test_reconciliation_store.py` | Create | 31 | Yes | Isolated persistence/reconciliation invariants, including stale/future evidence and emergency projection synchronization. |
| `python/packages/quant-execution/tests/test_bybit_account.py` | Create | 6 (supporting regression) | Yes | Five offline tests cover explicit environment/category, malformed binding/material rejection and fail-closed resolver behavior without exchange IO. |
| `python/packages/quant-execution/tests/test_bybit_order_mapper.py` | Create | 7 (supporting regression) | Yes | Ten offline tests cover market/limit mapping, stable identity, reduce-only, catalog binding, fingerprint/state/ID and precision rejection; no exchange IO. |
| `python/packages/quant-execution/pyproject.toml` | Modify | 7 dependency edge | Yes | Declares the existing `bybit-quant-data` workspace dependency required by the mapper's typed ledger boundary. |
| `python/uv.lock` | Modify | 7 dependency lock | Yes | Records the editable workspace dependency edge; no external package or live capability added. |
| `python/packages/quant-data/tests/test_migrations.py` | Modify | 32 | Yes | Migration head and preservation assertions. |
| `python/packages/quant-data/tests/test_command_ledger.py` | Modify | 33 | Yes | Ledger fixture expects the new migration head. |
| `sdd/features/DESIGN_NATIVE_TESTNET_EXECUTION.md` | Modify | Manifest | Yes | Manifest expanded to 36 entries to include persistence, regression and packaging dependency tasks; migration filename aligned with implementation. |
| `sbom.cdx.json` | Regenerate | Complementary | Yes | CycloneDX SBOM contains 200 npm components. |
| `sbom.python.cdx.json` | Regenerate | Complementary | Yes | Python CycloneDX SBOM regenerated after the workspace dependency edge changed. |
| `sdd/reports/ARCHITECTURE_IMPLEMENTATION_AUDIT_2026-11-19.md` | Modify | Audit | Yes | Updated the latest architecture-status handoff to match this Build receipt. |

## Migrations aplicadas

| Arquivo | Projeto (nome · ref) | Aplicada em | Prova por leitura |
|---|---|---|---|
| `python/packages/quant-data/alembic/versions/0007_native_execution_state.py` | Isolated SQLite fixtures · local temporary paths (no remote ref) | 2026-11-22 (pytest migration fixtures) | `alembic command.upgrade(..., "head")` reached `0007_native_execution_state`; migration preservation and downgrade-guard tests read `alembic_version` and all native tables. No shared or production database was changed. |

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | Manifest 4, 6–29 | The design assumes a verifiable Nautilus Bybit private execution session, but the current repository exposes only read-only Testnet preflight and synthetic paper execution. | Keep the product execution gate blocked; do not silently replace Nautilus with a direct REST writer. | Implemented durable admission/claim primitives and reconciliation activation in items 1–5/31–33 plus the offline config boundary in item 6; provider remains GET-only and AT-014/015/016/021/022 remain unproven. The activation call and config builder are internal trust boundaries, not exchange identity verifiers. |
| 2 | Manifest 21–24 | User-facing dashboard already follows the requested AI-decision boundary: chart filters only change displayed data, while dynamic candidates feed AI research. | No deviation. | Preserve read-only UI and simulation-only AI bridge until an independently accepted engine capability exists. |

---

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Focused native ledger regression | `uv run --project python --locked pytest python/packages/quant-data/tests/test_command_ledger.py -q` | Pass | 29 passed, exit 0; includes native admission/dispatch fencing, idempotency and missing-emergency fail-closed behavior. |
| Persistence/migration regression | `uv run --project python --locked pytest python/packages/quant-data/tests/test_reconciliation_store.py python/packages/quant-data/tests/test_migrations.py -q` | Pass | 24 passed, exit 0; uses isolated SQLite databases and stale/future timestamp cases. |
| Native combined regression | `uv run --project python --locked pytest python/packages/quant-data/tests/test_reconciliation_store.py python/packages/quant-data/tests/test_command_ledger.py -q` | Pass | 42 passed, exit 0. |
| Quant-data test package | `uv run --project python --locked pytest python/packages/quant-data/tests -q` | Pass | 70 passed, exit 0. |
| Quant-data typecheck | `uv run --project python --locked pyright` | Pass | 0 errors, warnings or informations, exit 0. |
| Targeted Ruff | `uv run --project python --locked ruff check python/packages/quant-data/src/quant_data/ledger.py python/packages/quant-data/src/quant_data/native_ledger.py python/packages/quant-data/src/quant_data/reconciliation_store.py python/packages/quant-data/tests/test_command_ledger.py python/packages/quant-data/tests/test_migrations.py` | Pass | All checks passed, exit 0. |
| Native account-config regression | `uv run --project python --locked pytest python/packages/quant-execution/tests/test_bybit_account.py -q` | Pass | 5 passed, exit 0; constructs only explicit Testnet Linear configs from fixture material and performs no exchange IO. |
| Native account-config lint/typecheck | `uv run --project python --locked ruff check python/packages/quant-execution/src/quant_execution/bybit_account.py python/packages/quant-execution/tests/test_bybit_account.py`; `uv run --project python --locked pyright python/packages/quant-execution/src/quant_execution/bybit_account.py python/packages/quant-execution/tests/test_bybit_account.py` | Pass | Ruff and Pyright exit 0 after import-sort correction; no diagnostics. |
| Native order-mapper regression | `uv run --project python --locked pytest python/packages/quant-execution/tests/test_bybit_order_mapper.py -q` | Pass | 10 passed, exit 0; READY/fingerprint/identity/catalog/precision mapping is offline-only. |
| Native order-mapper lint/typecheck | `uv run --project python --locked ruff check python/packages/quant-execution/src/quant_execution/bybit_order_mapper.py python/packages/quant-execution/tests/test_bybit_order_mapper.py`; `uv run --project python --locked pyright python/packages/quant-execution/src/quant_execution/bybit_order_mapper.py python/packages/quant-execution/tests/test_bybit_order_mapper.py` | Pass | Ruff and Pyright exit 0 with no diagnostics. |
| Full execution package suite | `uv run --project python --locked pytest python/packages/quant-execution/tests -q` | Pass | 109 passed, 10 existing Pandas warnings. |
| Full Python suite | `CI=1 NX_DAEMON=false pnpm run python:test` | Pass | 538 passed, 11 upstream/deprecation/simulation warnings, exit 0. |
| Python lint/format | `CI=1 NX_DAEMON=false pnpm run python:lint` | Pass | Ruff check passed; 118 files already formatted, exit 0. |
| Python typecheck | `CI=1 NX_DAEMON=false pnpm run python:typecheck` | Pass | Pyright reported 0 errors, warnings or informations, exit 0. |
| Root Verify Gate | `CI=1 NX_DAEMON=false pnpm run verify` | Pass for local scope | Nx build/lint/typecheck/unit/bundle/SDK/tooling checks passed, exit 0; not full product acceptance. |
| DSH plugin Verify Gate | `pnpm --dir apps/dsh-plugin run verify` | Pass | Build, lint, typechecks, unit tests and bundle checks passed, exit 0; 8 existing lint warnings remain. |
| SBOM | `pnpm run sbom` | Pass | Regenerated CycloneDX SBOM with 200 npm components, exit 0. |
| Dependency scan | `pnpm run security:deps` | Pass | `pnpm audit` found no known vulnerabilities; `pip-audit` found no known vulnerabilities among non-editable distributions (editable project packages skipped), exit 0. |
| Secret scan | `gitleaks dir --no-banner --redact .` | Pass | Scanned approximately 40.03 MB; no leaks found, exit 0. |
| Whitespace | `git diff --check` | Pass | No whitespace errors, exit 0. |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test + external execution gate |
| **Command / Method** | `pnpm run verify`; Python lint/typecheck/test; separately authorized capped Testnet lifecycle smoke |
| **Exit / Result** | All listed local commands exit 0; external Testnet lifecycle not run; native execution path remains absent |
| **Status** | Blocked / Inconclusive at product scope |
| **Evidence** | DEFINE states the local command is only a plugin regression gate; AT-014/015/016/021/022 and the remaining execution manifest require engine, SDK, Nautilus, private reconciliation, process and external evidence. Admission/reservation/claim were exercised only against isolated SQLite; no remote database or exchange endpoint was accessed. |

### Manual UX Receipt

N/A. No new UI change was made in this Build slice. The existing UI audit records the view-only dashboard and dynamic-candidate behavior.

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | `pnpm run python:lint` | Pass | Ruff check and format check exit 0. |
| Typecheck | `pnpm run python:typecheck` | Pass | Pyright exit 0 with no diagnostics. |
| Tests | `CI=1 NX_DAEMON=false pnpm run python:test` | Pass | 538 passed, 11 warnings. |
| Build / Compile | `CI=1 NX_DAEMON=false pnpm run verify`; `pnpm --dir apps/dsh-plugin run verify` | Pass for local scope | TypeScript/plugin and SDK checks exit 0. |
| SBOM / dependency / secret | `pnpm run sbom`; `pnpm run security:deps`; `gitleaks dir --no-banner --redact .` | Pass | SBOM generated; no known dependency vulnerabilities or detected secrets. |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-014 | Authorized intent submits exclusively through Nautilus with persistent client order ID | Blocked | A deterministic client order ID and durable dispatch claim exist locally, but there is no native authenticated execution runtime or exchange submission. |
| AT-015 | Uncertain submission reconciles before retry | Blocked | No private order reconciliation projector exists. |
| AT-016 | Environment/account ledgers are isolated | Blocked | Mainnet remains disabled; Testnet write session is not implemented. |
| AT-021 | Independent deterministic risk veto cannot be bypassed | Blocked | Native admission persists a typed risk result and does not reserve rejected commands, but no independent risk evaluator, account-balance aggregation or engine caller is connected to dispatch. |
| AT-022 | Emergency stop freezes and reconciles cancellation | Blocked | No native cancel/reduce-only/close state machine exists. |
| AT-032 | Dashboard filters do not alter candidate universe or portfolio | Pass for existing UI scope | Existing UI audit and plugin regression tests cover the read-only boundary. |
| AT-033 | AI chooses eligible instruments/parameters or abstains | Pass for existing simulation scope | Dynamic candidate pool and AI-decision UI boundary are implemented and tested; no exchange write is implied. |
| AT-034 | Fresh paginated instrument/ticker discovery produces bounded candidates | Pass for existing research scope | Existing dynamic-candidate tests cover fresh/stale/empty behavior. |
| AT-035 | Discovery failure fails closed without static symbols | Pass for existing research scope | Existing selector/client tests cover stale and no-candidate paths. |
| AT-036 | Strategy evidence is research-only and cannot authorize exchange action | Pass for existing research scope | Existing strategy evidence contract tests cover explicit unavailable/invalid results. |

The remaining DEFINE acceptance tests are outside this execution slice or remain incomplete as documented by the architecture audit.

---

## Advisor Ledger

None — no formal external review was executed.

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Native Bybit private execution and exact Nautilus factory behavior were not safely verifiable in the current environment. | Kept the execution boundary disabled and recorded a blocked Build instead of introducing an unverified writer. | No Testnet or Mainnet order can be sent by the product. |
| 2 | Full unattended loop, private exchange reconciliation and restart recovery are not connected to the existing paper/provider paths. | Preserved simulation/read-only behavior and documented the missing integration. | Product remains PARTIAL; unattended exchange trading is not ready. |
| 3 | Pinned Nautilus config objects include credential fields in their own `repr`. | Added a redacted project wrapper representation and regression assertions; kept underlying config use limited to a future trusted factory. | Runtime/factory integration must demonstrate that credentials are never formatted, serialized or logged before any client can start. |

## Deviations from Design

None. The design explicitly describes a future Build and states that current Testnet writes remain disabled.

## Blockers

| Blocker | Required Action | Owner |
|---|---|---|
| No verified native Nautilus Bybit Testnet account/session | Extend the offline item-6 boundary into independently tested `BybitLiveDataClientFactory`/`BybitLiveExecClientFactory` construction and private-session lifecycle using a disposable Testnet account. | Future Build owner |
| No durable admission/order identity/reconciliation path | Implement manifest items 1–16 and prove uncertainty, idempotency and recovery tests. | Future Build owner |
| No generated execution contract or DSH engine capability | Implement and regenerate manifest items 17–24 after the engine boundary is accepted. | Future Build owner |
| No process/external Testnet evidence | Run manifest tests 25–29, then an explicitly capped and separately authorized Testnet smoke lifecycle. | Future Build owner / authorized operator |

---

## Final Status

### Overall: BLOCKED

- [ ] All File Manifest tasks completed (persistence foundation only; execution items remain blocked)
- [x] Incremental verification recorded
- [ ] Verify Gate green or manual-ux receipt positive for product scope
- [x] Complementary local checks pass
- [ ] Acceptance Tests verified
- [x] LLM prompt receipts complete for this slice (no new prompt)
- [x] Drift decisions recorded
- [x] Advisor findings disposed when applicable
- [ ] No unresolved blocker
- [x] No TODO/FIXME used as unfinished implementation

The current product status remains **PARTIAL**. This Build adds locally tested, generation-bound admission/reservation/claim foundations, not a usable exchange execution path. The risk result is supplied by an internal caller and does not itself prove funds, precision, instrument limits or aggregate exposure. The algorithm libraries named in the architecture book are not fully integrated as production live strategies; only an isolated local research subset is present. The DSH dashboard is aligned with the requested observation-only boundary, and the AI can choose dynamic candidates in simulation/research flows. Fully unattended Testnet trading, and any Mainnet trading, remain unavailable.

## 2026-11-22 offline order-mapper boundary

Manifest item 7 now has `quant_execution.bybit_order_mapper.map_testnet_order`.
It accepts a `CommandRecord` only after checking `READY` state and recomputing
the canonical command fingerprint. The mapper requires the exact Bybit venue
and symbol from the server-owned catalog, converts quantity and limit price
through the Nautilus `CryptoPerpetual` precision, step and min/max rules, and
rejects any value that would be rounded. It uses the ledger-owned
`native_client_order_id` and produces a native `MarketOrder` or `LimitOrder`
with explicit trader/strategy IDs, GTC and reduce-only fields. It does not
accept a UI symbol, caller venue ID, arbitrary client ID, credentials or
network handle, and it performs no exchange IO.

This is a pure mapping boundary, not proof of dispatch. The Nautilus live
factories, private stream, account permission/balance checks, reconciliation,
cancel/reduce/close state machine, engine admission and restart recovery remain
absent; Testnet and Mainnet orders were not sent.

Latest mapper receipts:

| Command | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest python/packages/quant-execution/tests/test_bybit_order_mapper.py -q` | 0 | 10 tests passed; all fixtures are local and offline. |
| `uv run --project python --locked ruff check python/packages/quant-execution/src/quant_execution/bybit_order_mapper.py python/packages/quant-execution/tests/test_bybit_order_mapper.py` | 0 | All checks passed. |
| `uv run --project python --locked pyright python/packages/quant-execution/src/quant_execution/bybit_order_mapper.py python/packages/quant-execution/tests/test_bybit_order_mapper.py` | 0 | 0 errors, warnings or informations. |
| `uv run --project python --locked pytest python/packages/quant-execution/tests -q` | 0 | 108 tests passed; 10 existing Pandas warnings. |
| `CI=1 NX_DAEMON=false pnpm run python:test` | 0 | 538 tests passed; 11 upstream/deprecation/simulation warnings. |

The package's `pyproject.toml` now declares its workspace dependency on
`bybit-quant-data`, and `python/uv.lock` records that edge. This is packaging
metadata only; it does not enable a live executor.

## 2026-11-22 offline Testnet account boundary

Manifest item 6 now has a narrow, credential-handle-only module at
`python/packages/quant-execution/src/quant_execution/bybit_account.py`.
`BybitAccountBinding` validates an opaque profile reference and expected UID /
subaccount facts; `resolve_testnet_credentials` accepts material only from a
host-owned resolver; and `build_testnet_linear_configs` constructs immutable
Nautilus data/execution config objects with `BybitEnvironment.TESTNET` and
`BybitProductType.LINEAR`. The module does not read ambient environment
variables, persist or print secrets, create live clients, open a network
connection or submit an order. Its returned wrapper has a redacted `repr` so
accidental logging of the pair does not expose credentials; callers must still
pass the underlying configs directly to a future trusted factory. The underlying
Nautilus config objects' own `repr` includes their credential fields, so they
must not be logged, formatted, or serialized; client creation and Nautilus
logging behavior have not been enabled or verified. The five tests in
`python/packages/quant-execution/tests/test_bybit_account.py` exercise these
invariants against fixture strings only.

This closes only the offline configuration part of item 6. It is not evidence
of trusted exchange identity, permissions, balance, precision, private events,
factory startup, reconciliation or order execution. The product-level gate
therefore remains **BLOCKED** and Mainnet remains disabled.

## 2026-11-22 account-config type-boundary correction and package verification

The first focused Pyright pass exposed that Nautilus 1.231.0 types the
`BybitEnvironment` and `BybitProductType` enums in
`nautilus_trader.core.nautilus_pyo3`, even though the adapter config module
re-exports them at runtime. The implementation and its tests now import the
typed public location; no behavior or credential boundary changed. A final
boundary hardening also makes non-string profile/UID inputs fail with the
module's stable `ValueError` instead of leaking an attribute error.

Latest receipts:

| Command | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest python/packages/quant-execution/tests/test_bybit_account.py -q` | 0 | 5 passed. |
| `uv run --project python --locked ruff check python/packages/quant-execution/src/quant_execution/bybit_account.py python/packages/quant-execution/tests/test_bybit_account.py` | 0 | All checks passed. |
| `uv run --project python --locked pyright python/packages/quant-execution/src/quant_execution/bybit_account.py python/packages/quant-execution/tests/test_bybit_account.py` | 0 | 0 errors, warnings or informations. |
| `CI=1 NX_DAEMON=false pnpm run python:test` | 0 | 528 passed, 11 upstream/deprecation/simulation warnings. |
| `CI=1 NX_DAEMON=false pnpm run python:lint` | 0 | Ruff passed; 116 files already formatted. |
| `CI=1 NX_DAEMON=false pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| `pnpm exec nx run quant-execution:build` | 0 | Python package build target succeeded. |
| `pnpm exec nx run quant-execution:test` | 0 | Package test target succeeded. |
| `pnpm exec nx run quant-execution:typecheck` | 0 | Package typecheck target succeeded. |
| `pnpm exec nx run quant-execution:lint` | 0 | Package lint target succeeded. |
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | Root TypeScript/Nx, DSH unit, Bundle/API, SDK and tooling Verify Gate passed after the account-config addition. |
| `gitleaks dir --no-banner --redact .` | 0 | Scanned approximately 40.53 MB; no leaks found. |
| `git diff --check` | 0 | No whitespace errors. |

## 2026-11-22 final local verification receipt

This latest full-workspace run supersedes the earlier 523/528-test counts in
the chronological receipts above. It exercised local code and isolated
fixtures only; it did not access Bybit or submit an order.

| Command | Exit | Result |
|---|---:|---|
| `pnpm --dir apps/dsh-plugin run verify` | 0 | Plugin build, lint, typecheck, unit tests and bundle checks passed; 8 pre-existing lint warnings remain. |
| `CI=1 NX_DAEMON=false pnpm run python:test` | 0 | 538 tests passed; 11 upstream/deprecation/simulation warnings. |
| `CI=1 NX_DAEMON=false pnpm run python:lint` | 0 | Ruff checks passed; 118 files already formatted. |
| `CI=1 NX_DAEMON=false pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | Nx/TypeScript/plugin/unit/Bundle/SDK/tooling checks passed for local scope. |
| `pnpm exec nx show projects` | 0 | Nx discovered 9 projects across the workspace. |
| `pnpm run sbom` | 0 | CycloneDX npm SBOM regenerated with 200 components. |
| `pnpm exec nx run quant-data:sbom` | 0 | Python SBOM target passed. |
| `pnpm run security:deps` | 0 | No known npm or pip vulnerabilities; editable workspace packages were skipped by pip-audit. |
| `gitleaks dir --no-banner --redact .` | 0 | Scanned approximately 41.10 MB; no leaks found. |
| `git diff --check` | 0 | No whitespace errors. |

This receipt does not change the product status. The UI remains observation-only
and the AI simulation path may choose from a fresh dynamic candidate pool, but
the engine does not invoke the native ledger, the Bybit provider remains
GET-only, private reconciliation/cancel/restart recovery are absent, and no
Testnet or Mainnet order was sent. The algorithm repositories named in the
architecture brief remain research references; only the local strategy subset
is implemented.
