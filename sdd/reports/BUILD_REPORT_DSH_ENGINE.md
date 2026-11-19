# BUILD REPORT: DSH read-only engine integration

## Metadata

| Attribute | Value |
|---|---|
| Feature | DSH_ENGINE |
| Date | 2026-11-17 |
| Author | parent-delegated integration agent |
| BRAINSTORM | sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md |
| DEFINE | sdd/features/DEFINE_BYBIT_AI_QUANT.md |
| DESIGN | sdd/features/DESIGN_BYBIT_AI_QUANT.md; DESIGN_ENGINE_CLIENT.md; DESIGN_DSH_ENGINE.md |
| Status | In Progress — local implementation verified; aggregate gate/review parent-owned |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 14 source/config/test files plus design/report and generated SBOM |
| Cross-file coupling | Medium: Host runtime, generated SDK, route and independently displayed Client state |
| Security surface | Loopback destination, credentials isolation, Testnet fence, unload cancellation and deployment metadata |
| LLM prompt items | None; existing runtime prompts unchanged |
| Independent volume | Parent explicitly delegated SDK, integration and independent review |
| Context-rot risk | Controlled by written design and narrow ownership |
| Runtime capabilities | Parent-assigned parallel subtask |

Recommendation/decision: parent assigned implementation in this context under the existing user authorization. No new mode selection was invented. Pre-build formal review was not executed; independent post-build review is parent-assigned.

## Summary

Demand-driven read-only engine status/market tools and authenticated bridge views use generated SDK validation; no background service polling is introduced. The Client offers an explicit engine check without replacing REST candles/account/analysis. Non-Testnet Host environments fail closed. Engine facts explicitly distinguish market ingestion from unknown execution/reconciliation. No credential reaches the engine. Unload cancels SDK requests without terminating the independent service.

## Task Execution

| Task | Executor | Status | Evidence |
|---|---|---|---|
| Engine boundary/runtime/tools | integration agent | Complete locally | mock HTTP test and strict typecheck |
| Authenticated bridge and Client card | integration agent | Complete locally | route mock, client loader smoke; real React render remains skipped |
| Bundle deployment metadata | integration agent | Complete locally | packed manifest has no runtime dependencies; extracted archive imports outside repo |
| Recursive SBOM | integration agent | Complete locally | 197 components; plugin→SDK→openapi-fetch/Ajv edges explicitly asserted |
| Aggregate Verify Gate and independent review | parent/reviewer | Pending at report creation | parent records final receipt |

## Files Changed

- Created src/lib/engine.ts, src/host-tools-engine.ts, src/client-engine.ts, test/engine.ts under apps/dsh-plugin.
- Modified src/index.ts, src/host-runtime.ts, src/host-panel.ts, src/client.ts, cordis.patch.yml.
- Modified package.json, project.json, tsdown.config.ts, scripts/check-bundle.ts, scripts/sbom.ts.
- Created DESIGN_DSH_ENGINE.md and this report; regenerated root sbom.cdx.json under parent authorization. SDK agent owns lock refresh.
- Removed no files. No migration or runtime LLM prompt changes.

## Drift Detected

| Drift | Decision/action |
|---|---|
| Root-only SBOM omitted workspace runtime packages | Parent requested recursive roots and true workspace versions before implementation; supplement records decision. |
| Inlined private packages still appeared as workspace runtime dependencies | Parent requested move to build-only devDependencies and real packed-manifest validation; implemented before acceptance. |
| Engine has only partial Testnet public tickers | Do not replace account/candle/analysis paths or infer execution readiness; original full product gates remain open. |

## Verification Results

| Command | Exit | Evidence |
|---|---:|---|
| pnpm --filter @bybit-quant/dsh-plugin build | 0 | Host/Client generated; SDK and transitive dependencies inlined. Initial build before SDK dist existed warned unresolved SDK; rebuilt after SDK build, isolated archive import confirms closure. |
| pnpm --filter @bybit-quant/dsh-plugin typecheck | 0 | strict source/script types; first iteration fixed React namespace default mismatch with narrow React interface |
| pnpm --filter @bybit-quant/dsh-plugin typecheck:tests | 0 | strict test types |
| pnpm --filter @bybit-quant/dsh-plugin lint | 0 | four existing/scope warnings remain (host-panel closure scoping, old test shadow/reverse); no errors |
| node apps/dsh-plugin/test/engine.ts | 0 | loopback mock: ready/503/partial/missing/invalid response/network failure/timeout, strict args, no background request, no auth headers, env fence, caller abort and Host unload, independent service survives |
| pnpm --filter @bybit-quant/dsh-plugin test:unit | 0 | signals 9, AI17, loader, endpoint, OAuth3, backup, sandbox, trust and engine pass; render explicitly skips absent BQ_REACT_MODULES |
| node apps/dsh-plugin/scripts/check-bundle.ts | 0 | metadata, patch/resources; pnpm pack actual app, extract outside repo, packed dependencies empty, import extracted Host with no node_modules and empty NODE_PATH |
| node apps/dsh-plugin/scripts/sbom.ts | 0 | 197 npm components; recursive workspace roots and exact root metadata path |
| inline node SBOM assertions | 0 | SDK/openapi-fetch/Ajv components and plugin→SDK→runtime edges exist |
| git diff --check -- apps/dsh-plugin sdd/features/DESIGN_DSH_ENGINE.md | 0 | no whitespace errors |

