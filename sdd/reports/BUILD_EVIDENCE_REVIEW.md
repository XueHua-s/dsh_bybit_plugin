# Build Evidence Review

日期：2026-11-17
审查性质：历史快照；本审查形成于后续修复与最终重跑之前。文中的 **NOT READY / Verify Gate 未通过** 是该次只读审查的历史结论，不代表当前命令状态。当前重跑及未完成验收见 [`VERIFY_GATE_2026-11-17.md`](./VERIFY_GATE_2026-11-17.md)。未记录具体时刻，因此不推定时间。
范围：只读/安全验证当前实现；未连接 Bybit Mainnet，未发送任何订单，未修改源码。
依据：`AGENTS.md`、SDD Build/Verify Gate、Define AT-001..AT-009、软件设计哲学检查项。

## 结论

状态：**NOT READY / Verify Gate 未通过**。

已获得的正面证据：

- Nx 能发现 `quant-data`、`quant-engine`、`@bybit-quant/dsh-plugin` 三个独立项目。
- 所有扫描到的手写 TypeScript 文件均不超过 500 行；最长 `apps/dsh-plugin/src/client.ts` 为 494 行。
- 隔离临时 SQLite 的 Alembic upgrade/downgrade 往返成功。
- 备份 checksum 往返、篡改备份拒绝、运行时监控 smoke、Docker 沙箱测试成功。
- pnpm audit、pip-audit、gitleaks 均报告无已知问题/泄露；现有 TS/Python SBOM 可解析为 CycloneDX 1.6。

阻塞或未证实项：

- Define 的 Verify Gate 是 `pnpm run verify`，当前不能通过：构建找不到 `tsdown`，严格 TS 类型检查缺少 `react`/`tsdown` 类型和多个隐式 any，单元测试找不到构建产物。
- Python 全量测试 1 项失败：测试使用的 `python/packages/quant-data/alembic.ini` 缺 `script_location`；通过根配置的独立临时迁移命令可成功。
- Python lint 失败 2 项（`datetime.UTC` 和 import 排序）；根脚本 `python:typecheck` 指向不存在的 `python/src`。
- 运行时仅有内存生命周期计数器；未发现信号处理、持久 checkpoint、重启恢复或可核验的优雅关闭流程。WebSocket 明确 disabled，生产调用方没有 reconnect 事件来源。
- CI 中的 Nx 项目名仍为旧的 `bybit-quant-plugin`/`bybit-quant-python`，与当前发现名不一致；需修正后才能把 CI 作为证据。
- 没有官方 DSH Plugin Manager 在隔离 profile 上 install/upgrade/uninstall 的 receipt。

## 命令证据

| 检查 | 命令 | 退出码 | 证据与限制 |
|---|---|---:|---|
| 工具版本 | `node --version && pnpm --version && uv --version` | 0 | Node v22.20.0、pnpm 12.6.0、uv 0.13.8。 |
| Nx 发现 | `pnpm exec nx show projects` | 0 | 发现三个独立项目。 |
| Nx 图 | `pnpm exec nx graph --print` | 0 | 图可生成；`quant-engine -> quant-data` 仅显示为 implicit edge，插件无依赖边；仍需确认 CI 任务排序是否符合设计。 |
| TS 行数 | `find apps/dsh-plugin/src -name '*.ts' ... wc -l` | 0 | 最大 494 行，低于 500 行上限，但余量仅 6 行。 |
| Build Verify Gate 前置 | `pnpm build` | 1 | Nx 任务日志：`/bin/sh: tsdown: command not found`。 |
| TS lint | `pnpm lint` | 0 | oxlint 通过。 |
| TS 严格类型检查 | `pnpm typecheck` | 1 | 缺少 `react` 和 `tsdown` 类型，且出现多处 implicit any。 |
| 测试类型检查 | `pnpm typecheck:tests` | 1 | 构建产物 `dist/*.js` 不存在并连带产生类型错误。 |
| TS 单测 | `pnpm test:unit` | 1 | `dist/lib/signals.js` 不存在；原因与构建失败相关。 |
| Python 全量测试 | `uv run --project python --locked pytest python` | 1 | quant-engine 2 项通过；migration 测试因 package Alembic 配置缺 `script_location` 失败。 |
| Python lint | `pnpm python:lint` | 1 | Ruff 报 `UP017`（应使用 `datetime.UTC`）及 migration 测试 import 排序。 |
| Python 类型检查（根脚本） | `pnpm python:typecheck` | 4 | 根脚本传入不存在的 `python/src`。 |
| Python 类型检查（实际源码） | `uv run --project python --locked pyright python/apps/quant-engine/src python/packages/quant-data/src` | 0 | 0 errors/warnings；仅证明源码范围检查通过。 |
| JS 依赖审计 | `pnpm audit --audit-level high` | 0 | No known vulnerabilities found。 |
| Python 依赖审计 | `uv run --project python --locked pip-audit --skip-editable` | 0 | No known vulnerabilities found；两个本地 editable 包被跳过。 |
| Secret scan | `gitleaks dir . --redact --report-format json ...` | 0 | 扫描约 6.01 MB，no leaks found。第一次使用已移除的 `--no-git` 参数返回 126，随后用当前 CLI 正确命令重跑成功。 |
| SBOM 结构 | Python 解析 `sbom.cdx.json`、`sbom.python.cdx.json` | 0 | 两者均 CycloneDX 1.6；组件数分别 232、61。仅验证现有文件结构，没有重新覆盖写入仓库 SBOM。 |
| Python SBOM 临时生成 | `uv run ... cyclonedx-py ... --output-file /tmp/bybit-quant-sbom-review.json` | 0 | 临时产物生成成功，62 个组件；未改仓库文件。 |
| Alembic 隔离往返 | `uv run ... python -`，根 `alembic.ini` + TemporaryDirectory SQLite | 0 | upgrade 后有 `alembic_version`、`strategy_versions`、`trade_events`；downgrade 后仅保留 `alembic_version`。未触碰项目数据库。 |
| 备份恢复 | Node strip-types 临时目录调用 `createBackup/restoreBackup` | 0 | 修改源文件后恢复为 `original`，SHA-256 长度 64。 |
| 备份篡改拒绝 | 临时目录篡改 backup 后调用 `restoreBackup` | 0 | 抛出 checksum mismatch，源文件仍为 `safe`。 |
| 运行时监控 | Node strip-types inline smoke | 0 | queue=7、rejected=1、reconnects=1、recovery=1、latency=42；仅验证内存 monitor API。 |
| Docker 沙箱 | `node --experimental-strip-types apps/dsh-plugin/test/sandbox.ts` | 0 | 生成代码看不到宿主文件，网络连接失败且根文件系统不可写；没有覆盖超大 stdout、超时、镜像 digest 固定。 |
| Docker 可用性 | `docker info --format '{{.ServerVersion}}'` | 0 | Docker 29.2.1 可用。 |
| 工作树卫生 | `git diff --check` | 0 | 未发现 whitespace 错误；工作树原已有大量迁移改动，本审查未修改。 |

