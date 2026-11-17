# DESIGN: Bybit AI Quant

> Technical design for the phased Nx + pnpm monorepo and official DSH Bundle.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | BYBIT_AI_QUANT |
| **Date** | 2026-11-17 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **UX REVIEW** | N/A; existing DSH panel is retained and verified separately |
| **LLM Prompts** | true |
| **Status** | Build in progress; local worker supervision is verified, while process/order recovery and reconciliation remain open |

---

## Architecture Overview

```text
                         DeepSeek Harness
                               │
                    official Plugin Manager
                               │
                 apps/dsh-plugin (DSH Bundle)
             ┌──────────────┬──────────────┐
             │ Host runtime │ Client panel │
             │ tools/config │ slots/locale│
             └──────┬───────┴──────────────┘
                    │ explicit typed contracts
         packages/ts/quant-contracts + quant-api-client
                    │ localhost/OpenAPI boundary
          python/apps/quant-engine (long-running data plane)
              ┌─────┼─────────┬─────────┐
              │data │research │risk     │execution
              └─────┴─────────┴─────────┘
                    │
             PostgreSQL + Parquet/DuckDB
                    │
          Alembic migrations + backup/restore
```

The DSH plugin owns lifecycle, credentials, tools and UI. The Python data plane owns durable quant work and can shut down/recover independently. A narrow typed contract prevents exchange protocol, database schema and model prompt details from leaking into every caller.

#### Build decision: quant-contracts package scope

The first reusable package owns only the normalized market DTOs already used by the plugin: `Category`, `Candle`, `Ticker`, and `Instrument`. These describe stable concepts that cross Host/client and future engine boundaries; venue parsing, credentials, request inputs and account/order records remain in the Bybit adapter because sharing them now would couple the reusable API to transport or plugin concerns. The plugin's existing `bybit-types.ts` re-exports the shared market types so current internal import paths remain stable. The package emits ESM plus declarations, and Nx builds dependencies before the plugin so the app resolves its workspace export deterministically.

This package boundary scores **9/10** against the software-design diagnostic: the package owns a coherent contract, callers get a small type-only API, provider parsing stays hidden, and the boundary has compile-time negative cases. The remaining diagnostic is cross-boundary consumer coverage beyond the DSH plugin; the Python engine has no TypeScript consumer today, so connecting it now would invent a transport implementation rather than validate this contract. Revisit when that real consumer is implemented.

---

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| `apps/dsh-plugin` Host | Register tools, services, prompt section and lifecycle effects | TypeScript ESM, deep runtime facade | DSH context/config/credentials | Tool results, health route, cleanup | `packages/ts/quant-contracts` |
| `apps/dsh-plugin` Client | DSH slot UI and locale resources | TypeScript UI factory; no secrets | Host JSON snapshot | Dashboard view/actions | DSH client slots/locale |
| `packages/ts/quant-contracts` | Stable domain and API types | TypeScript schemas/interfaces | DTO definitions | Shared types | none |
| `packages/ts/quant-api-client` | Hide HTTP/Bybit transport and retry details | Typed adapter with bounded retry | Contract requests | Domain responses/metrics | contracts |
| `python/apps/quant-engine` | Long-running market/research/risk loop | uv project, FastAPI service, `quant_engine.market_data`, `quant_engine.supervisor` | Public Bybit Testnet ticker stream | normalized ticker events and typed lifecycle/health snapshot | `websockets`, Python packages |
| `python/packages/quant-data` | Durable models and migration boundary | SQLAlchemy + Alembic | snapshots/orders/audit | queries and migrations | PostgreSQL/SQLite dev |
| `python/packages/quant-risk` | Independent final veto | Pure deterministic functions | target/order/account state | allow/deny + reason | domain types |
| `python/packages/quant-sandbox` | Execute generated algorithms out of process | Docker/OS resource limits | reviewed source + fixture data | bounded result | Docker runtime |
| `apps/dsh-plugin/src/lib/trust.ts` evidence boundary | Normalize agent-provided free text and expose it only as a bounded, explicitly untrusted data envelope in model-visible tool results | TypeScript deep module; no regex denylist | `thesis` / `invalidation` strings | `{ source: 'agent', trusted: false, text }` | AI decision tools; code-owned risk gate remains independent |
| `scripts/check-bundle.ts` | Static package/patch/entry validation | TypeScript CLI | package manifest | exit 0/diagnostics | package files |
| `scripts/backup.ts` + `src/lib/backup.ts` | Snapshot/restore user state | SHA-256 manifest and atomic writes | state DB/files | verified restore | local storage |

