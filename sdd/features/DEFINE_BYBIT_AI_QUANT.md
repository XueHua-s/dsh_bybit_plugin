# DEFINE: Bybit AI Quant

> Build a phased, auditable Bybit quantitative platform delivered as an official DeepSeek Harness Bundle.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | BYBIT_AI_QUANT |
| **Date** | 2026-11-17 |
| **Author** | SDD Define by RDD |
| **Status** | Requirements restored from original brief; implementation and acceptance coverage incomplete |
| **Clarity Score** | 15/15 |

---

## Problem Statement

The existing repository has useful plugin, simulation and safety scaffolding, but it does not yet implement the original complete quant architecture: the workspace now has separated projects, but an independently running FastAPI engine, generated cross-language client, Nautilus-only execution, data consumption, portfolio/risk pipeline and AI research lifecycle remain incomplete. The project owner needs a verifiable path from the current partial implementation to a secure, autonomous Testnet quant system while Mainnet stays separately locked.

---

## Target Users

| User | Role | Pain Point |
|---|---|---|
| Open-source project owner/operator | Maintains the plugin and authorizes account boundaries | Cannot safely rely on claims about installation, algorithms or trading until the implementation, dependencies and tests are auditable. |
| DSH user | Installs and configures a Bybit quant plugin | Needs stable lifecycle, clear account/environment state, recoverable configuration/history and safe automated operation. |

---

## Goals

| Priority | Goal |
|---|---|
| **MUST** | Restructure as a discoverable Nx + pnpm monorepo with `apps/dsh-plugin`, reusable TS packages only where justified, and Python apps/packages under `python/`; keep root configuration as workspace orchestration. |
| **MUST** | Use TypeScript for all handwritten plugin and tooling code, ESM/strict types, and keep every handwritten source file at or below 500 lines. |
| **MUST** | Match current DSH Bundle metadata, Cordis patch, Host/Client entries, dependency injection, configuration and lifecycle; prove official install, upgrade and uninstall without hand-editing managed Harness profile files. |
| **MUST** | Keep Mainnet trading disabled; permit Testnet-only unattended testing within account identity, available balance, instrument, idempotency and independent risk guards. |
| **MUST** | Protect credentials and user state; migrate persistent data with Alembic; provide backup/restore; isolate generated algorithms; treat external text/code as untrusted. |
| **MUST** | Provide real monitoring, graceful shutdown/recovery, SBOM and dependency vulnerability scanning; keep evidence for all checks and document actual capabilities in English and Chinese. |
| **MUST** | Deliver the original numbered brief §§1–26 in dependency-ordered phases. Phasing does not demote mandatory product capabilities to optional scope; original conditional/optional items remain conditional/optional. |
| **MUST** | Run a Python modular-monolith quant engine independently of DSH conversations and Tool invocations, with FastAPI/Pydantic as the single `/api/v1` schema source and generated OpenAPI TypeScript client. |
| **MUST** | Consume validated live market and account data into features, regime detection, validated strategy selection, target portfolio calculation, independent deterministic risk and a persistent audit ledger. Detect stale/missing/inconsistent data and protect trading. |
| **MUST** | Use NautilusTrader as the sole exchange order execution authority and final event-driven backtest validator; remove the parallel direct TypeScript exchange-order path before trading acceptance. Distinguish Backtest, Internal Paper, Demo, Testnet and separately authorized Mainnet. |
| **MUST** | Implement the original strategy registry metadata/lifecycle and required strategy families, dynamic selector with cooldown/hysteresis/cost/OOS scoring, portfolio weights and safe position transition. Not every strategy must enter live trading in the initial phase. |
| **MUST** | Implement the original multi-role AI research team with structured decisions, provenance/expiry and no secret or execution access; implement isolated hypothesis/experiment/OOS/walk-forward/paper/review/approved-registry research progression and version rollback. |
| **MUST** | Deliver required Bybit public/private recovery and reconciliation, all specified deterministic risk controls and emergency stop, faithful cost/validation/performance accounting, plugin Tools/Skills and DSH Dashboard, persistence, observability, tests and CI described in original §§11–22. |
| **MUST** | Implement bounded learning/evolution of approved strategy weights/parameters, periodic degradation review and reproducible model/data/parameter versions; new algorithms/models and increased risk limits require the original validation and authorization gates (§23). |
| **MUST** | Complete source-level audits of every original upstream reference; resolve incompatibility/license conflicts explicitly. A shallow audit or a convenience-based decision to omit mandatory NautilusTrader does not satisfy §6. |
| **MUST** | Keep the DSH dashboard view-only for market analytics, simulated P&L, decisions and operational state. Symbol/market/timeframe filters change only displayed data; they never select or parameterize a trade. The AI chooses whether to act and selects eligible instruments and decision parameters within configured risk and environment limits. |

