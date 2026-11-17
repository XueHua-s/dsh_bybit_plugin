# HANDOFF: BYBIT_AI_QUANT

## Ficha

| Attribute | Value |
|---|---|
| Feature | BYBIT_AI_QUANT |
| Objetivo | 完成原始架构全部 MUST；分阶段交付可审计能力，不以量化骨架替代完整产品。 |
| Status | 进行中 / PARTIAL：独立只读 Testnet 服务已通过独立 review；完整量化、执行、AI 和研究平台未完成。 |
| Última sessão | 2026-11-17 |
| Branch / pasta | `codex/bybit-ai-quant-sdd` · `/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant` |
| Artefatos | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` · `sdd/features/DESIGN_BYBIT_AI_QUANT.md` · `sdd/reports/VERIFY_GATE_2026-11-17.md` · `sdd/reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md` |

## Feito

- 真正 Nx + pnpm / uv 工作区：`@bybit-quant/dsh-plugin`、`@bybit-quant/quant-contracts`、`quant-engine`、`quant-data`，有 plugin → contracts / engine → data 实际依赖边。
- DSH Host/Client 提供 REST 行情、指标/多头回测、watchlist、paper book、AI 决策账本与代码风控门。面板仍走 REST，尚未连接 Python 服务。
- Python 有公共 Testnet WebSocket adapter、有界队列、持续 consumer、有限重启的进程内 supervisor，以及独立 FastAPI/uvicorn CLI。只读 `/api/v1/health`、`/api/v1/market/{symbol}`，loopback only，无凭证/账户/订单 API。Python 生成 OpenAPI，导出不启动生命周期。
- supervisor、transport、engine-service 三份独立 ACCEPT 在 `sdd/reviews/REVIEW_ENGINE_{SUPERVISOR,TRANSPORT,SERVICE}_2026-11-17.md`。ACCEPT 仅针对这些切片，不是完整原始架构验收。
- runtime checkpoint v2 仅保留 reconnect count；队列、started/stopped 时间戳是进程状态。TS checksum backup/restore、临时 SIGKILL 重开、SQLite integrity/migration 保护有隔离收据。目标数据库 migration **未应用**。
- 最新根 TS gate：`NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` 与同前缀 `pnpm typecheck:tests` exit 0；执行需允许 mock OAuth 的本地 loopback callback。Python lint/format（21 files）、typecheck（0 errors）、test（111 passed）及 schema/diff check 均 exit 0。最初 test-only Task|None narrowing 失败已修正后全量重跑。
- TS/Python SBOM 已重新生成 exit 0；TS 241 / Python 78 components；`security:deps` exit 0，无已知漏洞，pip-audit 跳过两个 editable workspace 包。完整命令/限制见 Verify Gate。
- 已有官方 install/enable/uninstall/reinstall/re-enable 收据；upgrade 与 disposable-profile state hash 未验证。OAuth fake-backed 本地测试通过；Bybit Testnet OAuth 官方支持、真实 consent/revoke 未验证，无 revoke CLI。

- 根代理带日志公共 Testnet smoke：health 200 / ready=true / connected，执行 unknown；SIGTERM 后按序完成 shutdown/lifespan 日志、listener 关闭，probe exit 0。uvicorn 关闭后重发 SIGTERM，child -15 符合实现，不能单凭该码认定失败。

## Falta

- 生成 TypeScript SDK 并接入 DSH；当前 `quant-api-client` 是设计计划，未实现。独立服务只解决公共行情读取，尚无认证远程 API/控制、完整 snapshot 重建、持久化/来源、OTel 和完整恢复。
- 保留原始 MUST（DEFINE AT-010–031）：Nautilus 唯一执行权、完整策略/特征/regime/portfolio/risk、AI 团队、隔离研究和受控演化。当前 TS 直接 REST create/cancel 路径是 DRIFT-ORIGINAL-003，不能视为已获批准替代方案；引入真实订单前必须消除双重执行权。
- OS 进程监督、订单恢复、exchange reconciliation、持续 Testnet soak 和跨版本状态保留；行情 ready 不等于账户/执行 ready。订单延迟、拒单、对账是 unknown/null。
- Plugin Manager upgrade + disposable-profile 状态哈希、OAuth provider/真实授权撤销验证；确认目标数据库和备份恢复方案后才可迁移。

## Definition of Done

- [x] 当前独立只读服务、wire hardening 与 supervisor 切片有独立 ACCEPT。
- [x] 原始范围恢复为 MUST，未完成项有 traceability；不声称完整产品或生产就绪。
- [ ] 最新完整工作树根 TS/Python、安全、schema、diff 等发布前 gate 全部有可审计收据。
- [ ] 原始架构 AT-010–031 全部完成并验证，包括唯一执行权及量化/AI/研究闭环。
- [ ] 官方 upgrade/state preservation、真实 OAuth 生命周期及目标环境迁移均有独立证据。

## Landmines

- 不读取、打印、提交凭证或 `.env`；不手改 Harness 管理的 profile 文件。
- Mainnet 默认关闭，任何真实交易都需独立明确授权；Testnet 仍执行身份、余额、精度、名义额和风控。
- 临时 SQLite 不代表目标迁移；fixture/local gate 不代表 provider OAuth 或生产运维。
- 历史 `BUILD_EVIDENCE_REVIEW.md` 和旧测试计数不能覆盖当前收据。旧 7+27 Mainnet public network run 是历史；修正后 Testnet public smoke 是 8 checks，无凭证/账户/订单。

## Eventos

- 2026-11-17 — 从根应用迁移为四个真实工作区项目；过时的“root monorepo 缺失”描述改为历史。
- 2026-11-17 — network target 改为公共 Testnet；历史 Mainnet public-only 结果保留在 Verify Gate。
- 2026-11-17 — checkpoint、migration protection、backup restore、trust envelope、bounded sandbox output 与 supervisor review fixes 陆续有真实命令收据；旧 7/15/21/26 测试数仅属于对应历史切片。
- 2026-11-17 — 原始范围审计纠正无依据的 SHOULD/COULD 降级，恢复完整 MUST，不将平台目标缩小为骨架。
- 2026-11-17 — 独立服务落地，adapter/supervisor/service 三份 review ACCEPT；生成 TS SDK/DSH integration 及完整执行/量化/AI/研究仍 open。
- 2026-11-17 — 用户已授权 feature branch commit/push；此前 handoff 的笼统“当前不提交、不推送”不构成额外限制。仍必须执行 sdd-release 检查，不声称尚未发生的 Git 动作。

## Setup

```sh
cd /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant
pnpm install --frozen-lockfile
uv sync --project python --locked
uv run --project python --locked quant-engine --symbols BTCUSDT ETHUSDT
```

运行手册：`docs/runbooks/engine-service.md`。只绑定 `127.0.0.1:8765`，明确选择 symbols；不暴露未认证代理。

## Tarefas

1. 最终发布前重审工作树与文档后的 diff/secret gate；当前根 TS/Python/schema 与带日志进程关闭 smoke 已通过。检查 `git status --short --branch`，保留其他所有者改动。
2. 依照原始范围审计和 DEFINE 的依赖顺序推进 SDK/DSH 接线、Nautilus authority 和量化/AI/研究能力；实现新切片前更新设计 manifest，独立 review 后再整合。
3. 发布前执行 `.agents/skills/sdd-release/SKILL.md`；用户已授权 feature branch commit/push，完成检查后由根代理操作。无 `--force`，不合并主分支或声称已部署。

## Ship

本文件更新时尚未由文档集成者提交/推送。Git 实际结果由根代理最后写入；不删除 worktree、分支或历史报告。

## Prompt de retomada

```text
继续 BYBIT_AI_QUANT，目录 /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant，branch codex/bybit-ai-quant-sdd。
先读 sdd/handoffs/HANDOFF_BYBIT_AI_QUANT.md、AGENTS.md、DEFINE/DESIGN_BYBIT_AI_QUANT.md、sdd/reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md 和 VERIFY_GATE_2026-11-17.md。
四个 Nx 项目及实际依赖已存在。Python 独立只读 Testnet FastAPI 服务与真实 consumer、adapter、supervisor 已获三份 scoped ACCEPT；DSH 仍 REST，生成 TS SDK/DSH 连接未实现。完整原始 MUST、Nautilus 唯一执行权、策略/portfolio/risk/AI/research 均未完成，不能将产品降为 scaffold。现有 TS 直接 REST order 是 open drift。
运行 git status --short --branch 确认现场；刷新 NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify，再以同前缀 pnpm typecheck:tests，及 pnpm python:lint、pnpm python:typecheck、pnpm python:test；逐项记录实际退出码，不能沿用旧测试计数。mock OAuth 需 loopback 权限，网络/沙箱失败如实记录。检查 OpenAPI schema drift、SBOM/audit/secret/diff。
服务启动命令：uv run --project python --locked quant-engine --symbols BTCUSDT ETHUSDT；默认 loopback 8765，/api/v1/health 和 /api/v1/market/{symbol} 只读，无私有 API/订单。ready 仅行情，执行/对账 unknown。按 docs/runbooks/engine-service.md 核实 SIGTERM 的有序日志和 listener 关闭；uvicorn 会在优雅关闭后重发 SIGTERM，-15 本身不能判断成功或失败。
禁止读取/打印凭证，禁止 Mainnet 或未经明确授权的真实订单；Testnet 保留所有账户与风控检查。目标 DB 未迁移，临时 SQLite 不是部署。官方 upgrade/state hash、OAuth provider/真实授权撤销尚未验证。
用户已授权 feature branch commit/push；先执行 sdd-release 真实检查，再由根集成者提交/推送并记录真实 SHA/remote 结果，不使用 force，不把 push 声称为生产部署。
```

## Histórico de slices

2026-11-17 — 先后完成 migration/backup、runtime checkpoint、Nx unit coverage、bounded sandbox、trust envelope、supervisor hardening；原命令和旧计数保留在 BUILD_REPORT/VERIFY_GATE，各切片本地通过不代表完整平台。
2026-11-17 — 最新整合独立只读服务与三份 review，恢复原始完整 MUST，待根集成者完成最终工作树收据和 Git 结果。