Mock loopback listening initially failed with sandbox EPERM; authorized require_escalated test runs passed. First focused test expected SDK `aborted` but actual documented safe code is `cancelled`; corrected assertion and reran. Native Node cannot resolve source .js imports from .ts entry, so test imports the actual built Host. No exchange request, order, secret file, live account or external service is used. Tests explicitly set a nonexistent temporary credentialsFile.

### Verify Gate

| Attribute | Value |
|---|---|
| Kind | aggregate DEFINE gate |
| Command | pnpm run verify |
| Exit/result | Parent-owned, not executed by integration agent |
| Status | Pending aggregate receipt |

Manual UX receipt: N/A; real React render skipped locally. New files are 28/30/40/128 lines; Client entry497 lines. No handwritten file introduced above500 lines.

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-013 scoped | DSH reads generated engine contract | Local pass | built Host mock service tools and authenticated bridge |
| AT-005 scoped | graceful lifecycle | Local pass | pending request cancelled on unload, service still responds |
| AT-003 packaging subset | private SDK deploys with Bundle | Local pass | packed manifest/import; official manager lifecycle not verified |
| Full original MUST | account/execution/data/research platform | Not accepted by this slice | original scope audit remains authoritative |

## Advisor Ledger

Independent review requested by parent; final receipt remains parent-owned. Applied reviewer P2: external pnpm unsaved link: dependency versions were leaking into CycloneDX PURLs. Read only public dependency package.json metadata to normalize name/version; regenerated BOM197 components and asserted no link: versions/PURLs plus SDK/runtime edges. Strict typecheck exit0. Supplement recorded before code correction. No claimed ACCEPT.

## Issues Encountered

Sandbox prohibits loopback listeners; test permission handled explicitly. React render dependency absent. Initial dependency build ordering, source import and React type mismatch were corrected and verified. Aggregate checks and official plugin lifecycle are not inferred from local build.

## Deviations from Design

No silent deviation. Supplemental design records parent-directed SBOM/metadata changes before edits. Host config destination is owned by engine factory rather than duplicated in credential settings; factory validates before resolving credentials.

## Blockers

| Item | Required action | Owner |
|---|---|---|
| Full DEFINE gate | Run aggregate checks after concurrent edits settle | parent |
| Independent review | Record verdict and any corrections | reviewer/parent |
| Real React/manual UI | Supply existing React render runtime or manual receipt | parent/user |
| Official PluginManager lifecycle | Isolated official install/upgrade/uninstall | release owner |

## Final Status

Overall: IN PROGRESS at scoped receipt creation. All local implementation checks above pass; parent must append aggregate/review evidence. No deployment, install, profile mutation, commit or push was performed. No TODO/FIXME substitutes implementation.

## Parent-authorized real React verification closure

Added React/react-dom19 only as devDependencies; optional BQ_REACT_MODULES override remains, but missing default React now fails instead of skipping. Parent-authorized `pnpm install --ignore-scripts --no-frozen-lockfile` ran once with required sandbox network permission: exit0, three packages added. No Harness profile changes.

- `node apps/dsh-plugin/test/render.ts`: exit0, real React19 SSR populated/empty/failed/loading cases, engine card and Linear Testnet label, explicit Not checked and unknown account/reconciliation/execution labels. Chart failure does not falsely classify an unqueried engine as unavailable.
- `pnpm --filter @bybit-quant/dsh-plugin typecheck:tests`: exit0.
- `pnpm --filter @bybit-quant/dsh-plugin test:unit` with loopback permission: exit0, includes actual React render with no skip.
- SBOM generation exit0, now200 components after React dev dependencies; packed bundle metadata/import check exit0, runtime dependencies remain empty.

These final receipts supersede earlier render-skip and197-component notes. SSR never runs useEffect, so it cannot demonstrate completed engine fetch, post-fetch unavailable/ready state, visual appearance, interaction or browser cancellation. Real visual/manual acceptance remains pending; test does not manufacture that evidence.

## Root Nx gate correction: nested pnpm environment

Parent root verification second run failed exit1 in Bundle check: nested pnpm pack inherited Nx/npm lifecycle variables and attempted a broken auto-switch executable (ENOEXEC). Standalone pack/import passing was insufficient evidence of Nx gate compatibility. Added shared `apps/dsh-plugin/scripts/pnpm-environment.ts` and used it in both SBOM and Bundle pack: preserve only PATH/HOME/USER/TMPDIR/SystemRoot, disable Corepack project spec/auto-pin and pnpm manage-package-manager-versions. No global package manager or Harness mutations.

- `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm bundle:check`: exit0, one Nx task, no cache hit.
- `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx run @bybit-quant/dsh-plugin:bundle:check --skip-nx-cache --output-style=static`: exit0, actual nested pack/extracted import logs visible, cache explicitly skipped.
- Plugin strict source/script typecheck exit0; shared helper SBOM generation exit0 (200 components); scoped diff check exit0.

These targeted receipts repair the reproduced failure; parent must rerun the remaining/full aggregate gate. Independent reviewer notified for recheck.
