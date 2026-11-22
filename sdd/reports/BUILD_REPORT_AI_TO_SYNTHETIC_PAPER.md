# BUILD REPORT: AI decision to durable synthetic-paper admission

> Implementation report for the offline-only AI-to-synthetic-paper vertical slice

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | `AI_TO_SYNTHETIC_PAPER` |
| **Date** | 2026-11-21 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | N/A — no feature-specific Brainstorm exists |
| **DEFINE** | `sdd/features/DEFINE_AI_TO_SYNTHETIC_PAPER.md` |
| **DESIGN** | `sdd/features/DESIGN_AI_TO_SYNTHETIC_PAPER.md` |
| **Status** | Incomplete — Python Verify Gate green; Host internal-paper request wiring is present behind the existing paper capability, but deployed registry provisioning, Host E2E coverage, LP-001 evaluation and production execution remain open |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 50 |
| Cross-file coupling | High: cross-language OpenAPI, Python registry/API/native OMS, TS Host and receipt persistence share identity and digest contracts. |
| Security surface | High: loopback auth scopes, fail-closed decision input, migration isolation and no-network requirements. |
| LLM prompt items | LP-001: bounded AI loop prompt inventory item. |
| Independent volume | Some tests are independently verifiable, but shared registry and API contracts dominate. |
| Context-rot risk | High file count; keep ordered dependency execution and record incremental checks. |
| Runtime capabilities | Direct sequential execution is available; no fresh-context respawn mode is assumed. |

**Recommendation:** `default` sequential execution because shared DTOs, registry digest, admission identity and native routing require one coherent implementation path.

**User decision:** `default`, authorized by the parent task; the user's standing instruction permits continuing without another prompt.

**Pre-build review:** Parent design review completed. The prior Host-owned/BTC-only fixture drift was resolved by making Python's explicitly injected `SyntheticFixtureRegistry` the sole source. The current Design manifest contains 50 paths after consolidating the decision orchestrator into `paper_cycle_service.py`.

**OpenAPI drift resolution:** Initial review incorrectly assumed `quant-paper.v1.json` did not exist. Direct inspection confirmed that both canonical contracts exist and `project.json` serially exports/checks both. The internal-paper routes must update `quant-paper.v1.json` and the existing `paper-paths.ts`, `paper-schema.ts`, and `paper.ts`; `quant-engine.v1.json` remains readonly API authority. No `project.json` change is required or permitted by the manifest. The required generated-contract gates are the existing Nx `quant-engine:openapi-check` and SDK `generate:check`.

## Summary

| Metric | Value |
|---|---|
| **Manifest paths present and changed/created** | 45/50 (18 created and 27 modified, including this report) |
| **Manifest paths unchanged** | 1 (`python/packages/quant-execution/tests/test_native_execution.py`) |
| **Manifest paths absent** | 4: planned loop v5 prompt, standalone orchestrator test, dedicated bootstrap-loopback test, DSH AI-cycle transport test |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 20+ (focused tests, full Python gate, root Nx gate, security/SBOM/secret scans; exact receipts are listed below) |
| **Verify Gate** | Passed — `pnpm run python:test` exit 0, 499 passed with 11 warnings; overall Build remains incomplete because Host integration and LP-001 are not complete |
| **Execution Mode** | default |

## Scope and resolved drift

- The manifest has 50 paths. Items 44–46 satisfy the Alembic metadata-head and command-ledger gates for migration 0006; items 47–48 align native instrument construction with the shared dynamic symbol grammar; item 49 adds a two-symbol risk/admission integration gate; item 50 owns receipt persistence. Item 7 and the former item 51 were consolidated into `paper_cycle_service.py` to avoid a duplicate forwarding module.
- The internal-paper runtime uses Python `SyntheticFixtureRegistry` as the single owner of candidates, snapshot, bid/ask/depth, rules and native instrument mapping. A Host request supplies fixture identity and decision only; it cannot supply execution prices or rules.
- Bundle A/B tests must use different arbitrary fixture symbols and prove AI selection reaches the matching synthetic instrument. No production symbol allowlist or exchange market source is added.
- `paper_bootstrap.py` source remains unchanged. A dedicated new bootstrap-loopback test path from the initial manifest is absent; the existing `test_service.py` checks the shared `loopback_host` helper but does not replace that planned regression receipt.
- Registry bundles are explicitly injected in isolated service/test assembly. This slice adds no operator setting or market-data loader and does not claim a deployed autonomous loop.
- Migration validation is limited to a SQLite database created beneath pytest `tmp_path`, with network denied and rollback or backup/restore asserted. No configured/shared database may be opened.
- Migration 0006 is represented by a separate `AiPaperDecisionBinding` metadata mapping. `ExecutionCommand` ORM columns remain unchanged; the migration suite asserts the binding table at head, verifies Alembic metadata consistency, and exercises legacy ORM queries across migration upgrade/downgrade/re-upgrade.
- **Cycle-receipt drift (2026-11-20):** The binding table requires a real `command_id`, so it cannot represent no-order cycles. Define/Design require immutable cycle headers and append-only events, with command binding reserved for actual admission. Migration `0006` and metadata now create both receipt tables and SQLite no-update/no-delete triggers. `CycleReceiptStore` implements transactional begin/replay/conflict, append-only transitions, and durable lookup. Focused tests prove terminal abstain replay, changed-payload conflict, event order, trigger rejection, and migration protections. Full live/exchange orchestrator and restart recovery remain parent-product gaps.
- **Source-size drift (2026-11-20):** `paper_admission.py` exceeded the 500-line limit. Receipt persistence lives in item 50 (`cycle_receipt_store.py`); selector/planning/submit orchestration lives in item 7 (`paper_cycle_service.py`). The service and receipt responsibilities remain separate and below the 500-line handwritten-source limit.
- **Risk-matrix drift (2026-11-20):** The independent evaluator initially rejected ALPHA→BETA with `correlation_missing`; this was not an equity or notional failure. The approved contract now requires each multi-symbol bundle to carry exactly one canonical, digest-bound synthetic coefficient per unordered pair (finite and within [-1, 1]); missing, duplicate/reversed or out-of-range entries fail closed. Registry, DTO/snapshot, RiskContext and tests now implement this contract. A fixture value of `1.0` is used only as a conservative worst-case synthetic assumption.
- The Python paper API has a verified positive synthetic path through selector, planner, mapper, independent risk, durable admission and the matching native OMS. The Host now has an `internal_paper`-only path that reads the authenticated fixture snapshot, binds strategy/evidence/digest identity, posts one cycle request and resolves an ambiguous transport result with the same request ID. This path is not a deployed unattended loop: `paper_bootstrap.py` still does not provision a registry, and there is no Host-to-Python end-to-end receipt proving the scheduler reaches the service process. Testnet continues to use the separate local simulated journal path.
- No browser, credentials, account, exchange network, Testnet/Mainnet or exchange order write was used for this slice.

