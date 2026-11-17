# DESIGN: Risk workspace integration

Date: 2026-11-17. Scope: integration supplement to BRAINSTORM_BYBIT_AI_QUANT,
DEFINE_BYBIT_AI_QUANT and DESIGN_BYBIT_AI_QUANT. The risk package's own design
owns the deterministic risk contract; this supplement owns discovery, installation
and CI only. No exchange connection or order authorization is added.

## Decisions and boundaries

- Install the real `bybit-quant-risk` package through the existing uv workspace.
  The root workspace declares the dependency and workspace source explicitly, as
  it does for the other independently discoverable Python packages.
- Add Hypothesis to the root development group for the required risk property
  tests, rather than leaking test tooling into the package's runtime dependencies.
- Extend the existing explicit Python CI target list with `quant-risk`, including
  its wheel build as well as lint, typecheck and deterministic tests.
- Keep package ownership in `python/packages/quant-risk`; root configuration only
  orchestrates it. Do not invent an engine dependency edge until the engine
  actually imports risk. Nx must discover seven real projects with their actual
  pre-existing edges.
- Retain `fsspec==2026.6.0` root override: NautilusTrader 1.231.0's exact
  2026.2.0 metadata pin is vulnerable. Existing `uv pip check` metadata mismatch
  remains an explicit limitation; adding risk must not downgrade fsspec.

## File Manifest

| ID | Path | Action | Ownership / purpose |
|---|---|---|---|
| RW-01 | `python/pyproject.toml` | Modify | Workspace dependency/source and Hypothesis development tooling |
| RW-02 | `python/uv.lock` | Regenerate with uv | Resolve real workspace member and test tooling; single lock/sync owner |
| RW-03 | `.github/workflows/ci.yml` | Modify | Include risk lint/type/test and wheel build |
| RW-04 | `sdd/features/DESIGN_RISK_WORKSPACE.md` | Create before implementation | Boundary, rationale, manifest and checks |
| RW-05 | `sdd/reports/BUILD_REPORT_RISK_WORKSPACE.md` | Create | Real commands, exits, limitations and delegated aggregate checks |

No README, SBOM, package-source or trading configuration edit belongs to this
manifest. Parent integration owns final SBOM/security/aggregate Verify Gate.

## Dependency order and verification

Read the risk package's real pyproject/public import first; then modify root
configuration and CI, run `uv lock --project python` and
`uv sync --project python --locked --all-groups` using
`UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache`. Verify locked consistency,
root-installed `quant_risk` import, Nx discovery/graph and risk targets. Record
every actual command and exit in the report. CI itself remains unexecuted until
GitHub runs it. Property-test tooling remains dev-only.

## Complexity review

Score: 10/10 for this scoped integration design; all eight diagnostic rows pass.
The workspace owns package resolution, the package owns risk policy and its
public interface, and CI delegates existing targets. No forwarding facade,
runtime configuration or duplicate policy knowledge is introduced. The boundary
can be understood without reading risk implementation.

## Scope and remaining acceptance

AT-001 is checked only for discovery/actual graph edges; AT-021 and complete
original §13 risk acceptance belong to the parent risk implementation/review.
No full product acceptance, live risk enforcement or hosted CI success follows
from installing and building this offline package.
