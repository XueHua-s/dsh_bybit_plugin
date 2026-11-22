# DESIGN: Authenticated DSH native internal-paper controls

> Bounded integration contract. Existing paper service/SDK acceptance is scoped; this document does not certify the full quant platform.

> **Superseding dashboard decision (2026-11-19):** The original card-level Start/Stop design below was replaced by the view-only dashboard boundary in `DESIGN_BYBIT_AI_QUANT.md`, Decision 5. The browser route and card expose status only; model-facing paper Tools remain a separate, explicitly configured, default-off control surface. The historical manifest rows below describe the original proposal, not the final dashboard behavior.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | DSH_PAPER |
| **Date** | 2026-11-17 |
| **Author** | paper_dsh_design / SDD Design by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **UX REVIEW** | N/A; bounded interaction states specified here |
| **LLM Prompts** | true at product scope; existing DSH loop consumes Tool descriptions; no new model/provider/runtime loop |
| **Status** | Ready for scoped Build after parent acceptance; service shutdown repair is a prerequisite verification gate |

This slice connects the accepted optional native synthetic service to DSH. It includes a concrete, independently operable capability provisioning path, five model-facing Tools, an observation-only dashboard card and an actual built-Host process test. No exchange connection, Testnet execution, Mainnet authorization, TS exchange-write cutover, replay recovery, new strategy/AI research runtime or user database migration belongs to this slice. Those original MUSTs remain incomplete. Existing `quant_paper`/AI books remain separate legacy simulations; this slice neither migrates nor routes them to the native service.

## Architecture Overview

```text
Operator starts optional quant-engine-paper CLI with explicit migrated DB/session
    | --capability-socket PATH (opt-in; no token in args/env/files)
    v
Python paper process --prebound loopback HTTP listener--> Uvicorn/FastAPI
    | process-memory capability, optional private Unix broker       |
    | owner directory0700 / socket0600                             v
    |                                                     existing PaperAdmission
    |                                                   risk + ledger + native IPC
    |                                                             v
    |                                                 spawned Nautilus paper owner
    v
Host private capability provider <---- bounded Unix connection, exact session/origin
    |
    v
Host native-paper facade --> generated SDK.paper --> authenticated loopback API
    ^                      (no browser Origin forwarded; no mutation retries)
    |
    +-- five strictly validated model Tools (control opt-in)
    +-- owner-only DSH connection.fetch exact GET/HEAD status route
             ^
             +-- demand-driven Client native-paper status card

Legacy Testnet market facade, REST exchange adapter and local paper books are separate.
Host unload closes only its requests/provider sockets; service/native lifetime is independent.
```

### Current evidence and drift

- `lib/engine.ts` exposes only default read-only public Testnet health/market. `createHostRuntime()` currently composes legacy REST/client/store state. Its `ctx.credentials.resolve()` path is unrelated to paper and must not become a capability fallback.
- `quant-api-client` exports `paper.status/start/stop/submit/command/request`, generated `PaperStatus`, `PaperSubmitRequest`, `PaperCommand` and explicit `PaperUncertain`. Python `paper_api_models.py` remains the sole HTTP DTO source. Current SDK validates environment and some identities, but does **not** bind every success to the Host-configured session; the new facade owns that binding.
- Python CLI currently accepts a private inherited FIFO FD only. Node child-process stdio can be a socketpair; do not assume Node fd3 satisfies that existing `S_ISFIFO` contract. Keep that path unchanged and add a distinct broker mode.
- Independent design review found an existing SDK ambiguity gap: Python can return503 after durable dispatch/native submit, while SDK mutations currently return plain unavailable. Manifest33–34 correct that policy in its existing SDK owner before Host acceptance; GET503 remains unavailable.
- Installed desktop runtime and relevant packages are `0.2.2-rc.3`. ASAR source confirms exact Fetch methods GET/HEAD/POST, carrier trust/auth admission, owner-only exact-route dispatch and async route disposal. This is source evidence, not a fresh installed interaction/authentication receipt.
- Installed credentials API provides reference and GrantRecord operations, but `resolve()` falls through managed values to process environment and dotenv layers. No supported standalone credential-export CLI was established. Durable GrantRecords are unnecessary for this ephemeral paper capability. Bybit keys remain governed by DSH secure credentials separately.
- Parent reports a current hosted shutdown-test failure and has assigned an independent fix. Do not treat earlier `b75d73c` CI as proof of the later documentation CI or repaired cleanup. New process gates depend on the final repaired baseline.

Detailed static receipts and actual inspection commands are in `sdd/reports/DESIGN_DSH_PAPER_EVIDENCE_2026-11-17.md`.

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| Private paper broker | Give the same OS user one process-local paper capability bound to this service | Python stdlib asyncio Unix server; strict local protocol | Nonsecret expected session/origin tuple | Bounded private capability envelope | Existing configured paper app and prebound HTTP listener |
| Host capability provider | Hide Unix path policy, scope validation, socket deadlines and cleanup | Node fs/net; closure, no exported token property | Fixed operator configuration | SDK capability callback; fixed-code failures | Broker |
| Native-paper facade | Present scoped paper operations and preserve uncertainty | Generated SDK plus Host authorization/context checks | Validated proposals/IDs; AbortSignal | Safe internal_paper result | Provider, existing SDK |
| Model Tool registrar | Expose five narrow operations without secret/configuration authority | Existing raw JSON Schema Tools | Strict model arguments | Facade result | Native-paper facade |
| Panel bridge | Serve native-paper status observation through the owner-authenticated carrier | Existing `connection.fetch.register` | Bounded same-origin UI requests | Safe facade status result | Installed DSH owner/auth fence |
| Client card | Show actual native-paper state on demand | Existing injected React runtime | Bridge result and user refresh | Status states | Bridge; no direct Python access |

## Key Decisions

### Decision 1: Service-owned ephemeral broker, no Host supervisor or durable capability record