### Scheduler environment scope drift (2026-11-21)

The scoped Define says its AI scheduler accepts only literal `internal_paper`
(AT-010/013). The active general-purpose DSH scheduler currently allows both
`internal_paper` and `testnet`; in Testnet mode its tool path uses the Bybit
candidate/market provider and records only to the local simulated journal. It
still does not call the Python AI-cycle API or submit an exchange order. This
is an unresolved scope boundary between the offline synthetic-paper slice and
the earlier Testnet research-mode loop. It is recorded as drift; no code was
changed to silently merge the two paths or claim AT-013 is satisfied. Resolve
it in the parent Define/Design before wiring the Python cycle into Host.

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---:|---|---|---|---|---|
| 1 | 43 | Create this Build report before source implementation | direct | Done | `git status --short sdd/reports/BUILD_REPORT_AI_TO_SYNTHETIC_PAPER.md` | Report is within the approved manifest. |
| 2 | 1 | Add strict cross-language AI paper decision/snapshot/receipt schema | direct | Done | `python -m json.tool contracts/schemas/ai-paper-decision.v1.json >/dev/null` (0) | Schema validates as JSON; authoritative quotes/rules stay outside decision request. |
| 3 | 2 | Implement immutable multi-symbol `SyntheticFixtureRegistry` and bundle digest/snapshot validation | direct | Done | Focused registry tests (0) | Registry resolves only injected bundles, binds digest, rejects stale snapshots and invalid symbols/rules. |
| 4 | 26 | Add registry bundle A/B, digest, stale/clock and validation tests | direct | Done | `uv run --project python --locked pytest python/apps/quant-engine/tests/test_synthetic_fixture_registry.py -q` (0) | 4 passed; inconsistent-balance fixture uses a distinct symbol so balance validation is exercised. |
| 5 | 3 | Implement strict Python DTOs, identity/digest/freshness validation and terminal decision contracts | direct | Done | Focused contract tests and Pyright (0) | Request digest binds fixture identity, AI decision and environment; request has no quote, price or rule fields. |
| 6 | 25 | Add contract edge cases for duplicate candidates, unknown fields, action consistency, replay digest and environment | direct | Done | `uv run --project python --locked pytest python/apps/quant-engine/tests/test_ai_paper_contracts.py python/apps/quant-engine/tests/test_synthetic_fixture_registry.py -q` (0) | 8 passed; added Pyright and Ruff checks for all first-batch files. |
| 7 | 11 | Extend paper API DTO boundary with strict fixture/AI-cycle request and receipt aliases | direct | Done | Python API focused tests (0) | DTOs reuse strict Python contract models; no duplicate coercive schemas. |
| 8 | 12 | Add authenticated fixture snapshot, AI-cycle submit and same-request lookup routes | direct | Done | `pytest ...test_fixture_registry_api.py ...` (0) | Existing paper capability observe/control dependencies guard every route; missing injection fails closed with 503. |
| 9 | 13 | Regenerate canonical `quant-paper.v1.json` from `create_paper_app` | direct | Done | `quant-engine-openapi --paper` (0) | Readonly `quant-engine.v1.json` remains separate. |
| 10 | 14 | Regenerate paper route types | direct | Done | client `generate:check` (0) | `generated/paper-paths.ts` includes three new routes. |
| 11 | 15 | Regenerate paper schemas | direct | Done | client `generate:check` (0) | `generated/paper-schema.ts` includes fixture/decision/receipt schemas. |
| 12 | 16 | Add runtime AJV validators for fixture/decision/receipt responses | direct | Done | client typecheck/tests (0) | Unknown/malformed wire data remains rejected by shared bounded validation. |
| 13 | 17 | Add typed paper client fixture/cycle/status methods | direct | Done | `pnpm --filter @bybit-quant/quant-api-client test` (0) | Cycle mutation uses same-key uncertain recovery and never blind retries. |
| 14 | 44–45 | Extend existing migration gate and map the independent 0006 binding table | direct | Done | `uv run --project python --locked pytest -q python/packages/quant-data/tests/test_migrations.py` (0; 11 passed) | Head table set and Alembic metadata check pass; the legacy `ExecutionCommand` ORM query remains valid after upgrade/downgrade/re-upgrade. Tests use temporary local databases. |
| 15 | 46 | Update command-ledger fixture's expected Alembic head | direct | Done | `uv run --project python --locked pytest -q python/packages/quant-data/tests/test_command_ledger.py` (0; 30 migration/ledger focused cases passed together) | Only the pinned head expectation advances from 0005 to 0006; command-ledger semantics remain unchanged. |
| 16 | 47–48 | Align native instrument factory and compatibility regression with dynamic fixture symbol grammar | direct | Done | `uv run --project python --locked pytest -q python/packages/quant-execution/tests/test_catalog_compatibility.py` (0; 16 passed); Ruff/Pyright scoped checks (0) | Accepts ALPHA-PERP/BETA.PERP/GAMMA_1 and legacy BTCUSDT/ETHUSDT; rejects lowercase, malformed/repeated separators, whitespace, path separators and >40 chars. |
| 17 | 4–5, 7–8, 11, 32–36, 49–50 | Route multi-symbol fixtures through selector, planner, mapper, native OMS, risk snapshots, durable receipts and pairwise correlation assumptions | direct | Done | Focused API/admission batch (0; 14 passed) and full `pnpm run python:test` (0; 499 passed) | API tests exercise filled and risk-vetoed cycles, bundles A/B, symbol-bound native commands, idempotent replay and payload conflict. This proves the isolated Python cycle path only, not DSH Host-to-engine wiring. |

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `contracts/schemas/ai-paper-decision.v1.json` | Create | 1 | Yes | JSON parser exit 0; no authoritative quote or rule fields in decision request. |
| `python/apps/quant-engine/src/quant_engine/synthetic_fixture_registry.py` | Create | 2 | Yes | Immutable bundle, canonical digest and fresh candidate snapshot. |
| `python/apps/quant-engine/src/quant_engine/ai_paper_contracts.py` | Create | 3 | Yes | Strict wire contracts and request digest validation. |
| `python/apps/quant-engine/tests/test_synthetic_fixture_registry.py` | Create | 26 | Yes | 4 focused cases pass. |
| `python/apps/quant-engine/tests/test_ai_paper_contracts.py` | Create | 25 | Yes | Contract validation cases pass. |
| `sdd/reports/BUILD_REPORT_AI_TO_SYNTHETIC_PAPER.md` | Create/update | 43 | Yes | Records actual incremental commands, corrected OpenAPI drift and current limitations. |
| `python/apps/quant-engine/src/quant_engine/paper_api_models.py` | Modify | 11 | Yes | Re-exports strict AI paper DTOs. |
| `python/apps/quant-engine/src/quant_engine/paper_api.py` | Modify | 12 | Yes | Authenticated fixture and cycle routes with registry identity checks. |
| `python/apps/quant-engine/tests/test_fixture_registry_api.py` | Create | 30 | Yes | 4 route/auth/digest/schema cases pass. |
| `contracts/openapi/quant-paper.v1.json` | Modify | 13 | Yes | Generated from actual paper FastAPI app. |
| `packages/ts/quant-api-client/src/generated/paper-paths.ts` | Modify | 14 | Yes | Generated routes. |
| `packages/ts/quant-api-client/src/generated/paper-schema.ts` | Modify | 15 | Yes | Generated schemas. |
| `packages/ts/quant-api-client/src/validation.ts` | Modify | 16 | Yes | AJV validators for new paper responses. |
| `packages/ts/quant-api-client/src/paper.ts` | Modify | 17 | Yes | Typed fixture/cycle client methods. |

