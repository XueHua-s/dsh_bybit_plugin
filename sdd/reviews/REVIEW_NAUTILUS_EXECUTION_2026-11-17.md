# Independent review: native Nautilus execution foundation

Date: 2026-11-17 (Asia/Shanghai). Reviewer scope: `python/packages/quant-execution`, its uv registration/lock and `DESIGN_NAUTILUS_EXECUTION.md`. Read repository `AGENTS.md`, local `software-design-philosophy/SKILL.md` and `NAUTILUS_STABLE_COMPATIBILITY_2026-11-17.md`. This reviewer changed only this review artifact.

## Verdict

**ACCEPT for the bounded offline native BacktestEngine foundation. No outstanding P1/P2 finding in that scope.** This is not approval for live Bybit execution, portfolio risk, a production executor, historical strategy validation or product readiness. There is no exchange connectivity or credential parameter in this package.

## Verified findings and boundaries

- **Native authority:** `run_simulation` constructs the installed Nautilus `BacktestEngine`; strategy callbacks invoke the native order factory, `submit_order` and `cancel_all_orders`. Results are read from actual native orders (`status`, `filled_qty`, `order.events`, native `OrderFilled.last_qty`). The wrapper does not synthesize successful fills/cancels or maintain a second execution ledger.
- **Version/source correspondence:** package metadata and uv lock pin `nautilus-trader==1.231.0`; runtime distribution inspection returned `1.231.0`. The lock contains the macOS CPython 3.12 wheel hash `ed9304cbedeccd03e157c89b1e9acc3c9c35785f3bc2a114e4ea2e262a051890`, matching the compatibility report. Existing stable checkout resolves to `27a8e54e7ac3c57d6cbf8891f0283dfbaee97317`. This is compatibility evidence, not an independent binary reproducibility attestation.
- **Real finite liquidity:** native venue explicitly sets `BookType.L2_MBP` and `liquidity_consumption=True`. One initial two-sided L2 snapshot precedes quote callbacks by one nanosecond; subsequent stationary quotes drive callbacks without supplying new L2 liquidity. Nonstationary quote input is rejected rather than presenting stale L2 depth as a moving market. A reviewer probe submitted two BUY limit intents of 0.010 each against 0.004 ask liquidity: native filled quantities were `(0.004, 0)`, both canceled, open orders 0. No phantom replenishment occurred across orders/callbacks. This deliberately stationary two-level fixture does not establish queue realism or realistic historical impact.
- **Partial/cancel sequencing:** checked-in test verifies native Accepted → Filled → Canceled ordering, exact 0.004 filled quantity and native fill quantity tuple `(0.004,)`. An additional observer subclass called the real `run()` and inspected the cache before disposal: Initialized/Submitted/Accepted/Filled all had `ts_event=ts_init=1_000_000_000`; PendingCancel/Canceled had both timestamps `2_000_000_000`. Cancellation is reported only from the native terminal state, not from sending a cancel request.
- **Identity/idempotency:** duplicate/blank request IDs are rejected before engine construction; admission is explicitly per finite run. Native UUID client order IDs are unique within the checked run and across repeated runs. This is not durable deduplication or exchange reconciliation. No client-order-ID persistence is claimed.
- **Admission:** actual native instrument supplies increments and quantity/notional limits. Nonfinite/nonpositive sizes, increment mismatch, min/max quantity, minimum notional and invalid limit-price increments fail closed; malformed fixture rules/fees and unsorted timestamps are rejected. A user-selected alternate symbol is exercised. Metadata is explicitly synthetic, not claimed current Bybit metadata. The fixture account balance and margin configuration do not substitute for account identity, usable-balance authorization or independent portfolio risk.
- **Environment:** only literal `backtest` is accepted, including the default. Explicit mainnet/testnet/demo/internal-paper/empty/uppercase values are rejected. No Bybit adapter, URL, credential access, generated code execution or upstream live example was executed.
- **Cleanup and ownership:** every call creates its own local engine/strategy/cache and uses `finally: engine.dispose()` around configuration, run and result extraction. The new exception test uses a subclass of the real native engine which raises from `run`, then asserts its actual trader is disposed. Normal runs confirm disposed trader/strategy, stopped strategy and zero open orders. An additional 4-worker/8-run thread smoke completed with 8 filled/disposed results and 8 unique IDs. That small smoke does not establish general native thread safety or a shared long-running engine ownership contract; no shared engine API exists in this increment.
- **Workspace/structure:** src-layout installable package has its own pyproject and Nx project descriptor; uv root dependency/source and wildcard membership discover the package under `--locked`. Native implementation files are 6, 88, 58 and 147 lines (299 total), all below 500. Nx discovery is intentionally left to the coordinating agent while pnpm manifests stabilize; this reviewer did not run pnpm or claim a verified Nx graph.

## Executed evidence

All commands ran from repository root. Every uv invocation used `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache`.

