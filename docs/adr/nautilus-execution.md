# ADR: NautilusTrader 作为唯一执行核心

- 日期：2026-11-17，Asia/Shanghai。
- 状态：**采用边界已决定；实现、依赖安装和交易验证未完成**。本 ADR 是下一 SDD Design/Build 切片的研究输入，不是可运行集成或发布验收。
- 原始需求：用户附件 `pasted-text-1.txt` §6.1（403–470 行）、§12（1113–1170 行）、§16（1336–1402 行）已实际读取。唯一真实订单入口必须是 NautilusTrader；Python FastAPI/Pydantic 是跨语言 schema 的唯一来源。

## Drift 与决定

旧 `docs/research/github-repository-audit.md` 因 Rust/Python 和 LGPL 复杂度拒绝 Nautilus，与原始需求直接冲突。复杂度是隔离和验证的理由，不是删改要求的授权。修正：采用 Nautilus 原生 Bybit Adapter、执行引擎、OMS、仓位/成交事件和 reconciliation；禁止用自写 TS/Python REST executor 替代。pybit 仅能补充非下单能力，不成为第二执行系统。

已读取 `apps/dsh-plugin/src/host-tools-trade.ts`：create/close 直接调用 TS `client.createOrder`，cancel/cancel_all 直接调用 `client.cancelOrder/cancelAll`，且以 `sent: true` 返回请求结果。这些路径是待消除的第二执行入口；本次文档修改没有改变运行行为，当前 drift 仍存在。迁移必须一次切断全部四个 mutation 分支，保留预览 UX 但将执行校验移入 Python 权威边界。撤单不应误要求开仓余额，但仍必须校验环境、账户身份、订单归属和授权。

## 当前采用版本：稳定版 1.231.0（追加兼容性决策）

**下一切片采用 `nautilus_trader==1.231.0`，保留 Python3.12，不为 2.x RC 升级运行时。** 官方 tag `v1.231.0` peeled commit `27a8e54e7ac3c57d6cbf8891f0283dfbaee97317` 已实际浅克隆读取；PyPI JSON 与已下载 macOS wheel 的 METADATA 均要求 `>=3.12,<3.15`。本机 macOS27.3 ARM64 与实际 `cp312-cp312-macosx_26_0_arm64` tag 下限匹配；LinuxCI 有 `manylinux_2_35_x86_64`/aarch64 wheel 元数据。未安装、未 import，兼容性仍需真实 smoke。

权威 stable API 为 `BybitExecClientConfig`、`BybitLiveDataClientFactory`、`BybitLiveExecClientFactory`、`TradingNode(config=TradingNodeConfig(...))`；经 `node.add_data_client_factory` / `add_exec_client_factory` 注册后 `node.build()`。`LiveExecEngineConfig(reconciliation=True, ...)` 控制对账。Sandbox 使用 `SandboxExecutionClientConfig` 与 `SandboxLiveExecClientFactory`，starting_balances 为字符串列表；Backtest 使用 `nautilus_trader.backtest.engine.BacktestEngine` 和 `nautilus_trader.backtest.models.FillModel`。**下文 2.x LiveNode、ExecutionClientConfig/Factory 示例仅保留研究历史，不作为所选 stable 的实现 API。**

详见 [稳定版兼容性报告](../../sdd/reports/NAUTILUS_STABLE_COMPATIBILITY_2026-11-17.md)：固定源码文件/测试、实际 wheel SHA256/依赖、macOS文档与wheel tag差异、Demo/Testnet配置、Mock未知提交对账、Sandbox/Backtest事件验证计划。stable METADATA 许可为 `LGPL-3.0-or-later`，不能沿用 2.x `-only` 元数据；发行义务仍按实际产物复核。

## 先前 2.x 开发线研究（历史证据，不采用其 API）

