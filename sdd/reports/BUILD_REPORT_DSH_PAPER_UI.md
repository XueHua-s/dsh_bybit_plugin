# BUILD REPORT: DSH native internal-paper Client

> Local UI implementation and executable evidence for manifest14–17,29. Installed browser/authentication and aggregate release acceptance are separate and pending.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | DSH_PAPER_UI, scoped part of DSH_PAPER |
| **Date** | 2026-11-17 |
| **Author** | dsh_paper_ui_build / SDD Build by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **DESIGN** | `sdd/features/DESIGN_DSH_PAPER.md` |
| **Status** | In Progress — assigned UI files implemented and locally verified; integrated/installed acceptance pending |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | Five assigned files:14–17,29 of the34-file design |
| Cross-file coupling | Medium: injected React card, generated PaperStatus, type-only Host result aliases, built Client registration |
| Security surface | Presentation of scoped Host results; same-origin demand requests; no direct Python/exchange/capability access |
| LLM prompt items | None assigned; LP-001/002 belong to Host owners |
| Independent volume | UI files have exclusive ownership; Host contract coordinated before implementation |
| Context-rot risk | Bounded five-file slice; full Brainstorm/Define/design read before changes |
| Runtime capabilities | Sequential default inside this delegated worker; parent coordinates independent implementers/review |

**Recommendation:** Sequential default within the UI slice, using the settled Host envelope and no shared-file refactor.

**User decision:** Parent delegated this slice under the repository's model-role rules and explicitly sent GO after prerequisite shutdown CI and design review. No additional user mode choice is invented here; project-level mode/release decisions remain parent-owned.

**Pre-build review:** Independent revised-design ACCEPT in `sdd/reviews/REVIEW_DSH_PAPER_DESIGN_2026-11-17.md`; source receipt read. Parent supplied prerequisite shutdown-CI clearance. This worker did not independently inspect remote CI.

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** |5/5 assigned files; full34-file manifest not owned or certified here |
| **Files Created** |3 |
| **Files Modified** |2 |
| **Files Deleted** |0 |
| **Verification Commands Run** |11 command invocations, including one initial test-harness failure corrected below; source-cap/read-only inspection additional |
| **Verify Gate** | Not run here; aggregate `pnpm run verify` and installed-auth receipt remain parent-owned |
| **Execution Mode** | Sequential default within delegated UI slice |

The card always identifies native synthetic internal paper, its `quant-engine-paper` source, no exchange connection, and separation from legacy paper/AI books and Linear Testnet. It starts unqueried and offers explicit Check/Start/Stop through the exact Host route. The card stores only validated safe context/status fields; arbitrary response strings and transport errors are never displayed.

One synchronous request owner prevents same-turn duplicate clicks and concurrent controls. No automatic query, polling or mutation retry is added. Idle/ready:false enables first Start; running or protected with a live native process allows Stop independently of readiness. Missing/unavailable/uncertain/inconsistent status disables mutations. Unmount aborts its owned HTTP request and never sends Stop. A later successful response with a different session fails closed until remount.

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---:|---|---|---|---|---|
|1 |14 | Create `apps/dsh-plugin/src/client-paper.ts` | UI worker | Complete locally | `node apps/dsh-plugin/test/client-paper.ts`; source typecheck | exit0; demand-only effects, scope checks, actions, uncertainty and abort |
|2 |15 | Mount independent card in `apps/dsh-plugin/src/client.ts` | UI worker | Complete locally | Plugin build; real React SSR; client bundle smoke | all exit0; existing registration retained;499 lines |
|3 |16 | Create `apps/dsh-plugin/test/client-paper.ts` | UI worker | Complete locally | Node effects test; test typecheck; targeted lint | final exit0; real card effects with injected fetch and stable hook slots |
|4 |17 | Extend `apps/dsh-plugin/test/render.ts` | UI worker | Complete locally | `node apps/dsh-plugin/test/render.ts` | exit0; real React19 SSR initial native identity and disabled mutations |
|5 |29 | Create this report | UI worker | Complete locally | Read against Build report template/checklist | Assigned files/evidence and pending gates distinguished |

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `apps/dsh-plugin/src/client-paper.ts` | Create |14 | Yes |130 lines; generated/Host types; no runtime Host import |
| `apps/dsh-plugin/src/client.ts` | Modify |15 | Yes |499 lines; minimal import/factory/mount plus obsolete comment correction |
| `apps/dsh-plugin/test/client-paper.ts` | Create |16 | Yes |212 lines; executable effects and meaningful request-count/state assertions |
| `apps/dsh-plugin/test/render.ts` | Modify |17 | Yes |197 lines; real React SSR; effects explicitly excluded |
| `sdd/reports/BUILD_REPORT_DSH_PAPER_UI.md` | Create |29 | Yes |No aggregate/native/installed success inferred |

