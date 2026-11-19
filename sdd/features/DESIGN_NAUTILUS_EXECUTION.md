# DESIGN: Native Nautilus execution foundation

Date: 2026-11-17. Sources: BRAINSTORM_BYBIT_AI_QUANT.md, DEFINE_BYBIT_AI_QUANT.md, DESIGN_BYBIT_AI_QUANT.md and original attachment §§5,6.1,12,13,15. This is a bounded implementation increment, not acceptance of the complete product.

## Drift and decision

The prior 2.x architecture assessment does not describe the selected stable 1.231.0 API. Pin the actual stable wheel and use its public `BacktestEngine`, native simulated exchange, Strategy, order factory and event/cache lifecycle. Python quant implementation follows the original Python data-plane requirement; TypeScript remains mandatory for plugin/tooling. The existing parallel TS exchange-order path remains unresolved original-scope drift; this increment does not approve it.

## Architecture and contract

`quant_execution` is an offline backtest foundation. `run_simulation(instrument, quotes, intents, environment='backtest')` admits a deterministic finite plan, executes native market/limit orders from quote callbacks, cancels remaining orders on a later quote, snapshots native events and cache states, and disposes the engine in finally. The small immutable result hides Nautilus event wiring, engine configuration, strategy lifecycle and cache. Fixture metadata (symbol, currency, precision, increments, minimum/maximum size and notional) is explicit and caller-selected; no implicit BTC or live exchange metadata. Validation uses the actual constructed native instrument and never rounds unsafe user input silently. Intent request IDs are unique per simulation; native ClientOrderIds come from the native factory. This in-memory idempotency fence is not crash-durable production deduplication.

Only literal `backtest` is accepted. No exchange adapter, credential argument, external client factory, URL, environment variable or live environment default exists. Testnet, Demo, Internal Paper and Mainnet are deliberately unavailable here. There is no empty production execution API. Native risk checks remain enabled; local admission checks are precision/size/notional guards and do not substitute for independent portfolio risk.

## File Manifest (before implementation)

| ID | Path | Action / purpose |
|---|---|---|
| N1 | python/pyproject.toml; python/uv.lock | Add real workspace dependency, compatible Python upper bound and exact native wheel lock |
| N2 | python/packages/quant-execution/pyproject.toml; project.json | Installable src-layout project and Nx targets |
| N3 | python/packages/quant-execution/src/quant_execution/__init__.py; models.py | Typed immutable input/result interface and validation |
| N4 | python/packages/quant-execution/src/quant_execution/fixtures.py | Explicit reusable native instrument/quote construction for offline fixtures |
| N5 | python/packages/quant-execution/src/quant_execution/simulation.py | Deep native runtime boundary; real events/order lifecycle and cleanup |
| N6 | python/packages/quant-execution/tests/test_native_execution.py | Native accepted/fill/cancel, uniqueness/deduplication, guards, environment fence, cleanup tests |
| N7 | sdd/reports/BUILD_REPORT_NAUTILUS_EXECUTION.md | Executed evidence and remaining original requirements |
| N8 | python/packages/quant-execution/tests/test_catalog_compatibility.py | Local native Parquet catalog/filesystem compatibility of security override |

Root depends on the Python execution package so `uv run --project python --locked` discovers it. Nx project is independently discoverable with test/lint/typecheck/build targets. The engine app will depend on this package only when an actual integration exists; no invented dependency edge.

## Verification and acceptance

Run exact pinned uv sync, native pytest, Ruff, Pyright and Nx discovery. Native proof must inspect actual OrderAccepted/OrderFilled/OrderCanceled events and native cached statuses, never synthesized success. Finite fixtures use one native L2 book snapshot and stationary quote callbacks, spread, taker/maker fees and instrument rules. `liquidity_consumption=True` prevents repeated synthetic reuse of consumed book size. Nonstationary quotes are rejected because this small fixture is not a depth-delta replay engine. Test non-default symbols. Native L2 partial fill and subsequent cancellation are proven from the native order event history and last-quantity values; this does not prove realistic market impact or a complete cost model. Native UUID ClientOrderIds remain unique across repeated runs while request deduplication remains run-local. No generated algorithm, prompt or DB migration is introduced.

## Limits and requirement traceability

§5/6.1: establishes real Nautilus dependency and isolated order authority foundation only. §12: native finite order submission/cancellation and IDs only; live Bybit execution, persistent idempotency, uncertain-result reconciliation, reduce-only/TP/SL and recovery remain missing. §13: local size/precision safety is not the independent full risk engine. §15: deterministic event-driven fixture proof is not strategy validation, OOS, funding/liquidation/impact modelling or a profitability result. Long-running engine/API and TS cutover remain separate work.

## Design diagnostic

8/8 rows satisfied (10/10 planned): modules have coherent purposes, small contract hides native wiring, fixture formats remain explicit, interface comments define safety invariants, native internals remain swappable, checks review boundaries and design is recorded before code. No failed row at design time; implementation review will reassess.

## Security dependency remediation — 2026-11-17

Audit found introduced `fsspec==2026.2.0` affected by PYSEC-2026-4217, fixed in 2026.6.0. Nautilus 1.231.0 wheel metadata pins exactly 2026.2.0, confirmed from installed `importlib.metadata.requires`; upstream source also uses an exact range. Ordinary additional constraints cannot select the fix. Retain the required verified Nautilus version, use a transparent root uv security override `fsspec==2026.6.0`, record the upstream metadata divergence and rerun native/full Python tests plus vulnerability audit. This is a bounded, tested local compatibility override, not a claim of upstream support for all persistence/catalog features. No ignore/allowlist is permitted. `uv pip check` is expected to flag the original upstream exact pin; report that conflict explicitly.

### Override compatibility evidence

Inspected pinned Nautilus `persistence/catalog/parquet.py`, `persistence/config.py`, and `persistence/writer.py`: imports `fsspec.filesystem`, AbstractFileSystem, LocalFileSystem path conversion, MemoryFileSystem, `infer_storage_options`, and AbstractBufferedFile. Catalog uses filesystem open/exists/glob/isdir/isfile/mkdirs/rename/rm/_strip_protocol. Official fsspec changelog https://filesystem-spec.readthedocs.io/en/latest/changelog.html inspected at 2026.6.0: disables referenceFS template parsing by default (#2039/#2029), plus fixes local symlink removal, glob recursion, referenceFS compatibility, async walk/cache, and FTP filenames. The finite execution boundary does not consume referenceFS templates or remote filesystems. Native local Parquet catalog instrument/quote write-read roundtrip is now a required smoke test, not an invented claim of general remote filesystem compatibility.

The execution package itself also requires patched fsspec exactly, so a standalone pip install cannot silently select the vulnerable upstream pin: without the documented workspace override policy its conflicting metadata fails resolution. Supported installation is the tested uv workspace.
