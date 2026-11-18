# Final Acceptance Audit — Bybit AI Quant

Date: 2026-11-17
Audited revision: `f6e519d` (`codex/bybit-ai-quant-sdd`); current worktree also contains the uncommitted runtime-checkpoint follow-up reviewed below.
Scope: independent read-only acceptance audit of the pushed HEAD and current worktree evidence. No credentials, `.env`, DSH state, provider account data, or orders were accessed. No external network calls were made by this audit.

## Verdict

**Overall: PARTIAL / NOT READY for full product acceptance or production.** The current local TS/Python verification chain passes, the workspace is Nx-discoverable with meaningful edges, and scoped migration, backup, sandbox, and market-data components exist. Several MUST criteria are only local scaffolds or fake-backed tests; official Plugin Manager upgrade/state preservation, integrated durable service recovery, verified Testnet OAuth support, and Testnet order E2E remain unproven.

The repository search did not find a separate pasted-text architecture brief file (`find . ... | rg -i 'paste|架构|architecture|brief|requirements|design'`); the audit therefore used the supplied `AGENTS.md`, `BRAINSTORM`, `DEFINE`, `DESIGN`, handoff/build/verify/lifecycle reports, READMEs, and source. No source changes were made. The worktree was already dirty at audit start; the report distinguishes recorded HEAD from observed uncommitted follow-up files.

## Acceptance matrix

| Requirement | Status | Evidence and boundary |
|---|---|---|
| Nx + pnpm topology and real task graph | **Complete for current workspace structure** | `pnpm exec nx show projects --json` → exit 0: `@bybit-quant/quant-contracts`, `@bybit-quant/dsh-plugin`, `quant-data`, `quant-engine`. `pnpm exec nx graph --file=/tmp/bybit-quant-final-audit-graph.json` → exit 0; graph edges are plugin → TS contracts (static) and engine → quant-data (implicit). Does not prove a running cross-language service contract. |
| DSH Bundle metadata, Cordis patch, Host/Client entries | **Complete for static checks** | Current Verify Gate records `pnpm run verify` exit 0 including bundle check. README documents Bundle under `apps/dsh-plugin`. Static consistency does not establish every installed DSH-version compatibility behavior. |
| Official Plugin Manager install/enable/uninstall/reinstall | **Partial** | `PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md` records official UI install, enable, uninstall, reinstall and re-enable. It used the active profile; only file sizes/timestamps were compared, not content hashes. |
| Official Plugin Manager upgrade + disposable-profile state preservation | **Missing / blocked** | Lifecycle report says no disposable profile or standalone manager was available; installed version remained 1.4.5. No upgrade receipt or before/after state hashes exist. |
| Python / TypeScript boundary and package ownership | **Partial** | Nx discovers separate TS plugin/contracts and Python engine/data projects. Graph has only the two edges above; no `quant-api-client`, localhost/OpenAPI service, or TS-to-Python contract consumer exists. `quant_engine` has lifecycle/adapter modules but no running service entrypoint. This falls short of the broader DESIGN diagram. |
| Alembic migration backup and failure protection | **Partial** | `quant_data.migrations.upgrade_sqlite` requires an explicit existing SQLite file, creates verified backup/candidate, checks integrity, and atomically replaces only after success; tests cover fixture preservation, failures, concurrency and downgrade refusal. Current receipts include 9 migration tests, exit 0. SQLite only; no production/target DB migration and no PostgreSQL backup contract. |
| Backup / restore and state recovery | **Partial** | Reports record checksum restore/tamper rejection, temporary SQLite restore, and a SIGKILL/reopen rehearsal. The backup regression is wired into Nx `test:unit` and passes the root Verify Gate. Python `EngineRuntime` now has a bounded versioned checkpoint for reconnect count only; queue depth and lifecycle timestamps are fresh process state on restart. Service supervision, order-state recovery, reconciliation and automatic restart remain absent. |
| Prompt-injection and untrusted-input boundary | **Partial** | Runtime decision prose is now normalized at the boundary, persisted as bounded strings, and returned through `{ kind: "untrusted-evidence", source: "agent", trusted: false, text }`; a local injection-like fixture proves prose alone cannot alter the numerical risk gate. This is a provenance/containment boundary, not proof of arbitrary LLM immunity; no news/GitHub connector exists and the model can still misread any tool result. |
| Generated algorithm isolation | **Partial** | `lib/sandbox.ts` runs Docker with no network, read-only root, dropped caps, non-root, CPU/memory/pid/time bounds, and an immutable image digest. The working tree captures stdout/stderr into fixed-capacity byte buffers; a flood regression retains only its configured 400 KB. Full supply-chain attestation and all failure modes remain outside this local smoke. |
| Monitoring: backlog, CPU/memory, WS, API/order latency, rejects | **Partial** | TS monitor exposes these counters/gauges, and Python adapter exposes queue/reconnect/event health. Host constructs monitor with `websocketEnabled: false`; adapter is not wired into a running engine/service, so production WS state and Python metrics do not feed the Host health surface. Metrics are process-local. |
| Graceful shutdown and automatic recovery | **Partial** | Python adapter `close()` closes socket, cancels and joins its worker; Host monitor effect returns timer cleanup. The runtime checkpoint restores only the reconnect counter after a graceful stop; queue depth and lifecycle timestamps reset with the new process. No engine signal handler/supervisor, order recovery or exchange reconciliation path exists. |
| TS/Python SBOM, dependency audit, secret scan | **Complete for recorded scope; partial coverage noted** | Current `VERIFY_GATE_2026-11-17.md` records TS and Python CycloneDX generation, `pnpm security:deps`, and gitleaks worktree/history scans, all exit 0. `pip-audit --skip-editable` excludes two editable workspace packages; no current independent rerun was made in this audit. |
| English and Chinese README alignment | **Partial** | Both README files describe REST-only operation and non-production status. The working tree narrows OAuth claims: provider support and real consent/revoke lifecycle are explicitly unverified, and the user is told to inspect the agent/scopes before authorizing. |
| OAuth: real/provider-backed Testnet support | **Missing / unverified** | `BUILD_REPORT_BYBIT_OAUTH_TESTS.md` records three fake-backed local cases, exit 0, with no outbound request. Verify Gate says official Testnet OAuth support is not confirmed; client has no revoke operation and no real consent/grant evidence. |
| Testnet order end-to-end | **Missing / unverified** | Corrected network receipt is public Testnet market-data only, read-only, no credentials/account access/orders. Build report says order E2E remains blocked by account identity/equity state. Safety guards must remain enabled; no order was sent by this audit. |
| Mainnet lock and code-side guards | **Partial, local tests only** | README and source document Mainnet disabled by default plus account/equity/instrument/notional/risk gates. Reports record mock/integration guard tests, but no live Mainnet or Testnet order request was attempted, appropriately. |
| Handwritten source size / strict TS checks | **Complete for recorded checks** | Current Verify Gate records maximum handwritten source 494 lines and strict typechecks exit 0. |