---

## Success Criteria

- [ ] `nx show projects` discovers separate app/package projects, and `nx graph` shows real dependency edges rather than a single root application.
- [ ] All handwritten `.ts` source files are at most 500 lines; build and strict TypeScript checks pass.
- [ ] Bundle checks prove `dsh.bundle`, `cordis.patch.yml`, Host and Client entry points, and packaged resources are internally consistent.
- [ ] The installed DSH version's official Plugin Manager completes install, upgrade and uninstall in an isolated test profile; managed profile files are never edited manually.
- [ ] Mainnet trading is false by default and a test proves denied trading cannot reach the Mainnet order endpoint.
- [ ] Testnet safety tests reject wrong account identity, zero/insufficient equity, invalid instrument constraints, duplicate order submission and risk-limit violations.
- [ ] Alembic upgrade tests pass; backup and restore round-trip preserves user configuration, strategy settings, trade history and audit data.
- [ ] Prompt-injection fixtures are treated as inert data and generated algorithms only execute in an isolated runtime with bounded resources.
- [ ] Monitoring exposes queue backlog, process memory/CPU, WebSocket state/reconnects and API/order latency; shutdown and restart recovery checks pass.
- [ ] TypeScript and Python SBOMs are generated; dependency audit and secret scan report no unhandled high/critical issue or credential leak.
- [ ] Every GitHub reference in the project brief has a recorded commit, license, architecture, dependency/security review and explicit reuse/adaptation decision.
- [ ] English and Chinese READMEs match the verified feature set, include safe setup instructions and contain no credentials.
- [ ] Dashboard symbol/market/timeframe changes affect only the displayed market snapshot; candidate eligibility, AI decisions and simulated book state remain unchanged.
- [ ] AI decision cycles may abstain or choose eligible instruments and their decision parameters from the analysis evidence; dashboard selections are never decision inputs.

---

The following criteria remain **unchecked**: engine runs independently with a process/API integration test; a public stream is actually consumed and persisted; generated SDK matches Python OpenAPI; all exchange orders traverse Nautilus and independent risk; full strategy/regime/portfolio/backtest/AI/research/evolution acceptance in the original brief is evidenced. Detailed section-by-section coverage and gaps: [original scope audit](../reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md). Existing AT-001–009 alone do not cover the product.

## Acceptance Tests

| ID | Pattern | Criterion (EARS) | Gate (`kind`) |
|---|---|---|---|
| AT-001 | Event-driven | **When** Nx loads the workspace, the workspace **shall** expose independent DSH plugin, quant engine and data/domain package projects with their dependency edges. | test |
| AT-002 | Ubiquitous | The project **shall** keep each handwritten TypeScript source file at or below 500 lines and **shall** typecheck in strict mode. | typecheck |
| AT-003 | Event-driven | **When** the official DSH Plugin Manager installs, upgrades or uninstalls the Bundle in a disposable profile, the plugin **shall** register and clean up its resources while preserving user-owned credentials, settings and history. | smoke |
| AT-004 | Unwanted | **If** a live order is attempted while Mainnet is disabled or account/risk checks fail, **then** the system **shall** reject it before sending any exchange order request. | test |
| AT-005 | State-driven | **While** the service is running, the system **shall** report market queue backlog, CPU, memory, WebSocket reconnect state and order/API latency through health/metrics output. | test |
| AT-006 | Event-driven | **When** a backup is restored into an isolated test database, the system **shall** preserve the configured user state, strategy configuration, trade history and append-only audit trail. | test |
| AT-007 | Unwanted | **If** an external article, repository, file or agent output contains instructions, **then** the system **shall** treat them as untrusted content and shall not interpret them as authorization or execute them in-process. | test |
| AT-008 | Event-driven | **When** the project release checks run, the system **shall** produce TypeScript and Python SBOMs and complete dependency and secret scans with recorded results. | test |
| AT-009 | Event-driven | **When** a reader follows either README, the documentation **shall** describe only verified behavior and shall not contain credentials or environment-specific secrets. | smoke |

