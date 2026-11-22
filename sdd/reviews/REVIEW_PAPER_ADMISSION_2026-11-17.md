# Independent review: optional INTERNAL_PAPER admission

Date: 2026-11-17. Reviewer: paper_service_review. Scope: DESIGN_PAPER_ADMISSION and engine service/auth/lifecycle integration only. This is not full target, exchange, product, release, native-library or ledger acceptance. Only temporary synthetic data and test capabilities were used; no credentials/accounts/exchanges were accessed. No code/test fixes, installs, commits or pushes by this reviewer.

## Status

ACCEPT for the reviewed optional INTERNAL_PAPER service boundary. No unresolved blocking findings in this scope. Independent final combined service/API/process/control/economic suite: 15 passed, exit 0, 18.19s. After the final expired-claim protection propagation fix, all seven independent actual-native probes passed, exit 0, 6.36s. Parent owns the full Verify Gate/release and independent native/ledger reviews. Economic acceptance below supersedes the earlier cash-notional implementation, which was not accepted.

## Sources and boundaries

Read repository AGENTS.md, software-design-philosophy and sdd-build, DESIGN_EXECUTION_CUTOVER, DESIGN_PAPER_ADMISSION, DESIGN_ADMISSION_STORE, DESIGN_PAPER_NATIVE. Reviewed engine paper configuration, canonical HTTP models, context construction, API, bootstrap and admission implementation. Existing market API/bootstrap remains read-only/default. Optional CLI is explicit; synthetic fixture and trusted policy are server-owned. Proposals cannot inject balances, policy, reconciliation, leverage, account identity or arbitrary native metadata. Only native LIMIT execution is admitted. Mainnet/Demo/Testnet execution is unavailable here.

Native runtime now uses a spawned child process and its scoped design records that change. Native constructor/library review and ledger migration/transaction review have independent owners; this review tests their service integration, without replacing those reviews.

## Findings and dispositions

- Nullable last_admitted_at_ns conversion: APPLIED; absent history maps to zero.
- Very large digit Content-Length caused an uncaught conversion exception: APPLIED; bounded header length before conversion, independently reprobed 413.
- Initial event drain/snapshot occurred outside protection handling: APPLIED; outer guarded admission freezes before releasing writer. Independent injected persistence failure protects even if durable protect fails too.
- Initially apparent caller generation tautology: REBUTTED as blocker after inspecting durable claim's decision-generation+1 and expiry CAS; caller now also checks exact post-decision revision. Independently injected state change after decision prevents native submit and retains reservation.
- Native protect IPC exception skipped durable protection, cancellation/drain exceptions skipped disposal, and close exceptions skipped lock FD cleanup: APPLIED. Independent native protect/cancel fault tests prove real native process reaped, durable protection retained, and state protected rather than stopped.
- Native stream completeness/failure/protected status were ignored by readiness/admission: APPLIED. Healthy process alone no longer establishes readiness; actual stream/status and finite quote expiry are checked. Native snapshot and persistent read faults use protected fixed safe errors.
- Expired durable dispatch claim correctly denied execution but initially left in-memory/native state and readiness running: APPLIED. Claim refusal now propagates durable protection immediately; status also synchronizes durable protection. Independent simulated expired claim proves zero native submission, retained reservation, protected state and false readiness.
- Raw native available margin excluded unrealized loss: APPLIED. Native available_equity=min(raw free, raw free+unrealized), and risk context further caps it at durable marked equity; profits gain no margin credit. Independent adverse-mark probe verifies available margin deducts the unrealized loss.
- Parent SIGKILL could orphan a native process: APPLIED via native parent-liveness supervision; active-crash process test proves native stops, old command identity survives and restart remains protected.
- Parent-found perpetual accounting blocker: APPLIED and independently verified. Opening notional is not debited from perpetual wallet/equity. Durable accounting is explicitly LINEAR_PERPETUAL; gross durable realized minus cumulative fees reconciles native net realized. Wallet, positions and marked equity are checked before later admission. No pre-fix economic acceptance is claimed.
- Early fresh zero-byte migration fixture sidecar failures and transient native startup sequence failure: resolved by authors; final reruns supersede those failures. These were recorded during development, not hidden as successes.

## Independent evidence

