# Original architecture scope audit — 2026-11-17

## Authority, method and outcome

Authoritative requirements: the complete 1,974-line attachment `/Users/litlesnow/.codex/attachments/886f3b36-5cab-4ba1-bb1c-7ef525af0e6e/pasted-text-1.txt`, read in successive ranges 1–650, 651–1310 and 1311–1974, together with its final priority line read in the initial full-file read. Later explicit Testnet authorization does not authorize Mainnet and does not remove original product requirements. Read repository `AGENTS.md`, Brainstorm, DEFINE, local `sdd-define`, `sdd-design`, their template/EARS/clarification/Verify Gate references, and `software-design-philosophy`. This audit changes documentation only.

**Snapshot boundary:** source findings below describe the initial source inspection in this subtask. The parent is concurrently implementing `quant_engine/api.py`, `bootstrap.py`, `service.py` and `monitoring.py`; those new files appeared during the final inventory, but have not been reviewed or tested by this audit. Treat that work as in-flight/unverified and consult its separate Build report before updating individual gaps. No absence claim below supersedes later demonstrated implementation.

**Result: partial platform, not full original architecture.** Useful TypeScript plugin features, separated Nx/uv project manifests, public-stream adapter, bounded supervisor, checkpoint and migration modules exist. Their presence does not establish an independent running engine, consumed data plane, Nautilus execution, full risk/portfolio, AI team or research/evolution implementation. Static source inspection is evidence of implementation structure, not evidence of successful runtime operation.

**DRIFT-ORIGINAL-001 (corrected in DEFINE):** mandatory independent quant engine was classified SHOULD and AI research/evolution COULD. This was not supported by the original brief or a user scope reduction. Restored MUST scope and acceptance AT-010–031; original optional algorithms/conditional requirements remain optional/conditional, and staged implementation remains permitted. Existing AT-001–009 and `pnpm run verify` do not cover the product.

**DRIFT-ORIGINAL-002 (open):** `docs/research/github-repository-audit.md` explicitly elects not to introduce NautilusTrader to avoid runtime/license complexity. Original §§5/6/12 require Nautilus as unique order authority. This rationale cannot remove a mandatory requirement. Resolve actual compatibility and license/distribution questions in an ADR; no unverified legal conclusion or alternative execution approval is supplied here.

**DRIFT-ORIGINAL-003 (open):** `host-tools-trade.ts` invokes TypeScript `BybitClient.createOrder/cancelOrder/cancelAll`; `lib/bybit.ts` signs `/v5/order/create`, `/cancel`, `/cancel-all` directly. Thus even with safety guards, exchange order authority currently bypasses required Nautilus. No exchange action was executed during this audit.

## Numbered original-scope traceability

Statuses mean **partial** = concrete relevant implementation but incomplete scope; **missing** = no implementation found in inspected source inventory; **unverified** = external/runtime acceptance not executed here. None of the rows is a full-product PASS.

