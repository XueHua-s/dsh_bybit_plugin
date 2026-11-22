# Independent review: deterministic quant-risk foundation

Date: 2026-11-17 (Asia/Shanghai). Reviewer: independent reviewer for the quant-risk implementation owner. Reviewed repository `AGENTS.md`, the local `software-design-philosophy` and SDD Build Verify Gate/advisor instructions, original brief §13, Brainstorm/DEFINE, `DESIGN_QUANT_RISK.md`, and all package implementation/tests/manifests. The reviewer changed only this artifact; all runtime inputs were fabricated offline fixtures. A quick memory registry search found no relevant history; no historical memory claim was used.

## Verdict

**ACCEPT for the isolated pure deterministic offline risk veto foundation. No outstanding P1/P2 finding in that bounded code scope.** All fifteen original §13 controls have deterministic implementations and test coverage. This does **not** accept AT-021 as an unbypassable execution integration or claim complete §13 delivery: there is no engine-owned consumer, atomic reservation transaction, durable rejection/audit/notification path or final Nautilus enforcement here. An approved plan is explicitly evidence, not exchange authorization.

## Verified contract and behavior

- `evaluate(intent, context, policy)` separates the only agent-originated proposal from engine/operator-owned snapshots, limits and clock. No tool/JSON route, network, credentials, LLM, exchange or generated-code execution is present. Immutable records alone do not authenticate their origin; the documentation states this limitation rather than treating user-provided context as trustworthy.
- Every boundary Decimal must be an actual finite bounded Decimal; missing records, wrong types, float/string/bool impostors, NaN/sNaN/infinities and out-of-range precision/exponents deny before arithmetic. Enum strings, booleans, timestamps, tuple collections and duplicate references/pairs are validated. Stable rejection codes do not echo input. Arithmetic has a private precision/exponent/rounding/trap context.
- Position legs and pending reservations consume absolute gross notional without hedge netting. Per-symbol position/concentration limits aggregate legs; account exposure and effective leverage use full projected gross exposure. Pending orders consume slots and fee-buffered margin, conservatively even if exchange available margin already excludes them. SELL/reduction intents receive no bypass flag or exposure credit.
- Positive equity, account identity, permission, reconciliation and exact environment matching are mandatory; Mainnet is vetoed even when policy and account both select it. Backtest/internal_paper/demo/testnet remain isolated labels rather than actual exchange connections.
- Account, market, portfolio, correlation and individual exposure timestamps are checked for staleness/future state. Market estimates bind to the exact immutable proposal, including size, side, price and leverage. The plan expires at the earliest required snapshot timestamp plus TTL. Generation origin, mark/FX correctness and complete private-state reconciliation remain producer invariants; all values require a common trusted USDT valuation.
- Daily loss uses the larger of reported loss and day-start equity decline; drawdown uses peak equity, with equality freezing new exposure. Current/proposed leverage and liquidation distance are checked. Concentration and correlation limits use equity; complete pair coverage, absolute positive/negative correlations and transitive connected clusters deliberately avoid unsupported diversification credit.
- Spread, funding, executable liquidity, margin/fee buffer, cooldown, instrument precision/minimums and emergency freeze are enforced. Slippage checks the entire executable/limit envelope; minimum notional uses the lower envelope while exposure caps use the upper envelope. A stop veto does not claim cancellation, scheduler freeze, durable events or authorized position closure.

## Adversarial findings closed before acceptance

| Finding | Evidence before correction | Verified correction |
|---|---|---|
| P1: Decimal validation field discovery skipped policy/market numbers | Runtime dataclass inspection returned zero fields matching string `"Decimal"`; annotations were actual classes. | Exact `field.type is Decimal`; malformed-field regressions and independent field sweep pass. |
| P1: slippage checked estimate but allowed an unsafe submitted ceiling/floor | Reviewer fixture with BUY quantity 1, bid/ask/executable 100, limit 200, 1% slippage cap approved under otherwise loose caps. | BUY ceiling and SELL floor included in adverse envelope; both regressions deny. |
| P2: upper risk valuation reused for minimum notional | SELL quantity 1, limit 98, executable/bid 99, minimum notional 99 approved despite submitted value 98. | Separate lower-envelope minimum check; 98 denies and exact 99 equality approves. |
| Boundary clarity | Runtime enum/blank identifiers, per-leg freshness, estimate binding and mixed valuation assumptions needed explicit treatment. | Exact strings/blank rejection, per-leg timestamps, earliest expiry, exact proposal binding and common-numeraire producer contract documented/tested. |

No production/test fix was made by the reviewer. Findings were sent to the implementation owner and coordinator; corrections were made by the implementation owner and independently rechecked.

## Commands and evidence

Commands ran from repository root using the existing environment. No dependency installation, account request, trading, database migration, commit or push occurred.

