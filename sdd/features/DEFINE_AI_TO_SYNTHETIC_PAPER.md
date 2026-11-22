# DEFINE: AI decision to durable synthetic-paper admission

> Define a bounded, offline-only vertical slice from an AI decision through strategy selection, portfolio planning, independent risk and durable synthetic-paper admission.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | AI_TO_SYNTHETIC_PAPER |
| **Date** | 2026-11-20 |
| **Author** | SDD Define by RDD |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

This Define is a prerequisite slice of the complete Bybit AI Quant platform. It does not claim a complete DSH unattended trader, Testnet/Mainnet capability, official Plugin Manager lifecycle, or production readiness. The authoritative architecture brief is `/Users/litlesnow/.codex/attachments/886f3b36-5cab-4ba1-bb1c-7ef525af0e6e/pasted-text-1.txt` (read 2026-11-20, 1,974 lines). The companion design is `sdd/features/DESIGN_AI_TO_SYNTHETIC_PAPER.md`.

## Problem Statement

The repository has separate AI decision, Python selector, portfolio, risk and synthetic paper admission components, but no verified contract connecting them. Without this slice, a research decision cannot be shown to become a correctly sized, independently vetoable, durable internal-paper command while preserving stale-data, replay, timeout and restart safety.

## Target Users

| User | Role | Pain Point |
|---|---|---|
| Project owner/operator | Audits and maintains the quant platform | Cannot verify that AI evidence reaches the synthetic OMS without bypassing deterministic risk or losing durable audit identity. |
| DSH user in an offline test profile | Reviews AI research and simulated outcomes | Needs clear abstention, rejection and receipt states; dashboard filters must not secretly choose or size a decision. |

## Goals

| Priority | Goal |
|---|---|
| **MUST** | Define a strict, versioned `DecisionTrack` envelope bound to cycle, candidate-universe digest, market/evidence snapshot identities, expiry and strategy provenance. |
| **MUST** | Connect validated decision → Python strategy selector → account-free `PortfolioPlan` → Decimal exposure mapper → independent `RiskDecision` → `AdmissionStore` generation CAS → synthetic native OMS, using only isolated internal-paper fixtures. |
| **MUST** | Use engine-owned reconciled synthetic equity, positions, quote, precision, depth and policy; reject stale/missing/inconsistent data, unsupported fixtures, precision/funds/risk violations and unknown outcomes. |
| **MUST** | Make repeated identical requests idempotent through deterministic request identity, payload-digest conflict detection, stable client-order-id and durable receipt correlation; protect on uncertain timeout or restart. |
| **MUST** | Keep DSH dashboard symbol/category/timeframe controls view-only; AI chooses eligible symbols and parameters or abstains from the fresh universe. |
| **SHOULD** | Preserve append-only decision, risk, admission and native-event audit links across a controlled migration and backup/restore test. |
| **MUST** | Select among multiple arbitrary symbols in Python-owned isolated fixture bundles; tests must substitute bundles A and B with different arbitrary symbols, prices, depth and rules, the AI must be able to select a different eligible symbol from each bundle, and that exact symbol must reach its matching synthetic OMS instrument. No production symbol list is hardcoded. |
| **MUST** | Include deterministic synthetic OHLCV bars per fixture symbol in the same registry bundle. The engine shall run the existing Python selector over those bars and validated strategy candidates; it shall admit an AI intent only when the selector returns a valid strategy matching the AI `strategy_id` and symbol. Missing, stale, mismatched, or insufficient bars shall terminate as abstain/reject before mapping. |
| **MUST** | Evaluate every open position and pending reservation across the registered symbols with the existing independent risk evaluator. A multi-symbol fixture bundle shall carry exactly one explicit finite correlation coefficient for every unordered symbol pair; incomplete, duplicate/reversed or out-of-range matrices fail closed before admission. Values are synthetic assumptions, never external estimates. |

## Success Criteria

