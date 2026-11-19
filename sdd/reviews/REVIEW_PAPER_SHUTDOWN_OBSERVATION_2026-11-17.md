# Independent review: Paper shutdown observation — 2026-11-17

Verdict: **ACCEPT scoped test-observation correction** on the frozen source below.
No outstanding blocking finding remains in this slice. This accepts the native
SIGTERM reaping proof, separate bounded tracker/orphan inactivity proof and the
deterministic paused-tracker regression. It does not accept a broker design,
exchange reconciliation, full product acceptance, deployment or hosted CI result.

## Scope and source identity

Reviewed repository AGENTS, software-design-philosophy, SDD Build review/gate
guidance, `DESIGN_PAPER_SHUTDOWN_OBSERVATION.md`, relevant restored Brainstorm/
Define requirements, the changed process test and the existing native join/
owner-watchdog boundary. Reviewer changed only this review and temporary probe
scripts. No application or repository test source was changed by reviewer; no
credentials, account/exchange connection, exchange orders or Git mutations were involved.
All process evidence used synthetic local children, loopback HTTP and temporary
migrated SQLite databases.

Frozen reviewed file: `python/apps/quant-engine/tests/test_paper_process.py`,
234 lines, SHA-256:

```text
eabc56743dac53e3569d81fa6ba6adec6c15734cd3e4051d0214cecb57ff1fab
```

The historical CI44091570414 PID4770 had no recorded command role or creation
time. Its exact role remains unknown. The author's unmodified eight-cycle probe
is separate evidence: all eight native workers were gone at service exit; one
stdlib tracker remained for 1.438 ms. Reviewer read the installed CPython tracker
startup implementation, which explicitly permits the tracker to outlive its
parent. Neither fact identifies that historical CI PID or justifies a runtime
lifecycle change.

## Findings and disposition

| ID | Finding | Disposition |
|---|---|---|
| PS-R1, Medium | Initial `any(argv.startswith(tracker_text))` classified an actual Python sleeper carrying tracker text as a data argument as tracker. This could relax strict native reaping for an unknown descendant. Independent probe exited1 and acceptance was held. | **APPLIED and independently verified.** Final matcher requires exactly the test server's interpreter path, `-c`, and the complete stdlib `main(decimal_fd)` payload, with no suffix/extra arguments. Unknown shapes remain native. Actual data-argument, altered-code-payload and generic tracker-name children all remain native in the final probe. |

No other actionable finding remains. The exact invocation restriction is
deliberately local to this test server, which starts an unflagged interpreter.
An unfamiliar interpreter/argument shape fails closed instead of receiving the
tracker exemption.

## Contract assessment

- Captured `psutil.Process` objects retain PID/create-time identity. Both status
  observation and signalling use that identity. An independent simulated stale
  creation-time identity was treated as exited/reused while its PID still held a
  live process. Actual OS PID reuse was not forced or claimed.
- Graceful SIGTERM calls the immediate strict native check after owner `wait()`:
  live, stopped and unreaped zombie native children all fail. The existing native
  facade really joins its worker; this correction does not add a retry around
  native graceful failure.
- SIGKILL retains the existing 8 s native inactivity bound. A killed owner cannot
  reap its orphan; an exited orphan zombie can satisfy inactivity while remaining
  unable to satisfy graceful reaping. Trackers are independently observed with
  a 3 s inactivity bound; live, sleeping or stopped trackers cannot pass.
- The parameterized regression pauses known trackers, sends owner SIGTERM and
  proves native reaping while trackers are still stopped. Its `finally` resumes
  captured trackers. Two actual fault injections, immediately after SIGSTOP and
  after owner exit, proved bounded cleanup even when the scenario raises.
- Both ordinary and paused-tracker cases preserve unauthenticated 401,
  authenticated startup, real native order/fill, worker survival across HTTP
  calls, protected restart and refused restart. Dispatched SIGKILL preserves a
  queryable command and refuses automatic replay. This is partial protection
  evidence; DEFINE AT-015 still requires real exchange reconciliation before any
  safe retry claim.
- Failure diagnostics contain role/PID/cached creation time/state. They do not
  print process arguments or capabilities. No application lifecycle, dependency,
  migration, API or OpenAPI source changed in this slice.

