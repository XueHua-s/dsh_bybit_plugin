# HANDOFF: BYBIT_AI_QUANT

## Ficha

| Attribute | Value |
|---|---|
| Feature | BYBIT_AI_QUANT |
| Objective | Complete the original architecture MUSTs through independently verified increments; a scaffold is not the product. |
| Status | IN PROGRESS / PARTIAL. SDK/DSH/native/hooks accepted at published baseline; risk/command-ledger foundations independently ACCEPTED within scope and published with passing CI; new optional native paper/runtime/SDK have scoped ACCEPT and actual process E2E; data accounting/metadata43 ACCEPT and fullPython252 pass; final local gates/scans/artifact checks pass; current paper delta unpublished. Declared Nautilus/fsspec metadata mismatch remains. |
| Date | 2026-11-17 |
| Branch / folder | `codex/bybit-ai-quant-sdd` · `/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant` |
| Historical risk/ledger code | `411de43f07984f8d2af163c6e95abd53c3d98dc9`, pushed; exact remote SHA verified. CI44081030699 both jobs successful with steps inspected. Earlier566092a/4360381/f535981 are historical. This documentation follow-up is not covered by that code CI. |
| Authority | `AGENTS.md`, `sdd/features/DEFINE_BYBIT_AI_QUANT.md`, main DESIGN and `sdd/reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md` |

## Current paper integration — 2026-11-17 (VERIFIED SCOPED / overall PARTIAL)

Published baseline605fe709461e7157885da07216654a1da677926c has parent-verified
CI44081766003 success for both jobs. New local paper integration is uncommitted
and unpushed, with no new hosted CI receipt.

Scoped independent ACCEPTs: PAPER_NATIVE (33 execution tests plus actual
wallet/realized/unrealized/available-equity and owner-death blocked-loop probes),
PAPER_ADMISSION (15 combined and seven independent final expiry/economic/fault
probes), PAPER_SDK (21 tests), under `sdd/reviews/`, suffix `_2026-11-17.md`.
Data final scoped ACCEPT43 includes economic/backup/probes and actual Alembic
command.check with no new operations; native metadata alignment is corrected.
`PAPER_SDK_PROCESS_E2E_2026-11-17.md` records31 allowlisted real built-SDK→CLI→
risk/store→spawned-Nautilus checks0: later fills, stable IDs/idempotency/conflict,
SDK-close independence, native stop/reap, closed listener and protected restart;
capability never output. Public status does not expose native wallet/equity.

Parent root verify0 (SDK21/hooks9), TS testtypes0, fullPython252/11warnings
in35.43s0 (service115/native33/risk61/data43), both actual OpenAPI contracts
uncached0; final Python lint/format59/typecheck0 after metadata correction. Security0/four editables skipped; SBOM200/91 includes mixed execution
license. Initial `pnpm sbom` invoked pnpm12 builtin and exited2; corrected
`pnpm run sbom`0. Final changed-file gitleaks71files1,136,198bytes0 (before latest report append),
history11commits~2.25MB0, source125/max497/diff0. Parent wheel/sdist exact-byte
MIT/LGPL/GPL/NOTICE four-assets, adapted-source and SPDX inspection PASS.
Fetch0, main/feature ahead-behind both0/0 at inspection; no staged files yet. Native lifecycle uses a
spawned process; paper auth uses inherited private pipeFD; separatepaper schema/
SDK leaves defaultmarket2 paths unchanged. Corrected perpetual wallet tracks
realized PnL/fees, not opening notional; risk consumes marked/native conservative
available equity. Native watchdog contains orphan child even when its loop hangs;
SIGKILL containment is not graceful disposal/recovery.

Actual CLI/FD and temporary database recipe: `docs/runbooks/paper-service.md`.
Native paper_sandbox.py retains LGPL-3.0-only; mixed MIT AND LGPL-3.0-only package
ships LICENSES/NOTICE and companion GPLv3 base terms without relicensing original
MIT files. No exchange connection/real trades or DSH mutation cutover. Next
mandatory work remains authenticated DSH paper controls, native Testnet plus TS
exchange-write cutover, full replay/recovery, strategies/AI/isolated research.
Mainnet untested; no user database migration.

## Historical accepted foundations and receipts

