# DESIGN: AI decision to durable synthetic-paper admission

> A bounded integration slice in the complete Bybit AI Quant architecture. This design is a prerequisite for, and does not satisfy, the complete product goals or unattended Testnet acceptance.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | AI_TO_SYNTHETIC_PAPER |
| **Date** | 2026-11-20 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | N/A — no feature-specific Brainstorm found |
| **DEFINE** | `sdd/features/DEFINE_AI_TO_SYNTHETIC_PAPER.md` (authoritative acceptance and scope for this slice) |
| **UX REVIEW** | N/A |
| **LLM Prompts** | true |
| **Status** | Ready for Build |

The authoritative architecture brief is available outside the repository at `/Users/litlesnow/.codex/attachments/886f3b36-5cab-4ba1-bb1c-7ef525af0e6e/pasted-text-1.txt` (1,974 lines; read successfully on 2026-11-20). The offline defaults and contract decisions below are closed for this slice; parent-product gaps remain explicitly out of scope. Registry bundles are explicit in-process injections for isolated service assembly/tests; this document does not specify an operator-facing fixture provisioning system or claim a deployed autonomous loop. The public readonly API remains canonical in `contracts/openapi/quant-engine.v1.json`; all authenticated internal-paper routes remain canonical in `contracts/openapi/quant-paper.v1.json`, exported from the actual `create_paper_app` using `quant-engine-openapi --paper`. The existing Nx `quant-engine:openapi` and `quant-engine:openapi-check` targets serialize generation/check of both contracts; no target bypass or hand-edited OpenAPI is allowed. No code is changed by this document.

**Inspected evidence:** `python/apps/quant-engine/project.json` defines sequential Nx `openapi` and `openapi-check` commands for both `contracts/openapi/quant-engine.v1.json` and `contracts/openapi/quant-paper.v1.json`; both files exist. `python/apps/quant-engine/src/quant_engine/bootstrap.py::export_openapi --paper` serializes the actual `create_paper_app` without lifespan. `packages/ts/quant-api-client/scripts/generate.ts` reads both contracts and emits `generated/paper-paths.ts` and `generated/paper-schema.ts`; `validation.ts` registers the paper schema; `paper.ts` owns authenticated paper routes. The readonly engine contract and client artifacts must remain separate. Also inspected `apps/dsh-plugin/src/lib/ai-universe.ts` (currently Bybit-client-backed; it must gain an injected fixture adapter for this slice), `apps/dsh-plugin/src/host-runtime.ts`, `apps/dsh-plugin/src/host-tools-ai.ts`, `apps/dsh-plugin/src/host-tools-watchlist.ts`, `apps/dsh-plugin/src/lib/ai-scheduler.ts`, `apps/dsh-plugin/src/lib/ai-decision-writer.ts`; `python/apps/quant-engine/src/quant_engine/{strategy_evidence.py,strategy_selector.py,portfolio.py,paper_admission.py,paper_context.py,paper_api_models.py}`; `python/packages/quant-{portfolio,risk,execution}/src`; `sdd/features/{DESIGN_AI_STRATEGY_EVIDENCE.md,DESIGN_AI_DECISION_CONCURRENCY.md,DESIGN_STRATEGY_SELECTION.md,DESIGN_PORTFOLIO_ALLOCATION.md,DESIGN_PAPER_ADMISSION.md}` and their Build reports.

**Architecture brief traceability:** The attachment's §§1 and 8 require dynamic instrument discovery, market-state strategy selection and portfolio allocation; this slice uses a dynamic *isolated fixture* universe and the existing selector/planner while keeping them research/account-free. The live Bybit discovery requirement remains a parent gap. §§12–13 require a single execution authority and independent non-bypassable risk veto; this design routes only to the existing isolated native paper OMS and `quant_risk`, with no Bybit/Testnet/Mainnet write. §§14, 19 and 26 require explicit authorization, append-only auditability, credential isolation and safe recovery; the proposed decision/request binding, receipt chain, strict untrusted-input boundary and protected restart address these for synthetic paper only. §§15–16 require reproducible validation and authenticated/idempotent cross-language contracts; the manifest adds strict versioned DTOs, digest identity and fixture tests, and this slice therefore accepts only deterministic, digest-registered fixture evidence; unauthenticated live/research evidence remains outside scope. §§20–21 require monitoring and offline test coverage; the design includes stage metrics, recovery signals and isolated tests, while full SBOM/CI/Plugin Manager/Testnet evidence remains parent scope. The attachment's §§3–4 and 24–25 require independent engine lifetime and eventual Demo/Testnet/Mainnet capability; this prerequisite deliberately does not claim those capabilities.

### Architecture brief coverage matrix

| Brief reference | Requirement relevant to this slice | Design response | Coverage status after this slice |
|---|---|---|---|
| §1, lines 38–66 | Dynamic eligible market universe and instrument precision/limits; no hardcoded BTC-only product universe | Python-owned registry exposes only explicitly registered arbitrary offline fixtures; each bundle digest binds universe, rules and multi-instrument OMS | Partial: live Bybit discovery remains a parent gap; this slice proves dynamic isolated fixtures only |
| §§5, 8, lines 294–372, 853–908 | Separate AI, strategy, portfolio, risk and execution boundaries; dynamic strategy choice and safe transition | Explicit orchestrator boundary; selector and planner remain pure; each transition is mapped and independently re-evaluated | Partial: existing pieces exist but the end-to-end orchestration is absent; this design specifies it |
| §§12–13, lines 1113–1225 | Single Nautilus execution authority; independent risk veto; uncertain outcomes reconciled before retry | Only internal synthetic native OMS is reachable; risk rejection terminal; CAS/idempotency and protected unknown outcomes | In scope for synthetic paper design only; real Bybit and Testnet execution are excluded and remain unproven |
| §14, lines 1230–1262 | Secrets isolated; explicit authorization for Mainnet | No exchange secrets or external order transport enter this slice; environment fixed to internal paper | Covered for this slice's boundary; does not establish eventual Mainnet authorization system |
| §§15–16, lines 1262–1393 | Cost-aware reproducible validation; authenticated, validated, idempotent API contracts | Strict DTO/digest, digest-registered built-in fixture evidence and durable request binding | Partial parent gap: live/research artifact provenance is out of scope; fixture evidence contract is closed here |
| §19, lines 1531–1559 | Durable decisions/orders/snapshots and append-only audit history | Decision/request binding, evidence/intent digests and native receipts; additive migration proposed | Partial: no cross-pipeline binding currently exists; backup/restore and Alembic downgrade acceptance remain required |
| §§20–21, lines 1563–1637 | Runtime health, recovery and offline testing | Stage metrics/readiness and isolated unit/integration/crash tests planned | Partial: proposed evidence only; no new runtime/monitoring verification performed in this document task |
| §§3–4, 24–25, lines 160–373, 1752–1928 | Independent long-running engine, DSH integration, eventual multi-environment platform and full product acceptance | This is one prerequisite vertical slice; it does not change DSH lifecycle or add exchange environments | Explicitly not satisfied by this slice |

## Architecture Overview

