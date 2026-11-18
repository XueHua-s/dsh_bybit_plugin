# DESIGN: TypeScript Exchange Mutation Closure

> A bounded safety cutover that removes the TypeScript exchange writer while the native execution authority is not connected.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | TS_MUTATION_CLOSURE |
| **Date** | 2026-11-19 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| **DEFINE** | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| **UX REVIEW** | N/A |
| **LLM Prompts** | true |
| **Status** | Built for bounded cutover; full product remains partial |

---

## Architecture Overview

```text
DSH model
   │
   ├── reads / account queries ──> explicit BybitClient GET operations
   │
   ├── bybit_trade preview ──────> validated local preview + public/read-only data
   │                                  └── dryRun:false -> fixed unavailable result
   │
   └── internal paper tools ────> existing Python paper API / simulated state

BybitClient private signer: named signed GETs only
Exchange order writes: unavailable until a separately designed native authority is connected
```

---

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| Signed read client | Hide signature construction behind named read operations | TypeScript private method; GET-only transport | Trusted environment and resolved credentials | Account identity, wallet, positions, open orders | Existing Bybit read DTOs |
| Trade preview tool | Preserve validated intent previews without a writer | DSH Host tool | Model action and order parameters | Preview or fixed unavailable status | Public market data and instrument metadata |
| Readiness UI | Explain that exchange writes and background automation are unavailable | DSH Client panel contract | Host status DTO | Bilingual status badge and boundary card | Host panel route |
| Versioned system prompt | Keep model behavior aligned with the reduced tool capability | Static one-shot system section | Tool and environment facts | Conversation/tool-use instructions | DSH system prompt API |

---

## Key Decisions

### Decision 1: Remove every TypeScript exchange mutation path

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-19 |
| **Source** | DEFINE MUST (Nautilus sole execution authority); `NATIVE_TESTNET_CUTOVER_GAPS_2026-11-17.md`, subsequent dependency order 1 |

**Context:** `host-tools-trade.ts` can submit create/close/cancel/cancel-all through Bybit REST, and `BybitClient.signedRequest(method, path, params)` exposes arbitrary signed POST construction. The native engine does not yet own exchange execution.

**Choice:** Delete public TypeScript mutation methods and generic signed POST transport. Keep signing private to the four named signed GET reads. `bybit_trade` remains preview-only; `dryRun: false` returns a fixed unavailable result before any Bybit request. No TS REST fallback is provided when the engine is unavailable.

**Rationale:** This closes the alternate writer with no account access or exchange side effect and prevents dual execution authority.

**Alternatives Rejected:**
1. Keep the writer behind environment flags or confirmation fields — these do not prove native admission, final risk or reconciliation.
2. Route to the current paper API and call it exchange execution — internal paper is synthetic and has no Bybit authority.

**Consequences:** Exchange create/cancel/close is unavailable until a separately designed and verified native path exists. Product acceptance AT-014 remains pending.

### Decision 2: Keep preview, read and internal-paper behavior distinct

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-19 |
| **Source** | DEFINE AT-016 and AT-028; current plugin UI and tool contracts |

**Context:** Existing UI, plugin defaults, README and system prompt imply that several switches can enable real orders, which will no longer be true.

**Choice:** Remove obsolete trade-enable defaults from the Bundle patch and runtime settings; return `executionAuthority: unavailable`; label the panel and tool as preview-only; update English and Chinese user-facing docs. Keep account reads and internal synthetic paper labeled separately.

**Rationale:** Operators should not infer execution readiness from OAuth, API keys, Testnet selection, a successful preview or a healthy market feed.

**Alternatives Rejected:**
1. Keep `allowLiveTrading`/`allowTestnetTrading` toggles as if they work — misleading and unsafe.
2. Remove account reads with the order writer — unnecessary loss of read-only capability.

**Consequences:** Existing legacy write-enable keys are ignored. The preview ceiling remains a preview-only validation and grants no execution capability.

