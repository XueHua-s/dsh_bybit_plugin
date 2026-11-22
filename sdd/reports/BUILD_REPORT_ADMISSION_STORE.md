# BUILD REPORT: Transactional Internal Paper Admission Store

## Metadata

| Attribute | Value |
|---|---|
| Feature | ADMISSION_STORE |
| Date | 2026-11-17 |
| Author | admission_store / SDD Build |
| BRAINSTORM | sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md |
| DEFINE | sdd/features/DEFINE_BYBIT_AI_QUANT.md |
| DESIGN | sdd/features/DESIGN_EXECUTION_CUTOVER.md; sdd/features/DESIGN_ADMISSION_STORE.md |
| Status | In Progress — scoped implementation verified; parent integration and final Verify Gate pending |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 13 scoped files including design/report; expanded manifest documented before additions |
| Cross-file coupling | High: existing ledger transaction invariants, migration, projections and immutable provenance |
| Security surface | Account ownership, admission CAS, trusted decision evidence; no external execution/credentials |
| LLM prompt items | None for this slice; product research prompts remain incomplete |
| Independent volume | Data authority delegated explicitly by parent; separate independent reviewer |
| Context-rot risk | Frozen facade published to integration agent before dependent implementation |
| Runtime capabilities | Parent-coordinated delegated build; no additional agents spawned |

Recommendation: one data authority implements transaction logic; independent review probes invariants.
User decision: inherited authorized parent implementation scope; no additional permission sought.
Pre-build review: parent-owned independent ledger review; findings applied below.

## Summary

| Metric | Value |
|---|---|
| Tasks Completed | 5/5 scoped implementation tasks; final integration review pending |
| Files Created | 8 (six Python files, scoped design, scoped report) |
| Files Modified | 5 |
| Files Deleted | 0 |
| Verify Gate | Parent-owned `pnpm run verify` not run by this subtask |
| Execution Mode | Explicitly delegated data authority |

## Task Execution

| # | Task | Executor | Status | Verification |
|---:|---|---|---|---|
| 1 | Publish scoped design/manifest/facade | admission_store | Complete | Integration agent acknowledged API |
| 2 | Freeze0004 additive schema and append-only protection | admission_store | Complete | Migration preservation/downgrade/backup tests |
| 3 | Atomic decision, reservation, ledger and fresh dispatch | admission_store | Complete | CAS concurrency, rollback and stale-owner tests |
| 4 | Native identity, evidence, cumulative paper projections | admission_store | Complete | Partial cancellation, late reports, conflict and precision tests |
| 5 | Package migrations and validate package | admission_store | Complete | 40 pytest tests; ruff; explicit-interpreter pyright |

## Files Changed

| File under python/packages/quant-data | Action | Verified | Notes |
|---|---|---|---|
| src/quant_data/admission_contracts.py | Create | Yes | Frozen DTOs, stable evaluator-reason allowlist, nanosecond timestamps |
| src/quant_data/admission_models.py | Create | Yes | Session, risk decision, reservation, position, native/protection evidence |
| src/quant_data/admission_store.py | Create | Yes | SQLite serialized transactions; ownership/context checks; scoped reads |
| src/quant_data/admission_events.py | Create | Yes | Immutable dedupe evidence and conservative projections |
| alembic/versions/0004_admission_state.py | Create | Yes | Frozen additive DDL; no live ORM imports |
| tests/test_admission_store.py | Create | Yes | Twelve actual database contract tests |
| src/quant_data/ledger.py | Modify | Yes | Extract shared transaction-local transition invariant; public APIs unchanged |
| src/quant_data/migrations.py | Modify | Yes | Resolve migration resources inside installed wheel |
| pyproject.toml | Modify | Yes | Include Alembic tree/config in wheel; no dependency changes |
| tests/test_command_ledger.py | Modify | Yes | Advance exact head revision expectation only |
| tests/test_migrations.py | Modify | Yes | Advance exact schema/head expectations only |
| sdd/features/DESIGN_ADMISSION_STORE.md (repository root) | Create | Yes | Scoped design and manifested refinements |
| sdd/reports/BUILD_REPORT_ADMISSION_STORE.md (repository root) | Create | Yes | This evidence record |

## Migrations aplicadas

