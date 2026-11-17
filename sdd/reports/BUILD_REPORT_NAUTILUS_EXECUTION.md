# BUILD REPORT: Native Nautilus execution foundation

## Metadata

| Attribute | Value |
|---|---|
| Feature | NAUTILUS_EXECUTION |
| Date | 2026-11-17 |
| Author | Native execution implementation agent |
| BRAINSTORM | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| DEFINE | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| DESIGN | `sdd/features/DESIGN_NAUTILUS_EXECUTION.md` |
| Status | In Progress — bounded native slice verified; aggregate repository/release gates owned by coordinating agent |

Original attachment §§5,6.1,12,13,15 read. Selected native stable tag `1.231.0`, source inspection SHA `27a8e54e7ac3c57d6cbf8891f0283dfbaee97317`. Upstream LGPL-3.0-or-later dependency is dynamically imported, no upstream source was copied. Tested local interpreter: CPython 3.12.16 macOS arm64. Explicit range is `>=3.12,<3.15`, matching selected upstream metadata.

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 11 created/modified including design/report |
| Cross-file coupling | Small typed interface hides native engine and callback wiring |
| Security surface | Offline environment fence, run-local deduplication, instrument guards, cleanup |
| LLM prompt items | None |
| Independent volume | This native package is independent from concurrent TS SDK work |
| Context-rot risk | Bounded plan, explicit manifest written before implementation |
| Runtime capabilities | Parent-delegated parallel work, sequential package implementation |

Recommendation and decision: follow the parent/user-authorized implementation delegation; no extra permission request. Pre-build review: upstream source/API research; independent post-build review requested by coordinating agent.

## Summary

Native functionality is implemented and executed: market fill, resting-order cancellation, partial fill then confirmed cancellation, unique native UUID ClientOrderIds across repeated runs, duplicate request rejection, size/price/notional guards, non-live environment rejection, stop/unsubscribe/dispose and exception disposal. Results come from native Nautilus Order objects and events. No fake executor or REST order adapter exists in this package.

The reproducible fixture is deliberately a single L2 snapshot with stationary quote callbacks. `liquidity_consumption=True` prevents already consumed depth from being reused on each matching iteration. It is not a general historical depth replay system.

## Task Execution

| ID | Task | Status | Verification |
|---|---|---|---|
| N1 | Exact pinned dependency, uv member/root dependency and lock | Complete | uv sync exit 0; installed native 1.231.0 |
| N2 | Python src-layout and own Nx project | Package complete; Nx discovery pending shared install | Native wheel/sdist build exit 0 |
| N3 | Immutable typed contract | Complete | Pyright exit 0 |
| N4 | Explicit symbol/instrument/quote/L2 fixtures | Complete | ETH and BTC execution, stationary fixture rejection tests |
| N5 | Native strategy/engine/order lifecycle | Complete | Real accepted/fill/cancel/partial events and native disposal |
| N6 | Meaningful runtime tests | Complete | 21 native tests; full Python suite 132 tests |
| N7 | Evidence report | Complete | This report |

## Files Changed

| File | Action | Manifest |
|---|---|---|
| `python/pyproject.toml`, `python/uv.lock` | Modified | N1 |
| `python/packages/quant-execution/pyproject.toml`, `project.json` | Created | N2 |
| `python/packages/quant-execution/src/quant_execution/__init__.py`, `models.py` | Created | N3 |
| `python/packages/quant-execution/src/quant_execution/fixtures.py` | Created | N4 |
| `python/packages/quant-execution/src/quant_execution/simulation.py` | Created | N5 |
| `python/packages/quant-execution/tests/test_native_execution.py` | Created | N6 |
| `sdd/features/DESIGN_NAUTILUS_EXECUTION.md`, this report | Created | N7 |

No commits, pushes, DB migrations, live exchange orders or new virtual environments were created. Uses the existing `python/.venv`.

## Drift Detected

Prior 2.x ADR is incompatible evidence for selected stable 1.231.0; research agent updates upstream assessment. Existing direct TS exchange execution remains `DRIFT-ORIGINAL-003`; this foundation neither accepts nor replaces the required live cutover. Root Python upper bound changes because Nautilus supports `<3.15`; lock removes unsupported Python 3.15 wheel entries rather than arbitrarily upgrading existing packages.

