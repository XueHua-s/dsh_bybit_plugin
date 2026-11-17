# Independent EngineSupervisor review — 2026-11-17

Status: REQUEST CHANGES (two P2 findings; scoped review, no source edits).

Scope: `python/apps/quant-engine/src/quant_engine/supervisor.py`, `tests/test_supervisor.py`, and package `__init__.py`. Read repository AGENTS.md and `.agents/skills/software-design-philosophy/SKILL.md`. Current reviewed supervisor has 228 lines. This receipt is independent of the implementation agent's pass counts.

## Findings

1. **P2 — A failed monitor leaves a live worker advertised as supervised/running.** `supervisor.py:158-168` awaits the injected polling sleeper and calls the worker health boundary outside any terminal exception handler. A sleeper or health exception ends `_monitor`; state remains `running`, `last_error` remains `None`, and no cleanup runs. `start()` then returns the existing running snapshot instead of reinstating supervision. Reproducer: inject an async sleeper that waits on an Event then raises `OSError`; start; release Event; await the monitor with `gather(return_exceptions=True)`; assert monitor result is OSError while snapshot still reports running and the fake runtime remains active. Handle unexpected monitor errors at the monitor boundary, clean up the pair, and publish a sanitized terminal failure. Expected shutdown cancellation must retain normal shutdown behavior.

2. **P2 — Repeated cancellation can cancel cleanup and discard the only adapter handle.** `supervisor.py:124-125` and `208-214` shield only the first wait and then await cleanup without shielding. Successive cancellation traverses these nested awaits into the adapter-close coroutine. `_close_worker_impl` finally stops the runtime and clears both handles, even though adapter close was interrupted. Reproducer: start test `BlockingAdapter`; launch close; await `close_started`; call close_task.cancel() three times with `await asyncio.sleep(0)` between calls; catch CancelledError. Observed: `adapter.close_calls == 0`, `runtime.stop_calls == 1`, snapshot state still `running`, both handles `None`. Set release_close then call close again: adapter close_calls remains zero. Cleanup must remain owned and awaitable through repeated caller cancellation; don't discard ownership while a close operation is interrupted.

## Commands and evidence

- `UV_CACHE_DIR=/tmp/bybit-supervisor-uv-cache uv run --project python --locked pytest python/apps/quant-engine/tests/test_supervisor.py -q`: exit 2; dependency resolution attempted PyPI and DNS was unavailable. This is not a test failure or a live adapter check.
- `UV_CACHE_DIR=/tmp/bybit-supervisor-uv-cache uv run --project python --locked --no-sync pytest python/apps/quant-engine/tests/test_supervisor.py -q`: exit 0; 12 passed.
- `UV_CACHE_DIR=/tmp/bybit-supervisor-uv-cache uv run --project python --locked --no-sync ruff check python/apps/quant-engine/src/quant_engine/supervisor.py python/apps/quant-engine/tests/test_supervisor.py`: exit 0.
- `UV_CACHE_DIR=/tmp/bybit-supervisor-uv-cache uv run --project python --locked --no-sync pyright python/apps/quant-engine/src`: exit 0; zero diagnostics.
- `UV_CACHE_DIR=/tmp/bybit-supervisor-uv-cache uv run --project python --locked --no-sync python -u /tmp/review_supervisor_repro_three.py`: exit 0; deterministic fake-worker probes reproduced both findings. Script uses the repository's FakeRuntime/BlockingAdapter via runpy, Event-gated polling failure, and explicit task cancellation. No sockets, accounts, orders, or credentials.

The focused suite does meaningfully cover serialized concurrent starts, close taking precedence over queued/in-flight starts, explicit reopen, finite restart count, factory exceptions, cleanup exceptions, and one cancellation. Several older restart tests depend on a fixed 10 ms sleep; they do not cover dead monitor or repeated cancellation. The new concurrency cases use Events and assertions on actual created workers, close/stop counts and monitor tasks rather than pass count alone.

## Design assessment and limits

Software-design-philosophy score: **8/10**. Module purpose, deep interface, hidden restart/ownership policy, API rationale, explicit boundary and design review are strong. Failed Quick Diagnostic rows: interface contracts/newcomer understanding are incomplete around terminal monitor errors and cancellation guarantees; close currently promises stronger behavior than repeated cancellation provides. To reach 10/10, complete and document these lifecycle guarantees and preserve a single cleanup owner through cancellation. This assessment concerns scoped lifecycle code, not a score for the whole repository.

Fake-worker evidence does not establish real adapter failure/reconnect behavior, process supervision, hung-worker detection, queue consumption, order recovery, checkpoint restoration, account reconciliation, or live trading readiness. No source modifications, commit, release, credentials inspection, application network request or order was made by this reviewer. Pending: implementation fixes and independent rerun of these two probes before acceptance.

## Independent re-review after fixes

Final status: **ACCEPT for the scoped in-process supervisor behavior**. This supersedes the initial request-changes status; both findings above are retained as audit history and are now resolved.

Reread stable final implementation (243 lines) and test suite (389 lines), after the implementer's explicit stable-files notification. `_await_cleanup` now owns a shield loop until the actual cleanup task finishes; repeated caller cancellation no longer traverses into adapter cleanup. `_watch` now converts ordinary sleeper/health boundary errors into sanitized terminal failure and closes the owned pair. No additional actionable P1/P2 finding was identified in this scoped review.

Independent final commands:

| Command | Exit | Evidence |
| --- | --- | --- |
| `UV_CACHE_DIR=/tmp/bybit-supervisor-uv-cache uv run --project python --locked --no-sync pytest python/apps/quant-engine/tests/test_supervisor.py -q` | 0 | 16 passed |
| `UV_CACHE_DIR=/tmp/bybit-supervisor-uv-cache uv run --project python --locked --no-sync ruff check python/apps/quant-engine/src/quant_engine/supervisor.py python/apps/quant-engine/tests/test_supervisor.py` | 0 | All checks passed |
| `UV_CACHE_DIR=/tmp/bybit-supervisor-uv-cache uv run --project python --locked --no-sync pyright python/apps/quant-engine/src` | 0 | Zero errors, warnings or information diagnostics |
| `UV_CACHE_DIR=/tmp/bybit-supervisor-uv-cache uv run --project python --locked --no-sync python -u /tmp/review_supervisor_repro_fixed.py` | 0 | Independent triple-cancel probe remains pending while cleanup is blocked; after release, adapter/runtime close counts are 1/1 and state stopped; retry close preserves counts. Event-gated monitor exception completes with state failed, type-only error and both owned handles absent. |

The updated tests independently assert sleeper and health boundary failure, plus repeated cancellation during direct close and restart-close, using Events and actual cleanup/ownership assertions. My external probe reuses the original independent reproduction with the necessary release-before-await handshake for the now correctly waiting close.

Updated software-design-philosophy assessment: **10/10 for this scoped boundary**, all eight diagnostic rows satisfied after the ownership policy was centralized and the terminal monitor contract implemented; this is a qualitative architecture review, not proof of absent bugs or a score for the full repository. All earlier operational limits remain unchanged. I did not independently rerun the full engine/workspace gates or real adapter tests in this review; those require their own receipts.