```text
DSH Host AI cycle
  ├─ Python SyntheticFixtureRegistry bundle → read-only loopback snapshot/digest → bounded AI universe (research input only)
  ├─ AI chooses eligible symbol/action/parameters or abstains; decision CAS + receipt
  └─ Python strategy evidence (research only; never an execution token)
                    │ strict versioned proposal + evidence/snapshot identities
                    ▼
Python integration orchestrator (new; no DSH/venue credentials)
  ├─ verify decision/universe/evidence provenance, expiry and replay identity
  ├─ Python strategy selector → account-free TargetProposal
  ├─ portfolio planner → target exposure transition (not an order)
  └─ exposure mapper uses reconciled synthetic paper snapshot + fixture rules
                    │ exact OrderIntent + expected admission generation
                    ▼
Existing independent quant_risk evaluator
                    │ approve/reject with stable reasons; never bypassed
                    ▼
Existing PaperAdmission → AdmissionStore CAS/reservation/client-order-id
                    │ durable decision before dispatch claim
                    ▼
Python-owned multi-instrument PaperRuntime → isolated Nautilus synthetic OMS/fixture
                    │ native events + durable receipt/status
                    └── restart: query by request ID; protect uncertain/non-flat session

No Bybit private API, exchange order route, Demo, Testnet or Mainnet path is in this slice.

**Runtime single-source invariant:** For `internal_paper`, Python `SyntheticFixtureRegistry` owns the explicitly injected immutable bundle and its digest, including one canonical finite correlation coefficient in [-1,1] for every unordered symbol pair. Missing, duplicate/reversed or out-of-range pairs fail closed; 1.0 may represent only a conservative synthetic assumption. The API route exposes the bundle but does not source or synthesize market truth. The read-only fixture route returns candidates, snapshots, depth, rules and correlations; POST accepts only bundle identity and candidate choice, then resolves all values by registry lookup. The multi-instrument PaperRuntime and independent RiskContext receive that same bundle.
```

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| AI decision source | Choose zero or more fresh eligible candidates, action and simulated parameters; provide evidence references | Existing DSH Host tools, bounded prompt, optimistic journal CAS | Python registry snapshot and bounded fixture evidence | Cycle-bound decision record or abstention | DSH injected model boundary; Host tools; decision writer |
| SyntheticFixtureRegistry | Solely own and validate registered multi-symbol fixture bundles and canonical digest; serve read-only snapshot and resolve symbol/rules for OMS | Python typed registry; no network/credentials; immutable per session | Explicit local fixture bundle registration and session | Candidate universe, market/depth/rules snapshot and digest; symbol→instrument lookup | `paper_config.py`, `paper_api.py`, `paper_runtime.py`, `paper_native.py` |
| Internal-paper fixture adapter | Read the registry snapshot/digest over authenticated loopback and expose it to Host AI tools | Typed TS loopback adapter; no Bybit source in scoped profile | `internal_paper` profile | Host candidate pool and identity-bound snapshot | `engine.ts`, `ai-universe.ts`, `host-runtime.ts` |
| Decision contract adapter (new) | Validate AI decision identity, candidate membership, action semantics, expiry and duplicate receipt before quant processing | Strict Pydantic request DTO, no coercion/unknown fields | Decision ID, cycle receipt, universe snapshot ID/digest, candidate, market snapshot IDs/times, evidence refs | Immutable validated `DecisionEnvelope` | AI API contract; clock; Python validation |
| Strategy selector + portfolio planner | Turn permitted, fresh evidence into an account-free strategy choice and target transition | Existing pure selector/portfolio modules; no account side effects | One market snapshot, approved registry metadata, OOS evidence reference, reconciled internal-paper exposure read | Selection plus `PortfolioPlan`/transition | quant-strategies, quant-portfolio; validated evidence |
| Exposure mapper (new) | Convert one transition step into an exact internal-paper `OrderIntent` | Decimal arithmetic; fixture instrument filters; deterministic rounding | Target/current exposure, paper equity, fixture bid/ask, tick/step/min/max rules | Proposed intent and mapping audit record, or typed rejection | Portfolio transition; trusted paper snapshot and fixture |
| Independent risk/admission | Reconcile and evaluate each exact intent, persist decision/reservation with generation CAS, then dispatch once | Existing `quant_risk.evaluate`, `AdmissionStore`, `PaperAdmission` | Exact intent, server-owned current native/durable snapshot, policy | Durable rejected/admitted command, stable client order ID | Pre-migrated isolated SQLite; synthetic PaperRuntime |
| Native synthetic OMS | Simulate order lifecycle and emit observations | Existing isolated Nautilus Sandbox process with L2 fixture depth | Claimed durable limit command | Native order events and synthetic account snapshot | PaperRuntime; no external transport |
| Receipt/recovery reader (new or existing API adapter) | Correlate decision→intent→admission→native event and expose restart-safe status | Request-ID lookup and append-only audit references | Decision ID and idempotency key | Receipt/status; protected/unknown state when ambiguous | AdmissionStore get-by-request; read-only API |

## Key Decisions

### Decision 1: Environment and authority boundary

| Attribute | Value |
|---|---|
| **Status** | Accepted — mandated by this task and repository policy |
| **Date** | 2026-11-20 |
| **Source** | Current user instruction and `AGENTS.md` |

**Context:** The parent product includes exchange environments, while this slice must be safe and independently verifiable.

**Choice:** Permit only `internal_paper` with explicit synthetic fixtures and the existing native simulated OMS. The integration has no credential, exchange client, account API, or external order transport dependency. Fail startup if the environment or fixture mode is not literally internal synthetic paper.

**Rationale:** It keeps the new orchestration inside the already implemented deterministic paper boundary and prevents an accidental environment downgrade/upgrade from changing authority.

**Alternatives Rejected:** Testnet or live Bybit execution — explicitly outside this slice and requires separate authorization/acceptance.

**Consequences:** This does not prove Testnet or full-product readiness; the supported OMS symbols are limited to fixtures actually registered by PaperRuntime.

### Decision 1A: Versioned loopback transport

| Attribute | Value |
|---|---|
| **Status** | Accepted for this slice |
| **Date** | 2026-11-20 |
| **Source** | Existing `paper_api.py` route/authentication conventions and offline scope |

**Choice:** The Host first reads `GET /api/v1/trading/fixtures/{fixture_id}` with the existing process-private bearer capability and `observe` scope; Python returns the bounded candidate universe, snapshot, fixture rules/depth and canonical registry digest from the same bundle used by the OMS. It then uses `POST /api/v1/trading/ai-cycles` with `control`; status resolution uses `GET /api/v1/trading/ai-cycles/by-request/{request_id}` with `observe`. All routes are loopback-only, reject `Origin`, use the existing body cap and synthetic session binding, and accept no venue/exchange URL. The strict POST envelope contains literal `internal_paper`, request/payload digests, cycle/decision IDs, `fixture_id`, registry digest, universe/snapshot/evidence identities, expiry and typed decision; it carries no authoritative price, depth, precision or policy fields. Python re-resolves the bundle by ID+digest, ignores or rejects supplied execution data, and validates candidate membership before selector/admission. TS and Pydantic schemas reject unknown/coerced fields. A fixed test-injected 5,000 ms deadline is fail-closed; timeout permits one GET with the same request ID, then returns protected/unknown.

