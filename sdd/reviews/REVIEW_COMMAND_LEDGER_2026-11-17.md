# Independent review: durable command ledger

Date: 2026-11-17. Reviewer: independent `ledger_independent_review` agent. Implementation owner: `command_ledger`. Reviewer edited only this receipt; adversarial probes were written under `/tmp`. No production or test implementation was authored by reviewer.

**Verdict: ACCEPT for the bounded local SQLite command-ledger prerequisite.** No unresolved blocking finding remains in the reviewed revision. This is not product/trading/release acceptance, final risk acceptance, or approval to dispatch live orders.

## Scope and sources

Read repository AGENTS.md, `.agents/skills/software-design-philosophy/SKILL.md`, SDD Build instructions, `sdd/features/DESIGN_COMMAND_LEDGER.md`, relevant persistent audit/Nautilus/guard requirements in DEFINE_BYBIT_AI_QUANT.md and DESIGN_BYBIT_AI_QUANT.md, existing migration helper/tests and current ledger implementation/tests.

Only isolated SQLite temporary databases were used. No user's database, account, credentials, secret files, exchange connection or network request was used. The intentionally crashed child process ran only the local SQLite ledger and exited via `os._exit(17)` after committing a dispatch claim.

The design explicitly records the existing direct TypeScript execution drift and the Python data-plane exception; this slice does not resolve original product acceptance gaps.

## Findings and disposition

| Finding | Disposition | Verified evidence |
|---|---|---|
| Signed-zero limit price was accepted by text-based zero comparison; extreme positive-exponent zero could cause excessive Decimal formatting allocation. | APPLIED by implementer | Numeric positive-price validation; zero canonicalized before format; signed/extreme zero regressions pass. |
| SQLite DELETE triggers alone do not protect risk audit from `INSERT OR REPLACE` under default `recursive_triggers=0`. | APPLIED by implementer | Migration now rejects duplicate primary/event/version identities in BEFORE INSERT; independent SQL replacement with a changed primary key is refused. |
| Pyright could not access `rowcount` on SQLAlchemy's inferred Result type. | APPLIED by implementer | CAS uses UPDATE RETURNING with `scalar_one_or_none`; explicit-interpreter pyright reports zero errors. |

Preliminary SQLite loophole reproduction used an independent `sqlite3` in-memory table, confirmed replacement without DELETE-trigger execution, exit 0. It did not touch project data. The final migration fix was independently checked against Alembic-created schema.

## Real command evidence

All commands ran from `/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant` unless stated otherwise.

