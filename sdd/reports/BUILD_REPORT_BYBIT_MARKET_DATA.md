# BUILD REPORT: Bybit Public Testnet Market Data

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | BYBIT_MARKET_DATA |
| **Date** | 2026-11-17 |
| **Author** | SDD Build by RDD (scoped increment) |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **DESIGN** | `sdd/features/DESIGN_BYBIT_AI_QUANT.md` |
| **Status** | Complete (scoped increment; broader feature remains phased) |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 3 scoped groups (adapter, tests, uv dependency/lock) |
| Cross-file coupling | Medium; adapter is isolated behind a four-method consumer API |
| Security surface | Public unauthenticated Testnet inbound stream; no credentials or order endpoints |
| LLM prompt items | None in this increment |
| Independent volume | Three deterministic transport/lifecycle scenarios |
| Context-rot risk | Low; focused Python package change |
| Runtime capabilities | Default execution mode |

**Recommendation:** default mode, because this is a bounded adapter increment with mockable dependencies.

**User decision:** authorized by the parent task instruction.

**Pre-build review:** not available; software-design-philosophy was applied internally.

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 3/3 |
| **Files Created** | 3 |
| **Files Modified** | 4 |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 22 (including an initial lint failure corrected before final checks) |
| **Python adapter gate** | Pass — focused pytest 4 passed, with Python static checks passing |
| **Root TS Verify Gate** | Separate scope; see `VERIFY_GATE_2026-11-17.md` for the current `pnpm run verify` receipt |
| **Execution Mode** | default |

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---:|---|---|---|---|---|
| 1 | 19 | Add typed public Testnet WebSocket adapter | direct | Complete | focused pytest, pyright, ruff | all pass; final source 229 lines |
| 2 | 20 | Add deterministic fake-socket tests | direct | Complete | pytest | 4 focused pytest cases pass; fake socket, no network |
| 3 | 21 | Add uv `websockets` dependency and lock | direct | Complete | `uv lock` | exit 0; resolved websockets 15.0.1 |

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `python/apps/quant-engine/src/quant_engine/market_data.py` | Create | 19 | Yes | Public Testnet only; no auth/order/account code |
| `python/apps/quant-engine/tests/test_market_data.py` | Create | 20 | Yes | Fake connector/socket; no CI network |
| `python/apps/quant-engine/src/quant_engine/__init__.py` | Modify | 19 | Yes | Exports typed adapter API |
| `python/apps/quant-engine/pyproject.toml` | Modify | 21 | Yes | `websockets>=13,<16` |
| `python/uv.lock` | Modify | 21 | Yes | uv lock refresh |
| `sdd/features/DESIGN_BYBIT_AI_QUANT.md` | Modify | 19 | Yes | Ownership, data flow, manifest and error handling |
| `sdd/reports/BUILD_REPORT_BYBIT_MARKET_DATA.md` | Create | — | Yes | This scoped evidence report |

## Drift Detected

No material drift detected. The existing Design called the WebSocket adapter planned; this increment realizes the planned inbound public Testnet boundary without changing REST, DSH, strategy, risk, persistence or Mainnet scope.

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Adapter | `uv run --project python --group dev pytest -q python/apps/quant-engine/tests/test_market_data.py` | Pass | Final focused run: 4 passed |
| Adapter types | `uv run --project python --group dev pyright python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py` | Pass | 0 errors |
| Adapter lint | `uv run --project python --group dev ruff check python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py` | Pass | all checks passed after correction |
| Python package | `uv run --project python --group dev pytest -q python/apps/quant-engine/tests python/packages/quant-data/tests` | Pass | 6 passed |
| Python package types/lint | `uv run --project python --group dev pyright` and `ruff check python/apps/quant-engine python/packages/quant-data` | Pass | 0 errors; all checks passed |
| Python formatting | `uv run --project python --group dev ruff format --check python/apps/quant-engine python/packages/quant-data` | Pass | 11 files already formatted |
| Workspace lock | `uv lock` | Pass | resolved 65 packages; added websockets 15.0.1 |
| Root TS Verify Gate | `pnpm run verify` | Pass, separate scope | Root TypeScript build, lint, production typecheck, unit tests and bundle check; current receipt is maintained in `VERIFY_GATE_2026-11-17.md` |
| Diff/limits | `wc -l python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py; git diff --check` | Pass | Final files: adapter 229 lines, focused tests 171 lines; no whitespace errors at that run |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `pnpm run verify` |
| **Exit / Result** | 0 |
| **Status** | Pass for this Python adapter increment; root TS Verify Gate is separate |
| **Evidence** | The adapter's focused Python tests and Python checks are recorded in this report. The distinct root `pnpm run verify` result is in `VERIFY_GATE_2026-11-17.md`. |

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Python adapter lint | scoped Ruff commands | Pass | no diagnostics |
| Python adapter typecheck | scoped Pyright command | Pass | 0 diagnostics |
| Python adapter tests | `uv run --project python --group dev pytest -q python/apps/quant-engine/tests/test_market_data.py` | Pass | 4 passed |
| Root TypeScript checks | `pnpm run verify` and `pnpm typecheck:tests` | Pass, separate gate | Root workspace evidence is tracked in `VERIFY_GATE_2026-11-17.md`; it is not the Python adapter gate |

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-005 (market-data slice) | Health exposes queue depth, reconnects and stream state | Pass | `MarketDataHealth` and reconnect/backpressure tests |
| WS-001 | Subscribe only to public Testnet ticker topics | Pass | fake socket asserts fixed Testnet URL and subscribe payload |
| WS-002 | Malformed frames are discarded and counted | Pass | focused test asserts discarded count |
| WS-003 | Bounded queue and graceful close | Pass | queue size one test and socket close assertion |