## Prompts Generated / Refactored

| ID | Path | Type | Status | Receipt |
|---|---|---|---|---|
| LP-001 | `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v5.ts` | loop | Pending | Before editing, apply the available loop-specification and prompt-builder workflows; preserve abstain and no-side-effect retry boundaries, then record artifacts and actual verification. |

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | Fixture ownership and supported symbols | Existing `synthetic_config` and native paper runtime are single-instrument; an earlier design draft incorrectly made Host own fixtures and called the Build BTCUSDT-only. | Revise spec; parent approved Python registry, dynamic arbitrary fixtures and multi-symbol synthetic OMS. | Define/Design now require the same Python registry bundle for API, mapping and OMS; manifest expanded to cover config/context/native models/runtime/worker and bundle tests. |
| 2 | Runtime registry provisioning | Existing bootstrap has no operator-facing bundle loader; changing it was disallowed. | Bound the slice to explicit in-process fixture injection; deployed unattended provisioning remains a parent gap. | Keep bootstrap source unchanged, test loopback guard, do not claim a deployed autonomous loop. |
| 3 | OpenAPI canonical file and generated SDK mapping | First pass incorrectly asserted `quant-paper.v1.json` was missing and pointed paper routes at readonly `quant-engine.v1.json`. Inspection confirmed both contracts exist; `project.json` generates/checks both serially, and paper SDK artifacts are already separate. | Keep `quant-engine.v1.json` readonly and unchanged for this slice; new paper routes belong in `quant-paper.v1.json` from `create_paper_app`. Preserve existing generation/check gates. | Define/Design map Manifest 13–17 to paper canonical OpenAPI, generated paper paths/schema, shared runtime validation, and `paper.ts`. No `project.json` change is needed. |
| 4 | Selector inputs did not match the fixture contract | Actual `select_strategy` requires a `quant_strategies.MarketSnapshot` containing OHLC bars plus validated `SelectionCandidate` evidence and a `StrategyRegistry`; it abstains on insufficient history. The injected `PaperFixtureBundle` initially contained only bid/ask/depth, so direct AI-decision-to-portfolio wiring would bypass the required selector. | Do not treat the AI DecisionTrack as selector output. Revise Define/Design before coding: registry bundles now include bounded deterministic per-symbol OHLCV bars in the canonical digest; the orchestrator must run the existing selector and stop unless its selected/retained symbol and strategy identity match the AI intent and validated evidence. Missing/stale/insufficient bars and mismatch terminate before mapper/admission. | Define adds an explicit MUST and AT-017/018; Design updates schema/fixture/orchestrator/test manifest rationale and traceability. Runtime prompt/model online autonomy remains an explicit full-goal gap. No source code changed for this drift. |
| 5 | Portfolio symbol syntax was narrower than dynamic fixture contract; selector evidence had no authoritative source | `quant_portfolio.models` accepted only alphanumeric symbols, rejecting required fixture examples such as `ALPHA-PERP`; `PaperFixtureBundle` contained OHLCV but no `SelectionCandidate` evidence, while request data carried only an evidence digest. | Parent directed a closed safe syntax `[A-Z0-9]+(?:[-._][A-Z0-9]+)*`, max 40, and fixture-owned deterministic selector evidence with approved/paper-passed metadata, bounded OOS fields, digest and expiry. Evidence is synthetic and is not represented as online/GitHub provenance. | Define adds AT-019/020; Design updates fixture/schema/API/manifest flow and adds `quant-portfolio/models.py` plus validation test. Build is paused for affected selector/planner wiring until docs are verified. |