## Prompts Generated / Refactored

None in the UI assignment. Product `LLM Prompts:true` and LP-001/002 remain in the design; Host owner supplies their receipts. User-visible card wording is ordinary UI text, with no model provider, prompt, runtime loop or generated algorithm.

## Drift Detected

No material drift detected. Host exported `PaperStatusResult`/`PaperMutationResult` aliases as coordinated; failures expose fixed source/environment/synthetic/configured/control_enabled and no session field. UI binds successful `data.session_id`, preserving that binding across failures. The existing499-line Client stays within the500-line constraint without structural refactoring.

## Verification Results

### Incremental Verification

Commands were run from the repository root unless the package filter selects the project.

| Task | Actual Command / Method | Exit / Result | Evidence |
|---|---|---|---|
| Initial effect test | `node apps/dsh-plugin/test/client-paper.ts` |1 / Fail | Harness checked Start before the Response.json stream task completed; requirement remained unchanged |
| Initial test types | `pnpm --filter @bybit-quant/dsh-plugin run typecheck:tests` |0 / Pass | Strict test compilation |
| Initial lint | `pnpm exec oxlint apps/dsh-plugin/src/client-paper.ts apps/dsh-plugin/test/client-paper.ts apps/dsh-plugin/test/render.ts` |0 / warnings | Three local shadow-name warnings; renamed before final lint |
| Initial whitespace | `git diff --check -- apps/dsh-plugin/src/client.ts apps/dsh-plugin/src/client-paper.ts apps/dsh-plugin/test/client-paper.ts apps/dsh-plugin/test/render.ts` |0 / Pass | Existing tracked-file diff; newly created file contents separately inspected |
| Corrected effect test | `node apps/dsh-plugin/test/client-paper.ts` |0 / Pass | Harness now yields to Response.json I/O with setImmediate before checking dependent state |
| Build | `pnpm --filter @bybit-quant/dsh-plugin run build` |0 / Pass | tsdown built Client and Host; coordinated with Host owner to avoid concurrent dist writes |
| Real SSR | `node apps/dsh-plugin/test/render.ts` |0 / Pass | Real React19 populated/empty/failed/loading render; native identity and disabled Start/Stop |
| Bundle registration | `node apps/dsh-plugin/test/client.ts` |0 / Pass | Two registrations,84 dictionary keys |
| Source types | `pnpm --filter @bybit-quant/dsh-plugin run typecheck` |0 / Pass | Strict source compilation |
| Final lint | `pnpm exec oxlint apps/dsh-plugin/src/client-paper.ts apps/dsh-plugin/src/client.ts apps/dsh-plugin/test/client-paper.ts apps/dsh-plugin/test/render.ts` |0 / Pass | No output/warnings |
| Final test types | `pnpm --filter @bybit-quant/dsh-plugin run typecheck:tests` |0 / Pass | Corrected harness and SSR tests compile |

Additional `wc -l` verified130/499/212/197 source/test lines. Targeted `rg` found no `any`, timers, Authorization, browser storage or wallet/equity fields in the new card/test; only the allowlisted test-result console line matched the inspected terms. No actual credentials, `.env` or managed profile was read or modified. No dependency install/change, Git mutation, exchange call or native service launch occurred in this UI assignment.

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `pnpm run verify` from DEFINE |
| **Exit / Result** | Not run by this worker |
| **Status** | Inconclusive here; parent owns aggregate execution/receipt |
| **Evidence** | Local checks above cannot certify full AT-010–031 or installed authentication |

### Manual UX Receipt

