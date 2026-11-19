# Build report: Secure read-only Bybit Testnet provider

## Metadata

| Attribute | Value |
|---|---|
| Feature | Secure read-only Bybit Testnet provider |
| Date | 2026-11-19 |
| Design | `sdd/features/DESIGN_TESTNET_READONLY_PROVIDER.md` |
| Status | Complete for this implementation slice; product acceptance remains partial |

## Scope and decision

This increment implements the host-owned signed GET provider described by the
Design. It is intentionally limited to Testnet Linear reads and never submits,
cancels, transfers, or changes account settings. Mainnet OAuth is a separate
read-only authorization concern; it does not widen this provider's endpoint or
execution authority.

## Tasks

| Task | Path | Result | Evidence |
|---|---|---|---|
| Signed credential boundary, fixed host transport, response normalization and bounded pagination | `python/packages/quant-execution/src/quant_execution/bybit_http_provider.py` | Complete | Targeted tests, Ruff, and format checks all exited 0 |
| Fake resolver/transport contract tests and secret-redaction checks | `python/packages/quant-execution/tests/test_bybit_http_provider.py` | Complete | 14 tests passed; no network or real credential |
| Strict projection compatibility | `bybit_preflight.py` / existing projection contract | Complete | Preflight regression now accepts the exact coverage projection and remains non-trading |

## Files changed

- `python/packages/quant-execution/src/quant_execution/bybit_http_provider.py`
- `python/packages/quant-execution/tests/test_bybit_http_provider.py`
- `sdd/features/DESIGN_TESTNET_READONLY_PROVIDER.md`
- this report

## Verification results

| Command | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest python/packages/quant-execution/tests/test_bybit_http_provider.py` | 0 | 14 passed |
| `uv run --project python --locked pytest python/packages/quant-execution/tests/test_bybit_projection.py python/packages/quant-execution/tests/test_bybit_preflight.py` | 0 | 25 passed |
| `uv run --project python --locked ruff check python/packages/quant-execution/src/quant_execution/bybit_http_provider.py python/packages/quant-execution/tests/test_bybit_http_provider.py` | 0 | clean |
| `uv run --project python --locked ruff format --check python/packages/quant-execution/src/quant_execution/bybit_http_provider.py python/packages/quant-execution/tests/test_bybit_http_provider.py` | 0 | already formatted |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` | 0 | TypeScript build, lint, typecheck, unit, bundle, SDK and tooling gates passed |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm typecheck:tests` | 0 | strict test-source typecheck passed |
| `pnpm python:lint` | 0 | Ruff check and format check passed |
| `pnpm python:typecheck` | 0 | Pyright reported 0 errors |
| `pnpm python:test` | 0 | 331 passed, 11 warnings |
| `pnpm run security:deps` | 0 | npm audit clean; pip-audit clean for non-editable dependencies; four local editable packages skipped |
| `pnpm run sbom` | 0 | CycloneDX npm SBOM regenerated with 200 components |
| `gitleaks dir --redact --no-banner --log-level error .` | 0 | no findings |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx show projects` | 0 | seven projects discovered |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx graph --file=/tmp/bybit-quant-task-graph.json` | 0 | task graph JSON generated |
| `uv run --project python --locked quant-engine-openapi --output contracts/openapi/quant-engine.v1.json --check` | 0 | generated contract unchanged |
| source line-cap scan excluding generated output | 0 | no handwritten source over 500 lines; generated `paper-paths.ts` is 595 lines |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm exec nx run quant-execution:sbom` | 1 | no project-level `sbom` target exists; root SBOM command is the available check |

The first targeted run before the correction had one failure: the provider
returned pagination counts as extra keys, which the strict `ReportCoverage`
schema correctly rejected. The provider now performs the same bounded reads but
returns only the declared coverage fields. The regression suite then passed.

## Security and limits

The transport accepts only HTTPS `api-testnet.bybit.com/v5/*`, GET, deterministic
V5 HMAC signing, bounded responses, and denied redirects. Credential resolution
is injected by the host and credentials are not serializable in profile DTOs or
exceptions. Exchange errors are reduced to fixed safe codes. Tests use fixture
credentials and a fake transport only.

This report does not claim a live Testnet preflight, account activation, balance,
Nautilus reconciliation, scheduler, recovery, or order acceptance. No order was
sent. The wider DSH product remains PARTIAL because persistent unattended
scheduling, complete private-state reconciliation, single execution authority,
installed upgrade preservation, and full original SDD acceptance are still open.

## Drift and review

No material architectural drift was introduced. The strict projection contract
was honored; the provider's internal row counts remain an implementation detail
of pagination validation. No formal external review was run for this small
contract correction; the existing independent UX review remains at
`sdd/reports/UX_REVIEW_DSH_BYBIT_UI_2026-11-19.md`.

## Final status

The implementation slice is complete and locally verified. The repository-level
goal is not complete and must not be represented as an unattended live trading
system.
