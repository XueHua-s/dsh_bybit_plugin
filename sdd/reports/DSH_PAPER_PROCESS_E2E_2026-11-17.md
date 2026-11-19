# DSH native paper process E2E receipt

Date: 2026-11-17 (Asia/Shanghai)

Scope: Design manifest item 18 (`apps/dsh-plugin/scripts/test-dsh-paper-process.ts`) and item 30 (this report). The test is an independent process check for the bounded internal-paper slice. It does not certify the full Bybit quant product, Testnet, Mainnet, installed DSH owner/auth UI, or the complete original requirements.

## Mode and boundary

This delegated two-file task used the sequential default mode. The process boundary is deliberately kept in one TypeScript test script: the script owns only temporary synthetic fixtures, while the Python broker, Host facade, generated SDK, native runtime, and production database/migration code remain separate owners. This task did not modify package, CI, production source, credentials, current Harness profile, or user database files.

The script is POSIX-only by design and exits closed on other platforms. It starts the locked `python/.venv` interpreter with an allowlisted `PATH` and `LANG`; it does not inherit `.env`, credential files, exchange keys, or the caller's environment. It first creates a temporary 0700 directory, initializes an empty SQLite file with `PRAGMA user_version=0`, and invokes the existing migration command on that file. The service receives a fixed synthetic session and a canonical private Unix socket path. No token is printed or passed in arguments, environment, files, Tool arguments, or panel responses.

## Exact test command

From the repository root, after the existing Host and SDK build artifacts and locked Python environment are available:

```text
node apps/dsh-plugin/scripts/test-dsh-paper-process.ts
```

The script resolves its repository root from `import.meta.url`, so the command does not depend on the caller's current directory beyond being able to resolve the workspace dependencies. The Nx target wired by the integration owner invokes this same script uncached.

## Actual process evidence

The final direct run completed with exit 0 in 5.13 seconds:

```json
{"result":"ok","environment":"internal_paper","synthetic":true,"commands":4,"native_filled":3,"risk_rejected":1,"injected_postdispatch_503":true,"actual_fault_submit_posts":1,"service_pids":[38209,38228],"native_pids":[38222],"tracker_pids":[38221],"host_close_survived":true,"native_reaped":true,"listeners_closed":true,"restart":"protected","capability_disclosed":false}
```

The PIDs above are evidence from that run only and are no longer live. The script records PID plus process creation time before making lifecycle assertions; this prevents PID reuse from being mistaken for a child still owned by the service. Native children are required to disappear immediately after the explicit native stop. The separate Python `resource_tracker` child is permitted its bounded post-service exit window and must be gone or zombie within three seconds. No unconditional `SIGKILL` is used for a passing path.

The exercised path was:

1. Start the real `paper_bootstrap` CLI with a pre-migrated temporary SQLite database, numeric loopback port, and `--capability-socket` broker mode.
2. Let the built Host call the real Unix capability provider. The generated SDK then calls the real Python HTTP API with the private capability. An unauthenticated direct HTTP status request returned 401. A process-level fetch guard rejected every destination outside the configured internal-paper API and rejected ambient Origin, Cookie, and Bybit API-key headers.
3. Start the native paper service once. If the mutation result is uncertain under bounded transport timing, the script performs only status observations until the real service reports `running`, `ready`, and `native_process_alive`; it never resends `start`.
4. Submit `first-request`, replay it, and submit the same request with changed quantity. The replay preserved command/native IDs; the changed fingerprint returned the real 409 conflict. A later request received distinct IDs. Polling by the original request ID observed the real native `filled` state and `0.001` cumulative fill.
5. Use a second order large enough for the real risk policy to reject it. The returned state was `risk_rejected`, with zero fill. A read-only SQLite query verified four durable commands, three filled, one risk-rejected, three allowed decisions, one denied decision, three distinct native-filled commands, and three durable dispatch events.
6. Run the required post-dispatch-503 probe. The injected transport wrapper forwarded one actual submit to the real service, required its 202 durable/native receipt, then replaced only that response with a valid synthetic 503. The SDK returned `outcome_uncertain` with `cause: unavailable` and `recovery: query_request` for the original request ID. One original-ID GET recovered the same command ID and native client order ID; the wrapper observed exactly one submit POST. This is a test transport response substitution, not a new production fault endpoint or a claim that a naturally occurring production 503 was reproduced.
7. Close the Host facade. A separate SDK status request continued to observe the independently owned running service and live native process. A newly constructed Host issued one explicit stop. If stop was uncertain, the test observed status only until `stopped`; it did not retry the mutation. Native child reaping and `native_process_alive=false` were required before service shutdown.
8. Send SIGTERM to the real service, then require the Unix socket inode and HTTP listener to be closed. Restarting against the same temporary database reported `protected`, with no native process and no automatic restart. A status-only check confirmed protection; a start attempt returned mutation uncertainty caused by `unavailable`, and no start retry occurred. The original durable request still resolved to the same filled command/native IDs after restart.

## Verification commands

| Command | Exit | Evidence |
|---|---:|---|
| `pnpm --filter @bybit-quant/dsh-plugin typecheck` | 0 | Strict TypeScript accepted the script and Host imports. |
| `pnpm exec oxlint apps/dsh-plugin/scripts/test-dsh-paper-process.ts` | 0 | No lint findings. |
| `node apps/dsh-plugin/scripts/test-dsh-paper-process.ts` | 0 | Final receipt above; real cross-language/native process path. |
| `pnpm exec nx run @bybit-quant/dsh-plugin:test:paper-process --skip-nx-cache` | 0 | 4 Nx tasks succeeded, uncached; target executes the process test. |
| `git diff --check -- apps/dsh-plugin/scripts/test-dsh-paper-process.ts` | 0 | No whitespace errors. |

An earlier run after tightening capability-output capture exited 1 during `built_host_unix_sdk_cli_start` without a diagnostic cause because the first version intentionally suppressed exception detail. The script was changed to report only a fixed allowlisted stage/cause (never exception text or token material); the next direct run passed. That earlier transient is retained here rather than being presented as a reproduced product defect. No production code was changed to address it.

## Security and cleanup observations

- Capability material is held only in the test process's private Set for leak assertions. Captured child stdout/stderr, Host logs, Tool results, and the final receipt are checked for the exact capability and the receipt contains no capability value.
- The temporary database is deleted in `finally`; the script never resolves a configured user DB, credential path, `.env`, DSH profile, or exchange endpoint.
- Failure cleanup sends SIGTERM and waits within a bounded deadline; only an already-failing cleanup path may use SIGKILL to avoid leaving a worker. A passing path never needs it.
- The script uses no generated Python source file. Its two short `python -c` calls are fixed observations (SQLite migration setup/readback and PID/create-time/status inspection), run with sanitized environment and no user input. The actual broker, migration, admission, ledger, and native execution remain the checked-in Python modules.

## Acceptance status and limits

**Scoped result: ACCEPT for the process E2E contract.** The evidence supports the synthetic internal-paper path, stable IDs/idempotency/conflict, real native fills and risk rejection, Host-close independence, mutation-503 uncertainty recovery, protected restart, and bounded Unix/HTTP/native cleanup.

This receipt does not upgrade the project to full product acceptance. Installed DSH physical owner/auth behavior, Client browser interaction/visual appearance, Testnet or Mainnet execution, exchange cutover, replay recovery, long-term supervision, and the original strategy/AI/research requirements remain outside this test and must retain their existing partial or unverified status.