- [ ] Fixture integration tests prove valid cycles reach selector, planner, mapper, independent risk, durable admission and synthetic OMS for multiple arbitrary symbols; bundles A/B have distinct symbols/quotes/rules, AI selection changes the dispatched fixture symbol, and all receipt identities link without network calls.
- [ ] Negative tests cover stale, future, missing or mismatched universe/evidence/snapshot data; abstain and risk rejection produce no native dispatch.
- [ ] Decimal mapping tests prove signed exposure delta, tick/quantity rounding down, minimum/maximum quantity/notional and unsupported-fixture rejection using engine-owned synthetic state.
- [ ] Replay tests prove same request plus same payload returns the original receipt, changed payload conflicts, and no more than one dispatch claim occurs.
- [ ] Timeout, persistence failure, event-gap and dirty-restart tests leave the session protected or explicitly unresolved; no blind retry or new request ID is created.
- [ ] Dashboard filter fixture tests prove symbol/category/timeframe changes alter displayed snapshots only and never decision inputs, candidate eligibility or simulated book state.
- [ ] The scoped Python test, lint and type checks pass; the report records actual command exits and states that full parent-product gates remain incomplete.
- [ ] New fixture and AI-cycle routes are added to `create_paper_app`, exported only through the paper contract `contracts/openapi/quant-paper.v1.json`, and reflected in the existing generated `paper-paths.ts`/`paper-schema.ts` artifacts. The readonly `quant-engine.v1.json` contract remains independently generated; `pnpm exec nx run quant-engine:openapi-check` and the quant-api-client `generate:check` must pass without bypassing their targets.

### Current architecture and implementation status (2026-11-20)

| Requirement area | Status | Evidence / remaining gap |
|---|---|---|
| Nx/pnpm + uv workspace and separate plugin/engine/package boundaries | Partial | Projects and source boundaries exist; full project graph and parent Verify Gate evidence are separate acceptance. |
| Dynamic AI universe; dashboard filters are display-only | Partial | Dynamic universe and AI decision boundary exist; dashboard non-interference requires dedicated integration regression coverage. |
| Strategy registry/evidence/selector and portfolio planner | Partial | Separate modules and scoped tests/reports exist; evidence provenance is caller-supplied today and modules are not yet joined into admission. |
| AI decision → selector → portfolio → risk → durable admission → native synthetic OMS | Not satisfied | No verified end-to-end orchestrator or linked receipt chain currently exists; this Define states its target contract. |
| Independent deterministic risk and durable synthetic paper admission | Partial | Existing PaperAdmission calls risk and AdmissionStore with generation/dispatch protections; it does not consume AI decision/portfolio plan. |
| Multi-symbol dynamic universe to supported internal-paper fixtures | Not satisfied | Current `synthetic_config()` and `PaperRuntime` accept one instrument fixture at a time; this slice must add a Python-owned fixture registry and a multi-instrument native paper session for explicitly registered offline bundles. |
| Stale/timeout/replay/restart protection for integrated AI cycle | Partial | Component-level CAS/idempotency/protection exist; cross-pipeline replay and timeout recovery are unproven. |
| Full architecture brief §§1–26, DSH lifecycle, exchange environments, monitoring, SBOM/security and release evidence | Not satisfied by this slice | These remain mandatory parent goals and cannot be inferred from the scoped synthetic fixture tests. |

**Offline single-source invariant:** In the `internal_paper` profile, Python `SyntheticFixtureRegistry` is the sole owner and source for the dynamic candidate universe, per-symbol synthetic OHLCV bars, market snapshot, quote, precision, depth, explicit pairwise correlation assumptions and synthetic OMS instruments/feed. Each bundle carries one canonical finite coefficient in [-1, 1] for every unordered symbol pair; missing, duplicate/reversed or out-of-range pairs fail closed. A fixture may use 1.0 as a conservative worst-case assumption, never as measured correlation. Host AI tools retrieve a read-only snapshot/digest from Python and submit only decisions bound to that digest; Python ignores request-supplied bars/prices/rules and resolves values from the registered bundle. Missing, stale or incomplete registry data causes reject/abstain, with no network or provider fallback.

**Runtime boundary clarification:** Python is the single fixture source. Host obtains a snapshot through authenticated loopback GET, which includes a bounded dynamic list of arbitrary registered fixture symbols and one bundle digest; the decision request carries only candidate selection/strategy evidence and snapshot identity. The Python multi-instrument native OMS uses that exact registered bundle. `host-tools-ai.ts` must not reach the Bybit-backed `getAiUniverse` path in this profile; the scheduler must reject `testnet`, `demo`, and `live`. Dashboard/watchlist views retain their current provider and behavior; symbol/category/timeframe filters never enter the request. Tests use typed `DecisionTrack` or a no-network stub; normal Harness model-provider offline behavior remains unproven. `paper_bootstrap.py` stays unchanged; its existing `loopback_host` parser must have a focused regression asserting non-loopback bind hosts fail.

