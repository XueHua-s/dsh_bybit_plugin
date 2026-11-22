# Schema migrations

The durable trading/audit schema is migrated with Alembic through
`quant_data.migrations`, which requires an explicit existing SQLite path. It
creates and verifies a unique backup, upgrades a candidate copy, and atomically
replaces the database only after the migration and integrity check succeed.
Example: `uv run --project python --locked python -m quant_data.migrations
/absolute/path/to/isolated.sqlite`. The target database is never selected by a
default. The command requires a maintenance window: SQLite readers/writers are
blocked by an exclusive lock, while service processes and raw file writers must
be stopped separately. Existing `-journal`, `-wal`, or `-shm` sidecars are
refused, as is WAL journal mode even when no sidecar is present. Non-empty
destructive downgrades are refused by the revisions.