### Selector fixture bars (Manifest items 1–3, 11–17, 25–26, 30)

The registry now owns bounded per-symbol synthetic OHLCV bars, validates OHLC shape, monotonic timestamps, freshness, symbol coverage and maximum history length, and binds bar values into the canonical bundle digest. The authenticated fixture GET includes those same bars; strict Python DTO, canonical JSON Schema, generated paper OpenAPI and generated SDK schema expose them as response-only data. Decision requests still cannot supply bars or prices. Bundle tests cover digest binding, missing symbol bars, unordered bars, malformed OHLC and stale history.

Focused receipt: `uv run --project python --locked pytest python/apps/quant-engine/tests/test_synthetic_fixture_registry.py python/apps/quant-engine/tests/test_ai_paper_contracts.py python/apps/quant-engine/tests/test_fixture_registry_api.py -q` — exit 0, 12 passed (one upstream Starlette/httpx deprecation warning).

Static/contract receipts: Ruff on the 6 touched Python files — exit 0; Pyright on the 3 touched production Python modules — exit 0, 0 errors/warnings/informations; `uv run --project python --locked quant-engine-openapi --paper --output contracts/openapi/quant-paper.v1.json && node packages/ts/quant-api-client/scripts/generate.ts && pnpm exec nx run quant-engine:openapi-check --skip-nx-cache && pnpm --filter @bybit-quant/quant-api-client generate:check` — exit 0; `git diff --check` — exit 0.

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Design/Define formatting sanity | `git diff --check -- sdd/features/DEFINE_AI_TO_SYNTHETIC_PAPER.md sdd/features/DESIGN_AI_TO_SYNTHETIC_PAPER.md sdd/reports/BUILD_REPORT_AI_TO_SYNTHETIC_PAPER.md` | Pass (exit 0) | No whitespace errors reported after OpenAPI source correction. |
| Registry focused tests | `uv run --project python --locked pytest python/apps/quant-engine/tests/test_synthetic_fixture_registry.py -q` | Pass (exit 0) | 4 passed in 1.00s. |
| Contract + registry focused tests | `uv run --project python --locked pytest python/apps/quant-engine/tests/test_ai_paper_contracts.py python/apps/quant-engine/tests/test_synthetic_fixture_registry.py -q` | Pass (exit 0) | 8 passed in 0.57s. |
| First-batch Ruff | `uv run --project python --locked ruff check ...` (four new/changed Python files) | Pass (exit 0) | All checks passed. |
| First-batch Pyright | `uv run --project python --locked pyright` (four new/changed Python files) | Pass (exit 0) | 0 errors, 0 warnings, 0 informations. |
| Canonical OpenAPI target | `pnpm exec nx run quant-engine:openapi-check --skip-nx-cache` | Pass (exit 0) | Existing target ran readonly and paper exporters in sequence; no check bypass. |
| Generated TS SDK | `pnpm --filter @bybit-quant/quant-api-client generate:check` | Pass (exit 0) | Existing generator validated engine and paper generated artifacts. |
| Paper API focused tests | `uv run --project python --locked pytest python/apps/quant-engine/tests/test_fixture_registry_api.py python/apps/quant-engine/tests/test_command_api.py python/apps/quant-engine/tests/test_ai_paper_contracts.py python/apps/quant-engine/tests/test_synthetic_fixture_registry.py -q` | Pass (exit 0) | 12 passed, 1 deprecation warning. |
| Paper Python lint/type | `uv run --project python --locked ruff check ...paper_api.py ...paper_api_models.py ...test_fixture_registry_api.py`; `pyright` same files | Pass (exit 0) | Ruff clean; Pyright 0 errors/warnings/informations. |
| Paper SDK type/test | `pnpm --filter @bybit-quant/quant-api-client typecheck && pnpm --filter @bybit-quant/quant-api-client test` | Pass (exit 0) | 24 Vitest tests passed; TypeScript build/typecheck passed. |
| Pairwise correlation registry/API/admission | `uv run --project python --locked pytest -q python/apps/quant-engine/tests/test_synthetic_fixture_registry.py python/apps/quant-engine/tests/test_ai_paper_contracts.py python/apps/quant-engine/tests/test_fixture_registry_api.py python/apps/quant-engine/tests/test_admission.py` | Pass (exit 0) | 20 passed; covers missing/reversed/out-of-range pairs, digest binding, GET snapshot and two-symbol admission with explicit 1.0 fixture assumption. |
| Pairwise correlation Ruff | `uv run --project python --locked ruff check` on the 9 changed registry/API/config/context/test files | Pass (exit 0) | All checks passed after import/Decimal formatting fixes. |
| Pairwise correlation Pyright | `uv run --project python --locked pyright` on changed application source files | Pass (exit 0) | 0 errors, 0 warnings, 0 informations. |
| Pairwise correlation OpenAPI | `pnpm exec nx run quant-engine:openapi --skip-nx-cache` then `pnpm exec nx run quant-engine:openapi-check --skip-nx-cache` | Pass (exit 0) | Canonical paper OpenAPI regenerated and subsequent check passed. Initial check before generation correctly reported schema drift. |
| Pairwise correlation SDK | `pnpm --filter @bybit-quant/quant-api-client generate` then `pnpm --filter @bybit-quant/quant-api-client generate:check` | Pass (exit 0) | Initial check reported stale generated paper paths; regenerated SDK and verification passed. |
| Design manifest sanity (current revision 1.9) | Python read-only check of Design manifest | Pass (exit 0) | 50 items, IDs contiguous 1–50, no duplicates. The earlier 49-row receipt below is historical and superseded by revision 1.9. |
| Final whitespace sanity | `git diff --check` | Pass (exit 0) | No whitespace errors. |
| New-document whitespace sanity | Python read-only scan of Define and Design | Pass (exit 0) | No trailing whitespace or tab characters in either document. |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `pnpm run python:test` |
| **Exit / Result** | Exit 0; 499 passed, 11 deprecation warnings |
| **Status** | Passed |
| **Evidence** | Run against the current workspace; Host integration and parent-product acceptance remain outside this Python gate. |

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | `pnpm run python:lint` | Pass (exit 0) | Ruff checks and 110-file format check passed. DSH lint is included in the workspace verify receipt. |
| Typecheck | `pnpm run python:typecheck` | Pass (exit 0) | Pyright reported 0 errors. Workspace verify also passed TS typechecks. |
| Tests | `pnpm run python:test`; `CI=1 NX_DAEMON=false pnpm run verify` | Pass (exit 0) | 499 Python tests passed (11 warnings); root Nx workspace gate passed. |
| Build / Compile | `pnpm exec nx run quant-engine:openapi-check --skip-nx-cache`; SDK `generate:check`; DSH verify | Pass (exit 0) | Canonical OpenAPI/SDK and plugin build, lint, tests and bundle check passed. |
| Dependency and secret checks | `pnpm run security:deps`; npm/Python SBOM; `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | Pass (exit 0) | pip-audit skipped 6 editable Python packages; npm SBOM contains 200 components; Python SBOM target passed; no leaks found in ~35.47 MB. |
| Nx project graph | `pnpm exec nx show projects`; `pnpm exec nx graph --file=/tmp/bybit-quant-nx-graph.json` | Pass (exit 0) | 9 projects discovered; graph has `quant-engine` edges to data, risk, execution, portfolio and strategies. |

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-001–AT-007 | Decision through synthetic native admission; independent risk; replay, conflict and uncertainty protection | Partial | Python API tests exercise filled and risk-rejected orders, selector mismatch, stale fixture bars, durable receipt replay, payload conflict and concurrent single-owner claim. Full DSH entry path and every dirty-restart/uncertain-dispatch boundary are not proven. |
| AT-008–AT-009 | Dashboard filters remain view-only; abstention records a no-order outcome | Partial | UI render/integration checks and Python abstain receipt exist; DSH loop does not submit its decision to the paper API. |
| AT-010–AT-013 | Internal-paper-only decision path and registry-backed Host candidate universe | Partial | Python cycle API is internal-paper-only and fixture-owned. The active DSH loop still uses its Bybit-backed universe and local journal; the scheduler also accepts Testnet research mode. |
| AT-014 | DSH Host reads registry, posts cycle and performs same-key receipt lookup | Partial | `host-tools-ai.ts` now calls the paper facade for literal `internal_paper`, validates candidate/evidence identity and performs same-key lookup after an uncertain POST. The deployed bootstrap still has no registry injection and no Host-to-service E2E receipt exists. |
| AT-015 | Isolated migration/recovery gate with network denied and legacy ORM compatibility | Pass | Migration/recovery tests use `tmp_path` SQLite, deny network, verify 0006 and preserve legacy command queries through downgrade/re-upgrade. |
| AT-016 | AI selects different eligible symbols from fixture bundles A/B and matching OMS routes them | Partial | Python API tests prove ALPHA and BETA-PERP reach matching native fixtures; Host selection is now bound to the returned fixture snapshot, but bundle A/B Host E2E is not connected to a deployed service. |
| AT-017–AT-018, AT-020, AT-022 | Bar/evidence-driven selector identity; stale, missing or insufficient data fail closed | Partial | Service runs the registered selector and checks strategy/evidence identity; mismatch and stale fixture cases exist. Full no-mapper/no-admission coverage for every missing/insufficient-bar and Host case remains incomplete. |
| AT-019, AT-021 | Shared safe symbol grammar | Pass | Registry, portfolio and native instrument compatibility tests cover accepted dynamic symbols and malformed syntax. The Define duplicates these requirements; remove the duplicate in its next revision. |
| AT-023 | Complete canonical pairwise synthetic correlation matrix | Pass | Registry, DTO, API and two-symbol admission tests reject missing, duplicate/reversed and out-of-range values. |
| AT-024 | Atomic cycle claim, append-only events, same-key replay/conflict and restart protection | Partial | Transactional receipts, immutable events, replay/conflict and concurrent single-owner tests pass. Lease-expiry/restart protection at every specified crash boundary remains incomplete. |

## Advisor Ledger

None — no formal external review was executed.

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Native sandbox paper path originally represented one instrument per session. | Expanded manifest-listed models/runtime/worker/native code to support registered multi-symbol fixtures. | Python bundle/OMS integration passes; DSH Host routing remains separate and incomplete. |

## Deviations from Design

| # | Deviation | Decision | Record |
|---:|---|---|---|
| 1 | Design originally named `ai_paper_orchestrator.py`, while `paper_cycle_service.py` implements selector→portfolio→mapper→admission and durable service adaptation. | Consolidate the Design entry into item 7 at `paper_cycle_service.py`; remove the duplicate service item instead of adding a forwarding module. | Design revision 1.9. |
| 2 | DSH transport/prompt remain disconnected: Host `engine.ts` is read-only and active prompt v4 writes local simulated decisions. | Keep LP-001 pending; complete the loop-spec/prompt gate and Host capability boundary before claiming end-to-end autonomous paper. | No exchange-write permission added. |

## Blockers

| Blocker | Required Action | Owner |
|---|---|---|
| DSH Host does not call the registry-backed paper cycle; fixture provisioning is test/service injection only. | Implement bounded authenticated loopback client, safe capability acquisition, service lifecycle/provisioning and end-to-end Host tests; complete LP-001 loop/prompt receipts. | Build |
| Four manifest paths are absent: `background-loop-v5.ts`, `test_ai_paper_orchestrator.py`, `test_paper_bootstrap_loopback.py`, and `test/ai-paper-cycle.ts`. | Reconcile alternate test-path coverage in Design; implement missing Host transport/prompt pieces and prove fail-closed behavior. Existing `test_service.py` checks shared `loopback_host` but is not the dedicated paper-bootstrap receipt. | Build |
| Full product exchange cutover remains outside this synthetic-paper slice. | Complete Testnet execution adapter, account/order reconciliation, cancellation/emergency stop and restart recovery in the separate cutover scope; keep Mainnet locked. | Parent product |

## Final Status

### Receipt split checkpoint (2026-11-20; historical state, superseded by the revision 1.9 manifest)

- Manifest count is now 51. `paper_admission.py` is 496 lines; `cycle_receipt_store.py` is 120 lines; `paper_cycle_service.py` is 72 lines.
- `uv run --project python --locked pytest python/packages/quant-data/tests/test_migrations.py python/apps/quant-engine/tests/test_ai_paper_recovery.py -q` exited 0 with 14 passed.
- Scoped Ruff for the touched receipt/service/admission/test files exited 0 after import and Decimal-literal fixes.
- Receipt DAO and helper split are verified; production AI-cycle orchestration and API handler replacement remain pending, so the overall Verify Gate remains inconclusive.

### Default cycle service/API checkpoint (2026-11-20; before successful dispatch coverage was added)

- `create_paper_app` routes to the real `PaperCycleService` whenever an explicit fixture registry is supplied. Injected cycle handlers/lookups are now rejected unless the caller explicitly sets `test_only=True`; the test seam cannot silently replace production orchestration.
- The API test exercises default POST → durable abstain receipt → closes the app → creates a new app on the same `pytest tmp_path` SQLite file → GET returns the identical receipt. A second real-service POST verifies selector identity mismatch produces terminal `rejected` with `selector_identity_mismatch`. DTO/OpenAPI/SDK now preserve `rejected` instead of coercing it to `unknown`.
- `uv run --project python --locked pytest python/apps/quant-engine/tests/test_fixture_registry_api.py python/apps/quant-engine/tests/test_ai_paper_recovery.py -q` — exit 0, 6 passed, one upstream Starlette/httpx deprecation warning. After adding the explicit rejection assertion, `uv run --project python --locked pytest python/apps/quant-engine/tests/test_fixture_registry_api.py -q` — exit 0, 3 passed, same warning.
- `uv run --project python --locked pyright python/apps/quant-engine/src/quant_engine/paper_cycle_service.py python/apps/quant-engine/src/quant_engine/paper_api.py` — exit 0, 0 errors/warnings/informations. Scoped Ruff over the touched service/API/DTO/test files — exit 0.
- `pnpm exec nx run quant-engine:openapi-check --skip-nx-cache` — exit 0. Initial SDK `generate:check` correctly reported drift after the DTO addition; `pnpm exec nx run @bybit-quant/quant-api-client:generate` then `...:generate:check` — both exit 0.
- At that checkpoint, successful dispatch and the full Define Verify Gate were unproven. The 2026-11-21 tests below supersede that limited status for the isolated Python cycle path.

### Spread threshold checkpoint (2026-11-21)

- The independent evaluator's exact spread rule is `ask - bid > max_spread_fraction * ((ask + bid) / 2)`. `risk_context` copies the native instrument snapshot's bid/ask for the requested symbol without a quote rewrite or binary float conversion.
- With the default `max_spread_fraction=0.001`, bid `10` and ask `10.1` produce spread `0.1` versus an allowed `0.01005`, so `spread_limit` is the intended veto. This policy was not loosened.
- The API integration gate now parameterizes both sides of the unchanged default limit: ask `10.001` yields a filled positive path (spread `0.001` versus allowed `0.0100005`); ask `10.1` yields `risk_rejected` and persisted `spread_limit`.
- Focused command: `uv run --project python --locked pytest -q python/apps/quant-engine/tests/test_fixture_registry_api.py python/apps/quant-engine/tests/test_ai_paper_recovery.py python/apps/quant-engine/tests/test_admission.py` — exit 0, 14 passed (one upstream Starlette/httpx deprecation warning).
- `uv run --project python --locked ruff check python/apps/quant-engine/tests/test_fixture_registry_api.py` — exit 0. No production source changed.

### Current workspace verification and boundary (2026-11-21)

- `pnpm run python:test` — exit 0; 499 passed, 11 deprecation warnings.
- `pnpm run python:lint` — exit 0; Ruff checks and 110-file format check passed.
- `pnpm run python:typecheck` — exit 0; 0 errors.
- `CI=1 NX_DAEMON=false pnpm run verify` — exit 0; workspace build, DSH tests/typechecks/lint, bundle and contract checks passed.
- `pnpm run security:deps`, `pnpm run sbom`, `pnpm exec nx run quant-data:sbom`, Nx project/graph checks, `gitleaks dir`, and `git diff --check` — exit 0. npm SBOM: 200 components; pip-audit skipped 6 editable Python packages; 9 Nx projects found; secret scan found no leaks in approximately 35.47 MB.
- The active DSH runtime imports `background-loop-v4.ts`, whose `quant_decide_background` tool commits to the local AI journal. `engine.ts` only reads engine health, market and strategy evidence; it has no paper-cycle methods. Consequently the completed Python synthetic cycle is not yet reachable from DSH unattended operation.
- No Testnet/Mainnet order was submitted. The existing Bybit execution provider/preflight remains GET-only with `order_submission_allowed=False`.

### 2026-11-22 uncertain-receipt scheduler guard

The Host internal-paper path now maps `partially_filled` together with
`admitted`, `accepted`, `protected`, `unknown`, `claimed`, and `selected` to a
distinct `uncertain` scheduler receipt. These states are not confirmed fills;
the scheduler records the raw paper receipt, blocks automatic rescheduling,
and requires reconciliation of the original request identity before another
cycle can run. The UI readiness copy distinguishes this state from an ordinary
risk rejection. A regression test covers the block and proves no next-cycle
timer is queued.

Receipt: `pnpm --dir apps/dsh-plugin run verify` — exit 0 (build, lint,
source/test typechecks, unit tests and bundle check; five existing non-blocking
lint warnings). This remains an offline safety-boundary change; no exchange
request or order was sent.

### Final verification rerun (2026-11-22)

- `pnpm --dir apps/dsh-plugin run verify` — exit 0; build, lint, source/test
  typechecks, 19 unit suites and the packed Bundle boundary scan passed. The
  five existing Oxlint warnings remain non-blocking.
- `pnpm run python:test` — exit 0; 499 tests passed with 11 upstream
  deprecation warnings.
- `git diff --check` — exit 0.

These receipts only validate the offline safety boundary and local synthetic
components. They do not establish deployed Host-to-Python unattended-cycle
reachability or exchange execution authority.

## 2026-11-22 bootstrap fixture provisioning and process receipt

The deployment boundary now provisions one immutable `builtin-synthetic`
bundle inside `paper_bootstrap.py` from the already-created canonical
`synthetic_config` fixture. The provisioning helper generates bounded synthetic
bars and fixture-owned selector evidence in memory; it accepts no fixture file,
network feed, environment credential or model argument. Bootstrap passes this
registry to `create_paper_app` in both private-broker and capability-FD modes,
while the API still fails closed when no registry is injected by another caller.

The design statement that `paper_bootstrap.py` remains unchanged is recorded as
drift: the deployed process needed explicit trusted provisioning to make the
already-tested fixture and AI-cycle routes reachable. A subprocess regression
now starts the real CLI, authenticates `GET /fixtures/builtin-synthetic`, posts
an `abstain` AI cycle, and recovers the identical durable receipt by its
original request ID; unauthenticated fixture access remains `401`.

| Check | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest python/apps/quant-engine/tests/test_paper_process.py python/apps/quant-engine/tests/test_fixture_registry_api.py -q` | 0 | 12 passed; process fixture/cycle and existing API recovery coverage passed; one upstream Starlette/httpx deprecation warning. |
| `uv run --project python --locked ruff check ...` | 0 | Bootstrap, registry and process test files clean. |
| `uv run --project python --locked pyright ...` | 0 | Bootstrap and registry source report 0 errors, warnings or informations. |

