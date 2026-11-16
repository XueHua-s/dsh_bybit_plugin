# Bybit AI Quant

Bybit AI Quant 是运行在 DeepSeek Harness（DSH）中的 TypeScript Host/Client Bundle。仓库采用 Nx + pnpm Monorepo；Python uv 工作区包含 `quant-data` 数据包和 `quant-engine` 应用骨架。当前插件提供 Bybit REST 行情、确定性指标和单资产多头回测、本地模拟盘、交易对观察列表、带代码侧风控门的 AI 决策账本，以及只读 Web 面板。

仓库仍处于开发阶段。SDD 目标中的完整自主量化平台尚未完成：WebSocket 行情接入与重连接线、长期运行的引擎编排、官方 Plugin Manager 生命周期回执和生产就绪性都没有得到完整验证。当前只启用 REST 轮询。

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
- `bybit_trade`：只有全部安全检查通过后才会预览或发送订单。

回测不包含杠杆、资金费，也不保证盈利。

## 交易安全边界

Bundle 默认配置为 `env: testnet`、`allowLiveTrading: false`、`allowTestnetTrading: true`，单笔名义额上限为 24 USDT。Mainnet 默认关闭。真实订单还必须同时满足凭证、环境开关、`confirm: "LIVE"` 和 `dryRun: false`，并通过账户身份、余额、交易规则、名义额和风控检查。主账户凭证还需要额外的 `allowMainAccount` 开关。Testnet 授权不等于 Mainnet 授权。

面板只读，不发送订单。它通过已认证的 DSH bridge 使用 REST 轮询，不会新增未认证路由。

## Testnet OAuth

内置 PKCE 客户端只访问 Bybit Testnet OAuth。请在仓库根目录运行：

```sh
pnpm --filter @bybit-quant/dsh-plugin oauth -- start
pnpm --filter @bybit-quant/dsh-plugin oauth -- exchange
pnpm --filter @bybit-quant/dsh-plugin oauth -- accounts
pnpm --filter @bybit-quant/dsh-plugin oauth -- select <sub_member_id>
```

查看账户列表后，明确选择目标 AI 子账户；客户端不会自动选择或创建账户。Token 以受限权限写入本地，不会打印到日志。此流程不支持 Mainnet OAuth。

## 工作区结构

```text
apps/dsh-plugin/          DSH Host、浏览器客户端、工具、脚本和测试
python/packages/quant-data/  Alembic 数据包
python/apps/quant-engine/   Python 引擎骨架
sdd/                      Brainstorm、Define、Design 和验证报告
```

`dist/` 是生成产物，也是插件唯一打包内容。手写 TypeScript 使用 strict，并保持每个文件不超过 500 行。Python 项目由 uv 管理；Nx 会发现 `@bybit-quant/dsh-plugin`、`quant-data` 和 `quant-engine` 三个独立项目。

## 开发与验证

```sh
pnpm install --frozen-lockfile
pnpm build
pnpm lint
pnpm typecheck
pnpm test:unit
pnpm bundle:check
pnpm python:lint
pnpm python:typecheck
pnpm python:test
pnpm run security:deps
pnpm run sbom
```

根目录没有 `pnpm test:network` 脚本；公开端点 smoke 使用 `pnpm exec nx run @bybit-quant/dsh-plugin:test:network`。它只访问公开/demo 端点，不发送 Mainnet 订单，网络不可用时可能跳过。发布 Verify Gate 是 `pnpm run verify`；文档或 CI 通过不等于已经取得官方 Plugin Manager 生命周期回执。

## 状态与凭证

模拟盘状态和账本默认位于 `$DSH_HOME/bybit-quant/state.json`。API 凭证来自 DSH credential store、文档规定的环境变量或权限受限的本地文件；不得提交、记录或写入 Bundle patch。Python Alembic schema 与备份工具属于开发组件，连接持久化环境前必须确认环境并制定备份方案。

## 限制

当前版本不声称具备 WebSocket 流式行情、自动重连/恢复、生产级长期运行 Python 服务、自主投资能力或 Mainnet 就绪性。开发和审查请使用 Testnet、Mock 或公开端点，并以 SDD 证据为准。
