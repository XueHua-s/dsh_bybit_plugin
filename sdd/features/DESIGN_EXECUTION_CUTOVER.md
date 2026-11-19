# DESIGN: Execution Authority Cutover

> Dependency-ordered integration design. This document is a future Build contract, not evidence that execution is available.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | EXECUTION_CUTOVER |
| **Date** | 2026-11-17 |
| **Author** | execution_cutover_design / SDD Design by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **UX REVIEW** | N/A |
| **LLM Prompts** | true at product scope; this integration slice introduces no LLM call or prompt |
| **Status** | Draft — future integration; foundation interfaces are being implemented/reviewed independently |

## Architecture Overview

```text
DSH model -> existing Tool -> generated TS client --authenticated command--> FastAPI
Operator -> trusted settings/approval + secure credential references ---------> |
                                                                            v
                         Engine admission authority (one account/session writer)
                         | server-owned context + policy | durable commands
                         v                               v
                    quant-risk.evaluate              quant-data ledger
                         | exact plan / veto              | stable native ID
                         +-------------+------------------+
                                       v
                         bounded node-thread command bridge
                                       v
                        private Nautilus Strategy -> native RiskEngine/OMS
                                       v
                      SandboxExecutionClient (INTERNAL_PAPER first)
                      BybitExecutionClient (DEMO/TESTNET later)
                                       |
                 native events/reports -> durable audit + projections
                                       |
                  account/market/reconciliation -> next server context
```

Existing `run_simulation()` owns a finite, stationary-fixture BacktestEngine run and disposes it. It does **not** provide a live paper session, durable admission, independent account risk, authenticated control or restart reconciliation. It stays a backtest API. The next slice must own a continuously running native node after HTTP/Tool completion, accept later commands against that same OMS, and process later market events. Disabling existing TS mutations alone would close a bypass but would not implement this slice or satisfy AT-014.

Source hierarchy: latest explicit user authorization > DEFINE > Brainstorm for requirements; inspected current source for facts. The complete 1,974-line original brief is the detailed scope baseline. Historical audit absence statements are superseded only where newer source/evidence exists. The full strategy/regime/portfolio/AI/research/evolution platform remains mandatory and incomplete.

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| API auth | Enforce local service identity and scopes before control | FastAPI dependency, fixed safe errors | Host-held service capability | Authenticated principal | Private bootstrap channel |
| Admission authority | Own admission, policy context and account serialization | Python service module, bounded queue | Validated proposal and principal | Durable command receipt | Risk, ledger, server state |
| Risk evaluator | Deterministically veto all required §13 limits | Existing `quant_risk.evaluate` pure function | Exact intent, server context, policy | Reasons or scoped plan | No HTTP/exchange/credential dependency |
| Command ledger | Own immutable request identity and transition history | SQLAlchemy/Alembic | Canonical order, decisions, native evidence | Stable native ID, append-only history | Existing quant-data |
| Native paper runtime | Hide node construction, native OMS, event mapping and stop | Nautilus 1.231.0, dedicated loop/thread | Admitted command, complete fixture market events | Actual native events/account state | Ledger, fixture instrument |
| Execution projections | Derive reconciled state and reservations | Engine-owned transaction/projection | Durable native events | Context revision, protection state | Ledger event identity |
| Generated control client | Hide bounded authenticated transport | Existing OpenAPI/openapi-fetch package | Service capability, command DTO | Validated receipt/status | Python sole wire schema source |
| Bybit session resolver (later) | Bind a credential reference to verified environment/account | Trusted credential provider, native Bybit adapter | Operator-selected opaque profile | Private in-memory session | DSH secure mechanism/OS secure store |

## Key Decisions

### Decision 1: Build an internal-paper integration before authenticated exchange execution

| Attribute | Value |
|---|---|
| **Status** | Proposed for next Build |
| **Date** | 2026-11-17 |
| **Source** | DEFINE AT-010–016, original §§5/12/13/16; inspected runtime |

**Context:** No engine command/admission/auth service exists. Prior account snapshot was unfunded and is not current authorization evidence. Current public ticker lacks complete native instrument/liquidity inputs. Native BacktestEngine tests do not establish a continuously operating service.

