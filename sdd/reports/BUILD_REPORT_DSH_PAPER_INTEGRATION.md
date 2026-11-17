# BUILD REPORT: DSH native internal-paper integration

> Scoped integration and documentation receipt for Design manifest items 19–25. The full product, installed DSH authentication, browser acceptance and release state remain separate.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | DSH_PAPER, manifest 19–25 |
| **Date** | 2026-11-17 (Asia/Shanghai) |
| **Author** | integration/documentation owner / SDD Build by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **DESIGN** | `sdd/features/DESIGN_DSH_PAPER.md` |
| **Status** | In Progress — scoped integration checks pass; parent aggregate/release gates remain separate |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | Seven owned integration/documentation files, items 19–25 |
| Cross-file coupling | High: package scripts, Nx targets, CI order, opt-in settings and user-facing claims must agree |
| Security surface | Nonsecret Cordis defaults and documentation for the private capability boundary; no credential or managed-profile edits |
| LLM prompt items | Existing static Tool descriptions only; no new runtime loop or prompt |
| Independent volume | Broker, Host, UI, SDK and process owners supplied the frozen implementation and scoped reports |
| Runtime capabilities | Sequential default in this delegated slice; parent coordinates aggregate acceptance |

**Recommendation:** Sequential default integration keeps the command graph and safety wording consistent while avoiding source ownership overlap.

**User decision:** Parent delegated manifest items 19–25 and released the existing frozen implementation for integration. No new permission or mode decision was requested; no Git, credential or managed-profile mutation was performed.

**Pre-build review:** `sdd/reviews/REVIEW_DSH_PAPER_DESIGN_2026-11-17.md` records scoped design ACCEPT. Independent implementation review and installed owner/auth evidence remain parent/reviewer work.

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 7/7 scoped items inspected, integrated and verified |
| **Files Created** | 1 (this report) |
| **Files Modified** | 7 in this slice; `README.zh-CN.md` was brought to parity with the already modified English documentation |
| **Files Deleted** | 0 |
| **Verification Commands Run** | Multiple direct/static commands, including the root Verify command |
| **Verify Gate** | Green for the configured root `pnpm run verify`; parent still owns full Python/security/SBOM/release and installed gates |
| **Execution Mode** | Sequential default |

## Task Execution

| # | Manifest ID | Task | Status | Verification | Evidence |
|---:|---:|---|---|---|---|
| 1 | 19 | Wire package unit and uncached paper-process scripts | Complete | `pnpm --filter @bybit-quant/dsh-plugin test:paper-process` | Exit 0; locked uv sync and process receipt emitted |
| 2 | 20 | Mirror unit/process commands in Nx; process target uncached | Complete | `nx show projects`; `nx ...:test:paper-process --skip-nx-cache` | Seven projects discovered; four Nx tasks succeeded, process target uncached |
| 3 | 21 | Add blocking CI process step after install/verify | Complete | YAML/source review; process target run | Step is after `pnpm run verify`, before test/type and Python checks; network job remains separate/non-blocking |
| 4 | 22 | Add commented nonsecret paper settings to Cordis patch | Complete | Patch/source review; bundle check | Defaults remain Testnet/live-off; paper fields are commented opt-in values only |
| 5 | 23 | Document private broker, migrated temporary DB and cleanup limits | Complete | Runbook review; process E2E | Broker/FD modes, exact settings, no token fallback, uncertainty and cleanup limits match implementation |
| 6 | 24 | Document verified native DSH controls and remaining boundaries | Complete | README review; root Verify | English README links process receipt and preserves pending installed/browser/exchange boundaries |
| 7 | 25 | Keep Chinese documentation behavior/limits aligned | Complete | README diff/whitespace review; root Verify | Chinese README now describes five Tools, Check/Start/Stop card, broker and explicit remaining limits |

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `apps/dsh-plugin/package.json` | Modify | 19 | Yes | Unit command includes provider/Host/UI tests; explicit process script performs locked uv sync and invokes the built process script |
| `apps/dsh-plugin/project.json` | Modify | 20 | Yes | Unit command mirrors package script; `test:paper-process` uses `nx:run-commands`, depends on build, is `cache: false`, and runs serially |
| `.github/workflows/ci.yml` | Modify | 21 | Yes | Blocking process target follows `pnpm run verify`; public Testnet smoke remains a separate `continue-on-error` job |
| `apps/dsh-plugin/cordis.patch.yml` | Modify | 22 | Yes | Only commented nonsecret paper URL/session/socket/control examples were added |
| `docs/runbooks/paper-service.md` | Modify | 23 | Yes | Adds private broker recipe, supported DSH settings, five Tools/card boundary, cleanup and mutation503 uncertainty |
| `README.md` | Modify | 24 | Yes | Documents native-paper Tools/card, current process receipt and unresolved installed/product boundaries |
| `README.zh-CN.md` | Modify | 25 | Yes | Chinese behavior and limitation text matches English scope |
| `sdd/reports/BUILD_REPORT_DSH_PAPER_INTEGRATION.md` | Create | — | Yes | This scoped evidence receipt |

## Drift Detected