- Risk/ledger code411de43f07984f8d2af163c6e95abd53c3d98dc9 was committed/pushed with exact remote match, hooks0 and CI44081030699 both jobs success. Risk61/ledger28 scoped ACCEPTs, Python213, SBOM200/91, scans and original failures are retained in Verify Gate. This historical snapshot had no engine admission route; the current optional synthetic paper app above supersedes that absence only in its scoped environment.
- Read-only service/SDK/DSH/native-backtest/hooks scoped ACCEPTs remain in `sdd/reviews/REVIEW_{ENGINE_CLIENT,DSH_ENGINE,NAUTILUS_EXECUTION,GIT_HOOKS,ENGINE_TRANSPORT,ENGINE_SUPERVISOR,ENGINE_SERVICE}_2026-11-17.md`. Default market service owns bounded public Testnet streaming/consumer/supervisor; checkpoint persists reconnect count only. No account/private API route or full snapshot/recovery.
- DSH read tools/bridge/card share Python-generated validated SDK, numeric-loopback/byte/deadline/cancellation guards. Non-Testnet Host rejects before HTTP; no credentials passed, no polling, Host unload does not stop independent service. Private TS runtimes inlined; external archive import and real React19 SSR prove closure/render only, not installed authentication, upgrade or browser effects/visuals.
- Offline native BacktestEngine fixtures remain separate from the new continuous native synthetic runtime. No native Demo/Testnet executor or sole exchange authority is accepted. TS exchange-write drift stays open.
- Historical code4360381/CI44076026205, baseline566092a/CI44077034140 and docs605fe70/CI44081766003 both-job successes remain exact-snapshot receipts. Earlier Python133/native22 and later213 do not certify current paper source.
- Two nested-pnpm ENOEXEC aggregate failures exited1 before correction. Vulnerable fsspec2026.2.0 was explicitly overridden to2026.6.0 with catalog fixtures/security0. Nautilus1.231.0 exact-pin metadata still fails uv pip check1 and standalone pip resolution; require root locked uv, never downgrade merely to clear metadata. Full historical commands/exits are in Verify Gate.

## Remaining original MUSTs / Definition of Done

- [x] Preserve complete original MUST/AT-010–031 and audit initial snapshot plus latest delta.
- [x] Accepted read-only service, generated SDK/DSH, native backtest foundation and safe tooling increments.
- [x] Risk/ledger foundations and native/admission/SDK paper scopes have independent review; final paper aggregate receipts tracked above, not inferred from old scans.
- [ ] Nautilus sole exchange order authority and direct TS REST cutover. DRIFT-ORIGINAL-003 remains OPEN; offline native tests do not resolve live authority.
- [ ] Full features/strategies/regime/portfolio/final-risk, AI team, isolated research/controlled evolution, durable uncertain orders/reconciliation and recovery.
- [ ] Complete market snapshot/history/provenance/persistence, authenticated remote control/events, OTel and OS process recovery.
- [x] Hosted CI44081030699 for exact published code411de43: blocking verify and public Testnet jobs successful. Actual pre-commit/pre-push0; push0, exact remote SHA match. Older baseline receipts remain historical.
- [ ] Official upgrade/state preservation, installed Harness auth, browser visual/interaction, provider OAuth and authorized target migration evidence.

## Landmines

No credential/.env reads or logging; no managed Harness profile edits. Mainnet defaults off and real trading requires separate explicit authorization. Testnet retains identity/balance/precision/notional/risk checks. No private account/order request was made this increment. Temporary SQLite is not deployed migration, SSR/pack import is not installed UI, fixtures are not provider consent. Do not create empty packages or claim profits/full platform from directories or local green tests.

## Events

- 2026-11-17: original scope audit restored independent engine/AI research MUSTs; no scaffold scope reduction authorized.
- 2026-11-17: monorepo/service/SDK/DSH/native-backtest/hooks increments accepted and published across f535981,4360381,566092a; exact historical receipts retained in Verify Gate.
- 2026-11-17: risk/ledger code411de43 published, exact remote match/hooks0/CI44081030699 both jobs passed; docs baseline605fe70 CI44081766003 both jobs passed. PR1 remains draft, no main merge/deployment/orders.
- 2026-11-17: current paper increment adds separate native process, optional authenticated app, transactional reservations and separate schema/SDK. Review found and corrected spot/perpetual economic mismatch, marked available-equity ambiguity, expiry/protection and orphan cleanup. Current scoped evidence above supersedes only those reviewed gaps; full original MUSTs remain open.
- User already authorizes feature-branch commit/push after sdd-release checks; never force, infer deployment or edit managed Harness profiles.