**Fixture contract:** The injected `PaperFixtureBundle` is immutable for a session and contains `fixture_id`, `bundle_digest`, ordered candidates, symbol-keyed OHLCV/evidence/instrument/depth/rules, and exactly one `SyntheticCorrelation` per unordered symbol pair (self-pairs omitted). Pair keys must be strictly sorted (`first_symbol < second_symbol`) with no missing or duplicate entries; each Decimal coefficient must be finite and within [-1,1]. No implicit zero or external estimate is allowed. A test may use 1.0 only as a conservative worst-case synthetic assumption, not as measured correlation. The complete pair matrix is included in canonical digest and readonly snapshot and is converted unchanged into the existing independent `RiskContext`. Symbols match `[A-Z0-9]+(?:[-._][A-Z0-9]+)*`, length 1–40; repeated, leading or trailing separators and whitespace/control/path characters fail closed. Selector evidence is synthetic fixture-owned, with strategy identity, approval, paper-passed state, OOS values, expiry, regimes, samples and ready signal. No caller/online data can supply it. Each symbol has 1–32 fresh ordered OHLCV bars. The POST carries identity and decision only, never correlations or market/rule truth.

**Rationale:** Reuses the existing authenticated paper boundary while making the cross-process contract explicit and preventing an exchange transport from entering this slice.

**Consequences:** OpenAPI and generated client entries are required for fixture GET and AI-cycle POST/status GET; no new operator configuration or external base URL is introduced. The API remains fail-closed unless a registry is injected. The deployed `paper_bootstrap.py` explicitly injects one built-in, credential-free synthetic bundle derived from `synthetic_config`; it does not load fixture files or market data. Its `loopback_host` parser keeps the regression test proving non-loopback rejection.

### Decision 2: Evidence identity and freshness

| Attribute | Value |
|---|---|
| **Status** | Accepted for this offline slice; parent live/research provenance remains out of scope |
| **Date** | 2026-11-20 |
| **Source** | Existing code evidence plus proposed contract |

**Context:** The AI universe has observation/expiry timestamps; strategy evidence currently accepts caller-supplied bars and labels its source unauthenticated; selector evaluation references are provenance metadata, not independently verified artifacts.

**Choice:** Bind each decision to a unique cycle ID, a canonical digest of the exact fresh fixture universe snapshot, the selected fixture symbol/rules version, market snapshot ID/time, strategy ID/version, and a server-issued expiry. For this offline slice, the only accepted evidence artifact is a deterministic, fixture-owned selector record: strategy metadata is registered as approved and paper-passed, and its evidence digest, OOS score/confidence/cost, expiry, supported regimes, sample count and ready signal are validated by the registry. The registry constructs `SelectionCandidate` from that record; request text cannot supply or alter it. This artifact is synthetic test evidence only and makes no claim of GitHub, live research, or online model provenance. The orchestrator builds the selector `MarketSnapshot` exclusively from the same registry bundle's per-symbol synthetic OHLCV bars and runs the existing `select_strategy(snapshot, candidates, registry, now_ms, ...)`. It permits continuation only for `selected`/`retained` output whose symbol and strategy ID/version match the AI intent and validated evidence; abstain, insufficient regime history, stale/future bars, missing evidence or identity mismatch stop before portfolio mapping. Require monotonic timestamps, no future times, exact fixture membership and expiry. Python recomputes digests over canonical validated payloads.

**Rationale:** Identity and freshness must survive the cross-language boundary and be checked again at admission; a prompt or caller cannot assert these properties.

**Alternatives Rejected:** Trusting the model's symbol, timestamps, confidence or evidence URL as authoritative — caller-controlled and replayable; accepting untrusted external source provenance as if the offline fixture had authenticated it.

**Consequences:** This closes the offline Build contract without claiming live research provenance. Extending beyond deterministic fixture artifacts requires a new Define/Design decision.

### Decision 3: Exposure-to-intent mapping and trusted account state

| Attribute | Value |
|---|---|
| **Status** | Accepted for the current synthetic fixture |
| **Date** | 2026-11-20 |
| **Source** | Existing `PositionExposure`, `TargetProposal`, `PaperSnapshot`, `RiskContext` contracts |

**Context:** Portfolio exposures are signed fractions, while `OrderIntent` requires Decimal quantity and limit price. Portfolio code intentionally has no account access; PaperAdmission owns reconciled synthetic state and risk context.

**Choice:** Let `E` be the current durable/native reconciled synthetic marked equity; `c` current signed exposure and `t` requested transition target, each as fraction of `E`. Convert the planner's finite exposure values once via canonical decimal text (`Decimal(str(value))`), then compute signed delta notional `(t-c) × E`; side is its sign; raw base quantity is `abs(delta_notional) / selected_limit_price`. Use Decimal for mapping and risk-bound inputs, round quantity down to fixture `size_increment`, and choose the conservative executable limit: BUY at the fixture ask rounded up to `price_increment`, SELL at the fixture bid rounded down; never use a UI price. Reject zero-after-rounding, below min quantity/notional, above max quantity, stale quote, mismatch of fixture symbol/rules, overflow, or unit ambiguity. For reversals, submit only reduce-to-zero, then take a new native/durable snapshot and rerun risk before increase. `PaperAdmission` remains the source of positions, reservations, equity, available margin and depth; caller balances/positions are forbidden. The integration submits only the exact mapped intent and expected admission generation.

**Rationale:** The exact quote, asset units, valuation numeraire, rounding direction and account snapshot must be owned by the engine and auditable. The existing paper fixture is fixed/synthetic; external market quotes must never be smuggled into OMS as account truth.

**Alternatives Rejected:** Let AI choose quantity/price; use DSH wallet/account state; map a research exposure directly to an order; or use floats / round-to-nearest — all leak trust or can increase risk.

**Consequences:** The current implementation is single-instrument, so Build must extend the fixture schema, runtime, worker and native OMS to accept a registry bundle with multiple arbitrary symbols. Tests inject distinct bundle definitions A/B and prove the AI can select different symbols and that the exact registered instrument is matched; no BTCUSDT/ETHUSDT production symbol list or automatic market discovery is added. A symbol absent from the active bundle is rejected.

### Decision 4: Durable admission, CAS, idempotency and restart

| Attribute | Value |
|---|---|
| **Status** | Accepted for this slice |
| **Date** | 2026-11-20 |
| **Source** | `DESIGN_PAPER_ADMISSION.md` and `admission_store.py` |

**Context:** AI decision writes already use local compare-and-swap; PaperAdmission uses durable session generation, risk decision, reservation, dispatch claim and stable native client-order ID. There is no transaction spanning plugin journal and Python database.