### Software design philosophy review

Historical integrated control/data boundary score: **5/10**, as scoped in `sdd/reports/ORIGINAL_SCOPE_AUDIT_2026-11-17.md`; the accepted independent read-only service slice separately scores **10/10** in its review. The Nx migration is complete: root owns orchestration and plugin source lives in `apps/dsh-plugin`. The later generated SDK and demand-driven DSH integration now hide schema/transport/validation from Host tools; the native foundation hides BacktestEngine callbacks behind a finite interface. The original 5/10 assessment remains a historical control/data-boundary snapshot, not a fresh repository score. Remaining integrated work is converging exchange execution/risk on the required single authority; independently accepted slice scores do not certify the whole platform. A service-local score does not certify these broader missing connections.

---

## Key Decisions

### Decision 1: True Nx + pnpm workspace boundaries

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-17 |
| **Source** | User clarification and supplied architecture brief |

**Context at decision time (historical):** The original root package had Nx config but was not a discoverable multi-project monorepo. The subsequent migration created four discoverable projects and actual plugin → contracts / engine → data edges.

**Choice:** Move DSH code into `apps/dsh-plugin`, introduce only packages with real shared contracts, and retain `python/` as a uv workspace with `apps/` and `packages/` boundaries as modules become real.

**Rationale:** It satisfies the explicit architecture while avoiding empty package shells and classitis.

**Alternatives Rejected:**
1. Keep all code at root — fails the stated monorepo boundary.
2. Create empty packages for every future capability — adds speculative complexity.

**Consequences:** Package import paths and CI commands must be updated; migration is incremental and requires lockfile/build verification.

### Decision 2: Official DSH lifecycle only

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-17 |
| **Source** | User requirement and current DSH Bundle constraints |

**Context:** A Bundle must declare metadata and patch but Harness-managed profile files must not be edited manually.

**Choice:** Validate package metadata and patch in the repository, then use the installed official Plugin Manager `install_bundle`/upgrade/uninstall command when available. If unavailable, record the exact external blocker rather than simulating success.

**Rationale:** It preserves Harness ownership of managed state and makes lifecycle evidence reproducible.

**Alternatives Rejected:** Directly editing profile `package.json` or `cordis.patch.yml` — violates the requirement and can corrupt other plugins.

**Consequences:** A real DSH installation profile is required for the final smoke gate.

### Decision 3: Safety-first Testnet boundary

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-17 |
| **Source** | User authorization and prior read-only Testnet evidence |

**Context:** Testnet is authorized, but the current key was reported as main-account identity with zero equity.

**Choice:** Keep `allowLiveTrading: false`, require Testnet environment and all identity/equity/instrument/risk checks, and never bypass a failed guard to force an order.

**Rationale:** Testnet has no real funds but a mistaken endpoint, credential or guard can still create unsafe behavior and hide production bugs.

**Alternatives Rejected:** Disabling main-account/zero-equity checks or using Mainnet credentials — outside authorization and unsafe.

**Consequences:** Order lifecycle remains blocked until a valid funded Testnet account passes checks; paper/mocked lifecycle covers the meantime.

### Decision 4: State preservation on upgrade

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-17 |
| **Source** | User requirement |

**Context:** Plugin upgrades must not overwrite credentials, strategy configuration or trading history.

**Choice:** Keep credentials in Harness credential storage, version durable state with Alembic, back up before migration, restore atomically on failure, and test an upgrade against a disposable profile.

**Rationale:** Code/package replacement and user-owned state have different lifecycles.

**Alternatives Rejected:** Replacing the entire profile directory — would risk destructive overwrite.

**Consequences:** Upgrade runner needs explicit pre/post snapshots and migration evidence.

