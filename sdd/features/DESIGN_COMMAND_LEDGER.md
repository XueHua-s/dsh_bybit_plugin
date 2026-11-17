# DESIGN: Durable command ledger prerequisite

Date: 2026-11-17. Sources: BRAINSTORM_BYBIT_AI_QUANT.md, DEFINE_BYBIT_AI_QUANT.md, DESIGN_BYBIT_AI_QUANT.md. LLM prompts: false for this slice.

## Scope and drift

Implements only durable admission, risk-decision audit, single dispatch claim and local lifecycle observations for a future Nautilus authority. No HTTP API, exchange calls, credentials, executor, automatic resubmission or complete OMS. Existing direct TS execution drift remains unresolved. Existing Python quant-data ownership is explicitly preserved despite the repository's broad TypeScript wording; this follows the accepted Python data-plane design.

## Architecture and interface

`CommandLedger(sessionmaker)` hides SQLAlchemy transactions, unique-key races, canonical serialization, compare-and-swap updates and append-only audit insertion. Immutable typed `OrderCommand` contains environment (backtest/internal_paper/demo/testnet only), non-secret account reference, request ID, symbol, buy/sell, market/limit, Decimal quantity/limit price and reduce-only. No arbitrary payload/text metadata is accepted. Admission allocates a deterministic native client order ID and canonical SHA256 fingerprint before dispatch.

Public methods: `admit(command)`, `get(command_id)`, `events(command_id)`, `decide_risk(command_id, allowed, decision_code)`, `claim_dispatch(command_id)`, `observe(command_id, event_id, state, cumulative_filled)`, `recover_inflight()`. Return immutable records; dispatch claim returns a winner flag and record. Each call owns one fresh SQLAlchemy Session and transaction. Callers never hold transactions during exchange IO.

## States and invariants

- admitted -> ready or risk_rejected (coded risk decision).
- ready -> dispatching, one atomic winner only.
- dispatching -> accepted/partially_filled/filled/cancelled/rejected/reconciliation_required.
- accepted -> partially_filled/filled/cancelled/rejected/reconciliation_required.
- partially_filled -> partially_filled/filled/cancelled/reconciliation_required.
- reconciliation_required -> accepted/partially_filled/filled/cancelled/rejected only via externally obtained observation; never ready/dispatching.
- filled/cancelled/rejected/risk_rejected are terminal.
- Scope uniqueness is `(environment, account_ref, request_id)`. Same canonical typed payload returns the stored record; a changed payload raises conflict. Native ID is persisted at admission and does not change on retry/reopen.
- All successful transitions append an event in the same transaction; CAS uses state/version. No public update/delete of events. SQLite migration adds DB triggers rejecting event UPDATE/DELETE (PostgreSQL deployment is unverified).
- Event idempotency is `(command_id,event_id)` with a canonical event fingerprint. Same event replay causes no transition/event; changed reuse rejects. Lifecycle events store cumulative quantity, never decrement, never exceed order quantity; filled equals quantity and partial is strictly between zero and quantity.
- Risk rejection is durable and cannot dispatch. Risk admission does not implement the missing deterministic account/balance/notional guards: callers supply the independently computed decision.
- Recovery locally reclassifies only dispatching rows as reconciliation_required, atomically audited. It makes no exchange call and cannot infer execution outcome. Recovery requires the executor stopped/quiescent; a DB claim cannot fence an already running external exchange request.

## File manifest

| ID | Path | Action/purpose |
|---|---|---|
| 1 | python/packages/quant-data/src/quant_data/commands.py | Typed validated contracts and canonicalization |
| 2 | python/packages/quant-data/src/quant_data/ledger.py | Transactional deep ledger boundary |
| 3 | python/packages/quant-data/src/quant_data/models.py | Ledger ORM metadata |
| 4 | python/packages/quant-data/alembic/versions/0003_command_ledger.py | Durable schema, constraints and append-only triggers |
| 5 | python/packages/quant-data/tests/test_command_ledger.py | Admission/concurrency/lifecycle/recovery/backup fixtures |
| 6 | python/packages/quant-data/tests/test_migrations.py | Update head/schema expectations |
| 7 | sdd/reports/BUILD_REPORT_COMMAND_LEDGER.md | Real commands/exits, migration target evidence, limits |

## Verification and migration target

Only pytest `tmp_path` SQLite databases named `command-ledger-test.sqlite` and existing migration fixtures; no user database or default Alembic URL. Tests apply Alembic explicitly and inspect revision/schema. Backup uses existing protected `upgrade_sqlite` with fresh isolated fixture; restoring verified backup must preserve commands, native IDs, states and events. Verify concurrent threads with separate sessions for exactly one admission row and one dispatch winner, same/conflicting duplicates, persist/reopen, risk rejection, partial/fill/cancel, hostile input, terminal/invalid transitions, event replay conflicts and append-only triggers.

Commands: `uv run --project python --locked pytest python/packages/quant-data/tests`, `uv run --project python --locked ruff check python/packages/quant-data`, `uv run --project python --locked pyright python/packages/quant-data/src`. Parent owns full workspace Verify Gate, SBOM/security and independent review; no complete product acceptance claim.

## Complexity diagnostic

10/10 design target: one contract module owns validation/canonicalization; one ledger owns persistence/concurrency/state knowledge; ORM/migration share the explicit durable schema only. Interfaces document the important no-resubmission and transaction promises. All eight diagnostic rows pass for this bounded design; implementation/review evidence still required. Each source file <=500 lines.

## Limitations

SQLite concurrency and durability tested only; PostgreSQL locking/DDL, power-loss fsync, live reconciliation, account locks, risk engine, cancel commands, replace orders, fees/positions/trade reconciliation and Nautilus integration remain unimplemented. Observed cancel is a lifecycle outcome, not a cancellation request. Database owner can drop triggers; append-only enforcement is not tamper-proof or authorization. Restore requires stopped consumers and uses existing protected migration backup; no new general restore tool is claimed.

## Build refinements before acceptance

- Ready is only a recorded risk result: future execution integration must supply risk snapshot expiry, fresh account/instrument validation and capacity reservations immediately before dispatch. The boolean ledger decision is never standalone external trading authorization.
- Reports after a terminal cancelled/rejected/filled state raise `InvalidTransition` and explicitly require external reconciliation. They are never silently accepted/discarded as account-flat evidence. This prerequisite cannot process late-fill trade accounting or prove exchange finality.
- Canonical zero removes signed-zero differences and returns before Decimal formatting to bound extreme-zero exponents; limit price uses numeric positivity. SQLite insert guard also prohibits `INSERT OR REPLACE` replacing prior events, even with recursive triggers disabled.
- Concurrent identical observations read the committed event in a new transaction after a CAS loss; no transition or dispatch is retried. Audit insert fault injection proves rollback of both state/version and events.
