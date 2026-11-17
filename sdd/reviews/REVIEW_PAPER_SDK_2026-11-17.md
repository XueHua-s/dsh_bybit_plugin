# Independent review: authenticated internal-paper TypeScript SDK

Date: 2026-11-17. Reviewer: `paper_sdk_review`, separate from implementation author. Scope: `DESIGN_PAPER_SDK.md`, paper contract generation, SDK paper boundary and shared HTTP transport regression. **Verdict: scoped ACCEPT. No unresolved P1/P2 findings.** This is not product, installation, exchange or release acceptance.

## Authority and boundaries

Read repository AGENTS.md, project SDD Build guidance, software-design-philosophy and the scoped design; inspected actual Python models/routes/exporter and TS implementation/tests. Python `paper_api_models.py` and `create_paper_app` are the wire authority; `bootstrap.export_openapi --paper` exports that actual application without entering lifespan. The optional paper application is a separate document rather than a fictional readonly superset. Actual GET lookup paths use canonical `Opaque` annotations and registered route ordering places by-request before command ID. SDK paths/types and AJV schemas are generated from the separate document. The readonly OpenAPI and both existing generated readonly artifacts are byte-unchanged against HEAD.

The client injects a private trusted provider into transport, verifies numeric-loopback origin before resolving it, shares deadline/cancel/close state with provider/fetch/body, and sends capability only as Authorization. Manual redirects are rejected. Response JSON is checked recursively after decoding, including string keys, for reflected capability; errors expose fixed codes rather than provider exceptions or server diagnostics. No credential/config/environment files were read. All probes used synthetic data, isolated mocks and numeric loopback; no exchange/account request or order occurred.

Generated strict validators reject extra risk/account/cash truth, invalid environments, types, decimals and identity paths before authentication/HTTP. POSTs are never retried. Network/timeout/cancel/close/body/schema uncertainty returns original request lookup recovery; definitive validated auth/validation failures remain distinct. Session and command response identities are checked where the wire DTO carries them. The by-request response does not carry request_id, so its identity binding relies on the authenticated server route and durable store, not an invented TS DTO field.

## Findings resolved during independent review

| Finding | Resolution and independent evidence |
|---|---|
| P2: canonical IDs allowed `.`/`..`; WHATWG Request normalized a valid by-request recovery URL to another path. Real HTTP probe observed `/api/v1/trading/commands/` for `..`. | API author tightened canonical Python Opaque to alphanumeric first character, also on actual path parameters, then regenerated OpenAPI/types/runtime schema. Independent final HTTP probe confirms both lookup and POST dot-only IDs fail before HTTP. No hand-copied TS-only restriction. APPLIED. |
| P2: caller can mutate request DTO while capability provider awaits; failure recovery previously read mutated request_id although wire body carried original. | Author captures primitive request/session identity before await. Independent delayed-provider probe confirms actual wire body and uncertain recovery both retain original ID after caller mutation. Regression test included. APPLIED. |
| Defense-in-depth: reserialized JSON substring comparison does not reliably detect printable capabilities containing quote/backslash. | Author replaced comparison with recursive parsed string/key inspection and added synthetic quote/backslash reflection coverage. Existing strict output DTOs also constrain returned values. Final tests plus independent escaped reflection HTTP probe pass. APPLIED. |

## Executed verification

Final frozen-source check around 20:40 Asia/Shanghai:

| Actual command/probe | Exit | Result |
|---|---:|---|
| `pnpm --filter @bybit-quant/quant-api-client test` | 0 | Build plus 21 tests across 2 files passed; existing readonly cancellation/bodybound/close tests remain included. |
| `pnpm --filter @bybit-quant/quant-api-client typecheck` | 0 | Strict source/test/tooling TypeScript check passed. |
| `pnpm --filter @bybit-quant/quant-api-client generate:check` | 0 | Both documents' generated type and runtime schema artifacts match. |
| `pnpm exec oxlint packages/ts/quant-api-client` | 0 | Scoped lint passed. |
| `UV_CACHE_DIR=/tmp/paper-sdk-review-uv uv run --project python --locked --no-sync quant-engine-openapi --paper --output contracts/openapi/quant-paper.v1.json --check` | 0 | Actual paper exporter matches committed-path contract. |
| Same Python command without `--paper`, output `contracts/openapi/quant-engine.v1.json` | 0 | Actual readonly exporter remains consistent. |
| `git diff --exit-code HEAD -- contracts/openapi/quant-engine.v1.json packages/ts/quant-api-client/src/generated/paths.ts packages/ts/quant-api-client/src/generated/schema.ts` | 0 | Readonly schema/generated artifacts unchanged. |
| `node /tmp/paper-sdk-review-http.mjs` | 0 | 7 independent real HTTP probes passed: one lost POST/no retry/original-ID lookup/header-only auth; dot-ID preflight; redirect rejection; definitive auth error; escaped reflection rejection; body bound; stalled authenticated body timeout and close. |
| Independent inline Node delayed-provider mutation/origin probe | 0 | Original wire/recovery identity preserved; 7 remote/hostname/nonliteral/userinfo/path/scheme origins rejected before provider invocation. |
| `node /tmp/paper-sdk-review-drift/packages/ts/quant-api-client/scripts/generate.ts --check` against isolated intentionally corrupted generated paper artifact | 1 expected | Correctly rejected generated SDK drift. Repository artifacts were never modified for this probe. |
| Python paper exporter `--check` against isolated `/tmp/paper-sdk-review-drift/contracts/openapi/quant-paper.v1.json` deliberately replaced with `{}` | 1 expected | Correctly rejected Python/OpenAPI drift. |

Initial default uv cache attempt exited 2 due sandbox cache write restrictions; reran with isolated writable `/tmp` cache and no-sync, passed. Initial loopback mock bind exited 1 (EPERM); explicit sandbox escalation was approved, then real HTTP probes passed. These initial failures were not treated as verification successes. No dependency installation or implementation/test edits were made by reviewer.

Handwritten reviewed files are 74/108/108/38/21 lines (`index`, `paper`, `transport`, `validation`, generator), below 500. Strict base TS config is enabled; scoped inspection found no `any`, console logging, environment access or credential fallback.

## Source receipt

SHA256 of frozen reviewed sources:

```text
bb88f7f567bef1e7f300b94d50d8dbdb07449eb535304f2ca827d5275001df11  src/index.ts
55720552c62a4277065d4af85e6ebb9a4d3bcd97db2ebda0f8646d14f70f15b0  src/paper.ts
4cc615420719992aed9a461f94039a01486615cb327a0995e7fbd889ee938c25  src/transport.ts
a31a29f9084294323f5c9671fb2e22f5f818226788dad83c1e7949ffbe37875f  src/validation.ts
24878c9e7ba9821dfbcd33311db3409463b7de5da45f7fc4b78d94c39b0260f5  contracts/openapi/quant-paper.v1.json
```

TS source paths above are under `packages/ts/quant-api-client/`.

## Design assessment and limits

Software-design-philosophy: **10/10 for this scoped boundary, eight diagnostics supported, no failed rows.** Transport owns private HTTP/deadline/resource decisions; paper boundary owns validation, response interpretation and uncertainty; generation owns the cross-language schema. Interfaces are smaller than implementations, implementation decisions remain hidden, comments explain recovery/private-provider promises, and review led to concrete fixes rather than duplicated protocol knowledge. Design discussion, explicit manifests and source/tests demonstrate deliberate design investment; no elapsed-time percentage is asserted.

Python API/native subprocess/fault behavior is independently owned by `paper_service_review`/`paper_runtime_review`; their shared evidence is not relabeled as this reviewer's execution. No actual SDK-to-native Python process E2E was run here. This review does not certify DSH mutation tools, plugin installation, Mainnet/Testnet/Demo execution, trading performance, product-wide security/SBOM gates, crash recovery beyond original-ID query semantics, or release. Parent retains aggregate Verify Gate and release decisions.
