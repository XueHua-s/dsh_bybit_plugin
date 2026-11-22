# BUILD REPORT: Paper shutdown observation

## Metadata

| Attribute | Value |
|---|---|
| Feature | PAPER_SHUTDOWN_OBSERVATION |
| Date | 2026-11-17 |
| Author | paper_shutdown_fix / SDD Build |
| BRAINSTORM | sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md |
| DEFINE | sdd/features/DEFINE_BYBIT_AI_QUANT.md, AT-010/015 |
| DESIGN | sdd/features/DESIGN_PAPER_SHUTDOWN_OBSERVATION.md; existing PAPER_NATIVE/ADMISSION |
| Status | Complete for scoped correction; independent ACCEPT and parent Verify Gate green |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 3: prior design supplement, one test file, this report |
| Cross-file coupling | Low; application lifecycle/API/schema unchanged |
| Security surface | No exchange/account/credential/configuration access; synthetic temporary databases and loopback only |
| LLM prompt items | None in this slice |
| Independent volume | One focused regression, independent reviewer assigned by parent |
| Context-rot risk | Low |
| Runtime capabilities | Parent assigned scoped worker; sequential default within worker |

Recommendation: default for one test-only implementation file. Parent explicitly
authorized this execution and later independent review; no duplicate mode approval
was required. No new subagent was spawned by this worker. No Git operation,
installation, dependency update, deployed migration or release was performed.

## Summary

| Metric | Value |
|---|---|
| Tasks completed | 3/3 |
| Files created | 2 documentation artifacts |
| Files modified | 1 existing Python test file |
| Files deleted | 0 |
| Verify Gate | Green, attributed parent execution receipt |
| Execution mode | default within explicitly delegated worker |

## Task Execution

| ID | Task | Executor | Status | Evidence |
|---|---|---|---|---|
| PS-1 | Record evidence, lifecycle observation contract and manifest before source edits | paper_shutdown_fix | Complete | Original eight-cycle actual subprocess observation; supplement written before source |
| PS-2 | Identity-aware child roles, strict native reaping, bounded tracker inactivity, delayed-tracker regression and SIGKILL checks | paper_shutdown_fix | Complete for scoped tests | Initial 4 cases and five independent 4-case suites pass; final classifier verification below |
| PS-3 | Actual evidence and limits in this report | paper_shutdown_fix | Complete | Independent ACCEPT and parent root Verify Gate exit 0 received |

## Files Changed

| File | Action | ID | Verified | Notes |
|---|---|---|---|---|
| sdd/features/DESIGN_PAPER_SHUTDOWN_OBSERVATION.md | Create | PS-1 | Yes | Prior design and independent classifier correction recorded |
| python/apps/quant-engine/tests/test_paper_process.py | Modify | PS-2 | Yes, scoped | No application source changed |
| sdd/reports/BUILD_REPORT_PAPER_SHUTDOWN_OBSERVATION.md | Create | PS-3 | Yes | This report |

## Drift Detected

The hosted documentation follow-up CI 44091570414 failed one immediate PID-only
absence assertion at test_paper_process.py:105. Its surviving PID 4770 was not
classified or captured with creation time. Its role cannot be recovered from
the supplied log, so the exact historical PID is not claimed to be a tracker.

The unmodified actual CLI probe reproduced the same assertion failure condition:
of eight SIGTERM cycles, one observed native PID 98719 already gone while
resource_tracker PID 98718 / create time 1794921950.643889 still ran after service
wait. Tracker vanished1.438 ms later. All eight native children were already
gone at the service exit boundary. CPython 3.12.16 source explicitly starts a
resource tracker that outlives its parent and reads until pipe EOF; native
PaperRuntime instead explicitly joins its worker. This is evidence for fixing
the observation contract, not changing application shutdown or retrying CI.

The graceful native check remains immediate and strict: even a native zombie
fails. Captured psutil.Process identities protect against PID reuse. SIGKILL
requires native inactivity within the existing 8 s watchdog boundary; orphan
zombies are inactive but cannot be reaped by the killed owner. Trackers have a
separate 3 s inactivity deadline; live/sleeping/stopped trackers fail. Tracker
zombies reflect exit pending OS reparent reaping and never satisfy native proof.