## 运维能力审查

### Alembic、备份与恢复

临时 SQLite 的 migration upgrade/downgrade 通过，且备份 checksum 和篡改拒绝通过。现有 migration 只覆盖 `trade_events` 与 `strategy_versions`；没有证据证明配置、策略设置、交易历史和完整审计数据的跨版本迁移保留。package-level Alembic 测试配置漂移是实际失败原因。

### Sandbox

容器参数包含 `--network=none`、`--read-only`、内存/CPU/PID 限制、drop capabilities、no-new-privileges、非 root 用户和受限 tmpfs。测试验证了宿主文件隔离、无网络和根文件系统不可写。实现仍会先累计 stdout/stderr 后再截断；未验证 timeout、超大输出、镜像 digest 和 Docker 缺失时的安全结果。

### Monitoring

monitor API 能记录队列、内存/CPU、请求/订单延迟、WebSocket 状态/重连和 recovery counter，inline smoke 通过。Host 当前创建 `websocketEnabled: false`，面板注明 REST polling；没有真实 WebSocket adapter 或 reconnect 事件接线，因此 AT-005 不能判定完成。

### Graceful shutdown / recovery

Python `EngineRuntime` 仅维护内存中的 started/stopped、queue 和 reconnects；没有 signal handler、服务循环、持久 checkpoint、重启恢复或 reconciliation 证据。Host monitor 的 stop disposer 也没有独立运行时测试。该项保持 unverified/failed。

### SBOM、安全与 Mainnet 边界

现有两个 SBOM 可解析，pnpm audit、pip-audit、gitleaks 均为 0；editable Python 包被 pip-audit 跳过，不能等同于完整发布依赖审计。未执行会写回仓库的 SBOM 目标，避免超出本审查范围。全程未访问 Mainnet、未发送订单；本报告没有把本地安全检查升级为交易授权或生产证明。

## 软件设计哲学评分

当前评分：**5/10**（按八项 quick diagnostic，每项约 1.25 分）。

通过项：

1. 多数模块可用一句话描述。
2. 运行时监控、备份、沙箱等边界基本按知识职责拆分。
3. 接口注释包含部分抽象意图和安全不变量。
4. 设计文档与架构审查已讨论复杂度和边界。

失败项及达到 10/10 所需改变：

- 接口是否比实现简单：部分失败；修复构建入口、CI target 和测试入口，减少泄漏到调用方的构建细节。
- 实现能否独立替换：失败；补齐持久化恢复和 WebSocket adapter，并把生命周期 disposer 置于明确 owner。
- 新人能否仅凭边界理解系统：部分失败；补充真实 Nx dependency edges、Python project target 与运行时状态契约。
- 每个模块是否隐藏重要决策：部分失败；将 migration 配置、SBOM 生成路径和恢复策略集中到单一深模块。
- 是否避免配置泄漏/重复知识：失败；统一根脚本与 package 脚本的路径和项目命名，去除 stale CI 名称。
- 是否持续投入结构改进：未通过发布门禁；先修复上述 Verify Gate 红项，再记录新的 ADR/Build evidence。

## 后续修复门槛

1. 修复 `tsdown`/React 依赖与构建产物链路，直到 `pnpm run verify` 返回 0。
2. 修复 package Alembic 配置、Ruff 错误和根 Python typecheck 路径；重跑 `uv run ... pytest python`、lint、typecheck。
3. 为 shutdown/restart、持久 checkpoint、真实 WebSocket reconnect 和完整 backup/restore preservation 增加隔离测试。
4. 修正 CI 使用的 Nx 项目名，并在干净 frozen install 上重跑。
5. 用官方 Plugin Manager 在 disposable profile 取得 install/upgrade/uninstall receipt。
6. 重新运行 Verify Gate、SBOM、依赖审计和 secret scan，并把每条结果追加到新的 Build Report。