只读研究缓存 `/tmp/bybit-nautilus-research`；成功的 `git clone --depth 1 https://github.com/nautechsystems/nautilus_trader.git /tmp/bybit-nautilus-research` 退出码 0；`git rev-parse HEAD` 退出码 0，输出 **`ee28bfe123738d379166b123f1e142e8697c4bfb`**。缓存未进入项目发行物，未运行上游代码、安装脚本或测试。

此前审计的 `33492c8135a5e0dceedc21d9ee3ff7432f04ff12` 不是本次已验证提交；本次 GitHub API 与网页读取它均返回 404，原因未确定。不要继续把它当作可复核的 Nautilus 证据。本次完整 API 结论仅针对上述实际读取的 SHA。

重要：这个 SHA 是 **2.0 开发线**，`python/pyproject.toml` 标记 `2.0.0`；提交内安装文档明确 2.x 仍为 RC，普通未指定预发布的 PyPI 安装可能解析到 API 不兼容的 1.x。源码 version 字段不等于已发布稳定 wheel。不得把这里的 2.x API 与 1.x 示例或 `BybitLiveExecClientFactory` 混搭。

- 2.x 源码要求 CPython `>=3.13,<3.16`；安装文档支持 Python 3.13–3.15。
- 官方测试平台：Ubuntu 22.04+ x86_64/ARM64（glibc >=2.35），macOS 15+ ARM64，Windows Server 2022+ x86_64。其他平台的可运行性不能据此保证。
- 当前项目 `python/pyproject.toml`、engine pyproject 要求 `>=3.12`，pyright/ruff 目标 3.12，已存在 `.venv/lib/python3.12`；`python/uv.lock` 和 `pnpm-lock.yaml` 未匹配 `nautilus`，site-packages 未找到 Nautilus 元数据。**没有已安装、已锁定或已兼容的 Nautilus 证据**。
- **已被后续 stable 研究取代的提案**：此前建议 Python3.13/2.x Mock 切片未实施；现选择稳定 1.231.0 与 Python3.12，已完成独立源码和 wheel metadata 研究。仍需真实依赖锁/安装/执行验证，不允许浮动 `--pre`、nightly 或将开发 SHA 用作生产 pin。

## 先前 2.x 原生配置与工厂（不可用于 1.231.0）

实际读取 `python/nautilus_trader/adapters/bybit/__init__.py`、Rust Python bindings 与 `examples/live/bybit/exec_tester.py`，API 为：

- `from nautilus_trader.adapters.bybit import BybitDataClientConfig, BybitExecutionClientConfig, BybitDataClientFactory, BybitExecutionClientFactory, BybitEnvironment, BybitProductType`。
- `LiveNode.builder(node_id, trader_id, Environment.LIVE)`，通过 `.add_data_client(None, BybitDataClientFactory(), data_config)` 和 `.add_exec_client(None, BybitExecutionClientFactory(), exec_config)` 注册，`.with_reconciliation(reconciliation=True)` 后 `.build()`。
- config 显式传 `environment=BybitEnvironment.TESTNET` 或 `.DEMO`，`product_types=[BybitProductType.SPOT, BybitProductType.LINEAR]`；execution config 传稳定的 `AccountId`。允许策略/品种清单必须进一步收紧，不因配置两类产品而自动授权全部市场。
- Instrument ID 为 `BTCUSDT-SPOT.BYBIT` / `BTCUSDT-LINEAR.BYBIT`；只用 `BTCUSDT` 会丢失产品信息。Instrument provider 提供精度/规则，不能复用 TS 浮点四舍五入作为权威值；跨语言金额和数量用十进制字符串。
- 上游示例默认 MAINNET、`DRY_RUN=False`、`LiveRiskEngineConfig(bypass=True)`，**只作为 API 证据，不执行或照搬它的安全配置**。项目默认 internal paper；发送 Testnet/Demo 仍需要用户范围授权、账户和资金/风控校验；Mainnet 独立明确授权且本切片关闭。

