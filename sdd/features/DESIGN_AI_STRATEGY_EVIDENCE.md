# DESIGN: AI strategy research evidence bridge

Date: 2026-11-20. Status: implementation slice; research-only, no execution authority.

## Problem

The Python workspace contains deterministic strategy-family evaluators and a
metadata registry, while the DSH background decision loop currently sees only
the plugin's market brief. The evaluator and registry are not connected to the
AI research turn. Built-in strategy records are all `research/not_started`, so
none is eligible for validated strategy selection or deployment.

## Outcome and boundary

Detailed `quant_brief` results will include bounded, read-only signals from the
Python strategy-family evaluator for the AI-selected symbol. The DSH Host
fetches the candles itself, then sends a strictly validated snapshot to the
loopback quant-engine research endpoint. The Python endpoint evaluates only
registered built-in default configurations and returns each signal alongside
its lifecycle and validation state.

The AI continues to choose whether to act, which eligible symbol to analyze,
and all simulated decision parameters. The dashboard remains view-only. The
returned target exposure is labeled as research evidence and is never converted
to a portfolio target or order. In this increment all built-ins remain
ineligible because their status is `research/not_started`; the output must say
so explicitly. No repository code is downloaded or executed at runtime.

## Contract

`POST /api/v1/research/strategy-evidence` accepts one symbol, `spot` or
`linear`, one supported Bybit interval, at most 1,000 oldest-first OHLCV bars,
and an optional bounded funding rate. Unknown fields, malformed bars,
duplicate/out-of-order timestamps, unsupported markets, and oversized bodies
fail closed. The endpoint performs bounded deterministic CPU work and has no
account, credential, database-write, network, or exchange-order dependency.

The response contains the requested market context, the newest bar timestamp,
and a bounded list of family results: strategy ID/version, repository/license
metadata, supported market, lifecycle and validation status, `ready`, a
research-only target exposure when ready, and typed feature values. No result
is marked approved or execution-eligible by the endpoint. API failures are
returned to `quant_brief` as `unavailable`; they do not fabricate a signal.

The engine accepts caller-supplied market evidence and does not authenticate
its origin. Loopback binding limits network reachability; input validation and
the result label still treat the snapshot as untrusted evidence. The DSH tool
only submits bars it fetched for a symbol in the current fresh AI candidate
snapshot. Dashboard controls are not arguments to this flow.

## Data flow

1. Background Agent calls `quant_brief` without symbols and receives the fresh,
   dynamic eligible universe.
2. Agent chooses up to four symbols and calls `quant_brief` with that subset.
3. The Host revalidates those symbols against the current universe, fetches the
   primary timeframe bars/funding rate, and calls the loopback engine endpoint.
4. The engine evaluates the bounded snapshot with the registered built-ins and
   returns research-only signals plus validation metadata.
5. The Agent may cite those signals only as research evidence. They do not
   confer strategy approval, alter the deterministic risk gate, or authorize
   an exchange action. The existing tool can still write only a local
   simulated decision with a cycle-bound receipt.

## Failure behavior

Missing engine service, rejected request, timeout, or invalid response produces
an explicit `unavailable` research-evidence status. The market brief remains
available, but the prompt must not claim that a Python strategy was evaluated
or validated. A short/empty/stale bar window produces explicit not-ready family
results; there is no static symbol or signal fallback. AI simulation decisions
remain distinguishable from validated strategy deployment.

## File manifest

| Path | Change |
|---|---|
| `python/apps/quant-engine/src/quant_engine/strategy_evidence.py` | Create a pure bounded evaluator over registered built-in metadata |
| `python/apps/quant-engine/src/quant_engine/api.py` | Add strict request/response schemas and the read-only endpoint |
| `python/apps/quant-engine/tests/test_strategy_evidence_api.py` | Cover deterministic output, research-only status, invalid bars and bounds |
| `python/apps/quant-engine/tests/test_service.py` | Assert route shape and endpoint behavior without network access |
| `contracts/openapi/quant-engine.v1.json` | Regenerate the engine API contract |
| `packages/ts/quant-api-client/src/index.ts` and `validation.ts` | Add a bounded generated-contract client method and response validation |
| `apps/dsh-plugin/src/lib/engine.ts` | Expose strategy evidence through the existing loopback engine boundary |
| `apps/dsh-plugin/src/lib/ai-market.ts` | Attach optional research evidence to detailed briefs without duplicate candle fetches |
| `apps/dsh-plugin/src/host-tools-ai.ts` | Request evidence only for symbols revalidated against the fresh universe |
| `apps/dsh-plugin/src/prompts/bybit-quant/v3.ts` | Versioned successor to the active one-shot Host system prompt; explain the research-only evidence boundary |
| `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v4.ts` and `LOOP_SPEC-v5.md` | Versioned successor to the active background loop prompt/spec; explain how to interpret strategy evidence without changing candidate choice, risk, or authority |
| `apps/dsh-plugin/src/host-runtime.ts` and `apps/dsh-plugin/src/lib/ai-scheduler.ts` | Switch imports to the versioned prompt successors |
| `apps/dsh-plugin/test/*` | Verify the AI-selected symbols, evidence labels, and unavailable behavior |
| `sdd/features/DEFINE_BYBIT_AI_QUANT.md` | Add an acceptance criterion for the evidence boundary |
| `sdd/reports/BUILD_REPORT_AI_STRATEGY_EVIDENCE.md` | Record exact verification receipts and remaining strategy/runtime gaps |

