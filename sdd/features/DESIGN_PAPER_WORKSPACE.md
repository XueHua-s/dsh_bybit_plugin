# DESIGN: Paper admission workspace integration

Date: 2026-11-17. Baseline: `605fe70`. Supplement to the existing project
Brainstorm/Define/Design and DESIGN_PAPER_ADMISSION, DESIGN_PAPER_NATIVE and
DESIGN_ADMISSION_STORE. This slice owns packaging/orchestration evidence only.

## Decisions

The engine's real imports of risk, execution and data require explicit uv
workspace dependencies and actual Nx edges. The engine integration owner edits
its package/project metadata and imports; this worker then resolves and syncs the
root lock as sole owner. No fake dependency edge is accepted. Root dependencies
already install all four packages, so root edits should be unnecessary.

Retain the exact patched `fsspec==2026.6.0` override. The known Nautilus1.231.0
metadata mismatch remains explicit; no downgrade clears it. No new third-party
dependency is expected. Existing CI checks all four Python projects; no CI
change is required unless inspection demonstrates missing coverage.

Fresh package builds inspect engine/native source artifacts and data migration
resources. A missing resource is a real packaging gap to report to its package
owner, not a reason to claim a successful installed runtime. Local offline
artifact/import checks never imply exchange connectivity or trading acceptance.

## File Manifest

| ID | Path | Action | Purpose |
|---|---|---|---|
| PW-01 | `python/uv.lock` | Regenerate after real engine metadata | Actual engine package dependencies |
| PW-02 | `python/pyproject.toml` | Inspect; modify only if necessary | Root workspace orchestration, retain override |
| PW-03 | `.github/workflows/ci.yml` | Inspect; modify only on proven gap | Four Python projects already covered |
| PW-04 | `sdd/features/DESIGN_PAPER_WORKSPACE.md` | Create before edits | Scope, rationale and manifest |
| PW-05 | `sdd/reports/BUILD_REPORT_PAPER_WORKSPACE.md` | Create | Actual command/exit receipts and limitations |
| PW-06 | `python/apps/quant-engine/project.json` | Modify after ownership transfer | Existing OpenAPI targets sequentially export/check both actual read-only and paper schemas |

Package source/metadata/packaging belongs to the three implementation owners;
README, final security/SBOM and aggregate Verify Gate belong to parent.

Parent approved the additive engine Nx ownership transfer and the engine author
acknowledged stable project metadata before edits. Use Nx run-commands with
`parallel: false` for two actual Python schema exports/checks inside the existing
targets; the existing CI `quant-engine:openapi-check` then blocks drift in either
contract without redundant CI steps. Separately rebuild native licenses/NOTICE
and revised linear-perpetual data artifacts; lock changes only if resolution
metadata requires it, with no dependency upgrade.

## Verification

Use `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache`. After engine metadata is
ready: uv lock, locked all-groups sync, offline lock check, import checks, Nx
seven-node graph with engine→risk/execution/data, and fresh package builds.
Notify all owners once the locked environment is safe. Record failures honestly;
hosted CI and full product acceptance remain separate.

## Complexity diagnostic

Scoped design score: 10/10; all eight diagnostic rows pass. Package owners hide
runtime behavior/resources, root owns dependency resolution, and CI delegates
real targets without duplicating domain policy. Root metadata changes only for
real dependencies. No forwarding facade or speculative package is introduced.