This receipt proves process-level internal-paper fixture/cycle reachability only.
It does not enable exchange writes, Testnet order submission, Mainnet access,
prompt evaluation, scheduler persistence, lease recovery or full unattended
DSH operation. Overall product status remains **PARTIAL**.

### Non-dispatch failure guard (2026-11-22)

`host-tools-ai.ts` now releases the cycle reservation on a typed, non-ambiguous
`paper.cycle` failure (`control_disabled`, `invalid_request`, HTTP denial, and
similar) instead of converting it into an `uncertain` receipt. Only transport
ambiguity, or a failure after dispatch without a reconcilable receipt, blocks
the scheduler as `uncertain`. The guard preserves retryability without
claiming a fill.

`test/paper.ts` also proves a locally disabled cycle makes no provider, HTTP,
or mutation call.

Receipt: `pnpm --dir apps/dsh-plugin run verify` — exit 0 after adding the
regression assertion. The assertion confirms the disabled cycle adds no
provider resolution, HTTP request, or mutation. No exchange request or order
was sent.

### Overall: INCOMPLETE

- [ ] All File Manifest tasks completed
- [ ] Incremental verification recorded
- [ ] Verify Gate green or manual-ux receipt positive
- [ ] Complementary checks applicable pass
- [ ] Acceptance Tests verified
- [ ] LLM prompt receipts complete when required
- [ ] Drift decisions recorded
- [ ] Advisor findings disposed when applicable
- [ ] No unresolved blocker
- [ ] No TODO/FIXME used as unfinished implementation

