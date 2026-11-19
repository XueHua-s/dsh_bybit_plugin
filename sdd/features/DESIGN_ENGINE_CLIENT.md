# DESIGN: generated read-only engine client

Date: 2026-11-17. Supplement to BYBIT_AI_QUANT BRAINSTORM/DEFINE/DESIGN, original brief §16, AT-013. Parent explicitly delegates Build and dependency installation. LLM Prompts: false.

## Contract and scope

FastAPI/Pydantic remains the sole DTO schema authority. Generate openapi-typescript paths and a runtime JSON Schema document from the committed OpenAPI; openapi-fetch owns typed endpoint construction. No handwritten Python DTO copies. Only health and market reads exist; trading, authentication and remote control remain future product requirements, not accepted by this slice.

The client hides transport/validation/lifecycle behind createQuantApiClient(options), health(options?), market(symbol, options?), close(). Health 200/503 returns typed data; market 200 returns typed data. Other outcomes return fixed safe error codes without raw exception/provider text. Caller signal, total deadline and close cancel body reads as well as connection establishment. No retries. Base URL is HTTP numeric loopback only, root path, no credentials/query/hash; redirects forbidden. Responses are streamed with a bounded byte ceiling. Schema validation rejects wrong fields/types; a generic resource policy bounds numbers/strings/containers/depth and excludes unsafe object keys. Market symbol is bounded uppercase alphanumeric.

Software design score: 10/10 target, all eight diagnostics covered by documented narrow public API, generated shared protocol knowledge, and internal transport/validation ownership. Independent review remains required to confirm.

## File manifest

| Path | Action | Acceptance |
|---|---|---|
| packages/ts/quant-api-client/package.json, project.json, tsconfig*.json | create | real Nx/pnpm project, strict ESM build/test/check |
| packages/ts/quant-api-client/scripts/generate.ts | create | deterministic generation and nonmutating drift check from committed OpenAPI |
| packages/ts/quant-api-client/src/generated/* | generate | openapi-typescript types and JSON Schema derived from same source |
| packages/ts/quant-api-client/src/index.ts, validation.ts, transport.ts | create | safe typed read-only factory; bounded validation, cancellation and loopback transport |
| packages/ts/quant-api-client/test/*.ts | create | mock response/transport/readiness/contract checks |
| package.json, pnpm-lock.yaml | modify | dependency installation and root generated SDK verification scripts |
| sdd/reports/BUILD_REPORT_ENGINE_CLIENT.md | create | exact commands, exits and incomplete items |

## Verify gate

Run generation, generation drift check, strict typecheck, package build and mock tests. Nx discovers client; plugin integration supplies real dependency edge. Parent owns full pnpm verify, bundle/CI integration, independent review and release gate. No exchange requests or orders. Generated data is public contract only; no secrets read or stored.
