# BUILD REPORT: TypeScript Exchange Mutation Closure

> Auditable bounded cutover for the TypeScript Bybit writer removal. The overall product remains PARTIAL.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | TS_MUTATION_CLOSURE |
| **Date** | 2026-11-19 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **DESIGN** | `sdd/features/DESIGN_TS_MUTATION_CLOSURE.md` |
| **Status** | Complete for bounded cutover; product PARTIAL |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 30, including this report and regenerated tracked TypeScript SBOM |
| Cross-file coupling | High: Host tools, read-only client, prompt, panel contract, Bundle scan, tests and bilingual docs must agree |
| Security surface | Exchange mutation boundary, environment-scoped reads, OAuth configuration and prompt trust boundary |
| LLM prompt items | LP-001, one versioned one-shot system section |
| Independent volume | Serial execution was selected because the execution contract crosses source, UI, Bundle and docs |
| Context-rot risk | Low in default mode with incremental checks |
| Runtime capabilities | Default mode; no worker delegation was required |

**Recommendation:** default serial mode because the mutation boundary and prompt/UI contract are coupled.

**User decision:** unattended work was explicitly authorized and proceeded in default serial mode.

**Pre-build review:** yes. The execution-cutover review recommended removing the alternate TypeScript writer; that finding was applied.

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 30/30 bounded manifest items |
| **Files Created** | 3 |
| **Files Modified** | 27 |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 15 unique checks; the repository gate was rerun after fixes |
| **Verify Gate** | Green (`pnpm run verify`, exit 0) |
| **Execution Mode** | default |

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---|---|---|---|---|---|
| 1 | 1–4 | Remove TypeScript mutation transport, methods and send path | direct | Complete | root Verify Gate; cutover matrix | named signed GET reads remain; no TypeScript order writer |
| 2 | 5 | Register versioned preview-only system prompt LP-001 | direct | Complete | integration/unit tests | prompt receipt below |
| 3 | 6–11, 24 | Align Host panel, client contract, readiness card and config | direct | Complete | root Verify Gate; SSR render | execution unavailable, account unknown, no background loop |
| 4 | 12–15 | Remove stale order-sending claims from tool descriptions | direct | Complete | source/docs scan | active send-enable claims removed |
| 5 | 16–18, 29 | Add mutation matrix and include it in the Nx unit target | direct | Complete | `pnpm --filter @bybit-quant/dsh-plugin exec node test/trade-cutover.ts` | 98 passed; no exchange mutation request |
| 6 | 19 | Scan packed Bundle for mutation markers | direct | Complete | `pnpm --filter @bybit-quant/dsh-plugin bundle:check` | exit 0; 27 JavaScript files scanned |
| 7 | 20–23 | Align Bundle detail pages and bilingual READMEs | direct | Complete | diff check; claim scan | AI simulation and unavailable writes described consistently |
| 8 | 25 | Keep order metrics empty without an execution writer | direct | Complete | cutover matrix | read-only realtime order query is not counted as an order event |
| 9 | 26–27 | Preserve OAuth isolation and render tests | direct | Complete | root unit gate | OAuth tests and readiness/UI assertions pass |
| 10 | 28, 30 | Record evidence and regenerate tracked SBOM | direct | Complete | report reread; SBOM commands | npm SBOM has 200 components; Python SBOM target exits 0 |

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `apps/dsh-plugin/src/lib/bybit.ts` | Modify | 1 | Yes | GET-only private client; removed mutation methods |
| `apps/dsh-plugin/src/lib/bybit-types.ts` | Modify | 2 | Yes | Removed mutation-only input type |
| `apps/dsh-plugin/src/host-tools-trade.ts` | Modify | 3 | Yes | Preview retained; send intent unavailable before network |
| `apps/dsh-plugin/src/host-runtime.ts` | Modify | 4 | Yes | Registered V2 prompt and removed obsolete execution guards |
| `apps/dsh-plugin/src/prompts/bybit-quant/v2.ts` | Create | 5 | Yes | Versioned prompt describes the current capability boundary |
| `apps/dsh-plugin/src/host-panel.ts` | Modify | 6 | Yes | Reports unavailable writer and non-running background loop |
| `apps/dsh-plugin/src/client-types.ts` | Modify | 7 | Yes | Matches the readiness contract |
| `apps/dsh-plugin/src/client.ts` | Modify | 8 | Yes | Displays unavailable exchange writes |
| `apps/dsh-plugin/src/client-assets.ts` | Modify | 9 | Yes | Chinese/English simulation and readiness copy |
| `apps/dsh-plugin/src/lib/host-config.ts` | Modify | 10 | Yes | Removed ineffective write switches |
| `apps/dsh-plugin/cordis.patch.yml` | Modify | 11 | Yes | Removed stale order-enable defaults |
| `apps/dsh-plugin/src/host-tools-account.ts` | Modify | 12 | Yes | Removed stale switch claim |
| `apps/dsh-plugin/src/host-tools-watchlist.ts` | Modify | 13 | Yes | Removed stale switch claim |
| `apps/dsh-plugin/src/host-tools-ai.ts` | Modify | 14 | Yes | Removed stale switch claim |
| `apps/dsh-plugin/src/host-tools-backtest.ts` | Modify | 15 | Yes | Removed real-order implication |
| `apps/dsh-plugin/test/trade-cutover.ts` | Create | 16 | Yes | 98 denial/read-only checks |
| `apps/dsh-plugin/test/integration.ts` | Modify | 17 | Yes | Prompt and tool contract assertions |
| `apps/dsh-plugin/package.json` | Modify | 18 | Yes | Includes cutover test in unit script |
| `apps/dsh-plugin/scripts/check-bundle.ts` | Modify | 19 | Yes | Scans extracted Bundle for writer markers |
| `apps/dsh-plugin/docs/DETAIL.md` | Modify | 20 | Yes | Preview-only exchange behavior documented |
| `docs/DETAIL.md` | Modify | 21 | Yes | Synced AI simulation and conversation-triggered wording |
| `README.md` | Modify | 22 | Yes | Labels AI decisions/positions as simulated |
| `README.zh-CN.md` | Modify | 23 | Yes | Labels AI decisions/positions as simulated |
| `apps/dsh-plugin/src/client-readiness.ts` | Modify | 24 | Yes | Shows authority/account/automation as separate facts |
| `apps/dsh-plugin/src/lib/monitor.ts` | Modify | 25 | Yes | Leaves real-order metrics empty without execution events |
| `apps/dsh-plugin/test/oauth.ts` | Modify | 26 | Yes | Removes obsolete live-write config expectation |
| `apps/dsh-plugin/test/render.ts` | Modify | 27 | Yes | Tests visible simulation/readiness wording |
| `sdd/reports/BUILD_REPORT_TS_MUTATION_CLOSURE.md` | Create | 28 | Yes | This evidence report |
| `apps/dsh-plugin/project.json` | Modify | 29 | Yes | Includes cutover regression in root Verify Gate |
| `sbom.cdx.json` | Modify | 30 | Yes | Regenerated tracked npm inventory; dependency graph unchanged |