### 环境与能力

依据固定提交 `crates/adapters/bybit/src/common/urls.rs` 和 `docs/integrations/bybit.md`：

| 环境 | REST / private WS | public WS | 下单传输 |
|---|---|---|---|
| Testnet | `api-testnet.bybit.com` / `stream-testnet.bybit.com/v5/private` | `stream-testnet.bybit.com/v5/public/{spot,linear}` | 原生 Adapter trade WS；不使用生产凭证 |
| Demo | `api-demo.bybit.com` / `stream-demo.bybit.com/v5/private` | mainnet **public** `stream.bybit.com/v5/public/{spot,linear}` | Adapter 自动用 HTTP；不支持 trade WS、fast execution |
| Mainnet | `api.bybit.com` / `stream.bybit.com/v5/private` | `stream.bybit.com/v5/public/{spot,linear}` | 本项目本切片禁止连接私有交易端点 |

REST 为 HTTPS，WS 为 WSS。Demo 的公共市场数据来自 Mainnet，并不意味着 Demo 私有账户可混用 Mainnet。env enum 由项目必须显式设置；不得依赖上游 MAINNET 默认值，不允许普通 API 调用者覆盖 base URL。凭证通过服务侧受控 credential reference 解析，API 响应/日志/schema 不包含 key/secret。

Spot 和 Linear 均支持 Market/Limit、IOC/GTC/FOK 与条件订单；reduce-only 仅在衍生品有意义，Spot 拒绝。下一切片先 Market/Limit + Linear reduce-only，停止/TP/SL 能力显式标记未实现，而非虚构全覆盖。没有原生 OCO/括号安全关联；不得同时裸发 entry/TP/SL 并假设安全。要在确认 entry fill 后按实际已成交仓位配置退出，并逐腿处理拒绝/撤销竞态。One-way 为首个受支持模式；Hedge 需要 USDT linear perpetual 与 `params.position_idx` 1/2、双侧仓位验收后再启用，不能取 `positions[0]` 盲目平仓。

## ID、幂等与恢复

- Pydantic command 必须带 `idempotency_key`；服务端持久化 `(environment, account_ref, idempotency_key)` 唯一约束和 canonical payload digest。同 key 同 payload 返回原命令；不同 payload 返回冲突。生成一次并持久化稳定 ClientOrderId，派生重试绝不创建新 ID。
- 固定源码 `execution.rs` 将 `client_order_id` 写入 Bybit `order_link_id`（HTTP/WS payload），撤单携带 venue ID（如已有）与 client ID；缓存维护双向身份，不用 HTTP request ID 冒充订单 ID。ID 长度/字符规则在实际选定 release 与 Bybit 文档中再次验收；本次未单独核验其硬限制。
- transport accepted/HTTP ack 不等于 accepted、filled 或 canceled。返回 command receipt（202）后通过 `OrderAccepted/OrderRejected/OrderFilled/OrderCanceled` 与 status/fill/position reports 更新状态。保存已成交数量、累计手续费、venue order ID、TradeId 和事件去重键，允许 partial-fill 与 cancel racing。
- 上游 `execution.rs` 对非确定拒绝的 submit failure 保留订单并等待 reconciliation。本项目命令状态转 `reconciling`，禁止盲目再次 submit；先按原 ClientOrderId/venue ID 查询，再按已验证恢复策略处理；无确切证据时保持 unknown 并冻结新开仓。
- `LiveNode.with_reconciliation` 是必要条件，不是本项目“恢复安全”的充分证明。启动读取持久化状态，与 open orders、历史 executions 和 positions 对账后才 ready；私有流重连、数据过期、身份/余额/规则缺失、队列溢出均关闭新开仓。取消 ack 或超时不能提前更新 terminal；query/reports 确认后才完成。

## 跨语言 API 与最小深模块

