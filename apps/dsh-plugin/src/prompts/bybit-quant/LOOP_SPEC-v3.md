# LOOP_SPEC v3 — AI background decision cycle

This file records the v3 decision-write contract and the active
`background-loop-v3.ts` machine prompt. Scheduler creation, turn, and cleanup
timing is specified by the superseding lifecycle contract in `LOOP_SPEC-v4.md`.
The active prompt remains unchanged; the prompt-evaluation gate and unattended
exchange trading are not complete.

This file is the auditable loop contract for `background-loop-v3.ts`. It is a
bounded, default-off, simulation-only cycle; it has no exchange order authority.

## Intent and damage model

The cycle discovers a fresh eligible candidate universe, lets the default DSH
model request evidence and propose up to four simulated decisions, and writes a
receipt only after the local simulated journal/book persists successfully. A
false-positive simulated position is the larger error, so missing, stale,
ambiguous, or unsupported evidence fails closed to abstention.

## Control state

The scheduler owns an opaque cycle ID, active/closed state, pending and
committed receipt counts, normalized symbol keys, failure count, timestamps and
last persisted decision ID/status in process memory. The AI track is persisted
by the existing atomic local state store. A cycle ID is invalid after closure or
process restart; no cross-restart cycle continuation exists.

## Cycle protocol

`SNAPSHOT → PROPOSAL → PRE-WRITE VALIDATION → LOCAL SIMULATED WRITE → RECEIPT
VERIFICATION → CYCLE CLOSE`.

`quant_brief` without symbols performs discovery. The model may request detailed
`quant_brief`/`quant_signals` evidence for up to four selected candidates. The
only write action is `quant_decide_background`, which requires the exact cycle
ID. `quant_decide` is the ordinary conversation tool and rejects `cycleId`.

## Deterministic verifier and limits

The code verifies AI enablement, Testnet/internal-paper environment, candidate
eligibility, schema, risk limits, one write per normalized symbol, at most four
writes per cycle, successful state persistence, and receipt idempotency. A
concurrent same-symbol request is pending; a retry after persistence returns the
original receipt without another journal write. Persistence failure restores the
previous track and releases the reservation.

## Recovery, budget, and stop rules

The Agent turn receives at most 1,600 tokens and each Tool invocation has a
20-second timeout. Scheduler failures back off at 2× then 4× the interval,
capped at one hour, and block after three consecutive failures. There is no
same-cycle data retry or static fallback. Terminal states are disabled,
environment/configuration rejected, completed with receipts, completed without a
receipt (`no_decision_receipt`), failed/backoff, blocked, or stopping on unload.

## Tool boundary

The allow-list is `quant_brief`, `quant_decide_background`, `quant_review`,
`quant_signals`, `bybit_market`, `bybit_instruments`, and
`quant_get_market_snapshot`. Exchange/account/watchlist/paper-control/credential
tools are excluded. The panel's symbol/category/timeframe filters never enter
the cycle context.

## Verify gate

Run the plugin contract and unit suite, including discovery failure/empty
universe, stale or missing cycle ID, ordinary-tool cycle-ID rejection,
duplicate-symbol and four-write limits, persistence failure recovery, and active
v3 prompt/tool registration. An independent model evaluation over those cases is
required before the SDD LLM prompt gate can be marked complete; no market
performance ground truth is available in this build.
