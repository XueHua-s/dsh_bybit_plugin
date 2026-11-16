# HANDOFF: BYBIT_AI_QUANT

## Ficha

| Attribute | Value |
|---|---|
| **Feature** | BYBIT_AI_QUANT |
| **Objetivo** | 在安全边界内交付可审计的 Nx/pnpm + Python/uv Bybit 量化骨架，并明确尚未达到生产交易平台的部分。 |
| **Status** | 🔨 进行中；本地 Verify Gate 通过，产品生命周期升级、持久恢复和目标数据库迁移仍未完成。 |
| **Última sessão** | 2026-11-17 |
| **Branch / pasta** | `codex/bybit-ai-quant-sdd` · `/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant` |
| **Artefatos** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` · `sdd/features/DESIGN_BYBIT_AI_QUANT.md` · `sdd/reports/VERIFY_GATE_2026-11-17.md` · `sdd/reports/BUILD_REPORT_BYBIT_AI_QUANT.md` |

## Feito

- 根 `pnpm run verify` 返回 exit 0；当前测试源码检查 `pnpm typecheck:tests` 返回 exit 0。完整收据见 `sdd/reports/VERIFY_GATE_2026-11-17.md`。
- Nx 发现 `quant-data`、`quant-engine`、`@bybit-quant/dsh-plugin`；修正后的网络命令 `pnpm exec nx run @bybit-quant/dsh-plugin:test:network --output-style=static` 返回 exit 0，8 项通过，使用 Testnet 公共行情、只读，无凭证/账户访问/订单，也无 skip。此前同一 CLI 命令的 7 smoke + 27 integration 是错误指向 Mainnet 行情的历史运行，已在 Verify Gate 中标为历史并由 Testnet 运行取代。
- Python lint、typecheck、test 均返回 exit 0；Python 测试为 7 passed。Bybit market-data adapter 的 focused pytest 为 4 passed，最终 adapter 229 行、focused tests 171 行。
- 临时 SQLite Alembic upgrade/downgrade 往返返回 exit 0；只证明隔离数据库可逆，**目标数据库 migration 未应用**。
- TS/Python SBOM、依赖审计、gitleaks、手写源码行数扫描和 `git diff --check` 均有 exit 0 收据；pip-audit 明确跳过两个 editable workspace packages。
- 官方 Harness UI 已验证 install、enable、uninstall、reinstall、re-enable；收据在 `sdd/reports/PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md`。未验证 upgrade，也没有 disposable-profile byte-for-byte state hash。
- OAuth 只读审计：本地 CLI 有 PKCE/state/start/exchange/refresh/select，无 revoke；README 仅描述手动流程。已查官方 Bybit 页面只列出不同 API base，未确认 Testnet OAuth 支持；用户必须审阅 agent/scopes 并手动点击 Authorize。撤销需通过删除 AI subaccount。后续已加入 fake-backed 本地 OAuth 回归（3 scenarios，exit 0），但不访问 provider，不能声称真实 OAuth 已完成或 Testnet OAuth 已获官方确认。
- `OverflowError` oversized JSON integer hardening 的 focused pytest、Pyright、Ruff、format 和 `git diff --check` 均有 exit 0 记录；详见 `sdd/reports/BUILD_REPORT_BYBIT_MARKET_DATA.md`。

## Falta

- 取得 disposable Harness profile 或可执行官方 upgrade 的 Plugin Manager，记录实际 upgrade 和升级前后 state hash；在此之前 Plugin Manager lifecycle 保持 partial。
- 实现并验证 graceful shutdown、持久 checkpoint、重启恢复、reconciliation 和完整 backup/restore preservation；当前完整持久恢复/自动恢复仍 partial。
- 在确认目标环境、备份和回滚/恢复方案后才运行目标数据库 migration；当前只做过临时 SQLite round-trip，目标数据库未应用。
- 完成真实 WebSocket/reconnect 生产接线和独立验证；当前公共行情网络 smoke 不等于生产 WebSocket durability。
- 若要推进真实 Testnet order E2E，先独立核对账户身份、余额、精度、名义额和风险上限；Mainnet 默认关闭，任何真实交易都需明确用户授权。

## Definition of Done

- [x] 当前本地 Verify Gate 和补充安全/依赖/ SBOM 检查有真实 exit 0 收据。
- [x] 公共行情读取和 Python market-data adapter 只在无凭证、无订单边界内验证。
- [ ] Plugin Manager upgrade 与 disposable-profile 状态保留有可审计收据。
- [ ] Bybit 官方确认 Testnet OAuth 支持，并验证真实授权与撤销生命周期；现有 fake-backed tests 只验证本地边界，不证明 provider 支持。
- [ ] 目标数据库 migration 有环境确认、备份、回滚或恢复证据；不得把临时 SQLite 结果写成部署完成。
- [ ] 持久 checkpoint、优雅关闭、重启自动恢复和 reconciliation 完成并通过隔离测试。

## ⛔ Landmines desta feature

- 不把 `pnpm run verify` 的 exit 0 写成完整产品发布通过；升级、持久恢复和目标 migration 仍是未完成项。
- 不把临时 SQLite Alembic up/down 写成目标数据库已迁移；运行迁移前先确认目标数据库与备份。
- 不读取、提交或打印 API key、secret、OAuth token、credentials 文件或 `.env`；不要把公共行情 smoke 当作交易授权。
- 不把本地 OAuth CLI 能力或 README 手册写成 OAuth 已完成/官方 Testnet OAuth 支持；授权前用户必须审阅 agent/scopes 并手动点击 Authorize，撤销路径是删除 AI subaccount。
- 不发送 Mainnet 订单；Testnet 也必须通过账户身份、余额、精度、名义额和风险检查。
- 不手动编辑 Harness 管理的 profile `package.json` 或 `cordis.patch.yml`；优先使用官方 Plugin Manager lifecycle。
- `sdd/reports/BUILD_EVIDENCE_REVIEW.md` 是历史审查快照；其 NOT READY 不能覆盖当前 Verify Gate 收据。

## Casos e testes em aberto

- 修正后的 `pnpm exec nx run @bybit-quant/dsh-plugin:test:network --output-style=static` 当前返回 0，8 checks 通过；覆盖 Testnet 公共行情只读边界，不覆盖账户或订单。此前 7+27 的 Mainnet public market run 仅作历史记录。
- Python adapter focused test 当前 4 passed；Python workspace test 当前 7 passed；需要保持两者与根 TS gate 分开报告。
- Plugin Manager install/enable/uninstall/reinstall/re-enable 已有 receipt；upgrade 和 disposable state hash 未验证。
- 备份 checksum restore、篡改拒绝、内存 monitor 和 Docker sandbox smoke 有历史 exit 0 证据；完整跨版本用户数据保留、重启恢复和自动恢复未证明。
- package-level migration 的目标数据库尚未应用；仅临时 SQLite upgrade/downgrade 通过。
- OAuth fake-backed 本地回归已通过；provider support、真实 consent/revoke lifecycle 和真实授权 grant 仍未验证。

## Eventos

- 2026-11-17 — 将 Verify Gate 报告拆为当前重跑与历史审查；后续 network target 修正后，同一 CLI 命令以 Testnet 公共行情完成 8 checks、exit 0。更早 7+27 次 Mainnet public market run 作为历史保留，产品级未完成项仍标为 partial。
- 2026-11-17 — 修正 market-data build report 的过时行数、测试数和 Gate Green 表述；adapter 229 行、focused pytest 4 passed，并区分 Python adapter gate 与根 TS gate。
- 2026-11-17 — 明确 Plugin Manager upgrade、完整持久恢复/自动恢复和目标数据库 migration 未完成；临时 SQLite 不代表部署。
- 2026-11-17 — 补充 OAuth 只读审计：本地支持 PKCE/state/start/exchange/refresh/select，无 revoke；官方资料未确认 Testnet OAuth；fake-backed 本地回归 3 scenarios 通过，但 provider、consent/revoke lifecycle 仍待验证。

## Recomendações

- 下一次先取得可审计的 Plugin Manager upgrade/profile 状态证据，再扩展持久恢复测试；这样能减少生命周期与数据保护两个独立验收面之间的混淆。
- 保持 Verify Gate、Python adapter gate、网络 smoke 和生产运维验收分栏记录；每条命令保留真实退出码和覆盖边界。
- OAuth 继续保持证据分层：实现能力、provider support、用户 consent、测试和 revoke 生命周期分别记录，避免把 README 或本地命令当作授权完成证明。
- 迁移前生成并校验备份，迁移后读取 schema/version 并准备回滚或 restore 证据；在证据齐全前保持“未应用目标数据库”。

## Veredito

🟡 CONCERNS — local Verify Gate 及补充检查通过；Plugin Manager upgrade、disposable-profile preservation、目标数据库 migration、完整持久恢复/自动恢复、真实生产 WebSocket durability 和 OAuth provider/consent/test lifecycle 未完成。该状态不能发布为 production-ready。

## Setup

1. `cd /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant`，确认 `git status --short --branch` 显示 branch `codex/bybit-ai-quant-sdd`；不要覆盖其他未提交改动。
2. 阅读本文件，然后阅读 `sdd/features/DEFINE_BYBIT_AI_QUANT.md`、`sdd/features/DESIGN_BYBIT_AI_QUANT.md`、`sdd/reports/VERIFY_GATE_2026-11-17.md` 和 `sdd/reports/PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md`。
3. 需要刷新本地 gate 时，运行 `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test`；预期全链为 exit 0。随后再运行 `git diff --check`。

## Tarefas

1. **验证 Plugin Manager upgrade** — Pronto quando: 官方 manager 在 disposable profile 完成 upgrade，并有升级前后 state hash receipt；更新 `sdd/reports/PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md`。
2. **补齐持久恢复闭环** — Pronto quando: graceful shutdown、checkpoint、restart recovery、reconciliation 和 backup/restore preservation 的隔离测试与真实命令均有收据；更新 Verify Gate/Build Report。
3. **确认并应用目标 migration（若获授权）** — 先核实目标数据库身份、备份 checksum 和 rollback/restore 计划；仓库 `pnpm db:upgrade` 现在要求显式传入 SQLite 文件路径，并先备份/验证、在候选副本迁移后原子替换。只有目标明确且获授权后才执行，再记录 revision、schema 读取及恢复证据。在此之前保持“未应用目标数据库”。
4. **完成发布前检查** — Pronto quando: 运行 `/sdd-release` 要求的检查，审查 `git diff`、敏感文件、测试和 SBOM；未获明确授权不提交、不推送。

## Ship

- **Publicar:** 完成上述未完成验收后，按 `.agents/skills/sdd-release/SKILL.md` 执行发布检查；当前不提交、不推送。
- **Limpar:** 本次文档工作不删除 worktree、分支或历史报告；仅在用户明确要求并确认后归档或清理。

---

## Prompt de retomada

```text
Retomar a feature BYBIT_AI_QUANT.

