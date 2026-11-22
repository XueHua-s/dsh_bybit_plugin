# BUILD REPORT: Deterministic Strategy Families

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | STRATEGY_FAMILIES |
| **Date** | 2026-11-19 |
| **Author** | SDD Build continuation |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **DESIGN** | `sdd/features/DESIGN_STRATEGY_FAMILIES.md` |
| **Status** | Complete for this scoped increment; parent product remains partial |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 15 logical entries |
| Cross-file coupling | Medium: new uv/Nx package, shared metadata imports, registry tests |
| Security surface | Pure strategy math; no credentials, exchange, account or order APIs |
| LLM prompt items | None in this increment |
| Runtime capabilities | Default sequential execution |

**Recommendation:** default mode; the files are tightly coupled and the project has a single shared worktree.

**User decision:** existing session authorization to continue unattended project work; no additional execution mode was requested.

**Pre-build review:** the available independent review agents were unavailable for this slice; no formal external design review was executed.

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 15/15 scoped entries |
| **Files Created** | 15: strategy package, builtin registration/test, and this report |
| **Files Modified** | 11: workspace/registry wiring, research/UX/design records, and SBOMs |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 20 including initial failures and corrected reruns |
| **Verify Gate** | Green for the parent command's stated local plugin scope |
| **Execution Mode** | default |

## Task Execution

| # | Manifest ID | Task | Status | Verification | Evidence |
|---:|---:|---|---|---|---|
| 1 | 1-2 | Create uv/Nx strategy package and shared metadata/models | Complete | `uv lock --project python` | Exit 0; lock resolved 94 packages |
| 2 | 3-6 | Implement indicators, Alpha158 subset and built-in evaluators | Complete | scoped pytest | 63 strategy/registry tests passed |
| 3 | 7-8 | Add formula/family tests and third-party notice | Complete | `pytest python/packages/quant-strategies/tests` | Passed in full suite |
| 4 | 9-12 | Wire engine dependency and builtin registry registration | Complete | Python full test/static checks | 218 tests passed; Ruff/Pyright passed |
| 5 | 13-15 | Update repository audit, design drift and build report | Complete | `git diff --check` | Exit 0 |

## Files Changed