**Choice:** Next slice uses `SandboxExecutionClient` in a process-owned node with explicit fixture instrument, finite depth quotes, synthetic paper balance and paper account identity. Fixtures are server-configured, visibly synthetic, credential-free and inaccessible through arbitrary model code. No Bybit execution client is created or connected. A credential-free fixture data client registered with the node owns complete instruments/quotes and subscription handling; it forwards actual native data through the native data engine, with the sandbox venue matching the instrument venue. Do not publish a quote directly to only one observer or silently omit native data-client subscription setup. HTTP command handlers enqueue work; they do not own runtime lifetime. Later real public data must include actual executable sizes and instrument metadata; partial tickers are insufficient.

**Rationale:** Proves actual service admission → risk → native OMS → durable events without depending on funded exchange access or inventing liquidity. A live wall-clock session is distinct from offline research simulation.

**Alternatives Rejected:**
1. Call `run_simulation` per request — resets OMS/cash and disposes execution after each Tool call.
2. Generate custom Python/TS fills — bypasses required native execution and cannot validate native event behavior.

**Consequences:** Internal-paper evidence is explicitly limited; Demo/Testnet remains a separate gate. Native replay/recovery support cannot be inferred from sandbox report APIs.

### Decision 2: One engine-owned account writer and one canonical durable intent

| Attribute | Value |
|---|---|
| **Status** | Proposed; foundation coupling must be confirmed in Build |
| **Date** | 2026-11-17 |
| **Source** | DEFINE AT-012/014/015/021/029; current quant-risk/quant-data source |

**Context:** Concurrent individually approved requests can collectively exceed exposure. A risk plan is evidence, not a transferable execution authorization. Native memory duplicate detection does not survive process loss.

**Choice:** The engine serializes account/session admission and owns policy, context generation, reservations and dispatch. Resolve request principal to an allowed environment/account/session before ledger access. Persist `OrderCommand` before dispatch, including ledger-generated stable `native_client_order_id`. Same `(environment, account_ref, request_id)` plus same payload returns prior receipt; changed payload is 409. Explicit native `ClientOrderId` is supplied to `order_factory.market/limit`. Include pending reservations and last accepted time in later risk contexts. Recheck generation/expiry, emergency state, account identity, environment and worker health immediately before dispatch.

**Rationale:** Keeps all safety truth below the model and makes uncertain outcomes recoverable by the original ID. A single service writer and bounded backlog are sufficient now; no speculative broker fleet.

**Alternatives Rejected:**
1. HTTP fields for equity, identity, freshness, risk policy or reconciliation — callers could self-authorize.
2. Native auto-generated ID only / new ID on retry — loses durable identity and permits duplicate exposure.

**Consequences:** Single-process ownership combines a local process lifetime lock and durable account/session generation; no two engine processes may dispatch the same account. Ownership loss freezes dispatch. A database lease alone cannot fence an already-running external submit; future multi-host execution is unavailable until that fencing problem is explicitly solved. No claim of exactly-once exchange execution: commit and network submission are not one atomic transaction.

### Decision 3: Fail protected on uncertain dispatch and incomplete paper recovery

| Attribute | Value |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-11-17 |
| **Source** | Original §12; stable Sandbox/Bybit execution source |

**Context:** Sandbox `generate_order_status_report` returns `None`; bulk order/fill/position reports return empty lists. Empty reports are not proof of a flat recovered account. Native cache database is a separate persistence facility; SQLAlchemy command tables do not automatically restore it.

**Choice:** Persist dispatch claim before invoking native submit. A crash after claim becomes `reconciliation_required`, never a resend. For the first paper slice, restart with a previously active/nonterminal or non-flat session remains protected; show durable facts and unresolved status, deny new exposure. Do not silently seed a new starting balance. An operator may explicitly create a separate new paper session/account alias after preserving old state; this is a reset/new simulation, not recovery. Full paper recovery is a later deterministic replay of versioned native instrument/account/order events **and market/command chronology**, with side effects/audit duplication suppressed and replay-state digest verified before resuming. Cache-only order replay does not restore sandbox matching engine.

**Rationale:** Honest partial recovery is safer than falsely claiming the empty sandbox status reports reconcile positions. Live reconciliation must query native Bybit reports by existing client/venue IDs plus fill/account/position history and deduplicate reports/events.