不把 Nautilus 对象、Bybit REST payload 或生命周期控制权泄漏给 DSH Tools。常驻 Python engine 拥有 node、事件循环、账户/OMS 与恢复；FastAPI 提交有界命令到 engine 线程/队列，绝不在每次 Tool 中启动 node 或在任意 HTTP worker 上直接访问非线程安全 cache。

契约源仅 Pydantic/FastAPI `/api/v1`：在既有 health/status 基础上增加 `POST /execution/commands`（discriminated union submit/cancel/cancel_all/close，preview flag），`GET /execution/commands/{id}`、`GET /orders`、`GET /positions`、`GET /execution/events` SSE（带可恢复 cursor）。schema 包含 environment、account_ref、strategy_id、instrument_id、decimal-string qty/price、client_order_id/venue_order_id；响应 command_id/status/reason，不含 credentials。认证、重放防护、受限授权与幂等在 Python 执行入口强制；DSH 的 confirm 字符串不是服务端授权能力。响应事件带 seq、event_id、时间和 correlation ID，SSE 掉线要补拉状态。

下一切片拟定 File Manifest（**尚未新增源码**）：

| 文件 | 职责 |
|---|---|
| `python/apps/quant-engine/src/quant_engine/execution/contracts.py` | Pydantic command/receipt/event schema，OpenAPI 唯一来源 |
| `python/apps/quant-engine/src/quant_engine/execution/service.py` | 深模块：preview/submit/cancel/status 与授权、risk、idempotency admission，屏蔽底层引擎细节 |
| `python/packages/quant-execution/src/quant_execution/bybit_runtime.py` | 唯一 Nautilus node owner 的进程边界、工厂/命令桥接和 shutdown；无自写 REST executor |
| `python/apps/quant-engine/src/quant_engine/execution/reconciliation.py` | 事件/report 到持久化状态、恢复闸门、unknown outcome；避免 service 与 runtime 重复 OMS |
| `python/apps/quant-engine/src/quant_engine/execution/store.py` | durable command/ID/event journal，封装 DB schema/transaction；迁移单独备份与回滚 |
| `python/apps/quant-engine/src/quant_engine/api.py`、`runtime.py`、`service.py` | 挂接 router、生命周期与健康指标；保持单个手写文件 <=500 行 |
| `packages/ts/quant-contracts/src/generated/openapi.ts` | 从 Python schema 生成，禁止手写重复 DTO |
| `packages/ts/quant-contracts/src/index.ts` | 导出 generated types 与 `openapi-fetch` client 边界 |
| `apps/dsh-plugin/src/host-tools-trade.ts`、`host-runtime.ts` | 所有 mutation/preview 走生成 client；删除直接 create/cancel/cancelAll 与 positions[0] close 路径 |
| Python engine tests / TS trade contract tests | Mock/Sandbox 执行与边界 deny/receipt/event 测试，禁止 Mainnet |
| Python workspace/engine pyproject、uv.lock、Nx/CI、README、TS/Python SBOM | 精确依赖与真实项目任务边、兼容版本、审计与运维同步 |

应用 software-design-philosophy：当前该切片设计诊断 **5/10（8 项中 4 项未满足；评估，不是测试分数）**：失败项是实现变化会影响 callers（TS 直接持有 Bybit payload）、接口注释/生命周期保证不足、order ownership 决策未被单一模块隐藏、仅读边界不足以理解恢复语义。上面的执行 service 隐藏环境、授权、ID 与恢复知识；generated contract 消除重复知识，runtime 隐藏 Nautilus API。达到 10/10 仍需实现这些边界、注释和独立审查，不靠增加 pass-through wrapper 数量。

## 验证设计（2.x 历史表面；stable 以追加报告为准）