---

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `AGENTS.md` | Create | Repository rules for SDD, TypeScript, 500-line limit and design philosophy | general | none |
| 2 | `package.json` | Modify | Root workspace orchestration and safe scripts | general | 3,4 |
| 3 | `apps/dsh-plugin/package.json` | Create | Official Bundle package metadata and exports | general | 5-8 |
| 4 | `pnpm-workspace.yaml` | Modify | Discover apps and real TS packages | general | 3 |
| 5 | `apps/dsh-plugin/src/index.ts` | Move/Modify | Host entry and exports | general | 6 |
| 6 | `apps/dsh-plugin/src/client.ts` | Move/Modify | Client entry and UI factory | general | 5 |
| 7 | `apps/dsh-plugin/src/lib/*` | Move/Modify | Deep adapters, state, risk and monitor modules | general | 5,8 |
| 8 | `apps/dsh-plugin/cordis.patch.yml` | Move/Modify | Bundle patch and Testnet-safe defaults | general | 3,5 |
| 9 | `packages/ts/quant-contracts/*` | Create | Shared typed contract only when used by both sides | general | 5,10 |
| 10 | `python/apps/quant-engine/*` | Create/Move | Long-running quant service boundary | general | 9,11 |
| 11 | `python/packages/quant-data/*` | Create/Move | Alembic/data domain boundary | general | 10 |
| 12 | `python/packages/quant-risk/*` | Create | Independent deterministic risk boundary | general | 10 |
| 13 | `scripts/check-bundle.ts` | Modify | Static bundle contract checks | general | 3,8 |
| 14 | `scripts/plugin-manager-smoke.ts` | Create | Detect and run official lifecycle in disposable profile | general | DSH installation |
| 15 | `docs/research/github-repository-audit.md` | Create | Source/license/dependency/security audit of every requested reference | general | network/read-only sources |
| 16 | `docs/architecture/monorepo.md` | Create | Project graph and ownership boundaries | general | 2-12 |
| 17 | `sdd/reports/BUILD_REPORT_BYBIT_AI_QUANT.md` | Create | Evidence for Build gate | general | manifest checks |
| 18 | `README.md` and `README.zh-CN.md` | Modify | Verified bilingual behavior and safe setup | general | all verified features |
| 19 | `python/apps/quant-engine/src/quant_engine/market_data.py` | Create | Public Testnet ticker adapter with typed parsing, bounded queue, reconnect and health boundary | market-data increment | 10 |
| 20 | `python/apps/quant-engine/tests/test_market_data.py` | Create | Deterministic fake-WebSocket coverage for subscription, parsing, backpressure, reconnect and close | market-data increment | 19 |
| 21 | `python/apps/quant-engine/pyproject.toml` and `python/uv.lock` | Modify | Pin the `websockets` runtime dependency in the uv workspace | market-data increment | 19 |
| 22 | `python/packages/quant-data/src/quant_data/migrations.py` | Create | Own explicit SQLite target selection, verified backup, candidate upgrade and atomic replacement | migration protection increment | 11 |
| 23 | `python/packages/quant-data/alembic/versions/0002_strategy_config.py`, `0001_initial.py` | Modify/Create | Prove state-preserving schema evolution and refuse destructive downgrade with user rows | migration protection increment | 22 |
| 24 | `python/packages/quant-data/tests/test_migrations.py` | Modify | Fixture-backed upgrade, backup, failure and downgrade regression | migration protection increment | 22,23 |
| 25 | `sdd/reports/ADR_MIGRATION_BACKUP.md` | Create | Record the database safety boundary and SQLite-only scope | migration protection increment | 22 |
| 26 | `apps/dsh-plugin/test/trust.ts` | Create | Prove bounded provenance envelopes and risk-gate independence for agent-provided prose | gpt-6.1-sol | 7 |
| 27 | `apps/dsh-plugin/test/integration.ts` | Modify | Assert quant_decide and quant_review expose decision prose as untrusted evidence envelopes | gpt-6.1-sol | 26 |
| 28 | `python/apps/quant-engine/src/quant_engine/supervisor.py`, `tests/test_supervisor.py` | Create | Bounded, cancellation-safe in-process worker lifecycle | supervisor increment | 19 |
| 29 | `python/apps/quant-engine/tests/test_market_data_validation.py` | Create | Hostile wire values, timestamp bounds, lifecycle and parser regressions | transport hardening | 19 |
| 30 | `python/apps/quant-engine/src/quant_engine/service.py`, `api.py`, `monitoring.py`, `bootstrap.py` | Create | Independent lifecycle, consumer, schema/HTTP, metrics and CLI ownership | engine service | 19,28 |
| 31 | `python/apps/quant-engine/tests/test_service.py` | Create | Actual adapter/consumer/supervisor + ASGI lifespan integration | engine service | 30 |
| 32 | `contracts/openapi/quant-engine.v1.json`, `docs/runbooks/engine-service.md` | Create | Python-generated read-only contract and operational setup | engine service | 30 |
| 33 | `python/apps/quant-engine/project.json`, `pyproject.toml`, `python/pyproject.toml`, `python/uv.lock` | Modify | CLI, serve/schema tasks and locked service/test dependencies | engine service | 30 |
| 34 | `packages/ts/quant-api-client/*`, `sdd/features/DESIGN_ENGINE_CLIENT.md` | Create | OpenAPI-generated paths/runtime schema, bounded loopback transport, Ajv boundary and Vitest | SDK slice | 32 |
| 35 | `apps/dsh-plugin/src/lib/engine.ts`, `host-tools-engine.ts`, `client-engine.ts`, `test/engine.ts`, `sdd/features/DESIGN_DSH_ENGINE.md` | Create | Demand-driven validated engine tools/card and authenticated bridge | DSH engine slice | 34 |
| 36 | `apps/dsh-plugin/package.json`, `tsdown.config.ts`, `scripts/check-bundle.ts`, `scripts/sbom.ts`, `scripts/pnpm-environment.ts` | Modify/Create | Inline private SDK runtime, verify packed closure, recursive version-correct SBOM | DSH engine slice | 34,35 |
| 37 | `python/packages/quant-execution/*`, `sdd/features/DESIGN_NAUTILUS_EXECUTION.md`, `docs/adr/nautilus-execution.md` | Create/Modify | Real native stable 1.231.0 offline fill/cancel/partial fixtures and compatibility evidence | native slice | 10 |
| 38 | `.githooks/*`, `scripts/git-hooks.ts`, `scripts/test-git-hooks.ts`, `scripts/tsconfig.json`, `sdd/features/DESIGN_GIT_HOOKS.md`, `.github/workflows/ci.yml` | Create/Modify | Sensitive staged-path guards, redacted scanning, fixture safety and actual monorepo gate wiring | hooks/CI slice | workspace scripts |