**Alternatives Rejected:**
1. Treat empty report list as zero holdings — can lose fills/reservations.
2. Automatically resend after timeout — an accepted exchange order may already exist.

**Consequences:** First slice proves durable uncertainty and safe restart, not autonomous state reconstruction. The later recovery gate is required for continuous operational acceptance.

### Decision 4: Keep node lifetime and secrets below the API boundary

| Attribute | Value |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-11-17 |
| **Source** | Stable `TradingNode.run_async/stop_async/dispose`; original §§14/16 |

**Context:** `TradingNode.dispose()` manages its event loop and can wait synchronously. FastAPI also owns an event loop. Existing read SDK has no auth. Bybit config defaults to MAINNET and can fall back to process environment credentials.

**Choice:** Node owns a dedicated thread and loop. Bootstrap constructs node with that loop, adds explicit data/execution factories and private strategy, builds then starts a supervised `run_async` task. Node bridge delivers only validated native actions through its loop; callbacks never mutate API-loop objects unsafely. Stop freezes admission first, persists protection, drains/records remaining work, awaits node stop on its loop, waits boundedly for native queues, disposes on node owner thread, closes loop and joins thread. Failure to stop yields protected/failed outcome and retained uncertainty; HTTP `stop` cannot report stopped while thread remains alive.

**Rationale:** Concentrates native lifecycle knowledge and prevents closing the FastAPI loop. One private bridge hides required concurrency rather than spreading native APIs to tools.

**Alternatives Rejected:**
1. Run node/its synchronous dispose directly in an API handler — can block or close the server loop.
2. Put API credentials in model Tool parameters or generated strategy code — violates credential boundary.

**Consequences:** Native-loop ownership must be proven with subprocess integration. Auth credentials and later exchange secrets travel through protected process bootstrap/secure provider, never model-visible JSON or command-line arguments. No new LLM prompt is required.

### Decision 5: Cut over TS writes only after an executable paper path; exchange writes remain gated

| Attribute | Value |
|---|---|
| **Status** | Proposed; existing direct REST drift remains open |
| **Date** | 2026-11-17 |
| **Source** | DEFINE Nautilus MUST; `apps/dsh-plugin/src/host-tools-trade.ts` |

**Context:** Existing TS create/cancel/cancel-all/close call signed REST directly. A preview/flag/confirmation string does not establish sole Nautilus execution or final risk.

**Choice:** Stage transport/auth/admission/native runtime first, then route paper Tool commands through generated control client. Before any Demo/Testnet activation, remove reachable signed REST mutations from TS tools and low-level public client surface, including close and bulk cancellation. Preserve public/private read capability only under proper credential/environment separation. Unsupported exchange actions return explicit unavailable status; that is a limitation, not completion. No silent fallback to TS REST when engine is down.

**Rationale:** Delivers a working replacement while avoiding two writable exchange authorities at exchange activation.

**Alternatives Rejected:**
1. Add a Python executor while retaining TS writes — permanent bypass of final risk/reconciliation.
2. Disable all tools and declare cutover complete — removes product behavior without implementing authority.

**Consequences:** Controlled paper tools and exchange tools need distinct environment labels. Cancel/emergency/reduce-only require dedicated command/state semantics before being exposed; foundation submit-only types are insufficient.

## File Manifest

