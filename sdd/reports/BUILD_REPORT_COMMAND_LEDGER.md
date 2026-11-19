# BUILD REPORT: Durable command ledger prerequisite

## Metadata

| Attribute | Value |
|---|---|
| Feature | COMMAND_LEDGER |
| Date | 2026-11-17 |
| Author | command_ledger implementation agent |
| BRAINSTORM | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| DEFINE | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| DESIGN | `sdd/features/DESIGN_COMMAND_LEDGER.md`; parent `DESIGN_BYBIT_AI_QUANT.md` |
| Status | Implementation verified; independent review pending at report creation |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 7 logical entries plus design itself |
| Cross-file coupling | Contracts, ledger, schema, migration and tests |
| Security surface | Execution idempotency and append-only audit; no credentials/exchange IO |
| LLM prompt items | None in this slice |
| Independent volume | Parent assigned bounded quant-data implementation and separate reviewer |
| Context-rot risk | Explicit immutable design and bounded interfaces |
| Runtime capabilities | Existing Python venv and SQLAlchemy/Alembic, no installation |

Recommendation/decision: parent explicitly delegated this bounded implementation; sequential work within assigned paths. Pre-build review: design shared with parent and reviewer before implementation. Parent arranged independent post-build review (`ledger_independent_review`); acceptance receipt remains reviewer-owned.

## Summary

Seven manifest entries implemented. Four Python files created, two modified, design/report created. Local prerequisite tests green; full product Verify Gate, SBOM/security aggregation and release remain parent-owned. No install, commit, push, user database migration or exchange request performed.

## Task Execution

| Manifest | Task | Executor | Status | Evidence |
|---|---|---|---|---|
| 1 | Immutable secret-free command contracts/canonicalization | implementation agent | Complete | hostile numeric, scope identity and equivalent Decimal tests |
| 2 | Transactional ledger/CAS/recovery/audit | implementation agent | Complete | six independent Engine/session admission, dispatch and duplicate-observation races |
| 3–4 | ORM + Alembic0003 + SQLite append-only triggers | implementation agent | Complete | migrated temp schema, downgrade guard, UPDATE/DELETE/REPLACE refusal |
| 5–6 | Lifecycle/concurrency/backup/migration tests | implementation agent | Complete | 28 tests passed |
| 7 | Build report | implementation agent | Complete | real command receipts and explicit limitations below |

## Files Changed

| File | Action | Manifest |
|---|---|---|
| `python/packages/quant-data/src/quant_data/commands.py` | Create | 1 |
| `python/packages/quant-data/src/quant_data/ledger.py` | Create | 2 |
| `python/packages/quant-data/src/quant_data/models.py` | Modify | 3 |
| `python/packages/quant-data/alembic/versions/0003_command_ledger.py` | Create | 4 |
| `python/packages/quant-data/tests/test_command_ledger.py` | Create | 5 |
| `python/packages/quant-data/tests/test_migrations.py` | Modify | 6 |
| `sdd/reports/BUILD_REPORT_COMMAND_LEDGER.md` | Create | 7 |
| `sdd/features/DESIGN_COMMAND_LEDGER.md` | Create before code; refinements appended | Design |

## Migrations aplicadas

Only isolated pytest fixtures were migrated. Explicit verification root: `/private/tmp/bybit-command-ledger-20261117-verify-733c`. No default Alembic URL or user database was targeted.

| File | Project/name/reference | Applied | Read proof |
|---|---|---|---|
| `0003_command_ledger.py` | isolated pytest / `test_append_only_and_downgrade0/command-ledger-test.sqlite` under root above | 2026-11-17 test run | revision0003; command/event counts1/4; three immutable-audit triggers present |
| same | verified backup `command-ledger-test.sqlite.pre-migration-_uvxea1q.sqlite` and restored `command-ledger-restored-test.sqlite`, same fixture folder | test protected head->head backup and copy restore | revision0003 in all three; same record/native ID/events; command/event counts1/4 and all triggers preserved |

Other migration fixtures named `migration-test.sqlite`, `failed-migration.sqlite`, `locked.sqlite`, `raced.sqlite`, `initial.sqlite` and special-character path stay under the same pytest temp root. Source0001 legacy rows survive0003; failed upgrades preserve original bytes. Populated ledger downgrade refuses before dropping either ledger table. When ledger is empty,0003 can downgrade and the older0002 guard subsequently refuses legacy populated strategy/trade removal; test correctly expects revision0002 after that rejected multi-step downgrade.

## Drift Detected

The parent product's direct TypeScript execution path remains unresolved original drift; this ledger does not resolve it. Python quant-data work follows accepted Python data-plane ownership despite broad repository TypeScript wording. Parent explicitly authorized the bounded prerequisite and isolated test migrations. No API, full OMS, engine wiring or live capability is implied.

## Verification Results

### Incremental Verification

