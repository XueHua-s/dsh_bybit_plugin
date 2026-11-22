# BUILD REPORT: AI Background Decision Loop

> Implementation report for the default-off, simulation-only DSH background Agent loop

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | AI_BACKGROUND_LOOP |
| **Date** | 2026-11-19 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **DESIGN** | `sdd/features/DESIGN_AI_BACKGROUND_LOOP.md` |
| **Architecture source** | `/Users/litlesnow/.codex/attachments/886f3b36-5cab-4ba1-bb1c-7ef525af0e6e/pasted-text-1.txt` |
| **Status** | Blocked |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 10 scoped paths, including runtime, UI state, configuration, tests and prompts |
| Cross-file coupling | High: Host lifecycle, injected DSH Agent services, prompt/tool allow-list, config and panel state |
| Security surface | High: background model tools and exchange-adjacent data; exchange writes are explicitly excluded |
| LLM prompt items | BQP-01 conversation/background contract plus the loop prompt in `src/prompts/bybit-quant/background-loop.ts` |
| Independent volume | One scheduler and deterministic fake-Agent test suite |
| Context-rot risk | Medium; existing worktree contains broad unrelated uncommitted changes |
| Runtime capabilities | `default` execution available; no separate Ralph/Briefs execution was selected |

**Recommendation:** `default`, because the manifest is tightly coupled and all scoped changes were already present in one reviewable worktree.

**User decision:** This build only records verification of the existing `default`-mode worktree; no new mode selection was recorded in this turn.

**Pre-build review:** Not available as a formal external review. Existing scoped UI and strategy reports were used as local review evidence.

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 9/9 scoped implementation tasks |
| **Files Created** | 5 scoped files: 3 implementation/test files, the design file and this report |
| **Files Modified** | 10 scoped code/config/docs/prompt files (other worktree changes are not attributed here) |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 5 recorded commands (plugin verify, unit tests, repository verify, diff check, report whitespace check) |
| **Verify Gate** | Passed on the later workspace rerun; the earlier registry 404 is historical. Prompt receipts and full unattended trading acceptance remain incomplete. |
| **Execution Mode** | default |

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---|---|---|---|---|---|
| 1 | LOOP-01 | Add bounded scheduler lifecycle and allow-list in `apps/dsh-plugin/src/lib/ai-scheduler.ts` | direct | Complete | `npm --prefix apps/dsh-plugin run verify` | exit 0; scheduler tests cover default-off, environment fence, backoff, block and unload |
| 2 | LOOP-02 | Add fixed simulation-only background prompt | direct | Complete | plugin build and prompt review | exit 0; prompt forbids exchange writes, watchlist mutation and treats evidence as untrusted |
| 3 | LOOP-03 | Inject optional DSH Agent services and cleanup in Host runtime | direct | Complete | plugin typecheck and unit suite | exit 0; `ctx.effect()` disposes active loop |
| 4 | LOOP-04 | Keep dashboard filters observational and expose truthful loop state | direct | Complete | render/integration assertions in plugin unit suite | exit 0; panel reports simulated-only state and unavailable execution authority |
| 5 | LOOP-05 | Add default-off, bounded Testnet/internal-paper configuration | direct | Complete | plugin build/typecheck | exit 0; default false, interval clamped to 1 minute–24 hours |
| 6 | LOOP-06 | Add deterministic fake-Agent scheduler tests | direct | Complete | `npm --prefix apps/dsh-plugin run test:unit` | exit 0; all plugin unit tests passed |
| 7 | LOOP-07 | Register test target and test typecheck in package/Nx manifests | direct | Complete | plugin verify | exit 0; test typecheck now runs in `verify` |
| 8 | LOOP-08 | Update user-facing docs and product prompts | direct | Complete | plugin build/bundle check | exit 0; docs state simulation-only limits |
| 9 | LOOP-09 | Record SDD evidence and unresolved architecture limits | direct | Complete | `git diff --check` | exit 0; this report records the historical registry failure, successful rerun and remaining gaps |

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `apps/dsh-plugin/src/lib/ai-scheduler.ts` | Create | LOOP-01 | Yes | Single active Agent, allow-list, environment gate, backoff, block and disposal |
| `apps/dsh-plugin/src/prompts/bybit-quant/background-loop.ts` | Create | LOOP-02 | Yes | Fixed machine prompt for simulated decisions only |
| `apps/dsh-plugin/src/host-runtime.ts` | Modify | LOOP-03 | Yes | Optional `agents`/`agentDefaultModel` injection and cleanup |
| `apps/dsh-plugin/src/host-panel.ts` | Modify | LOOP-04 | Yes | Read-only loop state in panel/health payload |
| `apps/dsh-plugin/src/client-assets.ts` / `src/client-types.ts` | Modify | LOOP-04 | Yes | Bilingual truthful status labels and typed state |
| `apps/dsh-plugin/src/lib/host-config.ts` / `cordis.patch.yml` | Modify | LOOP-05 | Yes | Default-off configuration and interval bounds |
| `apps/dsh-plugin/test/ai-scheduler.ts` | Create | LOOP-06 | Yes | Deterministic lifecycle and failure tests |
| `apps/dsh-plugin/package.json` / `project.json` | Modify | LOOP-07 | Yes | Unit test registration and test typecheck in verify |
| `apps/dsh-plugin/docs/DETAIL.md` | Modify | LOOP-08 | Yes | Operation and limits are explicit |
| `apps/dsh-plugin/src/prompts/bybit-quant/v2.ts` | Modify | LOOP-08 | Yes | Dashboard filters are observational; AI selects eligible candidates or abstains |
| `sdd/features/DESIGN_AI_BACKGROUND_LOOP.md` | Create | LOOP-09 | Yes | LOOP_SPEC v2, manifest and verification contract |
| `sdd/reports/BUILD_REPORT_AI_BACKGROUND_LOOP.md` | Create | LOOP-09 | Yes | Build evidence and unresolved gates |

