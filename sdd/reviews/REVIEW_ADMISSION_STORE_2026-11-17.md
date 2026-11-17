# Independent review: transactional paper admission store

Date: 2026-11-17. Reviewer: `ledger_independent_review`, independent from implementation owner `admission_store`. Baseline supplied by parent: `605fe70`; current working-tree implementation reviewed. Reviewer wrote only this receipt and `/tmp` adversarial probes, never production/test implementation.

**Current verdict: ACCEPT for the bounded SQLite admission-store extension, including the explicit linear-perpetual accounting correction reviewed in the final addendum below.** No unresolved blocking finding remains in the reviewed data slice. Earlier sections retain the initial generic spot-context evidence and historical fingerprints; the final addendum is authoritative for the changed accounting files. This is not full product, native service integration, exchange execution, risk evaluator, release or autonomous recovery acceptance.

## Sources and boundary

Read AGENTS.md, software-design-philosophy and SDD instructions already loaded for this review, DESIGN_EXECUTION_CUTOVER.md, DESIGN_ADMISSION_STORE.md, BUILD_REPORT_ADMISSION_STORE.md, current contracts/models/store/event projection code, migration0004 and shared ledger transition extraction. The parent requires independent engine/native reviews and full Verify Gate separately.

Only isolated SQLite databases in reviewer-created temporary directories and pytest temporary fixtures were used. No user's database, credentials, account, network, install, root dependency lock, commit or push was accessed or modified. Process-crash probes use local SQLite only; engine lifetime process-lock enforcement is outside this data receipt.

## Findings and disposition

| Finding | Severity | Disposition/evidence |
|---|---|---|
| Unscoped snapshot/get/decision lookups could not enforce forbidden cross-session/account reads. | High | APPLIED: all store reads now require session+owner; cross-session command lookup and observation denied independently. |
| Coarse RiskCode omitted detailed allowlisted evaluator veto provenance required by cutover design. | Medium | APPLIED: immutable reasons tuple persisted and reconstructed; hostile reason rejected by package tests. |
| Latest caller generation could dispatch an older persisted risk plan after a later reservation changed context. | High | APPLIED: dispatch requires persisted decision.context_generation+1 equals current, plus caller generation/owner/expiry; independent A-then-B admission probe denies A even with latest supplied generation. |
| Migration0004 imported live ORM tables, permitting historical schema drift on future model edits. | Medium | APPLIED: migration now contains frozen DDL, no live model imports. |
| Mutable protection reason could erase earlier protection/restart evidence. | Medium | APPLIED: initial reason preserved; immutable protection events retain subsequent reasons, including reopen. Raw SQL evidence attacks denied. |
| Changed duplicate native report needed attempted facts retained alongside original immutable identity. | Medium | APPLIED: deterministic conflict identity retains structured attempted report; independent cross-command UUID collision protects session without altering original or projections. |
| Accepted numeric range silently rounded cash/projections using ambient Decimal precision28. | High | APPLIED: private precision100 arithmetic context. Independent original reproducer failed: starting balance1e30 minus buy notional1 remained1e30. Same reproducer now returns exactly999999999999999999999999999999. Precision2+Inexact-trap probe also preserves all18 fractional places. |

No production fix was authored by reviewer. Findings were sent directly to author and parent before final acceptance.

## Executed command receipts

All commands ran from `/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant`.

| Real command | Exit | Observation |
|---|---:|---|
| `python/.venv/bin/python /tmp/admission_review_probe.py` | 0 | Broad independent probe passed before arithmetic finding; repeated after fix also passed. |
| `python/.venv/bin/python /tmp/admission_precision_probe.py` before fix | 1 | Reproduced silent rounding:1e30-1 stored as1e30. |
| `python/.venv/bin/python /tmp/admission_precision_probe.py` after fix | 0 | Exact expected balance persisted. |
| `python/.venv/bin/python /tmp/admission_identity_migration_probe.py` | 0 | Protected0003->0004 preservation, full native UUID collision/audit-only events, hostile ambient precision/trap all passed. |
| `python/.venv/bin/python -m pytest python/packages/quant-data/tests -q` preliminary | 0 |38 passed before final regression additions. |
| `python/.venv/bin/python -m pytest python/packages/quant-data/tests -q` final | 0 |**40 passed in1.08s**. |
| `python/.venv/bin/ruff check python/packages/quant-data && python/.venv/bin/ruff format --check python/packages/quant-data && python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src` final | 0 |All lint checks passed;18files formatted;0 type errors/warnings. |
| `git diff --check -- python/packages/quant-data` | 0 |No whitespace errors. |
| `wc -l python/packages/quant-data/src/quant_data/*.py python/packages/quant-data/alembic/versions/0004_admission_state.py` | 0 |Admission store346, events185, contracts137, models76, migration59, ledger357; all reviewed handwritten sources <=500lines. |
| `shasum -a 256` on seven core/reviewed files below | 0 |Fingerprint receipt below. |