**Choice:** The first receipt transaction atomically inserts an immutable cycle header and a `claimed` append-only event keyed by `(environment, account_ref, request_id)`, with canonical payload/decision/fixture digests, unique worker owner token, generation and bounded lease deadline. SQLite `BEGIN IMMEDIATE`, the unique request constraint and event sequence constraint allow only one worker to claim. Same key and payload while the owner lease is active returns the current in-progress projection without appending or dispatching; a changed payload conflicts. Lease expiry never transfers ownership: it appends `protected` and requires recovery review. On process restart, the exclusive paper process lock proves the previous worker is gone; every nonterminal claim is appended as protected before serving requests. Abstain, stale, mismatch, mapping and risk rejection write terminal no-order events and never create a fake command. A real mapped intent passes through existing `PaperAdmission`; its risk decision/reservation and the separate command binding are committed with generation CAS before dispatch claim. Only the one successful claim may dispatch the stable `native_client_order_id`. Native observations and terminal events are appended before being returned. A nonterminal or dispatch-claimed outcome after uncertainty remains protected/unknown and is never resubmitted; no exactly-once claim beyond this idempotency boundary is allowed.

**Rationale:** The plugin and engine stores cannot provide a cross-database atomic transaction, so stable idempotency keys plus read-after-timeout resolution are needed to avoid duplicate simulated orders.

**Alternatives Rejected:** Retrying with a fresh request ID; resubmitting on timeout; treating a local AI receipt as OMS admission; or replaying unsettled commands on restart.

**Consequences:** Migration `0006_ai_paper_decision_binding` adds a cycle request header table and append-only cycle event table plus the command-only decision binding table; all are represented in shared Alembic metadata. Claim events record owner token, generation and lease deadline; non-claim events leave these columns null. Receipt rows are immutable; status is a projection of ordered events, not an overwritten field. The unique cycle key is `(environment, account_ref, request_id)` and the stored canonical digest must match for replay; command bindings exist only for actual admission and retain unique command/native IDs. Keep legacy `ExecutionCommand` unchanged. Build tests unique-key/thread races, one owner, payload conflicts, event ordering/append-only semantics, expired lease protection without takeover, downgrade/restore under `tmp_path`, metadata-head and legacy queries, and restart at pre-admission, post-admission and post-dispatch-claim boundaries. Existing paper restart protects rather than reconstructs unsettled state.

### Decision 5: Abstain, stale, timeout and retry stop rules

| Attribute | Value |
|---|---|
| **Status** | Accepted for this slice |
| **Date** | 2026-11-20 |
| **Source** | Parent Define safety constraints and existing fail-closed boundaries |

**Context:** An autonomous loop may retry after network or storage errors, but the component chain contains non-idempotent state transitions.

**Choice:** `abstain`, empty candidate set, unavailable/unverified evidence, stale/future snapshots, expired decision, selector rejection, no-op/under-step target, or risk rejection ends this cycle with a durable typed outcome and no dispatch. Use at most one read-only refresh before an admission request exists. Set the offline defaults to a 5,000 ms absolute cycle deadline, one read-only refresh, and one same-key resolution attempt; all later failures stop and protect. Retries may reuse only the exact request key and payload digest after `get_by_request`; never mint a replacement key. Any persistence/CAS conflict, identity mismatch, risk-context expiry, timeout with unknown dispatch status, native event gap or dirty restart stops and protects; no blind retry or automatic flatten.

**Rationale:** Retry is safe only before side effects or through idempotent resolution; stale decisions cannot be repaired by replaying old evidence.

**Alternatives Rejected:** Infinite retry, retry with stale snapshot, or model-directed retry policy.

**Consequences:** The defaults are testable and conservative for this offline fixture. A production/live environment requires a separate Define and cannot inherit these values silently.

## File Manifest

The Build modifies only the files in this manifest. Every planned handwritten source file must remain below 500 lines. `paper_bootstrap.py` injects the built-in credential-free fixture registry; its loopback parser remains covered by an isolated regression test.

