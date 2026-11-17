# DESIGN: Paper process shutdown observation

Date: 2026-11-17. Status: scoped regression fix authorized before source editing;
final implementation independently ACCEPTED, application runtime unchanged.
Sources: BRAINSTORM_BYBIT_AI_QUANT.md, DEFINE_BYBIT_AI_QUANT.md AT-010/015,
DESIGN_PAPER_NATIVE.md decisions 4/5, DESIGN_PAPER_ADMISSION.md, current handoff.
LLM prompts: false for this test-only slice. Application requirements and lifecycle are unchanged.

## Evidence and drift

Hosted CI 44091570414 failed only the SIGTERM test's immediate `pid_exists` assertion
for descendant PID 4770. The log did not capture its role/create time, so that exact
PID cannot now be identified. No application source changed in that documentation
commit. The assertion conflates the owned native worker with CPython's resource
tracker, and cannot distinguish PID reuse.

Before source editing an actual unmodified paper CLI probe ran eight SIGTERM
cycles with temporary migrated SQLite, synthetic native Sandbox and loopback HTTP.
All native children were already absent when service `wait()` completed. In one
cycle resource_tracker PID 98718 / create time 1794921950.643889 remained running at
that boundary and disappeared 1.438 ms later; native PID 98719 was already gone.
The other seven cycles observed both absent immediately. Probe exit 0. First
sandboxed attempt failed with loopback bind PermissionError / exit 1; the actual
probe ran with approved loopback execution. No exchange/account access occurred.

CPython 3.12.16 `multiprocessing.resource_tracker.ResourceTracker.ensure_running`
explicitly creates a process which outlives its parent without a parent wait;
`main` waits on pipe EOF before resource cleanup and exit. Native facade `_reap`
instead performs a real join before returning. This mismatch is test-observation
drift, not evidence authorizing an application lifecycle change.

## Decision

Keep native SIGTERM proof strict: every captured non-tracker descendant must have
disappeared at service exit, including reaping; a native zombie fails. Capture
`psutil.Process` identities before signalling: `is_running()` compares PID plus
creation time and prevents a reused PID from being reported as the old child.

Classify only the known stdlib `multiprocessing.resource_tracker` invocation as a
tracker; all other descendants remain under native proof. Trackers get a bounded
inactivity wait after owner/worker EOF. A live, sleeping or stopped tracker fails
at the deadline. A tracker zombie has exited and awaits OS reparent reaping; this
does not prove native reaping and cannot satisfy the separate strict native check.

Independent review rejected the initial implementation's match in arbitrary argv:
a sleeper carrying tracker-shaped data was misclassified. Before correction,
the known invocation is fixed to the exact interpreter path used by `server`,
the `-c` execution argument and a full stdlib `main(decimal_fd)` payload, with no
extra arguments. Unknown flags/shapes remain native (fail closed); this test's
server explicitly starts an unflagged interpreter. No application contract changes.

For service SIGKILL, native ownership watchdog has the existing bounded stop
deadline. An orphan zombie is inactive but cannot be reaped by the dead parent;
retain this distinction explicitly. Tracker cleanup is observed separately with
the same identity protection. Failure diagnostics include role, PID, creation time
and process state, never process arguments or credentials.

Add one actual-process adversarial regression: pause the identified resource
tracker with SIGSTOP before service SIGTERM, prove native reaping while tracker
is still paused, resume it in `finally`, and prove bounded exit. This reproduces
the legitimate ordering deterministically without relying on scheduler luck or
retrying a failed test. The unchanged HTTP auth, order/fill and restart-protection
scenario still runs in both ordinary and paused-tracker cases.

## File manifest and dependency order

| ID | File | Action | Purpose | Dependency |
|---|---|---|---|---|
| PS-1 | sdd/features/DESIGN_PAPER_SHUTDOWN_OBSERVATION.md | Create before source | Evidence, contracts and scoped manifest | Existing requirements/designs |
| PS-2 | python/apps/quant-engine/tests/test_paper_process.py | Modify | Encapsulate identity/role/exit evidence; delayed-tracker regression; SIGKILL observation | PS-1 |
| PS-3 | sdd/reports/BUILD_REPORT_PAPER_SHUTDOWN_OBSERVATION.md | Create | Actual commands, exits and limits | PS-2 |

No application source, API, OpenAPI, dependency, migration or package metadata
change. Runtime changes require new evidence and a prior design amendment.

## Verification

Run the actual process file repeatedly as independent pytest invocations,
including ordinary SIGTERM, deliberately delayed tracker and dispatch/SIGKILL.
Run native runtime lifecycle tests including blocked-worker SIGKILL and forced
shutdown failure; engine full suite, Ruff and Pyright. Parent owns full root
Verify Gate, independent review and any release. Failed live-child checks remain
failures; no rerun-until-green acceptance.

## Design assessment

Existing observation boundary: 7.5/10, six of eight software-design diagnostics.
Failed: information hiding (callers confuse tracker and native contracts) and
abstraction comments (PID absence does not explain identity/reaping guarantees).
One private test helper owns identity, classification, deadlines and diagnostics;
comments state strict graceful versus orphan/tracker guarantees. Planned 10/10
requires all eight diagnostics and actual process/review evidence; no runtime
quality improvement is inferred from changing a test. Final scoped independent
assessment: 10/10, eight of eight diagnostics, no failed rows, in
`sdd/reviews/REVIEW_PAPER_SHUTDOWN_OBSERVATION_2026-11-17.md`. Actual commands and
parent root gate receipt are recorded in the corresponding Build report.