| Brief section | Concrete source/evidence inspected | Gaps and acceptance still required |
|---|---|---|
| 1 Product positioning and full capabilities | `apps/dsh-plugin/src/host-tools-account.ts`, `host-tools-watchlist.ts`, `host-tools-backtest.ts`, `host-tools-ai.ts`, `client.ts`; REST instrument discovery, watchlist, three strategies, paper/decision books. **Partial.** | Full data/AI/strategy combination/research/execution scope absent. Arbitrary discovered Spot/USDT-linear selection must drive engine, not just tools. Later USDC/inverse/options remain later expansion as originally stated. |
| 2 Nx/pnpm and Python engineering | Root `package.json`, `pnpm-workspace.yaml`, `nx.json`, `tsconfig.base.json`, `.node-version`; app/package manifests; `python/pyproject.toml`, `uv.lock`. **Partial.** | FastAPI/Pydantic/Nautilus absent from engine dependencies; Hypothesis absent from dev group. No complete original Oxfmt/Vitest/OpenAPI toolchain or all unified commands in root scripts. A fresh full command/graph gate is required; manifests alone do not prove it. |
| 3 Responsibility structure | `apps/dsh-plugin`, `packages/ts/quant-contracts`, `python/apps/quant-engine`, `python/packages/quant-data` each have project manifests. **Partial.** | No actual feature/regime/portfolio/risk/execution/backtest/research/model/agent Python modules. No independent process entry point. Do not create empty packages merely to match the example directory tree; preserve responsibilities as real vertical slices arrive. |
| 4 DSH plugin integration | `apps/dsh-plugin/package.json`, `cordis.patch.yml`, `src/index.ts`, `host-runtime.ts`, `client.ts`, `scripts/check-bundle.ts`. `apply()` registers Host tools/panel and effects. **Partial/unverified.** | Installed-version official Plugin Manager install/upgrade/uninstall and actual UI/lifecycle evidence not produced here; supported services/skills and new engine ownership must be established. No managed profile edits authorized. |
| 5 Overall control/data plane | TypeScript Host runtime composes direct REST client, local store, panel; Python `runtime.py`, `market_data.py`, `supervisor.py` provide separate in-process primitives. **Partial.** | No FastAPI application/API transport connecting Host/UI to engine; no continuous pipeline from data to target/risk/execution. `EngineRuntime.start()` changes health state, not a strategy worker. Independent process and engine-owned task lifecycle required. |
| 6 GitHub source research (6.1–6.5) | `docs/research/github-repository-audit.md` records 14 repository HEAD/license/high-level observations and admits shallow review. **Partial, conflicted.** | Missing required deep core algorithm/API/test/dependency and actual Bybit support matrix. FreqAI-specific source/workflow evaluation not established. Nautilus omission conflicts with mandate. TradingAgents/RD-Agent/Qlib/FreqAI/VectorBT/FinRL-X/FinRL/Meta/Crypto/ElegantRL and Hummingbot/pybit must have appropriate source-level adaptation evidence; third-party tests not run. No copying, license clearance or package compatibility inferred. |
| 7 Strategy system | `lib/strategies.ts` implements `ma_cross`, `rsi_reversion`, `breakout`; `quant-data/models.py` has `StrategyVersion` metadata JSON. **Partial.** | No complete registry validation (source/license/markets/features/warmup/config/lifecycle/validation state); no shared engine lifecycle producing portfolio targets. Other required strategy families and research-only advanced candidates remain incomplete, not required all live at phase one. |
| 8 Regime and dynamic selector | `lib/ai-market.ts` builds multi-timeframe trend/volatility briefs; strategies produce targets. **Partial inputs.** | No implemented eight-regime classifier or validated candidate scoring using OOS/stability/costs, hysteresis/cooldown/confidence, portfolio combination or safe position migration. A human/model choosing a named strategy is not the specified selector. |
| 9 AI team | `host-tools-ai.ts` exposes `quant_brief/quant_decide/quant_review`; `lib/ai.ts` normalizes a single decision and code-side simulated risk verdict. **Partial.** | No actual Market/Technical/Sentiment/Strategy/Bull/Bear/Risk/Portfolio collaboration lifecycle, role provenance/checkpoint/evaluation, or full Pydantic decision schema (strategy/regime/target/conditions/expiry/data timestamp). No evidence of actual autonomous team calls. |
| 10 Research lab | `lib/sandbox.ts` runs bounded credential-free network-disabled Node container; `test/sandbox*.ts` exists. **Partial primitive.** | No connected hypothesis/discovery/candidate factor/model/experiment/report pipeline, Python research isolation, data/model versions, OOS/walk-forward/paper/review/promotion and rollback workflow. Container code presence is not a completed experiment or security runtime test here. |
| 11 Bybit data | `lib/bybit.ts` has REST instruments/ticker/candles/book/funding/account/positions/openOrders; `market_data.py` implements Testnet linear public ticker parsing and reconnect queue. **Partial.** | Production code has no `next_event()` consumer (search found only definition/tests). Queue can fill without useful downstream progress. No Spot stream, private WS, full trades/book/funding/OI/liquidations, bootstrap/reconciliation, snapshot/delta sequence integrity or trading freshness gate. Protocol health and account recovery need integration tests. |
| 12 Execution | `host-tools-trade.ts` implements direct create/cancel/close guards; `lib/bybit.ts: createOrder()` signs REST. **Partial but architectural conflict.** | Nautilus absent; no durable unique client intent ID in create payload, timeout uncertainty resolution, event-driven OMS/partial fill/reconciliation or fully modeled TP/SL lifecycle. Backtest/paper/demo/testnet/live config presence does not prove isolated end-to-end execution across five environments. |
| 13 Independent risk/emergency | `lib/ai.ts:riskGate` checks simulated per-trade risk/position/count/day loss/drawdown; `host-runtime.ts:assertLiveAccount` checks account/equity/notional share; trade tool checks min qty/notional. **Partial.** | No one independent final risk engine shared by every execution path; original leverage/exposure/slippage/spread/liquidity/funding/liquidation/concentration/correlation/cooldown coverage missing. No whole-engine emergency freeze/cancel/reconcile/authorized-close state machine. |
| 14 Credentials/funds | `host-runtime.ts` uses DSH credential resolver; Host config/credential scripts and Mainnet enable flags exist. **Partial/unverified.** | Environment key isolation and no-withdraw/no-transfer permission enforcement need runtime/security evidence; fallback credential paths require verified secure storage and redaction. Source reads excluded credential files. Current flags are not fresh user Mainnet authorization. |
| 15 Backtest and validation | `lib/signals.ts`, `lib/strategies.ts`, `host-tools-backtest.ts` implement long-only candle tests, fees/slippage and metrics. **Partial.** | No Nautilus final event-driven validation, complete §15 cost matrix (funding/partial fills/impact/latency/multiplier/leverage/liquidation/minima), shared data lineage, purged/OOS/walk-forward/parameter robustness and full metrics/bias controls. Existing simple result must not be presented as validated deployable strategy. |
| 16 Cross-language API | `packages/ts/quant-contracts/src/index.ts` is handwritten TS Candle/Ticker/Instrument interfaces. **Missing required transport/schema.** | No FastAPI/Pydantic `/api/v1`, OpenAPI snapshot, generated openapi-typescript/openapi-fetch client or drift check; no engine API auth/idempotency/events. No `contracts/` directory in current inventory. Handwritten TS types are not generated Python authority. |
| 17 Tools/Skills | Registrars expose `bybit_account`, `bybit_market`, `bybit_trade`, `bybit_instruments`, `quant_watchlist`, `quant_backtest`, `quant_paper`, `quant_brief`, `quant_decide`, `quant_review`, `quant_signals` (inspect registrars for exact live registration). **Partial.** | Original detailed Bybit/analysis/strategy/research/trading tool inventory not implemented as requested operations; no six product Skill assets found under plugin inventory. Need supported DSH approval integration and strict output contracts (current shared tool output is rendered text). |
| 18 Dashboard | `client.ts`, `client-types.ts`, `host-panel.ts`, `host-runtime.ts` and render/client tests show DSH panel and state view. **Partial/unverified UI.** | Full seven-view engine-backed overview/instrument/research/strategy/trading/risk/settings management, authenticated control and actual installed interaction coverage remain incomplete. No external website substitution. |
| 19 Persistence | `quant-data/models.py` defines `trade_events` and `strategy_versions`; Alembic revisions 0001/0002 plus migration/backup tests; plugin `lib/state.ts` JSON store. **Partial.** | Engine/Host domain state not wired to SQLAlchemy ledger. No complete instrument/market/model/backtest/targets/orders/executions/positions/account-snapshot entities or Parquet/DuckDB research pipeline. Migration tests do not prove PostgreSQL operational recovery or transactional exactly-once processing. |
| 20 Observability/protection | TS `lib/monitor.ts` records process resource/request/queue metrics; Host explicitly initializes `websocketEnabled:false`; Python adapter/supervisor health snapshots. **Partial.** | No OpenTelemetry pipeline or connected engine strategy/risk/reconciliation/protection state; plugin monitor is not Python-worker health. Reconnect counts/checkpoint recovery are not order/account recovery. No protective response for all listed failure modes proved. |
| 21 Test requirements | TS executable assertion tests under app `test/`; Python pytest files for adapter/runtime/supervisor/migrations. **Partial.** | Not run by this audit; no full Hypothesis/quant correctness/cost/bias/property suite, Nautilus OMS failure/partial-fill/in-doubt/reconciliation or Demo/Testnet trading E2E. Static green and read-only smoke cannot establish these gates. CI Mainnet prohibition remains mandatory. |
| 22 CI/quality | `.github/workflows/ci.yml` installs locked pnpm/uv, builds/tests/types/lints/bundle, scans deps and SBOM; public Testnet network smoke nonblocking. **Partial configuration.** | Missing complete Oxfmt/Vitest/Hypothesis/schema/generated SDK/affected-build/secret-scan acceptance; no CI run inspected. Root `verify` runs plugin build/lint/type/unit/bundle only, omits Python and restored product tests. No claim of a full green product gate. |
| 23 Learning/evolution | `quant_review` scores simulated journal; `StrategyVersion` persists version strings. **Partial inputs only.** | No scheduled degradation/concept-drift/research feedback, bounded approved adjustments, reproducible experiment/model/data/parameter version lineage and deployment rollback. Score reports alone are not learning. |
| 24 Phased implementation | Brainstorm/DEFINE/DESIGN, reports and manifests show staged work. **Partial.** | Phase 0 source audit incomplete; phase 1 full toolchain not evidenced; phase 2 external lifecycle pending; phase 3 full ingestion/account recovery absent; phases 4–7 core/AI/research/continuous sim not accepted. Phase 8 requires separate explicit user authorization. No phase certified from directory presence. |
| 25 Final acceptance | Individual plugin/DB/adapter primitives map to portions of engineering/Bybit/quant/AI/trading. **Incomplete.** | No complete original engineering, Bybit, quant, AI or trading acceptance group passed. Missing core engine and unique execution authority preclude final delivery, regardless of local plugin regression results. |
| 26 Execution rules | This audit inspected code, preserved other work, did not access credentials or execute exchange actions. **Ongoing constraints.** | Continue implementation in verified slices, actual upstream source review, state-preserving lifecycle, no empty shells/profit claims, no untrusted in-process execution and no unauthorized Mainnet. This documentation-only subtask is an audit, not the required final engineering delivery. |

