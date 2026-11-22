# BUILD REPORT: DSH native internal-paper Host

> Scoped Host implementation receipt; full product, installed authentication and release acceptance remain separate.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | DSH_PAPER_HOST, manifest 6–13 and 28 |
| **Date** | 2026-11-17 |
| **Author** | dsh_paper_host_build / SDD Build by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **DESIGN** | `sdd/features/DESIGN_DSH_PAPER.md` |
| **Status** | In Progress — scoped Host implementation/tests complete; parent aggregate acceptance pending |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | Nine owned items within the 34-file integration manifest |
| Cross-file coupling | High inside the Host: provider, fixed authority, generated SDK, Tool and carrier contracts |
| Security surface | Private Unix provisioning, fixed-session authorization, strict proposals and owner-carrier bridge |
| LLM prompt items | LP-001 unchanged; LP-002 static Tool interface guidance, no new runtime loop |
| Independent volume | Broker, SDK, UI and process tests have separate parent-assigned owners and disjoint paths |
| Context-rot risk | Bounded to one Host slice and its tests/report |
| Runtime capabilities | Parent coordinates implementation and independent review; this owner uses sequential default execution |

**Recommendation:** Sequential default work inside the Host slice preserves the coupled trust and lifetime contracts.

**User decision:** Existing session authorization and parent GO; no repeated permission requested. Parent explicitly released the source-write hold after shutdown commit `66476ad`, hosted CI and independent design ACCEPT. No worker dependency, Git or managed-profile mutations.

**Pre-build review:** Independent scoped ACCEPT in `sdd/reviews/REVIEW_DSH_PAPER_DESIGN_2026-11-17.md`, reviewed design SHA256 `9522a18cd5f21acae640bb781c622dacc0b1ff21876d904e3635769facfba923`. Later LP-002 classification correction is parent-owned.

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 9/9 owned items implemented with scoped verification; parent whole-slice gates remain open |
| **Files Created** | Seven: four source modules, two tests and this report |
| **Files Modified** | Two: Host composition and entry |
| **Files Deleted** | Zero |
| **Verification Commands Run** | Actual command ledger below; worker and parent execution are distinguished |
| **Verify Gate** | Not executed by this owner; parent aggregate gate remains required |
| **Execution Mode** | Default within the delegated Host slice |

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---:|---|---|---|---|---|
| 1 | 6 | Private provider and nonsecret operator validation | This owner | Verified | Plugin strict types; provider IPC test | Types exit0; parent IPC exit0, 31 assertions |
| 2 | 7 | Fixed-session generated-SDK facade | This owner | Verified | Plugin build/types; built-Host test | Parent Host exit0; SDK 503 policy remains in SDK owner |
| 3 | 8 | Five strict native-paper Tools | This owner | Verified | Strict test types/lint; built-Host test | Parent Host exit0; exact LP-002 wording; no mutation concurrency flag |
| 4 | 9 | Supported streaming exact panel route | This owner | Verified | Strict types/lint; built-Host test | Parent Host exit0; local512-byte/2-second bounds; physical auth remains separate |
| 5 | 10 | Private runtime composition and close effects | This owner | Verified | Build/types; built-Host test | Parent Host exit0; config before legacy settings, close-only lifetime |
| 6 | 11 | Register Tool and bridge lifecycle | This owner | Verified | Build; built-Host test | Parent Host exit0; separate legacy route and async route cleanup |
| 7 | 12 | Real temporary Unix provider regression | This owner, root executes | Verified | `node apps/dsh-plugin/test/paper-capability.ts` | Parent exit0, 31 private IPC assertions |
| 8 | 13 | Built Host/SDK/Tool/carrier regression | This owner, root executes | Verified | `node apps/dsh-plugin/test/paper.ts` | Parent reports actual mock Unix/HTTP exit0 |
| 9 | 28 | This evidence report | This owner | Verified | Template, evidence and whitespace review | Aggregate/independent acceptance deliberately remains open |

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `apps/dsh-plugin/src/lib/paper-capability.ts` | Create | 6 | Yes, scoped | No secret/env/legacy resolver imports; only resolve/close returned |
| `apps/dsh-plugin/src/lib/engine-paper.ts` | Create | 7 | Yes, scoped | Generated DTOs, fixed authority, control-before-I/O, scope and uncertainty |
| `apps/dsh-plugin/src/host-tools-paper.ts` | Create | 8 | Yes, scoped | Strict arguments and exact reviewed Tool guidance |
| `apps/dsh-plugin/src/host-paper-panel.ts` | Create | 9 | Yes, scoped | Optional supported exact carrier route, no raw web listener |
| `apps/dsh-plugin/src/host-runtime.ts` | Modify | 10 | Yes, scoped | Paper client close effect; supported streaming and async-disposer types; malformed Tool argument guard |
| `apps/dsh-plugin/src/index.ts` | Modify | 11 | Yes, scoped | Register native-paper Tools and route; legacy registrars unchanged |
| `apps/dsh-plugin/test/paper-capability.ts` | Create | 12 | Yes, scoped | Real private temporary sockets, no credential contents or inherited environment |
| `apps/dsh-plugin/test/paper.ts` | Create | 13 | Yes, scoped | Built Host plus real local mock HTTP and private broker |
| `sdd/reports/BUILD_REPORT_DSH_PAPER_HOST.md` | Create | 28 | Yes, scoped | This report |

