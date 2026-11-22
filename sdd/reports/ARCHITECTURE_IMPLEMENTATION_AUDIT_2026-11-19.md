# Architecture implementation audit

Original audit date: 2026-11-19 · Current-state refresh: 2026-11-22
Source of truth: the user supplied architecture brief (`pasted-text-1.txt`),
`sdd/features/DEFINE_BYBIT_AI_QUANT.md`, and the current workspace source.

This is an evidence report, not a claim that the complete product is finished.

**Current-state note (2026-11-22):** Later dated receipts in this report
supersede earlier rows that describe the Host-to-Python internal-paper path as
disconnected. The packaged `internal_paper` process now provisions the built-in
credential-free fixture registry and the Host process harness reaches the
Python selector → portfolio planner → independent risk → synthetic OMS path.
Those receipts do not change the separate Testnet/Mainnet execution boundary,
the prompt-evaluation gate, or the scheduler's durable lease/restart status.

## Current capability

| Area | Evidence | Status |
|---|---|---|
| Dashboard boundary | `apps/dsh-plugin/src/client-market-view.ts`, `test/render.ts`, `test/integration.ts` | **Implemented**. Symbol, category and interval controls change the displayed chart request only. They do not enter the AI candidate universe or simulated decision parameters. |
| Dynamic AI universe | `apps/dsh-plugin/src/lib/ai-universe.ts`, `test/ai-universe.ts` | **Implemented for the plugin slice**. Bybit instrument pages and ticker data are joined, filtered by trading status, USDT/category, quantity and price rules, turnover and spread, then bounded and ranked. Discovery failure fails closed. |
| Background AI loop | `apps/dsh-plugin/src/lib/ai-scheduler.ts`, `src/lib/paper-ai-cycle.ts`, `src/host-tools-ai.ts`, process harness | **Implemented as opt-in internal-paper/testnet research with different execution paths**. Each wake-up has one bounded DSH Agent turn. Internal paper calls the authenticated Python fixture/cycle API and records its durable receipt; the packaged process harness verifies a synthetic fill through Host tools. Testnet still records only to the local simulated journal. Host scheduler ownership/leases are in memory, and independent prompt/model evaluation remains open. |
| Native internal paper | `python/apps/quant-engine/src/quant_engine/paper_admission.py`, `paper_cycle_service.py`, `paper_bootstrap.py`, `quant-execution` tests | **Implemented and process-tested for synthetic fixtures**. The service provisions a credential-free fixture registry, runs selector → portfolio planner → independent risk → durable admission → isolated native synthetic OMS, and protects uncertain/restart states. This does not use live exchange prices or prove profitability. |
| Bybit Testnet execution | `python/packages/quant-execution/src/quant_execution/bybit_http_provider.py`, `bybit_preflight.py` | **Not implemented**. The provider is deliberately GET-only and preflight returns `order_submission_allowed=False`. `bybit_trade` returns `execution_authority_unavailable` before any exchange request when `dryRun:false`. No Testnet order was sent. |
| Mainnet OAuth | `apps/dsh-plugin/src/lib/bybit-oauth.ts`, `test/oauth.ts`, README receipt | **Read/account setup only**. Mainnet PKCE endpoints and environment-scoped credential storage are implemented and the recorded account-list request succeeded with an empty list. Mainnet trading remains disabled; no production order was sent. |
| DSH Bundle packaging and lifecycle | `apps/dsh-plugin/package.json`, `cordis.patch.yml`, `tsdown.config.ts`, `scripts/check-bundle.ts`, and `sdd/reports/PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md` | **Packaged and CLI lifecycle-tested with limits**. The current 1.4.5 tarball passes the Bundle check and installs/removes in a disposable profile using DSH CLI 0.2.2-rc.5; synthetic credential/token/state fixture hashes outside the package tree were unchanged. Earlier CLI receipt upgraded 1.4.5→1.4.6 via a loopback registry. Direct Host `plugin_manager.install_bundle`/`updateBundle` activation, rollback, current-source version upgrade, and active Host state preservation remain unverified; no public-registry package is claimed. |
| GitHub strategy frameworks | `docs/research/github-repository-audit.md`, `python/packages/quant-strategies`, `sdd/reports/BUILD_REPORT_STRATEGY_FAMILIES.md` | **Not wholesale integrated**. The repository contains independent, tested research implementations (SMA/EMA cross, Donchian, ADX trend, momentum, Bollinger/Z-score/RSI reversion, ATR breakout, funding carry and a small Alpha158 subset). The audited TradingAgents, RD-Agent, FreqAI, VectorBT, FinRL, ElegantRL and Hummingbot repositories are references only. |
| Full autonomous quant platform | DEFINE AT-010–031 and architecture §§1–26 | **Partial**. The internal-paper Host path now invokes fixture-bound strategy selection, portfolio planning and independent risk, and has a fake-Agent process receipt. This closes neither actual model-quality evaluation nor durable Host scheduler recovery. Bybit Testnet order writes, full exchange/account/order reconciliation, live Nautilus Bybit authority, research/evolution lifecycle and remaining architecture acceptance are open. |

## Verification receipts

The following commands were executed in this workspace on 2026-11-19:

| Command | Exit | Result |
|---|---:|---|
| `pnpm run verify` | 0 | TS build, lint, strict typecheck, tests, bundle check, OpenAPI drift check, SDK tests and tooling checks passed. |
| `pnpm run python:lint` | 0 | Ruff check and format check passed. |
| `pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| `pnpm run python:test` | 0 | 405 tests passed; 11 upstream/deprecation warnings. |
| `pnpm run security:deps` | 0 | npm audit and pip-audit reported no known high/critical vulnerabilities; editable distributions were skipped by pip-audit. |
| `gitleaks dir --redact --no-banner` | 0 | No leaks found across the worktree. |
| `pnpm run sbom` | 0 | CycloneDX SBOM written with 200 npm components; Python SBOM is tracked from the locked workspace. |
| `nx show projects` | 0 | 8 Nx projects discovered, including `quant-engine`, `quant-strategies`, `quant-execution`, `quant-data`, risk, contracts, SDK and DSH plugin. |

## Acceptance boundary

The project is not ready to claim unattended Bybit Testnet trading. Internal-paper now has a synthetic Host-to-Python process receipt, but the Bybit provider is still read-only. A safe execution slice must add the architecture-mandated Nautilus Testnet adapter behind engine admission and prove, with Testnet-only credentials and fixtures, account identity, balance, instrument constraints, idempotent command recovery, order/position reconciliation, stale-data protection, emergency stop and restart behavior. The adapter must remain unavailable by default and Mainnet must remain separately locked.

The current implementation is therefore suitable for dashboard observation, dynamic AI market research and internal paper testing. It is not evidence of profitability, exchange execution, or a production autonomous trader.

## 2026-11-20 portfolio boundary update

The workspace now contains `python/packages/quant-portfolio`, a pure target
allocation planner, and `quant_engine.portfolio.selection_to_proposal`, a
selector-to-proposal adapter. They carry strategy confidence and evaluation
evidence into bounded target exposures, preserve omitted positions, record
abstentions, cap gross exposure and turnover, and split sign reversals into
reduce/recheck/increase phases. They do not access credentials, account state,
the exchange or an order API. The long-running AI scheduler does not yet invoke
this adapter, so this update does not change the **Partial** autonomous-trading
status above.

Fresh verification on 2026-11-20: `pnpm run verify`, `pnpm run python:lint`,
`pnpm run python:typecheck`, `pnpm run python:test` (424 passed, 11 warnings),
`pnpm run security:deps`, `pnpm run sbom`, Python SBOM generation through
`quant-data:sbom`, `gitleaks dir --redact --no-banner`, `pnpm exec nx show
projects`, `pnpm exec nx graph --file=/tmp/bybit-quant-nx-graph.json`, and
`git diff --check` all exited 0. Nx discovers the package and the dependency
graph contains `quant-engine → quant-portfolio`.

## 2026-11-20 continuation verification and workspace hygiene

An independent rerun in the current worktree recorded these receipts:

| Command | Exit | Result |
|---|---:|---|
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | Workspace build, lint, typechecks, DSH tests, bundle/API checks and tooling checks passed. |
| `pnpm run python:lint` | 0 | Ruff passed; 96 Python files were already formatted. |
| `pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| `pnpm run python:test` | 0 | 424 passed; 11 upstream/deprecation warnings. |
| `pnpm run security:deps` | 0 | No known npm vulnerabilities; pip-audit skipped six local editable distributions. |
| `pnpm run sbom` | 0 | CycloneDX npm SBOM written with 200 components. |
| `pnpm exec nx run quant-data:sbom` | 0 | Python SBOM target succeeded. |
| `gitleaks dir --redact --no-banner` | 0 | No leaks in approximately 31.14 MB scanned. |
| `pnpm exec nx show projects` | 0 | Nine projects discovered. |
| `pnpm exec nx graph --file=/tmp/bybit-quant-nx-graph.json` | 0 | Graph includes `quant-engine` edges to `quant-data`, `quant-risk`, `quant-execution`, `quant-portfolio`, and `quant-strategies`. |
| `git diff --check` | 0 | No whitespace errors in tracked changes. |

The first ad-hoc graph reader looked for `dependencies` at the JSON root and
exited 1; the Nx artifact stores it under `graph.dependencies`. The corrected
read succeeded and confirmed the edges listed above. This was a report-reader
assumption, not a failed Nx graph task.

The worktree also contains untracked root-level `agent.ts` (751 lines) and
`index.ts` (838 lines). They import missing root siblings such as `inbox.ts`,
`runtime-context.ts`, and `constants.ts`, and no active workspace manifest or
Nx project references them. They do not belong to the DSH Bundle paths reviewed
here and exceed the repository's 500-line source limit. They were left intact
because their ownership is unclear; do not include them in a Bundle release
without resolving that provenance and restoring the required project boundary.

## 2026-11-20 Chrome visual check — reconciled

An earlier read-only Chrome pass found Bybit's public AI-agent integration
guide rather than a local dashboard preview. A later read-only inspection of
the active DSH panel is recorded in
`sdd/reports/UX_REVIEW_DSH_BYBIT_UI_2026-11-19.md` and supersedes that earlier
observation: the panel displayed the Testnet/write-unavailable boundary,
unknown account and engine readiness, the default-off scheduler state, and
the AI candidate summary. It also described symbol, market and interval as
chart-only filters and stated that the AI independently chooses eligible
instruments and decision parameters. No trade or account control was activated.

The screenshot's original labels (`交易对`, `市场`, `周期`) were ambiguous. The
current worktree labels them `图表币种`, `图表市场`, and `图表 K 线周期`, under
`行情查看（仅展示）`, and explains that AI independently selects symbols,
direction, size, exits and holding horizon. SSR and integration tests cover
that display/decision boundary and verify dashboard filters do not alter the AI
candidate universe. The manual inspection still does not prove exchange writes,
account/order reconciliation, process recovery, or unattended trading
readiness; those remain unimplemented or unverified as listed above.

Follow-up copy refinement: the chart interval is explicitly labeled
`图表 K 线周期` so it is not confused with the AI decision's holding horizon.
The Chinese display card is titled `行情查看（仅展示）` and names the AI-owned
choices (whether to trade, symbol, direction, size, exits and holding horizon).
`CI=1 NX_DAEMON=false pnpm exec nx run @bybit-quant/dsh-plugin:build`,
`CI=1 NX_DAEMON=false pnpm exec nx run @bybit-quant/dsh-plugin:test:unit`,
`CI=1 NX_DAEMON=false pnpm exec nx run @bybit-quant/dsh-plugin:typecheck:tests`,
and `git diff --check` all exited 0 after this copy change. This source change
is not yet a new Plugin Manager installation receipt.