| Command | Exit/result |
|---|---|
| `uv run --project python --locked pytest python/packages/quant-data/tests -q` | 2; sandbox forbids uv cache temporary lock at `~/.cache/uv`; no dependency installation attempted |
| `python/.venv/bin/python -m pytest python/packages/quant-data/tests -q` first | 1; 21 passed/1 legacy downgrade head expectation failed; corrected expectation to0002 because empty0003 was legitimately removed before older guard rejects |
| `python/.venv/bin/ruff check python/packages/quant-data` initial | 1; imports/type-exception style; corrected with scoped Ruff fix/format |
| `python/.venv/bin/pyright python/packages/quant-data/src` initial | 1; implicit interpreter could not resolve dependencies plus Decimal exponent narrowing; used explicit existing venv and narrowed exponent |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src` next | 1; SQLAlchemy Result.rowcount typing; replaced with typed UPDATE RETURNING/scalar_one_or_none |
| `python/.venv/bin/python -m pytest python/packages/quant-data/tests -q --basetemp=/private/tmp/bybit-command-ledger-20261117-verify-733c` final | 0; **28 passed in0.44s** |
| `python/.venv/bin/ruff check python/packages/quant-data` final | 0; all checks passed |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src` final | 0;0 errors/warnings/informations |
| `git diff --check` | 0 |
| read-only SQLite receipt probe against named fixture DB/backup/restore | 0; revision/schema/triggers and1/4 counts confirmed |

### Verify Gate

| Attribute | Value |
|---|---|
| Kind | bounded local prerequisite test |
| Command | final pytest command above |
| Result/status | exit0, green for this slice |
| Product gate | parent owns `pnpm run verify`; not claimed by this report |
| Manual UX | N/A, no UI |

All new source files <=500 lines (largest ledger344 at first count; below500 after final formatting). No new dependencies or root configuration changes.

## Acceptance Test Verification

| Scenario | Evidence/status |
|---|---|
| Scoped same payload retry/reopen/native identity | Pass; same row/hash/native ID; cross-account/environment separate |
| Conflicting payload or event identity | Pass; LedgerConflict, no mutation |
| Concurrent separate SQLAlchemy sessions | Pass;6 threads with independent engines/factories, one admission row and one dispatch winner; duplicate observations append once |
| Atomic transition + event | Pass; injected audit INSERT trigger failure leaves record/version/events unchanged |
| Risk rejection audit | Pass; rejection code durable, dispatch denied |
| Partial/full/cancel and stale observations | Pass; monotonic cumulative fill, exact full quantity, stale cancel rejected, partial cancel preserved; late terminal fill raises reconciliation-required error |
| Unknown recovery | Pass; dispatching->reconciliation_required after reopen, no redispatch, repeat recovery no-op; external reconciliation may resolve filled |
| Append-only | Pass; UPDATE, DELETE and INSERT OR REPLACE rejected |
| Backup/restore and migration | Pass; restored prior ledger IDs/state/events intact; legacy rows preserved; populated downgrade protected |
| Mainnet/malformed/free-form payload | Pass; typed environment excludes Mainnet, numeric/identifier validation; no arbitrary payload field |

## Advisor Ledger

| Note | Severity | Decision/evidence |
|---|---|---|
| Parent: risk-ready does not confer indefinite risk approval | High | APPLIED; interface/design explicitly require future fresh validation/expiry/reservations |
| Parent/reviewer: terminal late fills cannot imply flat | High | APPLIED; explicit exception + documented reconciliation duty and regression |
| Reviewer: signed zero/extreme zero exponent | Medium | APPLIED; numeric positive limit price, canonical zero fast path, hostile fixtures |
| Reviewer: SQLite REPLACE bypasses delete triggers | Medium | APPLIED; before-insert uniqueness protection plus direct SQL regression |
| Reviewer: SQLAlchemy rowcount typing | Medium | APPLIED; RETURNING scalar result, pyright green |

Independent formal acceptance remains pending; parent must consume reviewer's receipt.

## Issues Encountered

uv's cache lock was outside writable roots. Used already installed project venv directly without altering dependencies. Initial pyright selected an unsuitable interpreter; explicit `--pythonpath` fixes resolution. Local test/style/type failures were corrected and final checks rerun. No unresolved scoped test failure.

## Deviations from Design

Public API and state design retained. Additional audit fault-injection and concurrency replay coverage strengthens specified invariants. No unplanned root/config/CI/install edits.

## Blockers

Independent acceptance and aggregate product gate remain outside implementation ownership. PostgreSQL DDL/concurrency and exchange/Nautilus integration are unverified. Existing venv verification is real; uv locked command itself remains blocked by cache permissions.

## Final Status

Implementation verified for bounded local SQLite command/idempotency/audit prerequisite. NOT complete product execution authority or release. Risk computation/expiry/reservations, transactional exchange outbox, Nautilus dispatch, live recovery/reconciliation, account positions/finality and late-fill trade accounting remain future gated work. No automatic resubmission path exists. Recovery requires dispatcher quiescence and cannot revoke an already claimed external action. Database owner can alter/drop triggers; audit is append-only under application/schema safeguards, not tamper-proof storage.


## Parent aggregate format correction

Parent reported full Python pytest **212 passed** and Pyright **0 errors**, with aggregate lint failing solely because `test_migrations.py` was not Ruff-formatted. These aggregate receipts are parent-reported, not independently rerun here.

Executed `python/.venv/bin/ruff format python/packages/quant-data/tests/test_migrations.py`: exit **0**, one file reformatted. Then `python/.venv/bin/ruff format --check python/packages/quant-data/tests/test_migrations.py`: exit **0**, one file already formatted. Only that owned test file received the requested format correction. Reviewer notified; aggregate gate rerun remains parent-owned.