## Prompts Generated / Refactored

| Inventory | Path / version | Type | Builder | Result | Verification |
|---|---|---|---|---|---|
| LP-001 | `apps/dsh-plugin/src/prompts/bybit-quant/v2.ts` / V2 | One-shot system section | `sdd-prompt-builder v2.2.0` | Accepted against the design contract | Integration assertions and root unit gate pass |

The prompt states that exchange writes are unavailable, previews and simulated state must remain distinct, OAuth and API keys do not grant writes, and external text is untrusted. Missing account/reconciliation facts are reported as unknown; the fallback for exchange-order requests is a local preview. No provider, model, or new authority was introduced.

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | Native execution acceptance AT-014 | Close the alternate writer before Nautilus owns authenticated Testnet execution | Approved bounded deviation | Keep AT-014 pending; do not reintroduce TypeScript REST writes |
| 2 | Existing UI/docs | Prior language implied flags could enable real orders or that the AI workflow ran persistently | Approved correction | Removed ineffective switches from behavior; clarified simulation and conversation-triggered use |
| 3 | `apps/dsh-plugin/project.json` | The new cutover test was absent from the Nx target used by the repository gate | Approved bounded build correction | Added manifest item 29 and wired the test into the gate |
| 4 | `sbom.cdx.json` | Required verification artifact needed regeneration; its dependency graph did not change | Approved evidence update | Added manifest item 30; regenerated TypeScript SBOM |

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Repository Verify Gate | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` | Pass on rerun | exit 0; build, lint, strict types, unit tests, Bundle scan, SDK and tooling gates |
| TypeScript test types | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run typecheck:tests` | Pass | exit 0 |
| Cutover matrix | `pnpm --filter @bybit-quant/dsh-plugin exec node test/trade-cutover.ts` | Pass | 98 passed; no mutation request |
| Bundle scan | `pnpm --filter @bybit-quant/dsh-plugin bundle:check` | Pass | exit 0; 27 packed JS files and no exchange writer markers |
| Nx discovery | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx show projects` | Pass | seven independent projects discovered |
| Python lint/type/tests | `pnpm run python:lint && pnpm run python:typecheck && pnpm run python:test` | Pass | Ruff clean; Pyright 0 errors; 289 tests passed |
| TypeScript SBOM | `pnpm run sbom` | Pass | exit 0; 200 npm components |
| Python SBOM | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx run quant-data:sbom` | Pass | exit 0; reproducible artifact unchanged |
| Dependency audit | `pnpm run security:deps` | Pass | no known third-party vulnerabilities; pip-audit skips four editable workspace packages |
| Git history secret scan | `gitleaks git --redact` | Pass | 20 commits scanned; no leaks |
| Working-tree secret scan | `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | Pass | 24.57 MB scanned; no leaks after repair |
| Stale-claim scan | targeted `rg` scan of source, Bundle output and current docs | Pass | only explanatory legacy-key mentions and the warning “cannot submit real orders” remain |
| Diff hygiene | `git diff --check` | Pass | exit 0; rerun after the final report update |
| Post-repair recheck | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify`; `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run typecheck:tests`; `pnpm --filter @bybit-quant/dsh-plugin exec node test/trade-cutover.ts`; `gitleaks git --redact`; `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .`; `git diff --check` | Pass | Exit 0 after restoring four files whose line endings were damaged by a cleanup command; 98 cutover checks; no leaks; no whitespace errors |
| Post-UX clarity recheck | `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify`; `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run typecheck:tests`; `pnpm --filter @bybit-quant/dsh-plugin exec node test/trade-cutover.ts`; `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run bundle:check`; `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .`; `git diff --check` | Pass | Exit 0 after removing the redundant Mainnet approval-card row; SSR explicitly says exchange writes are unavailable; 98 cutover checks; no leaks |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `pnpm run verify` |
| **Exit / Result** | exit 0 after correcting the render assertion and Nx test target |
| **Status** | Green for the repository-defined local gate |
| **Evidence** | Plugin build/lint/typecheck/unit/bundle, SDK generation check/test and tooling checks passed |