| AT-010 | Event-driven | **When** the Python engine is started without DSH, it **shall** serve authenticated loopback `/api/v1/health` and complete bounded shutdown independently of a Tool lifecycle. | test |
| AT-011 | Event-driven | **When** market events arrive for selected discovered instruments, the engine **shall** consume them into timestamped state and persistent provenance rather than only queue them. | test |
| AT-012 | Unwanted | **If** market/account/order state is stale, missing or inconsistent, **then** the engine **shall** refuse new exposure and record the protection reason. | test |
| AT-013 | Ubiquitous | The TypeScript engine client **shall** be generated from FastAPI/Pydantic OpenAPI and **shall** fail a drift check when generated artifacts differ. | test |
| AT-014 | Event-driven | **When** an authorized order intent passes independent risk, the engine **shall** submit it exclusively through NautilusTrader with a persistent unique client order ID. | test |
| AT-015 | Unwanted | **If** submission outcome is uncertain, **then** the execution authority **shall** reconcile exchange order status before deciding whether a retry is safe. | test |
| AT-016 | Event-driven | **When** an environment is selected, the system **shall** isolate Backtest, Internal Paper, Demo, Testnet or separately authorized Mainnet configuration, credentials and ledgers. | test |
| AT-017 | Event-driven | **When** a strategy is registered, the registry **shall** validate all §7 metadata, configuration, lifecycle and validation-status fields. | test |
| AT-018 | Event-driven | **When** required §7 strategy-family fixtures execute, the strategies **shall** emit reproducible signals and target exposure through the common lifecycle without exchange access. | test |
| AT-019 | Event-driven | **When** market regime changes, the selector **shall** record a validated strategy choice based on stability, OOS results, costs, confidence, cooldown and hysteresis. | test |
| AT-020 | Event-driven | **When** selected strategies propose exposure, portfolio calculation **shall** produce auditable aggregate target weights and a safe transition plan. | test |
| AT-021 | Unwanted | **If** any required §13 limit fails, **then** independent deterministic risk **shall** veto the intent with a recorded reason that an Agent cannot bypass. | test |
| AT-022 | Event-driven | **When** emergency stop is invoked, the system **shall** freeze scheduling/new orders and reconcile cancellation while closing positions only under separate confirmation or explicit preauthorization. | test |
| AT-023 | Event-driven | **When** the §9 research roles analyze a selected instrument, the team **shall** deliver schema-validated, expiring, timestamped decisions with role evidence and no credential access. | test |
| AT-024 | Event-driven | **When** a candidate algorithm is proposed, research **shall** retain hypothesis, source/license, code/model/data versions, isolated experiment, backtest, OOS, walk-forward, paper and review results before eligible promotion. | test |
| AT-025 | Unwanted | **If** candidate validation or required approval is missing, **then** the registry **shall** deny deployment and preserve the prior approved version for rollback. | test |
| AT-026 | Event-driven | **When** candidate strategies are compared, validation **shall** use common data/cost assumptions, §15 applicable costs/metrics and bias checks, with final Nautilus event-driven validation. | test |
| AT-027 | Event-driven | **When** required §17 Tools and Skills are loaded, the DSH plugin **shall** expose their strictly validated and permission-checked operations through supported DSH interfaces. | smoke |
| AT-028 | Event-driven | **When** the user opens the DSH Dashboard, it **shall** provide §18 Overview, Instruments, AI Research, Strategy, Trading, Risk and Settings views from actual engine state without displaying secrets. | smoke |
| AT-029 | Event-driven | **When** §19 domain state changes, persistence **shall** retain the specified metadata, versions, results, decisions, targets, orders, executions, positions, snapshots and append-only risk/audit records. | test |
| AT-030 | Event-driven | **When** scheduled performance review detects degradation, learning **shall** record a bounded approved weight/parameter adjustment or candidate experiment with versioned rollback and unchanged user risk ceilings. | test |
| AT-031 | Event-driven | **When** release validation runs, CI **shall** verify the complete §21–22 TS/Python/quant/exchange/schema/SDK/security matrix and record unavailable external gates as incomplete. | test |
| AT-032 | Event-driven | **When** dashboard symbol, market or timeframe filters change, **then** only the displayed market snapshot **shall** change; the eligible candidate universe, decision journal and simulated portfolio **shall** remain unchanged. | test |
| AT-033 | Event-driven | **When** the AI evaluates its eligible candidate universe, it **shall** choose zero or more eligible instruments and determine each simulated decision's action, sizing and exit parameters from evidence, or abstain; dashboard filters **shall not** supply those values. | test |
| AT-034 | Event-driven | **When** an AI research cycle starts without a user allow-list, the plugin **shall** discover all pages of the selected Bybit Spot or USDT-linear instrument catalogue, join a current ticker snapshot, and give the AI a bounded, deterministic candidate set containing only Trading instruments with valid quantity/price rules and configured liquidity/spread eligibility. | test |
| AT-035 | Unwanted | **If** instrument or ticker discovery fails, returns incomplete data, or yields no eligible candidate, **then** the AI tools **shall** fail closed without using static BTC/ETH defaults; a new directional decision **shall** be limited to the fresh eligible set, while an existing simulated position may only be selected outside it for an explicit flat decision. | test |
| AT-036 | Event-driven | **When** the AI requests detailed evidence for symbols selected from the current fresh candidate universe, `quant_brief` **shall** attach bounded Python strategy-family results from the already fetched primary-timeframe bars as research-only evidence; unavailable or invalid engine responses **shall** be explicit, and no result **shall** select a symbol, approve deployment, prescribe portfolio exposure, bypass code-owned risk, or authorize an exchange action. | test |

