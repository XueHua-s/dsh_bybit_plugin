# DESIGN: Internal-paper documentation integration

Date: 2026-11-17. Feature family: BYBIT_AI_QUANT. Documentation-only scope.

## Pre-edit manifest

| File | Action | Purpose |
|---|---|---|
| `sdd/features/DESIGN_PAPER_DOCS.md` | Create first | This manifest, boundaries and real documentation checks |
| `README.md` | Update | English paper capability boundaries, licensing exception and current evidence |
| `README.zh-CN.md` | Update | Equivalent Chinese capability and licensing explanation |
| `sdd/features/DESIGN_BYBIT_AI_QUANT.md` | Append | Settled paper process/admission/schema boundary and design drift |
| `sdd/handoffs/HANDOFF_BYBIT_AI_QUANT.md` | Update | Current state, future work and verified continuation |
| `sdd/reports/VERIFY_GATE_2026-11-17.md` | Prepend | Scoped paper receipts without replacing historical gates |
| `docs/runbooks/paper-service.md` | Create after verified CLI/FD contract | Safe process lifecycle and credential-free synthetic-fixture operations |

## Input and current status

Published baseline605fe709461e7157885da07216654a1da677926c has parent-verified
CI44081766003 success for both jobs. The new paper integration is local and
under independent review; no final acceptance or current aggregate pass is
inferred. Final economic-model and parent-death cleanup corrections can change
its contract; integration text waits for settled contracts/receipts.

Scoped design sources: `DESIGN_PAPER_NATIVE.md`, `DESIGN_ADMISSION_STORE.md`,
`DESIGN_PAPER_ADMISSION.md`, `DESIGN_PAPER_SDK.md`,
`DESIGN_PAPER_WORKSPACE.md`, and the parent execution-cutover design.

## Information ownership and drift

Native runtime owns a spawned process/TradingNode lifetime and synthetic finite
liquidity; admission owns trusted paper state/risk/reservations; the data package
owns durable sessions/reservations/native audits and packaged Alembic resources;
Python paper OpenAPI owns command wire types; generated SDK hides authenticated
bounded transport. The default market app still has only two read-only routes.

A separate process replaces the earlier proposed native thread because native
signal/main-thread behavior conflicted with API-loop ownership. This must be
recorded as design evolution with concrete implementation/review evidence.
Spot cash versus perpetual risk equity is a review finding being corrected;
this documentation must not certify the intermediate economic mismatch.

`paper_sandbox.py` is adapted LGPL-3.0-only code. Its package LICENSES/NOTICE and
mixed MIT/LGPL metadata must be described explicitly in both READMEs; the root
MIT notice does not relicense that file or every dependency.

No exchange connection/order/trade, DSH mutation cutover, full strategy/AI/
generated-code/research acceptance or Mainnet readiness is implied. Preserve
all original MUSTs and private-state/recovery limitations. No dependency, lock,
source, credential or user-database edit belongs to this documentation task.

## Complexity diagnostic

Documentation score target9/10: boundaries and design intent have a single
source per concern, while main entry points summarize operational consequences.
Failed row: complete newcomer understanding cannot be verified until the final
native economic model, process cleanup and authenticated CLI/FD contract settle.
Resolve through accepted contracts and reproducible receipts, not duplicate
implementation/API detail in the README.

## Verification

Initial repository/docs status/design reads exit0. Bilingual local links and license/boundary term parity checked0 on the initial
pass; `git diff --check`0. Native/admission/SDK scoped ACCEPT and actual compiled
SDK process E2E now inform the CLI/FD runbook. Independent E2E owner extracted the exact launcher heredoc, parsed AST0 and
executed no-submit native start/stop in locked environment0; only allowlisted
synthetic_native_start_stop_ok output. External PID/listener proof remains
attributed to the separately executed hashed process probe. Final parent fullPython252, root/TS/format/types/schema/security/SBOM/scanners
and license-artifact receipts integrated in Verify Gate, scoped verified/overall
PARTIAL. Current paper delta remains uncommitted/unpushed.
Primary orchestrator remains parent; future delegated children use the user's
explicit gpt-6.1-sol/medium/fork-none choice, not a primary-model change.