The following is the concrete **next internal-paper slice** manifest, all future edits. Paths marked Create are proposed, not claims of observed files. Keep each source ≤500 lines; split native construction/event mapping from lifecycle. Later phases have their own manifests after this slice is accepted.

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `python/packages/quant-data/src/quant_data/models.py` | Modify | Decision provenance, reservations, session ownership, native event projections | Build owner | None |
| 2 | `python/packages/quant-data/alembic/versions/0004_admission_state.py` | Create | Additive reversible schema after 0003, isolated-target migration only | Build owner | 1 |
| 3 | `python/packages/quant-data/src/quant_data/admission_store.py` | Create | Atomic decision+reservation+dispatch eligibility; ownership check and native event dedupe | Build owner | 1,2 |
| 4 | `python/packages/quant-data/tests/test_admission_store.py` | Create | Rollback, races, lease loss, reservations, native event identity and backup preservation | Independent verification | 3 |
| 5 | `python/apps/quant-engine/src/quant_engine/auth.py` | Create | Principal/scopes, constant-time capability verification, safe errors | Build owner | None |
| 6 | `python/apps/quant-engine/src/quant_engine/command_contracts.py` | Create | Strict Pydantic submit/receipt/query DTOs; no caller risk truth | Build owner | None |
| 7 | `python/apps/quant-engine/src/quant_engine/paper_context.py` | Create | Synthetic server-owned policy/context and reservations with revision | Build owner | None |
| 8 | `python/packages/quant-execution/src/quant_execution/paper_node.py` | Create | Native config, fixture data-client factory, private strategy and explicit ID creation | Build owner | None |
| 9 | `python/packages/quant-execution/src/quant_execution/paper_events.py` | Create | Native event/report mapping and monotonic fill evidence | Build owner | 8 |
| 10 | `python/packages/quant-execution/src/quant_execution/paper_runtime.py` | Create | Dedicated node-loop lifetime, bounded bridge, stop outcome | Build owner | 8,9 |
| 11 | `python/apps/quant-engine/src/quant_engine/admission.py` | Create | Ledger/risk orchestration, per-session serialization, fresh dispatch | Build owner | 6,7,10,3 |
| 12 | `python/apps/quant-engine/src/quant_engine/command_api.py` | Create | Authenticated control and command lookup routes | Build owner | 5,6,11 |
| 13 | `python/apps/quant-engine/src/quant_engine/api.py` | Modify | Compose observation and control, versioned protection state | Build owner | 12 |
| 14 | `python/apps/quant-engine/src/quant_engine/service.py` | Modify | Lifespan-owned admission/runtime, independent of Tool | Build owner | 11 |
| 15 | `python/apps/quant-engine/src/quant_engine/bootstrap.py` | Modify | Explicit paper session/DB target, private auth bootstrap, startup validation | Build owner | 13,14 |
| 16 | `python/packages/quant-execution/tests/test_paper_runtime.py` | Create | Genuine long-lived native events, later commands, clean stop | Independent verification | 10 |
| 17 | `python/apps/quant-engine/tests/test_admission.py` | Create | Actual ledger/risk, concurrency, uncertainty and recovery | Independent verification | 11 |
| 18 | `python/apps/quant-engine/tests/test_command_api.py` | Create | Auth/scopes/schema/isolation, no auth in errors | Independent verification | 12,13 |
| 19 | `python/apps/quant-engine/tests/test_paper_process.py` | Create | Separate process runtime and stop/restart contract | Independent verification | 15 |
| 20 | `python/apps/quant-engine/pyproject.toml` | Modify | Real risk/execution workspace dependency edges | Build owner | None |
| 21 | `python/apps/quant-engine/project.json` | Modify | Nx real graph, uncached serving/control smoke | Build owner | 20 |
| 22 | `python/uv.lock` | Modify | Resolve changed workspace package edges with existing pins | Build owner | 20 |
| 23 | `contracts/openapi/quant-engine.v1.json` | Regenerate | Canonical Python control schema/auth documentation | Build owner | 13 |
| 24 | `packages/ts/quant-api-client/src/generated/paths.ts` | Regenerate | Wire DTOs from Python only | Build owner | 23 |
| 25 | `packages/ts/quant-api-client/src/generated/schema.ts` | Regenerate | Runtime response validation | Build owner | 23 |
| 26 | `packages/ts/quant-api-client/src/index.ts` | Modify | Secret-opaque service auth hook; bounded command/query methods | Build owner | 24,25 |
| 27 | `packages/ts/quant-api-client/test/client.test.ts` | Modify | Auth/202/status/conflict/timeout redaction contract | Independent verification | 26 |
| 28 | `sdd/reports/BUILD_REPORT_EXECUTION_CUTOVER.md` | Create | Commands/exits, acceptance and live gaps | Build owner | 16,17,18,19,21,22,27,4 |

**Total Files:** 28.

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| Build owner | 1–3,5–15,20–26,28 | One accountable owner integrates the existing independently owned foundations |
| Independent verification | 4,16–19,27 | Verify authority/lifetime boundaries against actual behavior |

