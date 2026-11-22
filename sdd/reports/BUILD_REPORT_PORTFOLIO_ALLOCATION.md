# Build report: deterministic portfolio target planning

## Result

Implemented a pure `quant-portfolio` package plus a narrow engine adapter that
turns validated selector decisions into bounded target proposals. The planner
keeps unmentioned positions, identifies abstentions, scales aggregate gross
exposure, and forces reversals through reduce-to-zero followed by an
independently revalidated increase. It also reports when existing exposure
cannot meet policy immediately because turnover limits cap the reduction. The
package and adapter have no account or exchange authority.

## Verification

| Command | Exit | Result |
|---|---:|---|
| `uv lock` (from `python/`) | 0 | Workspace lock updated with `bybit-quant-portfolio`. |
| `uv run --project python --locked pytest python/packages/quant-portfolio/tests -q` | 0 | 10 passed. |
| `pnpm run python:lint` | 0 | Ruff checks passed; 96 Python source/test files already formatted. |
| `pnpm run python:typecheck` | 0 | Pyright: 0 errors, 0 warnings, 0 informations. |
| `pnpm run python:test` | 0 | 424 passed; 11 upstream deprecation warnings. |
| `pnpm exec nx run quant-portfolio:test` | 0 | New package test target discovered and passed. |
| `pnpm exec nx show projects` | 0 | Nx discovers `quant-portfolio` and `quant-engine`. |
| `pnpm exec nx graph --file=/tmp/bybit-quant-nx-graph.json` | 0 | Task graph includes the `quant-engine` → `quant-portfolio` project edge. |
| `pnpm run verify` | 0 | DSH/TypeScript repository gate passed. |
| `pnpm run security:deps` | 0 | No known third-party findings; pip-audit skipped six editable workspace distributions. |
| `pnpm run sbom` | 0 | TypeScript SBOM contains 200 npm components. |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx run quant-data:sbom` | 0 | Python SBOM contains 93 components, including engine and portfolio. |
| `gitleaks dir --redact --no-banner` | 0 | No leaks found; approximately 30.81 MB scanned. |
| `git diff --check` | 0 | No whitespace errors. |

## Limits

This is a deterministic planning boundary, not a portfolio optimizer, account
reconciler, risk approval, order manager or Nautilus adapter. The selector
adapter is available but is not yet invoked by the long-running autonomous
runtime; there is no claim that this closes end-to-end unattended trading. Full
AT-020 still requires wiring plans to durable engine state and an independent
risk authority with Testnet-only fixtures.