| Attribute | Value |
|---|---|
| **Status** | Accepted for scoped design, subject to parent review |
| **Date** | 2026-11-17 |
| **Source** | Parent scope instruction; DEFINE AT-010/016/027; inspected CLI/DSH provider |

**Context:** An independently launched service and a Host need the same private capability. The existing inherited FIFO is suitable for trusted launchers but is not a concrete DSH provisioning mechanism. Ordinary secret config, Tool arguments, environment fallbacks or browser storage violate the requirements.

**Choice:** Extend `quant-engine-paper` with mutually exclusive required `--capability-fd N` or `--capability-socket PATH`. Broker mode generates `secrets.token_urlsafe(48)` in service memory and supplies that existing `Capability` to the app. It starts no exchange adapter. Host connects only to a configured local Unix socket; the capability is delivered directly to private Host memory and then the existing SDK Authorization header. No token persistence, browser provisioning form, Host child process, automatic migration or supervisor is added.

**Rationale:** One service-owned module hides provisioning and cleanup. The process can start without DSH and survive Host unload. This paper capability is not a Bybit API key and does not require copying exchange secrets into Python.

**Alternatives Rejected:**
1. `ctx.credentials.resolve()` — ambient/env/dotenv fallback is unsuitable and a separate service still needs private bootstrapping.
2. GrantRecord plus Host-launched detached supervisor — supported storage API, but unnecessary durable secret state and lifecycle scope expansion.
3. Secret in argv/config/Tool/UI or manual managed-profile edit — disallowed boundary.

**Consequences:** Broker deployment supports POSIX Unix sockets only in this slice; unsupported platforms fail unavailable. Trust includes other processes with the same OS user identity, as does the existing local credential store. A hostile same-user process/debugger is outside this authentication boundary; do not claim plugin/process attestation or protection from a compromised user account.

### Decision 2: Bind HTTP ownership before disclosing any capability

| Attribute | Value |
|---|---|
| **Status** | Accepted for scoped design |
| **Date** | 2026-11-17 |
| **Source** | Inspected Uvicorn `Server.run(sockets=...)`; loopback authority threat analysis |

**Context:** A rogue local listener occupying the configured port could receive a bearer token if provisioning merely returned an expected URL. Loopback destination validation alone does not authenticate the server.

**Choice:** In broker mode, the same paper process binds/listens its numeric loopback HTTP socket first, with exclusive normal TCP bind semantics; no `SO_REUSEPORT`. Pass that actual socket to `uvicorn.Server(uvicorn.Config(...)).run(sockets=[listener])`, preserving existing disabled access logging and shutdown configuration. Binding failure occurs before broker publication. The app opens `PaperAdmission` before it accepts broker requests; failure to open never releases a token. The broker envelope states the actual fixed listener origin and configured session. Host validates these against its explicit operator configuration before sending any HTTP request. HTTP listener, broker and native cleanup are all observed on shutdown; a retained token after the owner exits does not authorize a new listener.

**Rationale:** The process that possesses the capability also reserves the HTTP endpoint; no separate launcher or undocumented Uvicorn monkeypatch is needed. Installed Uvicorn accepts supplied sockets through its public Server interface.

**Alternatives Rejected:**
1. Probe an unowned port then later start Uvicorn — a bind race remains.
2. Trust broker metadata without checking filesystem owner/type/mode and tuple — permits accidental cross-session capability use.

**Consequences:** Do not cache capabilities across operations. Every operation re-reads the broker; after service exit the provider cannot obtain a token for a reused HTTP port. A malicious same-user replacement broker remains within the explicitly stated same-user trust boundary.

### Decision 3: A bounded local protocol owns no HTTP trading DTOs

| Attribute | Value |
|---|---|
| **Status** | Accepted for scoped design |
| **Date** | 2026-11-17 |
| **Source** | Existing generated SDK contract; local socket integration needs |

**Context:** The secret delivery envelope is a local IPC protocol; it is neither a model Tool schema nor a new FastAPI command schema.

**Choice:** One newline-terminated UTF-8 JSON request per Unix connection, maximum1024 bytes including newline; no trailing frame. Request has exactly `version:1`, `environment:"internal_paper"`, `session_id`, `origin`. Response has those exact fields plus `capability`; no arbitrary diagnostic text, token previews or scopes claimed by the caller. Broker validates the exact configured tuple before answering. Both ends accept only canonical encoding: the parsed object reserialized in the specified field order with compact separators, ASCII escaping and one LF must equal received bytes. This rejects duplicate keys, alternative/trailing frames and ambiguous encodings without a second parser. Host additionally rejects extras, wrong types/version/environment/session/origin, noncanonical origins, invalid printable capability or bytes beyond1024. Tests use the same explicit golden protocol fixtures; this small v1 protocol is documented here and is not a duplicated trading DTO. Invalid protocol closes without a secret-bearing response.

**Rationale:** A small fixed handshake needs no new package, dependency or second generated SDK. Changes to trading fields still happen only in Python OpenAPI and generated artifacts.

**Alternatives Rejected:**
1. Generic secret broker/credential enumeration service — unnecessary access surface.
2. Returning the capability from any HTTP health, Tool or panel route — leaks into model/browser surfaces.

**Consequences:** Both language implementations enforce this fixed local shape. Protocol changes require a version change and matching cross-language fixture update. Token content is never an error message or assertion operand printed on failure.

Stream completion is explicit: provider writes the entire canonical request with `socket.end(requestFrame)` to half-close its write direction while continuing to read. Broker reads **through request EOF**, under its total500ms/1024-byte budget, and validates the complete bytes before returning any capability. It then writes the canonical response and closes its write direction/connection. Provider reads **through response EOF**, under its own total500ms/1024-byte budget, before validation or trust. Neither side treats the first LF as completion. Delayed trailing frames, split frames, missing LF and peers which never send EOF are required tests; missing EOF times out without disclosure/trust. EOF waiting never extends either deadline.

### Decision 4: Native paper has a separate Host authority and visible identity