**Agent Discovery:** Parent-coordinated agents `command_ledger` and `risk_foundation` are building foundations; this design agent changes documentation only. This manifest assigns responsibilities, not permission to spawn further agents.

### Dependencies and later slices

1. Accept risk + ledger foundations, align conversion semantics and atomic risk reservation, verify migrated isolated database and backup/restore. Neither foundation alone authorizes execution.
2. Execute the 28-file paper slice above with fixture contexts and native runtime. No credentials or exchange connection.
3. Add paper cancel/emergency commands, portfolio targets and complete replay/recovery; wire DSH paper controls via generated client and tests. New manifest must cover `host-tools-paper.ts`/actual registrar, `lib/engine.ts`, panel/runtime types and installation evidence before claiming cutover.
4. Trusted Bybit connection/profile/permission preflight and native Testnet/Demo data/account reports; prove account identity, funds, fresh rules, no withdraw/transfer, no implicit account-setting mutations, full initial reconciliation. No order until these pass.
5. TS signed mutation removal plus fully routed native Testnet/Demo create/cancel/partial-fill/timeout/restart reconciliation. Initial supported product LINEAR only, explicitly configured; Spot and TP/SL/hedge support remain independent required acceptance.
6. Expand full strategy registry/features/regime/selector/portfolio pipeline, credible cost validation, AI team/research/evolution and operational gates from original brief. Paper plumbing cannot certify those requirements.

## Code Patterns

### Pattern 1: Use existing real foundation interfaces below one admission boundary

The inspected foundation APIs are `quant_risk.evaluate(intent, context, policy)` and `CommandLedger.admit/decide_risk/claim_dispatch/observe/recover_inflight`. Their final accepted revisions must be checked during Build. The risk author aligned its initial `paper` environment name to ledger `internal_paper` during this research. Current inspected environment names now agree; ledger lowercase sides vs risk uppercase still require explicit conversion. The engine owns explicit exhaustive conversions; never pass strings unchecked or silently equate Demo/Testnet/Mainnet. Risk `price_limit` must be an operator/server-derived execution bound for market requests, not a promise to fill at a quoted price. A native market order cannot enforce a limit; later exchange market execution needs an independently verified venue slippage mechanism or must remain unavailable.

```python
from nautilus_trader.model.identifiers import ClientOrderId

def native_client_id(persisted_id: str) -> ClientOrderId:
    """Reuse the committed ID; this function never allocates a retry identity."""
    return ClientOrderId(persisted_id)
```

Native `order_factory.market(..., client_order_id=native_client_id(record.native_client_order_id))` and `.limit(...)` accept explicit IDs in 1.231.0. Supply validated native `Quantity/Price` and the exact instrument from the server catalog. Current ledger only represents submit commands. Do not encode cancel/kill-switch as fake buy/sell commands.

### Pattern 2: Proposed API contract, not currently available endpoints

`POST /api/v1/trading/commands` admits an INTERNAL_PAPER submit proposal and returns HTTP202 with durable command ID, environment, paper-session alias, current state and native ID; acceptance is not venue acceptance/fill. `GET /api/v1/trading/commands/{id}` returns authenticated, scoped durable evidence. `POST /api/v1/trading/start` starts an explicit server-configured paper session; `POST /api/v1/trading/stop` freezes admission and reports stopping/protected/stopped accurately. Startup requests cannot provide cash/policy/identity flags. Internal fixture setup happens only in trusted service configuration/test composition.

Use strict Pydantic `extra='forbid'`, bounded IDs/decimals, no arbitrary metadata/prose or raw payload. Parse decimal strings with fixed precision/scale bounds. Unknown/mismatched environment/session fails before native factory creation. Validation errors redact input values. Authentication dependencies appear in OpenAPI; auth must not merely be documented.

## LLM Prompts

### Inventory

No prompt file or model runtime is added by this integration. Product `LLM Prompts:true` remains unchanged; existing/future research-role prompt contracts are outside this slice and remain governed by the full product design. Tool proposals are untrusted inputs; no model-generated code is loaded into the execution runtime. The trusted native bridge strategy is application source, not a generated algorithm.

## Data Flow