## Advisor Ledger

None — no formal external review was executed. Software-design-philosophy diagnostic: 8/10. The adapter has one clear responsibility, a small consumer API, and hides protocol/reconnect decisions; a later review should validate how the engine consumes lifecycle health and ensure the design is routinely reviewed as that integration grows.

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Initial ruff rejected broad exception handling and import order | Narrowed reconnect exceptions and fixed import ordering | None; checks green |

## Deviations from Design

None.

## Blockers

None for this scoped increment. Persistence, live public Testnet smoke, and production operational durability remain outside this increment and are not claimed as complete.

## Final Status

### Overall: COMPLETE for the scoped Python adapter increment

- [x] Scoped manifest tasks completed
- [x] Incremental verification recorded
- [x] Focused Python adapter gate passed
- [x] Complementary checks pass
- [x] Acceptance tests verified
- [x] Drift decisions recorded
- [x] No unresolved blocker
- [x] No TODO/FIXME used as unfinished implementation

## Limitations

The adapter does not persist market events, expose account/order data, or run a live network smoke in CI. A local public Testnet subscription remains optional and was not used here; all automated evidence uses fake sockets.

## Parser Hardening Follow-up (2026-11-17)

This scoped follow-up fixes parser acceptance of non-finite timestamps/prices, non-positive or fractional timestamps, and empty ticker topics/symbols. Invalid supplied price values now invalidate the frame instead of being silently represented as a missing price. `_run` continues reading after parser rejection; the fake-socket regression test feeds seven invalid frames followed by a valid update and verifies all seven are discarded while the valid update is delivered.

| Command | Exit code | Evidence |
|---|---:|---|
| `uv run --project python --group dev pytest -q python/apps/quant-engine/tests/test_market_data.py` | 0 | 4 passed; bad frames ignored, subsequent valid frame delivered |
| `uv run --project python --group dev pyright python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py` | 0 | 0 errors, 0 warnings, 0 informations |
| `uv run --project python --group dev ruff check python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py` | 0 | All checks passed |
| `uv run --project python --group dev ruff format --check python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py` | 0 | 2 files already formatted after applying formatter |
| `git diff --check` | 0 | No whitespace errors |

The format check initially returned exit 1 before the formatter was run; the final check above is the post-format result. No WebSocket network smoke, credentials, account endpoints, order endpoints, or Mainnet access were used. Files touched in this follow-up are the adapter, its fake-socket tests, and this report only.

## Overflow Rejection Follow-up (2026-11-17)

The numeric parser now catches `OverflowError` from converting oversized JSON integers (for example, a 400-digit `lastPrice`) to float. The fake-socket invalid-frame regression includes this frame before a valid ticker and confirms the worker continues normally. This is a Python adapter hardening result, not a change to or substitute for the root TypeScript Verify Gate.

| Command | Exit code | Evidence |
|---|---:|---|
| `uv run --project python --group dev pytest -q python/apps/quant-engine/tests/test_market_data.py` | 0 | 4 passed; oversized integer discarded and later valid frame delivered |
| `uv run --project python --group dev pyright python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py` | 0 | 0 errors, 0 warnings, 0 informations |
| `uv run --project python --group dev ruff check python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py` | 0 | All checks passed |
| `uv run --project python --group dev ruff format --check python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py` | 0 | 2 files already formatted |
| `git diff --check` | 0 | No whitespace errors |

Final line counts: adapter 229 lines; fake tests 171 lines. No network smoke, credentials, Mainnet, account, or order endpoints were used.

The focused Python test, Pyright, Ruff lint, Ruff format, and `git diff --check` commands listed immediately above returned exit 0 after this OverflowError hardening. The root TypeScript gate has its own current receipt in `VERIFY_GATE_2026-11-17.md`.