## Prompts Generated / Refactored

| Inventory | Path | Type | Builder / review | Result | Verification |
|---|---|---|---|---|---|
| BQP-01 | `apps/dsh-plugin/src/prompts/bybit-quant/v2.ts` | conversation/background contract | `sdd-prompt-builder` rules were reviewed, but the required compiled SDD input contract and independent eval receipt were not produced | Implemented and bounded in code; prompt receipt incomplete | plugin tests exit 0; SDD prompt receipt remains incomplete |
| Background loop | `apps/dsh-plugin/src/prompts/bybit-quant/background-loop.ts` | loop stage prompt | `sdd-loop-builder` rules and a LOOP_SPEC v2 were reviewed, but per-stage prompt contracts and independent eval receipts were not produced | Implemented with abstention, tool boundary, untrusted-evidence rules and a cycle-scoped simulated-journal receipt; prompt eval receipt remains incomplete | scheduler receipt/lifecycle tests exit 0; SDD loop eval receipt remains incomplete |

Because `LLM Prompts: true` in DEFINE, these are implementation checks only. They do not satisfy the SDD prompt gate's required prompt-builder/loop-builder receipts.

The loop's `whenIdle()` remains only an Agent-turn completion signal. The tool now supplies a separate cycle-scoped receipt after its simulated state-file write succeeds; the panel reports the latest cycle's decision count and persisted status. This receipt verifies the local simulated journal/book only, never exchange execution.

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | Architecture book vs. background loop | The architecture book requires a complete long-running quant data plane, execution, reconciliation and recovery; this increment only adds an opt-in simulated Agent wake-up loop. | Approved scoped implementation; full product acceptance remains open | Documented the negative scope in `DESIGN_AI_BACKGROUND_LOOP.md`, prompts and this report; no exchange execution was added |
| 2 | Existing worktree | Many unrelated files are already modified or untracked. | Preserve unrelated work | No reset, clean, commit or push; only scoped evidence was added |
| 3 | Runtime prompts vs. SDD prompt inventory contract | DEFINE says `LLM Prompts: true`; the current design inventory does not provide all compiled per-prompt contracts, per-stage prompt-builder receipts, or an independent decision-write verifier required by the SDD gate. | Unresolved; do not claim the prompt gate passed or silently revise the prompt specification | Recorded the missing artifacts as a blocker; existing prompts remain bounded and simulation-only |

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Scheduler and plugin | `npm --prefix apps/dsh-plugin run verify` | Pass | exit 0; build, lint, source typecheck, test typecheck, unit tests and bundle check passed |
| Plugin lint | included in verify (`oxlint .`) | Pass with warnings | exit 0; 4 non-blocking warnings in `host-panel.ts`, `test/ai.ts`, `test/integration.ts` |
| Initial repository gate | `pnpm run verify` | Historical failure | exit 1; dependency resolution returned `ERR_PNPM_FETCH_404` for `@deepseek-ai/dsh-desktop-host`; a later rerun passed |
| Whitespace | `git diff --check` | Pass | exit 0 |
| New report whitespace | `awk '/[[:blank:]]+$/ { print NR; bad=1 } END { exit bad }' sdd/reports/BUILD_REPORT_AI_BACKGROUND_LOOP.md` | Pass | exit 0; no trailing whitespace |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `pnpm run verify` |
| **Exit / Result** | Later workspace rerun: exit 0 |
| **Status** | Passed for the command gate; the SDD prompt receipt and product acceptance remain open |
| **Evidence** | The later `pnpm run verify` completed successfully after restoring the workspace root manifest and lockfile; the earlier registry failure remains a historical receipt. |