Independent adversarial review rejected matching tracker text in arbitrary argv:
an unknown sleeper with tracker-shaped data was misclassified. Final matcher
requires exactly the same interpreter path as this test's unflagged server
launch, `-c`, and the full stdlib `main(decimal_fd)` payload with no suffix/extra
arguments. Unknown shapes remain native. This correction was recorded in the
design supplement before source correction. No requirement drift occurred.

## Verification Results

### Incremental verification

| Actual command / method | Exit | Evidence |
|---|---:|---|
| python/.venv/bin/python /private/tmp/bybit-paper-shutdown-observe.py | 0 | Eight unmodified actual CLI/native/SIGTERM cycles; one reproduced asynchronous tracker exit 1.438 ms after owner wait |
| uv run --project python --locked pytest python/apps/quant-engine/tests/test_paper_process.py -q | 0 | Initial helper version:4 passed in 11.74 s, including ordinary SIGTERM, paused tracker, idle crash and dispatched SIGKILL |
| Five independent subprocess invocations of python/.venv/bin/python -m pytest python/apps/quant-engine/tests/test_paper_process.py -q | 0 each | Pre-classifier-refinement:4 passed each in 11.35 / 11.08 / 11.67 / 11.55 / 11.27 s; exits[0,0,0,0,0]; stopped on first failure would have aborted loop |
| python/.venv/bin/python -m pytest python/packages/quant-execution/tests/test_paper_runtime.py -q | 0 | 11 passed in 11.92 s, real native persistence/cleanup, forced deadline and normal/blocked native owner SIGKILL |
| python/.venv/bin/python -m pytest python/apps/quant-engine/tests -q | 0 | Pre-classifier-refinement:116 passed in 23.33 s; one existing Starlette/httpx deprecation warning |
| python/.venv/bin/python -m pytest python/apps/quant-engine/tests/test_paper_process.py -q | 0 | Final exact classifier:4 passed in 11.89 s; ordinary SIGTERM, delayed tracker, idle crash and dispatched SIGKILL |
| python/.venv/bin/ruff check python/apps/quant-engine | 0 | Final classifier source, all checks passed |
| python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/apps/quant-engine | 0 | Final classifier source,0 errors / 0 warnings |
| python/.venv/bin/ruff format --check python/apps/quant-engine/tests/test_paper_process.py | 0 | Final classifier source, already formatted |
| Source line/trailing-whitespace and SHA-256 check | 0 | Final classifier 234 lines; SHA eabc56743dac53e3569d81fa6ba6adec6c15734cd3e4051d0214cecb57ff1fab; below 500 |

Final classifier actual 4-case process receipt is green. Parent explicitly judged
one final focused run plus adversarial classifier
review and Ruff/Pyright sufficient after this classifier-only correction; the
earlier 20 cases are not represented as executions against the final matcher.

Actual process/socket tests ran with approved unsandboxed loopback/process
inspection. First sandboxed probe exited 1 at loopback bind PermissionError; no
process test ran there. Sandboxed uv Ruff/Pyright attempts exited 2 because shared
uv cache was not writable, so installed tools ran directly with explicit venv
Python. A first direct Pyright invocation without --pythonpath exited 1 because
root-context pytest import resolution used the wrong interpreter; explicit venv
Pyright passed. A sandboxed tracker argv inspection exited 1 at psutil/sysctl
permission denial; final actual service tests verify the real invocation shape.
These infrastructure failures are not counted as passed tests.

An optional unconfigured Markdown formatting attempt used
`node_modules/.bin/prettier --write` and `--check` on these two documentation
files; both exited 127 because that executable is not installed. No formatter
or dependency was installed and no Markdown formatter pass is claimed. The root
manifest has no Markdown formatting command. Direct trailing-whitespace checks
on both documents passed with exit 0; Python's configured Ruff format check passed.

The native deliberate-crash suite emitted a CPython resource_tracker warning
about 9 semaphore objects to clean up at shutdown. This is recorded as actual crash
cleanup output, not a claim that the suite produced no warnings. The fixed engine
process tests explicitly observe both native and tracker inactivity separately.

