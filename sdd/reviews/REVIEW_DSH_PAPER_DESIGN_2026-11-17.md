# Independent pre-build review: DSH native paper integration

Date: 2026-11-17. Reviewer: `paper_dsh_design_review`, independent of design author. Scope: `DESIGN_DSH_PAPER.md` and current paper API/SDK/DSH carrier source. **Final verdict: scoped design ACCEPT after independent recheck; R1–R3 closed in the design contract.** Initial HOLD and its evidence are retained below. This is design acceptance only; shutdown repair, implementation, installed owner/auth UI and release gates remain separate.

## Top risks and specific fixes

| ID | Severity | Finding and evidence | Required disposition |
|---|---|---|---|
| R1 | P2 | Mutation HTTP503 may follow real side effects. `paper_admission.py:225` persists a decision; lines232–242 claim dispatch and call `runtime.submit`; subsequent drain/ledger lookup can fail; lines247–249 raise `PaperUnavailable`, mapped to503 by `paper_api.py:71–73`. SDK `paper.ts:40–45` excludes `unavailable` from uncertainty. Design Error Handling currently preserves503 as plain unavailable, losing explicit original-identity recovery. | Amend the existing SDK owner, `packages/ts/quant-api-client/src/paper.ts` and `test/paper.test.ts`, and add both to the manifest. Mutation503 must conservatively produce `outcome_uncertain`, cause `unavailable`, with original `query_request` for submit or `query_status` for start/stop. GET503 stays unavailable. Test all three mutations and zero retries. Keep facade session binding separate. |
| R2 | P2 | Canonical JSON comparison at Decision3 correctly rejects duplicate keys, but stream completion is unspecified. Parsing only through the first LF cannot reject a delayed trailing frame; waiting for EOF without specifying sender half-close can deadlock both ends. | State request half-close explicitly: provider `end(requestFrame)`; broker reads through EOF within its total500ms/1024-byte bound, validates the complete bytes, then responds and closes. Provider validates the complete response through EOF under its own bound. Add golden/split/delayed-trailing/no-EOF tests. Equivalent precisely defined framing is acceptable; do not promise detection the implementation cannot provide. |
| R3 | Low | UI `ready` is execution readiness, not lifecycle permission. Actual `_status` is always `ready:false` before first start and can be unready/protected while a native process still requires Stop. The present prose does not explicitly define per-action availability. | Add a small action table: scoped idle permits Start despite `ready:false`; scoped running/protected/unready may offer explicit Stop; stopped/protected cannot Start. Configuration/control opt-in and one-pending-request gates still apply. Cover idle-first-start and protected/native-alive-stop. |

Each finding was sent to the design author and parent before this receipt. R1 belongs in the SDK rather than a DSH-only workaround; the SDK already owns mutation ambiguity policy. R3 is a bounded clarification, not a new readiness model.

## What to retain and ignore

Retain service-owned prebound numeric-loopback listener before capability disclosure, admission-open prerequisite, exact broker tuple, no cache/fallback, four pre-admitted connections, private path/inode checks, independent provider close/deadline, and fixed-session checks on every successful facade result. Existing SDK transport checks cancellation after provider resolution, preventing a late callback from sending HTTP. Generated Python wire schemas remain authoritative; by-request responses lack `request_id`, so do not invent one for correlation. Retain default-off control, original-ID query-only recovery, truthful synthetic/native labels, owner-authenticated exact route, streaming body limits and installed-auth receipt gate.

Canonical fixed-order compact ASCII JSON byte equality already replaces the vague duplicate-key condition; no second JSON parser is required. Same-user hostile compromise/process attestation, generic credential storage, a Host supervisor, full exchange cutover and new user approval for authorized paper work are outside this review. The separate shutdown repair must not be expanded or certified here.

## Inspection evidence and limits

All following read-only commands completed with exit0. No test, process launch, network request, dependency install, Git mutation, credential file or `.env` read occurred. Only this review receipt was written.