## Next dependency-ordered vertical slice (recommended design, not implemented)

**Slice: independently launched, authenticated FastAPI market-state engine with a real bounded consumer, generated TypeScript read/control client and durable provenance; all exchange-order routes fail closed until a verified Nautilus authority exists.** This is the next executable increment toward the mandatory full architecture, not a substitute for it.

1. Resolve source-level Nautilus version/Python/platform/Bybit Spot-linear Demo-Testnet capabilities and LGPL distribution obligations in an ADR. Preserve original execution authority. Establish a compatible pinned version before depending on its event contracts; no license conflict is waived by this audit.
2. Add a real Python process/bootstrap entry point and FastAPI lifespan owning supervisor, consumer, persistence and shutdown. Bind loopback by default; authenticate requests before any control route. Supervisor health must expose actual task failure, finite recovery and protected status. The parallel supervisor fix may improve this primitive but does not implement a service or data consumer.
3. Add typed Pydantic instrument/market/health/control schemas as sole API authority; export OpenAPI, generate TS client with openapi-typescript/openapi-fetch and check drift. Persist correlation/environment/schema versions, not credentials. DSH accesses engine through the generated client rather than recreating Python protocol types.
4. Wire public Testnet dynamically discovered selected symbols into a consumer. Validate timestamp/source/subscription, merge ticker deltas into complete latest state without treating absent fields as zero, detect stale/gapped data, persist market provenance and publish protected state. Use bounded queue/backpressure and explicit overflow/freshness semantics. Build fixture-backed integration first; then a read-only Testnet stream smoke proves receipt **and consumption**. No account credentials are necessary for this step.
5. Expose authenticated health/instruments/market snapshots/events and shutdown controls through `/api/v1`; point one existing DSH panel/read tool at generated client. Prove engine continues after a DSH Tool completes or the panel closes. No fake success for unimplemented strategy/trading routes.
6. Establish Nautilus-backed internal-paper execution, common target-exposure planning and independent fail-closed risk before any exchange order intent can be accepted. Remove/disable direct TS signed create/cancel routes (including close/cancel-all) when switching authority; no period with two writable execution paths. Persist unique intents and event IDs, reconcile uncertainty/partial fills/restarts, then progress Demo/Testnet after identity/balance/permissions/instrument and original risk gates. This is the next dependent execution slice, not part of the read-only engine acceptance claim.
7. Build feature/strategy registry → regime/selector → portfolio → complete risk → Nautilus backtest/paper validation using the same domain contracts, then AI team → isolated research → controlled evolution. Add actual modules when their responsibilities become implemented rather than pre-populating empty package shells.