| # | File | Action | Purpose | Dependencies |
|---:|---|---|---|---|
| 1 | `contracts/schemas/ai-paper-decision.v1.json` | Create | Strict cross-language fixture snapshot (bounded OHLCV + selector evidence), decision and receipt envelope; request never carries authoritative quote/rules/bars/evidence | None |
| 2 | `python/apps/quant-engine/src/quant_engine/synthetic_fixture_registry.py` | Create | Sole Python owner of immutable multi-symbol bundles, per-symbol OHLCV/evidence, complete canonical pairwise synthetic correlation matrix, digest and lookup | 1, 3, 4 |
| 3 | `python/apps/quant-engine/src/quant_engine/ai_paper_contracts.py` | Create | Strict DTOs, evidence/digest/identity/freshness validation and received/claimed/protected/rejected terminal outcomes | 1, 2 |
| 4 | `python/apps/quant-engine/src/quant_engine/paper_config.py` | Modify | Build internal-paper config from an explicitly injected registry bundle; remove single-instrument assumption only in the scoped profile and preserve existing non-scoped behavior | 2 |
| 5 | `python/apps/quant-engine/src/quant_engine/paper_context.py` | Modify | Convert registry-owned bars and exact correlation matrix into selector inputs and reconciled independent `RiskContext` | 2, 4, 6 |
| 6 | `python/apps/quant-engine/src/quant_engine/paper_order_mapper.py` | Create | Decimal target-delta mapping against registry rules and trusted synthetic state | 3, 5 |
| 7 | `python/apps/quant-engine/src/quant_engine/paper_cycle_service.py` | Create | Decision intent→existing selector over bound symbol bars and validated evidence→strategy identity match→portfolio→mapper→PaperAdmission; fixture re-resolution and idempotent request binding. This module is also the AI-cycle service adapter; do not add a forwarding orchestrator module. | 3, 5, 6, 8, 50 |
| 8 | `python/apps/quant-engine/src/quant_engine/paper_admission.py` | Modify | Add exact-payload idempotent get-or-submit and receipt correlation where existing API is insufficient | 3, 7, 9 |
| 9 | `python/packages/quant-data/src/quant_data/admission_store.py` | Modify | Persist unique decision/request digest binding and conflict-safe lookup | 7, 8 |
| 10 | `python/packages/quant-data/alembic/versions/0006_ai_paper_decision_binding.py` | Create | Additive immutable cycle-header/event receipt tables with atomic claim owner/generation/deadline plus command-only decision binding; downgrade and isolated backup/restore coverage | 9 |
| 11 | `python/apps/quant-engine/src/quant_engine/paper_api_models.py` | Modify | Strict fixture snapshot, AI-cycle request and receipt DTOs | 1, 2, 3 |
| 12 | `python/apps/quant-engine/src/quant_engine/paper_api.py` | Modify | Add authenticated observe `GET /api/v1/trading/fixtures/{fixture_id}`, control `POST /api/v1/trading/ai-cycles`, observe request status GET | 2, 7, 11 |
| 13 | `contracts/openapi/quant-paper.v1.json` | Modify | Regenerate canonical internal-paper schema for fixture GET and AI-cycle routes from `create_paper_app` | 11, 12 |
| 14 | `packages/ts/quant-api-client/src/generated/paper-paths.ts` | Modify | Generated exact paper API route types | 13 |
| 15 | `packages/ts/quant-api-client/src/generated/paper-schema.ts` | Modify | Generated fixture/decision/receipt schemas for paper API | 13 |
| 16 | `packages/ts/quant-api-client/src/validation.ts` | Modify | Runtime validation for generated response payloads | 14, 15 |
| 17 | `packages/ts/quant-api-client/src/paper.ts` | Modify | Add typed fixture/AI-cycle API methods to existing authenticated paper client | 14, 15, 16 |
| 18 | `apps/dsh-plugin/src/lib/engine.ts` | Modify | Fixed loopback client, capability scopes, bounded deadline and same-key status resolution | 17 |
| 19 | `apps/dsh-plugin/src/lib/ai-scheduler.ts` | Modify | Permit only `internal_paper` for this profile and enforce bounded stop rules | 18 |
| 20 | `apps/dsh-plugin/src/lib/ai-universe.ts` | Modify | Read Python registry snapshot/digest; preserve separate dashboard provider behavior | 18, 19 |
| 21 | `apps/dsh-plugin/src/host-runtime.ts` | Modify | Inject one loopback fixture provider into scoped AI runtime without Host-owned fixture data | 20 |
| 22 | `apps/dsh-plugin/src/host-tools-ai.ts` | Modify | Use registry candidates; never invoke Bybit UniverseSource in `internal_paper` | 20, 21 |
| 23 | `apps/dsh-plugin/src/host-tools-watchlist.ts` | Modify | Preserve dashboard/watchlist as view-only and prevent filter leakage into decision request | 21 |
| 24 | `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v5.ts` | Modify | Explain dynamic registry candidates, abstention and simulated receipt semantics | 19, 22 |
| 25 | `python/apps/quant-engine/tests/test_ai_paper_contracts.py` | Create | Strict identity, digest, stale/future, candidate, evidence exclusion and replay contract cases | 3 |
| 26 | `python/apps/quant-engine/tests/test_synthetic_fixture_registry.py` | Create | Bundle A/B, digest binding, complete pair coverage, canonical direction, coefficient bounds, freshness and lookup | 2 |
| 27 | `python/apps/quant-engine/tests/test_paper_order_mapper.py` | Create | Decimal rounding, limits, quote freshness, funds/depth and unsupported-symbol cases | 6 |
| 28 | `python/apps/quant-engine/tests/test_ai_paper_orchestrator.py` | Create | End-to-end selector→planner→independent risk→CAS→matching native fixture integration for bundles A/B | 7, 8, 32–36 |
| 29 | `python/apps/quant-engine/tests/test_ai_paper_recovery.py` | Create | Concurrent single-owner claim, replay/conflict/lease expiry/restart and `tmp_path` migration isolation, network denial, rollback or restore | 7–10 |
| 30 | `python/apps/quant-engine/tests/test_fixture_registry_api.py` | Create | Authenticated loopback snapshot exposes deterministic fixture evidence; POST cannot supply it | 11, 12 |
| 31 | `python/apps/quant-engine/tests/test_paper_bootstrap_loopback.py` | Create | Assert `loopback_host` accepts loopback and rejects non-loopback; bootstrap provisioning remains credential-free | `paper_bootstrap.py` |
| 32 | `python/packages/quant-execution/src/quant_execution/paper_models.py` | Modify | Represent multiple registered instruments and symbol-bound synthetic orders/events/snapshots | 2 |
| 33 | `python/packages/quant-execution/src/quant_execution/paper_runtime.py` | Modify | Manage one continuous multi-instrument synthetic session from the registered bundle | 32, 34–35 |
| 34 | `python/packages/quant-execution/src/quant_execution/paper_worker.py` | Modify | Route commands/events by registered symbol in isolated native worker | 32, 35 |
| 35 | `python/packages/quant-execution/src/quant_execution/paper_native.py` | Modify | Match each order only against that symbol's registered finite depth/rules | 32 |
| 36 | `python/packages/quant-execution/tests/test_paper_runtime.py` | Modify | Multi-symbol startup, symbol routing, bundle mismatch and recovery regression | 32–35 |
| 37 | `python/packages/quant-execution/tests/test_native_execution.py` | Modify | Matching instrument and finite-depth behavior for arbitrary registered symbols | 32, 35 |
| 38 | `apps/dsh-plugin/test/ai-paper-cycle.ts` | Create | Typed decision/no-network boundary, registry identity, environment gate, abstention and timeout | 18–24 |
| 39 | `apps/dsh-plugin/test/ai-universe.ts` | Modify | Candidate pool equals Python fixture response; bundle identity and fail-closed behavior; no Bybit call | 19–22 |
| 40 | `apps/dsh-plugin/test/integration.ts` | Modify | Bundle A/B selection reaches API; UI symbol/timeframe never enters request; dashboards remain functional | 20–23, 38–39 |
| 41 | `python/packages/quant-portfolio/src/quant_portfolio/models.py` | Modify | Apply shared safe exchange-style symbol syntax to portfolio positions and proposals, preserving BTCUSDT | AT-019 |
| 42 | `python/packages/quant-portfolio/tests/test_models.py` | Create | Accept ALPHA-PERP/BETA.PERP/GAMMA_1/BTCUSDT; reject lowercase, repeated/edge separators, whitespace/control/path input | 41 |
| 43 | `sdd/reports/BUILD_REPORT_AI_TO_SYNTHETIC_PAPER.md` | Create | Actual command exits, tests, migration isolation/restore, manifest digest and parent-scope limitations | 1–42 |
| 44 | `python/packages/quant-data/tests/test_migrations.py` | Modify | Extend existing Alembic head table/metadata assertions and verify 0006 upgrade/downgrade plus legacy ORM query compatibility using isolated tmp_path SQLite | 10, 45 |
| 45 | `python/packages/quant-data/src/quant_data/models.py` | Modify | Map cycle header/events (including nullable claim owner/generation/deadline) and command-only decision binding; preserve `ExecutionCommand` columns and compatibility | 10 |
| 46 | `python/packages/quant-data/tests/test_command_ledger.py` | Modify | Advance its fixture's expected Alembic head to 0006 while keeping the existing command-ledger table and semantic regression checks | 10, 44 |
| 47 | `python/packages/quant-execution/src/quant_execution/fixtures.py` | Modify | Make shared instrument construction accept only the same safe uppercase exchange-style symbol grammar used by fixture registry/portfolio | 35, 41 |
| 48 | `python/packages/quant-execution/tests/test_catalog_compatibility.py` | Modify | Verify ALPHA-PERP/BETA.PERP/GAMMA_1 and legacy symbols construct; reject lowercase, separator, whitespace and path injection forms | 47 |
| 49 | `python/apps/quant-engine/tests/test_admission.py` | Modify | Extend isolated SQLite/native admission integration with explicit pairwise fixture assumptions, two-symbol risk evaluation, per-symbol quote/position reconciliation and total exposure accounting | 4, 5, 8, 32–36 |
| 50 | `python/packages/quant-data/src/quant_data/cycle_receipt_store.py` | Create | Keep immutable cycle header and append-only event DAO under 500 lines; atomic single-owner claim, lease-expiry protection, exact-key replay/conflict and latest receipt projection | 45 |

**Total Files:** 50 (49 implementation/test paths plus one Build report; Define and Design are phase artifacts and outside the Build manifest.)