## Acceptance Tests

| ID | Pattern | Criterion (EARS) | Gate (`kind`) |
|---|---|---|---|
| AT-001 | Event-driven | **When** a fresh, identity-bound AI decision cites a server-verifiable strategy evidence artifact and an eligible synthetic fixture, **then** the engine **shall** produce a deterministic `PortfolioPlan` and map one transition step to a Decimal `OrderIntent` using only engine-owned synthetic state. | test |
| AT-002 | Event-driven | **When** an exact intent is submitted, **then** independent deterministic risk **shall** evaluate it before `AdmissionStore` dispatch and **shall** persist either a stable rejection or a generation-bound admission decision. | test |
| AT-003 | Event-driven | **When** an admitted command is claimed, **then** `AdmissionStore` **shall** dispatch at most one stable native client-order ID and the synthetic OMS **shall** emit events linked to the durable command receipt. | test |
| AT-004 | Unwanted | **If** the universe, unverified evidence artifact, market snapshot or native/durable state is stale, missing, future-dated, inconsistent or outside the bound fixture, **then** the engine **shall** abstain or reject before native dispatch and **shall** record a stable reason. | test |
| AT-005 | Unwanted | **If** precision, minimum/maximum quantity, minimum notional, available synthetic equity/depth or any independent risk limit fails, **then** risk **shall** veto the intent and the Agent **shall** be unable to bypass or resize it automatically. | test |
| AT-006 | Event-driven | **When** the same idempotency request and payload digest is retried, **then** the engine **shall** return the existing receipt without a second dispatch; **if** the digest differs, **then** it **shall** return a conflict. | test |
| AT-007 | Unwanted | **If** a timeout, persistence error, native event gap or dirty restart makes dispatch outcome uncertain, **then** the session **shall** become protected or unresolved, the engine **shall** query the same request identity, and it **shall not** mint a replacement request or blindly retry. | test |
| AT-008 | Event-driven | **When** the dashboard changes symbol, category or timeframe filters, **then** only displayed market data **shall** change; the AI decision input, eligible universe, simulated portfolio and paper receipt **shall** remain unchanged. | test |
| AT-009 | Event-driven | **When** no fresh eligible candidate exists or the AI abstains, **then** the cycle **shall** persist an abstention outcome and **shall** create no `OrderIntent` or native command. | test |
| AT-010 | Ubiquitous | The slice **shall** operate only with literal `internal_paper` and isolated synthetic fixtures; it **shall** have no Testnet/Mainnet/private Bybit order transport or credential dependency. | test |
| AT-011 | Non-regression | The existing AI decision writer **shall continue to** reject stale simulated-track writes and preserve receipt ordering, and existing PaperAdmission **shall continue to** protect uncertain native/durable state. | test |
| AT-012 | Ubiquitous | When the `internal_paper` profile is active, Python's fixture registry **shall** be the sole source of candidate universe, market snapshot, bid/ask/depth and instrument rules; Host decisions and the multi-instrument synthetic OMS **shall** bind to its exact bundle digest; Python **shall** ignore request-supplied price/rule fields and reject missing/stale/incomplete bundles without Bybit fallback. | test |
| AT-013 | Ubiquitous | The scoped AI scheduler **shall** accept only literal `internal_paper`; other read-only dashboard/watchlist views **shall continue to** use their current providers without allowing UI filters to alter decision inputs. | test |
| AT-014 | Ubiquitous | The Host **shall** read the registry bundle using authenticated loopback `GET /api/v1/trading/fixtures/{fixture_id}` (`observe`), submit the strict AI-cycle request using `POST /api/v1/trading/ai-cycles` (`control`), and resolve status only through `GET /api/v1/trading/ai-cycles/by-request/{request_id}` (`observe`) using the same bounded request ID. Invalid schema, unauthorized scope, oversized body, timeout or unknown outcome **shall** fail closed. | test |
| AT-015 | Ubiquitous | Migration/recovery tests **shall** use only a SQLite file created under pytest `tmp_path`, assert its resolved path is beneath that directory, deny network access, verify 0006 upgrade/downgrade or backup/restore, and pass Alembic head/metadata consistency. After migration transitions, legacy `ExecutionCommand` ORM queries **shall** remain valid with their existing columns. | test |
| AT-016 | Event-driven | **When** fixture bundle A and bundle B expose different arbitrary test symbols, prices, depth and precision rules, **then** the returned AI candidate pool **shall** match the Python registry bundle and the AI **shall** be able to select a different eligible symbol from each bundle; each accepted decision **shall** dispatch only to that symbol's matching native synthetic instrument. Changing dashboard symbol/timeframe filters **shall not** affect request contents. | test |
| AT-017 | Event-driven | **When** a fresh fixture bundle contains deterministic OHLCV bars and the AI names a candidate symbol and strategy, **then** the engine **shall** run `select_strategy` using that symbol's bars, the validated candidate evidence and `StrategyRegistry`; it **shall** continue only if the selector returns selected/retained evidence for the same symbol and `strategy_id`, then pass its portfolio target through mapper, independent risk, admission CAS and the matching synthetic OMS. | test |
| AT-018 | Unwanted | **If** per-symbol bars are missing, stale, future-dated, insufficient for selector regime evaluation, or yield abstention / a different strategy or symbol than the AI intent, **then** the engine **shall** persist a terminal no-order outcome and **shall not** call the mapper or admission. | test |
| AT-019 | Ubiquitous | Fixture symbols **shall** use ASCII uppercase exchange-style syntax, length 1–40, matching `[A-Z0-9]+(?:[-._][A-Z0-9]+)*`; whitespace, control, path separators, lowercase and repeated/leading/trailing separators are invalid. Registry and portfolio contracts shall share this validation. | test |
| AT-020 | Unwanted | **If** selector evidence is missing, expired, unapproved, not paper-passed, lacks a ready signal, or its digest/strategy identity differs from the fixture artifact, **then** the cycle **shall** abstain before portfolio mapping and shall create no native command. | test |
| AT-021 | Ubiquitous | Fixture symbols **shall** use ASCII uppercase exchange-style syntax, length 1–40, matching `[A-Z0-9]+(?:[-._][A-Z0-9]+)*`; whitespace, control characters, path separators, lowercase and repeated/leading/trailing separators are invalid. Registry and portfolio contracts shall share this validation. | test |
| AT-022 | Unwanted | **If** selector evidence is missing, expired, unapproved, not paper-passed, lacks a ready signal, or its digest/strategy identity differs from the fixture artifact, **then** the cycle **shall** abstain before portfolio mapping and shall create no native command. | test |
| AT-023 | Unwanted | **If** a fixture bundle omits a required unordered pair, duplicates/reverses a pair, or supplies a coefficient outside [-1, 1], **then** registry construction shall reject before admission; no implicit zero or external estimate is allowed. | test |
| AT-024 | Ubiquitous | Each AI cycle request **shall** atomically create an immutable unique header and one `claimed` append-only event keyed by `(environment, account_ref, request_id)`, with one owner token, generation and bounded lease deadline. Same-key/same-payload requests under an active lease **shall** return the in-progress projection without taking ownership or dispatching; same-key/different-payload **shall** conflict. Expired leases or nonterminal claims found after process restart **shall** become protected and **shall never** transfer to another worker or be resubmitted. Abstain, stale, selector mismatch, mapping rejection and risk rejection **shall** persist terminal no-order events without fabricating an execution command. | test |

