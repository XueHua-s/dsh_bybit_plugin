# DESIGN: DSH read-only engine integration

Date: 2026-11-17. Supplement to BRAINSTORM/DEFINE/DESIGN_BYBIT_AI_QUANT and DESIGN_ENGINE_CLIENT/SERVICE. Parent explicitly delegates Build; no extra mode question. LLM Prompts: false (no runtime prompt changes).

## Scope and drift

AT-013 requires a generated client and DSH integration. Existing REST candles/account/analysis remain until engine capabilities cover them. The engine currently exposes public linear Testnet ticker deltas only; it is never evidence of account, risk, reconciliation or execution readiness. Existing direct trade path drift remains outside this slice.

## Decisions and boundaries

A Host engine module hides the generated SDK, Testnet environment fence, safe failures and lifecycle. No DTO duplication: generated response types are imported. Instantiate a bounded client, fetch only on explicit tool/view requests, default engineBaseUrl http://127.0.0.1:8765. No redundant enable flag or background polling. SDK validates numeric loopback/root URL; config is validated before reading legacy credentials. Reject requests in non-Testnet Host environments instead of mixing environments. Readiness refers solely to market ingestion; partial ticker fields remain null and partial. No credential is passed to engine. Host unload cancels requests via close(), never terminates independently operated service.

Authenticated connection bridge adds view=engine plus health.engine. Client component requests view=engine on demand and aborts on unmount, keeping existing chart intact. Tools have strict schemas and also runtime reject unexpected arguments. Existing Host generic health reports separate plugin and engine facts.

Bundle must inline private workspace SDK/transitive dependencies; tsdown noExternal owns this deployment decision. Isolated copied dist import outside repository proves no workspace node_modules dependency. No Harness profile modifications.

Software-design diagnostic: 10/10 target, all eight rows addressed by narrow engine/SDK APIs, generated wire knowledge, documented lifecycle invariants and a separate view that owns display/request state. Independent review must confirm.

## File manifest

- apps/dsh-plugin/src/lib/engine.ts: lifecycle/environment/API boundary.
- apps/dsh-plugin/src/host-tools-engine.ts, src/index.ts, src/host-runtime.ts: registration and runtime composition.
- apps/dsh-plugin/src/host-panel.ts: authenticated engine view and health integration.
- apps/dsh-plugin/src/lib/host-config.ts, cordis.patch.yml: validated loopback config default.
- apps/dsh-plugin/src/client-engine.ts, src/client.ts: demand-driven status UI without replacing charts.
- apps/dsh-plugin/package.json, project.json, tsdown.config.ts: dependency, test targets and private dependency bundling.
- apps/dsh-plugin/test/engine.ts, scripts/check-bundle.ts: mock loopback full Host integration, cancellation, strict args/environment, isolated import.
- sdd/reports/BUILD_REPORT_DSH_ENGINE.md: real commands/results and limitations.

## Verification

Strict source/test typecheck, lint, package build, focused mock HTTP tests and existing unit/render tests. Tests always configure a missing credentialsFile in a temporary directory, never read default credentials or call exchange APIs. Cover healthy and degraded engine responses, partial market, mismatch/invalid schema/symbol, unavailable endpoint, caller abort/unload, authenticated route and no fallback REST. Copied bundle imports outside repo without node_modules. Parent owns full DEFINE gate and independent review/release; no order, credentials, deployment, commit or push in this slice.

## SBOM workspace correction

Parent identified that root-only pnpm list omitted workspace runtime packages. Manifest adds apps/dsh-plugin/scripts/sbom.ts: use recursive workspace roots, identify metadata by exact workspace path, resolve linked workspace versions to actual roots, and sort components/edges. Verify SDK, openapi-fetch and Ajv components and dependency edges explicitly.

## Install metadata correction

Parent identified that inlining alone leaves workspace:* runtime dependencies in a file-installed manifest. Both private @bybit-quant packages are build-only devDependencies; generated Host dist contains their runtime code and dependency closure. No private runtime package resolution is needed. Extend bundle check to reject workspace runtime dependencies and pack via pnpm pack into an isolated directory, inspect packed manifest and import extracted Host dist. Official PluginManager lifecycle remains a separate unverified release acceptance; neither import nor packing claims it.

## Review correction: linked external SBOM versions

Independent review reproduced pnpm unsaved dependency link: version values leaking into component PURLs. Manifest unchanged. Resolve linked external package name/version from its public package.json metadata at pnpm-provided absolute path, reject missing/nonstring metadata, preserve dependency collections and normalize before graph traversal. Validate generated BOM contains no link: component versions/PURLs. No credential/config file reads are introduced.

## Parent-authorized UI verification closure

Manifest adds apps/dsh-plugin/test/render.ts and React/react-dom19 devDependencies. The existing secret-free real React SSR test must run by default using local dev runtime and fail if dependencies are missing; BQ_REACT_MODULES remains an optional override. Assert engine card, explicit Not checked state and unknown account/execution labels with populated/failed chart snapshots. SSR does not run effects, so it must not claim an engine request completed or infer unavailable/ready from chart failures. Browser visual/manual lifecycle acceptance remains separate.

## Review/root gate correction: nested pnpm environment

Root Nx verification reproduced inherited pnpm auto-switch ENOEXEC in nested bundle pack, despite standalone check passing. Manifest adds apps/dsh-plugin/scripts/pnpm-environment.ts shared by SBOM and pack: preserve only executable/system paths and disable Corepack project auto-pin and pnpm package manager version switching. No global pnpm or Harness changes. Validate through actual root Nx bundle:check with daemon/plugin isolation disabled.
