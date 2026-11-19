# BUILD REPORT: Paper admission workspace

Date: 2026-11-17. Baseline `605fe70`. Author: paper workspace integration worker.
Status: In Progress; parent owns final aggregate Verify Gate/review/security/SBOM.

## Inputs and mode

Existing BRAINSTORM_BYBIT_AI_QUANT, DEFINE_BYBIT_AI_QUANT and project DESIGN,
supplemented by DESIGN_PAPER_ADMISSION, DESIGN_PAPER_NATIVE,
DESIGN_ADMISSION_STORE and preimplementation DESIGN_PAPER_WORKSPACE manifest.
Parent-delegated bounded integration; sequential lock/sync after real metadata.
No new execution-mode decision or external review claimed by this worker.

## Task execution and files

| ID | Path | Action / result |
|---|---|---|
| PW-01 | `python/uv.lock` | Regenerated after actual engine risk/execution imports/dependencies; only four dependency/source rows added |
| PW-02 | `python/pyproject.toml` | Inspected, unchanged; already installs four real packages and patched fsspec override |
| PW-03 | `.github/workflows/ci.yml` | Inspected, unchanged; already checks all four Python projects and risk wheel |
| PW-04 | `sdd/features/DESIGN_PAPER_WORKSPACE.md` | Created before dependent edits |
| PW-05 | `sdd/reports/BUILD_REPORT_PAPER_WORKSPACE.md` | Actual receipts and pending artifact checks |
| PW-06 | `python/apps/quant-engine/project.json` | Parent-approved ownership transfer acknowledged by engine owner; existing OpenAPI generation/check targets sequentially run actual readonly and paper contracts |

No dependency upgrade/downgrade, root configuration change, credential access,
exchange request, commit or push occurred. The sole lock/sync owner notified
parent and engine author after editable engine rebuild completed.

## Verification receipts

All uv commands use `UV_CACHE_DIR=/private/tmp/bybit-engine-uv-cache`.
Nx uses `NX_DAEMON=false NX_ISOLATE_PLUGINS=false`.