| Actual commands / inspected inputs | Result |
|---|---|
| `cat AGENTS.md`; project `software-design-philosophy/SKILL.md`; `sdd-design/SKILL.md` and `references/advisor-review.md` | Repository boundaries and review/ledger requirements read. |
| `cat` full project Brainstorm/Define and DSH paper design/static-evidence report; line-numbered targeted rereads | Requirements, scoped manifest, protocol and uncertainty contract checked. |
| `cat` current SDK paper/transport/index/validation and Python paper API/bootstrap/config/models/admission; targeted `nl`/`rg` | R1 actual source path and R3 readiness distinction verified; no runtime side-effect claim. |
| `cat` current Host runtime/panel/read-only engine and Client types/engine; existing SDK review receipt | Current integration seam and prior scoped acceptance limits verified. |
| Read-only Node ASAR traversal of installed `dsh-client-connection` rpc/rpc-host/index/trust/browser-auth source | GET/HEAD/POST, streaming mode, async disposer, physical admission and owner-only exact dispatch confirmed. All five source SHA256 values match the companion design evidence report. No app/profile code executed. |
| `sed` installed Uvicorn server source | Public `Server.run(sockets=...)` and `loop.create_server(sock=...)` verified. |
| `shasum -a 256` design/SDK/API/admission | Reviewed snapshots below. |

```text
f0303dd2018f5b1a03fd137fb19e467396f6fab2600bc76e35476900d4629f57  sdd/features/DESIGN_DSH_PAPER.md
55720552c62a4277065d4af85e6ebb9a4d3bcd97db2ebda0f8646d14f70f15b0  packages/ts/quant-api-client/src/paper.ts
33891a13ead5a0ca9391dd284034c5235dcb97693be54a62b36ff69841ac0cc0  python/apps/quant-engine/src/quant_engine/paper_admission.py
06099467a81991bc94ae5300da4b7ffd5220eb1079e3c1418879449f824670c3  python/apps/quant-engine/src/quant_engine/paper_api.py
```

Software-design-philosophy proposed-design score: **7.5/10, six of eight rows supported**. Failed rows: abstraction promises are incomplete (R1/R2), and a newcomer must inspect implementation to distinguish lifecycle action availability from readiness (R3). Apply the bounded corrections above to reach a design target10/10; no implemented-boundary score is raised by this review. The modules otherwise hide substantive decisions rather than forwarding methods. Record every R1–R3 disposition as APPLIED/REBUTTED in the design Advisor Ledger and obtain a brief recheck before Build acceptance.

## Independent recheck: scoped design ACCEPT

Re-read the frozen revised design and added evidence on 2026-11-17. Reviewed design SHA256: `9522a18cd5f21acae640bb781c622dacc0b1ff21876d904e3635769facfba923`.

| Finding | Verified disposition |
|---|---|
| R1 | APPLIED. Existing SDK owner/files33–34 own all mutation503 uncertainty, original submit/status recovery and zero retry; GET503 remains unavailable. Facade only adds fixed-session authority. Code Patterns, Error Handling and tests agree. Test18 additionally requires an explicitly injected503 after a real service202, then original-request lookup preserving command/native identity; it does not claim the injection is a naturally observed production failure. |
| R2 | APPLIED. Decision3 requires request half-close, broker complete-request EOF before disclosure and provider complete-response EOF before trust; each side retains a total500ms/1024-byte budget. Required golden, split, delayed-trailing and no-EOF tests cover both directions. |
| R3 | APPLIED. Action table explicitly permits idle/ready:false Start and running/protected native-alive Stop, prevents protected/stopped Start, and disables conflicting actions during pending/uncertain state. UI tests include both regression cases. |

Actual recheck commands, all exit0: line-targeted `sed`/`nl`/`rg` reads of the revised design/evidence; `shasum -a 256`; an independent inline `python3` static validator checking exactly34 manifest IDs, referenced dependency existence, actual graph acyclicity, R1–R3 anchors, final footer and trailing whitespace. Validator output: `review_recheck_manifest34_dag_contract_anchors_footer_whitespace_ok`. Forward references33→7 and34→18 are legitimate stable IDs, not cycles. No implementation or runtime test was run by this reviewer.

**No unresolved design P1/P2 findings. Final proposed-design score10/10, eight diagnostics supported; failed rows:none.** This score describes the revised contract only. Build must still implement and independently test the promises, including strict framing/resource limits, real native lifecycle/recovery, no secret output and actual installed owner/auth behavior. The existing integrated implementation score and product/release status remain unchanged.