## Clarifications

### Session 2026-11-20

- [x] (scope) Is this a complete unattended trading product? → No; it is a prerequisite vertical slice limited to offline isolated synthetic paper; integrated into Metadata, Goals and Out of Scope.
- [x] (decision boundary) Who chooses symbols and parameters? → The AI chooses from a fresh dynamic eligible universe or abstains; dashboard symbol/category/timeframe controls are display-only; integrated into Goals and AT-008/AT-009.
- [x] (authority) Which component can approve/dispatch? → `quant_risk` has final deterministic veto, `AdmissionStore` owns durable CAS/claim, and the synthetic native OMS is the only dispatch authority in this slice; integrated into Goals and AT-002/AT-003.
- [x] (environment) Which environments are allowed? → Literal `internal_paper` only; no exchange/private account or real order writes; integrated into AT-010.
- [x] (retry) What happens on stale, timeout, replay or uncertain state? → Reject/abstain; same-key lookup only for retries; changed payload conflicts; uncertain state protects and never creates a new key; integrated into AT-004/AT-006/AT-007.
- [x] (transport) Which API boundary connects Host and engine? → Add `POST /api/v1/trading/ai-cycles` and `GET /api/v1/trading/ai-cycles/by-request/{request_id}` to the existing versioned paper API; use only loopback and its existing process-private control capability. The strict schemas, request-ID binding and bounded failure behavior are integrated into AT-014.
- [x] (test isolation) Where may migration tests run? → Only a SQLite file under pytest `tmp_path`; deny network and assert upgrade plus rollback or backup/restore. Integrated into AT-015.
- [x] (migration compatibility) How are receipts persisted without fake commands? → 0006 adds immutable cycle request headers and append-only cycle events, separate from command-bound decision bindings; only actual admissions create a command binding. No columns are added to legacy `ExecutionCommand`; migration tests verify metadata, uniqueness, event append-only behavior and legacy ORM queries across upgrade/downgrade.
- [x] (legacy gate) Which existing regression pins the migration head? → `test_command_ledger.py` is included in the scoped manifest; only its expected head advances to 0006, preserving all command-ledger semantics.
- [x] (native symbol boundary) Which shared constructor enforces fixture symbols? → `quant_execution.fixtures.make_instrument` shares the uppercase exchange-style grammar; its existing compatibility test covers dynamic symbols and legacy BTC/ETH symbols.
- [x] (multi-symbol risk boundary) How are correlations supplied offline? → Each bundle provides one explicit synthetic coefficient for every unordered pair, canonicalized and digest-bound. Missing, duplicate/reversed or out-of-range pairs are rejected; 1.0 is allowed only as a conservative synthetic assumption.
- [x] (OpenAPI authority) Which contract owns the new internal-paper routes? → The existing authenticated `create_paper_app` is authoritative; `contracts/openapi/quant-paper.v1.json` and generated `paper-*` SDK artifacts are canonical. The readonly engine contract stays separate. Existing Nx OpenAPI targets already generate/check both serially; no target/config change is needed.

