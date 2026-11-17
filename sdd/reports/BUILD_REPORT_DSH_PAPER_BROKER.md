# BUILD REPORT: DSH internal-paper capability broker

> Python provisioning/listener/lifespan slice only; no full quant-platform or release acceptance.

## Metadata

| Attribute | Value |
|---|---|
| Feature | DSH_PAPER_BROKER, DSH_PAPER manifest1–5,27 |
| Date | 2026-11-17 |
| Author | dsh_paper_broker_build / SDD Build by RDD |
| BRAINSTORM | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| DEFINE | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| DESIGN | `sdd/features/DESIGN_DSH_PAPER.md`, frozen SHA256 `9522a18cd5f21acae640bb781c622dacc0b1ff21876d904e3635769facfba923` |
| Status | Scoped implementation verified; independent implementation review and parent aggregate acceptance pending |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | Six owned paths, including this report |
| Cross-file coupling | High within broker/bootstrap/lifespan; explicit narrow open/close boundary |
| Security surface | Local private capability, Unix path/uid/mode/inode policy, bounded handshakes, HTTP prebinding |
| LLM prompt items | None in this Python slice; product LP-001/002 belong to Host owner |
| Independent volume | Disjoint Python owner coordinated with Host/UI/SDK/process owners |
| Context-rot risk | Bounded six-file slice |
| Runtime capabilities | Default sequential implementation inside explicitly delegated worker; independent root process execution |

**Recommendation:** default within the delegated slice, to keep the protocol and lifecycle coherent.

**User decision:** existing authorized project work and explicit parent delegation;
parent issued GO after remote shutdown baseline66476ad and hosted CI44095731073
were independently confirmed. No duplicate authorization was requested. Preparation
was read-only before GO. No new agent was spawned by this worker.

**Pre-build review:** independent scoped design ACCEPT in
`sdd/reviews/REVIEW_DSH_PAPER_DESIGN_2026-11-17.md`; implementation acceptance is separate.

## Summary

| Metric | Value |
|---|---|
| Tasks Completed |6/6 scoped implementation/report tasks; independent review and parent gate separate |
| Files Created | Four: broker, two tests, this report |
| Files Modified | Two: bootstrap, API lifespan |
| Files Deleted | Zero |
| Verification Commands Run | Actual commands/receipts below, including failures |
| Verify Gate | Parent aggregate gate not executed by this worker |
| Execution Mode | default within delegated worker |

Broker mode generates one capability in process memory, binds the actual exclusive
numeric-loopback HTTP listener, opens existing admission, then publishes its private
Unix broker. The optional inherited FIFO mode remains a distinct CLI mode. There
is no credential discovery, dependency change, service supervisor, migration at
startup, new fill model or exchange access.

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---:|---|---|---|---|---|
|1 |1 | Private broker and bounded lifecycle | delegated Python owner | Complete, scoped |29 real IPC cases | Final root combined run exit0 |
|2 |2 | Opt-in socket CLI and exclusive prebound HTTP | delegated Python owner | Complete, scoped | Actual CLI tests and `--help` | Port conflict before DB/broker publication; actual listener cleanup |
|3 |3 | Broker starts after admission and closes before engine | delegated Python owner | Complete, scoped | Actual startup/SIGTERM cases; schema checks | Existing HTTP DTOs unchanged; failed admission publishes no socket |
|4 |4 | Protocol/path/resource/redaction tests | delegated Python owner | Complete, scoped | Actual Unix peers |29 cases, no skipped cases |
|5 |5 | Actual CLI/prebind/FD/native/failure tests | delegated Python owner | Complete, scoped | Seven process cases | Native reaping, protected restart, FIFO regression and failures pass |
|6 |27 | Auditable Build report | delegated Python owner | Complete for scoped receipts | Report/source/diff review | Whole-product root gate/review remain explicitly pending |

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `python/apps/quant-engine/src/quant_engine/paper_capability.py` | Create |1 | Yes, scoped | Canonical local IPC, private paths, hard bounds, inode cleanup |
| `python/apps/quant-engine/src/quant_engine/paper_bootstrap.py` | Modify |2 | Yes, scoped | Exclusive HTTP socket passed through public Uvicorn Server interface |
| `python/apps/quant-engine/src/quant_engine/paper_api.py` | Modify |3 | Yes, scoped | Optional broker lifecycle after successful engine.open |
| `python/apps/quant-engine/tests/test_paper_capability.py` | Create |4 | Yes, scoped | Fixed exceptions prevent token-bearing assertion operands |
| `python/apps/quant-engine/tests/test_paper_capability_process.py` | Create |5 | Yes, scoped | Fresh temporary migrated DB only; sanitized PATH/LANG child environment |
| `sdd/reports/BUILD_REPORT_DSH_PAPER_BROKER.md` | Create |27 | Yes, scoped | This report |