### Manual UX Receipt

N/A. No live Chrome/Bundle visual receipt was obtained in this build.

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | `npm --prefix apps/dsh-plugin run verify` | Pass with 4 warnings | exit 0 |
| Typecheck | plugin source and tests via same command | Pass | exit 0 |
| Tests | plugin unit suite via same command | Pass | exit 0; scheduler and existing tests passed |
| Build / Compile | plugin `tsdown` and bundle check via same command | Pass | exit 0 |

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| LOOP-AT-01 | Disabled/default or AI-track-disabled scheduler does not create an Agent | Pass | `test/ai-scheduler.ts`; exit 0 |
| LOOP-AT-02 | Demo/live environments are rejected and no timer is scheduled | Pass | `test/ai-scheduler.ts`; exit 0 |
| LOOP-AT-03 | Background allow-list excludes exchange, account, watchlist and paper-control writes | Pass | allow-list assertion and prompt review; exit 0 |
| LOOP-AT-04 | Only one Agent turn is active and unload cancels/awaits/disposes it | Pass | fake-Agent lifecycle tests; exit 0 |
| LOOP-AT-05 | Failures back off and terminally block after three consecutive failures | Pass | fake-Agent failure tests; exit 0 |
| AT-032 | Dashboard filters stay display-only | Pass for scoped plugin evidence | render/integration tests in plugin suite; architecture-wide acceptance remains open |
| AT-033 | AI chooses eligible symbols/parameters or abstains independently of dashboard filters | Partial | The prompt and tool boundary keep dashboard filters out and permit candidate selection/abstention; a complete all-market AI strategy-selection loop is not implemented |

## Advisor Ledger

None — no formal external review was executed.

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Initial root pnpm verify could not install the private/unpublished DSH host package from npm | Retained as historical failed evidence; a later workspace rerun passed after the root manifest and lockfile were restored | No current dependency-resolution blocker is known; keep the historical failure distinct from current results |
| 2 | Initial scheduler version could not prove that a completed Agent turn wrote a decision journal entry | Added a cycle-scoped receipt committed after the simulated journal write; the panel distinguishes missing receipt from abstention | Receipt behavior is unit-tested; full Host-tool-to-disk persistence failure injection remains unverified |
| 3 | SDD prompt gate requires compiled prompt contracts and per-stage eval receipts | Kept the implementation bounded and recorded the gap instead of claiming the prompt gate passed | Build remains blocked for the LLM prompt gate; the simulated-journal write receipt is now implemented |