## Prompts Generated / Refactored

| Inventory ID | Path | Type | Builder / receipt | Result and verification |
|---|---|---|---|---|
| LP-001 | Existing `host-runtime.ts` systemPrompt text | Existing external loop guidance | Existing inventory; no edit | Diff preserves the text byte-for-byte |
| LP-002 | `host-tools-paper.ts` descriptions/schema | Static Tool interface guidance | `sdd/reports/PROMPT_CONTRACT_DSH_PAPER_2026-11-17.md`; separate prompt-contract owner | Applied all five exact v1 descriptions; strict schema/runtime checks remain deterministic. No local model/provider/loop or model-compliance claim |

## Drift Detected

No material Host architecture/behavior drift. Parent corrected LP-002's classification from a runtime loop to static interface guidance consumed by the existing external DSH loop, after the prompt/loop skill applicability review. Host added no local LLM stage, budget or provider. The shared Tool wrapper rejects malformed non-object arguments before any registrar, supporting runtime schema enforcement without changing valid legacy calls.

## Verification Results

### Incremental Verification

| Command / Method | Executor | Exit / result | Evidence |
|---|---|---|---|
| `pnpm --filter @bybit-quant/dsh-plugin typecheck` | This owner, repeated after source/type edits | 0 | Strict TS source checks pass |
| `pnpm --filter @bybit-quant/dsh-plugin build` | This owner, three successful builds | 0 | Host/provider/facade packaged; final build includes exact Tool guidance and UI owner's completed source |
| `pnpm --filter @bybit-quant/dsh-plugin typecheck:tests` | This owner | First 1, corrected 0 | Local test self-referential type and union narrowing fixed; no `any` introduced |
| Targeted `pnpm exec oxlint` for eight owned source/test files | This owner | First 1, corrected 0 | Replaced unnecessary Map spread; moved no-capture helper to module scope; removed test shadowing |
| `node apps/dsh-plugin/test/paper-capability.ts` | This owner | 1, environment refusal | Unix `listen` failed EPERM before runtime assertions; not a code/test pass |
| Same provider command, initial and final-source rerun | Root, unrestricted execution | 0 both times, parent-reported | 31 bounded private IPC assertions; final frozen provider rerun approximately0.54 seconds after no-useless-spread correction; canonical EOF/scope/path/inode/saturation/close and safe failures |
| `node apps/dsh-plugin/test/paper.ts` | Root, unrestricted execution | 0, parent-reported | Actual mock Unix/HTTP: private provider/SDK, strict Tools, fixed session, opt-in,503/original-ID recovery, streaming guards, abort and independent lifetime |
| `git diff --check` and owned-file `wc -l` | This owner | 0 | Longest owned source is `host-runtime.ts` at 341 lines; other owned sources below 150 lines; tests below 500 |

