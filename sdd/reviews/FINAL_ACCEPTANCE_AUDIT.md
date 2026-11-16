# Final Acceptance Audit — Bybit AI Quant

Date: 2026-11-17
Audited revision: `5571a7dab2bb81a597c4505e4ab51950b8d744df` (`codex/bybit-ai-quant-sdd`)
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
| Backup / restore and state recovery | **Partial** | Reports record checksum restore/tamper rejection, temporary SQLite restore, and a SIGKILL/reopen rehearsal. The backup regression is wired into Nx `test:unit` and passes the root Verify Gate. Python `EngineRuntime` only retains in-memory lifecycle fields; durable checkpoint, service supervisor, reconciliation and automatic restart are absent. |
| Prompt-injection and untrusted-input boundary | **Partial** | Host system prompt labels external material untrusted; `lib/trust.ts` wraps/filters text. The helper is not referenced by runtime call sites in the checked tree and no dedicated trust test was found. Pattern matching does not prove arbitrary external instructions are inert or non-authoritative across all prompt paths. |
| Generated algorithm isolation | **Partial** | `lib/sandbox.ts` runs Docker with no network, read-only root, dropped caps, non-root, and CPU/memory/pid/time bounds. The working tree now captures stdout/stderr into fixed-capacity byte buffers; a flood regression retains only its configured 400 KB. The image remains tag-pinned rather than digest-pinned, and Docker isolation is not re-proven by this pure unit test. |
| Monitoring: backlog, CPU/memory, WS, API/order latency, rejects | **Partial** | TS monitor exposes these counters/gauges, and Python adapter exposes queue/reconnect/event health. Host constructs monitor with `websocketEnabled: false`; adapter is not wired into a running engine/service, so production WS state and Python metrics do not feed the Host health surface. Metrics are process-local. |
| Graceful shutdown and automatic recovery | **Partial** | Python adapter `close()` closes socket, cancels and joins its worker; Host monitor effect returns timer cleanup. No engine signal handler/supervisor, durable checkpoint, restart recovery, or exchange reconciliation path was found. |
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
- Integrate the Python adapter and runtime into a managed service lifecycle; expose connected health, bounded metrics, graceful stop, durable checkpoint/restart and reconciliation tests.
- Close the trust-boundary test gap and validate the sandbox container image by digest.
- Establish authoritative evidence for Bybit Testnet OAuth support and real consent/revoke lifecycle.
- Complete a Testnet order E2E only after a valid Testnet account passes identity, balance and risk checks; no bypass.
- Keep Alembic application scoped to a confirmed target with backup/rollback evidence; current evidence is temporary SQLite only.

## Post-push follow-up — backup test integration

The follow-up change wires `apps/dsh-plugin/test/backup.ts` into both the package `test:unit` script and the Nx `@bybit-quant/dsh-plugin:test:unit` target. This resolves the test-wiring finding above: root `pnpm run verify` now invokes the backup regression through Nx, rather than relying only on a separately run test.

Fresh verification for this follow-up: `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test` → exit 0; Nx unit target passed with the backup test included, Ruff/format passed (13 files formatted), Pyright reported 0 errors, and Python tests reported 15 passed. The acceptance verdict remains **PARTIAL / NOT READY**: this test covers isolated TS state backup/restore and tamper refusal; it does not supply Python durable checkpoints/supervision, automatic recovery, exchange reconciliation, production WebSocket durability, Plugin Manager upgrade proof, official OAuth confirmation, or Testnet order E2E. No credentials, OAuth state, target database or user state were accessed by this follow-up; no target migration or order was performed.

Other open audit findings remain unchanged. In particular, the English and Chinese OAuth sections should be narrowed to describe an unverified local client flow until authoritative provider support and consent/revoke lifecycle are established.

## Working-tree follow-up — sandbox output and README claims

The current working tree adds `BoundedOutputCapture` to retain at most a fixed byte budget while continuing to drain child stdout/stderr. `apps/dsh-plugin/test/sandbox-output.ts` floods the capture with 100 × 2 MB chunks and verifies the configured 400 KB bound; the test is included in Nx and package unit targets. The bilingual READMEs now say Testnet OAuth provider support and real consent/revoke lifecycle are unverified and require the user to inspect the agent and scopes before authorizing.

Fresh verification on 2026-11-17: `pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test && git diff --check` → exit 0. Nx build/lint/typecheck reported cache hits; unit target and Bundle check ran, test typecheck passed, Ruff/format passed (13 Python files), Pyright reported 0 diagnostics, and pytest reported 15 passed. Sandbox output tests do not start Docker; image digest pinning and full container isolation review remain open. Overall acceptance stays **PARTIAL / NOT READY**.
