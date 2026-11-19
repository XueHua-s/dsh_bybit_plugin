# ADR: Protected SQLite migration boundary

## Decision

Alembic upgrades for the quant-data package run through
`quant_data.migrations.upgrade_sqlite`. The caller must pass an existing SQLite
file explicitly. The module snapshots that file to a uniquely named backup,
upgrades an isolated candidate copy, checks SQLite integrity, then atomically
replaces the target. A failed upgrade leaves the original file untouched and
retains the verified backup for inspection or recovery. The source is opened
with `BEGIN EXCLUSIVE` and held through the final source hash and atomic
replace. This blocks SQLite readers/writers that honor the database lock; the
caller must still stop service processes and raw file writers for a maintenance
window.

Existing `-journal`, `-wal`, or `-shm` sidecars and databases in WAL journal
mode are refused. The command rechecks sidecars and the source hash immediately
before replacement.
Alembic URLs are built with SQLAlchemy `URL.create`, so valid SQLite paths with
query, fragment, percent, or whitespace characters are not parsed as URL syntax.

Destructive downgrades are refused when either `strategy_versions` or
`trade_events` contains rows. Empty fixture databases may still downgrade for
schema tests.

## Rationale

The previous Alembic task pointed at a package-relative default database and
the test only checked an empty schema. A deep data-plane boundary owns target
selection, backup, candidate migration and downgrade policy together, so
callers cannot accidentally invoke a bare Alembic command against a user file.
The boundary is SQLite-only until a PostgreSQL backup/restore contract is
implemented and verified separately.

## Evidence and limits

`python/packages/quant-data/tests/test_migrations.py` runs only against
`tmp_path` SQLite files. It proves strategy configuration, trade history and
audit rows survive `0001_initial` → `head`, verifies the backup checksum and
integrity, rejects a non-empty downgrade, refuses all three sidecars, WAL mode,
and an active SQLite writer, detects a source-file race before replacement,
preserves special-character paths, and proves a failed revision does not alter
the source. No target database migration was run.
