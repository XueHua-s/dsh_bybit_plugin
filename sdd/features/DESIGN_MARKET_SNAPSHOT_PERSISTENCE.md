# DESIGN: Market Snapshot Persistence

## 状态

- Feature: BYBIT_AI_QUANT / market-data vertical slice
- Date: 2026-11-19
- Status: Build in progress
- Architecture source: `/Users/litlesnow/.codex/attachments/886f3b36-5cab-4ba1-bb1c-7ef525af0e6e/pasted-text-1.txt`
- Related design: `sdd/features/DESIGN_BYBIT_AI_QUANT.md`

## 需求与当前 drift

架构书要求独立长运行量化引擎、可恢复的数据层和完整市场数据治理。当前引擎虽然消费 Bybit Testnet ticker，但最新行情只放在进程内存；进程退出后没有可检查的数据来源记录。当前消费者还会用缺字段的 ticker 更新覆盖上一快照中的有效价格。

本切片为每个配置标的保存一个 SQLite 最新快照投影，并提供只读来源查询。它解决重启后的行情来源可审计性，但**不是**行情历史仓库、K 线存储、账户对账或交易执行恢复。旧快照只表示最近一次持久化观察，任何交易就绪判断仍必须依赖本次进程内的健康行情。

## 模块边界

- `quant-data.market_store` 拥有快照 DTO、SQLite upsert/read 和 schema 前置条件。调用方不接触 ORM 表结构。
- `quant_engine.service.MarketWorker` 拥有 ticker delta 合并、实时内存状态和串行持久化。持久化失败会让 worker 失败并进入现有监督恢复，不静默丢弃。
- `quant_engine.api` 的 `/market/{symbol}` 仍只返回本次进程已确认且新鲜的行情；新增 `/market/{symbol}/provenance` 只读返回数据库中的最近快照，并明确 `live_observation`。
- CLI 要求显式传入已存在、已迁移的 SQLite 数据库文件。应用不会自动创建数据库或运行迁移。迁移继续由 `quant_data.migrations` 的备份、候选库校验和原子替换流程执行。

## 生命周期与安全不变量

1. Stream parser 先校验字段和时间戳；价格使用 `Decimal` 保存，避免经由二进制浮点改写行情值。
2. 对 ticker delta，仅新值非空的字段覆盖旧值；事件时间与接收时间始终来自最新事件。
3. 单一消费者按顺序写入有界输入队列对应的最新状态，不创建无界写任务。
4. SQLite 行按 `(environment, symbol)` 唯一键 upsert。该表是可变最新投影，不伪称 append-only 事件历史。
5. 已恢复快照不进入内存实时行情。`/market` 仅在当前进程收到新事件且订阅连接健康时成功。
6. 持久化异常使消费者失败，由现有 supervisor 处理；不会以未落盘状态报告就绪。
7. 本切片只访问公开 Testnet 市场数据，不读取凭证、不访问账户端点、不写交易所。

## 设计取舍与剩余限制

使用 SQLite 最新投影而非把每条高频 ticker 都写入审计表，避免把无限增长的 tick 归档伪装成第一阶段数据库。量化研究需要的 K 线、成交、资金费率和可重放的历史数据仍需独立的分区归档设计（例如 Parquet/DuckDB）；本切片不得用于样本外验证或绩效回放。

数据库由运维显式迁移。服务启动时拒绝缺失或未迁移的数据库，避免自动 DDL 覆盖或意外创建空数据文件。`provenance` 返回的旧行可以用于检查来源，但 `live_observation=false` 时不可被策略或风控当作当前价格。

## Verify Gate

- Alembic 0005 可从 0004 前向迁移，保留先前账本表，且有 SQLite append/update 限制测试只适用于 append-only 表；市场快照按 projection 明确允许更新。
- Data store 测试覆盖精确 Decimal 往返、环境/标的唯一性、upsert 和错误 schema 拒绝。
- Engine 测试覆盖 delta 合并、持久化可读、进程内新鲜行情与历史来源状态分离、存储故障 fail-closed。
- Python Ruff、Pyright、quant-data / quant-engine 定向 pytest、OpenAPI drift 检查通过。
- `git diff --check`、Gitleaks 目录扫描通过；完整 Nx/pnpm Verify Gate 单独记录私有 npm registry 依赖阻塞。

## 软件设计哲学评估

本切片目标 **10/10**。设计审查聚焦八项诊断：单句描述模块职责、接口浅于实现、调用方不依赖 ORM、抽象意图写在接口注释、边界可从模块名识别、每个模块封装重要决策、接口能被新人理解、实现时留出设计改进。任何测试或类型检查不能替代尚缺的历史归档和交易恢复能力；这些属于架构目标的后续 drift。