## Setup / next tasks

```sh
cd /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant
pnpm install --frozen-lockfile
uv sync --project python --locked
uv run --project python --locked quant-engine --symbols BTCUSDT ETHUSDT
```

Market runbook: `docs/runbooks/engine-service.md`, loopback8765. Synthetic paper
CLI/privateFD/tempDB: `docs/runbooks/paper-service.md`, explicit separate app.
Read `DESIGN_EXECUTION_CUTOVER.md`, `DESIGN_PAPER_{NATIVE,ADMISSION,SDK,WORKSPACE}.md`
and `DESIGN_ADMISSION_STORE.md` under `sdd/features/` for current contracts.

1. Inspect local paper delta from published docs605fe70/Draft PR1. All local gates, scoped reviews and license artifacts pass; perform final release staging/diff checks before authorized publication; root records actual SHA/remote/CI. This paper delta is not published yet.
2. Continue authenticated DSH paper controls, native Testnet and TS mutation cutover, then original strategy/AI/research/recovery MUSTs in dependency order. Design/manifest first, independent review before integration. Future subagents explicitly `model="gpt-6.1-sol"`, `reasoning_effort="medium"`, `fork_turns="none"`, with self-contained task context. Primary orchestrator remains parent; primary model unchanged.
3. Read `.agents/skills/sdd-release/SKILL.md` before commit/push; inspect diff/staging/secrets/history/baseline, never force or claim merge/deployment. No worktree cleanup without user instruction.

## Resume prompt

```text
Continue BYBIT_AI_QUANT in /Users/litlesnow/Desktop/Project/幻方量化/bybit-quant, branch codex/bybit-ai-quant-sdd. Read sdd/handoffs/HANDOFF_BYBIT_AI_QUANT.md, AGENTS.md, DEFINE/main DESIGN, ORIGINAL_SCOPE_AUDIT_2026-11-17.md and VERIFY_GATE_2026-11-17.md first.
Published documentation baseline605fe709461e7157885da07216654a1da677926c / Draft PR https://github.com/XueHua-s/dsh_bybit_plugin/pull/1; CI44081766003 both jobs succeeded (parent verified). New local paper native/admission/SDK scoped reviews and actual built-SDK CLI process E2E pass; data43/fullPython252/security/SBOM now pass; final source/secret/history and GPL artifact checks pass; current delta remains uncommitted/unpushed with no current hosted CI. Runbook docs/runbooks/paper-service.md covers actual CLI/privateFD and disposable SQLite. No publication of this paper delta yet; older risk/ledger receipts do not certify new source. quant-risk is pure veto; ledger scoped ACCEPT is local durability, not execution authority. DESIGN_EXECUTION_CUTOVER.md and DESIGN_PAPER_* plus DESIGN_ADMISSION_STORE.md govern this in-progress native paper implementation; a design is not runtime acceptance. TS REST bypass, full risk/OMS/strategy/AI/research, private state/recovery and official upgrade/provider OAuth remain open.
Inspect git status --short --branch. Setup: pnpm install --frozen-lockfile; uv sync --project python --locked. Gates: NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify; same prefix pnpm typecheck:tests; pnpm python:lint; pnpm python:typecheck; pnpm python:test; pnpm sdk:check; uv run --project python --locked quant-engine-openapi --output contracts/openapi/quant-engine.v1.json --check; regenerate SBOMs/security/secret/line/diff. Record actual commands/exits. Loopback mocks need binding permission. Runbook docs/runbooks/engine-service.md defines service/readiness/shutdown. Root uv fsspec override2026.6.0 remains metadata-incompatible with Nautilus1.231.0 exact pin, deliberately retained for security.
Do not read/print credentials, enable Mainnet, send unauthorized orders, edit managed profiles or apply user/target migrations. User authorizes feature-branch commit/push after sdd-release checks; inspect safe remote baseline, never force or claim deployment. No scaffold scope reduction. Future subagents explicitly use gpt-6.1-sol, reasoning_effort medium, fork_turns none; provide self-contained task context. Primary chat model was not changed.
```