## Verification Results

All Python commands below use `UV_CACHE_DIR=/tmp/bybit-quant-uv-cache` because default user cache is outside sandbox writes.

| Command | Exit | Evidence |
|---|---:|---|
| `uv sync --project python` (authorized network escalation) | 0 | Resolved 91 packages; 11 installed including native Nautilus 1.231.0 |
| `uv sync --project python --locked --reinstall-package bybit-quant-execution --offline` | 0 | Rebuilt editable after initial source creation |
| `uv run --project python --locked pytest python/packages/quant-execution/tests -q` | 0 | **21 passed**, 0.53s |
| `uv run --project python --locked pytest python -q` | 0 | **132 passed**, 6.07s |
| `uv run --project python --locked ruff check python/packages/quant-execution` | 0 | All checks passed |
| `uv run --project python --locked ruff format --check python/packages/quant-execution` | 0 | 5 files already formatted |
| `uv run --project python --locked pyright python/packages/quant-execution` | 0 | 0 errors/warnings |
| `uv build --project python/packages/quant-execution --out-dir /tmp/bybit-quant-execution-dist --offline` | 0 | Wheel + sdist built |
| `git diff --check` | 0 | No whitespace errors |
| `uv run --project python --locked ruff check python/packages python/apps` | 0 | All checks passed |
| `uv run --project python --locked ruff format --check python/packages python/apps` | 0 | 26 files already formatted |
| `uv run --project python --locked pyright python/packages python/apps` | 0 | 0 errors/warnings |
| `uv pip check --python python/.venv/bin/python` | 0 | 89 installed packages compatible |
| `wc -l .../src/quant_execution/*.py .../tests/*.py` | 0 | Maximum source file 147 lines; total 415 |
| `pnpm exec nx show project quant-execution --json` | Pending/not accepted | pnpm attempted missing-dependency bootstrap, sandbox DNS failures; coordinator owns shared install/discovery |

Native smoke output (UUID varies):

```text
nautilus-trader 1.231.0
status=CANCELED filled_quantity=0.004 fill_quantities=(0.004,)
OrderInitialized -> OrderSubmitted -> OrderAccepted -> OrderFilled -> OrderPendingCancel -> OrderCanceled
disposed=True strategy_stopped=True open_orders=0
```

### Verify Gate

| Attribute | Value |
|---|---|
| Kind | Native bounded test increment |
| Command | `uv run --project python --locked pytest python/packages/quant-execution/tests -q` |
| Exit / result | 0; 21 passed |
| Status | Green for native slice; original DEFINE aggregate product gates remain open |
| Manual UX | N/A |

### Initial failures and corrections

Initial pytest collection exit 2: editable package was installed before source existed; rebuilt editable locally. First runtime tests exit 1: incorrectly queried nonexistent BacktestEngine `is_disposed`; corrected to real native trader and strategy state after dispose. Pyright exponent union errors fixed using explicit finite exponent conversion. Initial partial test exit 1 revealed native liquidity reuse default; explicitly enabled native liquidity consumption. Ruff initial findings fixed. These failures were corrected and final checks rerun; none hidden or counted as passing.

Native emits ten upstream `Timestamp.utcnow` Pandas4Warning deprecations under locked pandas 3.1.1; warnings remain visible. No test failures result, and no upstream code was patched.

## Acceptance Test Verification

| Scope | Evidence | Limits |
|---|---|---|
| Native finite order authority foundation (§5/6.1/12) | Native orders, events, fills, confirmed cancellations, partials | Live Bybit adapter not integrated |
| IDs and admission (§12/13) | Unique native UUID IDs; duplicate and instrument guard tests | Deduplication is run-local, not durable recovery |
| Environment separation (§12) | Every value except literal `backtest` rejected | No Internal Paper, Testnet, Demo or Mainnet executor implemented |
| Event-driven validation (§15) | L2 consumption and native partial-cancel proof | No strategy/OOS/walk-forward/full cost validation claimed |
| Shutdown | Native trader/strategy disposed; real engine exception disposal tested | Not production process recovery or reconciliation |