## Deviations from Design

None beyond the explicitly recorded architecture-scope drift above.

## Blockers

| Blocker | Required Action | Owner |
|---|---|---|
| LLM prompt receipt is incomplete | Compile the BQP-01 and background-loop prompt contracts from the SDD inventory, run prompt-builder for each LLM stage, and record eval/verification receipts before marking the prompt gate complete | Feature owner |
| Architecture book's full unattended trading data plane remains incomplete | Implement and independently verify long-running engine, strategy selection, risk/execution authority, reconciliation and recovery before claiming unattended trading | Future feature work |

## Final Status

### Overall: BLOCKED

- [x] All scoped File Manifest tasks completed
- [x] Incremental verification recorded
- [x] Verify Gate green (later `pnpm run verify` rerun: exit 0)
- [x] Complementary plugin checks pass
- [x] Scoped acceptance tests verified
- [ ] LLM prompt receipts complete when required; implementation review is recorded but the required compiled receipts are missing
- [x] Drift decisions recorded
- [x] Advisor findings disposed when applicable
- [ ] No unresolved blocker
- [x] No TODO/FIXME used as unfinished implementation

The implementation is a default-off, Testnet/internal-paper, simulated-decision loop. It is not a complete unattended quantitative trading system and does not submit Testnet or Mainnet orders.

## Reverification update (2026-11-19)

The workspace gate was rerun after the report's original dependency-resolution attempt. `pnpm run verify` now exits 0, as do `pnpm run python:lint`, `pnpm run python:typecheck`, `pnpm run python:test` (405 passed), `pnpm run security:deps`, `gitleaks dir --redact --no-banner`, `pnpm run sbom`, and `nx show projects`. The historical registry 404 is retained above as a prior-run receipt. The loop remains simulated and default-off; this successful tooling gate does not grant Testnet or Mainnet order authority.

## Documentation correction update (2026-11-19)

The Bundle detail and root detail previously described `aiSymbols` as a fixed BTC/ETH starter list and said full-market discovery was not implemented. Both now match the shipped implementation: an empty allow-list performs bounded discovery from the complete Bybit Instrument Info catalogue plus ticker data; a saved/configured list only narrows that universe; the AI chooses up to four candidates for detailed evidence or abstains; chart filters remain display-only. The candidate gate is Trading status, USDT quote, supported Spot/linear contract type, valid quantity/price rules, at least USD 1 million turnover and at most 75 bps spread, capped at 30 ranked candidates.

Evidence for this update: `pnpm run verify` exit 0, `uv run --project python --locked pytest python/packages/quant-strategies/tests python/apps/quant-engine/tests/test_builtin_strategies.py python/apps/quant-engine/tests/test_strategy_registry.py -q` exit 0 with 63 passed, `git diff --check` exit 0, and fixed-symbol/stale-discovery searches return no matches in the two detail files. This is a documentation and evidence correction; it does not change the blocked prompt receipt, exchange execution, reconciliation, or unattended recovery status.

## Decision receipt hardening update (2026-11-20)

The scheduler's receipt key is the normalized symbol. A background cycle allows
at most one decision per symbol and four symbols total. A concurrent retry is
reported as pending; a later retry returns the original decision ID, status,
and persistence time without another journal write. Repeated commits return the
same receipt, and stale cycle IDs are rejected. Accounting is staged on a cloned
track; the shared AI track is replaced only after the atomic state-file write
succeeds. If persistence throws, the prior in-memory track is restored and the
reservation is released. The panel hint now explains that no receipt is not an
abstention.

Verification on this update: `pnpm --dir apps/dsh-plugin run verify` initially
failed on an assertion that omitted the internal reservation state; after
correcting the duplicate receipt shape and adding commit/stale-cycle coverage,
the same command exited 0. It ran build, lint (four pre-existing warnings in
`host-panel.ts`, `test/ai.ts`, and `test/integration.ts`), source/test typechecks,
unit tests, and bundle checks. `pnpm run verify` exited 0 for the workspace
gate. `git diff --check` exited 0 before the report edit; it is rerun below.
The scheduler receipt unit tests do not yet inject a disk failure through the
full Host tool-to-store path, so that specific integration fault case remains
unverified. The LLM prompt eval receipts and full architecture acceptance also
remain open; this change adds no exchange-order authority.