### Concrete acceptance for the next slice

- Subprocess integration starts engine without DSH, authenticates loopback API, consumes multiple fixture events, returns persisted market snapshots and exits on termination without leaked tasks/sockets; restart distinguishes restored durable state from fresh exchange validity.
- Malformed/off-subscription/stale/delta/queue-full/disconnect fixtures never produce tradable healthy state; exhausted worker recovery is visible, and a consumer crash fails protection rather than leaving a healthy producer.
- Python-generated OpenAPI and TypeScript SDK drift check succeeds; existing DSH read tool uses the generated SDK. A Tool return has no effect on engine process uptime.
- Read-only public Testnet smoke records received, consumed and persisted event counts plus timestamp/latency. Network unavailability is incomplete external evidence, not fixture failure or success.
- Every old/direct exchange mutation route is denied until Nautilus+independent-risk execution acceptance exists. No Mainnet requests, API secrets, real orders or funded-account assumptions in tests.

### Software design philosophy assessment

Current audited control/data boundary: **5/10 (4 of 8 quick diagnostics supported)**. One-sentence module responsibilities, review-time design discussion, information-owning adapter primitives and deliberate design investment are supported by the inspected modules/artifacts. Failed rows: interfaces simpler than implementation (Host runtime exports many internal collaborators); implementation replaceable without caller changes (Host tools bind directly to REST/state details); abstraction comments (no single engine/service contract); newcomer-readable boundaries (documented Python authority has no actual API integration). To reach 10/10, hide exchange/session/queue/reconciliation details behind one engine-owned service contract, export Python schema-generated transport, move order/risk ownership into a single deterministic authority, and document invariants/protection semantics at that boundary. This score concerns inspected boundary design, not an unmeasured runtime quality or whole-repository score.

