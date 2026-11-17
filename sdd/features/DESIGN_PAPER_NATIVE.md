# DESIGN: Native continuous internal paper

## Metadata

| Attribute | Value |
|---|---|
| Feature | PAPER_NATIVE |
| Date | 2026-11-17 |
| Author | native implementation agent |
| BRAINSTORM | BRAINSTORM_BYBIT_AI_QUANT.md |
| DEFINE | DEFINE_BYBIT_AI_QUANT.md |
| UX REVIEW | N/A |
| LLM Prompts | false |
| Status | Ready for Build; parent approved scoped implementation |

## Architecture Overview

```text
Engine admission / ledger -> bounded synchronous facade -> spawned process/event loop
                                ^                            |
                                | immutable native DTOs      v
                         bounded event queue <- Strategy / TradingNode / SandboxExecutionClient
                                                             |
                                                native SimulatedExchange (finite L2)
```

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| Facade | Own bounded lifecycle and dispatch; freeze on uncertainty | Python spawned process/loop/queue | Explicit fixture and IDs | Immutable evidence | Native owner |
| Native owner | Hide node config, callbacks and matching | Installed Nautilus 1.231.0 | Validated commands and full L2 fixture | Native events/account/positions | Sandbox adapter |
| DTOs | Describe synthetic fixture and execution evidence | Frozen dataclasses | Decimal inputs | Immutable values | Existing InstrumentSpec |

## Key Decisions

### Decision 1: Native continuous owner

Status Accepted; Date 2026-11-17; Source user/parent cutover instruction and DEFINE AT-010/014.
A single TradingNode lives on its own process/main-thread loop until stopped. Later commands preserve OMS, cash and positions. SDK lifetime cannot dispose it. Reject per-request BacktestEngine and handcrafted fills. Consequence: bounded cleanup and uncertainty must be visible, and restart is not reconstruction.

### Decision 2: Finite Sandbox compatibility adaptation

Status Accepted; Date 2026-11-17; Source installed sandbox/config.py and execution.py, engine.pyx/pxd inspected before implementation.
Installed Sandbox config omits liquidity_consumption and the exchange property is readonly. A private SandboxExecutionClient subclass initializes its LiveExecutionClient base and builds exactly one native SimulatedExchange with liquidity_consumption=True, then one native BacktestExecClient, account registration and initialization. Native connect/on_data/submit/cancel methods remain inherited. No discarded/shadow exchange or duplicate initial account. Its factory is private and carries no exchange connectivity. Reject default False and monkeypatching upstream globals. Consequence: scoped constructor compatibility is pinned to installed 1.231.0 and proven by native tests; future dependency upgrade requires review.

### Decision 3: Deep evidence boundary

Status Accepted; Date 2026-11-17; Source software-design-philosophy.
Callers see frozen DTOs and provided order IDs. Queue overflow, callback fault or lifecycle ambiguity freezes new submits. Snapshot copies native account/position/order facts on the owning loop. No callback or native object escapes. Bounded event drain is consumptive; durable persistence belongs to engine ledger. Unknown/restarted sessions cannot infer flatness from Sandbox empty reports.

### Decision 4: Official node in spawned worker process

Status Accepted; Date 2026-11-17; Source parent architecture decision and independent reviewer agreement before native execution.
Drift: initial thread design is replaced by a spawned subprocess whose main thread owns official TradingNode. The upstream node installs process signals; using a worker process retains official constructors without private kernel/node copies or global patches. Bounded multiprocessing queues carry frozen DTOs and commands. The service remains one modular-monolith deployment; no extra network service. Failure freezes dispatch, stop verifies actual child death/join and graceful cleanup acknowledgment; forced termination is failed rather than stopped. Snapshot exposes process_alive/process_id instead of misleading thread_alive. Constructor adaptation provenance and LGPL-3.0 source attribution is retained for finite Sandbox constructor. Exact GPLv3 base terms incorporated by LGPLv3 accompany the LGPL text; this does not change MIT file licensing.

### Decision 5: Native marked derivatives and owner death