**Manifest:** 38 logical entries, including paired paths/globs; this is a phased plan rather than proof that planned packages exist. Each handwritten source file remains limited to 500 lines.

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| general (initial migration) | 1-18 | Initial sequential migration ownership; later slice ownership/review is recorded separately below. |

**Historical assignment:** The initial migration had no active specialist. Later independently owned supervisor, transport and engine-service slices and their separate reviews are recorded under `sdd/reviews/`; this table does not describe current agent availability.

---

## Code Patterns

### Pattern 1: Deep typed boundary

```ts
export interface MarketDataPort {
  readonly ticker: (request: TickerRequest) => Promise<Ticker>
}
```

The port hides HTTP signing, retries and provider response formats from tools and strategies.

### Pattern 2: Guarded side effect

```ts
export async function executeGuardedOrder(input: OrderIntent, deps: OrderDependencies): Promise<OrderResult> {
  const decision = await deps.risk.authorize(input)
  if (!decision.allowed) return { sent: false, reason: decision.reason }
  return deps.exchange.place(input)
}
```

The caller cannot bypass the final risk decision by calling the exchange adapter directly.

---

## LLM Prompts

Prompts are runtime inputs to the AI decision track. The system policy is code-owned and contains no interpolated agent/news/GitHub prose. Agent-provided `thesis` and `invalidation` are validated as strings, normalized and bounded, persisted as evidence, and returned to the model only in an explicit `trusted: false` data envelope. The envelope communicates provenance; it is not claimed to make arbitrary model behavior immune to prompt injection. Explicit action/size/stop fields and the independent code-owned risk gate determine simulated decisions; evidence prose is never authorization and cannot bypass the separate guarded order tool. No news or GitHub ingestion connector exists in this implementation phase. Decisions are persisted with brief hash, model/tool metadata, input provenance and risk result, without API credentials.

---

## Data Flow

