# Independent implementation review: paper SDK mutation503 recovery

Date: 2026-11-17. Reviewer: `paper_dsh_design_review`, independent of implementation author `paper_sdk_503_fix`. Scope: DSH_PAPER manifest33–34, `packages/ts/quant-api-client/src/paper.ts` and `test/paper.test.ts`. **Verdict: scoped ACCEPT; no unresolved P1/P2 findings.** This is SDK implementation acceptance only, distinct from the earlier design ACCEPT and ongoing broker/Host/UI/native process/installed-auth/release gates.

## Findings and contract verification

The fix adds `unavailable` to the existing SDK `uncertain()` cause list and documents why503 can follow a committed dispatch. It introduces no second ambiguity owner, new API, generated schema, transport or retry branch. All three mutation methods already invoke this helper with identities captured before awaiting the private provider: start/stop preserve `query_status`, submit preserves the original `query_request` ID. GET status/command/request bypass the helper and retain unavailable/status503.

The source reason remains real: current `paper_admission.py:225` persists a decision, lines232–242 claim dispatch and call `runtime.submit`, then drain/ledger lookup at243–244 can fail. The exception boundary at247–249 raises `PaperUnavailable`; current `paper_api.py:84–86` maps that class to503. This is inspected source-path evidence, not a claim to have naturally reproduced a native failure. Conservative uncertainty is valid even when a particular503 happened before dispatch.

The new test covers start, stop and submit with canonical503 error responses and exact increasing one-send counts. Existing definitive-error, strict-schema, header-only-auth, mutable-DTO, deadline/cancel/close and no-retry coverage remains. The implementation matches accepted design R1 without expanding scope or duplicating recovery policy in the Host.

## Independently executed verification

All commands below actually completed with exit0 using installed dependencies. No installation, exchange/account request, order, credential file/`.env` read or Git mutation occurred. Reviewer made no source/test edits; SDK test execution rebuilt normal ignored `dist` artifacts. Only this review receipt was added.

| Actual command | Result |
|---|---|
| `pnpm --filter @bybit-quant/quant-api-client test` | Build passed, then22 tests in2 files passed; includes readonly regressions. |
| `pnpm --filter @bybit-quant/quant-api-client typecheck` | Strict source/test/tooling typecheck passed. |
| `pnpm exec oxlint packages/ts/quant-api-client/src/paper.ts packages/ts/quant-api-client/test/paper.test.ts` | No diagnostics. |
| Independent `node --input-type=module` inline probe importing built `dist/index.js` | `sdk503_independent_probes_passed=10`; details below. |
| Targeted `nl`/`rg` source reads; `wc -l`; `shasum -a 256` | Current API failure chain checked; files108/177 lines; frozen hashes match author. |

The10 independent probe scenarios use an injected Fetch transport and synthetic in-memory capability only; they bind no sockets and make no real HTTP/native call:

1. Start503 returns outcome_uncertain/cause unavailable/query_status and exactly one POST.
2. Stop503 returns the same status recovery and exactly one POST.
3. Submit503 preserves original query_request and exactly one POST.
4. GET status503 remains unavailable/status503.
5. GET command503 remains unavailable/status503.
6. GET request503 remains unavailable/status503.
7. A delayed capability callback plus caller mutation retains the original wire/session/request identities; the stateful mock records a side effect, returns503, then original-ID GET recovers the same command/native IDs without another POST.
8. Validated401/403/409/422 mutation failures retain their existing definitive fixed codes.
9. Malformed503 error DTO produces invalid_response uncertainty with original recovery identity.
10. A capability-reflecting503 response is rejected and produces no capability in the returned result.

The stateful mock in7 proves SDK recovery composition, not actual Python/native persistence. Accepted design test18 still requires a real service202 followed by injected503 and original native-identity recovery; that separate owner has not supplied a receipt to this review.

## Frozen source receipt

```text
512560b2b72ba4b33a78341ac0cb7ad41bffa32b433b0d2efe94aaf1b6af9921  packages/ts/quant-api-client/src/paper.ts
3512246943e72c1550242b2f108d31f700c2b4057dcbf70f0c0551038a1a101f  packages/ts/quant-api-client/test/paper.test.ts
```

Software-design-philosophy: **10/10 for this bounded SDK policy change; eight diagnostics supported, failed rows:none.** The paper boundary remains describable in one sentence, with a smaller public interface than its validation/recovery implementation. Existing single ownership hides ambiguity decisions; consumers/generated DTOs do not change. Interface comments document original-ID/no-retry promises, the updated policy comment states the503 rationale, and the accepted design plus independent tests record deliberate design review. No shallow wrapper or additional configuration was introduced. This is not a score for the full DSH integration.

Root aggregate Verify Gate, process E2E, secret/security/SBOM and release acceptance remain parent-owned and are not inferred from these scoped checks.
