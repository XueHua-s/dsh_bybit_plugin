# Independent review: PAPER_NATIVE — 2026-11-17

Verdict: **ACCEPT scoped native continuous synthetic-paper foundation**. No outstanding blocking finding in the reviewed native slice. This does not accept the service/API integration, durable ledger recovery, complete product, dependency/license packaging or release.

## Scope and authority

Independent architecture/code review of `DESIGN_PAPER_NATIVE.md` and its native runtime implementation. Read repository AGENTS, software-design-philosophy, SDD Build, restored BRAINSTORM/DEFINE and `DESIGN_EXECUTION_CUTOVER.md`. Reviewer changed only this review file and `/tmp` probes; no production/test fixes, dependency installation, credentials, account connection or exchange orders.

The approved thread design drifted to a **spawned process** after installed official `TradingNode` signal-handler ownership proved incompatible with construction in a worker thread. Parent explicitly approved this change. Official node construction runs on the child's main thread; IPC preserves the bounded facade. The discarded private node/kernel constructor adaptation is absent. This is a cleaner public-API boundary than cloning kernel construction to avoid signals.

## Architecture and compatibility findings

- Installed SDK is 1.231.0; pinned source HEAD is `27a8e54e7ac3c57d6cbf8891f0283dfbaee97317`.
- Upstream Sandbox config omits finite liquidity consumption, native exchange defaults it false, and `engine.pxd:269` declares its property readonly. Default Sandbox cannot establish finite depth across orders.
- Calling Sandbox's constructor then replacing its exchange/client would retain an original initialized account and message-bus endpoint bound to the discarded exchange. Reviewer raised this before runtime implementation; author rejected that design.
- Final private subclass initializes `LiveExecutionClient` and exactly one actual native `SimulatedExchange(liquidity_consumption=True)` and `BacktestExecClient`. It inherits native Sandbox connect/data/submit/cancel. It validates its exact SIM/NETTING/MARGIN/USDT/L2 configuration rather than silently ignoring generic settings. No handcrafted fills or runtime `BacktestEngine` exist in the new path.
- Upstream node builder injects portfolio only when factory `__name__` equals `SandboxLiveExecClientFactory` (`live/node_builder.py:246`). The private factory intentionally has that name. This is explicitly pinned compatibility debt: upgrades need source inspection and actual native tests.
- Adapter now retains upstream copyright, exact source commit and LGPL provenance. Parent assigned separate license artifact/wheel/sdist verification; this review does not certify distribution compliance.

## Findings resolved during independent review

| Finding | Resolution and observed evidence |
|---|---|
| LIVE node rejects `LoggingConfig(bypass_logging=True)` | Author uses ERROR logging without bypass; actual startup passes. |
| Native `Position.signed_qty` is double; adding it to Decimal fails | Uses native `signed_decimal_qty()`; actual post-fill account/position snapshots pass. |
| Native `OrderInitialized` precedes cache insertion | Initialization maps native event safely; full native event chain observed. |
| Clean stop discarded pending events and closed the only drain | Child flushes event IPC, parent drains while joining, retains frozen DTOs for post-stop consumptive reads. Reviewer reproduced failure before fix and four retained native events after fix. |
| Forced process death falsely reported native loop closed | Loop closure now depends on clean child cleanup acknowledgement, exit0 and actual join. SIGKILL and SIGSTOP timeout probes report failed/dead/loop-not-confirmed. |
| Worker loss retained stale complete-event-stream evidence | Facade now retains immutable failure reason and incomplete stream after timeout/death. Actual killed-child probe confirms it. |
| Event overflow silently obscured evidence loss | Saturation yields protected/incomplete with `native_event_queue_full`, rejects further submits, and cannot report clean stopped. Parent explicitly accepted this fail-closed first-foundation scope; reliable replay remains unfinished. |

## Actual independent verification

All commands below used the repository's already-installed `python/.venv`; no live examples or exchange adapters were connected.