## Current verification performed

| Command | Exit | Result / limits |
|---|---:|---|
| `git rev-parse HEAD` | 0 | `5571a7dab2bb81a597c4505e4ab51950b8d744df`. |
| `pnpm exec nx show projects --json && pnpm exec nx graph --file=/tmp/bybit-quant-final-audit-graph.json` | 0 | Four projects discovered; graph written to `/tmp`; two meaningful edges listed above. |
| `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test` | 0 | Build/lint/typecheck and bundle Nx tasks reported success; build/lint/typecheck were 100% cached. Nx unit-test target ran. Test sources typechecked; Ruff/format and Pyright passed; pytest: 15 passed. |
| `pnpm --filter @bybit-quant/dsh-plugin exec node test/backup.ts` | 0 | Explicit backup/restore + tamper-refusal case passed. |
| `git diff --check` | 0 | No whitespace errors in tracked diff. The new audit report is untracked and therefore not covered by Git's tracked diff check. |

## Material drift / evidence caveats

1. The root Verify Gate includes backup restore and sandbox bounded-output regressions in the Nx `test:unit` command. The sandbox unit exercises the byte-capacity capture helper; it does not launch Docker or establish image provenance.
2. The Verify Gate and Build Report label product acceptance PARTIAL. Do not promote a local green gate into a complete platform, Plugin Manager upgrade, durable recovery, official OAuth, or order-E2E claim.
3. `sdd/reports/BUILD_EVIDENCE_REVIEW.md` and `sdd/reviews/ARCHITECTURE_REVIEW.md` are historical snapshots. The newer Verify Gate supersedes old build failures for local checks, but does not supersede open acceptance gaps.
4. The DSH lifecycle receipt concerns the active profile and did not inspect credential contents, but it records file metadata for sensitive state. This audit made no DSH UI or state access.

## Remaining gates

- Provide an isolated disposable Harness profile and prove a real version upgrade with non-secret state hashes before/after.
- Provide an isolated disposable Harness profile and prove a real version upgrade with non-secret state hashes before/after.
- Integrate the Python adapter and runtime into a managed service lifecycle; expose connected health, bounded metrics, graceful stop, process supervision, order recovery and reconciliation tests. The current checkpoint is only a health-state slice.
- Re-run the recorded sandbox digest smoke in CI/release and broaden the trust boundary review across any future news/GitHub connectors.
- Establish authoritative evidence for Bybit Testnet OAuth support and real consent/revoke lifecycle.
- Complete a Testnet order E2E only after a valid Testnet account passes identity, balance and risk checks; no bypass.
- Keep Alembic application scoped to a confirmed target with backup/rollback evidence; current evidence is temporary SQLite only.