The existing Python venv was used; this subtask did not run dependency resolution/install or claim a fresh locked environment. Prior ledger review recorded uv cache sandbox denial; no new permission escalation was attempted.

## Independent adversarial evidence

### Atomic admission and concurrency

Injected temporary SQLite trigger failure on reservation INSERT after command and decision construction. Entire database rows, session generation, command/ready audit, risk decision and reservation matched pre-call snapshot after rollback. Separate injection at dispatch audit INSERT also rolled back state/version/generation. Temporary triggers existed only in reviewer fixtures.

Eight rounds of six threads used separate Engines/Session factories against each temporary shared SQLite database, synchronized before deciding different requests from generation0. Exactly one command/decision/reservation won per round; other stale plans were denied. Six concurrent identical requests reused one durable command/native ID, despite original generation becoming stale. Changed same-key payload raised LedgerConflict.

### Ownership, scope and stale decisions

Wrong-owner snapshot denied. Session B owner could not get Session A command/decisions or observe its native report. A second session could not silently reuse account alias. Open-session config/account binding and stale-owner protection are covered in package tests. Admitting A then B invalidated A's dispatch even when caller supplied newest generation; caller stale generation also denied. Reopening preserved projections/reservations and rotated owner; old owner lost access and new owner could not admit exposure while protected.

### Native identity, partial exposure and uncertainty

Native cumulative partial0.5/notional50/fee1 from balance1000 produced cash949, signed position0.5 and residual reservation1.5 for quantity2. Identical event replay changed no table row or generation. Cancel with the same partial totals released only pending remainder, retained position0.5/cash949. A later full-fill report did not silently overwrite terminal state or infer flat: protected session, original projection retained, structured attempted report persisted with applied0.

Conflicting same event payload and out-of-order reports persisted attempted facts with protection and no double accounting. A full UUID native ID reused by a different command protected the session and retained original plus conflicting identity evidence. Audit-only OrderPendingCancel did not advance ledger lifecycle or release reservations; same audit replay was idempotent. Scoped get_by_request returned original identity.

High-range and low-ambient-context probes now preserve exact cash, signed position and residual quantities. Private arithmetic context prevented precision2 and Inexact-trap caller settings from altering18-place projections.

### Append-only protection, restart and recovery limits

For each of admission_decisions, paper_native_events and paper_protection_events, raw SQL UPDATE, DELETE and INSERT OR REPLACE were refused; exact table snapshot remained unchanged. Repeated protect kept initial reason while appending further protection reasons.

A separate child process committed admission/reservation and dispatch, then exited via os._exit(17). Parent reopened with a new owner and a much larger supplied starting balance. Session remained protected, persisted balance1000 and pending reservation survived unchanged, durable command stayed dispatching, and claim returned false. No automatic resubmission or fresh balance/session reset occurred. Durable uncertainty is established; native matching-engine reconstruction is not claimed.

### Migration, downgrade and backup restore

Created0003 with a populated old command, deterministic native ID, risk rejection and audit. Protected upgrade_sqlite explicitly migrated that temporary database to0004; legacy command/events remained byte-for-value equal. Retained backup still read revision0003 with old command row. No default Alembic target was used.

For populated0004 containing command/decision/projection/native/protection facts, downgrade to0003 refused and all rows remained unchanged. Existing protected backup followed by isolated copy restore preserved every table row, including native IDs, reservations, immutable reasons/evidence and revision. This is verified backup restoration during stopped local fixtures, not a new restore tool or live recovery claim.

## Complexity assessment

**10/10 within the reviewed data boundary; all eight diagnostic rows pass.** AdmissionStore owns transaction serialization, scope and generation; native projection module owns accounting/evidence; contracts own validation/canonical data; migration is historical frozen schema. Shared transaction-local ledger transition helper avoids duplicating lifecycle knowledge. Interface comments make native IO/process-lock and risk-authorization boundaries explicit. No failed diagnostic row requires a scoped change. This score does not certify overall engine/Host architecture.

## Reviewed SHA256 fingerprints