```text
1. DSH Host resolves config and Harness credential references
   │
   ▼
2. Bybit adapter fetches instruments, market/account data and records latency/queue metrics
   │
   ▼
3. Public Testnet WebSocket adapter validates ticker frames, applies bounded queue backpressure, and passes immutable ticker events to the Python quant engine
   │
   ▼
4. Data contract passes normalized snapshots to Python quant engine or deterministic local backtest
   │
   ▼
5. Research/strategy modules emit a typed target intent; AI output is untrusted proposal data
   │
   ▼
6. Agent prose is normalized and bounded by the evidence boundary, stored for the user, and returned to the model only as a provenance-tagged untrusted data envelope; it cannot authorize actions
   │
   ▼
7. Independent risk module checks account, environment, limits, precision, idempotency and reconciliation
   │
   ▼
8. Paper/Testnet executor acts; every event is append-only and backed up/migrated
   │
   ▼
9. Host/client health panel exposes state; graceful shutdown persists the reconnect counter and a new process starts with fresh lifecycle timestamps and an empty queue
```

---

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| DeepSeek Harness/Cordis | Bundle + injected services/slots | Harness-managed credentials/config | bidirectional | Validate version; cleanup effects on unload |
| Bybit V5 REST | Signed HTTPS adapter | Harness credential store; Testnet endpoint | bidirectional | bounded retry/backoff; never retry non-idempotent order blindly |
| Bybit public WebSocket | `quant_engine.market_data.BybitMarketDataAdapter` | None; public linear ticker topics only | inbound from fixed Bybit Testnet URL | bounded event queue applies consumer backpressure; reconnect uses capped exponential backoff with jitter; close cancels reads and closes the socket |
| PostgreSQL/SQLite dev | SQLAlchemy/Alembic | local secret/config | bidirectional | migration/backup/restore; fail closed on schema mismatch |
| Docker sandbox | local process boundary | no exchange credentials | bidirectional | resource/time limits; kill and record failure |
| GitHub references | read-only research input | no repository secret | inbound | pin commit, license/security review; treat content as untrusted |