## Prompts Generated / Refactored

None in this slice. Product inventory LP-001/002 remains with the Host owner; no
runtime LLM call, prompt, provider or model is added here.

## Drift Detected

No material requirement or architecture drift. Exact comparison to the configured
canonical request bytes accepts precisely the specified ordered JSON/ASCII/LF
tuple and rejects duplicate keys, alternate encodings and trailing frames without
parsing attacker JSON. Response serialization owns the same explicit golden
fixture as the Host: paper-test / http://127.0.0.1:8766.

The Python slice is explicitly listed in the frozen design and existing uv
workspace; the repository's handwritten TypeScript rule applies to the DSH plugin
and tooling, not a conversion of the explicitly specified Python service.

## Verification Results

### Incremental Verification

| Actual command / method | Exit | Evidence |
|---|---:|---|
| `python/.venv/bin/python -m pytest python/apps/quant-engine/tests/test_paper_capability.py -q` in worker sandbox |1 |20 socket-dependent failures at Unix bind EPERM,9 passed; not acceptance |
| Same focused IPC file, approved unrestricted execution with `--tb=short` |1 |28 passed, one close diagnostic still reported4 completed handlers; explicit awaited-task removal corrected bookkeeping |
| Root `python/.venv/bin/python -m pytest python/apps/quant-engine/tests/test_paper_capability.py python/apps/quant-engine/tests/test_paper_capability_process.py -q --tb=short` |1 |32 passed,4 fixture failures in12.92s; log `/private/tmp/bybit-dsh-broker-tests.log` |
| Root `python/.venv/bin/python /private/tmp/bybit-paper-broker-roles.py` |0 | Allowlisted role probe confirmed tracker payload/interpreter match and inherited -B/-s flags; canonical unflagged match false; no raw argv/token printed |
| Final frozen root `python/.venv/bin/python -m pytest python/apps/quant-engine/tests/test_paper_capability.py python/apps/quant-engine/tests/test_paper_capability_process.py -q --tb=short` |0 |36 passed in13.42s; attributed parent execution receipt, log `/private/tmp/bybit-dsh-broker-tests-final.log` |
| `python/.venv/bin/ruff check python/apps/quant-engine` |0 | Final full app lint, all checks passed |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/apps/quant-engine` |0 | Final full app0 errors/0 warnings |
| `python/.venv/bin/ruff format --check` with explicit five modified/new Python paths |0 | Five files already formatted |
| `python/.venv/bin/quant-engine-openapi --paper --output contracts/openapi/quant-paper.v1.json --check` |0 | Existing paper schema unchanged |
| `python/.venv/bin/quant-engine-openapi --output contracts/openapi/quant-engine.v1.json --check` |0 | Existing read-only schema unchanged |
| `python/.venv/bin/python -m quant_engine.paper_bootstrap --help` |0 | Required mutually exclusive FIFO/socket mode shown |
| Worker selected non-socket path and CLI-mode tests |0 | Six path tests and two CLI parser tests pass; deselections reported, not whole-file acceptance |
| `git diff --check`; explicit owned source/report line/whitespace/hash validator |0 | Tracked and new files clean; handwritten Python counts217/59/167/263/263, all≤500; no unfinished source |

The initial process failures were fixture errors, not weakened safety criteria.
Installed Uvicorn Server.startup explicitly exits STARTUP_FAILURE(3) when lifespan
fails; two tests incorrectly expected argparse2. They now require3 and silent
output. The test environment's PYTHONNOUSERSITE/PYTHONDONTWRITEBYTECODE generated
-s/-B tracker arguments. Root's actual diagnostic confirmed the shape. Removing
those unnecessary flags retains a fully allowlisted PATH/LANG environment and
the existing strict PaperChildren classifier untouched. Native reaping is still
immediate; tracker inactivity still has its accepted separate bounded deadline.

Worker permissions remained stale after the parent gained unrestricted access:
Unix bind still returned EPERM. One intermediate escalation diagnostic did not
execute because automatic approval review timed out; this was not a safety
rejection or a successful test. Root therefore executes real local socket/process
checks. No permission failure is represented as passed coverage.

The final36-case receipt is from the parent executing the frozen five-file
snapshot, not an execution claimed by this worker. The broker source SHA256 is
`94eaff22e822886aa94597d98b1d2d4b8f59d0de68addf449f0126afd1145430`;
process-test SHA256 is
`bc7dc730ae053ca18fab2dcb241b7714ff6cc41aed910a00bb26bd71b3ddd578`.
No source changed after that frozen run. Independent implementation review is
the next parent-owned gate, not inferred from these passing tests.

### Verify Gate

| Attribute | Value |
|---|---|
| Kind | test |
| Command / Method | `pnpm run verify` from DEFINE; parent-owned aggregate execution |
| Exit / Result | Not run by this worker against this slice |
| Status | Pending parent gate; no green inference from earlier baseline |
| Evidence | Scoped Python checks above do not replace DEFINE/root gate |

### Manual UX Receipt

N/A for Python slice. Installed DSH owner/auth/UI acceptance remains separate.

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | Full quant-engine Ruff | Pass | exit0 |
| Typecheck | Full quant-engine Pyright with explicit venv | Pass | exit0 |
| Tests | Final36 IPC/process cases | Pass | Parent unrestricted exit0,13.42s; no skips |
| Build / Compile | Both existing schema drift checks | Pass | exit0; source DTOs unchanged |
| Dependencies / SBOM / secret scans | Parent aggregate release checks | Pending parent | No dependency/lock change by worker |

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-010, scoped paper independent lifecycle | Exclusive HTTP prebind, broker starts only after admission; actual native SIGTERM cleanup | Scoped pass | Final actual CLI cases; native worker reaped, tracker inactive, HTTP and broker removed |
| AT-016 | Exact internal_paper/session/origin binding | Scoped IPC pass | Wrong tuple and malformed canonical request receive no response |
| AT-007/021 | Untrusted broker bytes never set risk/execution truth | Scoped IPC pass | Strict fixed request tuple; existing admission/risk/native code unchanged |
| AT-014/015/029 | Native lifetime and protected restart | Scoped process pass; full acceptance incomplete | Actual native start/stop/SIGTERM and protected restart; no new fills, replay or exchange reconciliation |
| AT-013 | Existing Python DTO schemas unchanged | Pass for drift check | Both canonical schema commands exit0 |
| Full product MUSTs | Full strategy/data/AI/recovery/exchange/installed DSH matrix | Incomplete outside slice | No broader acceptance inferred |

## Advisor Ledger

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| R2 | Pre-build independent design | Request and response must complete through EOF under unchanged total bounds | Medium | APPLIED | Callback admission≤4 before task creation,1024-byte cap,500ms total read/response, half-close tests |
| P-1 | Root runtime observation | Environment flags broke the strict unflagged tracker fixture | Test fixture | APPLIED | Actual allowlisted diagnostic; removed only unnecessary fixture flags |
| P-2 | Root runtime observation | Lifespan startup exit is public Uvicorn3 | Test fixture | APPLIED | Installed Server.startup inspected; no application semantic change |

Current author-assessed software-design-philosophy score **8.75/10 (7/8)** for
this broker boundary. Failed diagnostic: implementation design review is still
pending; independent code review must confirm that the simple open/close API
hides the path/protocol/resource/cleanup decisions before reaching10/10. Each
module has a single purpose, interfaces hide implementation, DTO ownership is
unchanged, invariants are documented, and the security/lifecycle design received
dedicated upfront work. No independent implemented-boundary score is claimed.

## Issues Encountered

Infrastructure EPERM and the review timeout are recorded above. Root runtime
found two fixture assumptions and one close-diagnostic bookkeeping issue; all
were corrected without relaxing bounds, native reaping or failure criteria.

## Deviations from Design

None in intended behavior. No user database, credential/.env, managed profile,
dependency/lock, Git operation, actual exchange call or order was accessed.

## Blockers

| Blocker | Required Action | Owner |
|---|---|---|
| Independent implementation and aggregate gate pending | Review final source, execute root gate/security/release checks | Parent/integration reviewer |

## Final Status

### Overall: IN PROGRESS at integration acceptance; scoped broker implementation verified

- [x] Owned implementation and tests written; no out-of-manifest source edited.
- [x] Final static/schema checks recorded.
- [x] Earlier runtime failures recorded and corrected from actual evidence.
- [x] Frozen36-case runtime receipt green, attributed parent execution.
- [ ] Independent implementation review and parent Verify Gate green.
- [x] Full product gaps remain explicit; no unfinished TODO/FIXME substitutes.

Parent owns the full DSH Build/Release outcome. No completion handoff is emitted
while independent implementation review and the aggregate gate remain pending.