| Attribute | Value |
|---|---|
| **Status** | Accepted for scoped design |
| **Date** | 2026-11-17 |
| **Source** | DEFINE AT-014/015/016/021/027/028; existing paper/legacy drift |

**Context:** Host `env` describes the legacy exchange adapter, not a native paper session. Existing legacy paper and AI books cannot become native OMS truth by renaming them.

**Choice:** New facade has its own explicitly configured session and URL; output context always says `environment:"internal_paper"`, `synthetic:true`, `source:"quant-engine-paper"`. It does not infer authority from legacy `env`, live/Testnet switches or `hasKeys`. Absent broker/session configuration disables paper integration; `paperControlEnabled` defaults false and gates every mutation before provider/network work. Validate config before legacy credential settings. Bind **every successful** status/start/stop/submit/command/request result to configured session and environment. Status mismatch is invalid_response; a mutation mismatch is outcome_uncertain with original recovery identity. Never expose the provider object/token through the runtime facade, logger, health or Client imports. Host close cancels requests and Unix sockets only.

**Rationale:** One deep boundary hides generated DTO validation, provisioning, scope checks, mutation policy and uncertainty. Tools/UI share it without sharing account, native or transport internals.

**Alternatives Rejected:**
1. Reuse `quant_paper`, REST `bybit_trade`, AI track or legacy starting balance — different execution authorities and persisted facts.
2. Fall back to REST/custom fills when service unavailable — defeats native authority.

**Consequences:** TS exchange writes remain an explicitly open separate cutover; this slice cannot certify sole exchange authority or Testnet trading acceptance. Public paper status has no wallet/equity fields; UI must not invent them.

## File Manifest

All new paths below are proposed; existing paths were inspected. No dependency/lock change is expected. Keep handwritten sources ≤500 lines; split on information ownership before reaching the limit. Do not edit the independently owned shutdown-fix files during parallel Build without explicit ownership transfer.

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `python/apps/quant-engine/src/quant_engine/paper_capability.py` | Create | Strict local broker, path policy, bounded connections, cleanup | Python broker implementer | None |
| 2 | `python/apps/quant-engine/src/quant_engine/paper_bootstrap.py` | Modify | Explicit alternative CLI mode, memory capability, prebound Uvicorn listener | Python broker implementer | 1 |
| 3 | `python/apps/quant-engine/src/quant_engine/paper_api.py` | Modify | Optional broker lifespan after admission open; bounded cleanup in finally | Python broker implementer | 1 |
| 4 | `python/apps/quant-engine/tests/test_paper_capability.py` | Create | Local protocol/path/limits/redaction/failure tests | Python broker implementer | 1 |
| 5 | `python/apps/quant-engine/tests/test_paper_capability_process.py` | Create | Actual CLI bind, refusal, broker/service/native cleanup, old FD regression | Python broker implementer | 2,3,4 |
| 6 | `apps/dsh-plugin/src/lib/paper-capability.ts` | Create | Private bounded provider and operator config validation | TS Host implementer | None |
| 7 | `apps/dsh-plugin/src/lib/engine-paper.ts` | Create | Scoped generated-SDK facade and authorization | TS Host implementer | 6,33 |
| 8 | `apps/dsh-plugin/src/host-tools-paper.ts` | Create | Five strictly validated native-paper Tools | TS Host implementer | 7 |
| 9 | `apps/dsh-plugin/src/host-paper-panel.ts` | Create | Exact owner bridge, bounded start/stop, no secret output | TS Host implementer | 7 |
| 10 | `apps/dsh-plugin/src/host-runtime.ts` | Modify | Compose private facade, close effect; route disposer type supports Promise | TS Host implementer | 7 |
| 11 | `apps/dsh-plugin/src/index.ts` | Modify | Register Tools/bridge with lifecycle | TS Host implementer | 8,9,10 |
| 12 | `apps/dsh-plugin/test/paper-capability.ts` | Create | Real temporary Unix sockets, scope/timeout/close/redaction | TS Host implementer | 6 |
| 13 | `apps/dsh-plugin/test/paper.ts` | Create | Built Host, SDK, Tool/bridge/session/uncertainty regressions | TS Host implementer | 8,9,11 |
| 14 | `apps/dsh-plugin/src/client-paper.ts` | Create | Native-paper status/start/stop card with request ownership | UI implementer | 9 |
| 15 | `apps/dsh-plugin/src/client.ts` | Modify | Mount independent native-paper card | UI implementer | 14 |
| 16 | `apps/dsh-plugin/test/client-paper.ts` | Create | Demand-only requests, controls, pending/uncertain/unmount behavior | UI implementer | 14 |
| 17 | `apps/dsh-plugin/test/render.ts` | Modify | Real React SSR initial native-paper identity and disabled state | UI implementer | 15 |
| 18 | `apps/dsh-plugin/scripts/test-dsh-paper-process.ts` | Create | Actual built Host→Unix provider→SDK→CLI→native E2E, synthetic temporary DB; post-dispatch503 recovery probe | Process-E2E implementer | 5,11,34 |
| 19 | `apps/dsh-plugin/package.json` | Modify | Wire new units and explicit `test:paper-process` target | Integration owner | 12,13,16,18 |
| 20 | `apps/dsh-plugin/project.json` | Modify | Mirror real unit/process commands; process target uncached | Integration owner | 19 |
| 21 | `.github/workflows/ci.yml` | Modify | Blocking process E2E after locked uv sync/build; keep network smoke separate | Integration owner | 20 |
| 22 | `apps/dsh-plugin/cordis.patch.yml` | Modify | Commented opt-in nonsecret paper settings only | Integration owner | 7 |
| 23 | `docs/runbooks/paper-service.md` | Modify | Runnable broker CLI, explicit premigrated DB, state/cleanup limits | Documentation owner | 2,7,18 |
| 24 | `README.md` | Modify | Verified native DSH controls and remaining boundaries | Documentation owner | 18 |
| 25 | `README.zh-CN.md` | Modify | Matching Chinese behavior and limits | Documentation owner | 24 |
| 26 | `sdd/handoffs/HANDOFF_BYBIT_AI_QUANT.md` | Modify | Current scoped receipts, outstanding full-goal work | Parent | 18 |
| 27 | `sdd/reports/BUILD_REPORT_DSH_PAPER_BROKER.md` | Create | Actual Python commands/exits/limitations | Python broker implementer | 5 |
| 28 | `sdd/reports/BUILD_REPORT_DSH_PAPER_HOST.md` | Create | Actual provider/facade/tools/bridge receipts | TS Host implementer | 13 |
| 29 | `sdd/reports/BUILD_REPORT_DSH_PAPER_UI.md` | Create | Actual Client states/tests; separate browser receipt | UI implementer | 16,17 |
| 30 | `sdd/reports/DSH_PAPER_PROCESS_E2E_2026-11-17.md` | Create | Allowlisted real process evidence and cleanup PIDs/listeners | Process-E2E implementer | 18 |
| 31 | `sdd/reviews/REVIEW_DSH_PAPER_2026-11-17.md` | Create | Independent code/design/native integration verdict | Independent reviewer | 27,28,29,30,34 |
| 32 | `sdd/reports/VERIFY_GATE_2026-11-17.md` | Modify | Aggregate root/Python/schema/security/SBOM/release facts | Parent | 31 |
| 33 | `packages/ts/quant-api-client/src/paper.ts` | Modify | Existing mutation ambiguity owner maps503/unavailable to outcome_uncertain; GET unchanged | SDK implementer | None |
| 34 | `packages/ts/quant-api-client/test/paper.test.ts` | Modify | All mutation503 recovery identities, zero retries and unchanged GET503 | SDK implementer | 33 |

