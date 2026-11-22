# BRAINSTORM: Bybit AI Quant

> Exploratory session reconstructed from the user's project brief and later explicit decisions.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BYBIT_AI_QUANT |
| **Date** | 2026-11-17 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Build a long-running, autonomous Bybit quantitative research and trading platform as a DeepSeek Harness Bundle, with AI research, deterministic strategies, independent risk controls, simulation, observability and a staged path to user-authorized live trading.

**Context Gathered:**
- The current repository is an existing TypeScript DSH plugin with modular Host/Client files, Bybit REST calls, paper trading, backtests, an AI decision journal and a dashboard.
- Current worktree contains broad uncommitted changes; preserve them. `main` points to `aae9295` and `origin` is `git@github.com:XueHua-s/dsh_bybit_plugin.git`.
- Current package declares `dsh.bundle`, a Cordis patch and TypeScript Host/Client exports. Python currently contains an Alembic migration and monitoring/data scaffolding.
- The requested project brief specifies Nx + pnpm + TypeScript and uv + Python, modular-monolith boundaries, secure autonomous quant operation and implementation phases.
- Full DSH Plugin Manager install/upgrade/uninstall verification, real WebSocket ingestion and all referenced GitHub repository audits are still unverified.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `src/`, `python/`, `docs/`, `scripts/`, `.github/` | Keep the DSH integration in TypeScript; Python quant packages remain separately managed. |
| Relevant KB Domains | DSH Bundle, Bybit V5, quantitative research, risk/security | Verify current upstream contracts and record evidence before claiming compatibility. |
| IaC Patterns | Nx/pnpm and uv workspaces; no full infrastructure deployment verified | Prefer a modular monolith and avoid claiming the independent engine is production-ready. |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Which implementation language is required for the DSH plugin? | TypeScript throughout; user corrected an earlier JS implementation. | Handwritten plugin and tooling source must be `.ts`; generated `dist/*.js` is acceptable. |
| 2 | Which trading environment may be tested autonomously? | Bybit Testnet only; the 24 USDT mentioned belongs to Mainnet and must not be used. User permits unattended Testnet tests without per-order confirmation. | Mainnet remains disabled; Testnet operations still obey account, balance, API permission and risk checks. |
| 3 | What is the desired architecture and scope? | A long-running AI quant platform inside DSH; modular monolith, Python quant engine, Nx/pnpm TS workspace and uv Python workspace per the attached brief. | Deliver in explicit phases and do not imply the full target is already implemented. |
| 4 | What references and deliverables are required? | Read and audit the listed GitHub references; provide Chinese and English README; sanitize environment/secrets; commit and push. | Audit and publication evidence are required; never publish credentials. |

