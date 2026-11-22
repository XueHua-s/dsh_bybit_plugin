# Bybit AI Quant

Bybit AI Quant 是运行在 DeepSeek Harness（DSH）中的 Bybit 量化插件。仓库采用 Nx + pnpm Monorepo；Python uv workspace 提供 `quant-data`、独立的只读 Testnet 行情引擎和可选的原生内部模拟服务。

当前 Bundle 提供 Bybit 行情与交易品种读取、确定性指标、单资产多头回测、旧版本地模拟账本、观察列表、带代码风控的 AI 模拟决策，以及只读仪表盘。仪表盘的币种、市场和周期筛选只改变展示行情；AI 使用独立发现的 Bybit 候选池。后台 AI 循环默认关闭且仅记录模拟决策，交易所写入不可用。

这是一个持续开发中的工作区。架构书描述的完整自主量化平台尚未完成。当前已有独立 Python Testnet 公共行情服务、生成的 TypeScript SDK、离线 Nautilus 原生回测基础、策略族和有限的策略选择/组合规划研究模块；Nautilus 作为唯一交易所执行权威、完整账户与订单对账恢复、研究演化闭环仍未完成或未验证。官方 DSH CLI 的临时 `DSH_HOME` 已有可复现的安装、升级、卸载和用户状态保留检查；Host 激活、回滚和活动配置升级保留仍未验证。请以 [架构实现审计](sdd/reports/ARCHITECTURE_IMPLEMENTATION_AUDIT_2026-11-19.md) 为准。

## 安装 Bundle

使用官方 DSH Plugin Manager 的 Bundle 流程安装、升级和卸载，不要手动编辑 Harness Profile 中受管理的 `package.json` 或 `cordis.patch.yml`。安装前构建插件，使 Host 和浏览器入口存在：

```sh
pnpm install --frozen-lockfile
pnpm build
pnpm bundle:check
```

Bundle patch 注册 `@bybit-quant/dsh-plugin` Host 行，默认环境为 `[TESTNET]`，不包含凭证。用户状态和凭证应保存在 `$DSH_HOME/bybit-quant/` 下，并由 Plugin Manager 负责生命周期操作。

如需复现一次不触碰当前 Harness 配置的 CLI 生命周期检查，可运行
`pnpm --dir apps/dsh-plugin run bundle:lifecycle`。脚本会在临时
`DSH_HOME` 中打包当前 Bundle，将临时副本从 1.4.5 升级到 1.4.6，再通过
官方 DSH CLI 卸载，并校验合成的用户状态文件哈希未变化；它不测试 Host
激活、回滚或交易所写入。

## 可用能力

- `bybit_market`、`bybit_instruments`、`bybit_account`：读取公开行情、交易品种规则和已授权账户数据。
- `quant_signals`、`quant_backtest`、`quant_watchlist`：确定性指标、单资产多头回测和交易所校验后的观察列表。
- `quant_paper`：旧版本地模拟账本。
- `quant_brief`、`quant_decide`、`quant_review`：生成候选池和市场简报、应用代码风控、记录模拟 AI 决策并评估结果。
- `quant_get_engine_status`、`quant_get_market_snapshot`：通过生成 SDK 读取独立引擎事实；行情就绪不代表账户或执行就绪。
- `quant_get_paper_status`、`quant_start_paper`、`quant_stop_paper`、`quant_submit_paper_order`、`quant_get_paper_command`：访问独立的原生内部模拟服务；控制能力必须显式配置且默认关闭。
- `bybit_trade`：只做本地预览校验；`dryRun: false` 会在任何 Bybit 请求前返回 `execution_authority_unavailable`。

回测仅支持单资产多头，不模拟杠杆和资金费率，也不保证盈利。当前没有可用的 Testnet 或 Mainnet 交易所下单路径。

## AI 决策与界面边界

AI 候选池由 Bybit Instrument Info 和 ticker 快照动态发现，按交易状态、USDT 计价、精度、成交额和价差过滤，并限制候选数量。可选的配置或观察列表只能收窄候选池；行情查看面板的币种、市场和周期不会进入 AI 决策输入。AI 可选择零个或多个合格标的，并决定方向、仓位和退出参数，也可以放弃交易。

当前后台循环只做受限的模拟研究回合，不提交交易所订单。要实现真正的无人值守 Testnet 交易，还必须完成 Nautilus 执行权威、持久 client order ID、提交不确定结果对账、账户/订单/持仓恢复、急停和完整风险验收。

## Bybit OAuth

插件包含 Bybit AI-agent OAuth PKCE 客户端，支持 Testnet 和 Mainnet 的账户授权读取。Testnet 为默认环境；生产环境使用 `--env=live`。开始授权前请阅读 Bybit 的 [AI-agent 连接指南](https://www.bybit.com/en/learn/ai-subaccount/agent-connect)，并在 Bybit 页面自行检查 Agent 名称和申请的 scope。

```sh
pnpm --filter @bybit-quant/dsh-plugin oauth -- start
pnpm --filter @bybit-quant/dsh-plugin oauth -- exchange
pnpm --filter @bybit-quant/dsh-plugin oauth -- accounts
pnpm --filter @bybit-quant/dsh-plugin oauth -- select <sub_member_id>
```

Mainnet 使用独立的凭证文件和环境变量（`BYBIT_MAINNET_API_KEY` / `BYBIT_MAINNET_API_SECRET`）。OAuth、API Key 或确认字段都不会开启交易所写入；Mainnet 默认关闭，当前 Bundle 没有 Mainnet 下单能力。凭证和 token 只保存在权限受限的本地文件或 DSH 凭证存储中，绝不会提交到 Git、日志或模型上下文。

## 工作区结构

```text
apps/dsh-plugin/              DSH Host、浏览器 Client、Tools、面板和测试
python/packages/quant-data/  Alembic 数据包、备份和持久命令账本
python/packages/quant-risk/  独立的确定性风险否决基础
python/packages/quant-execution/ 离线 Nautilus 原生执行基础
python/apps/quant-engine/    独立的只读 Testnet 行情服务
packages/ts/                 共享类型和生成的 API Client
sdd/                         Brainstorm、Define、Design 和审计收据
```

手写 TypeScript 使用 strict 模式，单文件不超过 500 行；Python 项目由 uv 管理，Nx 负责工作区编排和任务图。

## 验证

```sh
pnpm install --frozen-lockfile
CI=1 NX_DAEMON=false pnpm run verify
pnpm run python:lint
pnpm run python:typecheck
pnpm run python:test
pnpm run security:deps
pnpm run sbom
gitleaks dir --redact --no-banner
```

验证通过只表示当前代码、测试、SBOM 和扫描收据满足各自范围；它不等价于交易所执行、盈利能力或完整无人值守验收。Testnet 订单在当前实现中不会发送。

## 数据与安全边界

数据库变更通过 Alembic，并在隔离目标上执行备份/恢复测试。新闻、GitHub 代码、README、上传文件和 Agent 输出都视为不可信证据；其中的指令不会改变权限、风险限制或交易环境。生成算法必须走隔离研究与验证路径，不能在 Harness 进程中直接执行。服务包含行情队列、WebSocket 重连、资源和延迟状态检查，并在关闭或不确定状态下保护新暴露。

## 已知限制

独立行情服务支持有界的 Testnet 公共流和进程内重启；OS 级进程恢复、完整市场/账户快照重建、交易所订单对账、Testnet 执行适配器、Mainnet 就绪和完整 AI 研究演化流程仍未验证或未实现。开发和审查请使用 Testnet、Mock 或公开端点，并以 SDD 审计报告中的最新证据为准。