Independent final reviewer receipts, attributed to
`sdd/reviews/REVIEW_PAPER_SHUTDOWN_OBSERVATION_2026-11-17.md`: final process file
4 passed in 11.11 s / exit 0; unchanged native lifecycle 11 passed in 12.16 s /
exit 0; actual helper negative/identity/classification probe exit 0; both actual
failure-injection cleanup modes exit 0 in 1.948 s and 2.097 s; independent
Ruff/format/Pyright exit 0. Unknown data-argument, altered-code-payload and generic
tracker-name invocations all remained native. Live/stopped native and tracker
checks rejected execution; native zombie failed strict reaping; stale identity
was treated as exited/reused. Actual OS PID reuse was not forced or claimed.

### Verify Gate

| Attribute | Value |
|---|---|
| Kind | test |
| Command | NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify |
| Exit/result | 0; parent execution receipt, log /private/tmp/bybit-shutdown-root-verify.log |
| Status | Green; TypeScript unaffected/cached tasks and 9 actual hook tests, no aggregate Python coverage inferred |
| Scope | DEFINE gate is a local plugin regression gate, not full-product acceptance |

Manual UX receipt: N/A. No UI/user-flow change. No dependency/SBOM input change;
parent owns full release checks/security artifacts and independent acceptance.

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-010 scoped paper lifecycle | HTTP calls close while actual native worker stays owned; SIGTERM joins/reaps worker at service exit | Scoped pass | Ordinary and deliberately delayed tracker cases; strict native proof preserved |
| AT-015 partial protective evidence | Dispatch survives durably; killed owner ends native execution; restart remains protected and queryable | Partial; full AT-015 unaccepted | Actual dispatched SIGKILL case plus unchanged idle crash case; no auto-replay; exchange reconciliation before retry is outside this slice |
| Full product AT-010/015 and original MUSTs | Complete platform/operational recovery | Incomplete outside slice | Existing handoff gaps remain; no full acceptance inferred |

## Advisor Ledger

| Phase | Note | Severity | Decision | Evidence |
|---|---|---|---|---|
| Post-build independent, PS-R1 | Arbitrary argv tracker matcher could exempt unknown child from strict native reaping | Medium | APPLIED | Exact interpreter/-c/fullmatch correction; actual adversarial classification independently verified |

Independent reviewer: shutdown_independent_review. Final verdict: **ACCEPT scoped
test-observation correction** in
`sdd/reviews/REVIEW_PAPER_SHUTDOWN_OBSERVATION_2026-11-17.md`, exact source SHA above.
Pre-review design score 7.5/10: information hiding and abstraction comments failed.
Final independent score: 10/10, all eight diagnostics supported, failed rows none
within this observation boundary. No production/runtime score is inferred.

## Issues Encountered

No production leak was demonstrated. Historical CI child role remains unknowable;
the actual unmodified probe supports the resource-tracker scheduling explanation.
Test classification review found and corrected a real proof-quality issue before
acceptance. No application lifecycle patch was justified by the evidence.

## Deviations from Design

None in final intended behavior. Independent review correction implements the
original fail-closed known-invocation contract; earlier broad matcher was rejected.

## Blockers

None within the scoped correction. Parent owns release checks, commit/push and
hosted CI follow-through; none of these are claimed complete by this worker.

## Final Status

Overall: COMPLETE for scoped test-observation correction only.

- [x] All three manifest tasks completed and evidence recorded.
- [x] Final source focused tests, Ruff, formatting and Pyright passed.
- [x] Parent root Verify Gate exit 0 received with attribution.
- [x] Independent scoped ACCEPT, all review findings disposed.
- [x] Existing full-product gaps and partial AT-015 evidence remain explicit.
- [x] No unresolved blocker or unfinished TODO/FIXME in this slice.

All source remains below 500 lines. No secrets, account requests, user database,
Mainnet/Testnet order, Git operation or deployment was involved. No full SDD
product completion is inferred.

## Next Step

Execute o **SDD Handoff by RDD**.