- admission_contracts.py: `0e7e3f1efe10e1ab0a149383383a9a98b626ed7daf26607144716d4a1cb457a4`
- admission_store.py: `fadec2db9a5dbe41b4d2c10f17a280ad04c7ddd1b1697a34d437b4192579bb5d`
- admission_events.py: `e7fb34622c014891b353ea53083ad73cbfcf9d5487ea212696fe35ebbd2e6842`
- admission_models.py: `08ea8453aa1cd30d41fb3fdd8a1fff20adeba92007a701f1bcf438ec1c5bff3f`
- ledger.py: `cf51015d3ef14c01fd220ce0734837324a4ed631018d8b3252b38a8c42d2da8f`
-0004_admission_state.py: `014ebc56227bab7efd5b4211a2cd01d79e61b5e11a8b5cb58ad0ecdbbee4cef7`
- test_admission_store.py: `9228ae7f327ff7cdaaf1b17ecf47c829ad95f95b0e6a8efd45598a84ff9ec084`

## Residual limits and parent ownership

Store accepts trusted server-computed risk decisions and normalized native observations; it does not implement account authorization, risk evaluation, actual process lifetime account locking, native thread supervision or exchange IO fencing. Database owner/generation is not a fence for an already running external call. Multi-host, PostgreSQL, power-loss durability, native matching-engine replay, full trade/position reconciliation and exchange execution remain unverified/unimplemented here. Protected sessions cannot resume through an automatic reset/unprotect API.

An engine reviewer reported initial migration sidecar fixture failures while this work evolved. Data author identified the existing zero-byte SQLite source edge and coordinated initialized/closed SQLite setup with engine owner. This receipt independently validates protected migration on populated initialized0003 and head->head fixtures; successful engine/native startup is the separate integration reviewer's responsibility, not inferred here. Installed-wheel migration resource proof was reported by workspace author but not independently repeated by this reviewer.

The parent owns full pnpm Verify Gate, SBOM/dependency/secret scan, independent engine/native receipts, release/handoff and original MUST acceptance. No product trading approval follows from this data acceptance.

## Accounting drift re-review: final authoritative addendum

Parent reopened this scope after identifying that the actual native CryptoPerpetual MARGIN session cannot use generic spot cash economics. Initial acceptance did not validate that coupling and was historical only while this correction was pending. Read the pre-code accounting drift section of DESIGN_ADMISSION_STORE, changed contracts/store/model/projection/schema, new economic tests, env.py metadata discovery change and author's report append.

**Updated scoped verdict: ACCEPT.** Explicit SPOT retains generic cash behavior; native integration must select LINEAR_PERPETUAL. Perpetual balance now represents collateral wallet; notional opens exposure, and only gross realized PnL and actual native fees change wallet. Signed position average entry, gross realized PnL and cumulative fees are durable. This is local store accounting acceptance; authoritative native wallet/equity/free-margin comparison and engine risk-context comparison remain separately reviewed integration duties.

### Independent economic probe

`/tmp/admission_perpetual_review_probe.py` uses a freshly migrated temporary SQLite database, explicitly selected LINEAR_PERPETUAL and hostile caller Decimal precision2 with Inexact trap enabled. No native/exchange connection or user's database was used.

- Initial wallet1000; BUY3 was filled in two reports:1 at90, then cumulative3/notional330. Wallet999.7 reflects only0.3 fees, quantity3 and weighted entry110. Exact native report replay changed no database row.
- SELL2 at130 closed two units, retained entry110 for the residual unit, gross realized40, cumulative fees0.5 and wallet1039.5.
- SELL3 at100 realized a10 loss on the remaining long unit and opened a two-unit short at100. Gross realized30, fees0.8, wallet1029.2.
- BUY0.5 at80 realized a10 short profit; BUY1.5 at110 realized a15 short loss, flattened quantity and reset average entry to0. Final gross realized25, fees1, wallet1024, matching initial wallet plus gross realized minus fees.
- A further BUY partial0.4 at100 with0.01 fee produced wallet1023.99 and entry100; cancel released only remaining reservation and retained0.4 position, model, basis, PnL and fees.
- Injected native-evidence INSERT failure during a profitable close rolled wallet, average entry, position, gross PnL, fees, ledger and generation back to exact prior table snapshot. Retrying after removing the reviewer-only fixture trigger applied once.
- Protected backup/copy restore retained the complete accounting snapshot. Reopen with SPOT for the same perpetual session was denied before owner/state changes. Reopen with the correct model and a larger proposed starting balance retained all economic facts and became protected; no wallet reset.

Native adapter fields may report realized PnL net of commissions; durable store realized_pnl is gross with fees separately recorded. The wallet invariant uses gross realized minus fees. This receipt does not claim raw NET native realized equals gross store realized.

### Re-review command evidence