---

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `apps/dsh-plugin/src/lib/bybit.ts` | Modify | Restrict private transport and signing to GET; remove order mutations | (general) | None |
| 2 | `apps/dsh-plugin/src/lib/bybit-types.ts` | Modify | Remove mutation-only order input type | (general) | 1 |
| 3 | `apps/dsh-plugin/src/host-tools-trade.ts` | Modify | Keep previews and return fixed unavailable on send intent | (general) | 1 |
| 4 | `apps/dsh-plugin/src/host-runtime.ts` | Modify | Remove obsolete live-send guards and use versioned prompt; correct preview reason | (general) | 5 |
| 5 | `apps/dsh-plugin/src/prompts/bybit-quant/v2.ts` | Create | Versioned system prompt stating preview-only execution boundary | (general) | None |
| 6 | `apps/dsh-plugin/src/host-panel.ts` | Modify | Report unavailable execution authority and omit stale write switches | (general) | 7 |
| 7 | `apps/dsh-plugin/src/client-types.ts` | Modify | Match the read-only execution-status contract | (general) | None |
| 8 | `apps/dsh-plugin/src/client.ts` | Modify | Replace live-on/off badge with explicit writes-unavailable status | (general) | 9 |
| 9 | `apps/dsh-plugin/src/client-assets.ts` | Modify | Update Chinese/English status and automation text | (general) | None |
| 10 | `apps/dsh-plugin/src/lib/host-config.ts` | Modify | Ignore/remove obsolete exchange-send flags and equity-share guard | (general) | 3 |
| 11 | `apps/dsh-plugin/cordis.patch.yml` | Modify | Remove ineffective order-enable switches; retain preview-only limit | (general) | 10 |
| 12 | `apps/dsh-plugin/src/host-tools-account.ts` | Modify | Remove stale claim that flags enable order sending | (general) | None |
| 13 | `apps/dsh-plugin/src/host-tools-watchlist.ts` | Modify | Remove stale claim that flags enable order sending | (general) | None |
| 14 | `apps/dsh-plugin/src/host-tools-ai.ts` | Modify | Remove stale claim that flags enable order sending | (general) | None |
| 15 | `apps/dsh-plugin/src/host-tools-backtest.ts` | Modify | Correct references to real exchange orders | (general) | None |
| 16 | `apps/dsh-plugin/test/trade-cutover.ts` | Create | Prove all four actions cannot write across env/legacy flags; prove GET-only client | (general) | 1,3 |
| 17 | `apps/dsh-plugin/test/integration.ts` | Modify | Align Host integration expectations with preview-only behavior | (general) | 3,4,5 |
| 18 | `apps/dsh-plugin/package.json` | Modify | Include bounded cutover regression test in unit gate | (general) | 16 |
| 19 | `apps/dsh-plugin/scripts/check-bundle.ts` | Modify | Scan extracted Bundle JS for mutation endpoints and APIs | (general) | 1,3 |
| 20 | `apps/dsh-plugin/docs/DETAIL.md` | Modify | Document preview-only trade tool and no-write status | (general) | 3,9 |
| 21 | `docs/DETAIL.md` | Modify | Keep root detail documentation aligned | (general) | 20 |
| 22 | `README.md` | Modify | State verified order capability and remaining execution gap | (general) | 3,9 |
| 23 | `README.zh-CN.md` | Modify | State verified order capability and remaining execution gap | (general) | 3,9 |
| 24 | `apps/dsh-plugin/src/client-readiness.ts` | Modify | Render execution unavailable, account unknown and background loop stopped as separate facts | (general) | 6,7,9 |
| 25 | `apps/dsh-plugin/src/lib/monitor.ts` | Modify | Keep order count and order latency empty until an execution authority reports actual order events | (general) | 1 |
| 26 | `apps/dsh-plugin/test/oauth.ts` | Modify | Remove obsolete live-write setting expectation; preserve OAuth isolation assertions | (general) | 10 |
| 27 | `apps/dsh-plugin/test/render.ts` | Modify | Match unavailable execution contract in client rendering fixtures | (general) | 7–9,24 |
| 28 | `sdd/reports/BUILD_REPORT_TS_MUTATION_CLOSURE.md` | Create | Record commands, exits, acceptance evidence and remaining gaps | (general) | 16,17,19,25–27 |
| 29 | `apps/dsh-plugin/project.json` | Modify | Include the mutation regression matrix in the Nx unit-test target used by the repository Verify Gate | (general) | 16,18 |
| 30 | `sbom.cdx.json` | Modify | Regenerate the tracked TypeScript dependency inventory as a required verification artifact | (general) | 18,29 |