```text
1. Bootstrap loads explicit synthetic paper session and operator policy; opens configured
   isolated ledger; obtains service auth capability privately; starts protected.
2. Authenticate principal and scope; validate only proposal fields and allowed session.
3. Ledger admits canonical request before side effects; replay key returns durable prior.
4. Account writer obtains one server-owned snapshot generation: native account/positions,
   current complete quotes/instrument, reservations, policy, emergency/reconciliation.
5. Evaluate risk; atomically retain decision + context/policy provenance + reservation.
   Reject with stable reasons; a new request ID cannot override a policy veto.
6. Worker rechecks snapshot generation/expiry and authority, then claims dispatch durably.
   Database failure or stale plan prevents submit. Dispatch queue overflow stays protected.
7. Node owner builds order with committed ClientOrderId; Strategy.submit_order routes via
   native risk/OMS into SandboxExecutionClient; later complete ticks produce native events.
8. Durably record initialized/submitted/accepted/rejected/partial/fill/cancel evidence before
   publishing status; dedupe native event ID and venue trade ID, project cumulative quantities.
9. Replace reservation with actual state only on terminal/reconciled evidence. Cancel ack
   is not terminal. Partial-fill then cancel retains filled exposure and residual audit.
10. API/Tool returns may time out; runtime continues. Retry queries same durable command;
    no new native ID. Failure after dispatch claim remains reconciliation_required.
11. Stop freezes admission, persists state, supervises native stop/disposal/join. Restart
    cannot assert fresh/reconciled or reset balance from old checkpoints.
```

Coupling gaps to close in Build: ledger `RiskCode` is coarse, whereas evaluator reasons are detailed. Persist both stable coarse decision category and full **allowlisted code list**, policy/context revision and snapshot fingerprint in an append-only decision record. Current foundation has no atomic risk reservation/dispatch-eligibility transaction, durable account ownership or native event payload replay. Manifest files 1–4 explicitly add that integration state in quant-data; do not bury those writes in API modules. Detailed full matching-engine replay is a later slice; first-slice restart remains protected. Keep this Draft until accepted foundation revisions and implementation review confirm those contracts.

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| DSH Host | Generated loopback REST client | Private scoped service capability; never Tool parameter | Bidirectional | Timeout means query command; no TS execution fallback |
| SQL database | Existing SQLAlchemy/Alembic | Deployment-owned connection reference | Bidirectional | No side effect if commit uncertain; protect account |
| Nautilus Sandbox | In-process native APIs on owned loop | No exchange credentials | Bidirectional | Native task/event persistence error protects session |
| Bybit Demo/Testnet, later | Native Bybit factory/report APIs | Separate resolved secure credentials | Bidirectional | Native reconciliation by durable IDs before retry; no generic mutation retry |
| Credential provider, later | Trusted provider interface/private bootstrap | Host/OS secure storage; least privilege | Into engine memory only | Missing provider returns unavailable, never environment fallback |

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Actual evaluator + ledger conversion, no caller truth | `test_admission.py` | pytest | Wrong env/account, spoofed fields, invalid instrument, insufficient funds rejected before native submit |
| Integration | Concurrent intent reservation and stable IDs | `test_admission.py` | pytest + isolated migrated SQLite, later PostgreSQL | Two concurrent intents cannot overcommit; same key has one dispatch; changed payload conflicts |
| Native integration | Persistent native OMS | `test_paper_runtime.py` | pytest + real Sandbox/TradingNode | Second HTTP-independent command later in same node; native accepted/partial/filled/resting-cancel evidence |
| Failure injection | Commit/claim/submit/event/stop crash boundaries | `test_admission.py`, `test_paper_process.py` | pytest | Uncertainty retained; no automatic resubmit; protected restart preserves old paper state |
| Auth/security | Authentication, scopes, redaction, origin and session boundaries | `test_command_api.py`, SDK tests | FastAPI TestClient, Vitest | Unauthorized request causes zero ledger/native actions; no secrets in exceptions/response/logs |
| E2E | Independent process and native thread lifecycle | `test_paper_process.py` | Subprocess pytest + bounded HTTP | Server survives client close, pending command/status preserved, SIGTERM closes listener and node thread within deadline |
| Schema/engineering | Single schema, Nx real edges, existing regression matrix | Manifest 20–27 | Existing root `pnpm run verify`, schema/SDK checks, Ruff/Pyright/pytest/Vitest | Real exit0; uncached native/process evidence; no skipped required case |