**Coverage status (2026-11-17):** AT-010–031 describe restored required acceptance; they are not claims of existing passing tests. The original brief remains the detailed coverage baseline, including its conditional requirements. The current `pnpm run verify` covers a subset of the plugin only and cannot certify these rows.

---

## Clarifications

### Session 2026-11-17

- [x] (architecture) Is the target a true Nx + pnpm monorepo? → Yes; the supplied brief requires it, and the current root single-package layout is a design deviation; integrated into Goals, Success Criteria and the File Manifest.
- [x] (language) What language is used for handwritten code? → TypeScript; user corrected JavaScript drift; generated `dist/*.js` remains allowed.
- [x] (integration) Which trading environment may be tested unattended? → Testnet only; Mainnet funds are out of scope and Mainnet remains disabled.
- [x] (scope drift correction) The original brief requires the independent engine, Nautilus authority, quant pipeline, AI team, research and evolution. Their prior SHOULD/COULD classification had no user authorization; restored to MUST with incomplete coverage. This corrects documentation drift and adds no new product scope.
- [x] (done signal) What indicates completion? → All listed acceptance evidence, bilingual READMEs, clean secret scan, and authorized release workflow; implementation gaps remain open until proved.

### Session 2026-11-19

- [x] (dashboard/decision boundary) Which values may dashboard controls affect? → Market symbol, category and timeframe controls are display-only. The AI decides whether to trade, which eligible instrument to select, and its decision parameters; risk, account, environment and authorization limits remain code-owned. The Bundle now has a default-off, simulation-only background Agent cycle for Testnet/internal-paper; it still has no exchange execution authority and does not claim a complete unattended trader.
- [x] (dynamic instrument choice) Does the chart symbol or a static starter list choose what the AI evaluates? → No. The AI receives a fresh, bounded candidate set derived from the selected Bybit category's full Instrument Info catalogue and ticker data, then selects instruments for detailed analysis or abstains. A non-empty configured/user allow-list may only narrow discovery; empty means dynamic discovery. Discovery failure has no static-symbol fallback.

---

## Verify Gate

