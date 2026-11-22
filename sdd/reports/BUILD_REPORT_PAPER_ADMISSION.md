# BUILD REPORT: Paper admission integration

## Metadata

| Attribute | Value |
|---|---|
| Feature | Explicit internal-paper service admission |
| Date | 2026-11-17 |
| Author | paper_admission_integration, SDD Build |
| BRAINSTORM | sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md |
| DEFINE | sdd/features/DEFINE_BYBIT_AI_QUANT.md |
| DESIGN | sdd/features/DESIGN_BYBIT_AI_QUANT.md; DESIGN_EXECUTION_CUTOVER.md; DESIGN_PAPER_ADMISSION.md |
| Status | Complete for scoped paper admission; parent full-product Verify Gate/release separate |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | Six implementation modules, four test modules, engine metadata, scoped design/report; exporter delegated SDK owner; Nx targets workspace owner |
| Cross-file coupling | High: real quant-risk evaluator, transactional quant-data admission, long-lived native facade |
| Security surface | Scoped FD capability, loopback HTTP, session ownership, durable native dispatch |
| LLM prompt items | None added; full-product LLM requirements remain open |
| Independent volume | Parent explicitly delegated parallel owners and independent reviewers |
| Context-rot risk | Explicit DTO contracts documented before dependent service |
| Runtime capabilities | Parent-authorized parallel workers; implementation sequential inside this scope |

Recommendation and decision: follow parent-authorized work distribution, no repeated mode permission. Independent review performed by paper_service_review; final verdict ACCEPT in sdd/reviews/REVIEW_PAPER_ADMISSION_2026-11-17.md.

## Summary

Optional paper CLI/app runs separately from unchanged default public-market observer. Strict Pydantic schema owns separate paper OpenAPI; inherited private pipe provides capability. A bounded entrance retains capacity across client cancellation; one serialized writer owns real evaluator, atomic command/decision/reservation, stored generation/expiry dispatch CAS, native event persistence, background ingestion and shutdown. flock fences competing account processes. Restart always protects prior session; there is no native replay or silent balance reset.

Native official TradingNode runs in a spawned child process with bounded private IPC; parent death watchdog reaps it. Only synthetic fixed-depth LIMIT orders are admitted. No exchange connection, private credential resolution, Mainnet/Testnet/Demo order, generated strategy execution or complete AI/research cutover is implemented here.

## Task Execution

| Task | Executor | Status | Evidence |
|---|---|---|---|
| Scoped design/contracts/manifest | this worker + data/native owners | Done | DESIGN_PAPER_ADMISSION documented before source |
| Auth/config/wire/API/bootstrap | this worker | Done | Strict input/redaction/Origin/auth scope tests |
| Durable account admission/native event ingestion | this worker | Done | Actual evaluator, ledger/native tests |
| Economic alignment | this worker + native/data owners | Done; scoped independent ACCEPT | Derivative wallet+gross realized-fees, bid/ask UPL, native marked equity and marked available |
| Process lifecycle/crash | this worker | Done | Three separate-process tests |
| Root Verify Gate/release | parent | Pending | Scoped tests do not substitute full product gate |

## Files Changed

Created: `python/apps/quant-engine/src/quant_engine/paper_config.py`, `paper_context.py`, `paper_admission.py`, `paper_api_models.py`, `paper_api.py`, `paper_bootstrap.py`; tests `test_admission.py`, `test_admission_failures.py`, `test_command_api.py`, `test_paper_process.py`; this report and scoped design. Modified engine `pyproject.toml` dependencies/CLI and `project.json` dependency edges. SDK worker owns bootstrap schema exporter; workspace worker owns additive paper schema Nx targets. No SQL/migration file owned or modified by this worker. Tests migrate only explicit temporary SQLite fixtures via existing protected migration function; service never migrates.

## Drift Detected

| Drift | Decision | Action |
|---|---|---|
| Official TradingNode installs process signals | Parent approved process owner instead of private thread constructor workaround | Spawned native facade; process lifecycle and owner-death evidence |
| Combined schema would imply unavailable routes in separate runtime | Parent approved separate Python-generated paper contract | SDK worker keeps readonly contract intact |
| Initial durable cash semantics were spot but native instrument perpetual | Parent required faithful derivative accounting | Data owner explicit LINEAR_PERPETUAL model; engine reconciles wallet/net-realized and uses real marked equity |
| Raw native free margin excludes adverse UPL in pinned Nautilus | Reviewer identified; explicit native available_equity contract | Engine consumes marked available, no profitable UPL credit |

## Verification Results

### Incremental Verification