## 2026-11-20 current-source Bundle and workspace verification

The installed DSH CLI path was rechecked and reported `0.2.2-rc.5`. The current
`@bybit-quant/dsh-plugin@1.4.5` package passed `pnpm exec nx run
@bybit-quant/dsh-plugin:bundle:check` and packed successfully. The packed
tarball contained the Host/Client entries, `cordis.patch.yml`, package metadata,
locales, docs, and bundle scripts. In an isolated `DSH_HOME`, the official CLI
installed and removed both the local source and the packed tarball. A separate
packed install/remove run kept the SHA-256 hashes of synthetic environment-
scoped credential, token, and state/history files unchanged. An initial remove
attempt without the `DSH_HOME` environment was refused because the default
profile had no such dependency; read-only checks showed no default-profile
change, and the corrected command explicitly targeted the disposable profile.

Fresh receipts after adding the lifecycle report:

| Command | Exit | Result |
|---|---:|---|
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | Workspace build, lint, typechecks, DSH tests, Bundle/API checks and tooling checks passed. |
| `pnpm run python:lint` | 0 | Ruff passed; 96 files already formatted. |
| `pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| `pnpm run python:test` | 0 | 424 passed; 11 upstream/deprecation warnings. |
| `pnpm run security:deps` | 0 | No known npm vulnerabilities; pip-audit skipped six editable local distributions. |
| `pnpm run sbom` | 0 | CycloneDX npm SBOM generated with 200 components. |
| `pnpm exec nx run quant-data:sbom` | 0 | Python SBOM target succeeded. |
| `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | 0 | No leaks in approximately 31.42 MB scanned. |
| `pnpm exec nx show projects` | 0 | Nine Nx projects discovered. |
| `git diff --check` | 0 | No whitespace errors. |

## 2026-11-22 Bundle upgrade and legacy-paper boundary correction

The checked-in disposable lifecycle smoke now exercises the full local CLI
sequence `install → upgrade → remove`. It packs the current `1.4.5` Bundle,
creates a temporary `1.4.6` archive without changing the tracked package
version, installs both through the official DSH CLI in a temporary `DSH_HOME`,
and verifies the selected Bundle and installed version after each mutation.
Synthetic credential, strategy-config and paper-history sentinel hashes remain
unchanged; no exchange request is made.

Receipt:

```text
pnpm --dir apps/dsh-plugin run bundle:lifecycle  # exit 0
{"ok":true,"dshVersion":"0.2.2-rc.5","package":"@bybit-quant/dsh-plugin",
 "lifecycle":["install","upgrade","remove"],
 "versions":{"installed":"1.4.5","upgraded":"1.4.6"},
 "selectedAfterInstall":true,"selectedAfterUpgrade":true,
 "selectedAfterUninstall":false,"statePreserved":true,
 "exchangeRequests":0,"dshHome":"<temporary>"}
```

This is evidence for the official CLI package-manager path in an isolated
profile. It does not prove the in-process Host `plugin_manager.install_bundle`
or `updateBundle` activation method, rollback after a failed upgrade, or
active-profile preservation. Managed Harness profile files were not edited.

The old `quant_submit_paper_order` tool remains only as a compatibility seam
for a fixed synthetic BTCUSDT LIMIT command. Its description now labels it as
legacy, explicitly separates it from the autonomous AI path, and points the
model to `quant_brief` plus `quant_decide_background` for AI-selected symbols.
The background loop allow-list excludes this tool, so the dashboard and
unattended AI path cannot use a fixed-symbol direct command. The fixed tool is
still synthetic and does not grant Testnet/Mainnet authority.

The focused checks after this correction were `pnpm --dir apps/dsh-plugin run
typecheck:tests` (exit 0), `pnpm --dir apps/dsh-plugin run bundle:lifecycle`
(exit 0), `pnpm --dir apps/dsh-plugin run verify` (exit 0; build, lint,
strict source/test typechecks, unit suites and Bundle scan), and `git diff
--check` (exit 0). Product status remains **INCOMPLETE/PARTIAL** because
Testnet writes, exchange reconciliation, independent prompt evaluation, and
durable unattended recovery are still open.

The current source has a successful CLI package install/remove receipt and
synthetic outside-tree state-preservation smoke. This remains weaker than a
Host `plugin_manager.install_bundle`/`updateBundle` invocation with actual Host
activation, rollback and upgrade-state assertions. Testnet order submission is
still unavailable and no test or Mainnet orders were sent. The entire product
and the architecture brief's autonomous exchange-trading acceptance remain
**PARTIAL**.

## 2026-11-20 AI scheduler lifecycle hardening

The scheduler now uses the v4 lifecycle contract in
`apps/dsh-plugin/src/prompts/bybit-quant/LOOP_SPEC-v4.md`. Its default 120-second
monotonic deadline begins before `agents.create()` and covers creation plus
`whenIdle()`. Timed-out creation is aborted; a late handle is cancelled and
cleaned before backoff resumes. Idle/disposal waits are bounded, and uncertain
cleanup clears the timer and blocks future cycles so Agents cannot overlap.
Unload also has a bounded cleanup wait. The active decision prompt remains v3;
this change adds no exchange or account authority.