---

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Numeric signals, risk, trust boundary, state transitions | `test/*.ts`, Python tests | Node/Vitest-compatible scripts, pytest/Hypothesis | exit 0 and deterministic assertions |
| Security unit | Prompt-injection fixture is preserved only as bounded untrusted evidence; malformed/oversized inputs are rejected or bounded; changing evidence prose alone cannot change the risk-gate result | `apps/dsh-plugin/test/trust.ts`, `apps/dsh-plugin/project.json`, `apps/dsh-plugin/package.json` | Node local unit target; no network or credentials | Nx `test:unit` includes the fixture and remains green |
| Integration | Bybit REST mock, retries, order idempotency, migration and restore | `test/integration.ts`, `python/tests` | Node, pytest, Alembic | exit 0; no live endpoint |
| Unit | Public WebSocket subscription, typed ticker parsing, bounded-queue backpressure, reconnect jitter and graceful close | `python/apps/quant-engine/tests/test_market_data.py` | pytest with injected fake connector/socket/clock | deterministic; no network |
| Bundle | Manifest, patch, Host/Client and resource exports | `scripts/check-bundle.ts` | Node | exit 0 with all required files |
| Security | secret scan, prompt injection, sandbox and dependency audit | `test/sandbox.ts`, scripts/CI | pnpm audit, pip-audit, SBOM tools | no unhandled high/critical finding |
| E2E / Verify Gate | Full project checks | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` | `pnpm run verify` | exit 0; complementary Plugin Manager smoke recorded |

---

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Invalid/expired credential | exchange auth error | redact, mark degraded, stop new orders | No | health + audit event |
| Stale market data/queue backlog | timestamp/queue metric | protective state, no new order | after recovery | queue gauge + reason |
| WebSocket disconnect | heartbeat timeout | reconnect with bounded backoff | Yes | reconnect counter/state |
| WebSocket malformed frame | JSON/topic/schema validation | discard frame and increment discarded count | No | received/parsed/discarded counters |
| Order timeout/unknown status | request timeout/reconciliation gap | stop duplicate send, reconcile | bounded | order latency + audit |
| Migration/restore failure | command/result/hash mismatch | do not delete source; restore previous snapshot | No | migration log + health |
| Sandbox violation | timeout/resource/exit code | kill process and quarantine result | No | sandbox audit |

---

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `env` | `demo\|testnet\|live` | Bundle config / `testnet` | No | Exchange environment; live is disabled by default. |
| `allowLiveTrading` | boolean | Bundle config / false | No | Mainnet order fence. |
| `apiKeyEnv` / `apiSecretEnv` | string | Harness credential names | No (names only) | References, never values. |
| `maxOrderNotionalUsd` | number | Bundle config / 24 | No | Per-order ceiling. |
| `maxOrderNotionalPctOfEquity` | number | Bundle config / 25 | No | Equity share ceiling. |
| `stateFile` | path | local app data | No | User-owned state location, excluded from package replacement. |
| `DATABASE_URL` | URI | uv app environment | Yes | Data-plane database connection. |

### Public WebSocket market-data ownership

`BybitMarketDataAdapter` owns the public Testnet URL, V5 ticker topic construction, JSON validation, reconnect/backoff, and a bounded `asyncio.Queue`. Its small consumer API is `start(symbols)`, `next_event()`, `health()`, and `close()`; strategies and risk modules consume normalized immutable `TickerEvent` values and do not know the Bybit wire schema. A full queue suspends the reader until a consumer frees capacity, propagating backpressure to the socket instead of growing memory without bound. Health includes connection state, queue depth, receive/parse/discard counts, reconnects, and last event time. It does not own persistence, REST access, account state, credentials, strategy decisions, or order execution.

### Durable lifecycle checkpoint boundary

`EngineRuntime` optionally writes a versioned JSON checkpoint on graceful stop using a flushed, fsynced temporary file and atomic replacement. Version 2 contains only the reconnect counter. Queue depth and lifecycle timestamps are process-local: a new process starts with an empty queue, a new `started_at`, and `stopped_at=None`, so stale backlog or old lifecycle times cannot be reported. Version 1 files are accepted only after validating their historical running flag, timestamps and queue field; those legacy values are ignored and only reconnect continuity is retained. Credentials, strategy configuration, orders and trade history remain outside this file. Startup fails closed to zero counters when the file is missing, malformed or uses an unsupported version, while exposing a typed error string in `RuntimeSnapshot`. This is a bounded restart checkpoint, not a process supervisor, exchange reconciliation mechanism or guarantee of crash-consistent order state; those remain separate operational work.

---

## Security Considerations

- Keep credentials in Harness storage or a permission-restricted local file; redact all logs and test output.
- Treat market/news/GitHub/agent/user content as data; use trust labels and bounded schemas to prevent prompt injection.
- Execute generated algorithms only through the sandbox boundary with no exchange credentials and strict time/memory/CPU limits.
- Enforce Mainnet lock, account identity, balance, precision, notional, daily loss, drawdown and idempotency in code outside the model.
- Preserve user state across upgrade by backup/hash/migration and never replace user-owned directories.

---

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | structured redacted logger | explains auth, guard, recovery and lifecycle decisions |
| Metrics | runtime monitor plus data-plane metrics | queue backlog, CPU, memory, reconnects and API/order latency |
| Tracing | OpenTelemetry boundary planned | correlate market snapshot → decision → risk → execution |
| Health | `/api/bybit-quant?view=health` and process health | exposes environment, degraded state and last successful reconciliation |

---

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| MUST monorepo / AT-001 | Workspace projects and graph | `nx show projects`, `nx graph` |
| MUST TS/500 lines / AT-002 | TS app and atomic modules | `pnpm run typecheck`, line-count script |
| MUST Bundle / AT-003 | `package.json`, patch, Host/Client and lifecycle smoke | `bundle:check`, Plugin Manager smoke |
| MUST safety / AT-004 | independent guarded executor | negative order tests |
| MUST operations / AT-005 | runtime monitor and Python health | monitor tests/health route |
| MUST persistence / AT-006 | Alembic + backup/restore | migration/restore tests |
| MUST trust / AT-007 | trust labels and sandbox | injection/sandbox tests |
| MUST SBOM / AT-008 | npm/cyclonedx and Python SBOM | `pnpm run sbom`, `pnpm run security:deps` |
| MUST docs / AT-009 | bilingual README updates | secret scan + docs review |

---

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| DSH Plugin Manager unavailable locally | Cannot prove install lifecycle | detect exact tool/version and record blocker; do not edit managed profile | external verification pending |
| Current workspace move breaks imports | Build regression | move in small batches, update graph, run Verify Gate after each batch | medium during migration |
| Testnet account has zero equity/main-account identity | No live Testnet order E2E | preserve guard; use mock/paper lifecycle until account is valid | order E2E pending |
| Reference repositories change | audit drift | pin commit SHA and license evidence | future refresh required |
| Large UI/strategy modules | cognitive load and line-limit breach | split by knowledge, not temporal sequence; keep each file ≤500 lines | refactor effort |

---

## Advisor Ledger

None — no formal external design review was executed. The installed `software-design-philosophy` review is recorded above as an internal design diagnostic.

---

## Revision History

### In-process supervisor increment — 2026-11-17

`quant_engine.EngineSupervisor` owns a single market-data adapter/runtime pair, exposes a typed `SupervisorSnapshot`, closes the worker gracefully, and retries a worker that reports `stopped`/`failed` up to a configured finite budget. This is an in-process async worker supervisor only: it cannot detect a hung worker that continues reporting healthy state, survive supervisor-process death, supervise OS processes, recover orders or reconcile exchange/account state. Default adapter construction remains the public Testnet adapter; tests inject fakes and make no network calls.

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-11-17 | SDD Design by RDD | Initial design; records root-layout drift and true monorepo migration. |
| 1.1 | 2026-11-17 | market-data increment | Adds ownership, data flow, manifest and deterministic verification contract for public Testnet WebSocket ingestion. |
| 1.2 | 2026-11-17 | trust-boundary increment | Records observed runtime gap and defines a bounded provenance envelope for model-visible agent prose, with deterministic risk-independence tests; explicitly does not claim regex or envelope alone eliminates prompt injection. |
| 1.3 | 2026-11-17 | runtime checkpoint increment | Defines the versioned, atomic health checkpoint contract, fail-closed malformed-state handling and explicit limits: no credentials, strategy state, order state, supervisor or exchange reconciliation. |
| 1.4 | 2026-11-17 | checkpoint semantics correction | Removes queue depth from persisted state because it is process-local; startup resets backlog to zero and reads legacy v1 queue fields only for compatibility. |
| 1.5 | 2026-11-17 | checkpoint timestamp correction | Narrows v2 persistence to reconnect count; v1 timestamps are validated for compatibility then ignored. Restart lifecycle timestamps are always fresh process state. |
| 1.6 | 2026-11-17 | in-process supervisor increment | Defines finite restart semantics and typed health status, with explicit process supervision, hung-worker, order recovery and reconciliation limits. |

---

## Next Step

Execute o **SDD Build by RDD**.

## Independent read-only service integration — 2026-11-17

See `DESIGN_ENGINE_SERVICE.md` for the scoped contract and `../reviews/REVIEW_ENGINE_SERVICE_2026-11-17.md` for independent ACCEPT. FastAPI lifespan owns a supervisor and a real queue consumer; the worker restarts as a unit on consumer failure. Pydantic is the sole HTTP schema source. Exporting `contracts/openapi/quant-engine.v1.json` never enters lifespan. CLI requires explicit symbols and loopback binding; endpoints are only `/api/v1/health` and `/api/v1/market/{symbol}`. Readiness requires connected ingestion and receive/exchange freshness for every configured symbol; partial deltas remain explicitly partial, absent values null, and execution/reconciliation unknown.

At that service-only snapshot, SDK/DSH integration was absent; the next increment below implements the read-only portion. Authenticated remote control, full snapshot/persistence, Nautilus sole exchange execution authority, portfolio/risk/AI/research platform and OS process recovery remain incomplete. The existing direct TypeScript order path remains DRIFT-ORIGINAL-003; it is not accepted as a replacement for the mandatory Nautilus architecture. Full original MUST acceptance remains open.

## Generated SDK, DSH, native foundation and hooks — 2026-11-17

Supplements `DESIGN_ENGINE_CLIENT.md`, `DESIGN_DSH_ENGINE.md`, `DESIGN_NAUTILUS_EXECUTION.md` and `DESIGN_GIT_HOOKS.md` precede their implementation and record the detailed manifests. The Python OpenAPI remains schema authority: openapi-typescript emits paths, openapi-fetch owns typed calls, Ajv validates the same components at runtime. Transport hides numeric-loopback validation, bounded bytes/body deadlines/cancellation and fixed safe errors; readiness policy remains with Python.

Host's `createEngine` facade receives configuration without credentials. Two read-only tools (`quant_get_engine_status`, `quant_get_market_snapshot`), authenticated bridge `view=engine` and an explicit Client card query share the SDK. Host environments other than Testnet return environment_mismatch without making a service request. Unload closes requests, not the independently running process. Existing REST candle/account/analysis paths are retained; partial ticker fields stay null. Private workspace packages become build-only dependencies and tsdown inlines their runtime. Packed outside-repository import validates closure but proves no Plugin Manager install/auth/upgrade behavior.

Native `quant-execution` uses pinned stable NautilusTrader 1.231.0 for finite offline BacktestEngine simulations, with real accepted/fill/cancel/partial events, unique native IDs, run-local deduplication and dispose cleanup. Stationary L2 fixtures explicitly consume finite liquidity; they do not model historical replay. Only literal backtest is accepted. Live exchange adapter, durable uncertain-order recovery, complete final risk and TS REST cutover remain open; the existing direct-order authority drift is not resolved by adding offline native tests.

Hooks encapsulate sensitive-path classification, redacted scanner execution and unchanged-index guarantees in one ESM TypeScript module; thin launchers delegate. Tests use isolated repositories. CI shares root SDK/tooling/full TS project checks; hosted CI and actual hook installation require separate evidence. Each new slice has independent ACCEPT, but full original MUST acceptance remains open. Current dependency-security status and aggregate execution receipts are tracked in Verify Gate rather than inferred from tests.

### Security dependency override / tool subprocess correction

The native package pins patched `fsspec==2026.6.0`; root `python/pyproject.toml` explicitly overrides Nautilus1.231.0's vulnerable exact2026.2.0 pin. Root uv lock is the required environment. Native Parquet catalog round-trip plus execution regressions scope compatibility; upstream metadata remains incompatible (`uv pip check` exits1, standalone pip rejects the conflict). This is an explicit security override, not a claim that all Nautilus APIs/remote filesystems are compatible. Revisit when upstream releases a patched compatible pin. Verify Gate owns final scan/test receipts.

SDK Nx targets invoke installed root tools directly instead of nested package-manager switching. Bundle pack/SBOM subprocesses share `apps/dsh-plugin/scripts/pnpm-environment.ts`, hiding environment sanitation and workspace-root calculation. Two observed ENOEXEC gate failures drove this correction; fresh aggregate evidence is required rather than assuming scoped checks fix all callers.


## Independent risk and local command ledger foundations — 2026-11-17

`DESIGN_QUANT_RISK.md`, `DESIGN_COMMAND_LEDGER.md` and
`DESIGN_RISK_WORKSPACE.md` define this increment before code. `quant-risk` owns
strict snapshot/policy validation and deterministic conservative gross-risk
arithmetic, with no transport or execution dependency. `quant-data` owns durable
command identity, idempotent admission, lifecycle transitions, single dispatch
claim and append-only local SQLite audit. Callers must treat an approved risk
plan as data, not authorization. Neither package submits an exchange order.

The future engine transaction boundary must bind server-owned account/market
state, current risk generation, atomic exposure reservation and durable command
audit to sole Nautilus submission and uncertain-order reconciliation. These
foundations do not implement that boundary, account locking, long-lived paper or
private account state. The service still has only two read-only routes. Existing
TS REST submission remains DRIFT-ORIGINAL-003; no scope reduction or Mainnet
acceptance follows from local risk/ledger tests. Independent scoped risk/ledger ACCEPT reviews and current
aggregate/security receipts are recorded in Verify Gate; they do not accept
the missing execution transaction or full product requirements.

The package is a genuine discoverable Nx/uv project only after discovery, real
graph edges, root import and build receipts; a directory alone is insufficient.
The local schema migration is exercised against disposable SQLite fixtures,
not a deployed/user database. PostgreSQL and power-loss recovery are unverified.

`DESIGN_EXECUTION_CUTOVER.md` records the next dependency-ordered integration
contract, including authenticated engine admission, one durable account/session
writer, native internal-paper node lifetime, dispatch uncertainty and protected
restart. It is future design, not implemented runtime acceptance; finite
BacktestEngine fixtures cannot substitute for a continuously operating node.