The provider test proves split canonical replies, fresh resolution, exact tuple, extra/duplicate/noncanonical/malformed frames, delayed trailing frames, missing EOF timeout, four-socket saturation refusal, final close, unsafe directory/socket modes, socket/parent symlinks, non-socket file rejection, directory mutation and inode replacement. Synthetic token comparisons use boolean assertions and fixed messages so an assertion does not dump the token.

The parent-executed built-Host test verifies no background work, explicit missing temporary credential file, zero exchange credential resolution, five strict schemas and runtime guards, no mutation concurrency mark, default-disabled and control-disabled no-I/O, fixed context, all operation scope failures, SDK-owned mutation503 recovery/no retry, original DTO identity capture, not-found followed only by explicit lookup, streaming route methods/HEAD/no-store/media/origin/query/body/timeout/abort rejection, cancelled late provider preventing HTTP, client close and independent service lifetime. Carrier identity/authentication is mocked and not certified by this unit.

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `pnpm run verify` from DEFINE |
| **Exit / Result** | Not run by this owner |
| **Status** | Pending parent aggregate integration |
| **Evidence** | SDK, broker, UI, process E2E, independent review and release gates belong to their assigned owners; no partial unit substitutes for the DEFINE command |

### Manual UX Receipt

N/A for this worker. Actual installed owner/auth and UI behavior remain separate pending evidence.

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | Targeted oxlint for owned sources/tests | Pass | Exit0 after local corrections |
| Typecheck | Plugin source and test targets | Pass | Exit0 |
| Tests | Provider and built-Host commands | Scoped pass | Root provider exit0 and Host runtime exit0 |
| Build / Compile | Plugin build | Pass | Exit0; generated dist is not handwritten source |

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-002 | Strict TypeScript and source ≤500 | Scoped pass | Actual build/types, source line count |
| AT-007 / AT-021 | Untrusted proposals cannot alter authority or risk | Scoped pass | Strict schema and runtime proposal no-I/O guards; full service risk acceptance remains separate |
| AT-010 | Host does not own service lifetime | Scoped mock pass; real process separate | Actual mock service remains usable after Host close; native process E2E owned separately |
| AT-013 | Sole Python-generated paper DTO source | Scoped pass | Facade imports existing SDK types; no wire schema changes |
| AT-015 / AT-016 | Original-ID uncertainty and fixed internal-paper authority | Scoped pass | SDK503 and all operation scope checks pass in parent Host test; real native/reconciliation remains separately gated |
| AT-027 / AT-028 | Supported native-paper Tools and exact bridge | Partial | Build/types; installed physical carrier auth/UI gate remains open |
| AT-003 / AT-008 / AT-031 | Lifecycle/security/SBOM/release matrix | Parent-owned, incomplete | This worker performed no install, exchange call, scan, commit or push |

## Advisor Ledger

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| 1 | Pre-build | R1 SDK mutation503 may follow dispatch | Medium | APPLIED by SDK owner | Host consumes SDK uncertainty and does not duplicate its503 policy |
| 2 | Pre-build | R2 complete EOF required both directions | Medium | APPLIED | Provider half-closes canonical request, waits entire response EOF under one500ms/1KiB budget; actual provider tests |
| 3 | Pre-build | R3 lifecycle permission differs from readiness | Low | APPLIED by UI owner | Host returns generated readiness/state facts unchanged; card tests owned separately |
| 4 | Prompt contract | LP-002 is static guidance, not a new local loop | Scope correction | APPLIED by parent / this owner | Parent design correction and exact five description integration |

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Worker sandbox refuses Unix listen | Root executes exact commands unrestricted; no worker escalation | Provider and Host receipts explicitly attributed |
| 2 | Local test compile and lint findings | Corrected explicit test types/narrowing and scoped code style | Final strict checks pass; no acceptance relaxed |

