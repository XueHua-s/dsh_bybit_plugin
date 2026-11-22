# DESIGN supplement: Engine transport failure and cleanup

Date: 2026-11-17. Sources: BRAINSTORM/DEFINE/DESIGN_BYBIT_AI_QUANT.
Scope: AT-005 graceful lifecycle/recovery; no LLM prompts, credentials, orders or network tests.

## Observed drift

The existing adapter drops its socket reference without closing on reconnect or terminal errors. Unexpected worker exceptions leave health connected and escape observation; the supervisor consequently cannot detect them. Explicit close can fail before cancelling the worker. This contradicts the documented adapter lifecycle contract; this supplement defines its repair before implementation.

## Decisions

Keep the four-method consumer API unchanged. One worker owns each opened socket and closes it exactly once in a finally block, before reconnect/backoff or terminal completion. Close failures and unexpected transport/parser/backoff failures become terminal `failed` health without publishing untrusted exception text. Worker exceptions are handled internally rather than left as unobserved task exceptions. Expected connection errors retain bounded backoff and queue backpressure.

Explicit close synchronously marks the adapter closing, starts one shared shutdown task, cancels the worker once and waits for it through a shield. Concurrent close callers share that task; cancellation of a caller cannot cancel resource cleanup. Start rejects while shutdown remains in progress. Socket close uses a fixed five-second asyncio timeout; a cooperative close implementation times out rather than blocking shutdown forever. Python cannot forcibly terminate transport code that suppresses cancellation or blocks the event loop; that limitation remains explicit.

Design diagnostic: 10/10 for this local boundary (all eight rows pass): lifecycle ownership, serialization, protocol parsing and error redaction remain hidden behind the unchanged adapter API; comments describe concurrency promises; no additional public lifecycle knobs or shallow transport wrappers are introduced. The score does not assess whole-system production readiness.

## File manifest

- `python/apps/quant-engine/src/quant_engine/market_data.py`: repair worker failure and cleanup ownership, serialize close through a shared task.
- `python/apps/quant-engine/tests/test_market_data.py`: real adapter with injected transports; terminal recv/send/connect/backoff faults, reconnect cleanup, close errors, cancellation and concurrent close/start cases.
- This supplement: design/drift and focused command evidence.

## Verification

Run focused pytest, Ruff check/format and Pyright with the existing uv workspace and locked dependencies. Parent orchestrator runs the full DEFINE gate (`pnpm run verify`) and records aggregate release limitations. No release, commit, install or push is included in this subtask.

## Focused execution evidence

Mode: parent-assigned isolated adapter subtask; no user-visible release action. Files remain 255 and 431 lines respectively. Socket cleanup itself is shielded and awaited if explicit close cancels a worker already cleaning a failed connection; cleanup timeout remains owned by the worker.

- Initial `uv run --project python --locked pytest python/apps/quant-engine/tests/test_market_data.py -q`: exit 2; sandbox prevented writing default uv cache. No dependency installation was attempted.
- Existing environment rerun prefix: `UV_CACHE_DIR=/tmp/bybit-quant-uv-cache uv run --project python --locked --no-sync`.
- Prefix + `pytest python/apps/quant-engine/tests/test_market_data.py -q`: exit 0, 13 passed in 5.03s, including the actual five-second close timeout.
- Prefix + `ruff check python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py`: exit 0, all checks passed. An earlier exit 1 flagged deliberate BLE001 terminal error redaction; added a localized documented suppression, then reran successfully.
- Prefix + `ruff format --check python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py`: exit 0, two files already formatted.
- Prefix + `pyright python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py`: exit 0, zero errors/warnings.

Tests exercise actual adapter with injected connector/socket/sleeper, no credentials, live endpoint or orders. Remaining limits: close errors/timeouts guarantee a bounded cleanup attempt and worker termination, not successful remote closure. A transport that suppresses cancellation or blocks the event loop cannot be forcibly stopped by asyncio. These tests do not prove real Bybit networking, OS-process recovery, order recovery, reconciliation, or the full project Verify Gate; parent records aggregate checks separately.

## Review-driven parser boundary correction (before code edits)

Independent reviewer reproduced topic/data symbol mismatch and boolean/nonpositive prices being accepted. Parent explicitly authorized correction in this increment: require normalized payload symbol to equal topic symbol, reject boolean and nonpositive supplied prices, preserve genuinely absent delta price fields. This repairs typed ticker validation; it does not add trading logic or relax subscribed-symbol filtering in the consumer.

Manifest addition: `python/apps/quant-engine/tests/test_market_data_validation.py` owns focused parser-boundary regressions, keeping every file below 500 lines. `market_data.py` remains the single wire-validation boundary.

### Final review corrections and evidence

Applied: strict topic/data symbol matching; explicit null/bool/nonpositive/nonfinite prices rejected while missing fields remain valid delta updates; unexpected parser failure regression; public close concurrency documentation; repeated worker cancellation cannot penetrate socket cleanup shielding. No LLM/prompt surface was changed. Final line counts: adapter 265, lifecycle tests 477, validation tests 39.

Using the same existing-environment prefix above, final commands cover all three paths:

- `pytest python/apps/quant-engine/tests/test_market_data.py python/apps/quant-engine/tests/test_market_data_validation.py -q`: exit 0, 58 passed in 5.06s.
- `ruff check` on these three files: exit 0, all checks passed. The first parser-test iteration had import-order findings; `ruff check --fix` fixed only import layout, then a clean check passed.
- `ruff format --check` on these three files: exit 0, all three already formatted.
- `pyright` on these three files: exit 0, zero errors/warnings.
- `git diff --check --` on these three files: exit 0.

Earlier 13-test evidence describes the intermediate lifecycle-only stage; 58-test result is the final adapter-focused receipt. Full DEFINE gate and independent review verdict remain parent-owned evidence.

## Timestamp numeric boundary correction (before code edits)

The service reviewer reproduced `ts=10**400` passing integer ticker validation and overflowing health lag arithmetic. Parent authorized schema-bound repair: positive integral epoch milliseconds must be at most `253402300799999` (9999-12-31T23:59:59.999Z, the maximum datetime year). The deterministic bound is independent of local wall clock, remains safely representable by ordinary consumer numeric conversions, and complements consumer freshness checks rather than accepting future timestamps as ready. Manifest unchanged; parser boundary regression tests belong to `test_market_data_validation.py`.

Timestamp-bound verification using the existing-env prefix: focused two-file pytest exit 0, **71 passed in 5.07s**; Ruff check exit 0, format check exit 0, Pyright exit 0, diff check exit 0. Initial Ruff PYI041 found a redundant test `int | float` annotation; changed it to `float` (typing accepts integers) and reran Ruff/Pyright clean. Actual adapter transport test discards a `10**400` timestamp before a valid frame. Updated final file lengths: adapter 269, lifecycle tests 478, parser tests 57. Independent adapter and service reviewers were notified after edits settled; their final verdicts are recorded by the parent.