## Verification correction update (2026-11-20)

The final panel-render assertion fixture contained a duplicate
`readinessLoopBlocked` translation key, which caused the first post-change
plugin lint run to exit 1. The duplicate key was removed; no runtime behavior
changed. The corrected checks were rerun with these receipts:

- `pnpm --dir apps/dsh-plugin run verify` — exit 0 (build, lint with four
  existing warnings, source/test typechecks, unit tests, and bundle check).
- `CI=1 NX_DAEMON=false pnpm run verify` — exit 0 (workspace Nx build, lint,
  typechecks, unit tests, bundle/API checks, tooling checks).
- `git diff --check` — exit 0.

The full Host-tool-to-disk persistence failure injection, prompt eval receipts,
exchange execution, reconciliation, and recovery remain outside this scoped
implementation and are still blocked as described above.

## Strategy selector and final workspace verification update (2026-11-20)

The validated strategy-selection boundary was added as a separate research-only
slice. Its file manifest and receipts are recorded in
`sdd/reports/BUILD_REPORT_STRATEGY_SELECTION.md`; it does not grant execution
authority or complete the architecture book's unattended trading data plane.

Final receipts for the current workspace:

- `pnpm run verify` — exit 0.
- `pnpm run python:lint` — exit 0 after formatting the two new selector files.
- `pnpm run python:typecheck` — exit 0.
- `pnpm run python:test` — exit 0, 410 passed, 11 existing warnings.
- `pnpm exec nx show projects` — exit 0; eight applications/packages discovered.
- `pnpm run security:deps` — exit 0; no known npm or Python dependency vulnerabilities (editable Python distributions were skipped by `pip-audit`).
- `gitleaks dir --redact --no-banner` — exit 0; no leaks found in approximately 30.33 MB scanned.
- `pnpm run sbom` — exit 0; wrote the npm CycloneDX SBOM with 200 components.
- `pnpm exec nx run quant-data:sbom` — exit 0; Python SBOM target succeeded.
- `git diff --check` — exit 0.
- Hand-written source scan — exit 0; all scanned TypeScript/Python files are at
  most 500 lines.

These receipts validate compilation, tests, formatting and workspace discovery;
they do not change the remaining prompt-evaluation, exchange-execution,
reconciliation, recovery or full unattended-trading blockers.

## Current verification refresh (2026-11-20)

The workspace checks were rerun after the decision-receipt and strategy slices
were present in the shared worktree:

- `CI=1 NX_DAEMON=false pnpm run verify` — exit 0; build, lint, strict
  typechecks, unit tests, bundle/API checks and tooling checks passed.
- `pnpm run python:lint` — exit 0; Ruff check passed and 96 files were already
  formatted.
- `pnpm run python:typecheck` — exit 0; Pyright reported 0 errors, warnings or
  informations.
- `pnpm run python:test` — exit 0; 424 tests passed with 11 existing
  dependency/deprecation warnings.
- `NX_DAEMON=false pnpm exec nx show projects` — exit 0; nine projects were
  discovered, including `quant-strategies`, `quant-portfolio`, `quant-engine`
  and the DSH plugin.
- `git diff --check` — exit 0.

The refreshed receipts confirm the research and UI-boundary slices still build
and test together. They do not provide the missing independent model-quality
evaluation, native exchange execution, durable order/position reconciliation,
process recovery, or full unattended-trading acceptance.

## Lifecycle hardening update (2026-11-20)