N/A to DEFINE's test-kind gate. Actual installed DSH browser/owner-auth interaction is a separate required design acceptance item and remains pending under the parent. No human receipt or browser interaction is fabricated from SSR/effect tests.

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | Final targeted oxlint above | Pass | exit0, no warnings |
| Typecheck | Source and test typecheck above | Pass | both final exit0 |
| Tests | Effects, real SSR, bundle registration | Pass locally | All final exit0; mocks are not installed-browser evidence |
| Build / Compile | Project tsdown build | Pass | exit0 |

## Acceptance Test Verification

| ID / Scenario | Status | Evidence |
|---|---|---|
| AT-002, assigned TS strict/source cap | Pass locally | Strict source/tests and all four source/test files≤500 lines |
| AT-016, UI environment identity | Pass locally, product acceptance partial | Fixed source/internal_paper/synthetic context; visible native/legacy/Testnet distinction; mismatched context/session fails closed |
| AT-022, Stop disclosure | Pass locally, full emergency acceptance open | Protected/unready native-alive Stop works; stopping not completed; no flatten claim |
| AT-028, native dashboard increment | Pass locally, installed acceptance pending | Actual card render/effects; no claim about remaining full dashboard views |
| Initial and pending UX | Pass locally |0 mount requests; explicit GET only; same-turn click deduplicated; all conflicting controls disabled while pending |
| Lifecycle action table | Pass locally | Idle/ready:false Start; protected/running native-alive Stop; stopped/protected-dead/inconsistent states fail closed; control opt-in respected |
| Uncertain/unavailable recovery | Pass locally | Clear actionable stale state; literal outcome_uncertain; manual GET recovery; no automatic retry/poll |
| Unmount ownership | Pass locally | Signal aborted; late response causes0 closed-card state writes; no Stop request |
| Installed carrier auth/origin/non-owner denial | Pending | Parent/reviewer-owned physical DSH/browser receipt |
| Native/process/whole-product acceptance | Not evaluated here | Other manifest owners and parent gates |

## Advisor Ledger

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| R3 | Pre-build design | Readiness is not lifecycle permission | LOW | APPLIED | Idle ready:false Start and protected native-alive Stop both exercised by actual effect tests |

Post-build independent implementation review is parent-owned and pending. No independent ACCEPT is claimed by this implementer.

Scoped software-design-philosophy self-assessment: **10/10,8/8 diagnostics supported; failed rows:none**. One card owns presentation/request lifecycle; its factory exposes only injected React. Host/SDK types keep protocol authority outside the browser. Interface comments state safe consumption, lifecycle permission and abort ownership. Native/source/legacy labels make boundaries visible. Coordinated types and the minimal mount limit change amplification. Design discussion and this deliberate pre-build/interface review cover the review/investment diagnostics. This local self-assessment does not raise the integrated boundary's accepted score; independent implementation review and real gates remain required.

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
|1 | Initial hook harness awaited microtasks but not stream I/O | Await one setImmediate task before dependent checks | One initial test exit1; implementation/action criterion unchanged; corrected run exit0 |
|2 | Three shadow-name lint warnings | Rename local search parameters | Final targeted lint clean |

## Deviations from Design

None. Additional browser-side fixed-context/consumed-field validation and session-change rejection enforce the design's valid scoped-status prerequisite; no alternative service DTO, capability route or execution path was introduced.

## Blockers

| Remaining acceptance item | Required Action | Owner |
|---|---|---|
| Installed browser/auth receipt | Exercise actual owner success and unauth/cross-origin/non-owner refusal using supported isolated DSH lifecycle | Parent / independent reviewer |
| Aggregate gates/review | Run final integrated Verify Gate, required security/SBOM/process gates and independent review | Parent / assigned owners |

## Final Status

### Overall: IN PROGRESS

- [x] Assigned File Manifest tasks14–17,29 completed
- [x] Incremental verification recorded
- [ ] Aggregate Verify Gate green receipt attached by parent
- [x] Assigned complementary checks pass
- [x] Local UI acceptance scenarios verified with honest limits
- [ ] Whole-slice installed/native/product acceptance verified by responsible owners
- [x] No new LLM prompt item in UI scope; existing inventory receipts assigned to Host
- [x] Drift decisions recorded
- [x] Applicable pre-build R3 finding applied
- [ ] Independent post-build review and installed receipt complete
- [x] No TODO/FIXME used as unfinished implementation

Assigned implementation is ready for parent integration and independent review. This report deliberately has no completed-build handoff footer while the aggregate and installed acceptance remain open.