Verification commands above are planned. This design/research task ran no build/test, exchange adapter connection, account request, migration, dependency installation or order. Full product Demo/Testnet, all risk integrations and genuine autonomous recovery remain unaccepted until separately evidenced.

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Invalid input/auth/scope | Pydantic/auth boundary | Fixed safe 401/403/422; no supplied value echo | Corrected request only | Code counters |
| Key collision | Ledger fingerprint mismatch | HTTP409; preserve original | No | Correlated opaque command ID |
| Risk veto/stale generation | Evaluator/dispatch revision check | Durable deny/protect; no dispatch | Fresh evaluation only under policy | Allowlisted reasons |
| Queue full/native worker death | Bounded bridge/task monitor | Protect, retain durable work | No blind claim reuse | Queue depth/task state |
| Timeout/submit ambiguity | Claimed dispatch without terminal evidence | reconciliation_required | Query existing identity first | Uncertainty age |
| Persistence failure | Transaction failure/event callback | Freeze new orders; retain reservations and protect | Explicit recovery | Safe DB fault code |
| Stop deadline exceeded | Native task/thread still running | Failed/protected; do not claim stopped | Supervisor/operator recovery | Stop outcome/thread count |

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `execution_environment` | enum | Explicit `internal_paper` for next slice | No | Never infer from token/key/URL; live values unavailable |
| `paper_session_ref` | bounded opaque ID | Trusted bootstrap, required | No | Separate ledger/account per simulated session |
| `paper_fixture_id` | allowlisted fixture ID | Trusted bootstrap | No | Complete instrument/depth/account fixture; synthetic disclosure |
| `risk_policy_ref` | versioned opaque ID | Trusted operator config, required | No | All required policy values explicit, no permissive defaults |
| `command_queue_capacity` | positive bounded integer | Trusted bootstrap | No | Finite backlog; stale work must be revalidated |
| `shutdown_timeout_seconds` | finite positive number | Trusted bootstrap | No | Actual observed stop/join contract |
| `service_capability` | opaque capability | Protected FD/provider, required for control | Yes | Never argv/model/ordinary config/browser storage |
| `database_reference` | opaque deployment reference | Operator-selected test/dev DB | Possibly | Validate target before Alembic; never echo connection string |
| `credential_profile_ref` | environment-scoped opaque ID | Later trusted settings | No | A reference, not credentials or authority by itself |

## Security Considerations