Fresh receipts: `pnpm --dir apps/dsh-plugin run verify` exit 0,
`CI=1 NX_DAEMON=false pnpm run verify` exit 0, and `git diff --check` exit 0.
The scheduler source is 500 lines and its test is 356 lines. Fake-Agent tests
cover the shared deadline, timeout cancellation, late-handle cleanup,
no-overlap blocking and bounded unload. A real DSH Host lifecycle test is still
needed to prove that cancellation terminates underlying work; until that and
the independent prompt evaluation are available, the background loop is
**implemented as opt-in simulated research**, and the full autonomous quant
platform remains **PARTIAL/BLOCKED**.

## 2026-11-20 simulated decision journal concurrency guard

`apps/dsh-plugin/src/lib/ai-decision-writer.ts` now performs an optimistic
compare-and-swap check inside the synchronous simulated-store mutation. A
decision evaluated against an older AI track is rejected with
`ai_track_changed_during_decision`; it cannot overwrite the newer track or
commit a cycle receipt. If persistence throws after the in-memory replacement,
rollback is conditional on the store still containing that attempted
replacement, so a concurrent newer state is preserved. Successful persistence
still precedes receipt acknowledgement.

`apps/dsh-plugin/test/ai-decision-writer.ts` covers five checks: failed write
without receipt, failed write with a newer concurrent state, stale decision
rejection, successful write/receipt ordering, and a sequential successful
write followed by a stale write based on the old snapshot. The final
`pnpm --dir apps/dsh-plugin run verify` exited 0 after correcting one lint-only
unused-local failure found during rerun. This is a consistency improvement for
the local simulated journal only. It does not add database transactions,
exchange order idempotency, Nautilus execution, account/order reconciliation,
or unattended Testnet trading authority; the autonomous platform status stays
**PARTIAL/BLOCKED**.

Independent source review found no blocking defect in the concrete `createStore`
implementation and confirmed compare-before-write, conditional rollback and
store-write-before-receipt ordering. It identified the sequential
first-success/second-stale scenario as a low-priority test gap; the fifth test
now closes that gap. Custom Store implementations that clone reads or persist
partially before raising are outside the current concrete store contract and
remain an interface limitation rather than an observed production defect.

Final workspace gate after this change: `pnpm --dir apps/dsh-plugin run verify`
and `CI=1 NX_DAEMON=false pnpm run verify` both exited 0 on 2026-11-20;
the latter reran the changed DSH unit-test target rather than relying on its
Nx cache. `git diff --check` exited 0, and a trailing-whitespace scan across
the new concurrency source, test and report files found no matches.

## 2026-11-20 view-only chart suggestion correction

The dashboard follow-up now derives chart symbol suggestions exclusively from
the current AI-discovered candidate pool. A `fresh` pool is shown as a
convenience for inspecting current market data; stale, absent, empty, or failed
discovery produces no suggestions. The previous fixed starter symbols were
removed, and the panel copy states that chart symbol, market, and interval
controls affect presentation only. Render tests cover fresh and stale pools and
assert that no static starter symbol is reintroduced. The plugin Verify Gate
exited 0 after this change. This remains a UI/decision-boundary receipt and
does not establish strategy selection in the background loop or any exchange
execution capability.

## 2026-11-20 AI decision and Python research integration boundary

The dashboard's chart symbol, market, and interval controls remain display-only.
The DSH AI loop reads the fresh eligible universe, chooses whether to abstain
and which eligible symbol(s) to assess, then writes only a simulated decision
through the local journal. A detailed brief can request bounded,
read-only `strategyEvidence` from the Python engine for a symbol the AI has
already selected. That evidence is labeled `research_only` and
`deployment_eligible=false`; it is context for the AI, not a strategy choice,
portfolio target, risk approval, or order instruction.

The Python `strategy_selector` and portfolio planner are implemented and
unit-tested, but the DSH background loop does not call either one. The
Nautilus internal-paper session is another separate capability; it is not
driven by the AI journal or selector. Therefore the product does not yet have a
single AI-to-strategy-to-risk-to-Nautilus pipeline. Bybit exchange submission,
full reconciliation and restart recovery remain unavailable, and no order was
sent in this verification.

For the reviewed DSH/Python decision boundary, the software-design quick check
is **7.5/10** (6 of 8 diagnostics pass). Two diagnostics remain open:

- **Can the implementation change without affecting callers?** This has not
  been proven for strategy selection and portfolio allocation because the DSH
  background loop has no consumer for those APIs. Close this with a typed
  integration boundary and process-level compatibility tests.
- **Does each module own a clear design decision?** No component currently owns
  the AI-to-strategy-to-allocation lifecycle; AI symbol choice, research
  evidence, portfolio planning and native simulation are separate capabilities.
  Define one orchestrator contract without moving long-running work into a DSH
  Tool invocation, then verify its failure and recovery behavior.

Reaching 10/10 requires process-level tests for fresh/stale evidence,
abstention, allocation, risk rejection and recovery. This is a future SDD
design/build slice, not an inference from the currently passing unit tests.

Fresh verification on 2026-11-20:

| Command | Exit | Result |
|---|---:|---|
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | DSH build, lint, source/test typechecks, unit tests, Bundle check, SDK generation/API tests and tooling tests passed; the changed DSH unit-test target ran uncached. |
| `pnpm run python:lint` | 0 | Ruff passed; 98 Python files already formatted. |
| `pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| `pnpm run python:test` | 0 | 438 passed; 11 upstream/deprecation warnings. |
| `pnpm run security:deps` | 0 | No known npm vulnerabilities; `pip-audit` skipped six editable workspace distributions. |
| `pnpm run sbom` | 0 | CycloneDX SBOM generated with 200 npm components. |
| `pnpm exec nx run quant-data:sbom` | 0 | Python SBOM target succeeded. |
| `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | 0 | Scanned approximately 32.86 MB; no leaks found. |
| `pnpm exec nx show projects` | 0 | Nine Nx projects discovered. |
| `pnpm exec nx graph --file=/tmp/bybit-quant-nx-graph-current.json` | 0 | Current project graph generated. |
| `git diff --check` | 0 | No whitespace errors. |