## 2026-11-21 Host transport facade continuation

`apps/dsh-plugin/src/lib/engine-paper.ts` now exposes typed `fixture`, `cycle` and
`cycleRequest` methods over the existing private-capability SDK. Fixture and
receipt identities are checked at the Host boundary; cycle submission requires
the configured session and literal `internal_paper`, and an ambiguous response
retains the original request ID for query-only recovery. The public client entry
exports the generated fixture/cycle DTO types.

This completes only the cohesive Host wire facade. `host-tools-ai.ts` and the
active background prompt still write the local AI journal; they do not call the
new methods. `paper_bootstrap.py` still does not provision/inject a
`SyntheticFixtureRegistry`, so the packaged service returns unavailable for
fixture/cycle routes. AT-014 and unattended DSH→Python execution remain
**not met**; no end-to-end autonomous-cycle claim follows from these changes.

| Check | Command | Result |
|---|---|---|
| Host facade types | `pnpm exec nx run @bybit-quant/dsh-plugin:typecheck --skip-nx-cache` | Exit 0 after correcting the response type to distinguish session-scoped status/commands from fixture/cycle DTOs. |
| DSH bundle build | `pnpm --dir apps/dsh-plugin run build` | Exit 0. |
| DSH unit suite | `pnpm --dir apps/dsh-plugin run test:unit` | Exit 0; native-paper Host tests passed. Coverage includes valid fixture/cycle/readback, original identity, and mismatched session rejection. |
| Attempted focused test alias | `pnpm --dir apps/dsh-plugin run test:paper` | Exit 1; package has no such script. The supported `test:unit` command was run and passed. |

