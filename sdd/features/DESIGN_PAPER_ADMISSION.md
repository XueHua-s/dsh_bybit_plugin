# Paper admission integration

Status: Concrete scoped design, 2026-11-17. Parent-authorized parallel Build; independent review pending.
Sources: BRAINSTORM_BYBIT_AI_QUANT, DEFINE_BYBIT_AI_QUANT, DESIGN_BYBIT_AI_QUANT, DESIGN_EXECUTION_CUTOVER. No new requirements or LLM prompts. Full exchange/AI cutover remains open.

## Boundaries and contracts

The optional paper service owns one serialized account writer, actual quant_risk.evaluate, durable quant-data admissions, and a long-lived quant_execution.PaperRuntime. The existing public-market app remains unchanged/default. Only internal_paper, synthetic BTC fixture, LIMIT proposals are available. Caller cannot supply balances, policy, market truth, leverage, account identity or arbitrary metadata.

PaperRuntime uses immutable PaperFixture/Depth/Order/Event/Snapshot DTOs and hides native Nautilus spawned process/OMS. Native account SIM-001. Explicit finite depth with fixed observation timestamp expires; no fabricated liquidity refresh. Accepted risk price bounds are submitted as native LIMIT. Engine ingests native events before admission and continuously; durable event commit precedes advertised state. Persistence failure freezes admission/native submission.

Durability finalized: AdmissionStore owns scoped session/owner read, atomic decide(command+decision+reservation), claim_dispatch with stored decision generation/expiry CAS, NativeObservation cumulative fill/notional/fee, record_native audit-only events, protect and get_by_request. All timestamps ns. Manifest excludes SQL/migrations. flock on an adjacent database lock prevents concurrent process writers. Existing unsettled, inflight, nonflat, or unclean session cannot restart automatically. New session requires a new explicit isolated database/session configuration; no silent balance reset or full recovery claim.

HTTP canonical strict Pydantic DTOs own OpenAPI. Routes: authenticated POST /api/v1/trading/start and /stop, POST /api/v1/trading/commands, GET /api/v1/trading/commands/{command_id}, GET /api/v1/trading/commands/by-request/{request_id}, GET /api/v1/trading/status. Scope is a single configured session; capability carries observation/control principal scopes. Capability arrives only inherited FD into process memory, constant-time comparison; no CLI/env/config/JSON token. Origin requests rejected. Bounded request bodies, queue, opaque identifiers, decimal strings; validation errors return fixed code and never echo input. Optional paper bootstrap requires explicit pre-migrated isolated SQLite path; no implicit migration.

## File manifest

All below owned by paper_admission_integration. Dependencies: risk evaluator and accepted data foundation; data admission additions and native facade must be finalized before dependent implementation.

- python/apps/quant-engine/src/quant_engine/paper_config.py: immutable trusted fixture/policy/config and FD capability loading.
- python/apps/quant-engine/src/quant_engine/paper_admission.py: serialized risk/admission/native event lifecycle.
- python/apps/quant-engine/src/quant_engine/paper_context.py: native snapshot to risk context, scoped conversion.
- python/apps/quant-engine/src/quant_engine/paper_api_models.py: sole wire schema.
- python/apps/quant-engine/src/quant_engine/paper_api.py: auth, bounded redacted HTTP routes/lifespan.
- python/apps/quant-engine/src/quant_engine/paper_bootstrap.py: explicit optional CLI and secure inherited FD.
- python/apps/quant-engine/src/quant_engine/bootstrap.py: offline combined schema export only if parent schema owner requires.
- python/apps/quant-engine/pyproject.toml: dependencies and paper CLI.
- python/apps/quant-engine/project.json: actual Nx dependency edges.
- python/apps/quant-engine/tests/test_admission.py: real evaluator, persistence, replay, reservation, failures.
- python/apps/quant-engine/tests/test_command_api.py: auth/scope/redaction/strict proposals.
- python/apps/quant-engine/tests/test_paper_process.py: separate-process lifecycle, capability, SIGTERM/crash.
- sdd/features/DESIGN_PAPER_ADMISSION.md: this design/contracts/drift.
- sdd/reports/BUILD_REPORT_PAPER_ADMISSION.md: actual command and acceptance receipts.

## Design rationale and review

Deep admission boundary owns risk generation, durable reservation, dispatch authority and event persistence; HTTP is transport only. Native implementation changes do not affect HTTP DTOs. Trusted context construction is separate because it owns valuation/freshness rather than transport/persistence. Provisional 8/10: newcomer documentation and replaceable native boundary are explicit; durable integration and lifecycle evidence remain unverified (not 10/10 until review/tests).

## Verification

Run engine Ruff, Pyright, pytest including real native and subprocess tests. Required evidence: no overcommit/replay dispatch, LIMIT price enforced, runtime survives HTTP calls, strict scoped auth, input redaction, stale generation veto, persistence protects, second writer fails, SIGTERM bounded disposal, restart protected. Root full Verify Gate/release is parent-owned.

## Approved drift

Official TradingNode installs process signals. Parent approved dedicated spawned native process, preserving public facade and bounded private IPC, rather than private constructor thread workaround. Canonical paper OpenAPI is separate quant-paper.v1.json (SDK agent owns exporter/bootstrap and generated artifacts); default market app remains unchanged. Native worker failure/forced cleanup protects uncertain orders.

Manifest extension before additional failure work: `python/apps/quant-engine/tests/test_admission_failures.py` owns persistence/claim/generation/shutdown failure injection independently of normal native flow. Account-valuation drift found during parent review: spot cash accounting does not represent CryptoPerpetual equity. Data/native owners must correct derivative realized/unrealized/fees before acceptance; engine context will use genuine native marked equity and reconcile durable wallet/position state. No false cash-as-loss estimate is accepted.

## Final derivative and failure invariants

Session accounting is explicitly LINEAR_PERPETUAL: durable wallet equals initial wallet plus gross realized PnL minus cumulative commissions. Position average entry owns partial-close/reversal basis. Native portfolio realized PnL is net of commissions, so reconciliation compares durable gross realized minus fees to native realized; fees are not subtracted twice. Marked equity is wallet plus signed position UPL at bid for longs and ask for shorts. Risk uses the lesser of independently consistent durable/native marked equity. Native raw free margin excludes UPL in pinned Nautilus; `available_equity=min(raw_free,raw_free+UPL)` removes adverse UPL without granting profitable UPL credit. These are separate wallet, equity and available measures. Native snapshot acquisition timestamp is recorded without refreshing delivered market timestamp.

Durable protection is authoritative even when claim returns `(False, READY)` on expiry; the service freezes native admission and readiness immediately. Initial event-drain failure protects before writer release. Native protect/cancel/event failures cannot skip durable protection or bounded stop/reap; close releases flock in finally. Incomplete native event stream/status or dead process never reports ready. Private process ownership is independently verified after service SIGKILL, including dispatched/nonflat commands; old commands remain queryable and session protected, with no resubmission.