Contexto: /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant está na branch codex/bybit-ai-quant-sdd. O root `pnpm run verify`, `pnpm typecheck:tests`, Python lint/typecheck/test, isolated Alembic round-trip, SBOM, dependency audit, gitleaks, line scan e `git diff --check` têm receipts exit 0 no Verify Gate de 2026-11-17. O produto ainda está PARTIAL: Plugin Manager upgrade/disposable-profile state hash, durable restart recovery, production WebSocket durability e target database migration não foram verificados; a target database migration não foi aplicada. OAuth tem fake-backed local regressions, mas Bybit não foi contatado, suporte oficial a Testnet OAuth não foi confirmado, e o CLI não implementa revoke.

Leia primeiro: /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant/sdd/handoffs/HANDOFF_BYBIT_AI_QUANT.md; depois /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant/sdd/features/DEFINE_BYBIT_AI_QUANT.md, DESIGN_BYBIT_AI_QUANT.md, sdd/reports/VERIFY_GATE_2026-11-17.md e sdd/reports/PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md.

Próxima ação: rode `cd /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant && git status --short --branch && pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test`; preserve each real exit code, then inspect the Plugin Manager upgrade path.

Não faça: não envie ordens, não habilite Mainnet, não leia/imprima credenciais, não aplique migration a nenhum target database sem confirmar ambiente e backup, não edite Harness-managed package.json/cordis.patch.yml, não remova históricos. Não trate os testes fake-backed ou os comandos locais como prova de OAuth real ou suporte oficial Testnet; antes de qualquer consent, o usuário deve rever agent/scopes e clicar Authorize manualmente. Não há revoke CLI; a revogação documentada é excluir o AI subaccount.

Landmines: `pnpm run verify` exit 0 is only a local gate; temporary SQLite up/down is not deployment; BUILD_EVIDENCE_REVIEW.md is historical; Plugin Manager install/reinstall does not prove upgrade; full durable recovery remains partial.

Ao terminar, atualize os relatórios com comandos reais, exits e limites; execute `/sdd-release` antes de qualquer publicação, e não commit/push sem autorização explícita.
```

## Histórico de slices

### Verify Gate e handoff documental — 2026-11-17

- Reconciliou o relatório Verify Gate: current rerun separado do histórico, `pnpm run verify=0`, `pnpm typecheck:tests=0`, corrected Testnet network smoke=0 (8 checks; read-only/no credentials/orders), Python lint/typecheck/test=0 (7 passed), Alembic temporário up/down=0 e SBOM/deps/gitleaks/line/diff=0. O network run anterior 7+27 via Mainnet está identificado somente como histórico.
- Atualizou o relatório do adapter para 229/171 linhas, focused pytest 4 passed e hardening `OverflowError` com comandos exit 0; separou Python adapter gate do root TS gate.
- Marcou `BUILD_EVIDENCE_REVIEW.md` como revisão histórica e registrou lifecycle upgrade, target migration e full recovery como pendências.