The scheduler lifecycle was tightened and versioned as `LOOP_SPEC-v4.md`. The
monotonic 120-second default deadline now starts before `agents.create()` and
is shared by Agent creation and `whenIdle()`, so slow session creation cannot
extend the model-turn budget. Configured limits are clamped to 5 seconds–10
minutes. Creation/turn timeout requests abort or cancel the Agent; a handle that
arrives after a timed-out creation is cancelled and disposed before backoff may
resume. Idle and disposal waits use a bounded 10-second default (maximum 60
seconds). If cleanup cannot be confirmed, the scheduler clears its timer and
enters `blocked`, preventing overlapping Agents. Plugin unload also returns
after a bounded cleanup wait and records uncertainty.

The v3 machine prompt remains active; v4 changes the lifecycle contract and
does not grant exchange authority. A cancellation request is only a Host API
request. The fake-Agent tests prove scheduler fencing, but a real DSH Host
integration receipt is still required to establish that cancellation terminates
underlying work.

Verification receipts for this update:

| Command | Exit | Result |
|---|---:|---|
| `pnpm --dir apps/dsh-plugin run verify` | 0 | Build, lint (five non-blocking warnings), source/test typechecks, unit tests, and Bundle check passed. |
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | Workspace Nx build, lint, strict typechecks, DSH tests, Bundle/API checks and tooling checks passed. |
| `git diff --check` | 0 | No whitespace errors. |
| `wc -l apps/dsh-plugin/src/lib/ai-scheduler.ts apps/dsh-plugin/test/ai-scheduler.ts` | 0 | Scheduler 500 lines; scheduler tests 356 lines, within the hand-written source limit. |

The scheduler test suite covers a shared creation/turn deadline, timeout
cancellation, late-handle cleanup, no-overlap blocking when cleanup is
uncertain, bounded unload, backoff, and the existing receipt limits. It does
not establish model quality, market performance, exchange execution,
reconciliation, restart recovery, or Host cancellation semantics. The overall
Build status remains **BLOCKED**.

### Design review (software-design-philosophy)

Current score: **6.25/10** (5 of 8 quick-diagnostic checks pass for the
scheduler module). The loop's lifecycle and receipt invariants are centralized
in one describable scheduler module, and the design file documents its boundary.
The failed checks are:

| Diagnostic | Current gap | Change needed for 10/10 |
|---|---|---|
| Interface simpler than implementation | The internal scheduler factory accepts separate clock and timer injection hooks alongside runtime settings. | If the scheduler gains another consumer, group test-only clock/timer seams behind one private dependency object or factory so callers configure policy rather than timer mechanics. |
| Design discussion in review | No independent code/design review receipt is recorded for this lifecycle change. | Add a reviewer receipt before release and record any disposition. |
| 10–20% design-improvement evidence | This Build report has no time/process evidence to judge the ongoing design-investment practice. | Record the review/refinement step in the feature's Build workflow; do not infer it from green tests. |

These are design and process follow-ups; the just-run Verify Gate passes, while
Host cancellation behavior and prompt evaluation remain release blockers.

## 2026-11-22 complexity and Python gate refresh

The Agent service contract remains isolated in `ai-agent-services.ts`; the
scheduler is 448 lines and `paper_admission.py` is 498 lines after a small
import-boundary cleanup. Both remain below the repository's strict handwritten
source limit. The cleanup changed no runtime policy or execution authority.

Fresh receipts after this cleanup:

| Command | Exit | Result |
|---|---:|---|
| `pnpm run python:test` | 0 | 500 passed; 11 existing upstream/deprecation warnings. |
| `pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| `pnpm run python:lint` | 0 | Ruff check and format check passed. |
| `pnpm --dir apps/dsh-plugin run verify` | 0 | Build, lint (five non-blocking warnings), source/test typechecks, unit suites and packed Bundle checks passed. |
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | Workspace build, lint, typechecks, DSH unit tests, Bundle/API checks and tooling safety checks passed. |
| `git diff --check` | 0 | No whitespace errors. |

This refresh does not close prompt evaluation, durable lease/restart recovery,
Host-to-Python background deployment, Testnet exchange writes, reconciliation,
or Mainnet execution. Overall unattended quant-trading status remains
**PARTIAL/BLOCKED**.
