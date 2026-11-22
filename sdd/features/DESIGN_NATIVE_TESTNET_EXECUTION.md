# DESIGN: Native Bybit Testnet Execution

> A future Build contract for the first authenticated exchange execution slice. This document does not claim that Testnet orders are currently available.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | NATIVE_TESTNET_EXECUTION |
| **Date** | 2026-11-22 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **UX REVIEW** | `sdd/reviews/UX_REVIEW_BYBIT_AI_QUANT_2026-11-19.md` |
| **LLM Prompts** | true at product scope; this slice adds no new prompt or model call |
| **Status** | Draft — future Build; Testnet writes remain disabled |

The current provider is GET-only and returns `order_submission_allowed=false`. The current paper runtime is synthetic and credential-free. Neither is evidence of this design being implemented. The pinned `nautilus-trader==1.231.0` package and its official Bybit integration were inspected locally and against the [Nautilus Bybit guide](https://nautilustrader.io/docs/latest/integrations/bybit/): the adapter exposes `BybitDataClientConfig`, `BybitExecClientConfig`, `BybitLiveDataClientFactory`, `BybitLiveExecClientFactory`, and `BybitEnvironment.TESTNET`. Build must verify the exact installed API again; this design does not infer readiness from documentation.

## Architecture Overview

```text
DSH AI cycle (candidate selection, target exposure, or abstention)
        │ generated TS client; opaque Host capability
        ▼
FastAPI command API ──► admission serializer ──► durable command ledger
        │                         │                    │
        │                         ▼                    ▼
        │                   quant-risk veto       stable ClientOrderId
        │                         │                    │
        │                         ▼                    │
        │              fresh account/rules check      │
        │                         │                    │
        │                         └──────────────┬─────┘
        │                                        ▼
        │              Nautilus Bybit Testnet node (single account writer)
        │                ├─ BybitDataClient/BybitExecutionClient factories
        │                ├─ private orders/executions/positions/wallet
        │                └─ bounded cancel/reduce-only/close state machine
        │                                        │
        │                                        ▼
        │             durable event projection + REST/WS reconciliation
        │                                        │
        └────────────── read-only status/PnL/decision/audit projections
```

The dashboard remains an observation surface. Chart symbol, market and interval only change the displayed snapshot. The AI and deterministic engine choose eligible instruments and parameters; a panel control never creates or authorizes an order.

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| Trusted profile resolver | Bind an opaque profile reference to Testnet Linear, expected UID/subaccount and an OS/Host credential handle | `bybit_profiles.py` plus a production Host/OS secret-store adapter; no ambient environment fallback | Profile reference, trusted settings | Sanitized profile binding and one-time in-memory credential handoff | DSH secure storage |
| Readiness and preflight | Prove identity, permissions, funds, instrument rules and complete initial reports before a session can dispatch | Existing `bybit_preflight.py` and `bybit_projection.py`, fail-closed | Named GET evidence | Versioned readiness evidence; never an order permit by itself | GET-only provider |
| Private account session | Own one account generation, authenticated native data/execution factories and private stream lifecycle | New `bybit_account.py` and `bybit_runtime.py`; dedicated child-process main-thread event loop; explicit `BybitEnvironment.TESTNET`, `BybitProductType.LINEAR` | Trusted profile, readiness evidence | Native account context and health | Nautilus 1.231.0 Bybit adapter |
| Admission authority | Serialize proposals, bind environment/account/session, reserve exposure and recheck policy immediately before dispatch | `quant_engine` service plus `quant_data` ledger | AI target exposure or operator emergency command | Durable command/receipt or veto | `quant-risk`, data ledger |
| Native order mapper | Convert an admitted intent into exact native instrument, `Quantity`, `Price`, `ClientOrderId`, reduce-only and protection fields | New `bybit_order_mapper.py`; no rounding or caller-supplied venue IDs | Server-owned intent and catalog | Native order command | Instrument/risk context |
| Reconciliation projector | Join REST bootstrap, private stream events and ledger by stable client/venue IDs; preserve unknowns | New `bybit_reconciliation.py` and additive data tables | Orders, executions, positions, wallet, fills | Reconciled account revision or protected state | Bybit REST/WS, ledger |
| Control API/client | Expose strict command/query DTOs generated from FastAPI OpenAPI | Existing `api.py`, `quant-api-client`, new execution paths | Host capability and validated DTOs | 202 receipt, status, safe errors | OpenAPI generator |
| DSH AI bridge | Pass AI intent to the same admission boundary while forbidding exchange credentials and UI inputs | Future bounded additions to `host-tools-ai.ts` / scheduler | Fresh candidate evidence, decision DTO | Simulated receipt until this slice is separately enabled | Existing AI loop |
| Read-only dashboard | Show AI-selected symbols, simulated/real state, readiness and reconciliation facts | Existing Client/Panel modules | Sanitized projections | Analysis and operational status | Host route |

## Key Decisions

### Decision 1: Testnet Linear only, with a hard Mainnet fence

| Attribute | Value |
|---|---|
| **Status** | Accepted for this slice |
| **Date** | 2026-11-22 |
| **Source** | DEFINE, architecture brief §§11–14, existing preflight evidence |

**Context:** The brief requires multiple environments, while current execution support is absent and Mainnet is explicitly disabled.

**Choice:** Implement one explicit `testnet` + `linear` session first. Mainnet factories, endpoints and credentials are rejected before construction, and no environment flag or OAuth result can enable them. Spot, Demo, inverse and options remain separate later slices.

**Rationale:** A narrow native contract is testable and prevents accidental endpoint/category widening.

**Alternatives Rejected:**
1. Reuse the current generic signed REST writer — it bypasses the sole Nautilus authority and has no durable reconciliation.
2. Implement all Bybit categories together — multiplies account, hedge, precision and recovery states before one product is safe.

**Consequences:** Initial acceptance covers only Testnet Linear; category expansion needs a new design and independent gate.

### Decision 2: Readiness is evidence, not permission

**Context:** A healthy public ticker, OAuth grant, API key or zero-error HTTP request does not prove the selected account or complete private state.

**Choice:** Before every session generation, require trusted UID/subaccount binding, exact non-withdraw permissions, fresh wallet/equity, current instrument rules, complete paginated orders/executions/positions and a clean reconciliation revision. Any missing, stale, ambiguous or inconsistent report protects the session and denies new exposure.

**Rationale:** This preserves the existing fail-closed preflight boundary while adding the account facts required by AT-012/014/016.

**Alternatives Rejected:** Treat an empty list, connected WebSocket or `eligible_for_reconciliation` as a flat account — it can hide an accepted order or external position.

**Consequences:** A session can remain read-only or protected even with positive balance until all report coverage is complete.

### Decision 3: Durable identity and one writer

**Context:** Network submission and local commit are not atomic; native in-memory duplicate checks do not survive process loss.

**Choice:** Persist the canonical intent, account generation, payload digest, risk reservation and a generated `native_client_order_id` before dispatch. Serialize one writer per account. The same request and payload returns its existing receipt; changed payload conflicts. Retries query the original client/venue ID and never allocate a new identity.

**Rationale:** This is the only safe way to handle timeout and post-dispatch uncertainty without claiming exactly-once exchange execution.

**Alternatives Rejected:** Generate a fresh ID on every retry, accept caller-provided equity/risk truth, or retain a second TypeScript exchange writer.

**Consequences:** A crash after the dispatch claim enters `reconciliation_required` and freezes new exposure until the original identity is resolved.

### Decision 4: Dedicated emergency state machine

**Context:** Cancel, reduce-only and flatten have different authorization and fill semantics; a generic “sell” command cannot represent them safely.

**Choice:** Add durable `freeze_new`, `cancel_open`, `reduce_only` and separately authorized `close_positions` commands. Stop freezes admission first, reconciles every remainder, preserves partial fills and never market-flattens because of a network error.

**Rationale:** It satisfies the architecture emergency-stop contract without letting an Agent or UI bypass risk or confirmation.

**Alternatives Rejected:** Category-wide cancel-all with no per-instrument evidence, or automatic flattening on shutdown.

**Consequences:** Emergency stop may leave a protected position until a verified, separately authorized close command succeeds.

### Decision 5: AI remains a proposer; deterministic code owns execution

**Context:** The user wants the AI to choose the coin and operation data, while the architecture requires independent risk and Nautilus execution.

**Choice:** The AI may choose zero or more symbols, action, target exposure, exits and horizon from a fresh candidate snapshot. It submits no exchange method and sees no secret. Admission recomputes sizing, rules, reservations, account state and risk; any veto records a reason. Dashboard filters never enter this input.

**Rationale:** This preserves the requested autonomous decision boundary without making the model an execution authority.

**Consequences:** “AI decided” means an admitted intent; it does not mean a venue order was accepted until native events and reconciliation prove it.

## File Manifest

The following is the next Build slice. No file below is evidence that the capability already exists.

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `python/packages/quant-data/src/quant_data/models.py` | Modify | Add account generation, reconciliation revision, native order identity and emergency state | (general) | None |
| 2 | `python/packages/quant-data/src/quant_data/commands.py` | Modify | Add submit/cancel/reduce-only/freeze/close command states and legal transitions | (general) | 1 |
| 3 | `python/packages/quant-data/alembic/versions/0007_native_execution_state.py` | Create | Additive migration for durable identity, reservations, events and reconciliation snapshots | (general) | 1,2 |
| 4 | `python/packages/quant-data/src/quant_data/ledger.py` | Modify | Atomic intent, reservation, dispatch claim and event dedupe | (general) | 1,2,3 |
| 5 | `python/packages/quant-data/src/quant_data/reconciliation_store.py` | Create | Persist redacted REST/WS evidence, revisions and protected reasons | (general) | 1,3 |
| 6 | `python/packages/quant-execution/src/quant_execution/bybit_account.py` | Create | Build only explicit Testnet Linear `BybitDataClientConfig`/`BybitExecClientConfig` and native factories from trusted credentials; reject ambient env fallback | (general) | Profile/preflight |
| 7 | `python/packages/quant-execution/src/quant_execution/bybit_order_mapper.py` | Create | Map server-owned intent to exact native instrument/order objects and stable ID | (general) | 1,6 |
| 8 | `python/packages/quant-execution/src/quant_execution/bybit_reconciliation.py` | Create | Join private REST/WS reports and preserve unknown/partial evidence | (general) | 5,6 |
| 9 | `python/packages/quant-execution/src/quant_execution/bybit_runtime.py` | Create | Own a native node in a dedicated child-process main thread, bridge bounded commands, stop and protected failure outcome | (general) | 6,7,8 |
| 10 | `python/apps/quant-engine/src/quant_engine/bybit_session.py` | Create | Session generation, preflight gate, account ownership and readiness | (general) | 4,5,6,8 |
| 11 | `python/apps/quant-engine/src/quant_engine/admission.py` | Create | Serialize AI intents, invoke deterministic risk and dispatch native commands | (general) | 4,7,9,10 |
| 12 | `python/apps/quant-engine/src/quant_engine/emergency.py` | Create | Freeze/cancel/reduce-only/close state machine with authorization scopes | (general) | 2,4,8,11 |
| 13 | `python/apps/quant-engine/src/quant_engine/command_contracts.py` | Create | Strict Pydantic request/receipt/status DTOs with no caller risk truth | (general) | 2,11,12 |
| 14 | `python/apps/quant-engine/src/quant_engine/api.py` | Modify | Mount authenticated execution queries/commands and safe error mapping | (general) | 10–13 |
| 15 | `python/apps/quant-engine/src/quant_engine/service.py` | Modify | Lifespan ownership, scheduler lease, restart protection and metrics | (general) | 9–14 |
| 16 | `python/apps/quant-engine/src/quant_engine/bootstrap.py` | Modify | Explicit secure profile bootstrap; reject Mainnet and ambient credentials | (general) | 10,15 |
| 17 | `contracts/openapi/quant-engine.v1.json` | Regenerate | Canonical command/query wire contract | (general) | 13,14 |
| 18 | `packages/ts/quant-api-client/src/generated/paths.ts` | Regenerate | Generated execution paths | (general) | 17 |
| 19 | `packages/ts/quant-api-client/src/generated/schema.ts` | Regenerate | Generated DTO validation types | (general) | 17 |
| 20 | `packages/ts/quant-api-client/src/index.ts` | Modify | Add capability-opaque execution query/command methods | (general) | 18,19 |
| 21 | `apps/dsh-plugin/src/host-tools-ai.ts` | Modify | Route only AI proposals through the engine; retain simulation-only default | (general) | 20 |
| 22 | `apps/dsh-plugin/src/host-tools-trade.ts` | Modify | Keep direct exchange writes unavailable; expose explicit engine-unavailable errors | (general) | 20 |
| 23 | `apps/dsh-plugin/src/client-types.ts` | Modify | Add typed readiness, reconciliation and protected-state projection fields | (general) | 14,20 |
| 24 | `apps/dsh-plugin/src/client-readiness.ts` | Modify | Render readiness, reconciliation and protected state without order controls | (general) | 23 |
| 25 | `python/packages/quant-execution/tests/test_bybit_execution.py` | Create | Unit map, endpoint, permission, precision and no-secret assertions against the installed Nautilus API | (general) | 6–9 |
| 26 | `python/packages/quant-engine/tests/test_bybit_admission.py` | Create | Identity, balance, risk, idempotency, uncertainty and emergency tests | (general) | 10–13 |
| 27 | `python/apps/quant-engine/tests/test_bybit_process.py` | Create | Separate process lifecycle, reconnect and protected restart | (general) | 14–16 |
| 28 | `packages/ts/quant-api-client/test/execution.test.ts` | Create | Generated contract, timeout, conflict and redaction tests | (general) | 17–20 |
| 29 | `apps/dsh-plugin/test/testnet-boundary.ts` | Create | AI/UI boundary and no direct POST regression matrix | (general) | 21–24 |
| 30 | `sdd/reports/BUILD_REPORT_NATIVE_TESTNET_EXECUTION.md` | Create | Actual commands, receipts, gaps and external Testnet evidence | (general) | 25–29 |
| 31 | `python/packages/quant-data/tests/test_reconciliation_store.py` | Create | Verify account generation fences, contiguous/idempotent reconciliation revisions, protected incomplete evidence, credential-field rejection, append-only migration constraints and backup preservation | (general) | 1–5 |
| 32 | `python/packages/quant-data/tests/test_migrations.py` | Modify | Keep published schema and preservation assertions aligned with the additive native execution migration | (general) | 3, 31 |
| 33 | `python/packages/quant-data/tests/test_command_ledger.py` | Modify | Keep ledger fixture assertions aligned with the new migration head while preserving command and dispatch coverage | (general) | 3 |
| 34 | `python/packages/quant-data/src/quant_data/native_ledger.py` | Create | Own generation-bound Testnet admission, risk receipt, reservation and revalidated one-shot dispatch claim without venue IO | (general) | 1–5 |
| 35 | `python/packages/quant-execution/pyproject.toml` | Modify | Declare the direct workspace dependency required by the typed native ledger mapper | (general) | 7 |
| 36 | `python/uv.lock` | Modify | Record the generated workspace dependency edge without adding an external package | (general) | 35 |
| 37 | `python/packages/quant-data/src/quant_data/reconciliation_events.py` | Create | Own bounded, canonical private-event evidence, conflict resolution and append-only persistence | (general) | 1,3,5 |
| 38 | `python/packages/quant-execution/tests/test_bybit_reconciliation.py` | Create | Verify offline report projection, explicit private-event provenance, status normalization, unknown identities and fill consistency | (general) | 8,31,37 |
| 39 | `python/packages/quant-execution/tests/test_bybit_runtime.py` | Create | Verify owner-process lifecycle, fixed failure codes, protection and clean stop without exchange IO | (general) | 9 |
| 40 | `python/apps/quant-engine/src/quant_engine/bybit_session.py` | Create | Own Testnet account generation, preflight and reconciliation activation without credentials or venue IO | (general) | 4,5,6,8,10 |
| 41 | `python/apps/quant-engine/src/quant_engine/admission.py` | Create | Convert typed AI proposals into server-owned commands, run deterministic risk, and claim native dispatch durably | (general) | 4,7,9,10,11 |
| 42 | `python/apps/quant-engine/tests/test_bybit_admission.py` | Create | Verify account/reconciliation gates, AI proposal binding, risk veto and one-shot claim without venue IO | (general) | 40,41 |

**Total Files:** 42. Every handwritten source file must stay at or below 500 lines; split any implementation that approaches the limit.

### Item 9 lifecycle decision (2026-11-23)

The initial wording said “dedicated thread/event loop”. Inspection of the pinned
Nautilus 1.231.0 implementation found that a live `TradingNode` constructs a
kernel which registers process signal handlers; Python permits that only in the
main thread. `TradingNode.stop()` also schedules directly on its loop and is
not a thread-safe cross-thread bridge. Item 9 therefore uses the existing
paper-runtime ownership pattern: one spawned child process owns the node and
its main-thread event loop; the parent exposes a small, bounded, credential-free
facade over IPC. This is an implementation correction, not evidence that a
live Bybit client is enabled. A future live factory must be created only inside
that child and must still pass the Testnet/Linear and readiness gates.

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1–39 | No independent Build owner was authorized or required; the slice needs one accountable integrator and separate test review before activation. |

**Agent Discovery:** Existing reviews and source were scanned; no active agent assignment is part of this design. Build must arrange independent verification of files 24–28 before enabling any write path.

## Code Patterns

### Pattern 1: Stable identity before dispatch

```python
record = ledger.admit(intent, account_generation, policy_revision)
native_id = ClientOrderId(record.native_client_order_id)
ledger.claim_dispatch(record.id, native_id)
try:
    runtime.submit(map_order(record, native_id))
except TimeoutError:
    ledger.protect(record.id, "reconciliation_required")
```

The catch path never creates a second ID. The actual implementation must use the pinned Nautilus APIs and record native events separately.

### Pattern 3: Report snapshots and private events keep separate provenance

REST wallet/position/order/execution reports belong only to an immutable reconciliation snapshot. Only explicitly supplied, normalized private-stream events may enter `native_execution_events`. Canonical event identity, redaction, deduplication and append-only insertion live together in `reconciliation_events.py`; the reconciliation store owns the enclosing revision transaction and protection fence. Each event and the serialized event batch are bounded to 1 MiB; a conflicting event identity makes the revision incomplete and protects the account.

### Pattern 2: Dashboard boundary

```text
chart symbol/category/interval -> GET market snapshot only
AI candidate snapshot -> proposal -> admission/risk -> native runtime
```

No Client control may call a command endpoint, and no chart state may be copied into an AI proposal.

### Complexity diagnostic

Current design score: **8/10**. Six diagnostics pass directly: module responsibilities are one-sentence describable, the public admission interface is smaller than its ledger/runtime implementation, the native venue protocol is hidden behind the account/runtime boundary, interface comments capture the safety invariant, the design assigns important decisions to single owners, and the manifest is dependency ordered. Two diagnostics remain open until Build: the production profile-store adapter is still represented by a protocol plus a fixture implementation (credential-storage knowledge can leak into callers), and the DSH-to-Python readiness projection needs one generated contract rather than parallel DTO knowledge. Reaching 10/10 requires implementing the OS/Host secret-store adapter and regenerating one authoritative readiness contract, then proving both with boundary tests.

## LLM Prompts

This execution slice introduces no new prompt. Existing background-loop prompts remain simulation-only until the execution gate is independently accepted. The runtime contract is:

| Item | Type | Consumer | Output shape | Failure behavior |
|---|---|---|---|---|
| Existing `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v4.ts` — candidate discovery stage | loop | DSH AI scheduler | Fresh bounded eligible-candidate snapshot; may abstain | Back off/block on stale or incomplete universe; never use static symbols |
| Existing `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v4.ts` — evidence stage | loop | DSH AI scheduler | Bounded research evidence tied to candidate/evidence digest | Treat unavailable/invalid evidence as explicit and non-authorizing |
| Existing `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v4.ts` — decision stage | loop | DSH AI scheduler | Zero or more candidate-bound proposals with action, exposure and exits, or abstention | Schema rejection or deterministic risk veto; no exchange method or secret |
| Existing `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v4.ts` — receipt stage | loop | DSH AI scheduler | Simulation/engine receipt keyed by request and decision digest | Back off/protect on timeout or uncertain receipt; never submit a second identity |
| Native execution | N/A | Deterministic admission/runtime | No LLM output is trusted as risk/account truth | Veto/protect on missing or invalid context |

## Data Flow

1. The AI obtains a fresh dynamic Bybit Instrument Info/ticker universe and may abstain.
2. The Host sends only a validated proposal and opaque capability to the local engine.
3. The engine resolves the trusted Testnet profile and verifies UID/subaccount, permissions, balance, instrument rules and complete reports.
4. Admission serializes the account, recomputes target order and deterministic risk, reserves exposure, and writes a canonical intent plus stable ClientOrderId.
5. The native thread submits through Nautilus only after a final generation/health/emergency check.
6. Native order, execution, position and wallet events are projected into the ledger; REST and private-stream reconciliation advances the account revision.
7. A terminal receipt is returned only for a terminal native state. Timeout, missing reports, restart, or projection failure returns protected uncertainty.
8. The dashboard reads projections and AI decisions; its view filters do not feed steps 1–5.

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| Bybit Testnet V5 | Nautilus native REST/WS adapter | Host-resolved API key/secret, in memory only | Bidirectional | Bounded reconnect; original ID reconciliation before any retry |
| FastAPI engine | Loopback HTTP/OpenAPI | Short-lived Host service capability | Bidirectional | Safe fixed-code errors; no credential in DTO/log |
| SQLite/Alembic | Local durable store | Deployment-owned file permissions | Bidirectional | Transaction rollback; backup/restore before migration |
| DSH Host | Generated TS client/tool bridge | Trusted capability injection | Bidirectional | No direct exchange fallback; scheduler backoff |

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Profile, endpoint, permissions, precision, stable ID and error redaction | `python/packages/quant-execution/tests/test_bybit_execution.py` | pytest, Ruff, Pyright | Invalid identity/permission/rules produce zero private dispatch |
| Unit/data | Account generation fencing, monotonic reconciliation, secret-field rejection, append-only evidence and migration backup | `python/packages/quant-data/tests/test_reconciliation_store.py` | pytest against isolated SQLite/Alembic database | Restart creates a protected generation; incomplete evidence stays protected; conflicting replay fails; migration data round-trips through backup |
| Unit/data | Canonical private-event identity, duplicate/conflict replay, unapplied markers and emergency-state synchronization | `python/packages/quant-data/tests/test_reconciliation_store.py` | pytest against isolated SQLite/Alembic database | Duplicate events insert once; conflicts protect the account; unknown event application remains `applied=0` |
| Unit/projection | Offline REST/private report validation, status normalization, fill consistency and event provenance | `python/packages/quant-execution/tests/test_bybit_reconciliation.py` | pytest, Ruff, Pyright | REST snapshots never enter the native private-event table; incomplete or ambiguous evidence remains protected |
| Unit | Ledger transitions, reservations, duplicate payload, event dedupe and protected state | `python/packages/quant-engine/tests/test_bybit_admission.py` | pytest + isolated SQLite | Same request has one canonical ID; changed payload conflicts |
| Integration | Native node receives actual order events, partial fill/cancel, reconnect and stop | `python/apps/quant-engine/tests/test_bybit_process.py` | spawned process, Nautilus fixture/mocked transport | No event or timeout is silently treated as flat |
| Contract | OpenAPI generation and safe TS client behavior | `contracts/openapi/quant-engine.v1.json`, `packages/ts/quant-api-client/test/execution.test.ts` | Nx/pnpm, uv | `openapi-check` and client tests exit 0 |
| DSH boundary | AI proposal route, display-only UI and denial of direct POST | `apps/dsh-plugin/test/testnet-boundary.ts` | plugin verify + source scan | No chart/UI path can dispatch; AI path has no secret |
| External Testnet gate | Explicitly capped, pre-authorized Testnet order lifecycle after all offline gates | Build report only | Manual runbook; never CI | Identity, balance, rules, native events and reconciliation all match ledger; otherwise remain incomplete |
| Release | Full workspace, SBOM, dependency and secret checks | Existing root scripts | `pnpm run verify`, Python checks, gitleaks, SBOM | Every command records exit code; unavailable external gate remains incomplete |

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Wrong environment/account/permission | Profile or private report mismatch | Deny before native factory/dispatch | No | Sanitized reason code, audit event |
| Stale/incomplete rules or account | Age, pagination, revision or join failure | Protect session; no new exposure | Read refresh only | Reconciliation status/age metric |
| Risk veto | Deterministic `quant-risk` result | Record veto; no model retry bypass | No same intent | Risk reason and counter |
| HTTP timeout after claim | No terminal native evidence | `reconciliation_required`; query original ID | No new ID | Uncertainty age, alert |
| Rate limit/WS disconnect | HTTP 429 or stream gap | Bounded reconnect/read refresh; freeze if stale | Yes for reads, no blind submit | Reconnect and latency metrics |
| Partial fill/cancel | Native event sequence | Preserve filled exposure and residual state | Query/reconcile remainder | Event ledger and position revision |
| Process stop/lease loss | Worker death or lease generation change | Freeze admission and retain uncertainty | Resume only after reconciliation | Protected reason, restart count |
| Emergency stop | Durable command accepted | Freeze first; cancel/reduce/close through dedicated states | Query each command | Operator/audit event |

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `execution_environment` | literal | Host trusted settings / `disabled` | No | Only `disabled` or explicit `testnet` in this slice |
| `bybit_profile_ref` | opaque string | Host secure settings / unset | No | References credentials and expected account identity |
| `bybit_category` | literal | Code / `linear` | No | Hard fence for the initial adapter |
| `max_order_notional_usdt` | decimal | Server policy / required | No | Deterministic cap below account and global limits |
| `reconciliation_interval_ms` | bounded integer | Server policy | No | REST/private-state refresh cadence |
| `emergency_state` | enum | Durable store / `running` | No | Freeze/cancel/reduce/close state machine |
| API key/secret | secure handle | OS/Host secret store / unset | **Yes** | Never in model DTO, command line, Git or logs |

## Security Considerations

- Mainnet endpoint, credentials and factories are rejected before construction; no environment switch can widen the fence.
- Profile references are resolved by trusted Host code. The model supplies neither credentials nor account truth.
- API responses, repository text, news and AI prose are untrusted evidence. Pydantic/typed projections reject unknown fields and redact transport errors.
- Native generated or third-party strategy code never runs in the execution process; only registered, reviewed strategies produce target exposure.
- No withdrawal, transfer, borrow/repay, leverage or account-setting operation is included in this slice.
- Durable IDs and claim-before-submit protect against duplicate exposure, but the design does not claim exactly-once venue execution.

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | Structured fixed-code events with profile/account redaction | Trace admission, native lifecycle and protection without secrets |
| Metrics | Queue depth, dispatch/venue latency, 429s, reconnects, stale age, protected sessions, reconciliation lag | Detect operational degradation before new exposure |
| Audit | Append-only intent, risk decision, native event and emergency command rows | Explain every AI proposal, veto, fill and recovery choice |
| Tracing | Correlate request ID, decision ID, ledger command ID, ClientOrderId and account generation | Follow one intent across Host, API, ledger and native node |

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| AT-001 | Existing Nx projects plus manifest integration files 14–20 | `nx show projects`; root verify |
| AT-002 | TypeScript source cap and strict generated client boundary | plugin/root typecheck and source-cap check |
| AT-003 | Bundle lifecycle remains isolated from execution activation | existing lifecycle smoke; build report records no activation claim |
| AT-004 | Decision 1 hard Testnet/Mainnet fence and profile resolver | endpoint/factory denial test |
| AT-005 | Service metrics and runtime health in files 9, 15 | process/health integration test |
| AT-006 | Additive migration, backup and reconciliation store in files 3–5 | migration backup/restore test |
| AT-007 | Strict DTOs, untrusted evidence envelopes and no generated-code execution | trust/injection regression plus boundary scan |
| AT-008 | Build report and repository SBOM/security checks | root release checks |
| AT-009 | Read-only dashboard copy and verified-status documentation | docs smoke and UX review |
| AT-010 | Dedicated engine service lifespan and loopback API | spawned process lifecycle test |
| AT-011 | Account-session market/private event projection | `test_reconciliation_store.py` and `test_bybit_reconciliation.py`; live stream integration remains pending |
| AT-012 | Readiness evidence and protected session on stale/missing state | stale/incomplete fixture matrix |
| AT-013 | FastAPI OpenAPI as sole wire source and regenerated TS paths/schema | OpenAPI drift check |
| AT-014 | Admission authority, stable ClientOrderId and Nautilus-only runtime | native event integration test |
| AT-015 | `reconciliation_required` transition and original-ID lookup | timeout/uncertain-result test |
| AT-016 | Explicit environment/account/session binding and separate ledger scope | environment isolation fixtures |
| AT-017 | Existing strategy registry remains the only strategy registration path | registry test suite |
| AT-018 | Registered strategy fixtures feed target exposure without venue access | strategy lifecycle tests |
| AT-019 | Existing selector evidence remains code-owned and candidate-bound | selector evidence tests |
| AT-020 | Portfolio planner output enters admission as target exposure | portfolio transition tests |
| AT-021 | Deterministic risk veto is mandatory before dispatch | admission risk matrix |
| AT-022 | Dedicated freeze/cancel/reduce-only/close state machine | emergency command tests |
| AT-023 | Research-role evidence remains schema-validated, expiring and credential-free | prompt/evidence contract tests |
| AT-024 | Algorithm registry and isolated validation remain outside native adapter | research validation suite; no third-party code in runtime |
| AT-025 | Promotion/rollback gate remains registry-owned | strategy registry negative tests |
| AT-026 | Common-cost and Nautilus event-driven validation remains a promotion gate | offline validation and native fixture tests |
| AT-027 | DSH tools call only generated, permission-checked engine methods | DSH boundary regression |
| AT-028 | Dashboard reads sanitized projections with no order controls | UI render and source scan |
| AT-029 | Durable command, event, reservation and reconciliation records | migration plus ledger tests |
| AT-030 | Performance-learning changes cannot alter risk ceilings | existing learning/registry tests and admission veto |
| AT-031 | Full release matrix records unavailable external gates as incomplete | Verify Gate and BUILD_REPORT |
| AT-032 | Dashboard filters are read-only market queries | client boundary regression |
| AT-033 | AI chooses eligible symbols/parameters; UI state is excluded | prompt and DSH boundary tests |
| AT-034 | Fresh full-catalogue discovery feeds bounded candidate set | dynamic-universe tests |
| AT-035 | Discovery failure yields no static-symbol fallback and protects directional decisions | fail-closed candidate tests |
| AT-036 | `quant_brief` is research-only evidence tied to fresh bars and cannot authorize execution | brief/evidence tests |
| Architecture §§11–14 | Components, data flow, one-writer and reconciliation decisions | Build report plus capped external Testnet gate |

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Native adapter behavior differs across Nautilus/Bybit versions | Wrong lifecycle or reconciliation | Pin versions, inspect actual events, run fixture and capped Testnet smoke | External partial-fill evidence may remain unavailable |
| Exchange accepted an order while local write failed | Duplicate order or hidden exposure | Claim-before-submit, stable ID, protected reconciliation | No atomic transaction across venue and database |
| Private stream gap hides an order | Unsafe new exposure | REST bootstrap/reconciliation and freeze on stale revision | Exchange history limits can delay certainty |
| AI proposes a malformed or over-sized target | Loss or invalid order | Strict DTOs, server-owned sizing and deterministic risk | Strategy quality remains a separate research problem |
| Emergency close is assumed during outage | Unintended market risk | Freeze-first; close requires verified position and separate authorization | Operator must resolve protected state |
| UI implies execution readiness | Misuse | Explicit unavailable/protected labels and no order controls | Readability needs live visual recheck after activation |

## Advisor Ledger

None — no formal external design review occurred for this new slice.

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-11-22 | SDD Design by RDD | Initial future Testnet execution contract; preserves read-only and simulation boundaries. |
| 1.1 | 2026-11-23 | SDD Build continuation | Separate REST snapshot evidence from explicit private events; add the event evidence module and offline projector tests. |

## Next Step

Execute o **SDD Build by RDD**.
