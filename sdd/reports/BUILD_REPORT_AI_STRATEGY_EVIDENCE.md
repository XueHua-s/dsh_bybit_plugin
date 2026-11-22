# BUILD REPORT: AI strategy research evidence bridge

> Implementation report for the research-only Python strategy evidence attached to AI-selected symbols.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | AI_STRATEGY_EVIDENCE |
| **Date** | 2026-11-20 |
| **Author** | Codex / SDD Build continuation |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **DESIGN** | `sdd/features/DESIGN_AI_STRATEGY_EVIDENCE.md` |
| **Architecture source** | `/Users/litlesnow/.codex/attachments/886f3b36-5cab-4ba1-bb1c-7ef525af0e6e/pasted-text-1.txt` |
| **Status** | Blocked — implementation checks pass; prompt evaluation and broader product acceptance remain open |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 22 scoped paths, including Python evaluator/API, OpenAPI SDK, DSH bridge/prompts, tests and this report |
| Cross-file coupling | High: Python contract, generated SDK, DSH Host data flow and two runtime prompts |
| Security surface | Read-only market evidence and LLM instructions; no credentials or exchange write capability |
| LLM prompt items | LP-001 one-shot Host prompt; LP-002 bounded background simulation loop |
| Independent volume | One integration slice; code and prompts were already present in the shared worktree |
| Context-rot risk | High; many unrelated or earlier uncommitted files exist in the shared worktree |
| Runtime capabilities | Sequential verification in the current workspace; no Ralph/Briefs mode used |

**Recommendation:** `default`, because this was a narrow verification-and-report continuation over an existing shared worktree.

**User decision:** Continue the existing authorized work; no new execution mode was selected in this continuation.

**Pre-build review:** No formal external review of the strategy evidence or prompt contracts was available. A separate local code audit of the decision writer does not count as prompt evaluation.

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 8/8 scoped implementation workstreams |
| **Files Created** | 7 scoped artifacts (including this report) |
| **Files Modified** | 15 scoped source, contract, test and requirement files |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 13 distinct command lines |
| **Verify Gate** | Green (`pnpm run verify`, exit 0); SDD prompt gate remains incomplete |
| **Execution Mode** | default |

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---|---|---|---|---|---|
| 1 | SE-01 | Add bounded research-only strategy-family evaluation and API contract | direct | Complete | Python test/lint/typecheck | 438 tests pass; Pyright 0 errors |
| 2 | SE-02 | Regenerate the OpenAPI contract and TypeScript client | direct | Complete | `pnpm run verify` | SDK generation drift check and SDK tests pass |
| 3 | SE-03 | Add the DSH loopback engine client method | direct | Complete | `pnpm run verify` | Build, typecheck and plugin tests pass |
| 4 | SE-04 | Attach evidence from already-fetched candles for AI-selected fresh candidates | direct | Complete | Python + plugin tests | No duplicate candle request; missing engine response is explicit `unavailable` |
| 5 | SE-05 | Add Host and background-loop research-only prompt boundaries | direct | Implemented; prompt receipt incomplete | Prompt assertions in plugin tests | Prompts preserve `research_only=true`, `deployment_eligible=false`; no independent model evaluation |
| 6 | SE-06 | Add bounded-input, stale/empty and contract regression coverage | direct | Complete | `pnpm run python:test`; plugin test suite in root Verify Gate | 438 Python tests and plugin suite pass |
| 7 | SE-07 | Record acceptance and design boundary | direct | Complete | `git diff --check` | AT-036 and the research-only boundary are documented |
| 8 | SE-08 | Final verification and audit receipt | direct | Complete | checks below | Root gate, Python checks, SBOM, dependency and secret scans pass |

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `python/apps/quant-engine/src/quant_engine/strategy_evidence.py` | Create | SE-01 | Yes | Pure bounded evaluator; no account, network or execution dependency |
| `python/apps/quant-engine/src/quant_engine/api.py` and `tests/test_service.py` | Modify | SE-01/02 | Yes | Strict request/response contract and read-only route |
| `python/apps/quant-engine/tests/test_strategy_evidence_api.py` | Create | SE-06 | Yes | Fresh, stale, empty, malformed, reordered, oversized and market-specific cases |
| `contracts/openapi/quant-engine.v1.json` | Modify | SE-02 | Yes | Includes `/api/v1/research/strategy-evidence` |
| `packages/ts/quant-api-client/src/generated/{paths,schema}.ts`, `src/index.ts`, `src/validation.ts` | Modify | SE-02 | Yes | Generated contract and bounded response validation |
| `apps/dsh-plugin/src/lib/engine.ts` | Modify | SE-03 | Yes | Loopback-only client call; no process start or credentials |
| `apps/dsh-plugin/src/lib/ai-market.ts`, `src/host-tools-ai.ts` | Modify | SE-04 | Yes | Calls evidence only after fresh-universe validation and reuses fetched primary bars |
| `apps/dsh-plugin/src/prompts/bybit-quant/v3.ts`, `background-loop-v4.ts`, `LOOP_SPEC-v5.md` | Create | SE-05 | Partial | Versioned instructions preserve candidate, research, risk and execution boundaries |
| `apps/dsh-plugin/src/host-runtime.ts`, `src/lib/ai-scheduler.ts` | Modify | SE-05 | Partial | Active prompts are switched to the versioned successors |
| `apps/dsh-plugin/test/ai-market.ts`, `test/integration.ts`, `test/ai-scheduler.ts` | Create/Modify | SE-06 | Yes | Evidence availability, no duplicate bars, prompt assertions and candidate boundary |
| `sdd/features/DEFINE_BYBIT_AI_QUANT.md` | Modify | SE-07 | Yes | Adds AT-036 and dashboard/AI decision boundary criteria |
| `sdd/reports/BUILD_REPORT_AI_STRATEGY_EVIDENCE.md` | Create | SE-08 | Yes | This verification receipt |