**Total Files:** 30

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1–30 | The execution boundary, prompt, client contract, Bundle scan and release evidence must be integrated consistently. |

**Agent Discovery:** Repository skill and existing project guidance were inspected. This bounded change uses one owner; independent review is scheduled after implementation.

---

## Code Patterns

### Preview and unavailable contract

```ts
if (args.dryRun === false) {
  return {
    sent: false,
    unavailable: true,
    code: 'execution_authority_unavailable',
    action,
    env: client.env,
  }
}
```

### Signed read boundary

```ts
async #signedGet(path: string, params: Record<string, unknown>, signal?: AbortSignal) {
  return this.#request({ method: 'GET', base: this.tradingBase, path, params, signed: true, signal })
}
```

## LLM Prompts

| # | Path / Runtime | Type | Consumer | Output Shape |
|---|---|---|---|---|
| LP-001 | `apps/dsh-plugin/src/prompts/bybit-quant/v2.ts`, registered as `tool:bybit-quant` | one-shot system section | DSH model using Bybit tools | Free-form response plus tool arguments validated by existing schemas |

**Purpose:** Describe market, backtest, internal-paper, trust-boundary and execution capabilities accurately.

**Tone/Audience:** Concise operational instructions for the DSH model; preserve the existing audience and tone.

**Input shape:** Static tool capabilities, selected environment and untrusted market/news/user-provided evidence.

**Approved fallback:** When asked to send/cancel/close an exchange order, say exchange execution is unavailable and offer the local preview. Never imply that preview, OAuth or API credentials sent an order.

**Reference material:** Existing `ctx.systemPrompt.section` text, `host-tools-trade.ts`, internal paper tool contract, and the execution-cutover decision that no TS fallback exists.

**Settled decisions:** Provider/model are controlled by DSH and are not configured by this plugin. Keep the existing tool schemas; this slice changes no model service or output schema.

**Failure behavior:** If a preview/read tool is unavailable, report that status; do not retry by constructing an exchange request or using a different writer.

---

## Data Flow

```text
1. DSH receives a user request and sees the static preview-only system section.
   │
   ▼
2. A read request uses a named public or signed GET operation.
   │
   ▼
3. A bybit_trade preview validates inputs and may read public rules/prices or current position state.
   │
   ├── dryRun=false -> return execution_authority_unavailable before any exchange request
   └── preview -> return sent=false with an explicit writes-unavailable reason
```

---

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| Bybit public market/read-only account APIs | HTTPS GET | Public requests unsigned; account reads use environment-scoped credentials | Inbound only | Existing bounded timeout and safe errors; no POST, retry or write fallback |
| DSH system prompt and tool registry | Host API | DSH runtime | Plugin to model context | Registration failure follows existing Host lifecycle; no execution activation |