| Actual command/method | Exit | Observed result |
|---|---:|---|
| `PYTHONPATH=python/packages/quant-risk/src python/.venv/bin/python -m pytest -q python/packages/quant-risk/tests` after final corrections | 0 | **61 passed in 0.18s**, including four Hypothesis properties, all fifteen controls, gross hedges/reservations and both reported price-envelope regressions. |
| `python/.venv/bin/ruff check python/packages/quant-risk` | 0 | All checks passed. |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-risk` | 0 | 0 errors, 0 warnings, 0 informations. |
| Reviewer Python heredoc using the public API and test fixture before final minimum-notional refinement | 0 | **501 independent adversarial assertions**: malformed Decimal-field sweep across intent/policy/market/account/exposure/correlation, hostile ambient Decimal precision/exponent/rounding, correlation/position ordering invariance and ordinary frozen-record mutation rejection. |
| Independent runtime annotation and unsafe BUY ceiling/SELL minimum-notional reproduction heredocs | 0 | Produced the findings above; acceptance was withheld until corrected regressions passed. |
| `wc -l python/packages/quant-risk/src/quant_risk/*.py python/packages/quant-risk/tests/*.py` | 0 | Public export module 49, evaluator 172, models 155, validation 180; test module initially 447 lines, now 455 after the reproducibility refinement below. All individual handwritten files below 500. |

Invocation issues remain visible: an initial direct `python/.venv/bin/pyright python/packages/quant-risk` from root exited 1 because it could not resolve pytest/hypothesis/package imports without the environment interpreter. The explicit `--pythonpath` invocation above resolves the context and passes. An initial read of the not-yet-created `BUILD_REPORT_QUANT_RISK.md` exited 1; this was a pending artifact, not a failed product test. Earlier focused runs had 54 passing tests; the 61-test final run supersedes that count.

## Design diagnostic

`software-design-philosophy`: **10/10 for this bounded package, 8/8 rows satisfied; no failed row.** Each module has one coherent purpose. The single facade hides validation, portfolio arithmetic and correlation traversal. Callers depend on immutable semantic snapshots rather than evaluator mechanics. Public comments disclose units, gross accounting, thresholds and authority limits. Design discussion included early independent safety findings. Models own the snapshot contract, validation owns strict invariants and evaluator owns veto math. A newcomer can discover the boundary through the package docstring and models. The refinements invested in simpler explicit invariants instead of bypass flags or additional execution abstractions. No additional abstraction is needed to reach 10/10 for this scope; this score is not an integrated-system readiness score.

## Unfinished acceptance and parent-owned gates

The following remain unaccepted by this review: authoritative live account/market/instrument/correlation acquisition and provenance; integration that cannot be bypassed by any execution route; atomic concurrent reservation and durable idempotency; generation revalidation immediately before sole Nautilus submission; rejection persistence/user notification and retry controls; emergency cancel/reconcile/scheduler freeze and separately authorized closing; safe dedicated reduce-only transition planning. Incorrect server-supplied liquidation, funding, notional or correlation estimates cannot be detected merely because their values are finite and fresh.

Workspace uv/lock registration, full Nx graph, aggregate DEFINE `pnpm run verify`, full repository tests, wheel build, SBOM/vulnerability/secret scans, release/install/upgrade/uninstall and publication remain coordinator-owned evidence. This reviewer has not claimed those commands passed or waived them. Package-scoped acceptance must not close the original product checklist or substitute for `sdd-release`.

## Post-review reproducibility receipt

The final test-only refinement imports Hypothesis `seed`/`settings` and adds `@seed(20261117)` plus `@settings(database=None)` to each of the four existing properties. Their generated input domains and assertions remain unchanged; the eight decorator lines explain the test file's increase from 447 to 455 lines. This makes the declared seed explicit and prevents a local example database from affecting case selection. The implementation owner reported production hashes unchanged; independent current SHA-256 inspection matches the reported source baseline below.

After this refinement the reviewer independently reran the same scoped pytest, Ruff and explicit-interpreter Pyright commands: **61 passed in 0.19s**, Ruff **exit 0**, Pyright **exit 0 / zero errors**. The current build report now exists and records the focused results, fixed seed, independent receipt, cached offline wheel/source build and explicitly attributed parent aggregate checks. The earlier missing-artifact observation above is resolved. The package acceptance verdict remains **ACCEPT for the pure offline foundation only**.

Current independently read SHA-256 values:

| File under `python/packages/quant-risk/` | SHA-256 |
|---|---|
| `src/quant_risk/evaluator.py` | `e1a8a8feb788d248bd7bd328b4a29c901c6981c184454d2fa141e4473c562122` |
| `src/quant_risk/models.py` | `a29b3709f910a46c975e469f3849a2ab918f69e6c8be4fa34d436fac648f277a` |
| `src/quant_risk/validation.py` | `8d579bbb052a58ac8016e329bfb76abff07238ac61131f9fa6aaa271fbaf9931` |
| `tests/test_risk.py` | `1a2c38e6bab16011b5ad4871c5f4c6c27b77e17e0ef733b1dfd07ac6d0aa292d` |

The coordinator separately reports aggregate Python 213 tests, Ruff/format 36 files, typechecking, root Verify Gate and security checks exiting 0. Those aggregate results are attributed parent evidence, not commands independently run by this reviewer. Full original product acceptance remains partial.