Nine-category ambiguity sweep: Scope Clear; Data model Clear for this slice; UX flow Clear (view-only filters and explicit receipts); NFRs Clear for this slice (immutable 5,000 ms test-injected cycle deadline); Integrations Clear (offline fixtures and versioned loopback paper API); Edge cases Clear; Constraints Clear; Terminology Clear; Done signal Clear (Python test gate plus scoped evidence report).

## Verify Gate

```yaml
verify_gate:
  kind: test
  cmd: "pnpm run python:test"
  pass_when: "exit 0"
  threshold: "—"
  manual_fallback: "The command is the repository's real Python test gate. The Build report must additionally record focused fixture/recovery tests and explicitly mark full parent-product, Plugin Manager, exchange and release gates incomplete."
```

## Out of Scope

- Bybit private API, Testnet, Demo or Mainnet connectivity and any exchange order write.
- Network-backed Bybit universe/market reads inside the scoped `internal_paper` decision path; this slice does not claim an online autonomous AI loop.
- Provider/model selection, external LLM network isolation, or proof that the DSH-injected model itself runs offline; tests use typed decision fixtures or an injected no-network stub.
- User credentials, OAuth, account balances or live positions as inputs to this slice.
- Claiming the complete DSH Bundle, autonomous research company, Nautilus live execution, production readiness or full parent acceptance.
- Automatic code download/execution, strategy promotion, profitability claims or unbounded model retries.
- Exchange market feeds and production symbol catalogues; the dynamic universe in this slice is composed only from explicitly registered isolated fixtures injected into the offline service/test assembly. Runtime provisioning for an unattended deployed loop remains a parent-product gap.
- Dashboard controls selecting AI candidates or setting order parameters.
- Market history from a real venue; bars in this slice are deterministic synthetic fixture data only.

## Constraints

| Type | Constraint | Impact |
|---|---|---|
| Technical | Nx/pnpm TypeScript boundaries and uv/Python src-layout remain separate; handwritten TS files stay ≤500 lines. | Cross-language envelope and generated API must be explicit; no monolithic glue. |
| Security | Model output, market data, evidence and uploaded text/code are untrusted; secrets never enter prompts/logs/tests. | Strict schemas, digests, bounded fields, isolation and redaction are mandatory. |
| Trading | Mainnet remains disabled; this slice is literal internal paper only. | No safety bypass, account override or direct venue client. |
| Persistence | Admission data is pre-migrated and scoped; migrations are additive, reversible or backup-restored. | No implicit migration or destructive reset; append-only receipts and audit links. |
| Design | Selector/planner remain account-free; risk/admission owns trusted state and authority. | Prevents information leakage and shallow pass-through modules. |
| Testing | All tests are offline, fixture-backed and deterministic; no CI network or real orders. | Tests must assert transport absence and protected uncertainty. |
| Configuration | This slice adds no operator-facing configuration namespace or configuration files. | Use immutable safe defaults injected in tests: 5,000 ms deadline, one read-only refresh, one same-key resolution attempt, fixed fixture/session IDs; capability comes from the existing private process descriptor. |