## Commands, exits and limits

Audit command groups actually executed through `exec_command` (all source reads excluded credential/.env files):

| Command/group | Exit | Evidence/limit |
|---|---:|---|
| `cat AGENTS.md` and local software-design/SDD Define/Design skills; initial attachment read | 0 | Combined output exceeded tool display budget; attachment was therefore reread in three bounded ranges below. |
| `wc -l <attachment>`; `rg --files sdd/features python packages/ts apps/dsh-plugin`; globbed DEFINE search | 1 | Inventory printed; final zsh nested glob had no match. Replaced with exact DEFINE path. |
| `sed -n '1,650p' <attachment>` | 0 | Original §§1–6 partially, untruncated. |
| `sed -n '651,1310p' <attachment>` | 0 | Original remaining §6 through §15, untruncated. |
| `sed -n '1311,1974p' <attachment>`; `cat sdd/features/DEFINE_BYBIT_AI_QUANT.md` | 0 | Original §§15–26 and DEFINE; initial full read also included final bold priority line after blank-line counting. |
| `cat` exact SDD skills, Brainstorm/template, root/CI/manifests, models/sandbox/research audit | 0 | Source/artifact inspection; no third-party source or runtime audit newly performed. |
| `cat` Python runtime/market/supervisor and Host runtime/paper | 0 | Large combined output truncated; dependency and execution-critical sections reread separately below. |
| `cat` engine/workspace pyproject, TS contracts, trade tools; targeted `rg -n` and `rg --files` | 0 | Critical execution code untruncated; `rg` reported absent `contracts/` and root `scripts/` directories inside group. Group exit is final pipeline status, not proof every searched path existed. |
| `cat` four project manifests, `sed -n '370,435p' .../bybit.ts`, monitor, index; targeted tool/risk search; EARS/Verify/clarify references | 0 | Confirmed direct signed mutation, sparse task coverage, monitor and decision boundaries. |
| Python documentation edit script | 0 | Updated only DEFINE; no source mutation or tests executed. |