- Service remains numeric loopback only. Use capability authentication with distinct observation/control scopes, constant-time comparison, bounded body/response sizes and explicit no redirect/retry policy. Reject browser-origin control requests except a deliberately supported authenticated bridge; loopback alone is not browser-CSRF protection. Do not return token/profile secret values in generated schemas, errors or health.
- Host resolves service capability outside Tools. Cross-process bootstrap can use inherited private descriptor for service-launch integration; separately launched service requires an implemented secure provider. Missing provider is a blocker for authenticated integration, not permission to use a public default token. Unit tests inject synthetic capabilities.
- Later `/api/v1/bybit/connect` should accept only a trusted operator-selected opaque profile/environment reference. Engine resolves credentials through a secure provider inaccessible to model. Plain JSON Tool parameters, normal config files, model history and LocalStorage never carry key/secret. Ensure request validation/logging does not echo raw sensitive input even for unsupported fields.
- Native Bybit configs must explicitly set `BybitEnvironment.TESTNET` or `.DEMO`, correct single product type and explicit resolved key/secret; `None` environment means MAINNET. Forbid endpoint overrides/automatic env-key fallback. Never run upstream execution tester examples: defaults/exit actions are not this project's safety policy.
- Native adapter supports account-setting operations and defaults such as Spot auto-repay. Initial LINEAR factory forbids leverage/mode/margin overrides and borrow/repay paths until explicitly authorized and tested. Native connected state is not proof of correct subaccount, key permissions, reconciliation or available balance. No withdrawal/transfer permission is acceptable.
- Native runtime cannot accept dynamically supplied Python/JS, arbitrary native params, execution algorithms or user callbacks. Generated strategies stay in the separate research sandbox/promotion flow.
- Submit foundation conservatively treats all intents as extra gross exposure; it grants no reduce-only exemption. Dedicated cancel/kill-switch can stop new orders without flattening; flatten requires separate authorization/preauthorization and verified positions, not a network-failure default.

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | Fixed-code structured command/risk/native transition records | Trace opaque command/native IDs without payload/credential dumps |
| Metrics | Admission depth, native loop/thread health, risk denials, reservation exposure | Detect overcommit, dead worker and excessive rejection |
| Reconciliation | Explicit pending count/age, generation, last successful report/replay | Never imply recovered from checkpoint or connected WS alone |
| Lifecycle | Starting/running/protected/stopping/stopped/failed plus stop outcome | Distinguish requested stop from completed resource cleanup |
| Tracing | Propagate opaque request→command→native event IDs | End-to-end latency and durable evidence correlation |

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| AT-010, independent service | Dedicated node owner and FastAPI lifespan | Separate process/Tool-close/stop test |
| AT-012, AT-021, §13 | Server context, all original risk ceilings, reservations | Real evaluator + concurrent admissions; missing context veto |
| AT-014, AT-029 | Stable native IDs, ledger transitions, native events | Same-request one dispatch and restart uncertainty |
| AT-015 | Reconciliation-required state, no blind retry | Crashes at each dispatch boundary; later native reports |
| AT-016 | Explicit environment/account/session binding | Paper/Demo/Testnet alias and ledger isolation fixtures |
| AT-022 | Freeze-first design; dedicated cancel/close later | Next slice stop test only; full emergency acceptance still incomplete |
| AT-013, §16 | Pydantic authoritative DTOs and regenerated SDK | Schema/client drift tests and auth integration |
| Original §12, sole execution | Native strategy/OMS and later TS mutation removal | Repository mutation-path audit + no exchange write bypass |
| Original §§7–10/15/23 | Later strategy/research integration preserved | Not certified by this slice |

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Foundation API changes during review | Integration drift | Confirm accepted revisions, explicit adapters, no duplicate wire DTO | Files 1–4 add the reservation/ownership/decision schema; accepted foundation revisions must still be checked |
| Native event persistence is not atomic with execution | Lost local evidence | Claim-before-submit, protect on write failure, live report reconciliation | Cannot claim exactly-once external execution |
| Sandbox status methods are empty | False restart recovery | Protect old session; deterministic replay later | First slice cannot resume non-flat old paper sessions |
| Partial ticker/unknown depth | Fake executable liquidity | Complete explicit fixture feed; native real data later | Fixture fills do not predict exchange fills |
| Native disposal blocks/owns loop | API shutdown hang | Dedicated native loop/thread, bounded observed join | Implementation must prove actual installed lifecycle |
| Bypass remains in TS before exchange cutover | Two execution authorities | Do not activate engine exchange execution until removal audit passes | Existing direct TS drift stays open until implemented |
| Credential provider unavailable | No safe private connection | Keep paper credential-free; implement trusted provider before live | Demo/Testnet E2E remains blocked by real prerequisites |

Software-design assessment of the **current execution boundary**: **5/10 (4/8 diagnostics supported)**. Failed: interfaces simpler than implementations (Host exports REST/risk helpers), implementation replaceable without caller edits (TS direct exchange APIs), abstraction comments (no durable admission promise), newcomer-readable boundaries (native offline vs live authority conflated). This design targets all four via one deep admission API, private node lifecycle/event mapping, explicit durable invariants and separate paper/live evidence. A document does not increase the implemented score; 10/10 requires code/review evidence. One-sentence module purpose, information ownership within existing native/risk/ledger foundations, design review practice and deliberate design investment support the other four rows.

## Advisor Ledger

None — no formal external design review. Parent guidance to keep exchange prerequisites and full product gaps explicit is incorporated; foundation authors supplied API coupling facts, not architecture acceptance.

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-11-17 | execution_cutover_design | Draft dependency order, real installed API findings, concrete paper manifest and unresolved atomic ledger coupling |

## Next Step

Execute o **SDD Build by RDD**.