| Real command | Exit | Result |
|---|---:|---|
| First `python/.venv/bin/python /tmp/admission_perpetual_review_probe.py` | 1 | Reviewer fixture kept a pooled engine across protected file replacement, then wrote old inode. Corrected fixture disposes/reopens engine under migration maintenance contract; no implementation change inferred. |
| Second same probe | 1 | All economic/model/restart/backup assertions passed; added full `alembic.command.check` exposed legacy model/schema drift below. |
| Final same probe | 0 | All economic assertions passed; explicit metadata-drift inspection confirmed no admission/accounting diff while preserving legacy failure disclosure. |
| `python/.venv/bin/python -m pytest python/packages/quant-data/tests -q` | 0 |**42 passed in1.30s** on final accounting source. |
| `python/.venv/bin/ruff check python/packages/quant-data && python/.venv/bin/ruff format --check python/packages/quant-data && python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src` | 0 |Lint/18file format checks passed;0 type errors/warnings. |
| `python/.venv/bin/python /tmp/admission_review_probe.py` | 0 |Broad race/atomic/scope/protection/crash/backup invariants rerun after accounting schema change. |
| `python/.venv/bin/python /tmp/admission_identity_migration_probe.py` | 0 |Protected0003->new0004 preservation, full native UUID dedupe and low precision projection regressions rerun. |
| `git diff --check -- python/packages/quant-data` | 0 |No whitespace errors. |

Full Alembic metadata comparison is **not green**: existing strategy_versions metadata requests `uq_strategy_versions_id_version`, while existing trade_events ORM lacks the migrated `ix_trade_events_created_at` index. The comparison reports only those two legacy differences, not any admission/accounting table difference. Findings sent to parent/author; they are outside this scoped accounting extension. env.py now registers admission metadata explicitly and does not depend on application import ordering. No legacy schema repair was made by reviewer.

### Final fingerprints replacing earlier accounting fingerprints

- admission_contracts.py: `ae8bfb9426c05a871987b1a734ce5ce716792031b1e1917b0af2aa7b9290f4ec`
- admission_store.py: `51fc6d3a36267c44c11bbef9c0d027b09f31354fe1a414cb3586b11f66316887`
- admission_events.py: `2bee30d81ef5d4d99ec771e0bfa722f93c96764138175870b783f246a0518e04`
- admission_models.py: `5619b843157d978994fbcb3a6ad46aecafbd520a578cee6f2c0a223e8d8b8dac`
- ledger.py: `cf51015d3ef14c01fd220ce0734837324a4ed631018d8b3252b38a8c42d2da8f`
-0004_admission_state.py: `e4a79b0de13c5b492c508cf898e905a6439d02233415122556c2529c4044427f`
- alembic/env.py: `3f00623ded00c964897e6573acbf749c97ff8f79ac2e2a56bfeb9898a122e52a`
- test_admission_store.py: `3bd9d3c883b07db7741648fe5fc0c1b25ab1577be9e12d38ee420273bad70801`

Complexity score remains10/10 for this bounded store: private projection owns accounting-model formulas and public snapshots state their model and durable economics. All eight diagnostic rows pass within the slice, no failed row requires a further scoped change. All original product/native/release limits above remain in force; full original product acceptance remains parent-owned.

## Final metadata alignment re-review: legacy drift resolved

Parent explicitly requested a narrow ORM metadata correction and real Alembic comparison regression before final receipt. Author documented the manifest extension before modifying models.py/test_migrations.py. Independently inspected0001: it already creates the unnamed strategy_id/version uniqueness and ix_trade_events_created_at. The correction removes only the ORM's extra constraint name and adds metadata for the already-published index. No historical migration, user table, uniqueness semantics or stored history was changed by this correction.

**Final scoped verdict remains ACCEPT, now including clean current SQLite metadata consistency.** Earlier metadata-failure entries above are historical and resolved. Full `alembic.command.check` now reports `No new upgrade operations detected.` rather than suppressing legacy differences.

Final real commands:

- `python/.venv/bin/python /tmp/admission_perpetual_review_probe.py`: exit0; all economic, rollback, model/restart/backup probes passed and actual Alembic metadata comparison clean.
- `python/.venv/bin/python -m pytest python/packages/quant-data/tests -q`: exit0, **43passed in1.27s**, including real head-upgrade/command.check/reflected unique+index regression.
- `python/.venv/bin/ruff check python/packages/quant-data && python/.venv/bin/ruff format --check python/packages/quant-data && python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src && git diff --check -- python/packages/quant-data`: exit0; lint/18file formatting/type/whitespace checks green.

Additional final SHA256 fingerprints:

- models.py: `6b369ef87f8460f9f06257ad6895e5aeedfd52af924b714005b55f9ed7f2e057`
- test_migrations.py: `9a10ffee6bd0866165ea113ee7b1a80e3d60afd33c24540ecc2d3d6321d89162`

The final accounting fingerprints in the preceding addendum remain unchanged, including admission_events.py, frozen0004 and env.py. No unresolved blocker remains within the reviewed data/accounting/metadata slice. Full engine/native safety, product Verify Gate and release remain separately gated.
