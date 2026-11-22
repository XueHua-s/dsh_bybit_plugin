# Design: deterministic portfolio target planning

## Scope

This slice closes the missing pure portfolio calculation boundary in AT-020. It
accepts validated strategy proposals and reconciled current exposures, applies
operator-owned confidence, concentration, gross-exposure and turnover ceilings,
and returns an auditable target map plus a safe transition plan. It has no
exchange, credential, persistence or order authority; the independent risk
engine still revalidates every transition step.

An omitted proposal means hold. An expired or low-confidence proposal abstains
and does not flatten an existing position. A sign reversal is represented as a
reduce-to-zero step followed by an increase step and a recheck warning, so a
strategy change cannot unconditionally reverse an existing position.

## File manifest

| File | Purpose |
|---|---|
| `python/packages/quant-portfolio/pyproject.toml` | uv package metadata |
| `python/packages/quant-portfolio/project.json` | Nx targets |
| `python/packages/quant-portfolio/src/quant_portfolio/models.py` | immutable contracts |
| `python/packages/quant-portfolio/src/quant_portfolio/planner.py` | bounded allocation and transitions |
| `python/packages/quant-portfolio/src/quant_portfolio/__init__.py` | public package boundary |
| `python/packages/quant-portfolio/tests/test_planner.py` | deterministic acceptance tests |
| `python/apps/quant-engine/src/quant_engine/portfolio.py` | adapt validated selector decisions into account-free portfolio proposals |
| `python/apps/quant-engine/src/quant_engine/strategy_selector.py` | carry selected candidate confidence into the decision contract |
| `python/apps/quant-engine/tests/test_portfolio.py` | selector-to-proposal boundary tests |
| `python/apps/quant-engine/pyproject.toml`, `python/apps/quant-engine/project.json` | declare the engine dependency and Nx graph edge |
| `python/pyproject.toml`, `python/uv.lock` | register the Python workspace project |
| `sdd/reports/BUILD_REPORT_PORTFOLIO_ALLOCATION.md` | evidence and remaining limits |

## Verify gate

```yaml
verify_gate:
  kind: test
  cmd: "uv run --project python --locked pytest python/packages/quant-portfolio/tests -q"
  pass_when: "exit 0"
  threshold: "10 tests"
  manual_fallback: "No live exchange or credentials are required; missing uv/dependencies remains inconclusive."
```