| Arquivo | Projeto (nome · ref) | Aplicada em | Prova por leitura |
|---|---|---|---|
|0004_admission_state.py | pytest isolated tmp SQLite fixture only | 2026-11-17, actual pytest Alembic invocation | Scoped tests query native/protection evidence and positions; existing tests require0004 exact revision;0003 command survives upgrade unchanged |

No operator/default database was opened or migrated. Protected backup/restore tests use named pytest tmp databases only. Workspace integration independently reported a freshly extracted wheel migrated an initialized temporary SQLite file to0004 with11tables and retained backup.

## Drift Detected

| # | Drift | Decision | Action |
|---:|---|---|---|
| 1 | Prior design omitted transaction-local ledger reuse detail | Refine scoped design | Existing transition invariants extracted, never duplicated |
| 2 | Scoped reads needed account/session authorization | Apply reviewer requirement | All admission reads require session and owner; request lookup scoped |
| 3 | Coarse risk code alone lost evaluator veto provenance | Apply reviewer requirement | Immutable allowlisted detailed reasons persisted |
| 4 | Historical migration imported live models | Apply reviewer requirement | Freeze migration DDL |
| 5 | Migration files missing from installed wheel | Refine packaging manifest | Package resources and runtime resolver without dependency changes |

## Verification Results

### Incremental Verification

| Command / Method | Exit | Result |
|---|---:|---|
| `python/.venv/bin/python -m compileall -q python/packages/quant-data` | 0 | Compile complete |
| Initial package pytest before updating head expectations | 1 | Existing head/schema assertions expected0003; updated manifested assertions for0004 |
| `python/.venv/bin/pytest -q python/packages/quant-data/tests` | 0 | 40 passed in0.93s final scoped run |
| `python/.venv/bin/ruff check python/packages/quant-data` | 0 | All checks passed |
| `python/.venv/bin/ruff format --check python/packages/quant-data` | 0 |18files already formatted |
| Initial pyright without interpreter selection | 1 | Missing imports due tool resolver environment; no installed dependency change |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src` | 0 | 0errors/0warnings |
| `git diff --check` | 0 | No whitespace error |

### Verify Gate

| Attribute | Value |
|---|---|
| Kind | test |
| Command | pnpm run verify |
| Exit / Result | Not run by this scoped subtask |
| Status | Pending parent integration |
| Evidence | Package checks do not certify complete product acceptance |

### Manual UX Receipt

N/A. No user-facing workflow authored here.

### Complementary Checks

Package tests/lint/format/typecheck all passed. No install, commit, push, root dependency/lock or CI modification performed by this subtask.

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-006 | Complete new data state backup/restore | Scoped pass | Snapshot, decisions, positions, reservations, native/protection evidence preserved |
| AT-012/015 | Uncertain/out-of-order/late native evidence | Scoped pass | Protection committed; previous projection retained; no blind retry |
| AT-014 | Stable native ID before dispatch | Scoped pass | Atomic command identity + ready reservation; single durable dispatch claim |
| AT-016 | Explicit paper session/environment boundary | Scoped pass | Internal paper only; scope mismatch denies lookup/mutation |
| AT-021/029 | Risk and event provenance | Scoped pass | Immutable fingerprints, reasons, native event identity; append-only DB guards |

Native execution, full live OMS, strategy/research/replay and complete original product acceptance remain parent/future work, never implied by these data tests.

## Advisor Ledger

| # | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|
| 1 | Unscoped reads permit cross-account lookup | High | APPLIED | Scoped reads and denial tests |
| 2 | Fresh caller generation does not refresh older decision | High | APPLIED | Claim requires original context generation plus its own admission; later reservation invalidates claim |
| 3 | Append-only native identity loses conflicting attempted report | Medium | APPLIED | Deterministic derived conflict identity retains structured attempted facts |
| 4 | Mutable protection reason loses history | Medium | APPLIED | Append-only protection events; initial reason preserved |
| 5 | Ambient Decimal precision silently rounds1e30-1 | High | APPLIED | Private100digit context; exact high-range and hostile2digit/traps regression |

Independent reviewer reported broad probes green and precision probe green after fixes; final review receipt remains parent-owned.

## Issues Encountered

Zero-byte touched SQLite file protected upgrade trips existing sidecar safety check because its source lock creates a journal. Integration agent informed to initialize an actual SQLite header (`PRAGMA user_version=0`, close) before protected migration; extracted-wheel verification of initialized file passed. This slice does not weaken journal guards.

## Deviations from Design

Scoped manifest refinements recorded before code: packaging, scoped request lookup, audit-only native event append, protection history, detailed reasons. No trading environment expansion.

## Blockers

Parent integration/full Verify Gate and final independent review pending. Data package checks green.

## Final Status

Overall: IN PROGRESS — scoped data implementation verified, integration acceptance pending.

- [x] Scoped File Manifest implemented
- [x] Incremental verification recorded
- [ ] Parent Verify Gate receipt
- [x] Package complementary checks pass
- [x] Scoped acceptance evidence only
- [x] No runtime LLM prompt added
- [x] Drift recorded
- [x] Advisor findings applied
- [ ] Parent final acceptance
- [x] No TODO/FIXME substitutes for requirements

## Parent accounting integration correction and re-verification

Parent identified material drift after the first scoped review: actual native fixture is a margin CryptoPerpetual, while the generic initial projection used spot notional cash debits. Opening exposure falsely appeared as drawdown. Corrected scoped design before code; original scoped acceptance is historical and changed accounting requires new independent review.

Explicit persisted `AccountingModel` now distinguishes existing spot semantics from `linear_perpetual`. Real native fixture creation must pass LINEAR_PERPETUAL and include model in synthetic configuration fingerprint. Reopen checks model and fingerprint; no existing data silently converts. Linear perpetual wallet changes only by realized PnL and native fees, with durable signed quantity/average entry basis. Adds weight entry prices; partial/full closes and reversals realize actual closed exposure PnL; new reverse residual opens at fill price. Cumulative native fill notionals remain audit provenance. Engine compares marked durable equity against native authoritative equity; full opening notional is never loss. Only linear quote-currency perpetual fixture is supported; native instrument mismatches must protect/reject.

All changes remain in the premanifested contracts/models/events/store/frozen0004/tests files; no extra module introduced. Frozen0004 has only been exercised on disposable fixtures, never operator data.

Final accounting-specific verification executed:

| Command | Exit | Evidence |
|---|---:|---|
| `python/.venv/bin/pytest -q python/packages/quant-data/tests` | 0 |42passed in0.94s |
| `python/.venv/bin/ruff check python/packages/quant-data` | 0 |All checks passed |
| `python/.venv/bin/ruff format python/packages/quant-data` | 0 |Formatted actual modified file;17already unchanged |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src` | 0 |0errors/0warnings |