**Total Files:** 34. Dependency numbers are stable IDs rather than strict execution order:33 is built before7, and34 before18; the graph remains acyclic.

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| Python broker implementer | 1–5,27 | Owns service provisioning/listener/lifespan knowledge |
| SDK implementer | 33–34 | Existing SDK owns mutation ambiguity consistently for all consumers; no Host-only duplicate policy |
| TS Host implementer | 6–13,28 | Owns private client authority, Tool/bridge boundary |
| UI implementer | 14–17,29 | Owns presentation/request state, consumes fixed bridge contract |
| Process-E2E implementer | 18,30 | Exercises cross-language integration independently of unit mocks |
| Integration/documentation owner | 19–25 | Single writer for manifests, CI, opt-in defaults and user documentation |
| Independent reviewer / parent | 26,31,32 | Acceptance independent of implementation; whole-product context retained |

**Agent Discovery:** Parent explicitly coordinates delegated work; AGENTS.md conditionally prescribes GPT-6.1 Sol/xhigh when primary is Astra. Owners here are task roles, not claims that specific agents have been created. These assignments are acyclic and avoid shutdown repair ownership.

## Code Patterns

### Pattern 1: Existing SDK types remain authoritative

```typescript
import type { PaperCommand, PaperStatus, PaperSubmitRequest } from '@bybit-quant/quant-api-client'

// Proposed Host-only type. The service owns environment/session/order_type truth.
export type PaperProposal = Pick<PaperSubmitRequest,
  'request_id' | 'symbol' | 'side' | 'quantity' | 'limit_price'>
export type PaperCommandIdentity = Pick<PaperCommand, 'command_id' | 'native_client_order_id'>
export type NativePaperState = PaperStatus
```

Implementer defines `createPaperCapabilityProvider({socketPath, origin, sessionId})` returning only `{resolve():Promise<string>, close():void}`. It exports no token-bearing DTO. `createPaperEngine(config)` consumes that provider internally and exposes only `status/start/stop/submit/request/command/close`. Public results extend existing `PaperResult`/`PaperUncertain` with fixed `source:"quant-engine-paper"`, `environment:"internal_paper"`, `synthetic:true`, and nonsecret `configured:boolean`, `control_enabled:boolean`; return data uses generated types. Local disabled/control-disabled codes are fixed Host results, not fabricated HTTP statuses. Every facade operation returns this same context so Tool and UI cannot disagree about configuration or control availability.

Existing SDK `uncertain()` remains the **single** mutation ambiguity policy. Add `unavailable` to its existing uncertainty causes: submit503 returns `outcome_uncertain`, `cause:"unavailable"`, `recovery:{action:"query_request",request_id:originalRequestId}`; start/stop503 return the same code/cause with `recovery:{action:"query_status"}`. Observation503 stays `{ok:false,code:"unavailable",status:503}`. The Host adds session binding but never reimplements this503 policy. A503 may precede dispatch or follow it; without authoritative evidence it is not proof of no side effect. No branch retries a mutation.

### Pattern 2: Proposed explicit CLI and configuration interfaces

```text
quant-engine-paper --database /explicit/premigrated/paper.sqlite \
  --session native-paper-demo --host 127.0.0.1 --port 8766 \
  --capability-socket /private/tmp/bqp-UID/session.sock

# Existing independent trusted-launcher mode remains supported:
quant-engine-paper --database PATH --session ID --capability-fd N
```

The first command is a planned Build interface, not a command executed by this design task. UID is substituted by the trusted operator; it is not a secret. No CLI subcommand accepts token material.

Tools use strict `additionalProperties:false` **and** runtime validation:

| Tool | Arguments | Operation |
|---|---|---|
| `quant_get_paper_status` | `{}` | Authenticated status |
| `quant_start_paper` | `{}` | Start fixed configured native session |
| `quant_stop_paper` | `{}` | Freeze admission and stop native owner; no flatten claim |
| `quant_submit_paper_order` | `request_id`, `symbol:"BTCUSDT"`, `side:"buy"|"sell"`, decimal-text `quantity`, `limit_price` | Submit fixed internal_paper LIMIT proposal |
| `quant_get_paper_command` | `request_id` | Query original durable request identity |

