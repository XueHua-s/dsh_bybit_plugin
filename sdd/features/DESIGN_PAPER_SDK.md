# DESIGN: Authenticated internal-paper SDK

Sources: BRAINSTORM_BYBIT_AI_QUANT.md, DEFINE_BYBIT_AI_QUANT.md, DESIGN_EXECUTION_CUTOVER.md. Delegated Build scope: paper_sdk; no DSH mutation tools, installation, dependency changes, exchange calls or release. LLM prompts: none in this slice.

## Architecture and decisions

Python Pydantic + actual FastAPI routes are sole wire authority. Offline exporter --paper exports actual optional paper application separately as quant-paper.v1.json; readonly contract remains unchanged. Neither lifespan starts. Runtime readonly app remains readonly; paper routes may be unavailable there. SDK keeps existing readonly constructor behavior and adds optional trusted Host capability provider. The provider is never a DTO, model argument or result; transport resolves it only for verified numeric loopback origin and serializes it only in Authorization. Provider resolution shares the deadline/cancel/close budget. Authenticated response bytes containing the capability are rejected, with fixed errors.

The transport hides origin verification, bounded reads, provider errors, no redirects and cancellation. Paper boundary hides generated schema runtime validation, safe status codes and uncertainty. Mutation requests have no retries; ambiguous transport results instruct querying the original request identity or paper status before another action. Input objects are runtime validated with extra fields forbidden; callers cannot provide cash/equity/policy truth. Typed wire response DTOs are generated, not copied.

Drift discovered before Build: command GET by command_id alone cannot resolve lost POST response; API author requested to add request_id lookup before schema freeze. Canonical exporter exposes actual optional routes separately; parent selected separate contract to avoid advertising unsupported superset paths. Paper native implementation uses a dedicated process (native_process_alive), as coordinated by root.

## File Manifest

| ID | Path | Action | Purpose |
|---|---|---|---|
| S1 | python/apps/quant-engine/src/quant_engine/bootstrap.py | modify (delegated API author ownership) | separate offline paper export from actual application |
| S2 | contracts/openapi/quant-paper.v1.json | create | authoritative paper document |
| S3 | packages/ts/quant-api-client/src/generated/{paper-paths,paper-schema}.ts | regenerate | generated wire types and runtime schema |
| S4 | packages/ts/quant-api-client/src/transport.ts | modify | bounded private capability injection |
| S5 | packages/ts/quant-api-client/src/validation.ts | modify | generated paper input/output validators |
| S6 | packages/ts/quant-api-client/src/{index,paper}.ts | modify/create | compatible public client plus deep paper API boundary |
| S7 | packages/ts/quant-api-client/test/paper.test.ts | create | synthetic auth/status/uncertainty/security regressions |
| S9 | packages/ts/quant-api-client/scripts/generate.ts | modify | generate and check both separately authoritative contracts |
| S8 | sdd/reports/BUILD_REPORT_PAPER_SDK.md | create | canonical scoped Build evidence |

## Verification and acceptance

Run actual Python offline exporter and --check; pnpm package generate and generate:check; package build/typecheck/test; scoped lint. Existing readonly tests must remain green. New tests assert exact generated response status, extra-field request rejection, no capability in error/result, malicious redirects blocked, stalled provider/fetch/body bounded, timeout/cancel/close uncertainty and same-request lookup. Root owns product Verify Gate and independent review; no product-wide completion inferred.

## Software design assessment

Target 10/10, all eight diagnostics: one-sentence boundaries (transport owns private HTTP; paper owns safe control results), simpler client interfaces, hidden HTTP/auth decisions, abstraction comments, recorded design review, each module hides a significant decision, documented boundaries and explicit design investment. Current readonly baseline 8.75/10: paper uncertainty and private provider boundary absent; S4/S6 implement that missing behavior. Final score requires verification/review evidence.

## Review refinements

Independent reviewer detected two boundary cases before completion: printable capabilities containing quote/backslash need decoded-value/key comparison rather than JSON reserialization; dot-only opaque IDs normalize as URL path traversal and must be excluded by canonical Python schema. Both are addressed before the final generation/check. Paper routes are compile checked against generated path names. Product gate remains root-owned.

## Final assessment

Implemented scoped boundary: 10/10 against the eight design diagnostics above; no failed diagnostic remains within SDK scope. Independent ACCEPT receipt: sdd/reviews/REVIEW_PAPER_SDK_2026-11-17.md. This score and scoped acceptance do not certify the full execution platform.