## 2026-11-21 plugin Verify Gate follow-up

The paper facade test now narrows `invalidCycle` using `ok === false` before
reading its error code. `pnpm --dir apps/dsh-plugin run verify` exited 0 after
the correction. This verifies the plugin build, lint, source/test typechecks,
unit suite, and Bundle checks; Oxlint emitted five existing non-blocking
warnings. The Host AI decision tool still does not call the new fixture/cycle
facade, and `paper_bootstrap.py` still does not inject a
`SyntheticFixtureRegistry`. AT-014 and the DSH→Python unattended cycle remain
not met.

## 2026-11-22 deployment-provisioning correction

The preceding Host-facade receipt is historical. The current
`paper_bootstrap.py` injects a built-in, credential-free
`SyntheticFixtureRegistry` for both supported startup transports, so the
packaged process can serve the fixture and AI-cycle routes. The process test
starts the real CLI, retrieves `builtin-synthetic` with the private capability,
submits a bounded `long` cycle and resolves the durable receipt with the original
request ID; an unauthenticated fixture request is rejected. This closes the
bootstrap provisioning gap for **internal paper only**.

Latest verification: the full Python package/app suite exited 0 with 396
passed and 11 upstream/deprecation warnings; Python Ruff and Pyright exited 0;
the DSH plugin Verify Gate exited 0; and `git diff --check` exited 0. This
receipt still does not satisfy AT-014 for the unattended DSH scheduler: prompt
evaluation, scheduler persistence, lease/restart recovery, Testnet execution
authority and Mainnet execution remain open. Overall status remains
**INCOMPLETE/PARTIAL** and no exchange order was sent.