The shared worktree contains prior uncommitted changes, so these counts refer only to the scoped file manifest and do not describe the complete `git status`.

## Prompts Generated / Refactored

| Inventory | Path | Type | Builder / review | Result | Verification |
|---|---|---|---|---|---|
| LP-001 | `apps/dsh-plugin/src/prompts/bybit-quant/v3.ts` | one-shot | Prompt-builder rules were reviewed; a compiled builder receipt and independent model evaluation were not recorded | Implemented; gate incomplete | Plugin integration assertions pass; independent fresh/not-ready/unavailable case review remains open |
| LP-002 | `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v4.ts`; `LOOP_SPEC-v5.md` | loop | Loop-builder rules were reviewed; a per-stage builder receipt and independent model evaluation were not recorded | Implemented; gate incomplete | Scheduler assertions pass; independent candidate-choice/abstention review remains open |

`LLM Prompts: true` in the parent DEFINE. The code assertions verify wording and tool boundaries; they do not prove that the model follows them reliably. No profitability ground truth or independent strategy-quality evaluation exists.

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | Architecture book vs. current evidence bridge | The architecture requires validated strategy selection, portfolio/risk, Nautilus execution, exchange reconciliation and restart recovery; this slice only supplies read-only research evidence after AI candidate selection. | Keep the feature slice narrow; full acceptance remains open | Evidence is explicitly research-only; no execution or deployment eligibility is inferred |
| 2 | Existing shared worktree | Many files are already modified or untracked from prior work. | Preserve all existing work | No cleanup, reset, commit or push |
| 3 | LLM prompt gate | Runtime prompts have deterministic assertions but lack independent model evaluation and complete prompt-evaluation receipts. | Unresolved; do not mark Build complete | Recorded as a blocker below |

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Strategy evidence + API | `pnpm run python:test` | Pass | 438 passed, 11 dependency/deprecation warnings |
| Python quality | `pnpm run python:lint` | Pass | Ruff checks passed; 98 files already formatted |
| Python types | `pnpm run python:typecheck` | Pass | Pyright: 0 errors, 0 warnings |
| DSH plugin | `pnpm --dir apps/dsh-plugin run verify` | Pass (existing worktree receipt) | Exit 0; build, lint, source/test type checks, plugin tests and bundle check; existing lint warnings |
| Monorepo | `pnpm exec nx show projects` and `nx show project quant-engine --json` | Pass | 9 projects; engine edges include quant-data, quant-risk, quant-execution, quant-portfolio and quant-strategies |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `CI=1 NX_DAEMON=false pnpm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green for the repository's configured gate |
| **Evidence** | Build, lint, typecheck, DSH unit tests, bundle check, generated SDK check/tests and tooling checks completed successfully. This gate is narrower than the complete product acceptance in DEFINE. |

### Manual UX Receipt

N/A for this API/data-flow acceptance slice. The dashboard visual and display-only review is recorded separately in `sdd/reports/BUILD_REPORT_AI_DECISION_UI_BOUNDARY.md`; it is not evidence of trading readiness.

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | `pnpm run python:lint` and root gate | Pass | Ruff passed; Oxlint existing warnings are non-blocking |
| Typecheck | `pnpm run python:typecheck` and root gate | Pass | Pyright 0 errors; strict TypeScript checks passed |
| Tests | `pnpm run python:test` and root gate | Pass | 438 Python tests and DSH plugin suite passed |
| Build / Compile | Root gate and `pnpm --dir apps/dsh-plugin run verify` | Pass | Plugin build and Bundle consistency checks passed |
| Dependency scan | `pnpm run security:deps` | Pass with scope note | No known vulnerabilities; pip-audit skipped six editable Python distributions |
| SBOM | `pnpm run sbom && pnpm exec nx run quant-data:sbom` | Pass | TS SBOM: 200 npm components; Python SBOM target succeeded |
| Secret scan | `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | Pass | Final worktree scan after report creation; no leaks found |
| Whitespace | `git diff --check` and the report trailing-whitespace check | Pass | Both checks passed after report creation |

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-032 | Dashboard filters do not affect the AI candidate universe or simulated journal | Pass for the scoped DSH boundary | Plugin integration/render tests; user-facing receipt in `BUILD_REPORT_AI_DECISION_UI_BOUNDARY.md` |
| AT-033 | AI selects eligible symbols and simulated parameters or abstains independently of dashboard fields | Partial | Candidate and tool boundary are covered; this is not a validated live strategy or autonomous exchange execution loop |
| AT-034 | Dynamic universe is built from Bybit catalogue and ticker data without static fallback | Existing scoped implementation | Candidate-pool tests and UI report; this evidence bridge consumes only a revalidated fresh subset |
| AT-035 | Discovery failure fails closed without a static symbol fallback | Existing scoped implementation | Candidate-pool and integration tests; stale/empty strategy evidence is separately explicit |
| AT-036 | `quant_brief` attaches bounded research-only Python family output for a fresh AI-selected symbol and fails explicitly when evidence is unavailable | Pass for this contract slice | `test_strategy_evidence_api.py`, `test_service.py`, plugin `test/ai-market.ts` and integration tests; 438 Python tests and root gate pass |

