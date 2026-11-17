# Independent implementation review: DSH paper capability broker

Date: 2026-11-17. Reviewer: `dsh_paper_broker_review`. Scope is limited to the Python broker/bootstrap/lifespan slice:

- `python/apps/quant-engine/src/quant_engine/paper_capability.py`
- `python/apps/quant-engine/src/quant_engine/paper_bootstrap.py`
- `python/apps/quant-engine/src/quant_engine/paper_api.py`
- their broker/process tests and the scoped Build report

This is an implementation review of the scoped broker only. It does not certify the TypeScript Host, installed Harness owner/authentication, native cross-language E2E, Testnet/Mainnet behavior, or release gates.

## Verdict

**ACCEPT for the scoped Python broker slice; no unresolved P1/P2/P3 finding.** The implementation matches the frozen design on the reviewed boundaries: capability is process-memory only, the numeric loopback listener is prebound before broker publication, admission opens before broker acceptance, and broker cleanup runs before the engine cleanup. Existing FIFO provisioning remains a separate mutually exclusive mode.

The same-OS-user trust boundary is explicit in the design and is accepted as scoped. This review does not introduce or require speculative process attestation.

## Independent evidence

| Command | Exit/result |
|---|---:|
| `python/.venv/bin/python -m pytest python/apps/quant-engine/tests/test_paper_capability.py python/apps/quant-engine/tests/test_paper_capability_process.py -q --tb=short` | 0; 36 passed in 12.45s |
| `python/.venv/bin/python -m pytest python/apps/quant-engine/tests -q --tb=short` | 0; 152 passed, 1 existing Starlette deprecation warning, 37.14s |
| `python/.venv/bin/ruff check python/apps/quant-engine` | 0; all checks passed |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/apps/quant-engine` | 0 errors, 0 warnings |
| `python/.venv/bin/ruff format --check` on the five scoped Python paths | 0; all formatted |
| `python/.venv/bin/quant-engine-openapi --paper --output contracts/openapi/quant-paper.v1.json --check` | 0; schema unchanged |
| `git diff --check` | 0 |
| `/private/tmp/dsh_broker_adversarial_probe.py` (four partial-EOF peers, close/cancel, bounded cleanup) | 0; `adversarial_cancel_close_ok`, active=0, socket removed |

The full test suite warning is from the installed `fastapi.testclient` import and is unrelated to this broker; no test was skipped.

## Boundary checks

| Contract | Inspection/evidence | Result |
|---|---|---|
| Private path | Absolute canonical POSIX path; dedicated final directory `0700`; socket owner UID and mode `0600`; rejected symlink/non-directory/unsafe parent; existing inode never overwritten | Pass; covered by path and replacement tests |
| Cleanup | Device/inode captured after bind; unlink only when the owned socket inode remains; replacement path is preserved; close cancels and awaits active handlers | Pass; tests and adversarial close probe |
| Canonical protocol | Exact ordered compact ASCII JSON, one LF, max 1024 bytes; reads request through EOF before disclosure; duplicate keys, alternate spacing, CRLF, delayed trailing frame and missing EOF rejected | Pass; 36-case focused suite |
| Admission/resource bound | Four active connections; excess is refused before task creation; total 500 ms handler deadline; bounded writer close and task cleanup | Pass; active/refusal/deadline/close tests |
| Startup ordering | Bootstrap binds actual numeric loopback listener with normal socket options; no `SO_REUSEPORT`; lifespan opens `PaperAdmission`, then broker; startup failure yields no broker token/path | Pass; source inspection and process tests |
| Lifecycle independence | Host/service broker cleanup is separate from native service cleanup; no automatic migration; old inherited FIFO mode remains unchanged | Pass within Python scope; native/Host receipt remains external |
| Fixed errors / secrecy | Broker and API emit fixed safe errors; token is only in process memory/response; tests capture output and check no token disclosure; no credential/env resolver is imported | Pass; source scan, process output checks, full tests |
| Module design | Broker hides path/protocol/resource/cleanup knowledge behind `open()`/`close()` and diagnostics; bootstrap owns prebind/mode selection; API owns lifespan ordering | Pass for scoped boundary |

## Software-design-philosophy score

Scope-only score: **8/8 diagnostic rows (10/10 equivalent for this slice)**. The score is intentionally limited to the reviewed Python broker boundary and does not upgrade the whole-product score. Each module has a single describable responsibility, the public lifecycle interface is smaller than the implementation, path/protocol decisions are hidden, interface and invariant comments explain the design, and the implementation is covered by bounded tests. Existing same-user trust is a stated boundary rather than an omitted requirement.

## Limits and follow-up

The following are intentionally outside this receipt and remain parent/integration gates: TypeScript provider/facade and SDK uncertainty behavior, actual built Host-to-service E2E, installed Harness owner/auth/UI interaction, aggregate Nx/CI/security/SBOM checks, and SDD Release. The scoped Build report's attribution that the frozen 36-case run was executed by the parent is retained; this review independently reran the same suite and the broader 152-test Python suite.
