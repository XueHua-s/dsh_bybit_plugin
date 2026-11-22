# Nautilus 稳定版兼容性研究

日期：2026-11-17（Asia/Shanghai）。范围：SDD Design 的版本决策证据；只读上游/发行元数据，不安装依赖、不执行上游代码，不接触凭证或订单。

## 决定

下一实现切片选择 **`nautilus_trader==1.231.0`**，保留项目 CPython 3.12，依赖支持范围应收紧为 `>=3.12,<3.15`，不要为了开发分支 2.x RC 升级 Python。它是本轮官方 PyPI JSON 中最新非预发布版本，2026-08-02 上传，相关 wheel 均未 yanked。稳定发布不等于没有 bug，更不代表本项目交易验收通过。

权威版本证据：[PyPI 1.231.0 JSON](https://pypi.org/pypi/nautilus_trader/1.231.0/json)、[PyPI 项目](https://pypi.org/project/nautilus_trader/1.231.0/)、[官方固定源码](https://github.com/nautechsystems/nautilus_trader/tree/27a8e54e7ac3c57d6cbf8891f0283dfbaee97317)。实际获取的是全版本 JSON `https://pypi.org/pypi/nautilus_trader/json`，本地 `/tmp/nautilus-pypi.json`。官方 tag `v1.231.0` 为 annotated tag object `d3e1685e979925d7b0ffacd1b3f442547686e18f`，peeled commit **`27a8e54e7ac3c57d6cbf8891f0283dfbaee97317`**，缓存 `/tmp/bybit-nautilus-stable`。

## Python、ABI 与平台

固定源码根 `pyproject.toml` 与 wheel METADATA 都是 `>=3.12,<3.15`，不同于此前研究 2.x develop 的 >=3.13。已读取提交内 `docs/getting_started/installation.md`：官方平台是 Ubuntu22.04+ x86_64/ARM64（glibc >=2.35）、macOS ARM64、Windows Server2022+ x86_64。

**不能只凭安装文档的 macOS15+ 描述承诺 wheel 支持 macOS15**：实际 1.231.0 PyPI macOS wheel tag 是 `macosx_26_0_arm64`。本机只读 `sw_vers -productVersion` 输出 `27.3`，`uname -m` 输出 `arm64`，与该 wheel 的 OS/arch 下限相容，但未 import，不能据此宣称运行时成功。若必须支持 macOS15，需另评估 1.230.0（PyPI 的 cp312 wheel tag 为 macosx_15_0_arm64）及其对应源码和缺陷，不可静默降级或把较新 wheel 强装到旧 OS。

| CPython3.12 发行文件 | SHA256（官方 JSON） | 决策 |
|---|---|---|
| `nautilus_trader-1.231.0-cp312-cp312-macosx_26_0_arm64.whl` | `ed9304cbedeccd03e157c89b1e9acc3c9c35785f3bc2a114e4ea2e262a051890` | 本机候选；已下载并核验 hash/zip metadata |
| `nautilus_trader-1.231.0-cp312-cp312-manylinux_2_35_x86_64.whl` | `8c438e95c275a13df0c0ddb7012c462708b5e99ff3612e36a1b7bd49ab39c216` | Linux CI 候选；仅核对 PyPI 元数据，未下载/运行 |
| `nautilus_trader-1.231.0-cp312-cp312-manylinux_2_35_aarch64.whl` | `cae3d3b0dd26e88ce44b75d7696bd0193af62846c22cf6b19d93928643089b83` | Linux ARM64 可用 wheel 元数据；未运行 |
| `nautilus_trader-1.231.0-cp312-cp312-win_amd64.whl` | `0697f51e9143f9d8d040f75d2e6a45218003cc34f7ea5b0eb2f9cda6935427de` | 元数据存在；不属于本轮验证平台 |

macOS wheel 156,041,405 bytes；下载到 `/tmp/nautilus_trader-1.231.0-cp312-cp312-macosx_26_0_arm64.whl`，SHA256 与上述官方值一致。WHEEL 明确 `Root-Is-Purelib: false`、`Tag: cp312-cp312-macosx_26_0_arm64`，不是通用 py3/abi3 包。通过 Python 标准库 zipfile 读取 METADATA/WHEEL 和源文件，**没有 import wheel、解压安装或执行 native code**。

wheel 的 Bybit config/factories/execution 与 Sandbox config/factory 共五个 Python 文件，逐字节与上述 tag checkout 比较全部相同。这是这些文件的源码对应证据，不是 native binary 可重现构建或全 wheel 来源证明。

METADATA 的基础依赖包括 click>=8.4.1,<9、fsspec==2026.2.0、msgspec>=0.21.1,<1、numpy>=1.26.4、pandas>=2.3.3,<4、portion>=2.6.1、pyarrow>=25、pytz>=2026.2、tqdm>=4.68.4,<5、tzdata>=2026.3，以及非 Windows 的 uvloop==0.22.1。锁定 1.231.0 后仍必须生成真实 uv.lock、核验可解析性与平台 wheel，更新 Python SBOM 并扫描；本报告未执行 solver，不能宣称依赖可安装或无漏洞。无需 Betfair/IB/Polymarket/visualization extras。

## 稳定版真实 Bybit API

实际读取固定提交：

- `nautilus_trader/adapters/bybit/config.py`、`factories.py`、`execution.py`。
- `examples/live/bybit/bybit_exec_tester.py`、`docs/integrations/bybit.md`。
- `tests/integration_tests/adapters/bybit/test_execution.py` 的具体 Mock 测试区段。

**采用 1.x API，禁止拿 2.x LiveNode builder 当作可用实现**：

```python
from nautilus_trader.adapters.bybit import BybitDataClientConfig
from nautilus_trader.adapters.bybit import BybitExecClientConfig
from nautilus_trader.adapters.bybit import BybitLiveDataClientFactory
from nautilus_trader.adapters.bybit import BybitLiveExecClientFactory
from nautilus_trader.adapters.bybit import BybitEnvironment, BybitProductType
from nautilus_trader.config import TradingNodeConfig, LiveExecEngineConfig
from nautilus_trader.live.node import TradingNode
```

配置传 `environment=BybitEnvironment.TESTNET` 或 `.DEMO`，`product_types=(BybitProductType.LINEAR,)`（Spot 为 `(BybitProductType.SPOT,)`）。`TradingNodeConfig(data_clients={"BYBIT": data_config}, exec_clients={"BYBIT": exec_config}, exec_engine=LiveExecEngineConfig(reconciliation=True, ...))`，`node=TradingNode(config=config)`，`node.add_data_client_factory("BYBIT", BybitLiveDataClientFactory)` / `node.add_exec_client_factory("BYBIT", BybitLiveExecClientFactory)`，`node.trader.add_strategy(strategy)` 后 `node.build()`。strategy `submit_order(order)` / `cancel_order(order)` 驱动统一 OMS，不直接调用 adapter 私有方法或自己拼 REST。

上述只是实际 API 关系，非可直接运行完整代码；新实现还需固定 trader ID、账户归属、instrument allowlist、risk 配置、loop 与 persistence。上游例子默认 Mainnet、risk bypass、开仓和退出动作，**只读，禁止直接运行或照抄安全设置**。默认环境 `None` 会落 MAINNET，项目必须显式传 enum 并先 fail-closed。

注意源码内部文档 drift：BybitExecClientConfig docstring 说 Spot 不可与其他类型混用，但同一固定版 `execution.py` 125–138 行与 exec tester 实际支持 mixed UTA（纯 Spot => CASH；其他或 mixed => MARGIN）。本项目先单产品明确配置，不依赖这处矛盾拓展权限；mixed 产品支持需独立测试。这也说明不能将 docstring 当作唯一事实。

固定版支持 Demo（HTTP 下单，不建 trade WS）、Testnet（独立 private/trade WS）、Spot/Linear；产品 ID suffix 仍为 `-SPOT.BYBIT` / `-LINEAR.BYBIT`。Spot reduce-only 在 `_validate_order` 明确拒绝；Demo TP/SL trigger-price 自定义字段存在限制；不得从 2.x 新增能力推导 1.231.0 支持。后续 TP/SL、Hedge、OCO 仍需逐项验收，不在此切片默认开放。

`execution.py` 1080 行附近对非确定 venue rejection 的 submit error 保持 submitted 并等 reconciliation；Mock `test_submit_order_demo_post_submit_lookup_failure_waits_for_reconciliation` 断言 HTTP submit 只调用一次、没有发 rejected；另有 WS error 等待对账的测试。cancel tests 分别涵盖 client ID 和 venue ID，并不证明撤单 ack 等于已取消。本项目仍须在事件/report 确认后才标 terminal，不能把工具 `sent:true` 当执行结果。

## 稳定版模拟/回测表面与下一实现

**真实 Sandbox API**：`nautilus_trader.adapters.sandbox.config.SandboxExecutionClientConfig`，工厂 `nautilus_trader.adapters.sandbox.factory.SandboxLiveExecClientFactory`（注意 1.x 名称）。配置用 `venue="SANDBOX"`、`starting_balances=["100_000 USD"]`、`account_type="CASH"`、`base_currency="USD"` 等字符串字段；与 2.x Money/Venue 参数不同。它基于 Nautilus `SimulatedExchange`，不需要 Bybit 凭证。

实际读取 `tests/integration_tests/adapters/sandbox/conftest.py` 和 `test_execution.py`：fixture 向 cache 添加 instrument、构造 SandboxExecutionClient（注入 loop/portfolio/msgbus/cache/clock），`connect()` 后推进 event loop；strategy.submit_order，`exec_client.on_data(QuoteTick(...))` 触发原生 submitted/accepted/filled；limit resting order 的 strategy.cancel_order + tick 产生 pending-cancel/canceled。测试使用真实模拟引擎、受控市场数据；不是自写假成交账本。

**真实 Backtest API**：`nautilus_trader.backtest.engine.BacktestEngine` / `BacktestEngineConfig`，`nautilus_trader.backtest.models.FillModel`；固定版 `tests/unit_tests/backtest/test_engine.py` 读取了 import/setup：`engine.add_venue(venue=Venue("SIM"), oms_type=OmsType.HEDGING, account_type=AccountType.MARGIN, base_currency=USD, starting_balances=[Money(...)], fill_model=FillModel())`，随后 add instrument/data/strategy/run 的完整构建应照固定版接口逐项验证。不能沿用 2.x DefaultFillModel/LiveNode 导入。

建议下个 Build 先实现 **离线原生 BacktestEngine 驱动的 deterministic paper adapter** 或上述 SandboxExecutionClient，在常驻 engine 中隐藏，受控 tick 测试真实 OMS/仓位/成交事件；非 paper 的 Bybit executor 工厂必须仍是唯一真实执行入口，暂不连接。用同一个 domain command / admission / journal 驱动，不建立 TS 或 Python custom REST executor。

最小 gate：CPython3.12 import 与确切版本；Nautilus native simulated market/limit、resting cancel、partial fills/position/fees；命令幂等与 unknown outcome；Bybit factory/config 构建测试（无 connect、无 key）；Demo/Testnet/Mainnet deny 默认策略；API generated schema/TS client 与所有 TS mutation 路径切断；Nx/Python checks、uv锁/SBOM/扫描。Sandbox fill 顺序稳定且可重放后才扩大测试。**所有这些是计划，本轮未运行**。

## 许可与未完成项

稳定版 wheel METADATA 和根 pyproject 是 **LGPL-3.0-or-later**，不同于此前 2.x SHA 的 LGPL-3.0-only；发行审查必须使用选定 stable artifact 的精确信息。保持原样依赖、版权/许可文本、可替换性、对应源码和组合发行条款复核，不能把独立进程认定为自动豁免。未做法律结论或完整许可证扫描。

未完成：依赖安装/solver/lock 与漏洞扫描、native import、macOS/LinuxCI 真正执行、完整 Bybit 规则/ID/对账审计、恢复/持久化/账户授权、TS bypass 移除、Demo/Testnet E2E。最新 stable 选择是兼容性决定，不是生产准入。

## 真实命令与结果

| 操作 | 结果 |
|---|---|
| `git status --short` 开始检查 | 0；只有 `.agents/` 未跟踪，已有 ADR 已提交到当前基线；本轮无提交 |
| `curl -fsSL https://pypi.org/pypi/nautilus_trader/json -o /tmp/nautilus-pypi.json` | 0，读取官方 metadata |
| `git -C /tmp/bybit-nautilus-research ls-remote --tags origin 'refs/tags/v1*'` | 0，输出过多；最终 tag 以 clone peeled SHA 为准 |
| `git clone --depth 1 --branch v1.231.0 https://github.com/nautechsystems/nautilus_trader.git /tmp/bybit-nautilus-stable` | 0，detached HEAD `27a8e54...` |
| `git -C /tmp/bybit-nautilus-stable rev-parse HEAD` | 0，上述完整 SHA |
| `curl -fsSL <PyPI JSON 给出的精确 macOS wheel URL> -o /tmp/nautilus_trader-1.231.0-cp312-cp312-macosx_26_0_arm64.whl` | 0；URL 为 `https://files.pythonhosted.org/packages/2d/cc/d0898a1311e39278b8b92667d487dd636e698020b5736ac73e6d0f3f1976/nautilus_trader-1.231.0-cp312-cp312-macosx_26_0_arm64.whl` |
| Python stdlib hashlib/zipfile metadata 与五文件 byte comparison | 0，hash 一致、五项 True；未 import 第三方代码 |
| `sw_vers -productVersion` / `uname -m` | 0 / 0，`27.3` / `arm64` |

所有临时研究产物保留 `/tmp`，未加入发行物或访问凭证。仅修改本报告和执行 ADR。最终 whitespace/diff check 另记录在本轮结果。