## Advisor Ledger

Independent native review **ACCEPT**, no P1/P2: `sdd/reviews/REVIEW_NAUTILUS_EXECUTION_2026-11-17.md`. Reviewer independently reran 21 tests, Ruff and Pyright, probed two orders sharing finite liquidity (0.004 then zero fill), exact fill/cancel timestamps and concurrent finite runs with native disposal/unique IDs. This does not establish a production thread ownership contract.

## Issues Encountered

Sandbox default uv cache access denied; task cache moved to `/tmp`. Sandbox DNS prevented initial install; authorized escalation installed requested dependency successfully. Shared pnpm bootstrap/Nx proof remains coordinated separately.

## Deviations from Design

Partial-fill proof upgraded from conditional to proven by native L2 snapshot and consumption; recorded in design. Stationary fixture constraint made explicit and validated to avoid silently claiming historical depth replay.

## Blockers / Remaining Product Work

Nx discovery awaits shared TS dependency installation. Aggregate original Verify Gate, Python SBOM/vulnerability/secret scans are owned by coordinator; independent native review is ACCEPT. Missing original product requirements include live Bybit executor, authenticated account/balance/startup reconciliation, persistent uncertain-execution handling, independent complete risk engine, reduce-only/TP/SL, live recovery, long-running execution integration and TS direct-order cutover. No part of this native fixture harness authorizes or enables live orders.

## Final Status

IN PROGRESS for aggregate gate coordination. The native finite simulation slice is implemented and verified. Full original product acceptance remains incomplete.

## Security remediation follow-up — 2026-11-17

Aggregate audit initially returned exit 1 for introduced fsspec 2026.2.0, PYSEC-2026-4217; fixed release 2026.6.0. Verified wheel metadata requires exactly `fsspec==2026.2.0`, as does selected upstream source. An ordinary compatible constraint cannot solve this pin. The root uv workspace therefore explicitly overrides to `fsspec==2026.6.0`, preserving `nautilus-trader==1.231.0`; lock records the override. No vulnerability ignore or allowlist was added. This is an intentional metadata divergence, accepted for the scoped offline native functionality with direct compatibility tests; broad Nautilus persistence/live compatibility remains unproven.

Inspected pinned Nautilus fsspec imports and filesystem calls and official patched release changelog (linked in design). Added manifest N8 `tests/test_catalog_compatibility.py`: actual native ParquetDataCatalog local filesystem writes and reads native instrument and all quote fields/timestamps. It executes only trusted installed libraries and temporary local files.

| Command (same UV_CACHE_DIR prefix) | Exit | Result |
|---|---:|---|
| `uv sync --project python` | 0 | fsspec 2026.2.0 removed; 2026.6.0 installed; Nautilus pin retained |
| `uv run --project python --locked pytest python/packages/quant-execution/tests -q` | 0 | **22 passed**, including native catalog roundtrip |
| `uv run --project python --locked pytest python -q` | 0 | **133 passed**, 6.06s |
| `uv run --project python --locked pip-audit --skip-editable` | 0 | **No known vulnerabilities found**; only three workspace editables skipped |
| `uv run --project python --locked pyright python/packages/quant-execution` | 0 | 0 errors/warnings |
| `uv run --project python --locked ruff check python/packages python/apps` | 0 | All checks passed |
| `uv run --project python --locked ruff format --check python/packages python/apps` | 0 | 27 files already formatted |
| `git diff --check` | 0 | No whitespace errors |
| `uv pip check --python python/.venv/bin/python` | 1 | **Expected metadata conflict**: Nautilus requires fsspec==2026.2.0; installed2026.6.0 |

The earlier pre-remediation pip-check compatibility receipt is historical, superseded by the explicit upstream metadata conflict above. Patched dependency audit and tested native runtime/catalog functionality pass; do not describe the entire dependency graph as metadata-compatible.

Packaging fence: the execution package also explicitly depends on `fsspec==2026.6.0`; without the root uv override, standalone pip resolution fails on the upstream conflicting exact pin instead of selecting vulnerable fsspec silently. Supported install is the tested uv workspace, not an unqualified standalone pip install.