Parent Host runtime completed with exit0. Environmental refusal did not trigger speculative code fixes or change resource/scope criteria.

## Deviations from Design

No material behavioral deviation. Ancestor path checks also enforce root/current uid and refuse writable ancestors except explicitly root-owned sticky `/private/tmp` or Linux `/tmp`; final dedicated parent and socket remain same-user0700/0600. This concrete policy was aligned with the Python broker owner before source writes.

### Software-design-philosophy assessment

Scoped implemented-boundary self-assessment: **8.75/10, seven of eight diagnostics evidenced**. Each module has one purpose; provider/facade interfaces hide substantially more complexity than they expose; Tools/UI do not share the IPC format; interface comments explain authority/lifetime; provider hides filesystem/protocol/resource policy, facade hides fixed authorization/session trust; names/context keep native and legacy authority visible; deliberate read-only prebuild protocol/design alignment preceded implementation. The remaining row is independent discussion/review of the implemented security decisions: accepted design review is not code acceptance. Required change to reach the implemented10/10 target: independent reviewer inspects the frozen code and actual receipts, then resolves findings without lowering the contract. This owner does not self-award independent acceptance.

### Frozen source/test hashes

Actual `shasum -a 256` command exit0 after root Host runtime pass and final worker strict checks:

| File | SHA256 |
|---|---|
| `src/lib/paper-capability.ts` | `a1fd30e11574fb61b23460340e681be878d355963c104d6f2581e1a9b3b40d43` |
| `src/lib/engine-paper.ts` | `048a9df3e8737e46db315d4fef75d0130e496f611c0ffbcc1937a1d482359625` |
| `src/host-tools-paper.ts` | `32d393c70432621afbcba89f52cd08ea4ff4f5308c273e0a0b36251eb0347e30` |
| `src/host-paper-panel.ts` | `4f9698208426a5a732be0e16826c5961a21247ed465e291eaae9bd8608c9fdfc` |
| `src/host-runtime.ts` | `fea24133ff704ee9d8309b1c9b7dd6475cef248703f91acce75a555cd2acb5f3` |
| `src/index.ts` | `b4383db62269d5aa2b2629c028c2f5a3a0f3ce29ab88cc5c3c759587f9488067` |
| `test/paper-capability.ts` | `dff2ce4c230deab61445573fec0965f8b583334d8676ae775489d2fa2dcc0751` |
| `test/paper.ts` | `866089435378ef62f1048543f2172584b7c707ad387a9911a4cd163dd755630e` |

All table paths are relative to `apps/dsh-plugin/`. Source/test files are frozen for independent review; generated dist and shared integration work remain separately owned.

## Blockers

| Blocker | Required Action | Owner |
|---|---|---|
| Integration and whole-slice acceptance | Wire unit commands, real native E2E, independent review, installed auth/UI and aggregate Verify Gate | Assigned integration/review owners and parent |

## Final Status

### Overall: IN PROGRESS

- [x] All owned File Manifest tasks have scoped receipts
- [x] Incremental worker checks and attributed provider receipt recorded
- [ ] Parent Verify Gate green for final integrated tree
- [x] Applicable worker build/type/lint checks pass
- [x] Scoped Host runtime verified
- [ ] Required external/integrated acceptance verified
- [x] LLM inventory and exact static guidance receipt recorded
- [x] Drift decisions recorded
- [x] Pre-build findings disposed by assigned owners
- [ ] No unresolved acceptance blocker
- [x] No TODO/FIXME used as unfinished implementation
