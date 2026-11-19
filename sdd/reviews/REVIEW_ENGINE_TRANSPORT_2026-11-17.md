# Independent engine transport review — 2026-11-17

Verdict: **ACCEPT, scoped to adapter lifecycle and ticker schema validation.** No remaining P1/P2 finding was identified in this scope. This is not production acceptance or proof of real Bybit connectivity, order recovery, reconciliation, process recovery, or remote socket closure.

## Scope and independence

Read repository AGENTS.md, software-design-philosophy skill, DESIGN_ENGINE_TRANSPORT_RECOVERY.md, the real adapter, transport tests, parser regressions, and the consumer's symbol-filtered state update. Reviewer changed only this report. The implementation owner confirmed edits stable before final review. No credentials, live network, orders, dependency installation, commit or push were involved.

## Findings resolved during review

- **P2: Reject topic/payload identity disagreement.** Previously, topic `tickers.ETHUSDT` with `data.symbol=BTCUSDT` produced a BTC event. `service.py:60-61` would accept that event into subscribed BTC state. `market_data.py:228-236` now requires topic/payload symbol equality, while allowing a genuinely missing payload symbol to inherit the topic. Parameterized schema tests cover disagreement, wrong case, blank, boolean, numeric and null identities.
- **P2: Reject invalid supplied prices.** Previously, `lastPrice=true` became `1.0` and `lastPrice=-3` became `-3.0`; both crossed the validated-event boundary. `market_data.py:247-260` now rejects boolean, null, nonpositive, nonfinite and nonnumeric supplied prices. Missing delta fields remain valid. All three price fields have parameterized coverage.
- **Follow-up P2 correction: Bound untrusted timestamps before numeric consumers.** The final diff adds a deterministic upper bound of `253402300799999` epoch milliseconds (`market_data.py:33-34,237-245`), preventing a huge positive JSON integer such as `10**400` from reaching downstream float conversion. Reviewed both boundary acceptance/rejection regressions and the actual-adapter invalid-frame case, which discards the huge timestamp and continues to a valid ticker. The schema still accepts old/future timestamps within its numeric bounds; freshness remains a separate consumer policy.

Before-fix reproducer used the real static parser with three JSON frames: mismatched topic/payload, boolean price, negative price. Command `UV_CACHE_DIR=/tmp/bybit-quant-uv-cache uv run --project python --no-sync python -c ...` exited 0 and returned `[('BTCUSDT', 3.0), ('BTCUSDT', 1.0), ('BTCUSDT', -3.0)]`. The final regression tests reject these frames.

## Lifecycle assessment

`market_data.py:148-205` gives the worker ownership of each acquired socket. Cleanup runs before reconnect/backoff or terminal completion; cleanup is shielded against repeated worker cancellation and bounded by a five-second cooperative timeout. Unexpected transport, parser and backoff exceptions terminate with safe `failed` health and no escaping task exception. Explicit shutdown shares one shielded task; concurrent/cancelled callers cannot interrupt cleanup, and start rejects while cleanup remains pending (`115-135`). Queue capacity and backpressure remain bounded (`83`, `167`).

The tests exercise the actual adapter with injected fake transport, not a replacement adapter. They cover unexpected connect/send/recv/parser failure, reconnect cleanup ordering, jitter/sleeper failure, cleanup error, queue backpressure cancellation, repeated worker cancellation, concurrent cancelled close, start/close exclusion, terminal-cleanup cancellation, real five-second timeout, and restart after failure. Exception text is absent from public health. Explicit shutdown ultimately reports `closed`; a failing cleanup attempt does not prove successful socket closure.

## Fresh verification

After the timestamp follow-up, independently reread the final diff and reran every command below. This final receipt supersedes the earlier 58-test acceptance. All commands used prefix `UV_CACHE_DIR=/tmp/bybit-quant-uv-cache uv run --project python --no-sync` against the existing workspace environment:

| Command after prefix | Exit | Observed result |
| --- | --- | --- |
| `pytest python/apps/quant-engine/tests/test_market_data.py python/apps/quant-engine/tests/test_market_data_validation.py -q` | 0 | 71 passed in 5.05s |
| `ruff check python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py python/apps/quant-engine/tests/test_market_data_validation.py` | 0 | All checks passed |
| `ruff format --check python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py python/apps/quant-engine/tests/test_market_data_validation.py` | 0 | 3 files already formatted |
| `pyright python/apps/quant-engine/src/quant_engine/market_data.py python/apps/quant-engine/tests/test_market_data.py python/apps/quant-engine/tests/test_market_data_validation.py` | 0 | 0 errors, 0 warnings, 0 informations |

Earlier independent lifecycle-only pytest passed 13 tests in 5.03s; the initial parser correction passed 58 tests in 5.03s. Final files are 269, 478 and 57 lines, below the repository's 500-line bound. The implementation owner confirmed no pending adapter edits before this final re-review.

## Design diagnostic

**10/10 for this local boundary: all eight diagnostics pass; failed rows: none.** The adapter has one describable responsibility; its unchanged four-method API hides substantially more lifecycle/protocol complexity than it exposes; cleanup ownership and parsing can change without consumer edits; the close interface documents concurrency/cancellation promises; this review explicitly evaluates complexity; the module owns wire validation and reconnect policy; module/interface comments expose the boundary to newcomers; the recorded design supplement and review-driven corrections demonstrate design improvement in this increment. No specific additional change is needed for 10/10 within this scope. This score does not cover the whole repository.

## Remaining verification limits

Cooperative asyncio timeouts cannot terminate a transport that suppresses cancellation or blocks the event loop. A close error/timeout proves a bounded cleanup attempt and completed worker shutdown, not remote resource release. Live networking, stale/future timestamp policy, delta snapshot composition, supervisor integration, full Verify Gate, SBOM/security scans and release acceptance are outside this report and must retain their separate evidence/status.
