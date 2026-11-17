# Built paper SDK / real process E2E

Date: 2026-11-17. Status: PASS for this isolated synthetic process slice. Independent tester: `paper_end_to_end`; implementation authors were separate. No product-wide acceptance, release, installation, commit or push is claimed.

## Scope and isolation

Read repository AGENTS.md and DESIGN_PAPER_ADMISSION / DESIGN_PAPER_NATIVE / DESIGN_PAPER_SDK before execution. Parent assigned existing authorized parallel Build validation. SDK package was built, and a separate Node TypeScript probe imported its actual compiled `dist/index.js`. No injectable fetch or mocked transport was supplied. A Python orchestrator launched the actual `quant_engine.paper_bootstrap` CLI with `--database`, `--session`, `--capability-fd`, explicit loopback host and random available port. CLI launched its real spawned TradingNode/Sandbox native owner; process identity was inspected externally using PID plus create time, excluding the multiprocessing resource tracker.

Only explicit temporary SQLite under `/private/tmp/paper-sdk-process-*` was used. Initialization executed `PRAGMA user_version=0`, closed the connection, then ran the actual protected `upgrade_sqlite` implementation. Readback verified Alembic revision `0004_admission_state`; protected backup existed. The temporary directory/database/backup were deleted on successful completion. No user database, account, exchange, API key, secret or environment file was read.

One synthetic ephemeral capability was generated inside the orchestrator with `secrets.token_urlsafe(48)`. Server received it through an inherited pipe FD; each Node client received it through private stdin. Its value never entered argv, environment, files, report, tool output or source. Server stdout/stderr and SDK output stayed in process memory and were checked for absence of the actual capability before reporting only allowlisted booleans and exit codes. Native/runtime configuration was the canonical synthetic CLI fixture, not a replaced implementation.

## Actual commands and exits

Working directory: `/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant`.

| Command | Exit | Evidence |
| --- | ---: | --- |
| `pnpm --filter @bybit-quant/quant-api-client build` | 0 | Actual `tsc -p tsconfig.build.json` completed |
| `.venv/bin/python /private/tmp/quant-paper-e2e-20261117/probe.py` | 127 | Incorrect root interpreter path; no test ran |
| `python/.venv/bin/python /private/tmp/quant-paper-e2e-20261117/probe.py` | 1 | Protected temporary migration completed; sandbox socket creation denied with PermissionError; no E2E pass claimed |
| `python/.venv/bin/python /private/tmp/quant-paper-e2e-20261117/probe.py` (approved escalated loopback execution) | 0 | Full real process scenario returned PASS |
| `shasum -a 256 /private/tmp/quant-paper-e2e-20261117/probe.py /private/tmp/quant-paper-e2e-20261117/client.ts packages/ts/quant-api-client/dist/index.js packages/ts/quant-api-client/dist/paper.js packages/ts/quant-api-client/dist/transport.js contracts/openapi/quant-paper.v1.json python/apps/quant-engine/src/quant_engine/paper_admission.py python/packages/quant-execution/src/quant_execution/paper_native.py python/packages/quant-execution/src/quant_execution/paper_worker.py python/packages/quant-data/src/quant_data/admission_events.py` | 0 | Hash receipt below |

The final run used three separate SDK client processes, all exit 0. Two CLI service processes exited `-15` following SIGTERM. This is accepted only with explicit cleanup evidence below: native process was already stopped and reaped before first CLI SIGTERM, restarted service had no native owner, and each listener refused connections after process exit. No forced kill was needed in the passing scenario.

## Acceptance observations

| Criterion | Observed result |
| --- | --- |
| Unauthorized HTTP | Actual unauthenticated loopback GET returned 401 |
| Explicit paper start | SDK observed idle/no native owner, sent `internal_paper` start, received ready/synthetic paper status |
| Real native execution | SDK submitted BTCUSDT buy LIMIT `0.01` at `50000`, stable request identity `sdk-request-1`; original request lookup reached filled with cumulative `0.01` |
| Duplicate semantics | Same complete request returned original command and native client order IDs; database contained exactly one applied filled native event for that command |
| Conflict safety | Same request identity with changed quantity returned exact safe SDK failure `{ok:false,code:'conflict',status:409}` |
| Genuine evaluator/ledger | Durable `admission_decisions` contained two allowed decisions for the two unique proposals; fills and reservations were real database state |
| Continuous runtime | Later `sdk-request-2` order of `0.001` filled with a distinct native order ID; same native PID/create time across both orders |
| Persistent economic state | Durable position became `0.011`; wallet remained above `9999` and exactly `10000 - cumulative_fee` after both orders, so opening notional was not falsely charged as a loss |
| SDK ownership | Closing/exiting first SDK client left the CLI service and same native owner alive |
| New client read | New separately initialized Node client retrieved the same filled durable command |
| Explicit stop | SDK stop returned stopped/no native process; external PID existence check proved native process reaped |
| SIGTERM | CLI process exited within deadline; listener closed; `-15` was not treated as sufficient evidence alone |
| Protected restart | Same database/session restarted protected/no native process; SDK start returned safe 503 unavailable; original filled command remained unchanged |
| Capability boundary | Every captured subprocess output was checked against the actual in-memory capability; no match |