### Manual UX Receipt

N/A for the automated Verify Gate. The review at `sdd/reviews/UX_REVIEW_BYBIT_AI_QUANT_2026-11-19.md` found the rebuilt SSR panel readable for this slice. It also observed that the active installed Harness still runs the older Bundle without the readiness card. Installed-browser acceptance is pending and is not claimed as passed.

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | included in Verify Gate | Pass with existing non-blocking warnings | exit 0 |
| Typecheck | Verify Gate and `pnpm run typecheck:tests` | Pass | exit 0 |
| Tests | root TS/SDK/tooling plus Python | Pass | 98 cutover checks; 289 Python tests |
| Build / Compile | root build and SBOM generation | Pass | exit 0 |

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-004 | Denied exchange intent cannot reach an order request | Pass for this TypeScript path | 98-case matrix across actions, environments and legacy flags; GET-only fetch assertion |
| AT-009 | Documentation describes verified behavior | Pass for changed docs | bilingual detail pages and READMEs state simulation and unavailable exchange writes |
| AT-014 | Nautilus is sole exchange writer for authorized live intent | Pending | Authenticated Testnet writer, admission, durable IDs and reconciliation remain unimplemented |
| AT-016 | Environment-separated read credentials | Pass for credential isolation in this slice | OAuth/config tests pass; no Mainnet sub-account was selected, and full ledger isolation is not claimed |
| AT-028 | Dashboard makes execution authority visible across the required views | Partial | Readiness-card and simulation-label SSR assertions pass; full seven-view dashboard and active installed Bundle acceptance remain incomplete |
| Product completion | Full autonomous platform | PARTIAL | AT-010–031 and the original-scope audit retain unimplemented or unverified items |