## LLM Prompts

The parent DEFINE sets `LLM Prompts: true`. The runtime uses DSH's injected
default Agent model; this slice does not select a provider or model.

| ID | Name / path / version | Type / consumer | Input → output | Closed decisions and fallback | Reference material | Completeness / refactor |
|---|---|---|---|---|---|---|
| LP-001 | Bybit quant Host system / `apps/dsh-plugin/src/prompts/bybit-quant/v3.ts` / v3 | `one-shot`; `host-runtime.ts` | Existing tools and one user turn → normal assistant answer or tool calls | Dashboard is view-only; exchange execution unavailable; research result never approves deployment or changes risk; missing/invalid evidence is unavailable | Contract below; active v2 prompt and this DESIGN's Outcome, Contract and Failure behavior | All evidence claims must be grounded in tool results; versioned refactor of active v2 |
| LP-002 | Background simulated research / `apps/dsh-plugin/src/prompts/bybit-quant/background-loop-v4.ts` / v4; `LOOP_SPEC-v5.md` | `loop`; `lib/ai-scheduler.ts` | Fresh candidate-universe tool result and up to four selected-symbol briefs → zero to four cycle-bound local simulated proposals or no receipt | AI chooses the subset; evidence can be cited only as research; no target exposure is an instruction; no promotion, risk bypass, exchange write, or static fallback; absent evidence stays unavailable | Contract below; active background-loop-v3 prompt, `LOOP_SPEC-v4.md`, and this DESIGN's Outcome, Contract, Data flow and Failure behavior | Preserve one-cycle limits/receipt verifier; add the evidence boundary; versioned refactor of active v3 |

### Contract by prompt

| ID | Tone / audience | Output type | Approved fallback | Autonomous? | Internal verification | Minimum pre-ship evaluation |
|---|---|---|---|---|---|---|
| LP-001 | Concise, factual, user-facing | DSH tool calls and natural-language answer; no new JSON format | Omit unavailable evidence claims and state `unavailable`; market brief remains usable | Yes, within the existing tool permissions | Check candidate eligibility and distinguish market facts, strategy research, simulation, and exchange execution | Fixture-backed prompt contract assertions plus an independent model review of cases with fresh/not-ready/unavailable evidence; no profitability inference |
| LP-002 | Concise, tool-oriented, one bounded cycle | Zero to four tool-mediated simulated proposals, with a persisted cycle receipt only on successful local write; otherwise no receipt | Continue without a Python signal when evidence is unavailable; abstain on missing/stale candidate data | Yes, bounded by existing LOOP_SPEC and scheduler | Code-owned tool, candidate, risk, receipt and lifecycle checks remain authoritative | Deterministic prompt assertions and an independent model review of candidate-choice, unvalidated exposure, unavailable evidence, and abstention cases; no profitability inference |

### Evidence contract injected through `quant_brief`

```json
{
  "strategyEvidence": {
    "status": "available | unavailable",
    "research_only": true,
    "deployment_eligible": false,
    "snapshot_status": "fresh | stale | empty",
    "strategies": [{
      "strategy_id": "string",
      "lifecycle_status": "research",
      "validation_status": "not_started",
      "ready": "boolean",
      "research_target_exposure": "number | null",
      "reason": "string",
      "features": "bounded typed feature values"
    }]
  }
}
```

This is evidence after the AI selects a fresh eligible symbol. It cannot select
the symbol, approve a strategy, set a portfolio target, replace the decision's
thesis/invalidation, alter code-owned risk, or authorize execution. Source
metadata and the complete response remain available in the tool result. Current
built-in registry status is `research/not_started`; any future status change
still does not change the endpoint's `deployment_eligible=false` contract.

### Prompt-builder and loop-builder receipts

LP-001 is compiled by `sdd-prompt-builder` from the contract above; LP-002 is
compiled by `sdd-loop-builder` as LOOP_SPEC v2 before its stage prompt is
compiled by `sdd-prompt-builder`. Runtime provider/model selection stays with
DSH. The prompt gate is not a strategy-quality gate: independent model review
remains required before release, and no profitability ground truth is implied.

## Verification gate

Run the focused Python strategy/API tests and type/lint checks, regenerate and
check the OpenAPI-derived SDK, run the DSH plugin Verify Gate and repository
Verify Gate, then record the Python test count, Nx graph, SBOM, dependency scan,
secret scan, and `git diff --check` outcomes. These checks do not prove strategy
profitability, independent OOS validation, persistent selector state, portfolio
allocation, or exchange execution.
