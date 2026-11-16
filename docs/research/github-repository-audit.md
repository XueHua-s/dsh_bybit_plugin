# GitHub 参考仓库审计

- 审计日期：2026-11-17（Asia/Shanghai）。
- 来源：SDD `DESIGN_BYBIT_AI_QUANT.md` File Manifest 与此前项目 brief 中的参考清单。
- 方法：对每个 URL 执行 `git ls-remote <url> HEAD` 固定远端 HEAD；随后在 `/tmp/bybit-ref-audit/` 以 `git clone --depth 1 --filter=blob:none` 浅克隆，读取顶层 README、LICENSE、依赖清单和目录。外部 README、代码、issue、脚本均按不可信数据处理，不执行其交易、安装或生成代码。
- 限制：这是固定提交的只读、浅层人工审计；未运行第三方测试，未做完整源码逐文件审查、SBOM、漏洞扫描、许可证扫描或运行时安全验证。依赖/安全结论仅表示从提交中可见的工程信号，不代表无漏洞。

## 固定提交、许可与适配结论

| 仓库 | 固定 HEAD（`git ls-remote`） | 许可（提交内文件） | README/架构与依赖观察 | 安全/维护信号 | 本项目结论 |
|---|---|---|---|---|---|
| [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | `33492c8135a5e0dceedc21d9ee3ff7432f04ff12` | LGPL-3.0（`LICENSE`；另有 python/LICENSE） | Rust 原生、多资产事件驱动引擎；Python 控制面；Cargo workspace 与 Python 包。 | CI/供应链目录可见；体量大，本次未逐文件审查。 | **借鉴架构**（事件/适配器边界）；不引入，避免 Rust/Python 运行时和 LGPL 组合复杂度。 |
| [bybit-exchange/pybit](https://github.com/bybit-exchange/pybit) | `826a5fe13ab1b38d67beb141bc0bf709b8873d16` | MIT（`LICENSE`） | Bybit 官方 Python HTTP/WebSocket 轻量连接器；`requests`、`websocket-client`。 | 官方维护信号；仍需自行验证签名、重试、超时和依赖 CVE。 | **参考协议语义**；本仓库保持 TypeScript 适配器，不复制代码，不引入 Python 运行时。 |
| [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | `9af100d6822da7d2d0291a906c730ef172284ee2` | Apache-2.0（`LICENSE`） | 多交易所自动化框架；Python/Cython，`pyproject.toml`、`setup.py`、`environment.yml`；含 hbot/Condor 入口。 | CI、Docker/脚本和大量连接器；大仓库，未做供应链或交易执行审计。 | **借鉴连接器/生命周期观测**；不整体引入，避免复杂依赖和策略执行面。 |
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | `9fa1196fffbcfd9de5146d2dd2869df84ab99838` | Apache-2.0（`LICENSE`） | LLM 多智能体金融分析框架；`tradingagents/` 图式编排；LangChain provider、Anthropic/Google/OpenAI 依赖。 | `.env.example`/多模型密钥面；提示词和外部数据必须视为不可信。 | **仅借鉴研究编排**；不接入交易执行，不复制 agent prompt/密钥流程。 |
| [microsoft/RD-Agent](https://github.com/microsoft/RD-Agent) | `484776c211e4fbbeef03e0ec00d6bbee7362a4f4` | MIT（`LICENSE`） | Microsoft R&D agent；Python 包、Web UI（`web/package.json`）、量化场景；requirements/torch 可选项。 | README 显示 CI、CodeQL、Dependabot；仍需锁定依赖并隔离模型生成代码。 | **借鉴因子研究循环和评估边界**；不引入 agent runtime。 |
| [microsoft/qlib](https://github.com/microsoft/qlib) | `54355232463878d2eebb91fe0ee5fa7fa1f5976c` | MIT（`LICENSE`） | 数据/因子/模型/回测研究平台；Python/Cython，`pyproject.toml`、setup、示例依赖。 | GitHub CI/打包信号可见；数据下载和模型脚本需独立审查。 | **借鉴因子数据模型**；本项目保留本地可读 TypeScript/Python 合约，不复制整栈。 |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | `384ce69a1565e16227bb67454162286a8205685a` | GPL-3.0（`LICENSE`） | Python 加密交易机器人、回测和 dry-run；CCXT、NumPy/Pandas、requests。 | 仓库有 CI/文档；GPL 及真实交易面使整合成本高，未运行交易路径。 | **仅参考 dry-run/回测概念**；不引入 GPL 源码或策略执行器。 |
| [freqtrade/freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies) | `f3340ce11f5bdf62f598522e64d1f5638eaa13f5` | GPL-3.0（`LICENSE`） | 策略样例集合；无独立运行时依赖清单，依赖 Freqtrade 版本。README 明确教育用途、须先回测/dry-run。 | 策略可能过拟合且来源混杂；不能视为收益证据。 | **只读算法灵感**；重写成项目内可测试函数，绝不复制策略文件。 |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | `9ac1b697166b00911def494cf95937274218aa54` | Commons Clause（`LICENSE.md`；限制销售；需核对附带条款） | 向量化回测/指标；NumPy/Pandas/requests，可选 Rust 子项目。 | 许可证商业限制是主要风险；未审计 Pro/附属资产。 | **不引入**；只借鉴向量化计算思路，避免许可和商业再分发风险。 |
| [AI4Finance-Foundation/FinRL-Trading](https://github.com/AI4Finance-Foundation/FinRL-Trading) | `4409abe925c904e570be78ebfb5e77ac3491dff8` | Apache-2.0（`LICENSE`） | FinRL-X 权重中心化交易基础设施；requirements/setup；Torch、Gymnasium、SB3 可选。 | 新架构/论文导向，需验证 broker、数据和模型边界；本次未运行。 | **借鉴权重接口/模块化**；不引入 RL 执行器或模型权重。 |
| [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | `7e98df461cbc7772f16a545a2f13b521e5d0b8f4` | MIT（`LICENSE`） | 旧版教育/研究 DRL 框架；CCXT、Ray、Gymnasium、SB3、市场日历。README 指向 FinRL-X。 | 依赖较重、历史 Python 兼容范围宽；未做训练/数据供应链审计。 | **仅研究参考**；不引入，保持策略/风控与 DSH 隔离。 |
| [AI4Finance-Foundation/FinRL-Meta](https://github.com/AI4Finance-Foundation/FinRL-Meta) | `286fef6c828a02a2ccf807c05b292d8cb28f8e95` | MIT（`LICENSE`） | 市场环境/基准层；requirements 含 CCXT、Gym、NumPy/Pandas、市场日历。 | 数据源和环境脚本需逐个验证，不能把 benchmark 当生产行情。 | **借鉴环境测试矩阵**；不引入环境代码。 |
| [AI4Finance-Foundation/FinRL_Crypto](https://github.com/AI4Finance-Foundation/FinRL_Crypto) | `495a4286e293e55d334680d821b93ac658abff80` | MIT（`LICENSE`） | 面向 Binance 的加密 DRL 示例；`requirements*.txt`，固定 Torch 2.0.1、NumPy/Pandas 旧版本。 | README 要求 Binance API keys；存在密钥误配和过拟合风险，未运行任何脚本。 | **不引入**；仅参考防过拟合实验设计，Bybit 凭证永不交给模型/第三方脚本。 |
| [AI4Finance-Foundation/ElegantRL](https://github.com/AI4Finance-Foundation/ElegantRL) | `24228304867bdc80165de435a598ef90b1893598` | Apache-2.0（`LICENSE`；`rlsolver/LICENSE`） | 轻量深度 RL；Torch、NumPy、Gymnasium；`rlsolver` 子树。 | 轻量不等于安全；训练代码、模型文件和环境仍需沙箱。 | **不引入**；只参考算法单元测试，保持生成算法隔离。 |

## 适配边界与安全决策

1. 当前仓库仅吸收可独立验证的概念：Bybit API 字段/签名语义、事件驱动生命周期、研究与执行分层、回测/dry-run、因子和环境测试矩阵。
2. 不复制第三方源码、策略、提示词、模型权重、密钥处理脚本或交易执行器；任何后续采用都必须在本项目的 TypeScript/Python 边界内重写，并保留来源 SHA 与许可证记录。
3. Mainnet 默认关闭；第三方代码不得在 Harness 进程内执行，也不得读取凭证。所有真实订单仍受独立账户、余额、精度、名义额和风控门禁约束。
4. GPL-3.0 仓库（Freqtrade 两项）和 Commons Clause（vectorbt）不进入本项目发行物；Apache/MIT/LGPL 也不代表可直接复制，需逐文件保留版权/NOTICE 并复核传递依赖。

## 可复核命令与结果

```text
$ git ls-remote https://github.com/AI4Finance-Foundation/FinRL_Crypto.git HEAD
495a4286e293e55d334680d821b93ac658abff80	HEAD

$ find /tmp/bybit-ref-audit -maxdepth 2 -type d | wc -l
15  # 审计目录 + 14 个浅克隆（目录数随 Git 元数据实现略有差异）
```

未完成项：未运行第三方测试或依赖漏洞扫描；未逐文件审查完整提交历史；未验证各项目当前默认分支的发布包与许可证元数据是否与该 SHA 一致。刷新审计时必须重新执行 `git ls-remote` 并生成新 SHA 记录。