## Technical Context

| Aspect | Value | Notes |
|---|---|---|
| **Deployment Location** | `apps/dsh-plugin` decision boundary plus independent `python/apps/quant-engine` and `python/packages/quant-*`; isolated SQLite/native fixture only | Engine must not depend on one DSH Tool call; no production DB or exchange process. |
| **KB Domains** | DSH AI decision lifecycle, Bybit V5 instrument semantics, quant selector/portfolio/risk, AdmissionStore/Alembic, Nautilus synthetic OMS, security and idempotency | Architecture brief §§1, 5, 8, 12–21, 24–26; current Design and Build reports. |
| **IaC Impact** | None for this slice | Use existing temporary fixtures; no cloud, account or infrastructure change. |
| **LLM Prompts** | true | Existing DSH background loop produces untrusted research decisions; prompt can choose or abstain but cannot authorize, resize, retry or bypass code-owned gates. |

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|---|---|---|---|
| A-001 | The current `PaperAdmission`/`AdmissionStore` synthetic path remains the only dispatch authority and is available with a pre-migrated isolated database. | Design must change before Build; no safe admission boundary exists. | Existing code/reports, yes |
| A-002 | Synthetic fixture symbols are arbitrary validated test symbols registered by the Python fixture registry; tests cover at least two distinct bundle identities and symbols, with no production allow-list. | Schema must reject invalid symbol syntax and require a registered fixture; no live market data. | Agreed for this slice |
| A-003 | A canonical digest can be computed over strict JSON-shaped envelopes without including secrets or non-deterministic fields. | Cross-language contract needs a different canonicalization design. | Proposed, to validate in Design |
| A-004 | Existing `pnpm run python:test` is the repository's executable Python gate; focused tests will be added during Build. | Replace the Verify Gate command before Build if repository scripts change. | `package.json`, yes |
| A-005 | The registry bundle enters this offline slice through explicit in-process fixture injection at isolated service assembly/test time; this slice adds no operator configuration or market-data loader. | Runtime fixture provisioning for a deployed autonomous loop remains a parent-product gap and cannot be inferred from the fixture API. | Agreed for this slice |

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---|---:|---|
| Problem | 3 | Missing cross-boundary contract and safety evidence are concrete. |
| Users | 3 | Operator and offline DSH test user with distinct needs. |
| Goals | 3 | Authority, identity, idempotency and offline scope are explicit. |
| Success | 2 | Observable tests are listed; exact timing budgets remain implementation configuration. |
| Scope | 3 | Synthetic-only prerequisite and parent-product exclusions are explicit. |
| **Total** | **14/15** | |

Minimum to proceed: **12/15**.

## Open Questions

None - ready for Design. Exact timeout/deadline numbers and fixture expansion are implementation configuration or a later scope change, not blockers to the Design gate.

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-11-20 | SDD Define by RDD | Initial Define for offline AI-to-synthetic-paper vertical slice. |
| 1.1 | 2026-11-20 | SDD Define by RDD | Fixed loopback AI-cycle routes, immutable test-injected defaults, and tmp_path/network-denied migration verification. |
| 1.2 | 2026-11-20 | SDD Define by RDD | Required Python-owned dynamic multi-symbol fixture bundles, bundle A/B symbol selection, the authenticated fixture snapshot route, and clarified that deployed autonomous fixture provisioning remains outside this slice. |
| 1.3 | 2026-11-20 | SDD Define by RDD | Added migration metadata/head consistency and legacy ORM compatibility as explicit acceptance evidence for the independent decision-binding table; migration tests remain isolated under pytest tmp_path with backup/restore protection. |
| 1.4 | 2026-11-20 | SDD Define by RDD | Required independent durable append-only cycle receipts for both order and no-order terminal outcomes, idempotent replay/conflict behavior and restart protection without fake commands. |
| 1.5 | 2026-11-20 | SDD Define by RDD | Kept receipt DAO and cycle service in dedicated cohesive modules so every handwritten source stays below 500 lines; acceptance behavior is unchanged. |

## Next Step

Execute o **SDD Design by RDD**.