Tool arguments never contain session/origin/URL/socket/account/balance/policy/token or arbitrary native parameters. Quantity/price use the current generated decimal bounds; reject zero as invalid proposal where the existing admission contract does. IDs follow the generated opaque grammar, including its leading alphanumeric rule. Control Tools are not marked concurrency-safe; the service remains the sole actual account serialization authority.

## LLM Prompts

### Inventory

| # | Path / Runtime | Type | Consumer | Output Shape |
|---|---|---|---|---|
| LP-001 | Existing `host-runtime.ts` systemPrompt note; unchanged by this slice | loop, existing external DSH agent loop | DSH model; no new local LLM call | Existing Tool proposals, never secret/configuration authority |
| LP-002 | `host-tools-paper.ts` descriptions/schema | static Tool interface guidance consumed by unchanged external DSH loop | DSH model | Strict arguments in the five rows above |

LP-001 retains existing research/legacy behavior; this slice does not rewrite or certify it. LP-002 explains synthetic internal-paper identity, native service separation, LIMIT-only proposals and query-original-identity recovery. Tone is factual operator guidance. Inputs are bounded proposals; result truth comes from service state. Approved fallback is a fixed disabled/unavailable/protected/uncertain result and no alternative execution path. No provider/model/version is selected or changed. External evidence remains inert data; text containing instructions cannot change configured control authority, risk limits or server context. The inventory describes prompt contracts; final wording belongs to Build review.

Build routing correction: `sdd-loop-builder` found no newly owned iterative LLM
process in these static interfaces, so no new LOOP_SPEC, stages or budgets are
introduced. `sdd-prompt-builder` compiled the five descriptions from the fixed
caller contract. Receipt and exact wording are in
`sdd/reports/PROMPT_CONTRACT_DSH_PAPER_2026-11-17.md`; LP-001 is unchanged.
This corrects inventory classification only, not architecture or authorization.
Actual external DSH model compliance remains unevaluated; deterministic guards
and integration tests, not prose, own safety acceptance.

## Data Flow

```text
1. Operator selects a premigrated isolated paper DB, fixed session, numeric HTTP
   origin and private Unix socket. No automatic DB upgrade, reset or recovery.
2. Broker-mode CLI validates private paths, reserves actual HTTP listener, generates
   capability in memory, opens admission, then admits bounded broker connections.
3. Explicit Tool/UI request reaches the Host facade. Validate arguments/config and
   control opt-in before private provider/network work; never resolve Bybit keys.
4. Provider lstat-checks path chain/type/uid/modes, connects with500ms deadline,
   exchanges one ≤1024-byte frame, validates exact tuple and file identity again.
5. Existing SDK sends capability in Authorization to the configured origin, with
   existing total deadline, redirects forbidden, size bound and no mutation retry.
6. Existing admission/risk/ledger/native service owns all trading truth. Host never
   manufactures fills, account data, risk context, balances or native IDs.
7. Facade validates every successful response session/environment; return safe
   generated data with fixed native internal-paper source context.
8. Accepted202 means command admitted/observed, not filled. Show returned native
   state. Same request/payload keeps durable identity; changed payload conflicts.
9. Ambiguous mutation preserves outcome_uncertain + original request/status lookup.
   A404 lookup is only currently not found; do not conclude no dispatch or auto-send.
10. Host/UI close aborts owned work only; native execution can finish independently.
    Operator SIGTERM closes broker/HTTP listener and reaps native child, or reports
    failure. Unclean/nonflat restart remains protected, with no balance reset.
```

### Broker resource and path contract

- POSIX only. Absolute canonical socket path, encoded length≤100 bytes for the macOS target; no abstract sockets. Final directory is dedicated, same uid, mode0700. Socket is same uid, mode0600. Reject symlink components, non-directory parents, unsafe owner/mode, regular file/FIFO instead of socket and invalid path traversal. `/private/tmp` may be an ancestor; never use a world-writable directory as the immediate socket parent. Do not chmod broad pre-existing parents.
- Service may create only its missing dedicated final directory0700. It never unlinks an existing socket/file on startup, including a supposedly stale one. Record created socket device/inode; cleanup unlinks only that same owned socket. Do not remove operator directories or user data.
- Broker total handshake deadline500ms, one frame/request per connection **through EOF**, maximum4 active connections. Use a synchronous connection callback which refuses excess **before** creating a task or waiting on a semaphore; do not accumulate unbounded accepted handler tasks. Set the stream-reader buffer limit to1024 and cap bytes before JSON parse; close every connection on completion/error and await bounded writer close. Closing broker first refuses new work, then cancels/awaits existing tasks. No request-body or raw exception logging.
- Provider has500ms total timeout including connect/read,≤1024 response bytes and at most4 live sockets; no queue or automatic retry/cache. On saturation fail capability_unavailable. Its `close()` is final, destroys live sockets synchronously and prevents later requests. Existing SDK callback has no signal parameter: provider timeout/close independently prevents leaks after SDK abort; late provider completion must never send HTTP after SDK deadline.
- Re-check directory/socket device/inode/type/uid/mode after connect/read before using capability; a changed path fails closed. This reduces accidental races and does not turn same-user filesystem permissions into remote attestation.

### Panel bridge and UX contract

The final exact `/api/bybit-quant/paper` route registers through existing optional webServer/connection injection and owns GET/HEAD status only. Unsupported query fields, method or request body fail with fixed codes; the browser has no start, stop, submit or capability-delivery route. Use the supported carrier auth/owner fence, reject cross-origin Origin/Sec-Fetch-Site when present, never proxy browser Authorization/Cookie/Origin to Python, and return `Cache-Control:no-store` with no body for HEAD. Do not proxy arbitrary Python error text/status into the browser. The original proposal for POST lifecycle actions, streaming-body limits and card-level mutation states is superseded by the read-only dashboard decision above; lifecycle actions remain available only through the separately configured model-facing paper Tools.