## Actual independent verification

Commands used the existing repository venv. Process/socket inspections ran with
approved local execution outside the restrictive sandbox. Every receipt below
is from reviewer execution, rather than copied author counts.

| Actual command | Exit | Observed result |
|---|---:|---|
| `python/.venv/bin/python -m pytest python/apps/quant-engine/tests/test_paper_process.py -q` | 0 | Final frozen source: 4 passed in 11.11 s; ordinary SIGTERM, paused tracker, idle crash and dispatched SIGKILL. Earlier pre-classifier-refinement run also passed 4 in 11.83 s and is historical only. |
| `python/.venv/bin/python -m pytest python/packages/quant-execution/tests/test_paper_runtime.py -q` | 0 | 11 passed in 12.16 s; includes forced shutdown failure and owner SIGKILL with both responsive and deliberately blocked native loops. Native application source was unchanged by this correction. |
| `python/.venv/bin/python /tmp/review_shutdown_observation_helpers.py` | 0 final | Actual known tracker/native capture; live/stopped native strict and inactivity rejection; live/stopped tracker inactivity rejection; native zombie strict rejection; orphan/tracker zombie inactivity; fully reaped acceptance; simulated stale create-time identity; three unknown invocation shapes kept native. Short controlled negative deadlines rejected active children in about 0.05–0.06 s. |
| `python/.venv/bin/python /tmp/review_shutdown_failure_cleanup.py` | 0 final | Actual synthetic HTTP/native scenario injected failure after SIGSTOP and after owner exit. Trackers resumed, native reaped, tracker inactive in 1.948 s and 2.097 s. Previous classifier version also passed these cleanup probes in 2.013 s and 2.009 s. |
| `python/.venv/bin/ruff check python/apps/quant-engine/tests/test_paper_process.py` | 0 | All checks passed on final source. |
| `python/.venv/bin/ruff format --check python/apps/quant-engine/tests/test_paper_process.py` | 0 | Final file already formatted. |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/apps/quant-engine/tests/test_paper_process.py` | 0 | 0 errors, 0 warnings. |
| `shasum -a 256 python/apps/quant-engine/tests/test_paper_process.py` and `wc -l python/apps/quant-engine/tests/test_paper_process.py` | 0 | Final identity above; 234 lines, below 500. |

Nonpassing evidence was retained rather than rerun into an apparent success:

1. First helper probe in the sandbox exited 1 at psutil/sysctl permission denial.
   Its finally block killed/reaped its temporary children. This was an
   infrastructure failure, not a passing observation test.
2. First actual unsandboxed helper probe exited 1 on PS-R1 after its preceding
   lifecycle/identity checks passed. The author corrected source and recorded
   the matcher decision in the design supplement before correction. The final
   probe added altered-code and generic-name cases and exited 0 against the new
   frozen source. No failed live-child check was ignored or retried unchanged.

The helper and fault-injection probes used bounded deadlines and finally cleanup;
all spawned direct children were reaped. Temporary probe scripts are review
evidence, not production/test implementation additions.

## Design complexity assessment

**10/10 for this scoped observation boundary: 8/8 diagnostic rows supported.**
The helper module has one describable purpose; its small observation interface
hides identity/classification/deadline/diagnostic details; callers retain only
the meaningful graceful-versus-crash distinction; comments state the reaping and
inactivity promises; independent design review is recorded; lifecycle knowledge
has one home; documented boundaries are understandable without native internals;
and deliberate design work replaced the misleading PID-only check without
changing runtime behavior. Failed diagnostic rows: **none in final scope**.
No change is needed to reach 10/10 within this slice. This score does not certify
the complete execution service, recovery guarantees or broker architecture.

## Remaining gates and limits

Parent owns full root Verify Gate, release checks, commit/push and exact hosted
CI follow-through. Author/parent report root verify exit 0 separately; this review
does not claim to have rerun that gate. Existing full-product, persistent
reconciliation, external execution, security/package and operational acceptance
gaps remain governed by their existing artifacts. No full AT-010/015 acceptance
or new trading authorization is inferred from this test correction.
