# LOOP_SPEC v4 — shared cycle deadline and cleanup fence

This version records the scheduler lifecycle contract introduced after v3.
The v3 machine prompt remains active and unchanged; v4 does not imply that the
prompt-evaluation gate or unattended exchange trading is complete. The
`LOOP_SPEC` format version below is v2; “v4” versions this loop contract.

```text
<LOOP_SPEC v="2" perfil="lite" nome="DSH AI background simulated decision loop">
<intent>
Run one default-off DSH Agent cycle for Testnet or internal-paper research.
The cycle may discover eligible market candidates and persist up to four local
simulated decision receipts. A cycle is operationally complete only after the
Agent turn ends and its handle cleanup is confirmed. It never submits, cancels,
or closes exchange orders, controls the native paper process, or resumes an
Agent cycle across process restarts. The larger error is an unsupported
simulated position; missing, stale, ambiguous, timed-out, or unverified state
therefore fails closed to abstention or blocking. The `lite` profile applies
because there is one Agent stage, the receipt/lifecycle verifier is code-owned,
and the only write effect is local simulated state; exchange data tools are
read-only.
</intent>

<control_state>
The scheduler keeps the cycle ID, open/closed flag, pending and committed
receipts, normalized symbol keys, consecutive failure count, start/completion
timestamps, and cleanup-uncertain flag in process memory. The simulated AI
track is persisted by the existing local atomic state store. The cycle deadline
is monotonic and starts before `agents.create`; the same deadline covers Agent
creation and `whenIdle()`. There is no cross-restart continuation or durable
attempt/action/error ledger.
</control_state>

<action_space>
Allowed effects are read-only market/instrument/brief/signal/review tools and
`quant_decide_background`, which can write only the local simulated journal
after schema, cycle-ID, candidate, and risk checks. A receipt is committed only
after the state-store write succeeds. Exchange orders, account mutation,
credentials, watchlist changes, native-paper controls, arbitrary generated
code, and every unlisted tool are outside the action space. Dashboard filters
are never cycle inputs.
</action_space>

<observation>
Observe Agent creation resolution, `whenIdle()` resolution, local write result,
receipt result, cancellation request, idle confirmation, handle disposal, and
the scheduler's final state/reason. A cancellation request alone is not proof
that Host work stopped. A completed turn with zero committed receipts is an
unknown decision outcome, not proof of model abstention. Tool and state-store
errors fail closed; the scheduler does not retry a write in the same cycle.
</observation>

<verifier>
Deterministic code checks supported environment/configuration, exact active
cycle ID, decision schema, candidate eligibility, code-owned risk result, one
receipt per normalized symbol, no more than four receipts per cycle, and
successful local persistence before committing a receipt. The scheduler
independently enforces one active Agent, a shared monotonic cycle deadline, and
confirmed idle/disposal before scheduling another cycle. This verifier does
not evaluate predictive quality, profitability, exchange execution, or whether
the DSH Host's cancellation API terminates underlying work.
</verifier>

<stop_rules>
DONE: the Agent turn finishes within the shared deadline and its handle is
confirmed idle and disposed; zero receipts remains an unknown outcome.
EXHAUSTED: the shared cycle deadline expires during creation or the Agent turn;
request abort/cancel and enter bounded cleanup. A late-created handle must be
cancelled, observed idle, and disposed before scheduling resumes.
BLOCKED: three consecutive cycle failures, or cleanup/late-handle release
cannot be confirmed. Clear the next-run timer and do not overlap another Agent.
After a late creation, resume with backoff only after cleanup is confirmed.
SAFETY_STOP: disabled/unsupported environment or plugin unload; clear timers,
request abort/cancel, and wait only within the bounded shutdown budget.
There is no within-cycle convergence loop; timer wake-ups are independent
research cycles. No model prompt can override these states.
</stop_rules>

<budget>
One Agent turn receives at most 1,600 tokens. One cycle has a default hard
wall-clock limit of 120 seconds from before Agent creation through turn
completion; configured limits are clamped to 5 seconds–10 minutes. Each
registered tool call has a 20-second timeout. The cleanup wait defaults to 10
seconds and is capped at 60 seconds for each idle/disposal wait; unload itself
returns after its bounded shutdown wait and reports uncertain cleanup. The
configured wake-up interval is clamped to 1 minute–24 hours. At most four
decision receipts are allowed per cycle. Failures back off by 2× then 4× the
configured interval, capped at one hour, and block after three consecutive
failures. These limits bound scheduler behavior, not strategy quality.
</budget>
</LOOP_SPEC>

STAGES:
| # | stage | type | input → output | verifier | maxTokens | retry | file |
| 1 | Agent research and simulated proposal | LLM | fixed prompt and cycle ID; tool evidence is discovered during the turn → zero to four cycle-bound proposals or no receipt | deterministic tool checks plus receipt; model evaluation is separate | 1600 | no same-cycle retry; a failed cycle uses scheduler backoff | `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v3.ts` |
| 2 | Candidate/read tools, risk gate, local write, receipt and lifecycle fence | code | allow-listed tool requests → evidence, persisted simulated receipt, or fail-closed result | scheduler and tool boundary | — | read retry only if explicitly attempted within the same hard deadline; never retry uncertain write | — |

PROMPTS PENDENTES: No new prompt was created for v4. The active v3 prompt remains subject to the independent evaluation receipt required by the SDD prompt gate.

VERIFY GATE: `pnpm --dir apps/dsh-plugin run verify`, `CI=1 NX_DAEMON=false pnpm run verify`, and `git diff --check`; tests must cover creation+turn sharing one deadline, timeout cancellation, late-handle cleanup, blocked/no-overlap on uncertain cleanup, and bounded unload. A real DSH Host integration check must separately establish cancellation semantics before relying on it; no market-performance ground truth or independent model-quality receipt is available, so the prompt gate remains incomplete.
```