| Command | Exit | Evidence |
|---|---:|---|
| `python/.venv/bin/python -c 'import nautilus_trader; print(nautilus_trader.__version__)'` | 0 | 1.231.0. |
| `python/.venv/bin/python /tmp/review_paper_native_direct.py` | 0 after author fixes | Real node: first order fills .003, second fills .001 against total depth .004; native account retains position .004; partial order cancel is native; loop closes. Initial iterations failed at real logging and initialization boundaries and were reported, not counted as passes. |
| `python/.venv/bin/python /tmp/review_paper_facade.py` | 0 after author fix | Spawned official node; stop without prior event drain retains native Initialized/Submitted/Accepted/Filled. Prior version exited1 with zero events after claimed clean stop. |
| `python/.venv/bin/python /tmp/review_paper_multicommand.py` | 0 | Two commands consume exactly .004 total; cancel partial second retains .001; third receives no reused depth; explicitly supplied later snapshot fills .002; same native instance, cumulative position .006, retained cash, provided ID duplicate rejected; actual clean stop/join. |
| `python/.venv/bin/python /tmp/review_paper_failure.py` | 0 | Capacity1 event saturation protects and blocks later submit; overflow stop failed. Killed child detected in .051s; final snapshot failed/dead, loop_closed false, explicit failure reason, incomplete stream. |
| `python/.venv/bin/python /tmp/review_paper_timeout.py` | 0 | SIGSTOP child simulates unresponsive native loop; stop returns failed/dead/loop_closed false in2.017s with configured1s deadline; no hanging child. |
| `python/.venv/bin/python /tmp/paper_runtime_review_probe.py` | 0 | Other reviewer's exact engine synthetic fixture starts/stops the native facade; no DB opened. |
| `python/.venv/bin/python -m pytest python/packages/quant-execution/tests -q` | 0 | Latest stable run:30 passed,10 existing offline Pandas timestamp deprecation warnings. |
| `python/.venv/bin/ruff check python/packages/quant-execution` | 0 | All checks passed. Earlier in-progress import/format failures were corrected by author. |
| `python/.venv/bin/ruff format --check python/packages/quant-execution` | 0 |13 files formatted. |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-execution` | 0 |0 errors/warnings. A preliminary invocation without the interpreter failed import resolution; corrected explicit interpreter invocation is the valid receipt. |
| `wc -l python/packages/quant-execution/src/quant_execution/paper*.py` | 0 | All five handwritten modules below500 lines; largest reviewed facade244 lines. |

## Design complexity assessment

**10/10 for this scoped boundary (8/8 diagnostic rows supported)**: each module has one stated responsibility; immutable facade is simpler than native/IPC internals; native compatibility changes stay private; interface comments describe identity, lifecycle and consumption promises; independent design review is recorded; native ownership/config, IPC supervision, and evidence DTO knowledge have explicit homes; documented module boundaries and pinned adapter explain the otherwise surprising factory name; deliberate design investment removed shadow exchange and private node construction. Failed diagnostic rows: none for this slice. This score does not imply complete trading functionality or reliable durable replay.

## Remaining mandatory work outside this acceptance

- Engine must persist native evidence before releasing reservations or claiming durable order status. Event stream completeness and failure reason must propagate into durable uncertainty/protection; native cache or reliable outbox/replay remains necessary for eventual recovery acceptance.
- Abruptly killed children cannot prove native loop cleanup or completeness. Forced termination is failure, not graceful shutdown; first-foundation reporting now preserves that distinction.
- Restarted sessions cannot reconstruct balances/positions from Sandbox's empty reconciliation reports. No session recovery or exactly-once external execution claim is accepted.
- Separate service/process/API/auth/risk/reservation integration review, full Verify/Release gates, mixed-license artifact inclusion, SBOM/security scan and broader product requirements remain parent-owned gates.

## Reopened delta review — perpetual valuation and owner-death cleanup

Status: **REVIEW IN PROGRESS; latest delta not yet accepted**. Parent integration findings require explicit derivatives wallet/available/realized/unrealized/equity marks and actual service-SIGKILL cleanup of the native child. Prior receipts and acceptance above describe the previously inspected source and remain historical; they do not certify forthcoming changes. Reviewer will record source hashes and independent valuation/parent-death probes when author declares the delta stable. License distribution artifacts remain separately parent-verified.

### Delta result: ACCEPT scoped native changes

The reopened native delta is independently **ACCEPTED** for the source hashes below. Prior30-test receipts remain historical; latest package suite is33 passed. No new service/API/durable-recovery acceptance is implied.

#### Perpetual valuation contract and evidence

`balance_total` is the native derivative wallet balance; it changes by realized PnL and fees, never by opening notional. `balance_free` remains raw native margin-free evidence and does not include adverse unrealized PnL. `realized_pnl` is native portfolio **net realized PnL including settlement commissions**, including previously closed positions. It must reconcile against durable gross realized PnL minus cumulative fees, not against durable gross realized alone. `unrealized_pnl` uses fresh native quote-based mark to liquidation (bid for long, ask for short); `equity = balance_total + unrealized_pnl`. Added `available_equity = min(balance_free, balance_free + unrealized_pnl)` conservatively charges mark losses without crediting unrealized gains. Risk consumers must use that explicit field rather than treating raw native free balance as marked available capacity. Snapshot timestamp is the native clock time, separate from delivered market timestamp.

Reviewer independently exercised actual native market orders and later feeds in `/tmp/review_paper_valuation_delta.py`: open .010 long at2000.10, mark bid1900, fully close at1900, reopen .010 short, mark ask2100. Exact Decimal expectations passed within native monetary precision: final wallet9998.9641994, net realized-1.0358006, unrealized-2, equity9996.9641994, raw free9989.4641994, conservative available9987.4641994. The probe explicitly checked fees once, opening no notional wallet debit, closed-position realized retention and both directional marks. Reviewer initially identified raw-free/mark-loss ambiguity; author added the separate available field and regression assertions rather than relabeling native evidence.

#### Owner-death cleanup and evidence

A watchdog thread, independent of the native asyncio loop, observes the captured multiprocessing parent's sentinel. Parent death cancels the native main task; if disposal/event-loop cleanup stalls, the watchdog exits **only its own orphan child** after2s. The live loop also checks owner liveness. Dead-owner cleanup avoids waiting for event feeders whose consumer no longer exists. This is failure containment, not durable recovery or graceful-stop proof after SIGKILL.

Independent probes killed the owning service process after actual .010 fill and checked the native PID with `os.kill(pid,0)` until `ProcessLookupError`:

- `/tmp/review_paper_parentdeath_delta.py`: native PID disappeared in0.055s after parent SIGKILL.
- `/tmp/review_paper_parentdeath_blocked_delta.py`: a temporary probe-only native `account()` wrapper blocked the native loop for60s after dispatch/fill; parent SIGKILL still removed the native PID in2.076s. The watchdog is demonstrably independent of native loop progress.

The first parent-death probe attempt could not invoke sandbox-restricted `ps` (exit1); reviewer replaced that observation with permitted signal0 PID checks. It was not counted as a passing cleanup receipt. No production source or repository tests were patched by reviewer.

#### Latest actual commands

| Command | Exit | Evidence |
|---|---:|---|
| `python/.venv/bin/python /tmp/review_paper_valuation_delta.py` | 0 | Long/adverse mark/close/reopen-short, wallet/net realized/unrealized/equity/available checks above. |
| `python/.venv/bin/python /tmp/review_paper_parentdeath_delta.py` | 0 | Actual post-fill native child disappeared after service owner SIGKILL. |
| `python/.venv/bin/python /tmp/review_paper_parentdeath_blocked_delta.py` | 0 | Native loop blocked; owner death still removes child within watchdog deadline. |
| `python/.venv/bin/python -m pytest python/packages/quant-execution/tests -q` | 0 |33 passed,10 existing offline Pandas deprecation warnings,13.67s. |
| `python/.venv/bin/ruff check python/packages/quant-execution` | 0 | All checks passed. |
| `python/.venv/bin/ruff format --check python/packages/quant-execution` | 0 |13 files formatted. |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-execution` | 0 |0 errors/warnings. |
| `wc -l python/packages/quant-execution/src/quant_execution/paper*.py` | 0 |74/204/244/106/202 lines; each below500. |

#### Reviewed source identity (SHA-256)

```text
fc222cac7595b0b50af72d4b09ff6024a9eef26e4e18249c19629f6272991625  src/quant_execution/paper_models.py
d0607da69aedbbd6ae44d966f706b3590583a8a60aa9db30280078f3f778cbf0  src/quant_execution/paper_native.py
8a3e2e513ad8db5babd28abbaf1a271900225a999749191f2af48f09b9192c28  src/quant_execution/paper_runtime.py
e516df145251a2a1505535ce0a8c913ce5091d0fd712016a6d59627abb3fe247  src/quant_execution/paper_sandbox.py
c80d4f426a5f168f9d09b91e5829fc3512d877e17c4c51f3b69a0ff1af3b5dea  src/quant_execution/paper_worker.py
6b2f88a5f97130927ffbb1ec32bdf14d41cfe30fd65d3717c2f276ddda47220c  tests/test_paper_runtime.py
```

Paths in hash block are relative to `python/packages/quant-execution/`. Parent owns mixed-license artifact and service-account integration verification. Final native delta has no outstanding blocking finding; previously stated recovery/reliable delivery/product limits remain.
