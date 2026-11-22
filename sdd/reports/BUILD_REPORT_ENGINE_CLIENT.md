# BUILD REPORT: generated read-only engine client

## Metadata

| Attribute | Value |
|---|---|
| Feature | ENGINE_CLIENT, scoped AT-013 implementation |
| Date | 2026-11-17 |
| Author | delegated SDK implementation agent |
| BRAINSTORM | sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md |
| DEFINE | sdd/features/DEFINE_BYBIT_AI_QUANT.md |
| DESIGN | sdd/features/DESIGN_BYBIT_AI_QUANT.md; DESIGN_ENGINE_CLIENT.md |
| Status | Complete for SDK slice; full product acceptance remains incomplete |

## Mode Selection

Parent explicitly delegated this implementation in the authorized parallel Build. Recommendation and execution: briefs/delegated worker for a disjoint package, dependency manifest/lock and scoped design/report. Medium cross-file coupling; security surface is local HTTP validation and cancellation; no LLM prompt items. Parent owns external review and overall release gate. No additional approval was inferred from the skill.

## Summary / Task Execution

All six SDK manifest groups implemented: package/Nx/TS configuration; deterministic generator; generated paths/runtime schema; narrow client/transport/validation; Vitest mocks; root scripts/dependency lock and this report. No order endpoints, credentials, live exchange calls, commit or push.

## Files Changed

| File | Action | Verification |
|---|---|---|
| packages/ts/quant-api-client/package.json, project.json, tsconfig.json, tsconfig.build.json | create | build/typecheck/Nx discovery |
| packages/ts/quant-api-client/scripts/generate.ts | create | generation and positive/negative drift checks |
| packages/ts/quant-api-client/src/generated/paths.ts, schema.ts | generate | exact regeneration from committed OpenAPI |
| packages/ts/quant-api-client/src/index.ts, transport.ts, validation.ts | create | strict typecheck, lint, Vitest |
| packages/ts/quant-api-client/test/client.test.ts | create | 9 Vitest tests |
| package.json, pnpm-lock.yaml | modify | installation exit 0; root sdk scripts and tooling types/scripts |
| sdd/features/DESIGN_ENGINE_CLIENT.md | create before code | manifest and criteria |

Handwritten TS modules remain below 500 lines. Generated artifacts are explicitly labeled. Existing unrelated files belong to other workers and were not edited by this worker.

## Drift Detected

Initial negative-lag rejection conflicted with service tolerance of future events. Parent identified the discrepancy; removed the duplicated lag policy and added a successful -4.5 second fixture. Service status owns freshness/readiness. Initial node:test harness switched to required Vitest. openapi-typescript defaultNonNullable=false preserves the contract's optional default fields rather than claiming runtime presence without validation.

## Verification Results

| Command / Method | Exit | Evidence |
|---|---:|---|
| pnpm install --ignore-scripts (escalated network) | 0 | installed openapi-typescript, openapi-fetch, Ajv and Vitest; linked workspace SDK |
| pnpm install --ignore-scripts --offline (escalated filesystem) | 0 | root/SDK Node types aligned to 22.20.5 |
| node packages/ts/quant-api-client/scripts/generate.ts | 0 | generated paths and runtime schema from quant-engine.v1.json |
| node packages/ts/quant-api-client/scripts/generate.ts --check | 0 | exact checked-in artifact consistency |
| deliberate generated-path append; same --check | 1 expected | drift detected; try/finally restored original bytes; subsequent check exit 0 |
| pnpm --filter @bybit-quant/quant-api-client test | 0 | build then Vitest 4.1.12: 1 file, 9 passed |
| pnpm --filter @bybit-quant/quant-api-client typecheck | 0 | source/scripts/tests strict TypeScript |
| pnpm --filter @bybit-quant/quant-api-client generate:check | 0 | deterministic nonmutating check |
| ./node_modules/.bin/oxlint packages/ts/quant-api-client/src packages/ts/quant-api-client/scripts packages/ts/quant-api-client/test | 0 | clean |
| direct tsc source/build, SDK vitest run --root packages/ts/quant-api-client, node generator --check, git diff --check (final Node22-types rerun) | 0 | all pass; Vitest 9 passed |
| NX_DAEMON=false ./node_modules/.bin/nx show projects | 0 | client discovered among six projects; sandbox socket denial caused in-process plugin fallback |

### Verify Gate

Scoped gate is green: generated drift check, strict typecheck, build, Vitest mocks and lint all exit 0. DEFINE full `pnpm run verify`, independent review, CI, SBOM/security scans and official Plugin Manager lifecycle are parent-owned; this report does not claim those passed. Manual UX: N/A.

## Acceptance Test Verification

AT-013 SDK portion passes: Python OpenAPI produces TypeScript paths and runtime schema; drift deliberately fails. Vitest covers health 200/503, contradictory readiness, malformed/extra/nonfinite/oversized/mismatched data, market safe errors, numeric loopback origin restriction, forbidden credentials/query/hash/path/remote hosts, redirects, total deadline including stalled body, caller cancellation, close, ignored AbortSignal and future-event lag preservation. No DTOs are manually duplicated from Python.

## Advisor Ledger

Parent-assigned independent SDK review reported build/typecheck/drift check and all 9 Vitest tests passing; final receipt and Nx graph evidence are owned by parent/reviewer. Timing-policy finding APPLIED as above.

## Integration gate failure and correction

Parent real `pnpm run verify` failed exit 1 at the SDK Nx build because nested pnpm package-manager switching attempted `/Users/litlesnow/Library/pnpm/.tools/pnpm/12.6.0/bin/pnpm` and failed ENOEXEC. This invalidated the initial integration gate. SDK Nx targets now execute root-relative tsc/node/oxlint/Vitest directly; test explicitly depends on SDK build. No global package-manager configuration changed. Fresh `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx run-many -t build,typecheck,test,lint,generate:check --projects=@bybit-quant/quant-api-client --skip-nx-cache` ran with authorized escalation: exit 0, all 5 tasks succeeded, cache skipped. Full aggregate remains parent-owned and is not green until rerun.

## Issues Encountered

Sandbox npm DNS failed; authorized escalated install succeeded. Later sandbox pnpm commands attempted automatic reinstalls and hit the same DNS restriction; direct binaries passed the complete final scoped gate after installation. First test attempt importing TS source with .js specifiers failed module resolution; tests now exercise built distribution. Initial fixture defaults and lint issues were corrected before passing final gate. No unresolved SDK blocker.

## Deviations from Design

None remaining. Resource bounds are generic finite safe numbers and bounded strings/container/depth/bytes, with semantic consistency only where needed; the service owns exchange lag policy. API factory configuration errors throw only fixed-code invalid_config; request outcomes return safe codes. last_error is normalized to engine_error before leaving the client.

## Final Status

Overall: COMPLETE for the scoped generated SDK; full BYBIT_AI_QUANT remains IN PROGRESS. All manifest tasks, local checks and scoped acceptance are recorded; parent must finish overall verification/review/release. No TODO/FIXME substitutes for implementation.

## Next Step

Execute o **SDD Handoff by RDD**.
