# Bybit AI Quant

Bybit AI Quant 是运行在 DeepSeek Harness（DSH）中的 TypeScript Host/Client Bundle。仓库采用 Nx + pnpm Monorepo；Python uv 工作区包含 `quant-data`、独立只读行情服务 `quant-engine` 和可选的原生合成 paper 服务。当前插件提供 Bybit REST 行情、确定性指标和单资产多头回测、本地模拟盘、交易对观察列表、带代码侧风控门的 AI 决策账本，以及包含原生 paper 控制卡的行情面板。

仓库仍处于开发阶段。SDD 目标中的完整自主量化平台尚未完成：Python 引擎已有公共 Testnet WebSocket、有界队列与受监督的持续消费，可独立于 DSH 运行；DSH 已通过生成式、运行时校验的 TypeScript SDK 提供引擎工具和只读面板卡片，原有 candle/account/analysis 页面保留 REST。离线原生 Nautilus 基础已验证有限回测成交与撤单。交易所订单的 Nautilus 唯一执行权、完整量化/AI/研究平台、官方升级状态保留与真实 OAuth 仍未完成或未验证，详见[原始范围审计](sdd/reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md)。

## 安装 Bundle

使用 DSH 官方 Plugin Manager 的 `install_bundle` 流程安装本仓库（或构建后的项目目录）。不要手工编辑 Harness Profile 中受管理的文件、`package.json` 或 `cordis.patch.yml`。安装前先生成 Host 和浏览器入口：

```sh
pnpm install --frozen-lockfile
pnpm build
pnpm bundle:check
```

Bundle patch 会插入 `@bybit-quant/dsh-plugin` Host 行，并默认使用 `[TESTNET]`。patch 不包含凭证。升级和卸载也必须通过 Plugin Manager；用户状态和凭证文件保留在 `$DSH_HOME/bybit-quant/`。

## 当前工具

- `bybit_market`、`bybit_instruments`、`bybit_account`：读取公开行情/交易规则或已授权账户数据。
- `quant_signals`、`quant_backtest`、`quant_watchlist`：运行确定性指标、单资产多头回测并维护经过交易所校验的交易对列表。
- `quant_paper`：操作本地模拟 USDT 账户。
- `quant_brief`、`quant_decide`、`quant_review`：构建行情简报，对 AI 提议执行代码侧限额，记录决策并评估已完成决策。
- `quant_get_engine_status`、`quant_get_market_snapshot`：通过生成式 SDK 读取独立引擎事实；行情 ready 不等于账户或执行 ready。
- `quant_get_paper_status`、`quant_start_paper`、`quant_stop_paper`、`quant_submit_paper_order`、`quant_get_paper_command`：访问独立原生合成服务；必须提供 paper 配置，控制默认关闭。
- `bybit_trade`：只有全部安全检查通过后才会预览或发送订单。

回测不包含杠杆、资金费，也不保证盈利。

## 交易安全边界

Bundle 默认配置为 `env: testnet`、`allowLiveTrading: false`、`allowTestnetTrading: true`，单笔名义额上限为 24 USDT。Mainnet 默认关闭。真实订单还必须同时满足凭证、环境开关、`confirm: "LIVE"` 和 `dryRun: false`，并通过账户身份、余额、交易规则、名义额和风控检查。主账户凭证还需要额外的 `allowMainAccount` 开关。Testnet 授权不等于 Mainnet 授权。

面板通过已认证 DSH bridge 提供 REST 视图及按需引擎查询。独立的原生 paper 卡片只为已配置的合成会话提供手动状态检查、Start 和 Stop，不提供浏览器下单路由，也不后台轮询。Python 服务仍只绑定 loopback，认证远程部署尚未实现；已安装载体的认证和真实浏览器交互仍待验证。

## Testnet OAuth