上游已实际读取：`python/tests/unit/adapters/sandbox/test_sandbox_factories.py`（`SandboxExecutionClientFactory` + `LiveNode.builder(..., Environment.SANDBOX).add_simulated_exec_client(...)`）、`python/tests/unit/backtest/test_fill_models.py`（BacktestNode/FillModel）、`crates/adapters/bybit/tests/integration/exec_client.rs` 的 Mock venue Demo cancel-confirm 测试（含 partial fill），及 `tests/common/mock_venue.rs` 文件存在性。这说明存在可用测试表面，不代表这些测试本次运行或通过。

下一 Verify Gate 必须按追加 stable 报告在隔离环境真实运行：Python 3.12 + 1.231.0 wheel import/factory smoke；Sandbox submit/partial fill/cancel 与累计数量；Mock Bybit adapter 断线/重复事件、timeout→reconcile→禁止重复下单、cancel ack 未确认、启动未完成对账；spot/linear 精度和 reduce-only；Testnet/Demo URL/凭证引用隔离；Mainnet fail-closed；TS Tool 全部 mutation 只访问本地 API；OpenAPI regeneration 无 diff；Nx build/typecheck/test；secret scan、漏洞扫描与双语言 SBOM。CI 默认禁网并无凭证，必要外部 Demo/Testnet E2E 是单独授权的人工 gate。使用 Sandbox 不可声称已通过真实 Bybit E2E 或盈利验证。

## LGPL 发行边界

实际读取上游根 `LICENSE` §0–4 与 `python/pyproject.toml` 的 `LGPL-3.0-only`。计划优先原样依赖独立 wheel/进程，记录版本/hash/源代码位置、版权及 LGPL/GPL 文本，保留库可替换性；若修改库或再分发组合产物，需要按实际打包方式核对 source、relink/recombine、安装信息与反向工程调试等条款。独立进程不是自动豁免证明，MIT 主项目也不会自动消除 LGPL 条件。发行前逐项核对 wheel 内 native/传递依赖许可和 notices，并由有资质人员复核适用义务；本 ADR 不是法律结论，也不宣称许可证扫描完成。

## 证据清单与未完成项

公开主源：[Bybit integration](https://nautilustrader.io/docs/latest/integrations/bybit/) 已通过 web 实际读取；会漂移，提交内文档为本次事实锚点。[固定提交树](https://github.com/nautechsystems/nautilus_trader/tree/ee28bfe123738d379166b123f1e142e8697c4bfb)。实际读取文件：`python/pyproject.toml`、`docs/getting_started/installation.md`、`LICENSE`、`python/nautilus_trader/adapters/bybit/__init__.py`、`crates/adapters/bybit/src/python/config.rs`、`src/python/factories.rs`、`src/common/urls.rs`、`src/execution.rs`（ID payload、submit error、query/reconcile 区段）、`docs/integrations/bybit.md`、`examples/live/bybit/exec_tester.py`、上述三个测试文件（均非全仓逐行审计）。所有 `src/...` 简写相对 `crates/adapters/bybit/`。

真实命令记录：初次 sandbox clone 因 DNS 失败退出 128；经网络权限重试 clone 退出 0；rev-parse/read/ripgrep 取证成功（`rg` 无匹配为退出 1，不能理解为已安装）；旧 SHA fetch 404；未执行第三方代码、未安装依赖、未访问 credentials、未发订单、未提交或推送。`git diff --check -- docs/research/github-repository-audit.md docs/adr/nautilus-execution.md` 退出码 0；新增 ADR 另用 trailing-whitespace 检查（未跟踪文件不计入普通 git diff）。

后续报告已补齐 stable 选择、macOS wheel hash 与五个 Python 文件源码对应证据；仍未完成：完整 native wheel 可重现构建证明、平台本机 smoke、线程桥与事件 hook 具体 release API 验证、凭证 provider 注入方式、完整 rate-limit/retry 策略与 ID 限制、持久化/DB migration、全套恢复验证、供应链与发行许可审查、Demo/Testnet E2E。上述缺口保持 pending；不能据研究笔记把执行/实盘 gate 改为 PASS。
