# DEFINE: Bybit AI Quant

> Build a phased, auditable Bybit quantitative platform delivered as an official DeepSeek Harness Bundle.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | BYBIT_AI_QUANT |
| **Date** | 2026-11-17 |
| **Author** | SDD Define by RDD |
| **Status** | Build in progress; local Verify Gate green, production gates partial |
| **Clarity Score** | 15/15 |

---

## Problem Statement

The existing repository has useful plugin, simulation and safety scaffolding, but it does not yet meet the requested Nx + pnpm monorepo architecture or prove the official DSH installation lifecycle, complete quant data plane, operational recovery and external research audit. The project owner needs a verifiable path from the current partial implementation to a secure, autonomous Testnet quant system while Mainnet stays separately locked.

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
| **SHOULD** | Implement independently operable quant data/strategy/risk/execution modules and exercise them with deterministic tests and Testnet adapters. |
| **COULD** | Add advanced AI research/strategy evolution only after data, backtest, out-of-sample and paper/Testnet gates exist. |

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

---

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

---

## Clarifications

### Session 2026-11-17

- [x] (architecture) Is the target a true Nx + pnpm monorepo? → Yes; the supplied brief requires it, and the current root single-package layout is a design deviation; integrated into Goals, Success Criteria and the File Manifest.
- [x] (language) What language is used for handwritten code? → TypeScript; user corrected JavaScript drift; generated `dist/*.js` remains allowed.
- [x] (integration) Which trading environment may be tested unattended? → Testnet only; Mainnet funds are out of scope and Mainnet remains disabled.
- [x] (done signal) What indicates completion? → All listed acceptance evidence, bilingual READMEs, clean secret scan, and authorized release workflow; implementation gaps remain open until proved.

---

## Verify Gate

```yaml
verify_gate:
  kind: test
  cmd: "pnpm run verify"
  pass_when: "exit 0"
  threshold: "—"
  manual_fallback: "Official Plugin Manager lifecycle and installed DSH UI checks are complementary external smoke evidence; a missing DSH manager is inconclusive, never a pass."
```

---

## Out of Scope

- Mainnet trading or use of Mainnet funds in development/testing.
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
| **Deployment Location** | Nx + pnpm workspace; DSH plugin under `apps/dsh-plugin` | Root package currently owns app code and is not the required package topology. |
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
| Scope | 3 | Mainnet and speculative microservices are explicitly excluded. |
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

---

## Next Step

Execute o **SDD Design by RDD**.