**Minimum Questions:** 3 (answered from the user's brief and subsequent explicit decisions; no invented user answers)

---

## Perfil de risco

| Pergunta | Resposta |
|---|---|
| Quem pode ver? | User-owned account, market and trading records; DSH model must not receive API Secret. Open-source repo contents are public. |
| Quem pode mudar? | User owns account, strategy and risk settings; plugin may make only explicitly authorized Testnet actions within independent risk limits. Mainnet activation requires separate explicit authorization. |
| Quanto alguém pode pedir? | Limits for model calls, request volume and uploaded artifacts are not specified. Exchange actions must be constrained by configuration, balance, account identity, symbol rules and independent risk checks. |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `/Users/litlesnow/.codex/attachments/886f3b36-5cab-4ba1-bb1c-7ef525af0e6e/pasted-text-1.txt` | 1 | Product brief and architecture constraints. |
| Output examples | Repository source and tests | 1 set | Existing TypeScript/Python code is implementation evidence, not a performance ground truth. |
| Ground truth | Bybit Testnet account read results from prior session | 1 snapshot | Reported zero balance, no positions/orders and key identity as main account; no order was sent. Recheck before any future Testnet order. |
| Related code | `src/`, `python/`, `package.json`, `cordis.patch.yml` | 1 set | Current state must be re-inspected; dirty worktree is not a released build. |

**How samples will be used:**
- Translate the brief into requirements and traceability records.
- Treat source repositories, news, user strategy input and tool outputs as untrusted data.
- Use deterministic mocks/fixtures; do not claim trading performance from the Testnet snapshot.

---

## Approaches Explored

### Approach A: Phased modular monolith ⭐ Recommended

**Description:** Keep DSH Host/Client, TS exchange adapter and management surfaces in a modular TypeScript package; keep quant-domain/data/risk/execution modules in the Python uv workspace behind explicit contracts. Implement and validate in phases.

**Pros:**
- Matches the user's architecture brief and the existing repository.
- Keeps DSH lifecycle and secret resolution in the Host while long-running quant work is independently operable.
- Makes risk, backtesting, exchange integration and packaging separately testable.

**Cons:**
- Requires a real process/API contract between TypeScript and Python before claiming a functioning quant engine.
- Phased delivery means the full autonomous platform will not exist after one packaging pass.

**Why Recommended:** It preserves existing work, honors the required stack and limits coupling without creating premature microservices.

### Approach B: All-in-one Python trading application

**Description:** Put the DSH integration, quant engine and exchange execution in one Python service.

**Pros:**
- Python ecosystem fits many quant libraries.

**Cons:**
- Conflicts with the explicit TypeScript DSH integration requirement and current TS plugin.
- Blurs Host lifecycle, user interface, model tools and exchange-risk boundaries.

### Approach C: Microservice fleet

**Description:** Split research, AI agents, data, risk, execution and dashboard into separately deployed services.

**Pros:**
- Independent scaling and deployment boundaries.

**Cons:**
- Unjustified operational and consistency complexity for the current project stage.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-11-17; directly specified modular monolith and Nx/pnpm/TypeScript plus uv/Python in supplied brief; later corrected the implementation to TypeScript. |
| **Reasoning** | Matches explicit architecture constraints and existing source; enables staged verification. |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Handwritten plugin code and scripts are TypeScript; JS under `dist/` is generated. | User explicitly corrected language drift. | New hand-authored JS files. |
| 2 | Mainnet is disabled and the 24 USDT Mainnet funds are out of scope. | User clarified the funds belong to production and authorized only Testnet. | Using Mainnet funds or enabling live trading. |
| 3 | A Testnet unattended test does not bypass code-side safety checks. | Current account evidence showed zero Testnet balance and a main-account key; no order was sent. | Disabling account/equity risk checks to force an order. |
| 4 | Use official DSH Bundle/plugin lifecycle and do not edit managed Harness profiles manually. | Explicit packaging requirement. | Editing managed profile package/patch files by hand. |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Microservices in the initial phase | Explicitly premature for this project; modular monolith is required. | Yes, with measured deployment/scaling evidence. |
| Mainnet order testing | Explicitly outside current authorization and 24 USDT is production capital. | Only after a separate explicit Mainnet authorization and production readiness review. |
| Claiming full institutional quant capability now | No evidence that the Python engine, multi-agent research, WebSocket adapter or portfolio stack is complete. | Yes, as phases are implemented and verified. |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Language and plugin composition | ✅ | User corrected JS drift; all handwritten code must be TypeScript. | Yes |
| Test environment and funds | ✅ | User clarified Testnet is authorized and the 24 USDT is Mainnet. | Yes |

**Minimum Validations:** 2 (historical user corrections/clarifications)

---

## Suggested Requirements for /define

### Problem Statement (Draft)
The repository has a partial DSH-integrated Bybit quant implementation, but its packaging, trading safety, operational reliability, research provenance and release evidence are not yet verified end to end, making autonomous use unsafe to claim.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Open-source project owner/operator | Needs an auditable, maintainable DSH plugin that can research and test strategies without exposing credentials or risking unauthorized Mainnet trades. |

### Success Criteria (Draft)
- [ ] Every handwritten plugin/tooling source file is TypeScript and no file exceeds 500 lines.
- [ ] Bundle metadata, patch, Host/Client entries and lifecycle match the installed DSH release, and official install/upgrade/uninstall flow is evidenced.
- [ ] Mainnet trading remains disabled; Testnet order paths cannot bypass identity, balance, symbol or risk guards.
- [ ] Required checks produce recorded exit results; failures remain explicit.
- [ ] GitHub repository audit records reviewed source refs, license, architecture, security and adaptation decision for each requested project.
- [ ] English and Chinese READMEs agree with implemented capabilities and reveal no credentials.

### Constraints Identified
- TypeScript for handwritten plugin and script source; generated JS bundles are allowed.
- Use Nx/pnpm and Python uv workspace; stay modular monolith initially.
- Official DSH Bundle/plugin manager lifecycle; no manual edits to managed Harness profile files.
- Mainnet trading is disabled; Testnet only under existing guardrails.
- Migrations, verified backup/restore, isolation for generated algorithms, operational monitoring, graceful shutdown/recovery, SBOM and dependency scanning are required.
- Never publish API keys, secrets, OAuth tokens or credential-bearing environment files.

### Out of Scope (Confirmed)
- Mainnet trading and use of the Mainnet 24 USDT balance in this task.
- Claims of positive strategy returns or a production-ready autonomous quant company without corresponding implementation/evidence.
- Replacing the modular monolith with microservices before operational need is demonstrated.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 (answers extracted from supplied brief and explicit follow-up decisions) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 3 |
| Validations Completed | 2 |
| Duration | Reconstructed from the current session |

---

## Next Step

**Ready for:** a skill `sdd-define`, com este documento.