## Advisor Ledger

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| 1 | pre-build | Close TypeScript direct REST mutation before the native cutover | HIGH | APPLIED | writer removal and 98-case matrix |
| 2 | post-build | Bundle scan passes, but current Plugin Manager update/rollback/state preservation is not evidenced | MEDIUM | APPLIED as a documented limitation | Bundle check passes; installed lifecycle acceptance remains pending |

## Design quality review

Software design philosophy score: 8/10. The read client hides signing and transport; the trade tool exposes a small preview contract; module boundaries and intent are documented. Remaining gaps are durable execution state and reconciliation outside a deep native execution module, and some Host-level status aggregation still crosses module boundaries. Reaching 10/10 requires a separate native execution/recovery design and a narrower Host adapter; this cutover does not invent that capability.

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | SSR render test expected the translation key `aiTitle`, while the real component renders translated text | Changed the assertion to require the visible simulated label | Resolved; gate green |
| 2 | Cutover regression was missing from the Nx target used by root Verify Gate | Added it to `apps/dsh-plugin/project.json` and the Design manifest | Resolved; 98 checks now run |
| 3 | Existing lint and Python deprecation warnings | Recorded without suppressing; commands exit 0 | No gate impact |
| 4 | Active Harness profile still contains the older Bundle | Left the active profile unchanged; recorded official lifecycle and installed-browser acceptance as pending | Product remains partial |

## Deviations from Design

| Deviation | User Decision | Reason | Impact |
|---|---|---|---|
| Added manifest item 29 for Nx test wiring and item 30 for tracked SBOM regeneration | Authorized bounded build corrections | The regression gate and required dependency inventory need explicit traceability | DESIGN now lists 30 items; no runtime architecture change |

## Blockers

These are remaining product blockers; none blocks completion of the bounded TypeScript writer cutover.

| Blocker | Required Action | Owner |
|---|---|---|
| Native authenticated Testnet execution, complete account/order admission, durable recovery, reconciliation and scheduler are not implemented | Create a separate Design/Build and keep TypeScript exchange writes closed | Future execution slice |
| The active Harness needs an official Plugin Manager install/upgrade in a disposable profile to validate the readiness card and state preservation | Run the official lifecycle flow and compare non-sensitive state hashes before/after | Release/operator |

## Final Status

### Overall: COMPLETE FOR BOUNDED TS MUTATION CLOSURE / PRODUCT PARTIAL

- [x] All bounded File Manifest tasks completed
- [x] Incremental verification recorded
- [x] Verify Gate green
- [x] Applicable complementary checks pass
- [x] Acceptance evidence recorded with AT-014 pending
- [x] LLM prompt receipt recorded
- [x] Drift decisions recorded
- [x] Advisor findings disposed
- [x] No TODO/FIXME used as unfinished implementation
- [ ] Full product acceptance AT-010–031

The bounded safety cutover is complete. The product remains PARTIAL until an independent engine owns authenticated Testnet execution, account/risk admission, unique order IDs, uncertain-order reconciliation, restart recovery, scheduling and the remaining original-scope acceptance tests.

## Next Step

Execute the **SDD Handoff by RDD**.
