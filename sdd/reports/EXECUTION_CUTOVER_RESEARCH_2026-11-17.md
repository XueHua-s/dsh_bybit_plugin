# Execution cutover research — 2026-11-17

Scope: read-only architecture/source research supporting `sdd/features/DESIGN_EXECUTION_CUTOVER.md`. No production code edits, dependency installation, migrations, account read, adapter connection, exchange action, commit or push. The design is **Draft / future integration**, not trading readiness.

## Verified local facts

- Installed `python/.venv/lib/python3.12/site-packages/nautilus_trader-1.231.0.dist-info/METADATA` says `Version: 1.231.0`. A stdlib byte comparison confirmed installed `adapters/bybit/{config,factories,execution}.py` and `adapters/sandbox/{config,execution,factory}.py` match the six corresponding files in `/tmp/bybit-nautilus-stable`. No third-party import was needed.
- `BybitExecClientConfig.environment=None` resolves to MAINNET (`adapters/bybit/config.py:_resolve_environment`); explicit TESTNET/DEMO is mandatory. Data/execution configs share environment credential fallback behavior (`factories.py:get_bybit_http_client`). Runtime must supply resolved credentials explicitly below the model boundary and prohibit untrusted endpoint overrides.
- `SandboxExecutionClientConfig` uses string venue/balances/account/OMS fields. `SandboxLiveExecClientFactory` is in singular `adapters/sandbox/factory.py`. Its runtime wraps the real native `SimulatedExchange`, receives subscribed `data.*.<venue>.*`, and `on_data()` processes native quote/book/trade data then advances exchange time (`execution.py:connect/on_data`). Native instrument venue must match client venue.
- Sandbox report methods return `None` or empty order/fill/position lists. A mass-status report can still contain an account ID. Neither proves a restarted account has zero orders/positions. No automatic resubmission or flat inference is acceptable.
- Native `OrderFactory.market` and `.limit` accept explicit `ClientOrderId` (`common/factories.pyx`, approximately lines 236–340). Persist that value before `Strategy.submit_order`. Strategy routes through native RiskEngine/OMS and rejects an ID already present in its in-memory cache (`trading/strategy.pyx:805+`); memory duplicate rejection is not durable idempotency.
- `TradingNode.build` uses registered data/execution factories; `run_async` starts the kernel and waits on its data/risk/execution tasks. `stop_async` stops the kernel; synchronous `dispose` waits and handles its event loop (`live/node.py:272–430+`). A dedicated node-owned loop/thread avoids treating the FastAPI loop as disposable. Exact runtime lifetime/stop behavior still needs implementation tests with the installed package.
- Bybit `_connect` loads instruments/account and subscribes private order/execution/position/wallet streams. Demo uses HTTP order operations because trade WebSocket is unsupported (`adapters/bybit/execution.py:236–275`). Native connection is not an independent account-permission/balance/reconciliation authorization.
- Bybit submit validates adapter parameters before marking submitted; Demo rejects specified unsupported TP/SL trigger-price params (`execution.py:905+`). Unconfirmed submit errors wait for reconciliation rather than always producing a rejection. Never turn a transport timeout into a new-ID retry.
- Stable `LiveExecEngineConfig` exposes startup reconciliation, in-flight checks and optional periodic open-order checks (`live/config.py`). Merely setting `reconciliation=True` does not implement the project's durable ledger, full report coverage, account identity or protective state.
- Existing `quant_execution.run_simulation` is a finite offline BacktestEngine run with synthetic fixture cash, stationary quote restriction, per-run IDs and final disposal. It is a native execution/backtest primitive, not a continuous internal-paper service.
- Existing FastAPI API exposes read-only health/market without authentication. Existing TS trade Tool directly calls signed REST for create/cancel/cancel-all/close. These are current source facts, not resolved by the design.

## Foundation interfaces and next integration

The in-flight ledger author confirmed `CommandLedger(sessionmaker).admit/get/events/decide_risk/claim_dispatch/observe/recover_inflight`, persistent IDs and conservative uncertain state. It provides atomic row+event transitions, **not** a transactional risk reservation, executor approval, native event replay, external-I/O fence or durable context expiry. The in-flight risk author confirmed `quant_risk.evaluate(intent, context, policy)` with server snapshot generation, exact intent-bound liquidity estimate, complete position/reservation legs and all 15 original risk controls. Both are foundation APIs pending their independent verification; their existence alone is no integration evidence.