These receipts establish workspace checks and local simulation/research
boundaries only. Full autonomous quant trading against either Testnet or
Mainnet remains **PARTIAL/BLOCKED**.

## 2026-11-21 AI-to-synthetic-paper follow-up audit

The offline Python `internal_paper` path now has integration-test evidence for
fixture-backed strategy selection, portfolio planning, independent risk
evaluation, durable receipt/admission, and routing into the matching isolated
native synthetic OMS. The current Build report records the Python Verify Gate
(`pnpm run python:test`, exit 0, 499 passed) and focused cycle/API/admission
coverage. This is synthetic-paper evidence only.

The DSH unattended path remains disconnected: the active
`background-loop-v4.ts` writes decisions to the local simulated journal;
`apps/dsh-plugin/src/lib/engine.ts` does not call
`POST /api/v1/trading/ai-cycles`; and the Python fixture registry is injected
for tests/service assembly rather than configured for unattended deployment.
Therefore DSH end-to-end unattended trading remains **PARTIAL**. The audited
GitHub algorithm repositories are references; only a research subset of
algorithm families is implemented locally, and this is not wholesale
integration of those repositories.

No Testnet or Mainnet execution readiness is claimed. The Bybit execution
provider/preflight remains GET-only with `order_submission_allowed=False`;
no real order was submitted during this audit or its cited synthetic-paper
verification.

Fresh evidence recorded in `sdd/reports/BUILD_REPORT_AI_TO_SYNTHETIC_PAPER.md`:

| Command / evidence | Result | Scope |
|---|---|---|
| `pnpm run python:test` | Exit 0; 499 passed, 11 deprecation warnings | Offline Python tests including the synthetic-paper integration; no exchange order. |
| `CI=1 NX_DAEMON=false pnpm run verify` | Exit 0 | Workspace and DSH checks; does not connect the DSH journal to the Python cycle endpoint. |
| Source boundary review: `background-loop-v4.ts`, `engine.ts`, Python fixture registry provisioning | DSH journal write remains local; no AI-cycle POST; no unattended registry provisioning found | DSH end-to-end path remains partial. |
| Testnet/Mainnet order activity | Not run; no real order submitted | No execution-readiness claim. |

## 2026-11-21 analysis-first UI and scheduler-scope drift

The supplied screenshot placed engine, native-paper and run-boundary cards
ahead of the chart and profit analysis. The DSH panel source now puts market,
chart, paper/backtest and AI PnL views first, with operational diagnostics in a
default-collapsed “System and runtime status” disclosure. The environment,
API-key-presence and unavailable-write badges stay visible at the top. This is
a presentation-order change only; AI candidate selection and decision inputs
are unchanged. `pnpm --dir apps/dsh-plugin run verify` exited 0, including the
SSR assertion that market view precedes readiness diagnostics. The active
Bundle was not reinstalled for this change, so live discovery and accessibility
of the collapsed section remain unverified.

The parent product Define permits guarded unattended Testnet testing; the
separate synthetic-paper Define limits its own integrated cycle to literal
`internal_paper`. The general DSH scheduler accepts both environments, but its
Testnet branch is only a market-backed simulated-journal path: `engine.ts` is
read-only, the DSH loop does not call `POST /api/v1/trading/ai-cycles`, and the
Python fixture registry is not provisioned for an unattended service. This is
a scoped synthetic-paper design/implementation mismatch, not a contradiction
in the parent Testnet requirement and not evidence that the internal-paper
Host-to-Python cycle is complete. Keep the product status **PARTIAL**; the
internal-paper adapter/provisioning and the separate Testnet execution path
still require their own integration and safety acceptance.

### 2026-11-21 active Harness layout follow-up

The read-only active-Harness accessibility-tree/screenshot review found the
installed panel still places engine, native-paper and runtime-boundary
diagnostics before market and analysis content. The analysis-first,
default-collapsed layout is present in the workspace source and passed the
plugin Verify Gate, but that layout change has not been activated in the
current Bundle. No scheduler was started and no account or order action was
performed. See the matching UX receipt in
`sdd/reports/UX_REVIEW_DSH_BYBIT_UI_2026-11-19.md`.

The fresh plugin Verify Gate on 2026-11-21 exited 0. It covers the changed UI
ordering and existing plugin checks only; no exchange order, account action or
live scheduler cycle was executed.

## 2026-11-21 continuation verification and active-path boundary

The current workspace removes the fixed starter-symbol suggestions from the
chart controls. Suggestions now come only from a fresh AI-discovered candidate
pool; stale, empty, absent or failed discovery shows no candidates. The chart
symbol/market/interval remain view-only and do not enter the AI decision
request. This improves the dashboard's information boundary, but the DSH
background loop still has no call to the Python paper-cycle API.

The runtime-path review confirmed that `create_paper_app` enables fixture and
AI-cycle routes only when a `SyntheticFixtureRegistry` is explicitly injected.
`paper_bootstrap.py` still builds `synthetic_config` without a registry. The
DSH's `engine.ts` remains read-only for health, market and strategy evidence;
the separate `engine-paper.ts` facade now has typed fixture, AI-cycle and
same-request receipt methods, but `host-tools-ai.ts` does not call them. The
tested Python selector → portfolio → risk → synthetic OMS behavior and DSH
local simulated-decision journal therefore remain separate. Runtime fixture
provisioning and the Host AI-cycle caller are still open SDD drift; do not
describe the current DSH loop as end-to-end autonomous paper trading.

Fresh continuation receipts on 2026-11-21:

| Command | Exit | Result |
|---|---:|---|
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | DSH unit tests, Bundle check, API generation check and tooling checks passed; five Nx tasks were cache hits. This gate does not make an exchange request. |
| `pnpm run python:test` | 0 | 499 passed; 11 Starlette/Pandas deprecation warnings. |
| `pnpm run python:lint` | 0 | Ruff check/format passed; 110 files already formatted. |
| `pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` | 0 | Scanned approximately 35.73 MB; no leaks found. |
| `git diff --check` | 0 | No whitespace errors. |

The active Harness observation remains the earlier read-only receipt: its
installed panel still had diagnostics ahead of analysis, while the
analysis-first layout and fresh-pool chart suggestions are verified in the
worktree only. No Bundle update, account action, scheduler cycle or order was
performed in this continuation. GitHub framework repositories remain research
references; the implemented strategies are a local research subset, not those
repositories integrated as a whole. Testnet exchange writes are unavailable
and Mainnet remains disabled. Product status remains **PARTIAL**.

## 2026-11-21 active Bundle restart receipt

According to the handoff receipt, the DSH plugin was re-enabled through the
official Harness Plugin Manager and Harness was restarted. A fresh
accessibility-tree inspection of the active window now confirms the workspace
layout change is active: market data, paper ledger, backtest and AI simulated
PnL appear before the default-collapsed system/runtime diagnostics. The active
panel labels chart symbol, market and candle interval as display-only and
states that AI independently chooses whether to trade, symbol, direction,
size, exits and holding horizon. The header continues to show Testnet,
exchange writes unavailable and API-key presence; no exchange order or
unattended-live control is exposed.

This receipt supersedes the preceding active-path note that the installed
Bundle still used diagnostic-first ordering. It is limited to installation and
accessibility evidence. No scheduler cycle, account mutation, exchange request,
order, reconciliation or restart-recovery test was run. DSH-to-Python cycle
wiring, Testnet execution authority, and the full unattended quant platform
remain **PARTIAL/BLOCKED**.

## 2026-11-21 Host paper facade verification follow-up

The Host facade now has methods for reading a Python fixture snapshot,
submitting an `internal_paper` AI-cycle request, and querying its receipt by
the same request ID after an uncertain result. A test-only result narrowing
error in `apps/dsh-plugin/test/paper.ts` was fixed by checking the discriminant
before reading the failure code. `pnpm --dir apps/dsh-plugin run verify`
exited 0 on 2026-11-21, including build, lint, source/test typechecks, unit
tests, and the packed Bundle boundary scan; five existing non-blocking lint
warnings remain.

This does not close AT-014: the active AI decision tool still persists to the
local simulated journal and never calls the facade, and the packaged
`paper_bootstrap.py` still does not inject a fixture registry. Prompt/loop
evaluation, Testnet execution authority, order/account reconciliation,
restart recovery, and Mainnet trading remain incomplete. No exchange order
was sent. Overall autonomous quant-trading status remains **PARTIAL**.

## 2026-11-22 deployment provisioning drift and process receipt

The packaged paper entry point now creates a single `builtin-synthetic`
`SyntheticFixtureRegistry` in memory from the canonical `synthetic_config`
fixture and injects it into `create_paper_app` for both capability transport
modes. The helper verifies the internal-paper environment and canonical
BTCUSDT instrument, emits 32 bounded synthetic bars plus approved fixture-only
SMA evidence, and performs no file/network/credential discovery. This closes
the prior deployment gap where fixture and AI-cycle routes returned `503`.

The Design document's earlier “`paper_bootstrap.py` remains unchanged” rule is
therefore a recorded implementation drift, justified by the requirement for a
real process-level unattended-paper boundary. `test_paper_process.py` now
starts the actual CLI, authenticates the fixture snapshot, submits an abstain
AI-cycle request and retrieves the same durable receipt by request ID; an
unauthenticated snapshot remains denied. This is internal-paper evidence only.

Exchange execution authority, Testnet writes, Mainnet access, prompt gate,
scheduler persistence, lease/restart recovery and the DSH background caller
remain incomplete; overall product status stays **PARTIAL**.

## 2026-11-22 internal-paper Host boundary follow-up

The workspace now contains a guarded `internal_paper` decision path in
`host-tools-ai.ts`: `quant_brief` reads the authenticated fixture snapshot,
candidate selection is limited to that snapshot, and the scheduled decision
binds strategy ID/version, evidence digest, signed target exposure, fixture
digest and cycle identity before calling the paper facade. An ambiguous cycle
transport result is resolved only with `cycleRequest` for the original request
ID; no new request is generated. Testnet continues to use the separate local
simulated journal path.

This is a boundary implementation, not proof of unattended service operation.
`paper_bootstrap.py` still constructs `synthetic_config` without injecting a
`SyntheticFixtureRegistry`, so a deployed bootstrap process cannot serve the
fixture/cycle routes. No Host-to-Python process E2E, bundle A/B scheduler run,
restart recovery, or model prompt evaluation was performed. The scheduler
remains default-off; Testnet/Mainnet order authority, reconciliation and
production execution remain unavailable.

Receipts for this follow-up: DSH source/test typechecks and the paper facade
test exited 0; the Python suite exited 0 with 499 passed and 11 deprecation
warnings; `git diff --check` exited 0. Product status remains **PARTIAL**.

## 2026-11-22 uncertain paper receipt boundary

`host-tools-ai.ts` now treats `partially_filled` as uncertain alongside
admitted/accepted/protected/unknown/claimed/selected. The scheduler receipt
status is `uncertain`, which blocks automatic rescheduling and keeps the raw
Python receipt available for same-request reconciliation. This prevents a
possible partial or protected synthetic position from being mistaken for a
simple risk rejection. The panel labels the outcome as uncertain and paused.

The plugin Verify Gate passed after this change. It does not close the larger
gaps: `paper_bootstrap.py` still lacks unattended fixture-registry provisioning,
the DSH→Python process E2E is absent, prompt evaluation and restart/lease
recovery remain open, and Testnet/Mainnet writes remain unavailable.