New regressions prove opening200notional with1commission leaves9999wallet from10000, mark99 for2units gives9997equity (actual2unrealized+1fee loss); add/partialclose/reversal/shortclose preserve `wallet=initial+realizedPnL-fees`; partial cancellation retains entry basis and position, releasing only unfilled reservation; backup/restore retains explicit model and complete derivative projection; reopening with mismatched spot model rejects. Parent-requested independent re-review pending at this report update.

Metadata discovery follow-up within documented manifest: Alembic env.py explicitly registers separated admission models, so future metadata comparison sees new tables without application import order.0004 still uses frozen DDL. Scoped file totals become14 (8created,6modified). Native portfolio realized_pnl was independently confirmed NETfees; durable realized_pnl is GROSS and must compare native net against durable gross minus cumulative_fee. Engine author informed.

## Parent metadata consistency follow-up

Independent Alembic schema comparison exposed preexisting ORM metadata drift, now corrected after scoped manifest update:0001 already creates an unnamed `UniqueConstraint(strategy_id,version)` and `ix_trade_events_created_at`; ORM had attached a new unique name and omitted that existing index. `models.py` now describes the actual published schema, preserving identical uniqueness and index semantics. No migration/user schema/data change was needed or performed.

Added `test_current_head_metadata_matches_published_migrations`: upgrade isolated tmp database to head, run actual `alembic.command.check`, then reflect/assert existing unnamed uniqueness and created_at index. Real command now reports no new upgrade operations. Scoped totals become15files (8created,7modified).

Verification after alignment: `python/.venv/bin/pytest -q python/packages/quant-data/tests` exit0,43passed in0.95s; `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src` exit0,0errors/0warnings; Ruff check/format exit0. Independent reviewer informed to refresh full scoped acceptance/fingerprints. Previously recorded40/42test receipts remain historical;43is current data package count.
