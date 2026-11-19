# DSH Bybit 量化插件 UX 审查

日期：2026-11-19
范围：当前运行的 DeepSeek Harness 插件详情页、配置说明、工具清单和本地实现；只读审查，未修改设置、账户或交易状态。

## 观察到的界面

当前 DSH 插件详情页显示版本 `1.4.5`，默认环境为 `testnet`，`allowLiveTrading=false`，并同时列出行情、回测、模拟盘、AI 决策和实盘订单工具。Quick start 使用自然语言示例引导用户调用这些工具。Safety 部分说明面板只读、交易有多重开关和名义额上限；Limitations 部分说明 REST 轮询、无 WebSocket、纸面 AI 账本以及签名账户/订单接口未在 Bundle 测试中执行。

配置表把 `env=live` 标为 real money，并把 `allowLiveTrading` 描述为实盘主开关；但凭证行仍显示通用的 `BYBIT_API_KEY/BYBIT_API_SECRET`，没有在当前已安装详情页中显式展示 Mainnet 专用变量和 `live/` 凭证目录。源码与新文档已经采用 Mainnet 专用变量和隔离目录，说明活动 Harness 详情页与当前工作树存在版本漂移。

## 判断

界面对于已实现的研究和 Testnet/纸面功能基本可理解，但不能被视为“无人值守 AI 量化操盘”入口。界面说明的是会话触发工具链；没有持续后台调度器、进程重启后的策略恢复、完整订单/持仓对账或逐笔 Mainnet 确认卡。当前实现还保留 Host 侧直接 REST 交易工具，Python/Nautilus 尚未成为唯一执行权威。

“AI loop”标题和“出一份简报然后你自己决定”的示例容易让用户误解为模型会持续运行；Limitations 中关于纸面账本和未验证签名接口的说明能降低风险，但位置较后，不能替代顶部的运行状态卡。活动 UI 也没有显示后台循环、账户就绪、对账状态或执行权威，因此用户无法从面板判断“连接成功”是否等于“可安全交易”。

## 风险与具体修正建议

| 编号 | 优先级 | 发现 | 建议 |
| --- | --- | --- | --- |
| UX-DSH-01 | P1 | 当前详情页仍把实盘订单列为可用工具，且配置凭证行与新 Mainnet 隔离实现不一致。 | 发布 Bundle 时同步详情页文案，明确 `live` 的专用变量、专用目录和默认关闭；在顶部显示环境、交易开关、账户就绪和对账状态。 |
| UX-DSH-02 | P1 | “AI loop”与 Quick start 可能暗示持续无人值守运行。 | 改为“会话触发的 AI 决策”；明确 `backgroundLoop=not_running`，并在没有 scheduler 时禁止使用“自己决定/自动操盘”措辞。 |
| UX-DSH-03 | P1 | 没有逐笔 Mainnet 授权卡，也没有将账户身份、余额、精度、名义额和风险检查集中展示。 | 在未来启用 Mainnet 写入前实现独立确认卡和可审计授权；在此之前将 Mainnet 写入显示为 unavailable，而不是可配置功能。 |
| UX-DSH-04 | P1 | 健康行情可能被误读为交易就绪。 | 增加明确的 readiness 卡：账户、订单/持仓对账、执行权威、WS/行情新鲜度分别显示 `ready/unknown/blocked`，未知状态默认阻断。 |
| UX-DSH-05 | P2 | 活动 Harness 使用旧 Bundle，无法看到工作树新增的就绪状态和文案。 | 通过官方 Plugin Manager 在 disposable profile 中安装并验证新 Bundle；对升级前后的非敏感状态哈希做保全检查，不能直接修改活动 profile。 |

## 验证边界

已验证：当前 DSH 无障碍树中的插件详情、配置表、工具清单、Quick start、Safety 和 Limitations 文案；工作树中的 `host-panel.ts`、`client-assets.ts`、`host-tools-trade.ts` 以及现有 UX/完成度报告。

未验证：真实后台 scheduler、OS 级自动恢复、完整订单与持仓对账、Python/Nautilus 唯一执行权威、Mainnet 逐笔授权流程、活动 Host 的 `updateBundle` 激活/回滚和升级后状态保留。Mainnet OAuth 的只读连接/账户读取不等于交易就绪，也不构成无人值守交易授权。

结论：当前 UX 对“会话触发的行情、回测、纸面和 AI 决策工具”是 **部分可接受**；对端到端无人值守 AI 量化操盘是 **未实现/未验收**。产品状态应继续标为 **PARTIAL**。
