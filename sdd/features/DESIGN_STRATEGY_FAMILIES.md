# DESIGN: Deterministic Strategy Families

> Scoped first implementation of the repository's required target-exposure strategy library.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | STRATEGY_FAMILIES |
| **Date** | 2026-11-19 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **Parent DESIGN** | `sdd/features/DESIGN_BYBIT_AI_QUANT.md` |
| **Status** | Scoped design; parent AT-018 remains broader than this increment |
| **LLM Prompts** | false |

## Problem and scope

The current DSH backtest exposes three TypeScript-only, long-only rules, while the Python quant engine has only a strategy metadata registry. The project needs reusable, deterministic algorithms that accept normalized market snapshots and emit bounded target exposure without gaining exchange, account, risk, credential, or order authority.

This increment creates the Python `quant-strategies` workspace package. It covers SMA/EMA crossovers, Donchian breakout, ADX trend filter, time-series momentum, Bollinger and Z-score mean reversion, RSI reversion, ATR breakout, and a funding-rate carry signal. It also independently reimplements five Qlib Alpha158 expressions (prior close/current close, rolling mean/current close, rolling standard deviation/current close, close position in rolling high-low range, and positive absolute-move share) as research inputs. It does not claim to implement every strategy named in the brief or to reproduce Qlib's complete data, model, training, or portfolio stack.

The algorithms emit `target_exposure` in `[-1, 1]` and never create order intents. Every built-in remains `research` / `not_started`; the registry metadata is provenance and lifecycle state, not evidence that backtests passed or permission to trade.

## Requirements and acceptance

- Implements reusable pure-Python algorithms behind one `evaluate(strategy_id, snapshot, config)` boundary.
- Validates bounded OHLCV/funding inputs, warmup, config names/types/ranges, finite arithmetic, and exposure bounds; malformed values fail with stable non-sensitive error codes.
- Registers built-in metadata through the existing engine registry without promoting any entry.
- Provides reproducible fixtures for the listed implemented strategies and Qlib-derived factor equations; no network or exchange credentials are used by tests.
- Explicitly leaves order execution, risk authorization, live market-data subscription, persistent strategy versions/results, regime selection, portfolio optimization, AI research, sandboxed candidate code, remaining crypto microstructure strategies, grid, DCA, market making, statistical arbitrage, ML/RL, and Testnet order operation open.
- Mainnet stays disabled; this package has no side-effect capability.

Parent traceability: partial progress on **AT-018** and **AT-017**; no change to the parent acceptance definition. AT-019, AT-020, AT-024, and AT-026 remain unimplemented by this increment.

## Design decisions

### 1. Put strategy-domain metadata and algorithms in a reusable Python package

**Choice:** Add `python/packages/quant-strategies`. Move the immutable metadata/configuration types there while retaining the existing engine-owned `StrategyRegistry` behavior and import compatibility from `quant_engine.strategy_registry`.

**Rationale:** Algorithms and their stable metadata belong to the strategy domain; the engine owns registration and lifecycle orchestration. This avoids a strategy package importing an application and lets the registry validate the same definitions that the algorithms expose.

**Alternatives rejected:** Keep algorithms in the DSH TypeScript plugin (duplicates the quant domain and keeps Python engine unable to use them); place all formulas in `quant-engine` (prevents reuse and mixes domain logic with service lifecycle); use Qlib/Freqtrade as runtime dependencies (unnecessary heavyweight/license surface and not a Bybit exchange adapter).

### 2. Pure target-exposure output

**Choice:** Inputs are immutable normalized bars plus optional funding rate; output is an immutable signal, bounded signed target exposure, warmup status, stable reason code, and bounded numeric feature values.

**Rationale:** The boundary is useful for deterministic research and later Nautilus adaptation while keeping orders, current account positions, final risk, and exchange state outside the algorithm.

**Consequence:** It is not yet wired to the long-running engine's ticker stream, DSH UI, or native Nautilus lifecycle. That integration remains a later requirement and must not be inferred from package-level tests.

### 3. Reimplement a narrow Qlib Alpha158 expression subset

**Choice:** Implement factor equations in pure Python with attribution to the audited Qlib source revision; do not import Qlib or copy its runtime. The Qlib window/market assumptions are recorded, and all generated factors begin unvalidated for crypto use.

**Source evidence:** `microsoft/qlib`, commit `54355232463878d2eebb91fe0ee5fa7fa1f5976c`, `qlib/contrib/data/loader.py` Alpha158 feature definitions for ROC, MA, STD, RSV, and SUMP. The repository's `LICENSE` is MIT. Qlib is stock-oriented; formula reuse is a research hypothesis, not evidence of Bybit predictive value.

### 4. Keep candidates unapproved

**Choice:** Built-ins carry internal source metadata, MIT project license, explicit configs, supported fixture instrument/timeframe, empty performance metrics, `not_started` validation, and `research` lifecycle status.

**Rationale:** A mathematical implementation is not a tested edge. Neither registration nor a successful unit test can authorize deployment.

## Software design philosophy diagnostic

**Target score: 10/10** for this slice:

| Diagnostic | Evidence / design action |
|---|---|
| One sentence per module | `metadata.py` owns strategy metadata; `models.py` owns normalized evaluation DTOs; `indicators.py` owns shared math; `alpha158.py` owns the attributed factor subset; `families.py` owns signal rules; engine `strategy_registry.py` owns lifecycle operations. |
| Simpler interface than implementation | Consumers call one `evaluate` function with a strategy ID, snapshot, and bounded config. |
| Implementation can change without callers | Formula helpers and factor implementation stay behind package exports; engine consumes stable metadata and result types. |
| Interface comments explain intent | Public docstrings state warmup, direction, units, and that target exposure is not an order. |
| Design discussion in review | Review checks source attribution, look-ahead avoidance, short/long signs, and status defaults. |
| Each module hides a decision | Window alignment, Wilder smoothing, and factor normalization are owned by the math modules. |
| Newcomers can see boundaries | Package map and this design document name ownership and non-goals. |
| 10–20% design investment | Shared metadata moved out of the service before adding algorithms; unit tests cover formulas and invalid inputs. |

## File manifest

| # | File | Action | Purpose | Dependencies |
|---:|---|---|---|---|
| 1 | `python/packages/quant-strategies/pyproject.toml`, `project.json` | Create | Discoverable dependency-free uv/Nx package and checks | none |
| 2 | `python/packages/quant-strategies/src/quant_strategies/metadata.py` | Create | Shared registry metadata/config contracts | none |
| 3 | `python/packages/quant-strategies/src/quant_strategies/models.py` | Create | Immutable bars, market snapshots, algorithm definitions, signals/errors | 2 |
| 4 | `python/packages/quant-strategies/src/quant_strategies/indicators.py` | Create | Validated moving averages, RSI, ATR, ADX, channels and rolling statistics | 3 |
| 5 | `python/packages/quant-strategies/src/quant_strategies/alpha158.py` | Create | Pure-Python, attributed Qlib factor subset | 3-4 |
| 6 | `python/packages/quant-strategies/src/quant_strategies/families.py`, `__init__.py` | Create | Built-in catalog and unified target-exposure evaluator | 2-5 |
| 7 | `python/packages/quant-strategies/tests/test_indicators.py`, `test_alpha158.py`, `test_families.py` | Create | Formula, input, warmup, sign, and reproducibility evidence | 3-6 |
| 8 | `python/packages/quant-strategies/THIRD_PARTY_NOTICES.md` | Create | Qlib source revision, MIT attribution, and reimplementation boundary | 5 |
| 9 | `python/pyproject.toml`, `python/uv.lock` | Modify | Include the new workspace package in the locked environment | 1 |
| 10 | `python/apps/quant-engine/pyproject.toml`, `project.json` | Modify | Declare the actual strategy-domain dependency and Nx edge | 1-2 |
| 11 | `python/apps/quant-engine/src/quant_engine/strategy_registry.py` | Modify | Import/re-export shared domain models while retaining engine registry logic | 2 |
| 12 | `python/apps/quant-engine/src/quant_engine/builtin_strategies.py`, `tests/test_builtin_strategies.py` | Create | Register built-in metadata as research-only records | 6, 11 |
| 13 | `docs/research/github-repository-audit.md` | Modify | Append exact Qlib code, license, revision, and adaptation evidence | 5, 8 |
| 14 | `sdd/features/DESIGN_STRATEGY_REGISTRY.md` | Modify | Record metadata model ownership after the package boundary is created | 11 |
| 15 | `sdd/reports/BUILD_REPORT_STRATEGY_FAMILIES.md` | Create | Record actual commands, partial AT evidence, limitations, and unresolved scope | 1-14 |

**Total:** 15 logical entries; only paths in this manifest may be changed for this slice.

## Testing and verification

- `uv run --project python --locked pytest python/packages/quant-strategies/tests python/apps/quant-engine/tests/test_strategy_registry.py python/apps/quant-engine/tests/test_builtin_strategies.py -q`
- `uv run --project python --locked ruff check python/packages/quant-strategies python/apps/quant-engine`
- `uv run --project python --locked ruff format --check python/packages/quant-strategies python/apps/quant-engine`
- `uv run --project python --locked pyright python/packages/quant-strategies python/apps/quant-engine`
- `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` — parent Define's gate; green only for its stated local plugin scope, not parent product completion.
- Verify Nx discovers `quant-strategies` and records `quant-engine -> quant-strategies`; verify the lock is current and build Python SBOM after the dependency graph changes.

## Security and operational boundary

- The package has no HTTP, WebSocket, filesystem, subprocess, credentials, exchange, or order APIs.
- Qlib source and all external material are untrusted research data; no upstream code is executed.
- Input sizes and configuration ranges are bounded. Nonfinite values, invalid OHLC relationships, duplicate/out-of-order timestamps, and unknown configuration keys fail closed.
- All strategies are `research` and `not_started`; independent account-aware risk, persistence, selection, backtest validation, paper validation, approval, and Nautilus execution are separate gates.

## Open scope after this slice

This deliverable is intentionally partial. Remaining named algorithms include volatility expansion/regime, funding/basis research, open interest, liquidation imbalance, order-book imbalance, volume profile, grid, DCA, market making, statistical arbitrage, ML prediction, RL, and ensemble composition. Multi-timeframe momentum, runtime scheduling, dynamic regime selection, common Nautilus lifecycle, backtesting/OOS/walk-forward, persistence, and autonomous Testnet execution also remain open.

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-19 | Initial scoped design derived from parent DEFINE AT-017/018 and the supplied strategy requirements. |