Initial risk environment name `paper` conflicted with ledger `internal_paper`; the risk author aligned it during this research and a final source search confirmed `internal_paper`. Ledger lowercase sides still map explicitly to risk uppercase. Risk is conservative gross exposure, including reduce-only proposals; do not invent a reducing-order exception or encode cancels/kill-switch as submits.

Concrete next slice: authenticated loopback submit/query/start/stop, atomic durable decision/reservation/session ownership extension, server-configured synthetic paper fixtures, a long-lived native Sandbox node, durable event projection and fail-protected restart. It introduces no credential or exchange dependency. Full native market inputs must be complete; existing partial public ticker snapshots cannot supply fabricated depth or balances. The 28-file Draft manifest covers this slice; future DSH cutover, Demo/Testnet connection, full recovery, cancel/emergency/TP-SL and the remaining quant/AI platform have separate gates.

Credential design: model control requests contain opaque profile references only. The trusted Host/secure provider resolves secrets below Tool/schema boundaries; bootstrap uses a protected private channel and no secret-bearing argv/model context. Later Bybit factory requires explicit environment/product/keys, and disables implicit account-setting/borrow/repay paths until authorized. Missing secure provider is unavailable, never a reason to use a public token or read process environment indiscriminately.

## Commands and truthful outcomes

All source inspection commands were run with `exec_command` in this task. Long combined reads were reread in bounded ranges where relevant; no command printed credential files.

| Command/group actually run | Exit | Outcome / limit |
|---|---:|---|
| `cat AGENTS.md` and local software-design/SDD design skill; template/protocol/LLM/glossary reads | 0 | Required local rules and canonical design structure read; first combined output was truncated |
| `rg --files sdd/features sdd/reports python/apps python/packages packages/ts`; exact Brainstorm/DEFINE/audit reads | 0 | Existing source/SDD inventory; combined output had display truncation, relevant source reread |
| `sed -n '1,650p'`, `651,1310p`, `1311,1974p` on original attachment; final `tail -4` | 0 | Complete original brief read, including final safety priority; no external instruction promoted to trading authority |
| `cat` exact engine API/service/runtime/bootstrap, execution model/simulation, Host trade tools, SDK facade and package/project manifests | 0 | Actual current boundaries inspected; future paths in design are explicitly proposed |
| `cat`/`sed`/`rg` safe stable Bybit/Sandbox/node/cache/factory/strategy/live config and integration-test sources | 0 | Actual stable API and failure semantics reviewed; upstream tests not executed |
| `rg --files python/.venv...` without ignored-file override | 0 | Empty inventory due ignored files; not treated as absence; exact safe paths used afterward |
| Group including nonexistent `examples/live/sandbox/sandbox_node.py` | 0 (group final command) | `cat` reported absent example; no such path/API claimed; actual source and upstream sandbox tests used |
| Group ending `rg ... apps/dsh-plugin/src/lib/engine-client.ts ...` | 2 | One guessed facade path absent; actual `lib/engine.ts` then read successfully |
| `python3` stdlib exact installed/source six-file comparison + version extraction | 0 | Six `identical True`; installed metadata 1.231.0; no native import/connection |
| Python documentation edit and `apply_patch` | 0 | Only the two assigned SDD artifacts changed by this agent |
| `git diff --check -- sdd/features/DESIGN_EXECUTION_CUTOVER.md sdd/reports/EXECUTION_CUTOVER_RESEARCH_2026-11-17.md` | 0 | Whitespace gate; both files are new artifacts, not staged/published |
| Python stdlib manifest validation | 0 | 28 rows, all dependencies earlier/acyclic, exact SDD handoff, no placeholders |

No build, typecheck, pytest, vulnerability/security scan or live E2E was run by this documentation task. Parent/other agents' checks remain their own receipts. Required unfinished work is documented in the Draft: actual auth/private bootstrap, admission/reservations, long-lived native runtime, native event durability, protected restart, later complete replay/Bybit reconciliation and removal of every TS signed mutation path before exchange activation.