No builds, pytest, TypeScript checks, live DSH install, account read, trading request, migration, dependency scan, secret scan, commit or push was run by this audit. Parent task may record its independent checks elsewhere. Outstanding work is every unaccepted scope/gap above; this report does not promote old report claims to current verified outcomes.


## Exact original acceptance inventories (unchecked)

These checklists preserve exact original named items so aggregate AT rows cannot hide scope. Every item is still **unaccepted by this audit**; partial source mappings are the corresponding numbered table rows above. A checkbox requires implementation-specific tests/evidence, not a matching name. Section 7 strategy families map to `lib/strategies.ts` (only three named implementations) and future engine registry; section 17 maps to current registrars (different names/partial operations), no six Skill assets; section 21 maps to existing TS assertions/Python tests and missing quant/exchange suite; section 25 maps to the complete matrix and cannot pass until all applicable requirements are met.

### 7. 量化策略系统

建立统一的 Strategy Registry。

每个策略必须包含：

- [ ] Strategy ID。
- [ ] Name。
- [ ] Version。
- [ ] Source Repository。
- [ ] License。
- [ ] Supported Markets。
- [ ] Supported Instruments。
- [ ] Timeframes。
- [ ] Required Features。
- [ ] Warmup Period。
- [ ] Configuration Schema。
- [ ] Entry Conditions。
- [ ] Exit Conditions。
- [ ] Target Exposure。
- [ ] Risk Constraints。
- [ ] Backtest Metrics。
- [ ] Validation Status。
- [ ] Current Status。

统一策略接口应覆盖：


接口可以根据 NautilusTrader 的策略生命周期调整，但不得让策略直接绕过统一订单管理和风控入口。

#### 初始策略库

必须实现或适配以下策略类型：

##### Trend Following
- [ ] EMA / SMA Crossover。
- [ ] Donchian Channel。
- [ ] ADX Trend Filter。
- [ ] Trend Strength。

##### Momentum
- [ ] Time-series Momentum。
- [ ] Rate of Change。
- [ ] Multi-timeframe Momentum。

##### Mean Reversion
- [ ] Bollinger Bands。
- [ ] Z-Score。
- [ ] RSI Reversion。
- [ ] Statistical Mean Reversion。

##### Volatility
- [ ] ATR Breakout。
- [ ] Volatility Expansion。
- [ ] Volatility Regime Strategy。

##### Crypto-specific
- [ ] Funding Rate Strategy。
- [ ] Funding / Basis Research。
- [ ] Open Interest Analysis。
- [ ] Liquidation Imbalance。
- [ ] Order Book Imbalance。
- [ ] Volume Profile。

##### Advanced
- [ ] Grid Trading。
- [ ] DCA。
- [ ] Market Making。
- [ ] Statistical Arbitrage。
- [ ] Machine Learning Prediction。
- [ ] Reinforcement Learning。
- [ ] Ensemble Strategy。

策略库应支持按需扩展，不要求第一阶段全部投入实盘。

### 17. DSH Tools 和 Skills

至少实现以下 Tools：

#### Bybit

- [ ] bybit_test_connection
- [ ] bybit_get_account
- [ ] bybit_list_instruments
- [ ] bybit_get_market_data
- [ ] bybit_get_positions
- [ ] bybit_get_orders

#### Market Analysis

- [ ] quant_analyze_market
- [ ] quant_detect_market_regime
- [ ] quant_analyze_sentiment
- [ ] quant_get_market_snapshot

#### Strategy

- [ ] quant_list_strategies
- [ ] quant_get_strategy_details
- [ ] quant_select_strategy
- [ ] quant_get_strategy_performance
- [ ] quant_run_backtest
- [ ] quant_compare_strategies

#### AI Research

