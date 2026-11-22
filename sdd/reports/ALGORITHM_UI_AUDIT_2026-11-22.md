# 算法落地与 AI 决策界面审计

## 结论

当前实现包含两条边界不同的模拟路径。Bybit 研究路径从公开 Instrument Info 与 ticker 快照发现动态候选，AI 从新鲜候选中选择零到四个标的或观望，并只把决策写入本地模拟账本。`internal_paper` 路径使用 Python 服务内置的合成 fixture 候选与策略证据；AI 选择 fixture 标的及证据，随后 Python selector、组合规划、独立风控和 Nautilus synthetic OMS 产生持久模拟回执。后者不使用 Bybit 实时报价或交易凭证。面板的币种、市场和 K 线周期字段只改变展示数据，不会进入后台 AI 决策输入。

这仍不是架构书要求的完整无人值守交易系统。Bybit provider 仍是 Testnet/linear 的只读 GET，未实现 Nautilus Bybit 原生下单、撤单、持久订单 ID 的交易所对账、跨重启未决订单恢复或可审计的真实账户循环。Mainnet 默认关闭；本轮没有发送 Testnet 或 Mainnet 订单。

## 算法落地范围

| 来源/能力 | 当前状态 | 证据与边界 |
|---|---|---|
| SMA/EMA 交叉、Donchian、ADX 趋势、时序动量 | 已在 `python/packages/quant-strategies` 独立重写 | 纯函数输出有界 target exposure；没有账户、凭证或订单权限 |
| Bollinger、Z-score、RSI 均值回归、ATR breakout、funding carry | 已在同一策略包实现 | 需要规范化 OHLCV/资金费率快照；元数据仍是 `research`/`not_started` |
| Qlib Alpha158 | 仅独立重写 5 个公式子集（ROC、MA、STD、RSV、SUMP） | 没有引入 Qlib runtime、完整因子库、训练或数据层 |
| regime + strategy selector | 已实现研究边界 | 只比较已有候选策略；要求 `APPROVED` + `PAPER_PASSED` 证据、OOS 样本、成本、冷却和 hysteresis；当前 DSH→Python 的进程回归使用内置合成 fixture 证据，不证明这些策略已由真实 Bybit 行情验证，也不证明收益 |
| TradingAgents、RD-Agent、FreqAI、VectorBT、FinRL、ElegantRL、Hummingbot | 未整体集成 | `docs/research/github-repository-audit.md` 记录了版本、许可证和采用/拒绝理由；只吸收概念，未执行第三方生成代码 |
| NautilusTrader | 仅内部 paper/native 基础设施 | 未接通 Bybit Testnet live execution；不能据此宣称真实交易已由 Nautilus 独占 |

因此，架构书提到的 GitHub 算法库**没有完整落地为生产策略运行时**；已经落地的是经过隔离、独立测试的本地策略子集和 selector 研究边界。

## AI 决策与 UI 边界

- Bybit 研究路径候选池为空时会执行动态发现；配置 allow-list 只能缩小候选集合，不会把 BTC/ETH 作为静态 fallback。图表候选建议仅在该 Bybit 池新鲜时显示。
- Testnet 环境下的后台 Agent 仍然只把决策写入本地模拟账本。`internal_paper` 使用另一份 Python-owned 合成 fixture 候选池；其 `quant_decide_background` 绑定当前 cycle ID、fixture 候选、策略证据摘要和目标敞口，再由服务端风控处理。没有回执不能解释为“AI 观望”。
- 任一路径的发现失败、过期或候选为空时都 fail closed；internal-paper 的真实回执只证明合成 fixture 上的本地持久状态与 native OMS 结果。
- 面板的 `图表币种`、`图表市场`、`图表 K 线周期` 明确标为“行情查看（仅展示）”；它们不改变候选池、AI 决策日志或模拟组合。
- 面板不提供真实下单、撤单、平仓或后台实盘开关；运行边界显示 Testnet 写入不可用、账户/对账/恢复状态未知或未就绪。

## 无人值守验收状态

| 能力 | 状态 |
|---|---|
| 默认关闭、Testnet/internal-paper 环境门禁、单 Agent、超时、退避、清理 | 已验证 |
| Bybit 动态候选发现、AI 选择或观望、Testnet 环境本地模拟账本回执 | 已验证；不是交易所订单 |
| 内部 paper Python selector→portfolio→risk→native OMS→持久回执 | 已验证；fixture-owned、credential-free |
| 独立运行与正常关闭/受保护重启 | 已验证于 synthetic process harness |
| Testnet 原生下单/撤单、订单状态查询、成交/持仓/余额对账 | 未实现或未验证 |
| 跨进程 durable scheduler lease、未决循环恢复、独立模型质量评估 | 未完成 |
| Mainnet | 默认关闭；真实交易仍需独立、明确授权，当前不开放 |

## 本轮验证收据（2026-11-22）

| 命令 | 结果 |
|---|---|
| `CI=1 NX_DAEMON=false pnpm run verify` | exit 0 |
| `pnpm run python:lint` | exit 0 |
| `pnpm run python:typecheck` | exit 0，0 errors/warnings/informations |
| `pnpm run python:test` | exit 0，500 passed，11 warnings |
| `pnpm --dir apps/dsh-plugin run verify` | exit 0；构建、lint、strict typecheck、unit、Bundle check 通过 |
| `pnpm --dir apps/dsh-plugin run bundle:lifecycle` | exit 0；isolated install→upgrade→remove，statePreserved=true，exchangeRequests=0 |
| `pnpm --dir apps/dsh-plugin run test:paper-process` | exit 0；native fill、risk reject、503 uncertainty、protected restart、reap/listener close 通过 |
| `pnpm run security:deps` | exit 0；无已知高危依赖 |
| `pnpm run sbom` / `pnpm exec nx run quant-data:sbom` | exit 0 |
| `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | exit 0；未发现泄露 |
| `pnpm exec nx show projects` | exit 0；发现 9 个 Nx 项目 |
| `git diff --check` | exit 0 |

## 当前产品标记

**INCOMPLETE / PARTIAL**。本次审计没有扩大交易权限，也没有把研究算法、OAuth 登录或正常行情误报为真实执行就绪。要达到架构书的无人值守交易验收，必须先补齐 Testnet Nautilus execution client、独立风险 admission、持久 order/reconciliation/recovery、scheduler lease 和模型质量评估，并为每项补充可执行 Verify Gate 收据。
