# DESIGN: Strategy Registry Metadata and Lifecycle

> Scoped deterministic registry foundation for Bybit AI Quant AT-017.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | STRATEGY_REGISTRY |
| **Date** | 2026-11-19 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **UX REVIEW** | `sdd/reports/UX_REVIEW_DSH_BYBIT_UI_2026-11-19.md` |
| **LLM Prompts** | true at parent product scope; this slice adds no prompt or model call |
| **Status** | Implemented registry foundation; shared model ownership updated by `DESIGN_STRATEGY_FAMILIES.md` |

## Architecture Overview

```text
caller-owned strategy metadata + config
                 │
                 ▼
       StrategyRegistry.register
        ├─ strict metadata checks
        ├─ bounded config-schema checks
        ├─ lifecycle/validation consistency
        └─ immutable in-memory definition
                 │
                 ▼
       registry lookup / safe transition

No strategy code loading, model call, exchange client, credential or order path
```

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| `quant_engine.strategy_registry` | Validate complete strategy metadata, a deliberately small config schema, and legal lifecycle transitions | Pure typed Python module; immutable dataclasses/enums; stable error codes | Shared metadata, scalar config, transition request | Immutable record or deterministic validation error | Python standard library; `quant_strategies.metadata` |
| Registry tests | Prove field validation, config bounds, registration uniqueness and lifecycle gates | pytest, existing engine test target | Valid and hostile fixtures | Pass/fail evidence | `strategy_registry` |

## Key Decisions

### Decision 1: Keep the registry in the existing engine project

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-19 |
| **Source** | Existing project structure and `AGENTS.md` |

**Context:** At the time of this scoped registry design, the registry contract was the only consumer of strategy metadata. The later `DESIGN_STRATEGY_FAMILIES.md` adds a reusable algorithms package that also needs those contracts.

**Choice:** Keep lifecycle and registry orchestration in `python/apps/quant-engine/src/quant_engine/strategy_registry.py`; define shared immutable metadata/configuration types in `python/packages/quant-strategies/src/quant_strategies/metadata.py`.

**Rationale:** The engine owns registration and lifecycle behavior, while the strategy-domain package owns contracts consumed by both the registry and deterministic algorithms. Nx and uv record the actual engine-to-package dependency.

**Alternatives Rejected:**
1. Keep shared strategy metadata inside the engine — algorithms would then depend on an application project.
2. Extend the DSH TypeScript backtest module — the original requirement places the shared strategy lifecycle in the Python engine and DSH remains a proposal/control surface.

**Consequences:** The registry is process-local and is not yet wired into a scheduler, API, persistence layer or UI. Those require separate manifests and acceptance.

### Decision 2: Metadata is descriptive and cannot authorize execution

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-19 |
| **Source** | DEFINE AT-017/021/025 and original brief §7 |

**Context:** Strategy metadata may contain source and validation claims that callers or agents cannot be trusted to turn into execution authority.

**Choice:** Validate and retain only typed, bounded metadata and scalar configuration. Approval lifecycle status requires paper-stage validation and a non-empty external approval reference, but the reference is provenance only. The module loads no strategy code and exposes no account, risk-execution or exchange API.

**Rationale:** The registry can reject incomplete or unsafe descriptions while keeping approval, deterministic risk and sole Nautilus execution as separate future boundaries.

**Alternatives Rejected:**
1. Execute registered code or treat `approved` as permission to submit orders — violates the independent risk and execution-authority requirements.
2. Accept arbitrary nested JSON/configuration — creates an unbounded and ambiguous validation boundary.

**Consequences:** A paper-passed record and approval reference do not prove a real validation run or user authorization. No strategy is deployed by this slice.

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `python/apps/quant-engine/src/quant_engine/strategy_registry.py` | Create | Strict metadata/configuration validation and lifecycle registry boundary | (general) | None |
| 2 | `python/apps/quant-engine/tests/test_strategy_registry.py` | Create | Valid/invalid fields, configuration, duplicate registration and transition gates | (general) | 1 |
| 3 | `sdd/reports/BUILD_REPORT_STRATEGY_REGISTRY.md` | Create | Record command evidence, scope and remaining product gaps | (general) | 1-2 |

**Total Files:** 3

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1-3 | One small, tightly coupled pure-domain slice; current runtime does not use another code agent. |

**Agent Discovery:** Not available for this slice.

## Code Patterns

### Pattern 1: Fail-closed registration

```python
record = registry.register(metadata, config)
# Raises RegistryValidationError with a stable code for any invalid field.
```

### Pattern 2: Approval is provenance, not authority

```python
record = registry.transition(
    strategy_id,
    version,
    LifecycleStatus.APPROVED,
    approval_ref="review-2026-0001",
)
```

The transition is allowed only for a paper-passed definition. It does not start a strategy, change risk caps or create an execution capability.

## LLM Prompts