Mutations were each sent once except the deliberate, fully acknowledged successful-request idempotency/conflict tests. No ambiguous mutation was retried.

## Artifact hashes (SHA-256)

```text
4142d4bd3f2332c08c0fb20caa5a58dc749f08e7c08d13a6732396e433f0bcfc  /private/tmp/quant-paper-e2e-20261117/probe.py
39eb5029f36c58009056bd23ae8159b755edf5a6d3cf6c5f19036dcc7caac3f3  /private/tmp/quant-paper-e2e-20261117/client.ts
1a8958bb45dde23ad7316eafc1b7c9fdc6460ca4adb79133d6c330dea5198fa7  packages/ts/quant-api-client/dist/index.js
cf6f0375bfb3245ec64e174cbea92dbe9805987251b84d23015b38be12599d02  packages/ts/quant-api-client/dist/paper.js
0e1f07242f3e2411c57772e7618b089d4aae96da8a183a6576a50dbc4ddaaa8b  packages/ts/quant-api-client/dist/transport.js
24878c9e7ba9821dfbcd33311db3409463b7de5da45f7fc4b78d94c39b0260f5  contracts/openapi/quant-paper.v1.json
3a779530ff55af4bd0d4ea8594f7bee94a015aec76e46014ee53bf69feca9db7  python/apps/quant-engine/src/quant_engine/paper_admission.py
d0607da69aedbbd6ae44d966f706b3590583a8a60aa9db30280078f3f778cbf0  python/packages/quant-execution/src/quant_execution/paper_native.py
c80d4f426a5f168f9d09b91e5829fc3512d877e17c4c51f3b69a0ff1af3b5dea  python/packages/quant-execution/src/quant_execution/paper_worker.py
2bee30d81ef5d4d99ec771e0bfa722f93c96764138175870b783f246a0518e04  python/packages/quant-data/src/quant_data/admission_events.py
```

## Limits and remaining work

Public status deliberately does not expose wallet/equity. This true SDK scenario proves durable derivative wallet arithmetic and later admission continuity; it does not independently read native unrealized PnL/equity through the public API. Direct native/evaluator reconciliation is covered by implementation-owner tests, not misrepresented here as an additional observed wire field. Forced service death / watchdog blocked-loop cleanup are separate native/admission test scopes. Full repository Verify Gate, SBOM, vulnerability scans, secret scan, independent review and release decision remain parent-owned.

No requirement/design drift was needed. Tester changed only this repository report and temporary probe files; build refreshed generated `dist` artifacts. No production source edit or Git mutation was performed.

## Independent runbook recipe receipt

After E2E, independently reviewed `docs/runbooks/paper-service.md` against actual `paper_config.capability_from_fd`, `paper_bootstrap.main`, canonical routes, and the executed private-FD protocol. No issue found. Extracted its exact Python heredoc to `/private/tmp/quant-paper-e2e-20261117/runbook-recipe.py` and parsed with `ast.parse` (exit 0). Then executed `python/.venv/bin/python /private/tmp/quant-paper-e2e-20261117/runbook-recipe.py` with approved loopback access: exit 0, protected temporary migration through `0004_admission_state`, output `synthetic_native_start_stop_ok`. No submit route was invoked. This uses the synchronized locked environment directly and does not repeat `uv sync`.

Recipe SHA-256: `c3a3d1407b25e33f849c0fb679864db5537d58fad687f2d4b46cf6f6b72bbe4f`.

Confirmed generated capability is 64 printable ASCII bytes in memory, written raw without newline to an `os.pipe` FIFO whose read FD is inherited through `pass_fds`; only the numeric FD enters argv. No capability value enters environment/config/output. Native start/stop uses authenticated memory headers without redirects. Temporary target is explicitly initialized before protected migration; bounded service wait and kill-as-failure fallback are present. The recipe confirms stopped native wire state and bounded service exit; independent native PID disappearance/listener closure are correctly attributed to the separate E2E above, not falsely asserted by this documentation block. No runbook source edit was made by the independent tester.