**Per-file verification mapping:** 1–3 are checked by 25 and 26; 4–10 by 28–29 and 44–46; 11–17 by 25, 28 and 30 plus `pnpm exec nx run quant-engine:openapi-check` and `pnpm --filter @bybit-quant/quant-api-client generate:check`; 18–24 by 38–40; 25–31 and 44/46 are focused contract/registry/API/isolation/migration tests; 32–37 by 28, 36 and 37; 38–40 are plugin tests; 41–42 and 47–48 by shared symbol contract tests; 43 is checked against actual command output, test count and manifest digest; 45 is checked by Alembic head metadata comparison; 49 exercises actual two-symbol admission and preserves risk rejection when correlation evidence is missing. `quant-engine.v1.json` remains the readonly engine contract and is regenerated by the same Nx target; the new paper routes are generated only into `quant-paper.v1.json` and `paper-*` SDK files. AT-016 requires bundle A/B to expose different allowed symbols and the AI to select a different eligible symbol in each, with matching synthetic OMS routing. Test 31 exercises the unchanged bootstrap parser. No item permits exchange order writes, host-supplied market truth, or fallback from registry fixtures to a venue provider.

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1–43 | Cross-language contracts and native lifecycle require one accountable Build owner with independent review. |

**Agent Discovery:** Not applicable to the bounded Build manifest; execution ownership is assigned by the parent agent.

## Code Patterns

### Pattern 1: Strict immutable input envelope (illustrative contract, not an existing API)

```python
class DecisionEnvelope(PaperModel):
    environment: Literal["internal_paper"]
    cycle_id: Opaque
    decision_id: Opaque
    universe_digest: Sha256
    snapshot_ids: tuple[Opaque, ...]
    evidence_digest: Sha256
    expires_at_ms: PositiveInt
```

### Pattern 2: Deterministic Decimal mapping core

```python
delta_notional = (target_exposure - current_exposure) * reconciled_equity
side = "buy" if delta_notional > 0 else "sell"
raw_quantity = abs(delta_notional) / limit_price
quantity = round_down_to_step(raw_quantity, fixture.size_increment)
if quantity <= 0 or quantity < fixture.min_quantity:
    return MappingRejected("below_minimum_quantity")
```

The names above describe the proposed contract. Build must adapt to actual Pydantic/quant-risk APIs and must not introduce guessed fields or import cycles.

## LLM Prompts

The parent Define sets `LLM Prompts: true`. This slice consumes an existing DSH-injected model and does not choose a provider/model. It must not ask the model to authorize an order, supply account truth, decide retry safety, or issue an OMS command.

| ID | Name / path / version | Type / consumer | Input → output | Closed decisions and fallback | Reference material | Completeness / refactor |
|---|---|---|---|---|---|---|
| LP-001 | Background research/decision loop / `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v5.ts` (planned successor) | `loop`; existing AI scheduler | Fresh universe and bounded evidence → candidate decision or abstain, with evidence references | Model chooses zero or more candidates/parameters; code verifies eligibility, identity, freshness, risk and all side effects; any missing evidence abstains | Parent DEFINE AT-033–036; current v4/v5 specs and this design contract | Update only after contract/Define closes; no prompt can authorize retry or claim durable admission |

### Contract by prompt

| ID | Tone / audience | Output type | Approved fallback | Autonomous? | Internal verification | Minimum pre-ship evaluation |
|---|---|---|---|---|---|---|
| LP-001 | Concise, tool-oriented | Existing structured tool-mediated decision; no free-form order payload | Empty decision/abstain on unavailable, stale, ambiguous or unsupported evidence | Yes, bounded by existing scheduler and code-owned gates | Strict parser, exact candidate/evidence match, server snapshot checks, independent risk and durable admission | Deterministic fixture assertions plus independent review of stale, unsupported, contradictory and abstain cases; no profitability claim |

## Data Flow

