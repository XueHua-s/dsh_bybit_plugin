# DESIGN: Transactional Internal Paper Admission Store

Sources: complete DEFINE_BYBIT_AI_QUANT and DESIGN_EXECUTION_CUTOVER; AT-006/012/014/015/016/021/029. This scoped refinement closes the explicitly identified atomic-ledger coupling gap. No LLM prompts in this slice; product LLM requirements remain incomplete.

One deep AdmissionStore owns SQLite transaction serialization, durable owner and context generation CAS, append-only decision/native evidence, pending reservations and signed position/cash projections. It reuses ledger command/event construction and transition invariants; existing public CommandLedger behavior remains unchanged. The engine must additionally hold a process lifetime account lock. A database owner token cannot fence an already-running native call; no multi-host/exactly-once execution claim is made.

## File manifest

| Path under python/packages/quant-data | Action | Purpose |
|---|---|---|
| src/quant_data/admission_contracts.py | create | Strict frozen secret-free DTOs |
| src/quant_data/admission_models.py | create | New session, risk, reservation, native identity, position tables |
| src/quant_data/admission_store.py | create | Public transaction authority |
| src/quant_data/admission_events.py | create | Atomic native evidence and projection reconciliation |
| src/quant_data/ledger.py | modify | Share transaction-local transition helper without changing public behavior |
| alembic/versions/0004_admission_state.py | create | Additive schema, append-only guards, populated downgrade refusal |
| tests/test_admission_store.py | create | CAS, races, rollback, protection, evidence, backups |
| tests/test_command_ledger.py, tests/test_migrations.py | modify | Update head expectations only |

Also create sdd/reports/BUILD_REPORT_ADMISSION_STORE.md. Every source <=500 lines. No dependency/lock/CI changes.

## Public facade

`AdmissionStore(sessionmaker[Session])` exposes `open_session(environment, account_ref, session_id, owner_id, config_fingerprint, starting_balance) -> SessionSnapshot`; `snapshot(session_id)`; `decide(session_id, owner_id, expected_generation, command, decision) -> CommandRecord`; `claim_dispatch(session_id, owner_id, expected_generation, command_id, now_ns) -> tuple[bool,CommandRecord]`; `observe(session_id, owner_id, observation) -> CommandRecord`; `protect(session_id, owner_id, reason) -> SessionSnapshot`; `decisions(command_id) -> tuple[AdmissionDecision,...]`.

AdmissionDecision fields: allowed bool, code RiskCode, policy_fingerprint str(64hex), context_fingerprint str(64hex), evaluated_at_ns int, expires_at_ns int, reservation_price Decimal. NativeObservation fields: command_id str, event_id str, state CommandState, cumulative_filled Decimal, cumulative_notional Decimal, cumulative_fee Decimal, occurred_at_ns int. Notional and fees are cumulative per command; cash changes only by delta. SessionSnapshot fields: session_id, account_ref, owner_id, generation int, protected bool, protection_reason str|None, balance Decimal, positions tuple[PositionSnapshot(symbol,quantity)], reservations tuple[ReservationSnapshot(command_id,symbol,side,remaining_quantity,price)], last_admitted_at_ns int|None.

First create requires explicit INTERNAL_PAPER and synthetic configuration fingerprint. Existing session reopen rotates owner and generation, preserves cash/positions/reservations and becomes protected. Existing account alias cannot create a second session. Config mismatch fails. Every mutation checks owner; decisions/claim check generation. Decisions atomically create command stable ID, risk provenance and ready/rejected ledger event plus pending reservation. Duplicate identical commands return prior record; changed payload conflicts. Dispatch claim is durable before external IO and never retried. Event identity is session-global; changed duplicate and invalid/out-of-order/late-terminal events durably protect and preserve existing projections, retaining structured evidence. Reservation quantity shrinks by cumulative fill but released remainder only on terminal native evidence; positions retain partial exposure after cancellation. Uncertain remains reserved. Native reports cannot infer flat from empty output.

Validation: isolated pytest tmp SQLite migrations only; 0003 preservation, append-only guards and downgrade refusal, complete snapshot backup/restore, concurrent CAS winner and rollback fault injection. Parent owns independent review and full Verify Gate. Full paper replay/live OMS reconciliation remain incomplete.

## Complexity review

Design score 8.75/10: seven diagnostic rows addressed by single transaction owner, shared ledger invariants, frozen facade DTOs and explicit boundary documentation. Remaining row is independent implemented design review, owned by parent; 10/10 is not claimed.