Status Accepted; Date 2026-11-17; Source parent integration requirement and actual CryptoPerpetual/MARGIN semantics. Snapshot adds native realized/unrealized PnL, equity (wallet plus native unrealized) and owner-clock snapshot timestamp. No spot notional debit is inferred for margin fills. balance_free preserves raw native wallet-minus-margin evidence and excludes unrealized; available_equity=min(balance_free,balance_free+unrealized_pnl) conservatively includes marked losses without crediting gains. realized_pnl includes commissions. Durable derivative projection belongs to admission store. Spawned child checks its Python multiprocessing parent sentinel during startup/service loop and a separate watchdog thread that remains responsive if the native loop blocks; it schedules cancellation, then self-exits with code70 if cleanup has not completed within2seconds. owner death stops/disposes native loop and exits without waiting on an unread event feeder. This guards service SIGKILL beyond daemon cleanup. Bounded-event overflow remains explicitly incomplete and not recoverable in this slice.

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | python/packages/quant-execution/src/quant_execution/paper_models.py | Create | DTOs/validation | paper_native_runtime | None |
| 2 | python/packages/quant-execution/src/quant_execution/paper_sandbox.py | Create | Pinned finite native sandbox client/factory | paper_native_runtime | 1 |
| 3 | python/packages/quant-execution/src/quant_execution/paper_native.py | Create | Node/strategy/event mapping | paper_native_runtime | 1,2 |
| 4 | python/packages/quant-execution/src/quant_execution/paper_worker.py | Create | Spawned native owner and typed bounded IPC | paper_native_runtime | 1,3 |
| 5 | python/packages/quant-execution/src/quant_execution/paper_runtime.py | Create | Bounded process facade | paper_native_runtime | 1,4 |
| 6 | python/packages/quant-execution/tests/test_paper_runtime.py | Create | Real native persistence/fill/cleanup proofs | paper_native_runtime | 5 |
| 7 | sdd/reports/BUILD_REPORT_PAPER_NATIVE.md | Create | Actual commands/outcomes/limits | paper_native_runtime | 6 |
| 8 | python/packages/quant-execution/LICENSES/LGPL-3.0-only.txt | Create | Exact pinned upstream license | paper_native_runtime | 2 |
| 9 | python/packages/quant-execution/LICENSES/MIT.txt | Create | Exact root MIT license for original files | paper_native_runtime | None |
| 10 | python/packages/quant-execution/NOTICE.md | Create | Adaptation provenance and mixed-license scope | paper_native_runtime | 8,9 |
| 11 | python/packages/quant-execution/pyproject.toml | Modify | Mixed-license metadata and artifact inclusion | paper_native_runtime | 8,9,10 |

| 12 | python/packages/quant-execution/LICENSES/GPL-3.0-only.txt | Create | Exact GNU GPLv3 base terms incorporated by LGPLv3 | paper_native_runtime | 8 |

Total Files: 12. Agent Discovery: parent-assigned implementer and separate independent reviewer. No edits to existing offline Backtest semantics.

## Code Patterns

```python
runtime = PaperRuntime(PaperFixture(instrument, depth, starting_balance))
runtime.start()
runtime.submit(PaperOrder(client_order_id, "BUY", quantity, limit_price))
events = runtime.read_events()
runtime.stop()
```

## Data Flow

1. Trusted engine config supplies complete explicit instrument, cash and L2 snapshot.
2. Facade starts spawned process, constructs node, awaits native running and feeds first snapshot.
3. Bounded bridge runs commands on owner loop; strategy uses exact ledger ID.
4. Native callbacks copy immutable event/fill/cumulative/account/position facts into bounded queue.
5. Engine persists events; persistence fault invokes protect. Stop freezes dispatch and joins actual process/closed loop.

## Integration Points

Nautilus native SDK only; no authentication, network clients, credentials or exchange endpoints. Engine service owns risk, authorization, durability and synthetic data TTL.

## Testing Strategy

Real installed-node pytest: native accepted/full/partial/resting cancel, depth depletion across orders, later data fills, cash/position/session persistence, exact IDs and duplicate guard, lifecycle failure/stop no leaks. Ruff/Pyright and package regressions required. No exchange tests.

## Error Handling

Invalid fixture/order fails before dispatch; bounded command/event overflow and native callback/worker faults protect runtime. Timeout is uncertain and never resubmitted. Stop deadline reports failed if process remains alive; never claims joined until proven.

## Configuration

Explicit fixture, finite queue capacities and finite positive timeout. No ambient credentials/settings. Native reconciliation disabled because Sandbox reports cannot establish restored state.

Pinned node builder checks factory.__name__ == "SandboxLiveExecClientFactory" to inject portfolio; the private finite factory retains this exact native-required name and validates fixed config rather than silently accepting options. Fixture prices/quantities are validated before instrument.make_price/make_qty normalizes representational precision; this changes no fixture value.

## Security Considerations

Synthetic SIM venue only, no dynamic code/callbacks, no exchange client registrations. Account is fixture SIM-001. Mainnet/Testnet/Demo unsupported. Generated algorithms stay outside runtime.

## Observability

Snapshot exposes lifecycle, native instance identity, loop closure/process liveness, full native cash and net position, open order IDs, latest explicit market timestamp/depth. Event IDs and fill evidence are native.

## Requirements Traceability

AT-010/014/016: independent continuous native owner, supplied native identities and synthetic-only account. AT-015: freeze/no restart reconstruction. Full product acceptance remains outside slice.

## Risks and Mitigations

Native constructor compatibility pinned and tested; no general recovery claim. Event queue bounded: loss freezes before further dispatch. Blocking native disposal has bounded caller deadline and explicit failure status.

Software-design score target 10/10: all eight diagnostics addressed by private native ownership, simple typed facade, interface invariant comments and independent design/code review. Independent scoped review score10/10 (8/8diagnostics), failed rows none; receipt sdd/reviews/REVIEW_PAPER_NATIVE_2026-11-17.md. Full recovery acceptance remains open.

## Advisor Ledger

Independent reviewer paper_runtime_review accepted scoped native implementation and final derivative/ownerdeath delta; all findings applied. Parent requested finite consumption ADR before implementation and official process owner; incorporated before native execution.

## Revision History

1.0 / 2026-11-17 / scoped concrete pre-implementation manifest.

## Next Step

Execute o **SDD Build by RDD**.