No material architecture or scope drift was found. The existing English README and runbook already described the integrated native-paper boundary, while the Chinese README still described a read-only panel and no DSH paper cutover. That documentation inconsistency was corrected without changing runtime behavior. The static Tool guidance remains the existing external DSH loop contract; no local model/provider or prompt stage was introduced.

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Project discovery | `pnpm exec nx show projects` | Pass (0) | Seven independent projects listed, including `@bybit-quant/dsh-plugin` |
| Build | `pnpm exec nx run @bybit-quant/dsh-plugin:build --skip-nx-cache` | Pass (0) | Host/Client bundle rebuilt |
| Plugin lint | `pnpm exec nx run @bybit-quant/dsh-plugin:lint --skip-nx-cache` | Pass (0) | No findings |
| Plugin source typecheck | `pnpm exec nx run @bybit-quant/dsh-plugin:typecheck --skip-nx-cache` | Pass (0) | Strict source types accepted |
| Plugin test typecheck | `pnpm exec nx run @bybit-quant/dsh-plugin:typecheck:tests --skip-nx-cache` | Pass (0) | All added/updated test types accepted |
| Unit tests | `pnpm exec nx run @bybit-quant/dsh-plugin:test:unit --skip-nx-cache` | Pass (0) | Existing plus provider/Host/UI paper regressions passed |
| Bundle | `pnpm exec nx run @bybit-quant/dsh-plugin:bundle:check --skip-nx-cache` | Pass (0) | Generated payload/export checks passed |
| Nx process E2E | `pnpm exec nx run @bybit-quant/dsh-plugin:test:paper-process --skip-nx-cache` | Pass (0) | Four Nx tasks succeeded; target was uncached |
| Package process E2E | `pnpm --filter @bybit-quant/dsh-plugin test:paper-process` | Pass (0) | Real receipt: 4 commands, 3 native fills, 1 risk rejection, injected post-dispatch503 uncertainty, protected restart, closed listeners, no capability disclosure |
| Root Verify Gate | `pnpm run verify` | Pass (0) | Build, lint, typecheck, unit, bundle, SDK, tooling and hook checks all passed |
| Documentation hygiene | `git diff --check -- .github/workflows/ci.yml apps/dsh-plugin/package.json apps/dsh-plugin/project.json apps/dsh-plugin/cordis.patch.yml docs/runbooks/paper-service.md README.md README.zh-CN.md` | Pass (0) | No whitespace errors |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test/build gate |
| **Command / Method** | `pnpm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green for the root configured Verify command |
| **Evidence** | Root command completed build, lint, TypeScript checks, plugin unit tests, bundle check, SDK generation/check/tests, tooling typecheck and hook tests. CI-only Python/security/SBOM/release checks and installed DSH lifecycle remain parent-owned. |

### Manual UX Receipt

N/A. No installed DSH profile or browser interaction was accessed by this integration owner.

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | Plugin Nx lint target | Pass | Exit 0 |
| Typecheck | Plugin source and test targets | Pass | Exit 0 |
| Tests | Plugin unit and process targets | Pass | Exit 0; process receipt recorded above |
| Build / Compile | Plugin build target | Pass | Exit 0 |
| YAML/JSON consistency | Read-back of CI, Cordis, package and project files; Nx execution | Pass | Targets load and execute; no managed profile was edited |

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-002 | Strict TypeScript/build and source integration | Pass (scoped) | Plugin build, lint, source/test typechecks and unit tests exit 0 |
| AT-003 | CI and verification command is discoverable and reproducible | Pass (scoped) | Nx discovery, package target, CI ordering and root Verify exit 0 |
| AT-010 | Host close does not own independent service lifetime | Pass (process) | Real process receipt reports `host_close_survived:true` |
| AT-016 | Fixed native-paper identity and control opt-in | Pass (scoped) | Cordis defaults commented/off; process receipt reports synthetic internal-paper and no capability disclosure |
| AT-027 / AT-028 | Five Tools and native-paper card are wired | Pass (local) / installed pending | Unit/SSR/Host tests and docs pass; physical owner/authenticated carrier and browser UX remain unverified |
| AT-031 | Full security/SBOM/release lifecycle | Parent-owned | This owner did not run or claim CI security/SBOM, official install/upgrade/uninstall or release acceptance |

## Advisor Ledger

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| 1 | Pre-build | Design review required the private broker to remain separate from legacy paper/exchange credentials and the process target to stay uncached | Medium | APPLIED | Cordis/runbook contain only nonsecret opt-in settings; project target sets `cache:false`; process receipt reports no capability disclosure |
| 2 | Pre-build | Mutation503 can follow durable side effects | Medium | APPLIED by SDK/process owners | README/runbook describe original-identity `outcome_uncertain` recovery and the E2E injects only a response substitution after a real 202 |
| 3 | Pre-build | Readiness does not grant lifecycle permission | Low | APPLIED by UI/Host owners | Docs describe Check/Start/Stop action boundary and do not claim automatic restart/cleanup |

## Issues Encountered

None in the final scoped integration run. The process target was run both through Nx and the package script; both completed with exit 0. No credentials, `.env`, user DB, DSH profile or exchange endpoint was accessed.

## Deviations from Design

None. The Chinese README parity correction is documentation-only and does not alter the design contract or runtime route.

## Blockers

| Blocker | Required Action | Owner |
|---|---|---|
| Installed DSH owner/auth and browser acceptance | Run supported Plugin Manager/profile lifecycle and capture authenticated/unauthenticated/cross-origin/non-owner evidence | Parent / independent reviewer |
| Full release acceptance | Run remaining Python, security, SBOM, source-cap, release and official lifecycle gates; update aggregate Verify Gate | Parent |

## Final Status

### Overall: IN PROGRESS

- [x] All manifest 19–25 tasks completed
- [x] Incremental verification recorded
- [x] Scoped root Verify command green
- [x] Complementary plugin checks pass
- [x] Documentation boundaries updated honestly in English and Chinese
- [x] Drift decisions recorded
- [x] Advisor findings reflected in integration/docs
- [ ] Installed DSH/browser acceptance complete
- [ ] Parent aggregate security/SBOM/release gates complete
- [x] No TODO/FIXME used as unfinished implementation

Parent should retain the final product status as PARTIAL until the outstanding installed and whole-product gates are independently evidenced.