| Command | Exit | Evidence |
|---|---:|---|
| `uv lock --project python --offline` | 0 | 93 packages, only engine risk/execution dependency/source edges added |
| `uv sync --project python --locked --all-groups --offline` | 0 | Editable engine rebuilt; all other installed packages retained |
| `uv lock --project python --check --offline` | 0 | Lock matches real metadata |
| `pnpm exec nx graph --file=/private/tmp/bybit-paper-workspace-graph.json` | 0 | Graph JSON produced |
| Python graph assertions (seven nodes; engine targets exactly data/risk/execution) | 0 | Seven actual nodes and three real engine edges |
| `uv pip check --python python/.venv/bin/python` | 1 | Sole known Nautilus1.231.0 requires fsspec2026.2.0 while patched2026.6.0 retained |
| `uv build --project python/packages/quant-data --offline --out-dir /private/tmp/bybit-paper-package-check/data` | 0 | Fresh source archive and wheel |
| `uv build --project python/packages/quant-execution --offline --out-dir /private/tmp/bybit-paper-package-check/execution` | 0 | Fresh source archive and wheel; current paper modules included |
| `uv build --project python/apps/quant-engine --offline --out-dir /private/tmp/bybit-paper-package-check/engine` | 0 | Fresh source archive and wheel; paper modules present at snapshot |
| Wheel resource inspection | 0 | Inspection ran; data0004 migration absent, a real packaging failure despite successful wheel build |
| `uv build --project python/packages/quant-data --offline --out-dir /private/tmp/bybit-paper-package-final/data` after owner fix | 0 | Fresh wheel contains `_alembic/versions/0004_admission_state.py` and configuration |
| Isolated extracted-wheel `upgrade_sqlite` smoke, zero-byte SQLite fixture | 1 | All migrations ran, then sidecar guard rejected zero-byte-source initialization; reported owner |
| Isolated extracted-wheel `upgrade_sqlite` smoke, initialized SQLite fixture | 0 | Python `-I`, extracted wheel first in sys.path, module origin asserted; PRAGMA user_version=0 creates valid header; 0004 revision, 11 tables and backup verified |
| `uv build --project python/packages/quant-execution --offline --out-dir /private/tmp/bybit-paper-package-final/execution` | 0 | Fresh wheel includes runtime/native/worker modules |
| `uv build --project python/apps/quant-engine --offline --out-dir /private/tmp/bybit-paper-package-final/engine` | 0 | Fresh wheel includes paper bootstrap/admission/API |
| Python `-I` extracted-wheel import smoke | 0 | Engine paper_bootstrap/paper_admission/paper_api, execution paper_runtime/paper_native and data admission_store imported; every module origin asserted inside temporary extracted artifact directory; no runtime constructor invoked |
| `uv lock --project python --check --offline` after native license metadata | 0 | Lock unchanged; license metadata does not change dependency resolution |
| `uv build --project python/packages/quant-execution --offline --out-dir /private/tmp/bybit-paper-package-licensed/execution` | 0 | Fresh native wheel/source archive after license declaration |
| Native wheel/sdist license inspection | 0 | Wheel License-Expression exactly MIT AND LGPL-3.0-only; MIT/LGPL/NOTICE bytes equal source; sdist contains all three plus adapted paper_sandbox/native source |
| `uv build --project python/packages/quant-data --offline --out-dir /private/tmp/bybit-paper-package-licensed/data` | 0 | Fresh revised linear-perpetual schema/resources |
| Revised extracted-data-wheel migration smoke | 0 | Isolated origin;0004/backup; accounting_model, realized_pnl, cumulative_fee and position average_entry_price columns verified |
| Final data owner-requested repeat: `uv build --project python/packages/quant-data --offline --out-dir /private/tmp/bybit-paper-data-final-accounting` and isolated artifact smoke | 0 / 0 | Fresh latest wheel; valid initialized temp SQLite0004, exact required session accounting_model/realized_pnl/cumulative_fee and position average_entry_price columns asserted; backup exists; no sync/dependency edit |
| `pnpm exec nx run quant-engine:openapi-check --skip-nx-cache --output-style=static` initial retry | 1 | uv run implicit metadata rebuild attempted Hatchling DNS; both schema checks not claimed passing |
| `uv sync --project python --locked --all-groups --offline` after package metadata | 0 | Sole owner refreshed data/native editables using cached build dependencies, no upgrades |
| `UV_OFFLINE=true pnpm exec nx run quant-engine:openapi-check --skip-nx-cache --output-style=static` | 0 | Actual readonly check followed by actual --paper check both ran and passed uncached |

## Drift and issues

The initial data wheel omits the external Alembic tree, including new
0004_admission_state.py. This pre-existing packaging design gap affects installed
runtime migrations and was reported to package owner/parent; it is not a pass.
Package owner added explicit wheel Alembic resources/config and resource-aware
lookup; fresh isolated extracted-wheel migration now passes with a valid
initialized temporary SQLite fixture. A zero-byte file triggers the existing
final sidecar protection; this narrower edge is reported separately and is not
claimed passing. No live database is used. Subsequent fresh engine/native wheels
include the complete module set and isolated imports pass. These prove artifact
closure for the checked snapshot, not behavioral acceptance; source owners and
parent own remaining functional/review changes.

The existing fsspec/Nautilus metadata conflict is preserved as an intentional
security override, not hidden or solved by vulnerable downgrade.

Parent requested separate actual paper OpenAPI coverage; engine author granted
project metadata ownership before the additive manifest/target edits. Existing
CI call now verifies both schemas, so no redundant CI step was added. Native
license change and data perpetual-accounting schema were rechecked with fresh
artifacts. Sole owner completed offline editable refresh and informed parent.

## Acceptance and remaining work

AT-001 scoped graph acceptance passes: seven nodes and actual engine→data/risk/
execution edges. Hosted CI is unexecuted. Package runtime/resource verification
passes isolated module-origin checks for engine/native/data; data resource/migration
smoke passes on an initialized fixture. Parent owns `pnpm run verify`, final
Python tests, independent review, SBOMs and security scans. This report does not
certify full original-product acceptance or live trading.

## Final status

IN PROGRESS at aggregate level: scoped lock/discovery/artifact checks completed.
Source owners/parent own final functional acceptance and independent review.
No premature full SDD completion handoff is emitted.