## Post-push follow-up — backup test integration

The follow-up change wires `apps/dsh-plugin/test/backup.ts` into both the package `test:unit` script and the Nx `@bybit-quant/dsh-plugin:test:unit` target. This resolves the test-wiring finding above: root `pnpm run verify` now invokes the backup regression through Nx, rather than relying only on a separately run test.

Fresh verification for this follow-up: `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test` → exit 0; Nx unit target passed with the backup test included, Ruff/format passed (13 files formatted), Pyright reported 0 errors, and Python tests reported 21 passed. The acceptance verdict remains **PARTIAL / NOT READY**: the checks cover isolated TS state backup/restore and tamper refusal plus the bounded Python health checkpoint, but do not supply process supervision, order-state recovery, exchange reconciliation, production WebSocket durability, Plugin Manager upgrade proof, official OAuth confirmation, or Testnet order E2E. No credentials, OAuth state, target database or user state were accessed; no target migration or order was performed.

Timestamp-contract correction (current worktree): the Python runtime checkpoint now persists only reconnect count in v2. Queue depth and lifecycle timestamps are process-local; restart creates a fresh `started_at` and clears `stopped_at`. Legacy v1 timestamp and queue fields are validated then ignored. `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test && git diff --check` exited 0 with 21 Python tests passed; this remains a health-state slice without service supervision, order recovery or exchange reconciliation.

Other open audit findings remain unchanged. In particular, the English and Chinese OAuth sections should be narrowed to describe an unverified local client flow until authoritative provider support and consent/revoke lifecycle are established.

## Working-tree follow-up — sandbox output, OAuth claims and trust boundary

The current working tree adds `BoundedOutputCapture` to retain at most a fixed byte budget while continuing to drain child stdout/stderr. `apps/dsh-plugin/test/sandbox-output.ts` floods the capture with 100 × 2 MB chunks and verifies the configured 400 KB bound; the test is included in Nx and package unit targets. The bilingual READMEs now say Testnet OAuth provider support and real consent/revoke lifecycle are unverified and require the user to inspect the agent and scopes before authorizing.

Fresh verification on 2026-11-17: `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test && git diff --check` → exit 0. Nx build/lint/typecheck reported cache hits; unit target and Bundle check ran, test typecheck passed, Ruff/format passed (13 Python files), Pyright reported 0 diagnostics, and pytest reported 15 passed. The 2026-11-19 follow-up pins the sandbox image to an immutable digest and records a Docker smoke in `SANDBOX_DIGEST_PIN_2026-11-19.md`; full container failure-mode coverage remains open. Overall acceptance stays **PARTIAL / NOT READY**.

The trust-boundary increment also passed a fresh build, lint, unit target and test typecheck. It normalizes NFKC/control characters, rejects non-string/blank/oversize decision prose, and exposes agent text only as a `trusted:false` envelope in model-visible decision results. It preserves the existing persisted string shape and keeps code-owned action/risk fields authoritative; it does not claim to defeat arbitrary prompt injection.

## Current worktree delta — 2026-11-19

The earlier finding that the TypeScript Host retained a direct Bybit writer is
superseded for the current worktree by
[`BUILD_REPORT_TS_MUTATION_CLOSURE.md`](../reports/BUILD_REPORT_TS_MUTATION_CLOSURE.md):
the tool now returns local previews and denies write intent before exchange
access; the 98-case matrix and packed Bundle scan pass. This closes only that
alternate writer and does not implement the missing Nautilus Testnet writer.

The current DSH source panel explicitly reports conversation-triggered use,
not running in the background, exchange writes unavailable and account readiness
unknown. Local SSR checks pass; the active installed Harness still has the older
Bundle, so its updated UI remains unverified in place. Official Plugin Manager
upgrade/rollback and state-hash preservation are still open.

An offline-only Testnet profile/projection/preflight boundary was added under
[`DESIGN_TESTNET_READONLY_PREFLIGHT.md`](../features/DESIGN_TESTNET_READONLY_PREFLIGHT.md).
Its 312 Python tests use fixtures; it has no production credential provider,
signed HTTP transport, live preflight, order writer or order authorization. The
result `eligible_for_reconciliation` never allows submission.

Fresh commands on 2026-11-19: `pnpm run python:test` (exit 0, 312 passed),
`pnpm run python:lint` (exit 0), `pnpm run python:typecheck` (exit 0),
`NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` (exit 0),
`gitleaks git --redact` (exit 0), `gitleaks dir --redact --no-banner
--ignore-gitleaks-allow .` (exit 0), and `git diff --check` (exit 0). The
overall verdict remains **PARTIAL / NOT READY** for full unattended trading.
