# Independent engine service review — 2026-11-17

Verdict: **ACCEPT for the read-only local Testnet service slice.** No remaining P1/P2 finding in reviewed service scope. This is not trading readiness, production deployment, real exchange connectivity, or completion of the broader engine architecture.

## Scope and independence

Read AGENTS.md, project software-design-philosophy skill, DESIGN_ENGINE_SERVICE.md, service.py, api.py, monitoring.py, bootstrap.py, test_service.py, engine/workspace pyproject configuration, Nx targets, generated OpenAPI, runbook, and the actual adapter/supervisor/runtime interfaces. Implementation owner confirmed source readiness. Reviewer changed only this report. No exchange connections, credentials, orders, installations, commits or pushes were performed.

## Findings resolved during review

- **P2: Hostile timestamp made both HTTP routes return 500.** A real injected socket frame containing positive integer `ts=10**400` crossed the parser boundary; `HealthMonitor.exchange_lag()` overflowed converting it for seconds. Independent before-fix integration returned health/market **500/500**. Adapter owner subsequently bounded timestamps to integral Unix milliseconds in `1..253402300799999`. Independent after-fix integration verified the frame was discarded, latest state remained empty, and both routes returned **503/503**. Boundary regressions cover enormous, out-of-range, nonfinite, fractional and boolean timestamps. Validation belongs to the wire adapter; service need not invent a timestamp or swallow a broken domain invariant.
- **Verification defect: queue-drain test waited on the wrong contract.** Initial `test_service.py` run exited 1: **1 failed, 5 passed**. Socket input being empty did not imply the adapter event queue had drained; observed depth was 88. Owner changed the condition to require parsed count 600, actual adapter queue depth zero and a latest event. Final focused integration passes and now also checks a real partial delta after a complete update.

## Integration assessment

MarketWorker composes the real bounded adapter queue with one consumer and keeps at most one event per configured symbol. Unexpected consumer completion changes worker health to failed; supervisor restarts the complete pair under its finite budget. Lifecycle cleanup cancels/awaits the consumer, closes the adapter and clears latest state. FastAPI lifespan owns service start/close, including startup failure through finally. The regression suite exercises actual adapter + consumer + supervisor + HTTP lifespan and verifies no remaining tasks/socket after normal shutdown and consumer failure exhaustion. Concurrent adapter/supervisor cancellation hardening is covered by their independent reviews rather than claimed anew here.

Health measures actual process RSS and CPU times. Readiness requires a running supervisor, connected worker and receive/exchange freshness for every configured symbol. Delayed and far-future exchange ticks fail closed. Order latency/rejection/reconciliation remain null/unknown. Market responses expose incomplete delta fields as null and mark partial; they do not merge older prices into a purported current snapshot. Partial events can satisfy feed readiness, which represents market-feed availability rather than full-price/account/execution readiness and matches this slice's documented scope.

An additional independent offline multi-symbol probe verified: BTC-only data leaves BTC+ETH health at 503; receiving ETH changes it to 200; omitted bid/ask remain null with partial=true; ten unconfigured injected symbols do not grow the two-entry latest dictionary; unconfigured HTTP symbol returns 404; shutdown closes the socket and leaves no background tasks.

CLI validation requires explicit bounded symbols and loopback IP binding, with positive finite freshness and valid port. Schema construction does not enter lifespan; source review confirms no connection side effect in app construction. Only the two read-only API routes exist. No private APIs, credential loading, order operation or mainnet switch exists in this service. Export/check output is deterministic and matches the checked-in schema. Nx serve is uncached; schema export is separated from runtime startup.

## Fresh command evidence

Every command below used prefix `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache uv run --project python --locked` against existing dependencies. Final checks ran after timestamp correction and service test correction.

| Command after prefix | Exit | Observed result |
| --- | --- | --- |
| `pytest python/apps/quant-engine/tests/test_service.py python/apps/quant-engine/tests/test_market_data_validation.py -q` | 0 | 63 passed in 0.19s |
| `ruff check python/apps/quant-engine` | 0 | All checks passed |
| `ruff format --check python/apps/quant-engine` | 0 | 13 files already formatted |
| `pyright python/apps/quant-engine/src` | 0 | 0 errors, 0 warnings, 0 informations |
| `quant-engine-openapi --output contracts/openapi/quant-engine.v1.json --check` | 0 | Current schema matches offline generation |
| `python -` injected-socket hostile-timestamp integration | 0 | Discarded event; health/market 503/503 |
| `python -` injected-socket multi-symbol/partial/bounded-state integration | 0 | All-symbol readiness, partial nulls, bounded state and socket/task cleanup passed |

No repository-wide verify, vulnerability/secret scan, SBOM generation, real server bind or release action was run by this reviewer; parent retains those gates. Heartbeat hardening, execution/account readiness, reconciliation, persistence, process recovery, authenticated remote control and OTel remain outside this accepted slice.

## Software-design diagnostic

Current score: **10/10 (8 of 8 rows pass for this slice)**. Coherent modules hide transport, composition/lifecycle, metrics, HTTP/schema and CLI decisions; interfaces are smaller than their implementations, and docstrings/design record the important ownership and safety intent. Design review and deliberate decomposition are evidenced by this artifact and feature design.

The initial 8.75/10 assessment identified duplicated freshness acceptance in api.py and monitoring.py. Owner subsequently introduced documented `HealthMonitor.is_fresh(event)` and both HTTP market availability and aggregate health now use that single policy. Independent source inspection and the final 63-test run verify the change; no diagnostic row remains failed. This scoped design score does not remove the broader unimplemented capabilities listed above.

## Final CI wiring review supplement

Independently inspected the final `.github/workflows/ci.yml` diff: its only change adds `pnpm exec nx run quant-engine:openapi-check` to the blocking `verify` job, after the Python Nx checks. Neither that job nor the added step has `continue-on-error`; the unrelated public-network smoke remains non-blocking. Engine `project.json` now runs Pyright over `python/apps/quant-engine`, covering tests as well as source. The remainder of its diff consists of formatting and the already-reviewed serve/OpenAPI targets. The feature design manifest records both wiring changes. No unrelated permissions, dependency commands, trading settings or runtime behavior were introduced by these final changes.

Independent rerun with prefix `NX_DAEMON=false NX_ISOLATE_PLUGINS=false UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache`:

| Command after prefix | Exit | Observed result |
| --- | --- | --- |
| `pnpm exec nx run quant-engine:typecheck --skip-nx-cache` | 0 | 2 tasks succeeded; cache explicitly skipped |
| `pnpm exec nx run quant-engine:openapi-check --skip-nx-cache` | 0 | 1 task succeeded; cache explicitly skipped |

Parent separately reports an actual public Testnet ETHUSDT process reached health HTTP 200 with ready=true, then completed ordered graceful shutdown and closed its listening port. Its child exit -15 is consistent with uvicorn's documented SIGTERM re-raise after shutdown; those process/network observations were performed by parent, not repeated by this reviewer. BUILD_REPORT_ENGINE_SERVICE.md attributes that evidence to parent and explains why a signal return code alone is insufficient. This supplement does not convert reported evidence into independent reviewer execution. Scoped ACCEPT remains unchanged.