---

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Four actions return fixed unavailable for all environments and legacy enable flags, with zero client calls | `apps/dsh-plugin/test/trade-cutover.ts` | Existing Node test runner | 98 matrix cases pass |
| Unit | Direct BybitClient import has no signer/mutation methods; signed account reads use GET only | `apps/dsh-plugin/test/trade-cutover.ts` | Existing Node test runner and fetch stub | No POST or body observed |
| Integration | Prompt, panel status and trade tool are consistently preview-only | `apps/dsh-plugin/test/integration.ts` | Existing Host fixture | Assertions pass; no order is sent |
| Bundle | Extracted package contains no signed mutation methods or Bybit order-write endpoints | `apps/dsh-plugin/scripts/check-bundle.ts` | Existing `bundle:check` | Archive scan passes |
| Unit | Read-only `/v5/order/realtime` activity is not counted as executed-order count or order latency | `apps/dsh-plugin/test/trade-cutover.ts` | Existing Node test runner | Order metrics remain zero/null |
| Verify Gate | Existing DEFINE plugin regression gate | N/A | `pnpm run verify` | Exit 0; product-level AT-014 remains pending |

---

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Explicit send intent while native authority is absent | `dryRun === false` | Fixed `execution_authority_unavailable`, zero exchange calls | No | Tool result code and panel state |
| Invalid preview input | Existing parser/validation | Return existing validation error | No | Tool result |
| Missing read credentials or Bybit GET error | Existing read client | Existing sanitized `BybitError` | No automatic retry | Existing request metrics |
| Native engine unavailable | Existing engine status | No TS REST fallback | No | Panel labels execution unavailable |

---

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `env` | `live \| demo \| testnet` | Existing Bundle default `testnet` | No | Selects read environment only for this slice; does not authorize order writes |
| `maxOrderNotionalUsd` | number | Existing Bundle default `24` | No | Preview validation ceiling only |
| legacy write-enable keys | unknown | May remain in an existing user profile | No | Ignored by runtime; not emitted as Bundle defaults |

---

## Security Considerations

- No signed POST transport, exchange create/cancel/close API, or engine-down REST fallback remains in the TypeScript Bundle.
- OAuth and account-read credentials do not imply order authorization or execution readiness.
- Unknown legacy config keys must not restore write behavior.
- Build and Bundle tests scan packaged output, not only TypeScript source.
- The existing local read endpoint still uses environment-separated credentials and never includes secrets in panel output.

---

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | Runtime reports `exchangeWrites=unavailable` | Avoid implying config flags enable order sending |
| Metrics | Keep existing read request counts; write latency is `null` | Do not report read-order-query latency as sent-order latency |
| Tracing | N/A for this bounded slice | No order dispatch exists to trace |

---

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| DEFINE Nautilus sole exchange writer MUST | Decision 1; private signed GET only | Unit and extracted Bundle scan |
| AT-004 denied order has no exchange request | `bybit_trade` fixed unavailable branch | Environment/flag/action matrix |
| AT-014 remains required, not implemented here | Explicit consequence and scope limit | Build report remains product PARTIAL |
| AT-016 environment separation | Reads remain bound to configured env; no writes | GET endpoint fixture |
| AT-028 clear Dashboard state | `executionAuthority: unavailable`, bilingual copy | Host integration assertions |
| AT-009 accurate documentation | Bilingual README/detail updates | Build report text checks and `pnpm run verify` |

---

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| User profile retains old `allowLiveTrading`/`allowTestnetTrading` keys | Operator may expect a switch to work | Remove default toggles, ignore all legacy values, show explicit unavailable status | Existing profile may display unknown fields in DSH settings until its next supported update |
| Preview is mistaken for a sent order | False operational state | `sent:false`, unavailable reason, prompt and UI wording, tests | User may still misread a preview; future UI should keep a persistent execution badge |
| Removing the old writer leaves no exchange trading path | Testnet/production order capability remains unavailable | Do not claim product completion; implement reviewed native path in a later phase | Full acceptance remains pending |

---

## Advisor Ledger

None — no formal external design review.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-11-19 | SDD Design by RDD | Defined the bounded TypeScript mutation closure and acceptance matrix. |

---

## Next Step

Execute o **SDD Build by RDD**.