The subsequent repository-wide gate `pnpm run python:test` exited 0 with 500
passed and 11 upstream/deprecation warnings. The root
`CI=1 NX_DAEMON=false pnpm run verify` gate exited 0, and dependency audit,
both SBOM targets and the redacted gitleaks scan exited 0. These checks do not
upgrade the internal-paper receipt into Testnet/Mainnet execution readiness.

The scheduler's optional Agent-service type guard and model-selection
normalizer were extracted into `apps/dsh-plugin/src/lib/ai-agent-services.ts`.
This information-hiding refactor keeps lifecycle and receipt policy in the
scheduler while the new module owns the untrusted service boundary; both
handwritten files remain below 500 lines. The DSH Verify Gate passed after
the refactor.

## 2026-11-22 Host AI-cycle process receipt

The packaged process harness now drives the opt-in `internal_paper` background
Agent through the real Host tools. The fake Agent performs the model-facing
sequence (`quant_brief` candidate discovery, fixture-owned selector-evidence
selection, and `quant_decide_background`); the Host reads the authenticated
Python fixture, submits one bounded cycle, and queries the durable receipt with
the original request ID. The receipt returned terminal synthetic `filled`
status and the scheduler mapped it to `open`; no local AI journal write or
Bybit request occurred. The harness also retained its command, risk-veto,
uncertain-503, child-reaping and protected-restart checks.

```text
pnpm --dir apps/dsh-plugin run test:paper-process  # exit 0
{"result":"ok","environment":"internal_paper","synthetic":true,
 "commands":4,"native_filled":3,"risk_rejected":1,
 "injected_postdispatch_503":true,"actual_fault_submit_posts":1,
 "host_close_survived":true,"native_reaped":true,"listeners_closed":true,
 "restart":"protected","capability_disclosed":false}
```

The TypeScript SDK permits only bounded integer fields whose key ends in `_ns`
to exceed JavaScript's safe-integer limit; ordinary numeric fields remain
strictly fenced. `pnpm --filter @bybit-quant/quant-api-client test` exited 0
with 25 tests, including acceptance of epoch nanoseconds and rejection of an
oversized confidence value. This is a reproducible internal-paper process
receipt, not proof of a persistent unattended loop: prompt evaluation,
scheduler lease/restart recovery, Testnet execution authority, reconciliation
and all Mainnet writes remain open.