Refinements before integration: read APIs require session_id and owner_id (`snapshot(session_id,owner_id)`, `get(command_id,session_id,owner_id)`, `decisions(command_id,session_id,owner_id)`). AdmissionDecision adds final reasons tuple[str,...]=(), validated against deterministic evaluator code allowlist and persisted immutable. Add paper_protection_events model/table for immutable protection history. Changed native duplicates retain structured attempted facts under deterministic conflict identities. Dispatch requires decision context_generation+1 == current generation, so later reservations/events invalidate earlier dispatch eligibility; no implicit risk reauthorization. 0004 freezes schema and never imports live models.

Packaging manifest refinement: modify pyproject.toml wheel force-include for Alembic tree/config and migrations.py resource location; installed wheel must migrate explicitly named tmp DB without repository. These are data package resources, no dependency changes.

Final facade additions (same owned files): `get_by_request(request_id,session_id,owner_id)` authorizes timed-out submission lookup without new native ID; `record_native(session_id,owner_id,command_id,event_id,event_type,occurred_at_ns)` retains audit-only native events under strict native event type allowlist. Normal lifecycle events use observe only. Fixed private Decimal arithmetic context prevents ambient rounding of accepted high-range values.

## Accounting drift correction: margin perpetual (2026-11-17)

Parent review identified a material integration mismatch: generic spot-style cash projection subtracted full BUY notional while native paper uses `CryptoPerpetual` with MARGIN accounting. This falsely treated newly opened notional as realized loss. Prior scoped ledger acceptance did not validate this economic coupling and is superseded for the changed accounting slice pending re-review.

Preserve existing spot behavior explicitly; add server-configured `AccountingModel` (`spot`, `linear_perpetual`) to first session creation, durable session row and snapshot, with explicit reopen comparison in addition to synthetic configuration fingerprint. Engine passes `LINEAR_PERPETUAL` and includes it in fixture fingerprint. Reject unsupported/inverse native instruments at the engine/native fixture boundary; this projection handles linear quote-currency perpetuals only. No automatic conversion of existing sessions.

For linear perpetuals, durable balance means collateral wallet: starting balance plus realized PnL minus cumulative native fees. Fills update signed quantity and weighted average entry. Partial close realizes closed quantity times price difference in prior position direction; reversal realizes prior closed exposure and opens residual at new fill price; flat average entry resets to zero. Retain realized PnL/fee totals and average entry durably with fixed arithmetic context. Spot balance meaning remains unchanged. Native cumulative report notionals remain immutable audit facts, not wallet debits for perpetuals.

`SessionSnapshot` adds accounting_model, realized_pnl, cumulative_fee; `PositionSnapshot` adds average_entry_price. `open_session` adds final `accounting_model=AccountingModel.SPOT` parameter to preserve existing generic tests, and the actual native perpetual integration must pass the explicit model. Engine computes marked durable equity from wallet plus signed quantity times (trusted mark minus average entry), compares against authoritative native equity, and accounts for actual fees/spread/mark PnL. Native author supplies authoritative wallet/free/equity/unrealized/realized/account time evidence for comparison. Opening notional itself cannot become loss. Unexplained discrepancies protect, never coerce into approval.

Manifest refinement within existing files only: add explicit accounting columns to frozen0004 schema/models/contracts; add perpetual averaging/closing/reversal projection to admission_events.py; tests prove no notional loss, actual fees and realized gains/losses, reversals, model mismatch on reopen, and exact fractional arithmetic. Add a private `paper_accounting.py` deep module if arithmetic would otherwise spread knowledge across store/event ownership; projection alone owns these accounting formulas. Parent-requested independent re-review is required before final acceptance. No user database migrated or funds accessed.

Migration metadata discovery refinement: modify `python/packages/quant-data/alembic/env.py` to import the admission model metadata alongside existing Base, ensuring future schema comparison sees all six new tables without relying on application import order. Historical0004 remains frozen and does not import live models.

## Parent metadata consistency correction (2026-11-17)

Independent `alembic.command.check` on an isolated fully migrated head found preexisting ORM drift: `StrategyVersion` declared a newly named unique constraint although0001 created the identical two-column unique constraint without a name, and `TradeEvent` metadata omitted the existing0001 `ix_trade_events_created_at` index. This is naming/discovery drift, not a proposed change to uniqueness or index semantics.

Manifest extension before edits: modify `python/packages/quant-data/src/quant_data/models.py` to match the existing unnamed strategy/version unique constraint and reflect the existing created_at index; modify already manifested `tests/test_migrations.py` to upgrade a named tmp database to head and run `alembic.command.check`. No historical migration file or user schema/data is changed. Independent reviewer rechecks metadata, ledger and perpetual behavior after this metadata-only alignment.