The implementation is in `python/packages/quant-strategies/`; the engine registry remains the lifecycle boundary. The repository audit and design records explicitly distinguish local rewrites from upstream library integration.

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `python/packages/quant-strategies/pyproject.toml`, `project.json` | Create | 1 | Yes | uv/Nx project discovery and package build pass |
| `python/packages/quant-strategies/src/quant_strategies/{metadata,models,indicators,alpha158,families,__init__}.py` | Create | 2-6 | Yes | Pure strategy contracts and evaluators |
| `python/packages/quant-strategies/tests/{test_indicators,test_alpha158,test_families}.py` | Create | 7 | Yes | Deterministic formula and bounds tests |
| `python/packages/quant-strategies/THIRD_PARTY_NOTICES.md` | Create | 8 | Yes | Qlib source and MIT attribution |
| `python/pyproject.toml`, `python/uv.lock` | Modify | 9 | Yes | Workspace dependency and lock updated |
| `python/apps/quant-engine/pyproject.toml`, `project.json` | Modify | 10 | Yes | Engine package dependency and Nx edge |
| `python/apps/quant-engine/src/quant_engine/strategy_registry.py`, `tests/test_strategy_registry.py` | Modify | 11 | Yes | Shared metadata import and valid internal URI fixture |
| `python/apps/quant-engine/src/quant_engine/builtin_strategies.py`, `tests/test_builtin_strategies.py` | Create | 12 | Yes | Built-ins remain research-only |
| `docs/research/github-repository-audit.md` | Modify | 13 | Yes | Records five Qlib formula rewrites and non-integration |
| `sdd/features/DESIGN_STRATEGY_REGISTRY.md` | Modify | 14 | Yes | Records the shared-model ownership boundary |
| `sdd/reports/BUILD_REPORT_STRATEGY_FAMILIES.md` | Create | 15 | Yes | This evidence report |
| `sdd/reports/UX_REVIEW_DSH_BYBIT_UI_2026-11-19.md` | Modify | User follow-up | Yes | Appends the current read-only panel state |
| `sbom.cdx.json`, `sbom.python.cdx.json` | Modify | Project rule | Yes | Regenerated with 200/92 components |

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | Registry design / shared metadata | The registry design predated the reusable strategy package and said no package consumer existed. | Approved documentation reconciliation | Updated `DESIGN_STRATEGY_REGISTRY.md`; registry remains engine-owned and contracts are package-owned. |
| 2 | Qlib attribution | The initial implementation was a narrow formula subset, not full Qlib integration. | No product-scope expansion | Updated repository audit and notice to state independent reimplementation and non-integration. |

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Strategy/registry tests | `uv run --project python --locked pytest python/packages/quant-strategies/tests python/apps/quant-engine/tests/test_strategy_registry.py python/apps/quant-engine/tests/test_builtin_strategies.py -q` | Pass | 63 passed |
| Python full tests | `uv run --project python --locked pytest python/packages python/apps -q` | Pass | 218 passed, 1 dependency deprecation warning |
| Ruff | `uv run --project python --locked ruff check python/packages/quant-strategies python/apps/quant-engine` | Pass | All checks passed |
| Format | `uv run --project python --locked ruff format --check python/packages/quant-strategies python/apps/quant-engine` | Pass | 42 files already formatted |
| Pyright | `uv run --project python --locked pyright python/packages/quant-strategies python/apps/quant-engine` | Pass | 0 errors, 0 warnings |
| Package build | `uv build --project python/packages/quant-strategies --out-dir /tmp/bybit-quant-strategies-dist` | Pass | sdist and wheel built |
| Nx discovery/graph | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm nx show projects --json`; `pnpm nx graph ...` | Pass | `quant-strategies` discovered; `quant-engine -> quant-strategies` edge present |
| Parent Verify Gate | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` | Pass | Exit 0; local DSH plugin gate only |
| Diff hygiene | `git diff --check` | Pass | Exit 0 |
| SBOM | `pnpm run sbom`; `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx run quant-data:sbom` | Pass | CycloneDX outputs contain 200 npm and 92 Python components; Python SBOM includes `bybit-quant-strategies` |
| Dependency audit | `pnpm run security:deps` | Pass | pnpm audit and pip-audit report no known vulnerabilities; five editable workspace packages are skipped by pip-audit |
| Secret scan | `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | Pass | 27.23 MB scanned; no leaks found |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green for the command's local plugin scope |
| **Evidence** | Build, lint, typecheck, unit tests, bundle, SDK and tooling checks all succeeded. The Define explicitly says this does not certify AT-010–031. |

### Complementary Checks

| Check | Status | Evidence |
|---|---|---|
| Lint | Pass | Ruff and existing TS lint passed |
| Typecheck | Pass | Pyright and parent TypeScript typecheck passed |
| Tests | Pass | 218 Python tests and parent plugin tests passed |
| Build / Compile | Pass | Strategy wheel/sdist and DSH build passed |

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-017 | Register strategy metadata/configuration/lifecycle | Partial implementation complete | Registry validation matrix passed; durable persistence and external provenance remain outside this slice. |
| AT-018 | Required strategy fixtures emit reproducible bounded signals | Partial | Implemented families and Alpha158 subset passed deterministic fixtures; full §7 catalog and runtime integration remain open. |
| AT-019/020/024/026 | Selector, portfolio, research loop and final validation | Blocked / open | No selector, portfolio optimizer, candidate sandbox, OOS/walk-forward or Nautilus integration was added. |

## Advisor Ledger

None — no formal external review was executed for this slice.

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Four initial test failures: float precision, ATR fixture expectation and internal URI form | Corrected tests/source to use approximate float, actual True Range value and valid `internal://` URI | Resolved; scoped tests pass |
| 2 | Ruff/Pyright found import, formatting and mapping type issues | Applied formatter/import fixes and explicit numeric config narrowing | Resolved; static checks pass |

## Deviations from Design

None after reconciliation. The implementation remains deliberately partial and does not claim upstream library integration or trading authority.

## Blockers

None for this scoped algorithm-package increment. Testnet execution and unattended scheduling remain parent-product requirements outside this manifest and are not represented as complete.

## Final Status

### Overall: COMPLETE for scoped strategy-family increment

- [x] Scoped manifest tasks completed
- [x] Incremental verification recorded
- [x] Verify Gate green for its stated local scope
- [x] Complementary checks pass
- [x] Drift decisions recorded
- [x] No generated prompt or credential path added
- [ ] Parent product acceptance complete (remains open by design)

## Next Step

Execute o **SDD Handoff by RDD**.