| Command | Exit | Result |
|---|---:|---|
| `uv run --project python --locked pytest python/packages/quant-data/tests -q` | 2 | Did not run pytest: sandbox denied temporary lock file under `~/.cache/uv`. |
| `uv run --project python --locked ruff check python/packages/quant-data && uv run --project python --locked pyright python/packages/quant-data/src` | 2 | Same uv cache permission issue; neither check claimed green from this attempt. |
| `python/.venv/bin/python -m pytest python/packages/quant-data/tests -q` | 0 | Initial independent snapshot: 26 passed; final snapshot: **28 passed in 0.46s**. |
| `python/.venv/bin/ruff check python/packages/quant-data && python/.venv/bin/pyright python/packages/quant-data/src` | 1 | Ruff passed; pyright lacked venv interpreter resolution (10 import errors). |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src` | 1 | Before correction: one real SQLAlchemy `rowcount` typing error. |
| `python/.venv/bin/ruff check python/packages/quant-data && python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-data/src` | 0 | Final: all lint checks passed, 0 type errors/warnings. |
| `python/.venv/bin/python /tmp/ledger_review_probe.py` | 1 | First reviewer probe fixture omitted legacy `created_at`; fixture corrected, no production defect inferred. |
| `python/.venv/bin/python /tmp/ledger_review_probe.py` | 0 | All independent migration/concurrency/state/audit/crash/restore probes passed (below). |
| `python/.venv/bin/python /tmp/ledger_atomic_review_probe.py` | 0 | Changed-command race and injected audit failure rollback passed. |
| `git diff --check -- python/packages/quant-data sdd/features/DESIGN_COMMAND_LEDGER.md` | 0 | No whitespace errors. |
| `wc -l python/packages/quant-data/src/quant_data/*.py python/packages/quant-data/alembic/versions/0003_command_ledger.py` | 0 | commands154, ledger344, models78, migration67; no reviewed source file exceeds500 lines. |

The existing Python venv was used after uv's sandbox cache failure; no dependency install or lock refresh was performed by reviewer. This receipt does not claim a successful locked uv invocation.

## Adversarial verification

- **Durable concurrency:** 15 rounds, eight independent Engines/Session factories per round, shared temporary SQLite database and start barriers. Identical admissions produced one command identity and exactly one dispatch winner; audit had admitted/ready/dispatching once. A separate two-thread conflicting canonical payload race produced one admission and one LedgerConflict.
- **Identity:** canonical Decimal equivalence is covered in package tests; changing quantity/side/reduce-only is rejected; environment/account scopes isolate identity. Native client IDs persist through reopen, duplicate admission, abrupt process exit and restore.
- **Monotonic state/fill:** independent partial0.4 -> cancel0.3 was rejected; conflicting reuse of partial event rejected; partial0.4 -> reconciliation_required0.4 retained fill. Claiming uncertain dispatch failed. Stale accepted0 and terminal late fill were refused; cancel retained0.4 rather than presenting flat state.
- **Risk audit:** persisted balance rejection survived reopen, could not dispatch, and raw SQL UPDATE/DELETE/INSERT OR REPLACE attacks were refused. Replacement probe used different primary key with the same event/version, exercising protection beyond the implementation's same-ID regression.
- **Crash recovery:** a separate Python process admitted, approved and claimed a command, then exited17 abruptly. Reopen found dispatching, recovery marked reconciliation_required, subsequent recovery was empty, native ID persisted and dispatch claim stayed false. No external execution is inferred.
- **Atomic audit:** reviewer-only temporary trigger injected failure at dispatch audit insertion. IntegrityError rolled state/version and audit back to the exact previous ready record; after dropping that temporary trigger, a fresh dispatch claim could win. No state transition without its audit was left committed.
- **Migration:** created0002 SQLite with preexisting strategy/trade/risk fixture rows; upgraded explicitly to head; read revision0003, ledger tables and three append-only triggers, and verified old rows survived. Populated ledger downgrade refused before data destruction. Existing protected `upgrade_sqlite` created a backup; copying it into an isolated restore fixture retained all command/event/trade/strategy/version rows exactly, passed integrity_check, retained native ID and prohibited uncertain resubmit.

## Complexity diagnostic

**Current score: 10/10 for this slice; all eight diagnostic rows pass.** Contract module owns validation/canonicalization; ledger owns state, concurrency, transactions and event replay; migration/ORM own durable schema. Public methods are simpler than transactional implementation and document external executor/risk boundaries, quiescent recovery and late-event uncertainty. No failed diagnostic row requires a further change. This score is scoped to current ledger design, not the entire repository architecture.

## Reviewed fingerprints

SHA256, captured after final independent checks:

- commands.py: `0983428f26c2e67c6b3facb588816789e586c1ef9e9537417a56d5bd2d412f80`
- ledger.py: `24132b48c18f96d3ab763c7fa5d73b14c65d77456f0ed8f7c902e4156231a24f`
- models.py: `8911ddebfdac4bd3242644b26bd9472e8861bb36e479a5dd606a7b62028515be`
- 0003_command_ledger.py: `d6be052eae07010488ba6c78225e7d8e94828bc39fdc790785effca60d5d2073`
- test_command_ledger.py: `5fd4920f576fe558af2a1658774f47fb669d8e7c6265ca1430476aa2ff66f65d`

## Remaining limits and ownership

No PostgreSQL, power-loss durability/fsync, live reconciliation, exchange reports, executor fencing, account balance/notional/risk engine, Nautilus authority integration or TS-order-path removal was verified. Observations are trusted typed inputs from future reconciliation; this ledger neither authenticates their source nor resolves late terminal fills automatically. Risk approval records a caller decision and is not a live authorization mechanism. Database owner privileges can bypass/drop schema safeguards; this is append-only application storage, not tamper-proof security.

The parent owns full workspace Verify Gate, dependency/SBOM/secret checks, release/handoff and remaining original MUST acceptance. No install, upgrade of user data, Git commit, push or release is claimed.
