# Build report — Read-only Testnet preflight boundary

Date: 2026-11-19
Design: `sdd/features/DESIGN_TESTNET_READONLY_PREFLIGHT.md`
Status: **offline slice passed; product preflight and native trading remain partial**

## Delivered

- Added a secret-free trusted Testnet/Linear profile contract and fixture store.
- Added strict normalized projections for identity/key permissions, Unified wallet
  totals, one Linear instrument, source freshness and reconciliation report coverage.
- Added a read-only preflight orchestrator with four named provider operations,
  fixed Testnet endpoint binding, a fixed timeout, sanitized failure codes, and
  `order_submission_allowed = false` on every result.
- Added fixture tests for identity mismatch, permission excess, stale data,
  incomplete reports, malformed projection fields, zero funds, provider failure,
  invalid profile and symbol input.
- Used synthetic numeric UIDs in tests; no account identifiers or credentials are
  persisted in the new files.

## Verification ledger

| Command | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest python/apps/quant-engine/tests/test_bybit_profiles.py python/packages/quant-execution/tests/test_bybit_projection.py python/packages/quant-execution/tests/test_bybit_preflight.py` | 0 | 28 focused fixture tests passed. |
| Initial `uv run --project python --locked ruff check python/apps/quant-engine/src/quant_engine/bybit_profiles.py python/apps/quant-engine/tests/test_bybit_profiles.py python/packages/quant-execution/src/quant_execution/bybit_projection.py python/packages/quant-execution/src/quant_execution/bybit_preflight.py python/packages/quant-execution/tests/test_bybit_projection.py python/packages/quant-execution/tests/test_bybit_preflight.py` | 1 | Found import-order/typing/catch issues; fixed before acceptance. |
| `uv run --project python --locked ruff check --fix <six changed Python files>` | 0 | Applied import sorting; no remaining Ruff check findings. |
| `pnpm run python:test` | 0 | 317 tests passed in 46.53s; 11 existing upstream/deprecation warnings. |
| `pnpm run python:lint` | 0 | Ruff check passed; all 68 Python files formatted. |
| `pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings, or information. |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` | 0 | Repository TypeScript/Bundle/SDK/tooling gate passed; some Nx build/lint/typecheck tasks were cache hits. |
| `gitleaks git --redact` | 0 | 20 commits scanned; no leaks found. |
| `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | 0 | 24.90 MB scanned; no leaks found. |
| `git diff --check` | 0 | Tracked changes have no whitespace errors. |

## Not implemented or claimed

- No production trusted-profile persistence or secure credential provider exists in
  this slice. The in-memory profile store is explicitly fixture-only.
- No signed HTTP transport, Bybit raw-response normalization, redirect denial, or
  online request was implemented or exercised. The typed provider is injected and
  fixture-tested; its four GET-only method names do not prove a production network
  transport is safe.
- No Nautilus execution client, order submission, cancellation, or Mainnet path was
  created. `eligible_for_reconciliation` is not `ready_to_trade`.
- Live account identity, key permissions/IP/expiry, balance, exchange rules,
  report completeness, private connectivity and native reconciliation remain
  unknown/unaccepted. Zero equity remains a diagnostic result; no order is allowed.
- No dependency or SBOM change was needed. Plugin Manager lifecycle, unattended
  strategy scheduling, complete risk/portfolio/strategy modules and full original
  acceptance remain open.

The repository product status stays **PARTIAL**. This build only establishes an
offline-safe contract and fixture behavior for a later reviewed secure provider.