## 2026-11-22 final verification rerun

| Command | Exit | Result |
|---|---:|---|
| `pnpm --dir apps/dsh-plugin run verify` | 0 | Build, lint, source/test typechecks, unit suites and packed Bundle checks passed; five existing non-blocking lint warnings remain. |
| `pnpm run python:test` | 0 | 499 tests passed; 11 upstream deprecation warnings. |
| `git diff --check` | 0 | No whitespace errors. |

These are offline/local verification receipts. They do not close the missing
fixture-registry bootstrap, Host-to-Python process E2E, prompt evaluation,
restart/lease recovery, Testnet write authority or Mainnet execution gates.
The GitHub strategy repositories remain references; the implementation is a
local research subset.

The same rerun includes a Host guard for non-ambiguous `paper.cycle` failures:
typed local or HTTP denials release the reservation and are not mislabeled as
an uncertain outcome; transport ambiguity still requires same-request recovery
and blocks automatic scheduling. This is a local boundary fix, not process
 E2E evidence.

## 2026-11-22 correction: bootstrap and process receipt are now current

The historical notes above that say `paper_bootstrap.py` does not inject a
fixture registry describe the state before the deployment-provisioning change.
The current source injects the built-in credential-free registry in both
capability-FD and private-broker startup paths. `test_paper_process.py` now
exercises the actual CLI, authenticated fixture retrieval, a bounded long
synthetic cycle and same-request durable receipt recovery; the unauthenticated
fixture request remains denied. Treat the 2026-11-22 deployment-provisioning
receipt as the current state and the earlier notes as historical receipts.

Latest local Verify Gate receipts:

| Command | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest python/apps/quant-engine/tests python/packages/quant-data/tests python/packages/quant-execution/tests` | 0 | 396 passed; 11 upstream/deprecation warnings. |
| `pnpm run python:lint` | 0 | Ruff check and format check passed. |
| `pnpm run python:typecheck` | 0 | Pyright reported 0 errors, warnings or informations. |
| `pnpm --dir apps/dsh-plugin run verify` | 0 | Build, lint, source/test typechecks, unit suites and packed Bundle checks passed; five existing non-blocking lint warnings remain. |
| `git diff --check` | 0 | No whitespace errors. |

This correction does not change the product boundary: Testnet/Mainnet order
authority, scheduler prompt evaluation, durable lease/restart recovery and
full unattended DSH execution remain **PARTIAL/BLOCKED**. GitHub strategy
repositories remain references; the implementation is a local research
subset. No exchange order was sent.

## 2026-11-22 final cleanup verification

The scheduler's optional Agent service boundary is isolated in
`ai-agent-services.ts`; the scheduler is 448 handwritten lines and
`paper_admission.py` is 498 lines. The cleanup removed an unused scheduler
import and did not change execution policy. Current gates are green:

- `pnpm --dir apps/dsh-plugin run verify` — exit 0; five existing lint warnings.
- `CI=1 NX_DAEMON=false pnpm run verify` — exit 0; workspace build, lint,
  typechecks, DSH tests, Bundle/API checks and tooling safety checks passed.
- `pnpm run python:test` — exit 0; 500 passed, 11 existing warnings.
- `pnpm run python:typecheck` — exit 0; no errors, warnings or informations.
- `pnpm run python:lint` — exit 0.
- `git diff --check` — exit 0.

These receipts remain offline/local. They do not close prompt evaluation,
background deployment, durable lease/restart recovery, Testnet exchange
writes, reconciliation, or Mainnet execution; product status remains
**PARTIAL/BLOCKED**.

The repository-wide Python gate subsequently covered all workspace packages
and apps: `pnpm run python:test` exited 0 with 500 passed and 11 upstream/
deprecation warnings. `pnpm run security:deps`, `pnpm run sbom`,
`pnpm exec nx run quant-data:sbom`, and
`gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` all exited 0;
the latest secret scan covered approximately 37.01 MB with no leaks. The
root `CI=1 NX_DAEMON=false pnpm run verify` gate also exited 0, including SDK
generation checks, API-client tests and tooling safety checks.

As a complexity-boundary correction, the optional DSH Agent service contract
and runtime validation now live in `apps/dsh-plugin/src/lib/ai-agent-services.ts`;
`ai-scheduler.ts` owns scheduling, receipt and lifecycle policy. This keeps
the scheduler below the repository's 500-line handwritten-source limit while
encapsulating the untrusted service boundary. The plugin Verify Gate passed
after the split.

## 2026-11-22 paper-cycle contract-test completion

The Design manifest's TypeScript contract test is now present at
`apps/dsh-plugin/test/ai-paper-cycle.ts` and is included in the plugin unit
script. It exercises the pure Host helper boundary without network access:
fixture-owned candidate lookup, selector-evidence identity binding, internal-
paper/session and bundle-digest propagation, signed target-exposure/action
consistency, canonical payload hashing, and fail-closed rejection of unknown
symbols, mismatched evidence, invalid direction/exposure pairs and non-finite
values. It does not start the scheduler, contact Python, Bybit, Testnet or
Mainnet, and it does not replace the missing DSH Host-to-Python process E2E.

Receipt: `pnpm --dir apps/dsh-plugin run verify` exited 0 on 2026-11-22. The
new test printed `ai paper cycle: fixture identity, evidence binding, digest,
and fail-closed checks passed`; the existing five non-blocking lint warnings
remain. The background prompt-evaluation gate, durable scheduler lease/restart
recovery, Testnet execution authority and Mainnet writes remain incomplete.

## 2026-11-22 DSH paper process harness rerun

The packaged DSH paper-process harness was rerun after the fixture-registry
bootstrap correction:

```text
pnpm --dir apps/dsh-plugin run test:paper-process  # exit 0
{"result":"ok","environment":"internal_paper","synthetic":true,
 "commands":4,"native_filled":3,"risk_rejected":1,
 "injected_postdispatch_503":true,"actual_fault_submit_posts":1,
 "host_close_survived":true,"native_reaped":true,"listeners_closed":true,
 "restart":"protected","capability_disclosed":false}
