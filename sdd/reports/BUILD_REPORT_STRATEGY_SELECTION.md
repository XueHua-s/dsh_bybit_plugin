# BUILD REPORT: Validated strategy selection boundary

> Implementation report for the research-only, engine-owned strategy selector.

## Scope and status

| Attribute | Value |
|---|---|
| Feature | STRATEGY_SELECTION |
| Design | `sdd/features/DESIGN_STRATEGY_SELECTION.md` |
| Date | 2026-11-20 |
| Status | Implemented slice; broader architecture acceptance remains open |
| Execution authority | None; the selector does not read account state, choose an exchange symbol, or create orders |

The selector compares already registered strategy records for one caller-supplied
market snapshot. It gates on approved lifecycle metadata, paper validation,
regime support and caller-supplied evaluation provenance. Evaluation references
and scores are audit inputs only: this slice does not independently verify the
research artifact or prove profitability.

## File manifest

| Path | Action | Result |
|---|---|---|
| `python/apps/quant-engine/src/quant_engine/strategy_selector.py` | Create | Complete; deterministic regime, eligibility, score, cooldown and hysteresis |
| `python/apps/quant-engine/tests/test_strategy_selector.py` | Create | Complete; five deterministic tests |
| `sdd/reports/BUILD_REPORT_STRATEGY_SELECTION.md` | Create | Complete; this receipt |

## Verification receipts

| Command | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest python/apps/quant-engine/tests/test_strategy_selector.py -q` | 0 | 5 passed |
| `uv run --project python --locked ruff check python/apps/quant-engine/src/quant_engine/strategy_selector.py python/apps/quant-engine/tests/test_strategy_selector.py` | 0 | All checks passed |
| `uv run --project python --locked pyright python/apps/quant-engine/src/quant_engine/strategy_selector.py` | 0 | 0 errors, 0 warnings, 0 informations |
| `uv run --project python --locked ruff format --check python/packages python/apps` | 0 | 90 files already formatted after formatting the two new selector files |
| `pnpm run python:lint` | 1 (initial) | Ruff checks passed; initial format check identified the two new files |
| `pnpm run python:typecheck` | 0 | 0 errors, 0 warnings, 0 informations |
| `pnpm run python:test` | 0 | 410 passed, 11 existing dependency/runtime warnings |
| `pnpm run verify` | 0 | Nx build, lint, TypeScript checks, plugin tests, bundle/API and tooling checks passed |
| `pnpm run security:deps` | 0 | No known npm or Python dependency vulnerabilities; editable Python packages were skipped by pip-audit |
| `gitleaks dir --redact --no-banner` | 0 | No leaks found in approximately 30.33 MB scanned |
| `pnpm run sbom` | 0 | Wrote CycloneDX SBOM with 200 npm components |
| `pnpm exec nx run quant-data:sbom` | 0 | Python CycloneDX SBOM target succeeded |
| `git diff --check` | 0 | No whitespace errors after code and documentation edits |

The initial formatting failure was corrected with Ruff's formatter and the
format check was rerun successfully. No Mainnet or Testnet order was sent.

## Acceptance and limits

- Approved + paper-passed registry records are required before a candidate can be selected.
- Unknown regimes, stale/future evaluation timestamps, fewer than 30 OOS samples,
  malformed evidence, non-ready signals and non-positive scores abstain.
- Cooldown and hysteresis make transitions deterministic and auditable.
- The selector does not select the instrument, construct a portfolio, validate
  the contents of an evaluation artifact, persist selection state, or connect
  to Nautilus/Bybit execution.
- AT-019's broader stability, common-data and portfolio-transition requirements
  remain unproven; this report must not be read as evidence of unattended trading.

## Drift and blockers

The architecture book describes a complete autonomous quant data plane. This
slice is intentionally narrower: the DSH AI still chooses eligible instruments
and whether to act, while this selector only scores strategies for an existing
snapshot. Full runtime integration, independent evaluation verification,
portfolio/risk orchestration, reconciliation and recovery remain future work.

## Final status

**Implemented research boundary; not production or unattended-execution ready.**