```text
1. Python `SyntheticFixtureRegistry` registers exactly one immutable bundle for `internal_paper`;
   it contains arbitrary eligible symbols, per-symbol deterministic OHLCV history, current
   market snapshots, bid/ask/depth and precision/rules.
   Host `ai-universe.ts` reads the authenticated fixture snapshot/digest and assigns
   cycle/snapshot identity and expiry. No second provider or venue fallback is allowed.
   No Bybit or other exchange market-data request is made in this slice.
   Failure/incomplete discovery → terminal no-action cycle; no static fallback.
   │
   ▼
2. AI returns candidate choice/strategy thesis/parameters or abstains. Host validates choice
   against that exact universe; decision CAS persists the local simulation decision and receipt.
   │
   ▼
3. Host/engine sends strict decision envelope with snapshot/evidence digests. Engine checks
   cycle identity, time bounds, evidence availability, registry approval and replay binding.
   │
   ▼
4. Python resolves the selected symbol's bars from the same registry digest and evaluates the
   existing selector with that fresh `MarketSnapshot`, validated candidates and `StrategyRegistry`.
   Selector abstention, insufficient/stale/missing bars, or a strategy/symbol mismatch with the
   AI intent → typed receipt, no mapper/admission call. Only a matching selected/retained result
   becomes a strategy-backed portfolio proposal; the planner computes transitions against a
   reconciled internal-paper snapshot.
   │
   ▼
5. For one transition step, mapper uses trusted native/durable equity and current exposure,
   fixture quote and instrument rules to derive exact Decimal intent. Unsupported symbol,
   stale quote, precision/funds/minimum failure → typed rejection, no order. The limit is
   marketable at ask/bid; native matching consumes only the displayed finite fixture size.
   Excess quantity stays partially filled/open until a later explicit fixture depth update;
   this slice never fetches or auto-refreshes a quote.
   │
   ▼
6. PaperAdmission re-reconciles current state and independently calls risk evaluator. Risk
   rejection is durable and terminal. Approval is persisted with generation CAS/reservation.
   │
   ▼
7. AdmissionStore claims dispatch once with stable client-order-id; PaperRuntime sends the
   command to the synthetic native OMS. Native event is durably ingested before receipt update.
   │
   ▼
8. Host records distinct AI decision and paper-admission/native lifecycle receipts. On timeout
   query the same request key; on uncertain restart or event gap protect and stop.
```

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| DSH injected Agent model | Existing Host runtime / tool loop | Harness-managed injection; no provider secret reaches new code | Inbound untrusted decision | Scheduler deadline; invalid output/timeout → abstain; never retry a side effect. Tests use typed fixtures/no-network stub; model-provider network isolation is not proven by this slice |
| Python quant engine | Existing authenticated loopback paper API, versioned strict DTO | Existing scoped capability via process-private FD; no credential copied into prompt or request | Bidirectional | Bounded timeout; resolve exact same request ID; unknown outcome → protected state |
| SQLite/Alembic admission database | Existing durable store; new additive migration only if needed | Process owner/session scope and adjacent file lock | Bidirectional | No implicit startup migration; persistence failure freezes admission; all tests create DB under pytest `tmp_path`, assert resolved path is beneath that root, deny network, and exercise upgrade plus downgrade or backup/restore preservation; application-configured/shared DB is never opened |
| Nautilus synthetic PaperRuntime | Existing private process/IPC facade | Parent/child process boundary; no exchange credentials | Bidirectional | Missing process/event continuity protects; no replay of uncertain dispatch |
| Isolated synthetic fixture source | One Python-owned immutable registry bundle read by Host and consumed by mapper/native OMS | Existing authenticated loopback read; no external network | Candidate, market/depth/rules snapshot and digest | Missing/stale/incomplete fixture means abstain; no exchange refresh/fallback; every stage verifies the same bundle digest |

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Canonical digest, identity, candidate membership, expiry/future/stale rejection, unknown fields, unsupported strategy/evidence | `python/apps/quant-engine/tests/test_ai_paper_contracts.py` | `uv run --project python --locked pytest ... -q` | Every invalid/ambiguous case rejects before planner/admission |
| Unit | Exposure delta conversion, Decimal-only sizing, buy/sell tick rounding, quantity step, min/max quantity/notional, zero delta, insufficient fixture funds/depth, stale/mismatched fixture quote | `python/apps/quant-engine/tests/test_paper_order_mapper.py` | pytest + Ruff + Pyright | Exact expected Decimal intent or stable rejection; no float use |
| Integration | AI envelope→selector→planner→mapper→real independent risk evaluator→temporary SQLite AdmissionStore CAS→native isolated fixture OMS; risk rejection and admitted path | `python/apps/quant-engine/tests/test_ai_paper_orchestrator.py` | pytest `tmp_path` DB; assert `db.resolve().is_relative_to(tmp_path.resolve())`; monkeypatch/deny socket and HTTP transports | No network/account dependency; durable decision/risk/event ordering verified |
| Recovery / concurrency / migration | Same-key/same-payload replay, same-key/changed-payload conflict, concurrent generation conflict, timeout then read-by-request, crash at persistence/dispatch boundary, event gap and protected restart; upgrade then downgrade or backup/restore preservation | `python/apps/quant-engine/tests/test_ai_paper_recovery.py` | pytest `tmp_path` DB only; path assertion; network denied; never read application DB config | At most one native dispatch; migration preserves data or restores exact backup; ambiguity remains protected; no false exactly-once claim |
| Plugin unit | Prompt boundary, stale/abstain/timeout, decision receipt vs OMS receipt, duplicate-cycle behavior | `apps/dsh-plugin/test/ai-paper-cycle.ts` | `pnpm --dir apps/dsh-plugin run verify` | No blind retry or simulated-decision-as-order wording |
| Host provider/regression | Internal-paper provider injection, no call to Bybit `UniverseSource`, scheduler rejects testnet/demo/live, identical fixture digest reaches Python/native OMS; dashboard/watchlist filters do not change the AI fixture; existing read-only views remain functional | `apps/dsh-plugin/test/ai-paper-cycle.ts`, `apps/dsh-plugin/test/ai-universe.ts`, and `apps/dsh-plugin/test/integration.ts` | `pnpm --dir apps/dsh-plugin run verify` | All scoped transport/provider calls are fixture-local; view-only regression assertions pass |
| Static / migration | Format, lint, typecheck, Alembic upgrade/downgrade and temporary DB restore round trip | Manifest source/tests and migration | `pnpm run python:lint`, `pnpm run python:typecheck`, `pnpm run python:test`; migration fixture commands to be frozen in Define | All exits 0; restored data and digests match; no production DB touched |
| Verify Gate | Full scoped contract and root gates; official Plugin Manager, SBOM/dependency and secret scan are separate acceptance evidence | Build report | `pnpm run verify`, `pnpm run python:lint`, `pnpm run python:typecheck`, `pnpm run python:test`, security/SBOM/secret scan commands | Record actual command, exit and limitations; no Mainnet/Testnet connection/order |

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Empty/incomplete AI universe | Catalogue/ticker completeness or zero eligible candidates | Record no-action cycle outcome | No same snapshot; at most one fresh read-only cycle within budget | `universe_unavailable` counter and snapshot digest |
| Invalid, stale, future or mismatched decision/evidence | DTO validation, digest, identity, expiry checks | Reject before selector/admission; preserve source receipt | No; new cycle required | Stable typed reason; IDs/digests only |
| Selector abstention or unapproved strategy | Existing selector decision/lifecycle gate | Terminal no-order receipt | No | Strategy ID/version, status/reason |
| Stale/mismatched paper snapshot or fixture | Native/durable generation and quote/rule comparison | Reject mapping and re-read only before admission if cycle valid | One bounded refresh before request creation; otherwise stop | Snapshot age/generation and rejection code |
| Precision/minimum/depth/available margin rejection | Mapper and independent risk evaluator | Persist risk/mapping rejection; do not increase size automatically | No same proposal; new AI cycle needed | Stable code and bounded numeric context, never secrets |
| CAS conflict / duplicate ID | AdmissionStore uniqueness/generation | Resolve exact existing request; changed payload conflicts | Read-only lookup only | Decision/request ID and expected/current generation |
| Timeout or persistence failure | Deadline, API exception, store error | Query exact request; if unresolved protect/freeze and surface unknown | No new request ID; exact-key resolution only | `unknown_outcome`/protected state, native process health |
| Native event gap or dirty restart | Event stream completeness/session cleanliness | Protect; preserve commands/receipts; require explicit new isolated session | No replay | Readiness false, gap and session state |

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| Cycle deadline | immutable positive integer | Test-injected constant `5000` ms | No | Absolute end-to-end cycle deadline; no new operator setting |
| Read refresh count | immutable integer | Test-injected constant `1` | No | Maximum read-only fixture refresh before request creation |
| Same-key lookup count | immutable integer | Test-injected constant `1` | No | Maximum status resolution after timeout |
| Fixture/session IDs | opaque fixture values | Injected by isolated test fixture / existing internal paper session | No | No configurable provider or fallback; must match registered local fixture |
| Capability | inherited process-private descriptor | Existing paper service mechanism | Yes | Read from capability FD and never copied to logs, prompt, configuration or model context |

## Security Considerations

