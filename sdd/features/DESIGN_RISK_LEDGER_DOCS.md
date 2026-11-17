# DESIGN: Risk and command ledger documentation integration

Date: 2026-11-17. Feature family: BYBIT_AI_QUANT. Scope: documentation only.

This supplement integrates `DESIGN_QUANT_RISK.md`, `DESIGN_COMMAND_LEDGER.md`
and `DESIGN_RISK_WORKSPACE.md` into the existing bilingual entry points and
aggregate handoff. Their implementation/review receipts remain authoritative;
documentation does not confer runtime execution authority or product acceptance.

## Pre-edit manifest

| File | Action | Purpose |
|---|---|---|
| `README.md` | Update | English package boundaries, verified baseline and limitations |
| `README.zh-CN.md` | Update | Matching Chinese package boundaries and limitations |
| `sdd/features/DESIGN_BYBIT_AI_QUANT.md` | Append | Risk/ledger architecture ownership and incomplete integration |
| `sdd/handoffs/HANDOFF_BYBIT_AI_QUANT.md` | Update | Aggregate state, historical receipts, concrete continuation |
| `sdd/reports/VERIFY_GATE_2026-11-17.md` | Prepend | Current scoped outcomes without overwriting old receipts |
| `sdd/features/DESIGN_RISK_LEDGER_DOCS.md` | Create first | This auditable manifest and documentation verification receipt |
| `sbom.python.cdx.json`, TS SBOM artifacts | Regenerate, parent owner only | Current dependency/component receipts after lock changes |

## Ownership and drift

The risk package owns deterministic validation/portfolio veto; the data package
owns canonical command identity, durable lifecycle and local concurrency. Future
execution integration must own atomic risk reservations, audit and sole Nautilus
submission. Pure approval and a local ledger are not an unbypassable final gate.
Existing direct TS REST orders remain DRIFT-ORIGINAL-003 until a separately
reviewed cutover. Full strategy/AI/research/account/private-state requirements
remain open. No code, credentials, target database migration or commit belongs
to this documentation task.

Published baseline supplied and independently verified by parent:
`566092aa8ace2aff354469e8d01638e0bcfdd7d7`, hosted CI run44077034140 both jobs
successful. Earlier code4360381 receipts remain historical. New local risk and
ledger scoped ACCEPTs, Python213, security0/four skipped editables and SBOM200/91
receipts are integrated from final parent evidence. This delta is unpublished.

## Complexity diagnostic

Score: 9/10 for documentation integration. Boundaries, design intent, policy and
persistence ownership are explicit; implementation decisions stay in their
scoped design documents. Failed row: newcomer understanding of the complete
execution boundary cannot yet be established because the integrated runtime is
unfinished. Resolve with a reviewed engine-owned risk/reservation/submission
contract and concrete cutover evidence, rather than duplicating low-level APIs
in README files.

## Verification

Initial AGENTS/skills/design/README/handoff/Verify reads: exit0. Python heredoc
checked both README relative Markdown targets exist and both languages retain
risk/ledger designs, baseline566092a/CI44077034140, quant-risk and fsspec2026.6.0:
exit0. `git diff --check` after integration: exit0. Parent-supplied scoped,
aggregate and scan receipts are recorded with limits in Verify Gate; no inferred
hosted CI for this unpublished delta. Final secret/diff rescan belongs to parent
release checks. Handoff preserves historical receipts via Verify and records the
user's future-subagent model choice without changing the primary chat model.