```yaml
verify_gate:
  kind: test
  cmd: "pnpm run verify"
  pass_when: "exit 0"
  threshold: "—"
  manual_fallback: "Current command is a local plugin regression gate only. Product acceptance also requires AT-010–031 and original brief coverage evidence; missing engine/SDK/Nautilus/AI or external DSH evidence is incomplete, never a pass."
```

---

## Out of Scope

- Mainnet trading execution or use of Mainnet funds in current development/testing. Separately authorized Mainnet capability remains mandatory final product scope; no Mainnet authorization is implied.
- Claims of profitability, autonomous investment competence or production readiness without reproducible evidence.
- Microservices before a measured operational need exists.
- Automatically importing and executing unreviewed third-party GitHub algorithms.

---

## Constraints

| Type | Constraint | Impact |
|---|---|---|
| Technical | Nx + pnpm monorepo; TypeScript DSH Host/Client; uv-managed Python 3.12+ modules. | Workspace boundaries and cross-language contracts must be explicit and graphable. |
| Technical | No handwritten TS file above 500 lines; follow installed `software-design-philosophy`. | Modules must hide decisions behind simple, stable interfaces. |
| Security | No secret in Git/logs/model context; all external inputs are untrusted. | Secret storage and prompt-injection tests are release gates. |
| Trading | Mainnet disabled; Testnet operations remain subject to all code-side guards. | No safety bypass to force a Testnet order. |
| Integration | Official DSH Bundle/Plugin Manager contract is version-specific. | Verify installed/upstream release before install/upgrade claims. |
| Operational | Alembic migrations, backup/restore, isolation, monitoring and recovery required. | Scaffolds or placeholder metrics do not count as complete. |

---

## Technical Context

| Aspect | Value | Notes |
|---|---|---|
| **Deployment Location** | Nx + pnpm workspace; DSH plugin under `apps/dsh-plugin` | Separated app/package manifests now exist; actual graph and each acceptance gate still require recorded verification. |
| **KB Domains** | DSH Bundle, Bybit V5, quantitative research, security, Python packaging | Record upstream versions and source refs. |
| **IaC Impact** | Modify workspace and CI; no production deployment requested | Test profile only for Plugin Manager verification. |
| **LLM Prompts** | true | AI research and agent decisions consume untrusted market/news/repository/user content. |
| **Segurança** | 6 applied requirements (secrets, input trust, sandbox, risk guards, Mainnet lock, state preservation) · 0 refused · 0 deferred | Derived from the user's explicit security constraints; catalog checklist still required before release. |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|---|---|---|---|
| A-001 | The user's local DSH version can be inspected or reproduced in a disposable profile. | Plugin Manager lifecycle evidence remains blocked. | No |
| A-002 | Testnet has no funded balance currently; prior read reported zero equity and no positions/orders. | End-to-end order lifecycle cannot pass until account state changes; no guard bypass is allowed. | Prior snapshot only; recheck at execution |
| A-003 | Nx project boundaries may be smaller than the full aspirational package list until a real module exists. | Creating empty package shells would increase complexity without functionality. | Yes, per modular-monolith brief |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---|---:|---|
| Problem | 3 | Partial existing implementation and measurable target gaps are identified. |
| Users | 3 | Owner/operator and DSH user are explicit. |
| Goals | 3 | Priorities and trading boundary are explicit. |
| Success | 3 | Workspace, test, safety, migration, monitoring and release signals are observable. |
| Scope | 3 | Original product scope restored; current Mainnet execution remains unauthorized, while final capability is conditional on explicit authorization. |
| **Total** | **15/15** | |

Minimum to proceed: **12/15**.

---

## Open Questions

None - ready for Design.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-11-17 | SDD Define by RDD | Initial requirements from the project brief and explicit follow-up decisions. |
| 1.1 | 2026-11-17 | Original scope audit | Restored mandatory original engine, data, Nautilus, quant/AI/research/evolution scope; added AT-010–031 and explicit incomplete gate coverage; corrected stale topology statement. |
| 1.2 | 2026-11-19 | User clarification | Added view-only dashboard boundary and AT-032–033 separating display filters from AI candidate selection and decision parameters. |

---

## Next Step

Execute o **SDD Design by RDD**.