- `internal_paper` and fixture mode are literal server-owned constants; requests cannot choose environment, account, policy, balance, quote, instrument limits, leverage or arbitrary metadata.
- All model output, market data, evidence references, and cross-language payloads are untrusted. Strict schemas, canonical digests, bounded lengths and identity binding are mandatory.
- Any eventual live Bybit universe and this synthetic OMS fixture universe are different; this slice supplies only the latter. A discovered symbol without a matching configured native fixture is rejected, never silently routed to a venue or substitute symbol.
- `quant_risk.evaluate` independently checks exact intent against current server-owned identity, equity, margin, market/depth, open positions/reservations, precision, concentration and configured limits. Mapping is not approval.
- No exchange credentials/network client/API endpoint is imported by the orchestrator; tests assert no external transport and use temporary DB + fixed fixture only.
- Migrations are additive, reviewed, backup/restore tested and never run implicitly by the service. Every test DB is created inside pytest `tmp_path`, its resolved location is asserted, network is denied, and the suite proves upgrade plus rollback or backup/restore; no application-configured DB path is read. No upgrade may drop decision/strategy/history/audit records.
- Cycle and request IDs do not contain secrets or user-provided unbounded strings. Logs redact capability and input payloads.

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | Structured stage event with cycle/decision/request IDs, snapshot digest prefix, generation, stable outcome code | Trace one decision to durable synthetic receipt without logging raw prompt, secrets or full user data |
| Metrics | Counts by outcome: abstain, stale, unsupported fixture, mapping reject, risk reject, admitted, unknown/protected; latency by stage; queue depth | Show where safe cycles stop and detect backlog/slow dependencies |
| Tracing | Correlation ID propagated from DSH cycle to Python request and native client-order-id | Diagnose contract and persistence boundaries while preserving correlation across restart |
| Recovery health | Existing native-process/event-stream/readiness plus admission generation and unresolved command count | Readiness must become false on gap, uncertain dispatch, persistence error or dirty restart |

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| Parent AT-019 strategy evidence/selection | Decision 2; selector stage | Contract + selector tests; current evidence endpoint alone is insufficient |
| Slice AT-017/018: AI strategy intent is checked against bar-driven selector output | Decision 2; registry bars and orchestrator selector gate | Fresh/insufficient/missing-bars tests; mismatch/abstain assert no mapper/admission |
| Parent AT-020 target exposure/transition | Decision 3; planner and mapper | Decimal mapper + end-to-end fixture test |
| Parent AT-021 independent deterministic risk veto | Decision 3; PaperAdmission remains authority | Risk rejection integration asserts no native dispatch |
| Parent AT-029 durable decisions/orders/audit | Decision 4; store binding and receipts | Migration/ledger/recovery tests and backup restore |
| Parent AT-033/034/035 AI-selected dynamic universe and fail-closed discovery | Decision 2; Host universe stage | Plugin tests assert dynamic membership, incomplete/no-universe abstention |
| Parent AT-036 strategy evidence is research-only | Decision 2; evidence validation | Test verifies no evidence alone can enter mapper/admission |
| AGENTS Mainnet off, no Testnet bypass; this slice internal paper only | Decision 1 and Security | Environment/transport boundary tests; no network or account tests |
| AI CAS plus durable idempotency and restart protection | Decision 4 | Concurrency, same-key, crash-boundary tests |

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Research evidence has caller-controlled provenance | Invalid strategy could reach target planning | Require trusted artifact registry/digest verification and approved lifecycle; otherwise abstain | Producer/signature contract is not implemented or specified yet |
| Fractional exposure denominator differs from paper/native valuation | Wrong size despite correct arithmetic | Engine-owned reconciled marked equity and common quote currency; independent risk re-evaluation | Fixture accounting/spec must be confirmed |
| Dynamic market universe exceeds current synthetic fixtures | AI selection cannot be admitted | Explicit registry capability check; reject unsupported symbol; bundle A/B tests prove multi-symbol replacement | Full live/venue universe remains out of scope |
| Cross-store atomicity absent | AI receipt and OMS receipt can diverge | Separate receipts, durable idempotency binding, exact-key lookup and protected ambiguity | Requires schema/migration and backup contract review |
| Retry after timeout duplicates simulated order | Duplicate native dispatch | Never create new key; resolve same key and dispatch once via claim CAS | Process crash at native boundary still requires protection, not exactly-once guarantee |
| Parent Define describes wider Testnet/full product | Slice may be mistaken for acceptance | Mark as prerequisite only; map tests narrowly and retain unchecked parent gates | Full architecture and release remain unproven |

## Build Closure and Remaining Parent Gaps

The following decisions are closed for this Build: internal_paper only; Python-owned registry bundles with arbitrary multi-symbol synthetic fixtures; deterministic built-in fixture evidence with SHA-256 digest; 5,000 ms cycle deadline; one read-only refresh; one same-key resolution attempt; Decimal exposure mapping against engine-owned marked equity; conservative ask/bid limit selection; finite fixture depth with native partial fills and no automatic quote refresh; stale/unknown outcomes protect.

The following remain parent-product gaps and are deliberately not blockers for this offline slice: deployed fixture provisioning for an unattended service, live strategy artifact provenance, venue-backed dynamic universe, Bybit private/Testnet/Mainnet execution, official Plugin Manager lifecycle, full DSH lifecycle, production monitoring/SBOM/release and complete architecture-brief §§1–26 acceptance.

## Advisor Ledger

None — no formal external design review.

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.1 | 2026-11-20 | SDD Design by RDD | Aligned to the dedicated Define, closed offline fixture defaults, removed Define from Build manifest, and clarified fixture depth matching. |
| 1.2 | 2026-11-20 | SDD Design by RDD | Closed Host-source drift: one injected fixture bundle for the internal-paper path, scheduler environment gate, explicit dashboard-provider non-regression, and no claim that Harness LLM execution is offline; expanded exact Host/test manifest. |
| 1.3 | 2026-11-20 | SDD Design by RDD | Fixed exact loopback POST/GET routes and capability scopes, removed unimplemented operator config names in favor of test-injected constants, specified tmp_path/network-denied migration gates, and corrected Manifest rationale count. |
| 1.4 | 2026-11-20 | SDD Design by RDD | Resolved fixture ownership drift: Python registry is the sole source, the API exposes its read-only snapshot, arbitrary multi-symbol bundles drive matching native instruments, and the precise Manifest covers multi-symbol OMS plus unchanged bootstrap loopback guard. |
| 1.5 | 2026-11-20 | SDD Design by RDD | Added the existing Alembic migration-suite gate and its metadata model mapping to the Manifest; preserve the legacy ExecutionCommand ORM and test migration upgrade/downgrade plus old-query compatibility. |
| 1.6 | 2026-11-20 | SDD Design by RDD | Added the quant-data command-ledger regression test because its fixture pins the Alembic head; update only the expected revision while retaining all ledger behavior assertions. |
| 1.7 | 2026-11-20 | SDD Design by RDD | Added the existing shared instrument factory and compatibility test to ensure fixture registry symbols accepted by the grammar are also representable by the native synthetic OMS. |
| 1.5 | 2026-11-20 | SDD Design by RDD | Resolved OpenAPI source drift: internal-paper routes belong to the existing separate `quant-paper.v1.json` generated from `create_paper_app`; the Nx target already serializes both contracts; generated TS artifacts are the existing paper-specific files/client. |
| 1.6 | 2026-11-20 | SDD Design by RDD | Resolved selector-input drift: fixture bundles and canonical digest now include deterministic per-symbol OHLCV bars; the orchestrator runs the actual selector and rejects/abstains unless its strategy identity matches the AI intent; missing/stale/insufficient bars stop before mapping. |
| 1.7 | 2026-11-20 | SDD Design by RDD | Closed receipt durability drift: immutable cycle request header plus append-only ordered events now cover no-order outcomes; command binding remains admission-only, and restart never fabricates or replays uncertain commands. |
| 1.8 | 2026-11-20 | SDD Design by RDD | Added cohesive receipt DAO and cycle service modules to keep handwritten sources below the 500-line repository limit while preserving the receipt contract. |
| 1.9 | 2026-11-21 | SDD Build follow-up | Consolidated the decision orchestrator and AI-cycle service adapter at `paper_cycle_service.py`; avoids a shallow duplicate module while preserving the selector→portfolio→mapper→admission boundary. |

## Next Step

Execute o **SDD Build by RDD**.