All pytest probes used freshly migrated isolated temporary SQLite databases. Loopback process tests required approved sandbox escalation because ordinary sandbox binding returned EPERM. Raw logs were captured under /tmp; only safe summaries were emitted, avoiding assertion repr of synthetic Authorization headers.

| Command/probe | Exit/result | Interpretation |
|---|---|---|
| Inline TestClient with injected observation service, no lifespan/database/native | 0 | Valid200; missing auth401; Origin:null403; slash404 without redirect; extra token-like marker422 with no marker echo; invalid JSON422; body4097 bytes413; negative length413; 5000-digit Content-Length413 after fix. No capabilities printed by probe. |
| Inline initial-drain event-persistence failure injection | 0 | Safe PaperUnavailable; service protected; runtime protect invoked even when durable protection also fails. |
| Engine admission+API pytest, first attempts | 1 | Initial 3+2 migration-sidecar failures, then transient native startup failure and unknown-ID422. Authors fixed; subsequent five tests passed. |
| python/.venv/bin/pytest python/apps/quant-engine/tests/test_paper_process.py -q | 0; 2 passed, 5.37s | Private inherited FD authentication; native process remains across closed HTTP clients; SIGTERM cleans listener/native children; restart protected; idle crash protected. |
| python/.venv/bin/pytest /tmp/test_paper_service_independent.py -q, control/failure phase | 0; 5 passed, 4.39s | Replay has exactly one actual native submit; generation mutation and failed dispatch claim have zero submit and retained reservation; failed native protect/cancel still reap and protect. |
| Combined pre-economics control/process probes | 0; 13 passed, 14.88s | Included active command/nonflat crash, orphan exit and preserved command identity; does not certify obsolete economics. |
| python/.venv/bin/pytest /tmp/test_paper_service_independent.py -q, economic phase | 0; 6 passed, 6.16s | Actual long open, subsequent admission, adverse mark, long close, short reopen, marked available margin and durable/native wallet/PnL reconciliation. |
| python/.venv/bin/pytest python/apps/quant-engine/tests/test_admission.py python/apps/quant-engine/tests/test_command_api.py python/apps/quant-engine/tests/test_paper_process.py /tmp/test_paper_service_independent.py -q | 0; 15 passed, 18.19s | Combined scoped security, real risk, serialized reservations, native economics, lifecycle, active crash/orphan supervision and independent fault/replay probes. |
| python/.venv/bin/pytest /tmp/test_paper_service_independent.py -q, final expiry delta | 0; 7 passed, 6.36s | Added actual durable claim-expiry fault; denied native submit and propagated durable protection to native/state/readiness. Earlier expectation requiring an exception first exposed the readiness gap; authors fixed it before this final pass. |

## Economic evidence

Actual 0.01 BTC BUY at 50000 opens 500 USDT exposure: wallet 9999.7 and equity 9999.699, reflecting 0.3 fee and 0.001 spread loss, rather than a 500-USDT loss. A following 0.001 BUY succeeds under the real evaluator instead of triggering false daily loss. Moving the explicit fixture bid to 49990 yields -0.11 unrealized PnL for 0.011 BTC while wallet remains unchanged; constructed server context daily loss is positive and below 1 USDT. Available margin is no greater than raw native free margin plus negative unrealized PnL, so marked loss cannot be spent again. Closing 0.01 and 0.001 realizes -0.11 gross; commissions are charged once. Reopening 0.001 short values at ask, giving -0.0001 unrealized. At every step durable wallet equals native wallet and durable gross realized minus fees equals native net realized within 1e-8. These are synthetic Sandbox evidence, not exchange or real-fund acceptance.

## Scope limits

Full deterministic native replay/recovery remains unavailable: reopening any previous session protects instead of resetting balance or treating empty Sandbox reports as flat reconciliation. Dedicated cancel/emergency/flatten API, DSH UI/install, Demo/Testnet connectivity, exchange risk/preflight, and product-wide release acceptance remain separate work. This review's stop test covers service shutdown; it does not certify the complete product emergency-stop workflow.

Software-design score: 10/10 for this scoped service boundary after independent evidence: all eight diagnostics supported. One deep admission interface owns serialization/risk/durability, transport owns canonical bounded schema, native details remain private, invariant comments and scoped designs explain replacement/lifecycle limits, and failure/economic revisions were reviewed. This is not a 10/10 claim about the full target or unreviewed modules.
