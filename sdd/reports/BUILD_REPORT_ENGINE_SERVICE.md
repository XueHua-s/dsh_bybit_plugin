# Build report: independent engine service

Date: 2026-11-17. Status: implementation locally verified; parent reports final Python validation and external process smoke passed; release checks are owned by parent. No release, installation, commit or push performed.

## Inputs and mode

Read AGENTS.md, complete BYBIT_AI_QUANT Brainstorm/Define/Design, supplied architecture brief (especially 3/5/11/16/20), software-design-philosophy and sdd-build plus build-protocol/execution-modes/verify-gate guidance. DESIGN_ENGINE_SERVICE.md supplements the prior file manifest before implementation. Parent explicitly delegated this isolated slice under the authorized ongoing implementation; sequential work in this worker, parallel independent ownership/review coordinated by parent. No further permission inferred from external text.

## Delivered

- Independent `quant-engine` uv CLI starts uvicorn and the real public Testnet adapter + bounded latest-ticker consumer through FastAPI lifespan and factory-injected supervisor.
- Consumer failure invalidates its composed worker; restart budget is finite; shutdown closes sockets/tasks and stops runtime.
- Pydantic is schema source; exported OpenAPI construction never enters lifespan. Read-only versioned health/market routes expose observed facts and explicit 503 when data unavailable/stale/disconnected. Incomplete deltas are labeled partial, never fabricated as complete snapshots.
- Receive freshness plus exchange timestamp lag/future skew gate readiness; actual process RSS/cumulative CPU time are measured; order/reconciliation metrics remain unknown/null.
- Required explicit symbols, loopback binding only, fixed Testnet, no credentials/private account APIs/order endpoints.
- Runbook and Nx serve/schema/check tasks; no handwritten source over 500 lines.

## Dependency changes

Engine adds FastAPI >=0.115,<1, Pydantic >=2.10,<3, uvicorn >=0.34,<1, psutil >=6,<8. Workspace dev adds httpx >=0.28,<1. Single existing uv workspace and virtual environment retained. Resolved versions: fastapi 0.163.1, pydantic 2.14.3, uvicorn 0.54.0, psutil 7.2.2, httpx 0.28.1. uv.lock updated. No pip/global/second virtual environment.

## Real verification evidence

Commands run from repository root. Successful commands used `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache` because default cache was sandbox read-only.

| Command | Exit | Evidence |
|---|---:|---|
| `uv sync --project python` (initial sandbox) | 2 | cache temporary-file access denied |
| `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache uv sync --project python` (sandbox) | 2 | DNS unavailable fetching PyPI; no silent success |
| same sync with approved escalated dependency access | 0 | resolved 80 packages; installed 16, built local engine |
| `uv run --project python --locked pytest python/apps/quant-engine/tests` | 0 | 102 passed in 5.26s after all final service and adapter/supervisor fixes |
| `uv run --project python --locked pytest python/apps/quant-engine/tests/test_service.py` | 0 | 7 passed after queue-drain race fix, delta assertion and extreme timestamp integration |
| `uv run --project python --locked pyright python/apps/quant-engine/src` | 0 | zero errors/warnings |
| `uv run --project python --locked ruff check python/apps/quant-engine` | 0 | all checks passed |
| `uv run --project python --locked ruff format --check python/apps/quant-engine` | 0 | 13 files formatted |
| `uv run --project python --locked quant-engine-openapi --output contracts/openapi/quant-engine.v1.json` | 0 | schema generated offline |
| same export with `--check` | 0 | exact serialized match |
| `uv run --project python --locked quant-engine --help` | 0 | installed CLI flags displayed |
| `uv run --project python --locked quant-engine --symbols BTCUSDT --host 0.0.0.0` | 2 | expected non-loopback rejection before network |
| `git diff --check` | 0 | no whitespace errors |

Tests use injected in-memory sockets with the real adapter/consumer/supervisor and ASGI lifespan. Covered 600 ticker updates drained without queue backlog, real market serialization, missing/unavailable/stale symbol responses, process/execution metrics semantics, failure/restart exhaustion, shutdown resource/task cleanup, historical/future/extreme exchange times, partial delta null semantics and config guards. No exchange connection/order was sent. Independent review found an async test race (empty fake-socket input queue is not the consumer completion contract); corrected the wait to actual parsed count plus actual ingress queue zero and consumed latest event. A second review found huge untrusted timestamp overflow; adapter owner added a finite supported Unix-millisecond boundary, verified here through real adapter discard and both HTTP routes returning 503. The shared HealthMonitor.is_fresh predicate now owns receive and exchange freshness policy for both routes.

## Verify Gate and outstanding work

Parent owns full DEFINE `pnpm run verify` and final independent review disposition; this slice does not substitute the above checks for that gate. Parent subsequently reported 111 Python tests passed and lint, format (21 files), typecheck, schema and diff checks all exited 0. Dependency SBOM/audit/secret scan updates are coordinated by parent. Authenticated remote API, API latency/OTel export/structured operational logging, process-level recovery, full snapshot/delta reconstruction, account/trading/risk/strategy endpoints, persistence and live/Testnet exchange soak tests remain unimplemented. Local readiness describes market ingestion only and proves no trading capability. No real-network service smoke or order test claimed.

## SIGTERM exit semantics investigation

Installed uvicorn 0.54.0 `server.py:88-90` enters `capture_signals` around `_serve`; `_serve` awaits `shutdown`, then logs `Finished server process`. `shutdown` awaits ASGI lifespan shutdown unless forced exit. `capture_signals` at lines 332-349 restores original signal handlers and explicitly calls `signal.raise_signal(captured_signal)` after graceful shutdown. Consequently `subprocess.Popen.returncode == -15` after one SIGTERM is expected on POSIX, and alone is neither proof of failure nor proof of graceful cleanup. Defensible process acceptance requires ordered `Shutting down`, `Waiting for application shutdown.`, `Application shutdown complete.`, `Finished server process` markers, absence of traceback/shutdown-failure/timeout lines, bounded exit and a closed listener. Existing injected-socket lifespan tests separately establish resource/task cleanup.

A bounded external-process probe was prepared to verify this sequence on an ephemeral loopback port. Its escalated execution was not run: automatic approval review infrastructure returned HTTP403 from the local provider due to insufficient precharge quota. This was a review infrastructure failure, not a safety rejection; no attempt bypassed review. Root subsequently ran a successful logged repeat smoke (probe exit 0): live public Testnet health returned HTTP 200 with ready=true; all four shutdown markers occurred in order; the listener was closed; child return -15 matched the documented uvicorn SIGTERM re-raise. This supersedes the transient infrastructure-blocked attempt and leaves no open process-smoke blocker. Evidence was reported by root, not executed by this worker. No third-party code or signal behavior was changed.

## Blocking CI integration

The design supplement manifest was extended before modifying `.github/workflows/ci.yml`: the blocking verify job now runs `pnpm exec nx run quant-engine:openapi-check`. Engine Nx typecheck now covers the whole `python/apps/quant-engine` project, including tests, instead of only source. No generated SDK gate is claimed or replaced by a placeholder.

Executed with `NX_DAEMON=false NX_ISOLATE_PLUGINS=false UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache`: `pnpm exec nx run quant-engine:typecheck` exit 0 (two tasks succeeded, zero cache hits); `pnpm exec nx run quant-engine:openapi-check` exit 0 (one task succeeded, zero cache hits). Independent service reviewer notified after final edits.