Card title is `Native internal paper / 原生内部模拟`, with always-visible synthetic/no-exchange wording and a separate legacy-book note. Initial state is Not checked, not idle/ready inferred from charts. An explicit Check starts one request. The dashboard card and `/api/bybit-quant/paper` bridge are observation-only: browser Start, Stop and order-submission mutations are intentionally absent. Start/Stop remain model-facing Tool operations behind explicit paper configuration and default-off control opt-in. Protected/unready states never display execution readiness. Show protected and outcome_uncertain literally with a Check status recovery action; never automatically retry. Unmount aborts HTTP requests, preserves no token in state and never stops the service. No new default background polling or UI account/equity inference. This later dashboard decision supersedes the earlier card-level Start/Stop wording in this document; it does not grant the model exchange authority.

Lifecycle action permission for the model-facing Tools is independent of execution `ready`. The following table applies after valid session binding, `configured:true`, `control_enabled:true` and no pending request; otherwise mutations are disabled. The dashboard exposes only an explicit status Check.

| Latest scoped status | Start | Stop | Display / recovery |
|---|---|---|---|
| No successful status, unavailable or uncertain mutation not yet queried | Disabled | Disabled | Check status; no inferred absence of side effects |
| `idle`, native process false, `ready:false` | Enabled | Disabled | Explicit first start is valid despite ready:false |
| `running`, native process true, ready either value | Disabled | Enabled | Readiness affects execution disclosure, not Stop authority |
| `protected`, native process true, ready:false or stale/unready | Disabled | Enabled | Preserve explicit Stop for a process requiring cleanup |
| `protected`, native process false | Disabled | Disabled | Query/inspect; no restart/reset via this card |
| `stopping`, native process either value | Disabled | Disabled | Check progress; never claim completed stop |
| `stopped`, native process false | Disabled | Disabled | Current service requires an explicit new session; no restart promise |
| Inconsistent state/liveness combination | Disabled | Disabled | Show invalid/inconsistent state and Check; infer no ready state |

In particular, do not implement `disabled = !status.ready` for both controls. Tests must cover idle first Start and protected/unready native-alive Stop.

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| Installed DSH carrier | Owner-only exact Fetch registration | Existing carrier Host/Origin/auth + owner dispatch | UI↔Host | Missing supported carrier leaves panel unavailable; no raw listener fallback |
| Python optional paper service | Existing generated SDK HTTP | Private broker-provided session capability | Host↔service | Existing timeout/abort; no mutation retry; preserve recovery identity |
| Local capability broker | Version1 private Unix protocol | Owner uid and private directory/socket boundary; exact tuple | Host↔service |500ms/1KiB/4 connections, fail closed, no env/credential fallback |
| Uvicorn | Installed Server/Config supplied socket | Reserved numeric loopback socket | Service listener | Bind/start failure publishes no capability; cleanup observable |
| DSH credential provider | Existing unrelated exchange integration | Existing DSH API | Existing Host only | No new call/storage/read in this slice |

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit + actual IPC | Broker/provisioning path, invalid frames/path/permissions, stalled peers and resource ceilings | 4,12 | pytest, existing Node assert tests, temporary Unix sockets | No secret output; no task/socket leak; no token on tuple mismatch |
| SDK ambiguity | All three mutation503 results, correct original recovery and zero retries; GET503 unchanged | 33,34 | Existing Vitest SDK tests | unavailable becomes explicit mutation uncertainty in SDK, with no Host duplicate policy |
| Host integration | Tool schema/runtime guards, opt-in, every success session/env binding, strict no fallback, uncertain result identity | 13 | Actual built Host, mock HTTP/broker, generated SDK | Invalid/control-disabled requests cause0 provider/network/ledger actions |
| UI | Not checked/configured/pending/protected/uncertain/stopped; idle ready:false Start and protected native-alive Stop; no polling/auto-retry, unmount abort | 16,17 | Existing Node/React SSR plus injected fetch/hooks behavior | Action table, exact identity labels and request counts; SSR not claimed to execute effects |
| Process | Prebound port conflict, actual broker/FIFO modes, admission-open failure, cleanup and protected restart | 5 | pytest subprocess, bounded sockets/HTTP | Real server/native PID and listener/socket removal evidence, no forced-kill pass |
| Cross-language native E2E | Built Host→private broker→SDK→actual CLI→risk/store→native process; post-dispatch503 response substitution | 18 | Existing Node TS execution, locked Python, new temporary migrated SQLite | Start, stable request lookup, actual native evidence, SDK503 uncertainty then original-request recovery, Host close survival, explicit SIGTERM cleanup |
| Installed owner/auth UI | Physical carrier refuses unauth/cross-origin/non-owner access and displays status/control correctly | 29,31 | Disposable DSH profile/browser, supported official Plugin Manager | Actual observed authenticated success and denial; source/mocks alone incomplete |
| Engineering | Strict TS/source cap, Python checks, schemas unchanged, real Nx targets, packed Bundle/security/SBOM | 19–21,32 | Existing root and Python gates | Actual exit0; no skipped required process case or inferred remote CI |

The real post-dispatch503 probe in18 uses an SDK test transport wrapper: forward one submit to the actual service, require its202 durable/native command receipt, then substitute a valid synthetic503 `PaperError` response to the SDK. Assert outcome_uncertain/query-original-ID, one POST only, and query the actual service by that original ID to recover the same command/native identity and real state. Keep the private provider callback in test-process memory; print only allowlisted assertions. This is an explicit injected response failure, not a claim that production503 can be reproduced without fault injection. Together with the independently inspected real API failure chain and SDK unit cases, it proves recovery after side effects without adding a production fault-injection route.

Bounded task sequence: B0 independently repair/review current shutdown regression; B1 implement broker, SDK503 fix and TS provider/facade in separate files; B2 register Tools/bridge and Client using the settled protocol; B3 integrate commands/CI and real process E2E; B4 independent review, installed auth/UI receipt, aggregate gates and SDD release. UI can develop against the fixed bridge while Python/Host work proceeds; E2E waits for all settled implementations. IPC tests explicitly cover canonical golden frames, split frames, delayed extra frames and no-EOF peers in both directions.