| Actual command / operation | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest -q python/packages/quant-execution/tests` (initial read) | 0 | 19 passed, 10 upstream Pandas4Warning warnings |
| Same command after author added exception/stationary fixture tests | 0 | **21 passed**, 10 upstream Pandas4Warning warnings |
| `uv run --project python --locked ruff check python/packages/quant-execution` | 0 | All checks passed |
| `uv run --project python --locked pyright python/packages/quant-execution` | 0 | 0 errors, 0 warnings, 0 informations |
| `uv run --project python --locked python - <<'PY'` version + two-order liquidity probe | 0 | Runtime 1.231.0; fills 0.004/0; canceled, disposed, stopped, open=0 |
| Same Python heredoc invocation, 4-worker/8-run probe | 0 | `runs 8 native_filled_disposed True unique_ids 8` |
| Same Python heredoc invocation, real-run observer subclass | 0 | Native partial/cancel timestamps described above; disposed True |
| `git -C /tmp/bybit-nautilus-stable rev-parse HEAD` | 0 | Exact stable SHA above |
| `wc -l python/packages/quant-execution/src/quant_execution/*.py` | 0 | All individual implementation files below 500 lines |

The three executable probes used this common input, imported from `quant_execution`: `InstrumentSpec('ETHUSDT','ETH',Decimal('.10'),Decimal('.001'),Decimal('.001'),Decimal(100),Decimal(5))`; three identical 2000.00/2000.10 bid/ask quotes at 1/2/3 billion nanoseconds. Liquidity and observer probes used quote size .004 and BUY .010 limit 2000.10; the liquidity probe supplied two distinct request IDs. The observer temporarily replaced the module's engine symbol with a subclass whose `run()` called `super().run()` and printed `self.cache.orders()` events before ordinary disposal. The thread probe used quote size 100.000, one BUY .010 market order per call, `ThreadPoolExecutor(max_workers=4)` and eight runs. No production files were patched for these probes.

The first memory registry search had no relevant hit; no historical memory fact was used. One existence probe `test -f sdd/reviews/REVIEW_NAUTILUS_EXECUTION_2026-11-17.md` returned 1 before this new artifact was created; it was not a failed product verification.

## Design diagnostic

`software-design-philosophy`: **10/10 for this bounded module (8/8 diagnostic rows; no failed row)**. Responsibilities are identifiable; the single execution API hides materially greater native engine complexity; callers do not depend on Strategy/event-loop wiring; interface comments disclose fixture and authorization limits; native lifecycle and validation knowledge have explicit owners; design and implementation boundaries were reviewed together; the API can be understood from immutable models and its contract; the initial-L2/stationary-fixture refinement avoids leaking misleading market behavior. No additional abstraction is required to reach 10/10 for this slice.

## Remaining acceptance limits

Full live executor integration, durable journal/deduplication, unknown-result reconciliation, account authorization, reduce-only/TP/SL, recovery, independent full risk, dynamic market data, fees/position/PnL reconciliation, long-running service ownership and TS execution-path cutover remain outside this acceptance. Fees are configured in native instrument metadata but the result contract does not prove fee or position accounting. The compatibility report's earlier unrun work is historical research status, not evidence that this slice passed those larger gates. No Linux runtime, SBOM/vulnerability/secret scan, Nx discovery, full repository Verify Gate, release, install into DSH, commit or push is claimed by this review.

## Security follow-up: fsspec override

The coordinating audit subsequently identified PYSEC-2026-4217 in the original transitive `fsspec==2026.2.0`. This section supersedes the earlier no-vulnerability-scan statement for the Python dependency scan only; it does not imply a complete repository release gate.

**Follow-up verdict: ACCEPT the explicitly documented uv workspace override for this bounded offline foundation. No outstanding P1/P2 in that scope. Standard pip compatibility is NOT accepted.**

Independently inspected the updated design, root uv override, package dependency, lock and new native catalog test. Installed distribution metadata reports `nautilus-trader 1.231.0` requiring `fsspec (==2026.2.0)`, while `bybit-quant-execution 0.1.0` explicitly requires `fsspec==2026.6.0`. Root `[tool.uv].override-dependencies` and lock select patched `2026.6.0`; the Nautilus pin remains unchanged. No ignore/allowlist was used to suppress the vulnerability. The package's patched direct dependency makes the conflict explicit to standalone resolvers instead of permitting silent installation of the vulnerable version. An ordinary pip resolver cannot satisfy both exact pins; I did not perform a standalone pip install or claim one passed.

The new regression uses the actual native `ParquetDataCatalog` on a pytest temporary local filesystem, writes a native instrument and three native quote ticks, and reads them through the native catalog APIs. It checks instrument identity, quote count, instrument IDs, event timestamps, bid/ask prices and sizes, and asserts the installed patched fsspec version. This exercises a real local filesystem integration rather than a mocked fsspec import. It does not prove other persistence protocols, reference templates, remote catalogs, all fsspec APIs or live execution compatibility. The exact upstream requirement remains an intentional and externally observable metadata divergence.

Executed independently after this change; same `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache` prefix:

| Actual command | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest -q python/packages/quant-execution/tests` | 0 | **22 passed**, including native local Parquet roundtrip; 10 upstream warnings |
| `uv run --project python --locked pytest -q python` | 0 | **133 passed**; 10 upstream warnings |
| `uv run --project python --locked pip-audit --skip-editable` | 0 | **No known vulnerabilities found**; three workspace editables explicitly skipped; pip cache disabled because host cache is not writable |
| `uv pip check --python python/.venv/bin/python` | **1** | **One known incompatibility:** Nautilus requires 2026.2.0, installed fsspec 2026.6.0. This check is not green and is not represented as compatible. |
| `uv run --project python --locked ruff check python/packages/quant-execution` | 0 | All checks passed |
| `uv run --project python --locked pyright python/packages/quant-execution` | 0 | 0 errors/warnings/informations |
| `uv run --project python --locked python - <<'PY'` installed `importlib.metadata.distribution(...).requires` inspection | 0 | Conflicting exact requirements above confirmed from installed metadata |

Operational limitation: install through the tested locked uv workspace override. Unqualified standalone pip distribution/install, upstream-supported compatibility, broad persistence and production readiness remain unverified/unapproved. A future supported upstream release or independently maintained patched dependency metadata would be needed to remove this packaging limitation; do not silently remove the direct patched dependency or downgrade fsspec to restore a green metadata check.