| Command / Method | Exit | Evidence |
|---|---:|---|
| `uv run --project python --locked ruff check python/apps/quant-engine --fix` | 2 | Sandbox could not create uv cache temporary lock; no lint ran |
| `python/.venv/bin/ruff check python/apps/quant-engine --fix` | 0 final | Direct existing environment executable; actual fixes applied |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python -p python/pyproject.toml python/apps/quant-engine` | 0 | 0 errors/warnings |
| Initial temp DB/native tests | 1 intermediate | Zero-byte SQLite migration sidecar guard; corrected fixture initialization to real SQLite header and closed connection. Revision identifier aligned to actual 0004_admission_state. Native equal-precision fixture conversion corrected by native owner. No migration guard bypass |
| `python/.venv/bin/pytest python/apps/quant-engine/tests/test_admission.py python/apps/quant-engine/tests/test_command_api.py -x -q` | 0 | Initial five tests passed; later expanded |
| `python/.venv/bin/pytest python/apps/quant-engine/tests/test_admission_failures.py -q` | 0 | 3 passed, 3.05s |
| `python/.venv/bin/pytest python/apps/quant-engine/tests/test_paper_process.py -x -q` | 0 | 3 passed, 10.28s, escalated loopback execution after sandbox bind denied |
| `python/.venv/bin/pytest python/apps/quant-engine/tests -q` | 0 | 114 passed, 20.09s; one existing Starlette httpx deprecation warning |
| `git diff --check` | 0 | No whitespace errors at receipt |

Final full-engine receipt after all scoped changes: `python/.venv/bin/pytest python/apps/quant-engine/tests -q`, exit0, 115passed20.42s; one Starlette httpx deprecation warning. Required subprocess test execution used approved isolated loopback escalation.

### Verify Gate

| Attribute | Value |
|---|---|
| Kind | Scoped test + lint + typecheck |
| Command | Engine pytest/Ruff/Pyright above |
| Exit / Result | Exit0, final115 engine tests20.42s; Ruff0; Pyright0 |
| Status | Scoped Green and independent ACCEPT; full DEFINE gate parent-owned |
| Manual UX | N/A; no new UI |

## Acceptance Test Verification

| Requirement | Evidence | Limits |
|---|---|---|
| AT-010 independent service lifetime | Separate CLI HTTP/process test, closed clients, SIGTERM child cleanup | Synthetic paper only |
| AT-012/021 risk admission | Actual evaluator, finite depth depletion, no caller truth, concurrent reservations, stale fixture veto | Full Testnet/provider risk certification remains open |
| AT-014/029 durable stable IDs/events | Same request stable command/native identity, cumulative native observation persists, by-request recovery lookup | No exactly-once venue execution guarantee |
| AT-015 uncertain recovery | Active service crash reaps orphan native, preserves old command, restart protected | No replay/reconstruction accepted |
| AT-016 scoped environment/session | Literal internal_paper, scoped capability and store reads, no caller account/config truth | Live credential provider deferred |
| AT-022 stop | Freeze, cancel request, durable protect, bounded native stop/reap even failure | Flatten/complete emergency workflow deferred |
| AT-013 schema | Canonical Pydantic paper models and separate generated SDK owned peer | Full DSH controls integration deferred |

## Advisor Ledger

| Note | Severity | Decision | Evidence |
|---|---|---|---|
| Initial drain error must protect synchronously | HIGH | APPLIED | Entire serialized admission fail-protect boundary + injected test |
| Native protect/cancel error must not skip durable protection/reap/lock release | HIGH | APPLIED | Independent failure probes and own native failure test |
| Check status/event_stream_complete, not merely process alive | HIGH | APPLIED | Admission and background ingest checks, readiness false on stale/failed |
| Native/durable derivative valuation and marked availability | HIGH | APPLIED; independent scoped ACCEPT | Explicit accounting model/marked snapshots/context |
| Huge Content-Length int conversion | MEDIUM | APPLIED | Bound string length before conversion, fixed413 |
| Dot-only path keys normalize in JS URL | MEDIUM | APPLIED | Canonical first-character alphanumeric IDs on bodies and GET paths |
| Generation check must bind persisted decision | HIGH | APPLIED | Data stored decision-generation CAS plus engine expected generation+1 |

## Issues Encountered

Sandbox blocked uv cache and loopback listener; direct existing venv commands and approved escalated isolated subprocess tests provided real evidence. Pyright needs explicit workspace configuration/interpreter when run directly. Uvicorn restores SIGTERM after graceful cleanup; process test accepts documented signal exit only while requiring native PID gone. Test fixtures contain only synthetic capabilities and fixture data. No user secrets were read.

## Deviations from Design

Only approved drift above. Conservative restart protects even a clean stopped flat session because native Sandbox replay is unavailable; new explicit isolated session is required. The implementation does not claim full recovery, sole-exchange TS cutover, DSH installation, full AI/research or release completion.

## Blockers

No unresolved scoped implementation/review blocker. Parent root full Verify Gate, security/SBOM scans and release remain separate acceptance work. No commit/push/install was performed by this worker.

## Final review refresh

Independent paper_service_review verdict: ACCEPT. Final seven independent probes passed in 6.36s after expiry propagation fix; economic probes cover marked equity, daily loss, marked available, long close/short reopen, wallet and gross/net realized fee reconciliation. Prior combined 15-probe pass18.19s additionally covered private FD auth/process lifetime, generation/claim failures, single native replay dispatch and cleanup faults. Explicit claim-expiry regression in repository: 4 failure tests passed5.05s; Ruff/Pyright/diff-check exit0 after fix. Final full-engine refresh: 115passed20.42s, exit0 after all scoped source changes.

## Final Status

Overall: COMPLETE for this scoped paper integration. Parent full-product gate/release acceptance remains separate.

## Next Step

Execute o **SDD Handoff by RDD**.