- [ ] quant_research_factor
- [ ] quant_generate_strategy_candidate
- [ ] quant_evaluate_model
- [ ] quant_get_research_report

#### Trading

- [ ] quant_get_portfolio
- [ ] quant_get_positions
- [ ] quant_get_orders
- [ ] quant_start_paper_trading
- [ ] quant_stop_trading
- [ ] quant_enable_live_trading
- [ ] quant_emergency_stop

所有工具必须有严格的输入输出 Schema、权限控制和异常处理。

不得把 API Secret 作为工具参数传给 Agent。

高风险交易工具必须使用 DSH 当前版本支持的审批机制。

#### Skills

提供：

- [ ] bybit-quant-operations
- [ ] quantitative-market-analysis
- [ ] quantitative-strategy-research
- [ ] quantitative-backtesting
- [ ] portfolio-risk-management
- [ ] algorithm-repository-audit

### 21. 测试要求

禁止只做静态检查。

必须建立以下测试：

#### TypeScript

- [ ] Oxlint。
- [ ] Oxfmt Check。
- [ ] tsc。
- [ ] Vitest。
- [ ] DSH 插件集成测试。

#### Python

- [ ] Ruff。
- [ ] Pyright。
- [ ] pytest。
- [ ] Hypothesis 属性测试。

#### Quant Tests

- [ ] 因子计算正确性。
- [ ] 策略信号正确性。
- [ ] 仓位计算。
- [ ] 风控边界。
- [ ] 手续费计算。
- [ ] Funding 计算。
- [ ] 滑点模型。
- [ ] 回测一致性。
- [ ] 时间序列无未来数据泄露。

#### Exchange Tests

- [ ] Bybit API Mock。
- [ ] WebSocket Mock。
- [ ] API Rate Limit。
- [ ] Network Failure。
- [ ] Partial Fill。
- [ ] Duplicate Order Prevention。
- [ ] Reconciliation。
- [ ] Demo / Testnet E2E。

绝不允许在 CI 中使用真实 Mainnet 账户执行交易。

必须使用可复现的测试数据和固定随机种子。

### 25. 最终验收标准

最终交付必须满足：

##### Engineering
- [ ] 正式 Nx + pnpm Monorepo。
- [ ] TypeScript 严格类型检查。
- [ ] tsdown 正常打包。
- [ ] Oxlint / Oxfmt 检查通过。
- [ ] Python uv Workspace 正常。
- [ ] Ruff / Pyright / pytest 通过。
- [ ] CI 完整运行。
- [ ] DSH 插件正常安装。

##### Bybit
- [ ] 用户可以直接连接自己的 Bybit API。
- [ ] 能动态读取交易品种。
- [ ] 能选择一个或多个币种。
- [ ] 能获取实时行情。
- [ ] 能读取账户和持仓。
- [ ] 能管理订单。
- [ ] 能处理网络和交易所异常。

##### Quant
- [ ] 有真实可运行的策略库。
- [ ] 有统一策略接口。
- [ ] 有回测系统。
- [ ] 有市场状态识别。
- [ ] 有动态策略选择。
- [ ] 有策略组合和目标仓位计算。
- [ ] 有风险管理。
- [ ] 有算法研发和验证机制。

##### AI
- [ ] 多 Agent 能正常协作。
- [ ] AI 能分析用户指定币种。
- [ ] AI 能根据市场状态选择策略。
- [ ] AI 能解释策略变更。
- [ ] AI 能研究候选算法。
- [ ] AI 不能绕过风控。
- [ ] AI 不能直接获得 API Secret。

##### Trading
- [ ] 支持历史回测。
- [ ] 支持内部模拟交易。
- [ ] 支持 Bybit Demo。
- [ ] 支持 Bybit Testnet。
- [ ] 经用户授权后支持 Mainnet。
- [ ] 所有真实订单可追踪。
- [ ] 所有策略支持回滚。
- [ ] 所有风险事件可审计。

Documentation verification: `git diff --check -- sdd/features/DEFINE_BYBIT_AI_QUANT.md sdd/reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md` exited 0. Exact registrar search and final source inventory exited 0; newly concurrent engine files are recorded above as in-flight/unverified. No release claim.
