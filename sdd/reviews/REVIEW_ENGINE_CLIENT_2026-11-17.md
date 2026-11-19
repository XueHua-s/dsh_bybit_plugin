# Independent review: generated engine client

Date: 2026-11-17. Reviewer: `sdk_review`, independent of SDK author.

Verdict: **ACCEPT within this read-only SDK slice**. No unresolved P1/P2 findings. This is not a release, live-engine acceptance, exchange connectivity test, trading authorization, or Plugin Manager installation acceptance.

## Scope and design

Reviewed `AGENTS.md`, `.agents/skills/software-design-philosophy/SKILL.md`, `sdd/features/DESIGN_ENGINE_CLIENT.md`, all handwritten SDK implementation/generation/configuration/tests, generated DTO/schema artifacts, committed OpenAPI, and Python API/health producers. The author confirmed the implementation was ready before this verdict.

The committed OpenAPI remains the DTO authority: `openapi-typescript` generates paths/components; the runtime schema copies OpenAPI components and resolves those same component references with Ajv 2020. Public DTO exports are aliases to generated components. There is no handwritten parallel wire DTO. `defaultNonNullable: false` preserves optional defaulted fields rather than inventing required wire fields. Resource and semantic checks are additional boundary policy rather than duplicate DTO definitions. Negative exchange lag is accepted consistently with the Python producer.

Transport owns loopback-only literal HTTP origin validation, manual redirect rejection, bounded streaming reads, total request/body deadline, caller cancellation and terminal close. Responses from a delayed injected fetch that ignores AbortSignal are cancelled after timeout/close. Error results contain fixed codes, HTTP statuses where applicable, and no raw thrown text. Health diagnostic `last_error` is replaced by a fixed marker; 200/503 readiness contradictions are rejected. Market symbol, price, age and event identity checks occur before returning data. No retries, credentials, trading methods or remote URLs are introduced.

Software design score: **10/10**, all eight diagnostic rows pass for this slice. Modules have coherent responsibilities, the factory interface hides transport and validation, protocol knowledge is generated centrally, interface comments document lifecycle/error promises, design discussion is recorded, transport/validation/generation each hide an important decision, boundaries are understandable from their public surface, and adversarial lifecycle verification reflects strategic investment. No failed diagnostic requires remediation.

## Commands and observed results

All commands ran from the repository root using mock Responses/ReadableStreams only. No Bybit requests, credentials, Mainnet/Testnet orders, commits or installation operations were performed.

| Actual command / probe | Exit | Evidence |
| --- | --- | --- |
| `pnpm --filter @bybit-quant/quant-api-client generate:check && pnpm --filter @bybit-quant/quant-api-client typecheck && pnpm --filter @bybit-quant/quant-api-client test` | 0 | Generated artifacts current; strict typecheck and build passed; Vitest 4.1.12: 1 file, 9 tests passed. |
| `NX_DAEMON=false pnpm exec nx show projects --json` | 0 | SDK and all six workspace projects discovered. Plugin-worker sockets encountered sandbox EPERM; Nx explicitly fell back to in-process plugins. |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx graph --file=/tmp/sdk-review-nx-graph.json` | 0 | Clean graph generation. Independent Node assertion found static `@bybit-quant/dsh-plugin -> @bybit-quant/quant-api-client` edge. |
| `node --input-type=module` inline assertions importing built SDK | 0 | Ignored-abort fetch resolved after deadline: result `timeout`, late body cancelled. Separate late response after close: result `closed`, body cancelled. Assertions inspected the generated Nx graph dependency. |
| `python3` temporary-copy drift probe invoking `node scripts/generate.ts --check` | 0 (wrapper) | Scratch copy of generator, components source and both generated outputs; original check exit 0, deliberately appended paths drift exit 1, restored paths then runtime-schema drift exit 1. Repository generated files were never changed. |

The nine package tests cover valid health 200/503, diagnostic redaction, status/readiness contradictions, malformed/extra/mismatched/resource-invalid responses, invalid URL/config/symbol rejection, safe provider failures, redirects, oversized/malformed bodies, ignored-abort timeout, caller cancellation/close, stalled-body cancellation, and negative exchange lag.

One discovery command combined `cat tsconfig.base.json`, `rg` over package/scripts plus absent `tools/`, and `git status`; `rg` reported that `tools/` does not exist. The final command status was 0 from `git status`; this mixed discovery command is not counted as a passing verification gate.

## Limits and remaining ownership

This review used in-memory transport doubles, not a live HTTP engine. Parent verification owns full workspace gates, actual bundle dependency resolution, CI/SBOM/security integration and the `sdd-release` workflow. Plugin bundling changes are reviewed separately. No observed limitation blocks acceptance of the reviewed SDK behavior.