## Advisor Ledger

None — no formal external prompt or strategy-quality review was executed for this slice.

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | The Python quality scan skips editable workspace distributions | Kept the limitation explicit; no claim that those distributions were independently audited by pip-audit | Dependency status is not a complete upstream package audit |
| 2 | Prompt assertions do not establish model behavior | Kept the prompt gate incomplete and retained the independent evaluation blocker | Build remains blocked; no strategy approval or profitability claim |

## Deviations from Design

None. The implementation preserves the design boundary: Python results cannot choose a symbol, approve a strategy, set portfolio exposure, override risk, or authorize exchange execution.

## Blockers

| Blocker | Required Action | Owner |
|---|---|---|
| LP-001 / LP-002 independent prompt evaluation receipts are missing | Evaluate fresh, stale/not-ready, unavailable, candidate-choice and abstention cases with the configured model; record actual outcomes before marking the prompt gate complete | Feature owner |
| Full architecture acceptance remains incomplete | Complete the independent engine/data path, validated strategy and portfolio pipeline, Nautilus-only execution, account/order reconciliation, emergency stop and restart recovery gates before claiming unattended trading | Future implementation |

## Final Status

### Overall: BLOCKED

- [x] Scoped implementation workstreams completed
- [x] Incremental verification recorded
- [x] Verify Gate green (`CI=1 NX_DAEMON=false pnpm run verify`, exit 0)
- [x] Complementary Python, SDK, SBOM and dependency checks pass, with limitations recorded
- [x] AT-036 contract behavior verified in tests
- [ ] LLM prompt receipts and independent model evaluation complete
- [x] Drift decisions recorded
- [x] Advisor findings disposed; no formal external review was claimed
- [ ] No unresolved blocker
- [x] No TODO/FIXME used as a substitute for this scope