Planned actual commands, not executed by this design: `node apps/dsh-plugin/test/paper-capability.ts`; `node apps/dsh-plugin/test/paper.ts`; `node apps/dsh-plugin/test/client-paper.ts`; `uv run --project python --locked pytest python/apps/quant-engine/tests/test_paper_capability.py python/apps/quant-engine/tests/test_paper_capability_process.py -q`; `pnpm exec nx run @bybit-quant/dsh-plugin:test:paper-process --skip-nx-cache`; `pnpm run verify`; `pnpm run typecheck:tests`; `pnpm run python:lint`; `pnpm run python:typecheck`; `pnpm run python:test`; both existing OpenAPI --check targets; `pnpm run security:deps`; TS/Python SBOM; changed-file/history secret scans. Use task-local UV cache if sandbox requires it. Root owns precise final aggregate commands, release checks and failure records.

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Disabled/missing config or control opt-in | Host config check | Fixed paper_disabled/control_disabled;0 provider calls | Explicit correction only | Nonsecret configured/control booleans |
| Unsafe/unavailable socket, bad protocol/tuple | Private provider | capability_unavailable, close connection; never raw value/exception | No automatic retry | Fixed provider failure code/count |
| Broker saturation/stall | Pre-admission active bound/deadline | Refuse/close, bounded task cleanup | No | Active/rejected count, no payload |
| Successful GET wrong session/env | Facade binding | invalid_response, no trusted data | No | Safe mismatch code |
| Mutation wrong session/malformed/timeout/cancel/close | Facade/SDK | Preserve outcome_uncertain with original query_request/query_status | Query only | Safe cause/opaque identity |
| HTTP401/403/409/422 | SDK validated failure | Preserve fixed auth/forbidden/conflict/invalid code | No mutation retry | Existing safe SDK result |
| Mutation503/unavailable, including after dispatch | Existing SDK uncertain() | outcome_uncertain, cause unavailable, original query_request or query_status | Query only; never resend | Safe cause and recovery identity |
| Observation503/unavailable | Existing SDK GET | Preserve unavailable/status503 | No automatic retry | Existing safe SDK result |
| Port occupied/service open fails | CLI before disclosure | Exit fixed failure, no broker token; close owned resources | Operator correction | Fixed startup outcome |
| Persistence/native shutdown failure | Existing service | Remain protected/uncertain; cleanup in finally; no stopped claim without proof | Explicit recovery | Existing native/ledger codes; PID/listener evidence |

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `paperBaseUrl` | Canonical numeric loopback HTTP root | Operator config; default `http://127.0.0.1:8766` only when integration configured | No | Separate from market `engineBaseUrl` |
| `paperSessionId` | Current generated opaque grammar | Required operator config | No | Fixed authority; never selected by Tool |
| `paperCapabilitySocket` | Absolute private Unix socket path | Required operator config; absent disables integration | No | Does not contain token material |
| `paperControlEnabled` | boolean | Operator config, false | No | Code-side opt-in for start/stop/submit |
| CLI `--capability-socket` | Private Unix path | Explicit mutually exclusive mode | No | Generates process-memory capability |
| CLI `--capability-fd` | FIFO FD≥3 | Existing explicit mutually exclusive mode | No | Existing trusted private-pipe contract retained |
| Capability |32–128 printable ASCII bytes | Service memory only; generated mode uses48 random bytes base64url | Yes | No config/env/file/Tool/UI/log exposure |

Partial configuration or wrong types fail fixed invalid_config before reading unrelated legacy credential settings. No default socket discovery, token generation by the Host, automatic service launch or managed-profile edit. Bootstrap DB/session/policy remain trusted existing service settings; this slice adds no policy/balance tuning.

## Security Considerations