内置 PKCE 客户端遵循 Bybit 面向 AI Agent 的 Testnet OAuth 流程。它使用 Testnet 授权页、`ai-account` 范围、`127.0.0.1:9876` 回环回调和 `api2-testnet.bybit.com` OAuth API。授权前请阅读 Bybit 的[AI Agent 连接指南](https://www.bybit.com/en/learn/ai-subaccount/agent-connect)。

请在仓库根目录运行这些命令，并在浏览器授权完成前保持 `start` 进程运行：

```sh
pnpm --filter @bybit-quant/dsh-plugin oauth -- start
pnpm --filter @bybit-quant/dsh-plugin oauth -- exchange
pnpm --filter @bybit-quant/dsh-plugin oauth -- accounts
pnpm --filter @bybit-quant/dsh-plugin oauth -- select <sub_member_id>
```

点击 **Authorize** 前，请你本人在 Bybit 页面核对 Agent 名称和请求权限。回环回调返回后运行 `exchange`，查看 AI 子账户列表，再明确选择目标账户。客户端不会自动选择或创建账户。Token 和已选择账户的凭证会以受限权限写入本地文件，不会打印到日志。撤销访问请在 Bybit 删除对应 AI 子账户。此流程不支持 Mainnet OAuth。

## 工作区结构

```text
apps/dsh-plugin/          DSH Host、浏览器客户端、工具、脚本和测试
python/packages/quant-data/  Alembic 数据包与本地持久命令账本
python/packages/quant-risk/  纯函数确定性风险否决基础
packages/ts/quant-contracts/ 共享行情 DTO
packages/ts/quant-api-client/ 生成式 SDK 和运行时校验
python/packages/quant-execution/ 离线原生 Nautilus 基础
python/apps/quant-engine/   独立只读 Testnet 服务
sdd/                      Brainstorm、Define、Design 和验证报告
```

`dist/` 是生成产物，也是插件唯一打包内容。手写 TypeScript 使用 strict，并保持每个文件不超过 500 行。Python 项目由 uv 管理；Nx 会发现 `@bybit-quant/dsh-plugin`、`@bybit-quant/quant-contracts`、`@bybit-quant/quant-api-client`、`quant-execution`、`quant-data`、`quant-risk` 和 `quant-engine` 七个独立项目（发现和实际依赖图均已验证）。

## 开发与验证

```sh
pnpm install --frozen-lockfile
pnpm build
pnpm lint
pnpm typecheck
pnpm test:unit
pnpm exec nx run @bybit-quant/dsh-plugin:test:paper-process --skip-nx-cache
pnpm bundle:check
pnpm sdk:check
pnpm sdk:test
pnpm typecheck:tooling
pnpm test:tooling
pnpm python:lint
pnpm python:typecheck
pnpm python:test
pnpm run security:deps
pnpm run sbom
```

根目录没有 `pnpm test:network` 脚本；公开端点 smoke 使用 `pnpm exec nx run @bybit-quant/dsh-plugin:test:network`。它固定访问 `api-testnet.bybit.com` 公共 Testnet 行情，无凭证、账户访问或订单；网络不可用时如实记录失败/未验证，不计为跳过后的通过。发布 Verify Gate 是 `pnpm run verify`；文档或 CI 通过不等于已经取得官方 Plugin Manager 生命周期回执。

## 独立 Testnet 引擎

在仓库根目录启动，并明确指定交易对：

```sh
uv sync --project python --locked
uv run --project python --locked quant-engine --symbols BTCUSDT ETHUSDT
```

服务只绑定 loopback，默认地址为 `127.0.0.1:8765`，提供只读 `/api/v1/health` 和 `/api/v1/market/{symbol}`。它不读取凭证、不调用订单 API。ready 仅表示行情摄取新鲜可用；执行与对账仍标为 unknown。增量行情缺少的字段保持 null。就绪性、关闭、Nx 命令及离线 OpenAPI 校验详见[引擎运行手册](docs/runbooks/engine-service.md)。DSH 的 `engineBaseUrl` 默认 `http://127.0.0.1:8765`，仅接受数字 loopback HTTP origin。两个引擎工具及已认证 `?view=engine` bridge 视图均使用 SDK。面板按用户点击查询，不进行后台轮询；卸载 DSH 会取消请求，独立进程继续运行。增量字段保持 null，失败返回有界安全代码。

## 离线原生执行及验证边界

`uv run --project python --locked pytest python/packages/quant-execution/tests -q` 使用真实 NautilusTrader 1.231.0 `BacktestEngine`，覆盖市场成交、挂单撤销及部分成交后撤销。离线模拟 API 只接受 `backtest`，另有下文说明的独立合成 paper 运行时；没有实现 live/Testnet 执行器、持久订单恢复或完整最终风控；当前 TS REST 订单路径尚未切换到 Nautilus。

原生测试必须使用根目录锁定的 `uv` 工作区：它显式将 fsspec 覆盖为已修复2026.6.0，而 Nautilus1.231.0 元数据仍精确要求2026.2.0。修复环境通过漏洞扫描和兼容 fixtures，但 `uv pip check` 会报告声明冲突，standalone pip 拒绝解析；不能声称元数据完全兼容。

SDK、DSH 接线、原生执行与命令准入层均有独立限定范围 ACCEPT。已发布代码 `b75d73c` 包含认证的持续模拟执行服务、原子风控预留及生成式 paper SDK；对应 [CI](https://github.com/XueHua-s/dsh_bybit_plugin/actions/runs/44089248505) 两个 job 均成功，已核对阻塞验证、四个 Python 项目、两个实际 OpenAPI 契约、安全扫描和 SBOM 步骤。实际提交/推送 hooks 通过，其中 Python 252 项测试通过。[Draft PR #1](https://github.com/XueHua-s/dsh_bybit_plugin/pull/1) 保持草稿，未合并。此收据覆盖代码提交，当前文档及治理更新另行验证。浏览器交互、已安装 Harness 认证与官方升级保留验证仍未完成；证据与边界见 [Verify Gate](sdd/reports/VERIFY_GATE_2026-11-17.md)。

## 风控与持久命令基础

新增 `quant-risk` 包提供独立的纯函数风险否决：使用引擎拥有的快照、待执行预留和显式策略，校验后以 Decimal 计算保守总敞口。`quant-data` 新增本地 SQLite 持久命令账本，用于命令幂等、生命周期、单次派发认领及追加审计事件。二者均取得限定范围的独立 ACCEPT；已发布风险/账本基线的 Python 213 项测试及类型、格式检查通过；当前集成 paper 的工作区为 252 项。此结论仅覆盖基础模块，不能视为已接入订单执行的最终风控。

风险批准不授予交易权限，账本也不会发送或自动重发订单。下述可选合成 paper 服务现已接入串行账户所有权、原子风险预留与持久原生成交证据；交易所订单的 Nautilus 唯一提交权、TS REST 切换、完整长期 private 状态及未知订单对账仍未完成。新 Alembic 迁移仅限隔离测试，未迁移用户数据库。详见 [risk 设计](sdd/features/DESIGN_QUANT_RISK.md)、[命令账本设计](sdd/features/DESIGN_COMMAND_LEDGER.md)与 [Verify Gate](sdd/reports/VERIFY_GATE_2026-11-17.md)。

## 持续运行的原生内部模拟盘

可选的独立 paper 应用在子进程中运行 Nautilus `TradingNode`。引擎串行执行风险评估、持久命令和风险预留，再进行原生派发；只支持显式合成 BTC 有限深度 fixture 与 LIMIT 命令。默认行情应用仍只有两个只读路由，paper 使用独立的 `quant-paper.v1` OpenAPI 和生成式 SDK。私有 Unix broker 为 DSH Host 提供固定会话、固定 origin 的内存 capability；可信启动器的私有 FD 模式仍受支持。Token 不会出现在配置、argv、环境变量、文件、浏览器或模型参数中。

[DSH 原生 paper 进程回执](sdd/reports/DSH_PAPER_PROCESS_E2E_2026-11-17.md)验证了真实构建 Host→私有 broker→SDK→CLI→原生进程链路，包括风控否决、原生成交、注入的 post-dispatch503 后按原 request ID 恢复、Host 关闭独立性及有界清理。原生 paper 卡片提供明确的 Check/Start/Stop，固定标识为 synthetic/no-exchange，配置和控制默认关闭。该进程目标是当前工作树的阻塞检查，不构成托管 CI 回执。已安装 Harness 认证、真实浏览器交互和官方升级状态保留仍待验证；旧 `quant_paper`、AI 账本和 TS 交易路径保持独立，Nautilus 唯一交易所执行权、TS 写路径切换、完整恢复、策略、AI 和隔离研究仍未完成。完整产品仍为 PARTIAL。实际 CLI、broker 和临时数据库流程见[内部模拟盘运行手册](docs/runbooks/paper-service.md)。

## 许可证范围

仓库根许可证为 MIT。`quant-execution` 是混合许可证包，元数据为 `MIT AND LGPL-3.0-only`：其中 [paper_sandbox.py](python/packages/quant-execution/src/quant_execution/paper_sandbox.py) 改编自固定 NautilusTrader 1.231.0 上游，保留 LGPL-3.0-only；本项目其他原始执行代码采用 MIT。包的 [NOTICE](python/packages/quant-execution/NOTICE.md) 和 `LICENSES/` 随源码与 wheel 分发，包含 LGPLv3 及其引用的 GPLv3 基础条款；附带 GPL 文本不改变其他原始文件的 MIT 许可。根 MIT 许可证不会将该改编文件或第三方依赖重新许可为 MIT。

## 状态与凭证

旧模拟盘状态和账本默认位于 `$DSH_HOME/bybit-quant/state.json`；原生 paper 使用明确选定、已迁移的 SQLite 数据库和服务拥有的会话。交易所 API 凭证来自 DSH credential store、文档规定的环境变量或权限受限的本地文件；不得提交、记录或写入 Bundle patch。原生 paper capability 只通过私有内存 broker 提供，不回退到交易所凭证。Python Alembic schema 与备份工具属于开发组件，连接持久化环境前必须确认环境并制定备份方案。

## 限制

独立服务已有公共 Testnet 流式行情、有界重连及进程内 worker 重启。OS 进程恢复、完整行情快照重建/持久化、账户/订单恢复、对账、自主投资能力和 Mainnet 就绪性仍未完成或未验证。开发和审查请使用 Testnet、Mock 或公开端点，并以 SDD 证据为准。
