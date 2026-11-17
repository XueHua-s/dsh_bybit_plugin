# Independent review: DSH engine integration

Date: 2026-11-17. Scope: `DESIGN_DSH_ENGINE.md` and the integration with `DESIGN_ENGINE_CLIENT.md`. Reviewer owns only this report; no implementation edits, credentials, exchange requests, orders, Harness writes, install, commit or push.

## Verdict

**ACCEPT for the scoped read-only integration.** No unresolved P1/P2 findings remain after the SBOM and package-metadata corrections. The read-only Host/client integration and packed runtime closure pass the checks below. This is not acceptance of the complete trading product, official Plugin Manager lifecycle, installed authentication behavior or browser interaction/manual UI quality.

## Findings

| ID | Priority | Reproduction and impact | Required correction |
|---|---|---|---|
| DSH-001 (resolved) | P2 | `sbom.cdx.json` contains six components whose `version` begins `link:` and whose PURLs encode workspace-relative installed paths (for example `pkg:npm/nx@link:../../node_modules/.pnpm/nx@24.0.6/node_modules/nx`). `scripts/sbom.ts` resolves workspace root metadata but accepts non-workspace `unsavedDependencies` link descriptors as package versions. The same installed tool can appear under multiple relative paths, preventing reliable dependency identification/scanning. | Resolve actual installed metadata for linked external dependencies or omit unsaved installation artifacts that are not declared dependencies; regenerate and assert all component versions/PURLs plus required runtime edges. Implementer corrected linked metadata resolution. Independent recheck: 197 components, zero link versions/PURLs, required runtime edges preserved; source typecheck and diff check exit 0. |

The earlier private workspace runtime-dependency problem was corrected before this verdict: both private packages are build dependencies, tsdown inlines runtime dependencies, and the real packed manifest has no runtime dependency entries. No unresolved runtime `workspace:` dependency remains in the reviewed package.

## Boundary review

- `lib/engine.ts` owns SDK creation, Testnet Host fencing, explicit ingestion-only context and lifecycle. It receives configuration rather than credential references; its SDK requests have no authentication headers. Demo/live Hosts return `environment_mismatch` without contacting the Testnet engine.
- Tools use `additionalProperties:false` plus runtime validation of unexpected keys and uppercase bounded symbols. SDK-generated schema validation and fixed failures protect Host outputs; partial/null ticker facts are preserved, with no REST fallback or execution-readiness inference.
- Engine requests are demand driven. Host construction starts no engine I/O or process. Unload closes the client, cancels pending work and leaves the separately operated service alive. SDK transport removes request/reader cancellation listeners in `finally`; its independent review remains SDK-reviewer owned.
- `view=engine` and `health.engine` register through `webCtx.connection.fetch`; no new raw unauthenticated HTTP listener was introduced. The mocked bridge verifies registration/behavior, not installed Harness authentication/Host/Origin enforcement.
- The Client card uses explicit refresh, aborts on effect cleanup/unmount, keeps existing charts, and labels public linear Testnet ingestion separately from execution/account readiness. Browser response DTOs originate from the validated Host boundary. Real React19 SSR now passes and verifies truthful initial engine labels; effects, browser interaction and visual quality remain unverified here.
- Current handwritten plugin files remain within 500 lines; `client.ts` is 497 lines. No execution/background-loop responsibility was placed in a Tool call.

## Independent command receipts

| Real command | Exit | Result |
|---|---:|---|
| `node apps/dsh-plugin/scripts/check-bundle.ts` (earlier snapshot) | 0 | Copied dist import outside repository without workspace node_modules. |
| `COREPACK_ENABLE_PROJECT_SPEC=0 COREPACK_ENABLE_AUTO_PIN=0 node apps/dsh-plugin/scripts/check-bundle.ts` (corrected metadata) | 0 | Actual pnpm pack, external extraction, empty packed runtime dependencies, Host import without node_modules/NODE_PATH. |
| `node apps/dsh-plugin/test/engine.ts` (sandbox) | 1 | Local bind rejected with EPERM; environmental failure, not a passing test. |
| `node apps/dsh-plugin/test/engine.ts` (approved escalation) | 0 | Mock loopback: strict tools, partial/degraded responses, safe failures, timeout, env fence, cancellation/unload and independent service remains available. Temporary nonexistent credentialsFile explicitly configured. |
| `node node_modules/typescript/bin/tsc -p apps/dsh-plugin/tsconfig.json --noEmit && node node_modules/typescript/bin/tsc -p apps/dsh-plugin/tsconfig.tests.json --noEmit` | 0 | Strict source/tooling and test types. |
| `node apps/dsh-plugin/test/client.ts` | 0 | Built Client loader/registration smoke. |
| `node apps/dsh-plugin/test/render.ts` (initial) | 0, skipped | No BQ_REACT_MODULES; not UI-render evidence. Superseded by real SSR receipt below. |
| `node apps/dsh-plugin/test/render.ts` (final local React19 default) | 0 | Real React19 SSR: populated/empty/failed/loading states; engine card says Linear Testnet, Not checked and unknown execution/account readiness. Chart failure does not invent engine unavailability. |
| Direct test tsc, packed bundle check, diff check after SSR dependency change | 0 | Test types remain strict; packed runtime dependencies remain empty and external Host import passes. |
| Lockfile/SBOM inspection after SSR dependency change | 0 | react/react-dom19.3.1 are build/test devDependencies, lock importer matches manifest, scheduler0.28.0 included in SBOM; no link versions. |
| `git diff --check` | 0 | No whitespace errors in current concurrent workspace snapshot. |
| Inline Node inspection of `sbom.cdx.json` components/edges (initial) | 0 | Plugin -> SDK -> Ajv/openapi-fetch present, but six invalid link versions found (DSH-001). |
| Inline Node assertions of corrected SBOM, direct source tsc and diff check | 0 | 197 components; no link versions/PURLs; plugin -> SDK -> Ajv/openapi-fetch edges preserved. DSH-001 resolved. |
| `pnpm exec tsc -p apps/dsh-plugin/tsconfig.json --noEmit && pnpm exec tsc -p apps/dsh-plugin/tsconfig.tests.json --noEmit` | 130, cancelled | pnpm 12 initiated on-demand workspace dependency restore and hit registry DNS failures before compiler execution; no pass inferred. Direct compiler rerun above passed. |

## Software-design diagnostic

**10/10 for the scoped integration design (all eight diagnostic rows pass).** Module responsibilities fit one sentence; narrow methods hide transport/lifecycle, DTO knowledge stays generated, abstraction comments state intent, design review is explicit, each boundary owns a material decision, manifest/design document boundaries, and the separate demand-driven view plus deployment correction evidence design investment. No failed diagnostic rows; preserving these properties requires leaving account/execution outside this ingestion adapter. SBOM finding is a verification/artifact correctness issue rather than evidence of a failed integration module diagnostic.

## Limitations

Aggregate SDD Verify/Release gates are parent-owned. This review does not accept live/Testnet trading, account identity/balance/risk checks, reconciliation, candle/research functionality, installed Plugin Manager preservation/upgrade/uninstall, live provider operation, or the original full product. Do not describe mock route tests as proof of actual installed authentication or server rendering as browser interaction/visual acceptance. The initial skipped render was replaced with a mandatory real React SSR check; missing local React now fails rather than skips.