```

This proves the isolated DSH Host paper command process boundary, private
capability handling, idempotent request identity, uncertain-result recovery,
native child reaping and protected restart behavior. It remains an
`internal_paper` harness receipt: it does not grant Bybit Testnet/Mainnet
execution authority and does not replace the separate prompt-evaluation,
durable scheduler lease/restart, or full Host-tool-to-Python AI-cycle gate.
## 2026-11-22 reproducible Bundle lifecycle smoke

`apps/dsh-plugin/scripts/plugin-manager-smoke.ts` is now the checked-in,
disposable lifecycle harness. `pnpm --dir apps/dsh-plugin run
bundle:lifecycle` exited 0 with DSH CLI `0.2.2-rc.5`: the packed `1.4.5`
Bundle was installed into a temporary `DSH_HOME`, the disposable profile
selected it, it was removed through the official CLI, and the profile no
longer selected it. Synthetic credential, strategy-config and paper-history
sentinel hashes were unchanged; the receipt reports zero exchange requests.
The script fails with an explicit external blocker when no official CLI is
available and never reads or prints credential contents.

This strengthens reproducibility for CLI install/remove only. It does not
prove Host `plugin_manager` activation, version-to-version upgrade/rollback,
or active-profile state preservation; those remain separate Bundle gaps.

The Nx `test:unit` target was also synchronized with the package script on
2026-11-22 so the root Verify Gate executes the dynamic-universe, market-brief,
paper-cycle and scheduler contract tests. A forced run of
`pnpm exec nx run @bybit-quant/dsh-plugin:test:unit --output-style=static`
exited 0; `CI=1 NX_DAEMON=false pnpm run verify` and `git diff --check` also
exited 0 after the target update.

## 2026-11-22 Host AI-cycle process receipt (current)

The current packaged process harness drives the opt-in `internal_paper`
background Agent through the real Host tools. A fake Agent executes candidate
discovery, fixture-owned selector-evidence selection and
`quant_decide_background`; Host code reads the authenticated Python fixture,
posts one bounded cycle, then performs a same-request receipt lookup. The
Python receipt was terminal `filled` and the Host scheduler receipt was
`open`. No local AI journal write, Bybit Testnet request or Mainnet request was
made. Existing command/risk-veto, post-dispatch 503, child reaping and
protected-restart assertions also passed.

Receipt:

```text
pnpm --dir apps/dsh-plugin run test:paper-process  # exit 0
{"result":"ok","environment":"internal_paper","synthetic":true,
 "commands":4,"native_filled":3,"risk_rejected":1,
 "injected_postdispatch_503":true,"actual_fault_submit_posts":1,
 "host_close_survived":true,"native_reaped":true,"listeners_closed":true,
 "restart":"protected","capability_disclosed":false}
```

The SDK boundary regression also passed:
`pnpm --filter @bybit-quant/quant-api-client test` — exit 0, 25 tests. Only
bounded integer keys ending in `_ns` may exceed the safe-integer fence; the
fixture regression confirms an oversized ordinary confidence number is still
rejected. This closes the previously missing **internal-paper process
receipt**, while prompt evaluation, durable scheduler lease/restart recovery,
Testnet execution authority/reconciliation and Mainnet writes remain
incomplete. Overall status stays **INCOMPLETE/PARTIAL**; no exchange order was
sent.

## 2026-11-22 current answer to the UI and algorithm-scope review

The dashboard controls are now presentation controls only. `client-market-view.ts`
receives suggestions exclusively from a fresh AI-discovered candidate pool;
there is no fixed BTC/ETH/SOL/XRP/DOGE/BNB starter list. Changing the chart
symbol, market type or candle interval changes only the read-only market query.
The AI loop owns candidate selection, abstention, direction, target exposure,
risk parameters and holding horizon. The internal-paper panel and route expose
status, PnL and analysis; they do not expose a user order form or exchange-write
control.

The architecture brief's algorithm repositories are **not** wholesale runtime
dependencies. The project has a local, independently tested research subset:
SMA/EMA cross, Donchian, ADX trend, time-series momentum, Bollinger/Z-score/RSI
reversion, ATR breakout, funding carry and five independently rewritten
Alpha158 factors. The audited TradingAgents, RD-Agent, FreqAI, VectorBT, FinRL,
ElegantRL and Hummingbot repositories remain reference-only. In the
`internal_paper` path, the AI-selected symbol is bound to fixture-owned
strategy evidence; Python then executes the registered selector and portfolio
planner before independent risk and the isolated synthetic OMS. This is a
verified research/paper path, not a profitability or live-trading claim.

The general Testnet mode still uses a separate simulated journal and the Bybit
provider remains GET-only with `order_submission_allowed=false`; no Testnet or
Mainnet order was sent. Prompt/model evaluation, durable Host scheduler
lease/restart recovery, complete exchange reconciliation and Nautilus-backed
Testnet execution remain open gates.

Latest local receipts for this review:

| Command | Exit | Result |
|---|---:|---|
| `pnpm --dir apps/dsh-plugin run verify` | 0 | Plugin build, lint, strict source/test typechecks, 19 unit suites and packed Bundle boundary checks passed; five existing non-blocking lint warnings remain. |
| `pnpm run python:test` | 0 | 500 tests passed; 11 upstream/deprecation warnings. |
| `git diff --check` | 0 | No whitespace errors. |