| # | Path / Runtime | Type | Consumer | Output Shape |
|---|---|---|---|---|
| LP-001 | Parent-defined DSH AI decision track; no prompt path is added by this manifest | Existing product loop; unchanged in this slice | DSH-managed model invoking bounded plugin tools | Existing tool input/output contracts; this module accepts only deterministic registry requests and never calls a model |

The parent design remains authoritative for existing prompt trust and untrusted-evidence handling. This slice adds no prompt, provider, model, agent call or generated code path. Prompt/model changes remain outside this manifest.

## Data Flow

1. A trusted engine caller supplies metadata fields and a flat scalar config mapping.
2. The registry validates required §7 fields, identifiers, source/license references, markets, instruments, timeframes, features, warmup, config schema, conditions, exposure/risk descriptions, metrics, validation status and lifecycle status.
3. Unknown config keys, missing required keys, wrong scalar types, non-finite numbers, invalid enum values, duplicate `(strategy_id, version)` and inconsistent lifecycle states are rejected with fixed error codes.
4. Successful registration stores an immutable process-local record; legal lifecycle transitions return a new record and replace the current in-memory value.
5. No scheduler, persistence, model, market-data, account or exchange operation follows from registration.

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| None | Pure in-process domain module | N/A | N/A | Invalid requests are rejected; no retry without corrected metadata/config |

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Every required §7 metadata field, scalar config schema, duplicate IDs, immutable records and lifecycle transition gates | `python/apps/quant-engine/tests/test_strategy_registry.py` | Existing locked pytest | Exit 0; invalid requests fail closed |
| Static | Strict Python types and formatting | `strategy_registry.py`, `test_strategy_registry.py` | Existing Ruff/Pyright | Exit 0 |
| Verify Gate | Parent DEFINE command | Workspace | `pnpm run verify` | Exit 0; this local gate does not certify full product acceptance |

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Invalid metadata/config | Deterministic field/schema validation | Raise `RegistryValidationError` with stable code; do not echo unsafe values | No | Caller may count stable error codes |
| Duplicate strategy version | Existing `(strategy_id, version)` key | Reject; create a new version for changed metadata | No | Stable duplicate code |
| Invalid lifecycle transition | Transition table and validation-stage gate | Reject without changing stored record | No | Stable transition code |
| Missing strategy record | Registry lookup | Raise stable not-found code | No | Stable lookup code |

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| Per-strategy keys | Flat scalar mapping defined by metadata schema | Caller supplied; no permissive defaults | No | Supports finite number/integer, boolean, bounded string and string enum values with explicit required/min/max/choices constraints |

## Security Considerations

- Source repository and commit are metadata only; registry does not fetch, import, evaluate or execute external code.
- Metadata is bounded and typed; config rejects unknown keys, nested values, non-finite numbers and bool/int confusion.
- `approved` is a lifecycle label, not a permission token. Separate user authorization, account identity, balance, instrument precision, risk, idempotency, reconciliation and Nautilus gates remain mandatory.
- No credentials, user account data, order intents or model-generated code are accepted by this module.

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | None in pure module | Callers receive stable codes and decide redacted logging policy |
| Metrics | None in this slice | Registry is not yet integrated into engine monitoring |
| Tracing | None in this slice | No cross-system operation exists |

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| MUST strategy registry metadata/lifecycle | `StrategyMetadata`, config schema and transition table | `test_strategy_registry.py` |
| AT-017 | Full required §7 metadata/configuration/status validation on registration | Per-field and invalid-state regression matrix |
| AT-018 (partial implementation in `DESIGN_STRATEGY_FAMILIES.md`) | Pure strategy family evaluators and deterministic fixtures | Package tests; broader §7 family coverage, runtime selection and shared lifecycle integration remain open |
| AT-019/020/025/029 (future integration) | Selector, portfolio, durable approvals and version ledger are excluded | Remain open; parent feature gate |
| Mainnet remains separately locked; Testnet guards cannot be bypassed | No exchange or execution dependency | Static dependency and import review; parent gate |

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Callers treat metadata as proof of validation | Unsafe strategy promotion | Validation stage is explicit; approval reference required; module has no execution authority | Evidence provenance is not cryptographically verified or persisted |
| Process restart loses registry state | Strategies may disappear | No persistence claim; integration must use the approved durable ledger/migration design | Full registry persistence remains unimplemented |
| Schema is narrower than future algorithm needs | Callers may be tempted to pass arbitrary objects | Flat scalar allowlist fails closed | Extend only through a separately designed, versioned schema |

## Advisor Ledger

None — no formal external design review was executed.

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-11-19 | SDD Design by RDD | Initial scoped design for AT-017 registry validation |
| 1.1 | 2026-11-19 | SDD Build continuation | Shared metadata contracts moved to `quant-strategies`; registry remains engine-owned; AT-018 now has a separately scoped partial implementation |

## Next Step

Execute o **SDD Build by RDD**.