- Never read actual credential files or `.env` in development/tests. Tests explicitly configure a nonexistent legacy credentialsFile and use a sanitized synthetic process environment. Paper provider imports no legacy secret resolver or credentials script.
- Source boundaries are distinct: DSH secure exchange credentials, legacy fallback files and ephemeral paper IPC capability are not aliases. New paper code cannot call a private Bybit method or trust an exchange key as a paper token.
- Numeric loopback HTTP and owner-only Unix permissions constrain this local design; do not expose the broker through a network port or raw unauthenticated DSH route. Same-user code compromise is outside the boundary; no invented OS peer-attestation API is assumed.
- Provider and HTTP errors are fixed codes. Never serialize config/provider closures, request headers, handshake frames, capability-bearing errors, masked token previews or native account objects into Tool/Client/logs. Synthetic-token leak tests inspect captured output privately and print only allowlisted results.
- Model/Agent/user prose is untrusted evidence; schemas reject unknown fields and cannot grant control, switch session/environment, set risk truth or load generated code. Existing Python risk/reservation/native authority remains unchanged.
- Uninstall/upgrade does not delete the service DB/history/socket directory or revoke state by overwriting user files. Runtime socket cleanup belongs solely to its creating service; service/operator shutdown governs ephemeral capability lifetime.

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | Fixed-code setup/auth/scope/timeout/close records | Diagnose boundary failures without token/frame/payload/config dumps |
| Broker health | Active/rejected/deadline/closed counters in private diagnostic tests; no secret health fields | Prove resource limits and cleanup |
| Native state | Generated `PaperStatus`/`PaperCommand` only | Actual synthetic/session/state/native-process/reservation facts |
| Request correlation | Existing opaque request/command/native IDs |202 vs native acceptance/fill vs uncertainty, no false completed status |
| Lifecycle evidence | Host client-close, service PID, native PID, HTTP listener, Unix inode | Demonstrate independence and completed cleanup distinctly |

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| AT-001/002, real TS/Nx boundaries | Existing projects; manifest6–21; source≤500 | Strict types, Nx target graph, source cap |
| AT-003/006, lifecycle/preservation | No Host service ownership/DB overwrite; official isolated lifecycle remains separate | Disposable-profile receipt; no broader completion inference |
| AT-004/016, environment isolation | Fixed internal_paper session and no exchange call | Wrong tuple/result rejected; zero private-exchange calls |
| AT-007/021, untrusted inputs/independent risk | Strict proposals; service-owned context/risk unchanged | Spoofed args rejected, real service risk veto remains observable |
| AT-010, independently running service | Service-owned broker/listener; Host close-only | Actual Host-close survival and operator SIGTERM cleanup |
| AT-013, sole wire source | Existing SDK-generated paper types | Both existing schema/SDK drift checks unchanged |
| AT-014/015/029, native IDs/durable uncertainty | Existing admission/ledger plus facade recovery binding | Same request stable identity/conflict, query-original, protected restart |
| AT-022, stop distinction | Stop freezes/stops native; no flatten/reconciliation claim | Native liveness/cleanup; full emergency acceptance remains open |
| AT-027/028, DSH Tools/Dashboard | Five Tools and native-paper card | Owner/auth bridge, Client states, installed smoke |
| AT-005/008/009/031, real receipts | Fixed boundary signals, bilingual docs, scans/CI | Root/Python/security/SBOM/release records; full matrix remains incomplete |
| Full strategy/AI/research/recovery and TS exchange cutover | Explicitly excluded from this increment; retained mandatory scope | Separate future designs/acceptance, never certified here |

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Current shutdown regression | Orphan native process/false cleanup | Independent repair prerequisite; repeat uncached actual process gates | No acceptance from old passing snapshot |
| Same-user hostile process | Can access local IPC/user-owned secrets | Explicit same-user boundary; permissions/symlink/inode checks | Not process attestation or OS account compromise protection |
| HTTP port reuse | Token sent to unrelated listener | Prebind listener before broker disclosure, no capability cache | Same-user replacement broker remains trusted OS-user risk |
| SDK callback lacks AbortSignal | Late provider/socket after cancellation | Provider500ms hard bound, close destroys sockets, SDK abort prevents HTTP send | Unit/process tests must prove no leaked handles |
| Exact-route body buffering | Excess memory for tiny controls | Supported streaming mode +512-byte2s local bound | Physical carrier/auth gate still needs installed evidence |
| Native fixture expires/protected restart | Users infer executable market/recovery | Display actual readiness, no refreshed timestamps/reset/session switch | Full replay/recovery remains unavailable |
| Distinct legacy/native paper and exchange routes | Confusing authority | Explicit source/session/synthetic labels and narrow new entry | TS exchange bypass remains open separate cutover |

### Eight-row software-design-philosophy assessment

Current **integrated DSH→native-paper boundary:5/10 (4/8 supported)**; this is not a re-score of the independently accepted read-only/SDK/native modules. Proposed design target **10/10 (8/8)**; implementation score requires independent review and real gates.

| Diagnostic | Current | Required change / target evidence |
|---|---|---|
| Each module describable in one sentence | Pass | Components table preserves one concern per boundary |
| Interfaces simpler than implementation | Fail | One facade hides socket security, auth, session checks and uncertainty |
| Implementation change does not affect callers | Fail | Tools/UI consume facade/generated results, never broker/native formats |
| Interface comments describe abstraction | Fail | Comment private lifecycle, fixed-session and no-retry promises before implementation |
| Design discussion in reviews | Pass | Existing independent reviews; new review must inspect this protocol/authority contract |
| Every module hides an important decision | Pass | Existing transport/native/admission; new provider owns IPC trust, facade owns authority |
| Newcomer understands boundaries without implementation | Fail | Native/legacy labels, independent service recipe, explicit paper/Testnet distinction |
|10–20% deliberate design improvement | Pass | Concrete pre-build design/inspection, no speculative supervisor/package fleet |

All four failed current rows have a concrete owner/file/gate in the manifest. Do not claim the document alone raises the implemented score. Review must reject shallow forwarding-only wrappers: `engine-paper` earns its boundary through authorization, fixed identity and ambiguity policy; `paper-capability` owns filesystem/protocol/deadline/resource complexity.

## Advisor Ledger

Formal independent pre-build review: `sdd/reviews/REVIEW_DSH_PAPER_DESIGN_2026-11-17.md`, initial HOLD for R1/R2 and R3 clarification. All dispositions below are applied in this revision; independent recheck remains pending and is not presumed ACCEPT.

| # | Note | Severity | Decision | Evidence |
|---|---|---|---|---|
| R1 |503 may follow durable/native side effects; SDK must preserve mutation uncertainty | MEDIUM | APPLIED | Manifest33–34 assign existing SDK owner; Code Patterns/Error Handling distinguish mutation503 from GET503; test18 requires actual post-dispatch503 response failure and original-ID recovery |
| R2 | First-LF validation cannot reject delayed trailing frames without a completion rule | MEDIUM | APPLIED | Decision3 defines provider request half-close, broker requestEOF before disclosure, provider responseEOF before trust, shared500ms/1024-byte bounds and split/trailing/no-EOF tests |
| R3 | ready is not lifecycle permission; idle must allow Start and protected native-alive must allow Stop | LOW | APPLIED | Explicit panel action table and required UI tests; stopped/protected cannot Start, no reset/recovery claim |

Parent's earlier fixed-session, prebound listener, pre-task saturation refusal and provider-close constraints remain incorporated. Design acceptance and implementation/native/installed-auth/release acceptance remain separate.

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
|1.0 |2026-11-17 | paper_dsh_design | Scoped DSH native-paper contract, real installed API evidence, private broker provisioning,32-file acyclic manifest and acceptance gates |
|1.1 |2026-11-17 | paper_dsh_design | Applied independent R1–R3: existing SDK503 uncertainty owner/files,34-file DAG, EOF handshake and lifecycle action table; recheck pending |
|1.2 |2026-11-20 | dashboard/AI decision boundary | Supersedes the earlier card-level Start/Stop wording: the dashboard and browser bridge are observation-only; model-facing paper Tools retain separate explicit default-off controls. |

## Next Step

Execute o **SDD Build by RDD**.
