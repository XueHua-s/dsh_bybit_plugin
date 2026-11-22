"""Run Alembic upgrades on a verified SQLite snapshot before replacing user state.

The original database remains untouched while migrations run. Only a fully
upgraded, integrity-checked candidate is atomically installed in its place.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sqlite3
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Connection

from alembic import command

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def migration_config() -> Config:
    """Resolve checked-in or wheel-packaged migrations without a default DB target."""
    packaged = Path(__file__).resolve().parent
    if (packaged / "_alembic.ini").is_file():
        config = Config(str(packaged / "_alembic.ini"))
        config.set_main_option("script_location", str(packaged / "_alembic").replace("%", "%%"))
    else:
        config = Config(str(PROJECT_ROOT / "alembic.ini"))
    return config


def revision_is_at_least(connection: Connection, minimum_revision: str) -> bool:
    """Return whether one known Alembic revision descends from a required schema.

    Runtime stores use this instead of pinning themselves to today's exact head;
    additive migrations can then keep existing consumers compatible.
    """
    try:
        has_version_table = connection.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'")
        ).first()
        if has_version_table is None:
            return False
        revisions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        if len(revisions) != 1 or not isinstance(revisions[0], str):
            return False
        scripts = ScriptDirectory.from_config(migration_config())
        required = scripts.get_revision(minimum_revision)
        pending = [scripts.get_revision(revisions[0])]
    except Exception:  # noqa: BLE001 - unknown schema revisions fail closed
        return False
    if required is None or pending[0] is None:
        return False

    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current is None or current.revision in visited:
            continue
        if current.revision == required.revision:
            return True
        visited.add(current.revision)
        parents = current.down_revision
        if isinstance(parents, str):
            pending.append(scripts.get_revision(parents))
        elif parents is not None:
            pending.extend(scripts.get_revision(parent) for parent in parents)
    return False


@dataclass(frozen=True)
class UpgradeResult:
    """Evidence returned after a protected upgrade completes."""

    database: Path
    backup: Path
    revision: str
    backup_sha256: str


def upgrade_sqlite(database: Path, revision: str = "head") -> UpgradeResult:
    """Back up and upgrade SQLite during a maintenance window with clients stopped.

    A unique, verified backup is retained beside the database. Alembic runs on
    a candidate copy; the candidate replaces the database only after success.
    The exclusive source lock refuses active SQLite readers/writers and remains
    held through the atomic replacement. All service processes must still be
    stopped: non-SQLite writers and raw file edits do not honor SQLite locks.
    """

    target = database.expanduser().resolve(strict=True)
    if not target.is_file():
        raise ValueError("SQLite migration target must be a regular file")
    if not revision or revision.startswith("-"):
        raise ValueError("protected upgrade requires a forward Alembic revision")
    _reject_sidecars(target)

    backup_fd, backup_name = tempfile.mkstemp(
        prefix=f"{target.name}.pre-migration-", suffix=".sqlite", dir=target.parent
    )
    os.close(backup_fd)
    backup = Path(backup_name)
    candidate_fd, candidate_name = tempfile.mkstemp(
        prefix=f".{target.name}.candidate-", suffix=".sqlite", dir=target.parent
    )
    os.close(candidate_fd)
    candidate = Path(candidate_name)
    try:
        with _exclusive_source_lock(target):
            original_hash = _sha256(target)
            target_mode = stat.S_IMODE(target.stat().st_mode)
            shutil.copyfile(target, backup)
            backup_hash = _sha256(backup)
            _assert_integrity(backup)
            shutil.copyfile(backup, candidate)

            config = migration_config()
            config.set_main_option("sqlalchemy.url", _sqlite_url(candidate))
            _assert_forward_revision(candidate, config, revision)
            command.upgrade(config, revision)
            _assert_integrity(candidate)
            candidate.chmod(target_mode)

            _reject_sidecars(target)
            if _sha256(target) != original_hash:
                raise RuntimeError("database changed during migration; refusing to replace concurrent data")
            os.replace(candidate, target)
        return UpgradeResult(target, backup, revision, backup_hash)
    except BaseException:
        candidate.unlink(missing_ok=True)
        raise
    finally:
        candidate.unlink(missing_ok=True)


@contextmanager
def _exclusive_source_lock(database: Path) -> Iterator[None]:
    """Hold SQLite's exclusive rollback-journal lock through the file swap."""

    connection = sqlite3.connect(database, timeout=0, isolation_level=None)
    try:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        if journal_mode.lower() != "delete":
            raise RuntimeError("protected migration requires SQLite DELETE journal mode; checkpoint and retry")
        connection.execute("BEGIN EXCLUSIVE")
    except RuntimeError:
        connection.close()
        raise
    except sqlite3.OperationalError as error:
        connection.close()
        raise RuntimeError("active SQLite client prevents migration; stop database users and retry") from error
    try:
        yield
    finally:
        connection.rollback()
        connection.close()


def _reject_sidecars(database: Path) -> None:
    sidecars = (Path(f"{database}-journal"), Path(f"{database}-wal"), Path(f"{database}-shm"))
    if any(sidecar.exists() for sidecar in sidecars):
        raise RuntimeError("SQLite journal/WAL/SHM sidecars exist; stop database users before migration")


def _assert_integrity(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    if result is None or result[0] != "ok":
        raise RuntimeError(f"SQLite integrity check failed for {database.name}")


def _assert_forward_revision(database: Path, config: Config, revision: str) -> None:
    """Reject an Alembic target that is not a descendant of the current revision."""

    scripts = ScriptDirectory.from_config(config)
    target_revision = scripts.get_revision(revision)
    if target_revision is None:
        raise ValueError(f"unknown forward Alembic revision: {revision}")

    engine = create_engine(URL.create("sqlite", database=str(database)))
    try:
        with engine.connect() as connection:
            has_version_table = connection.execute(
                text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'")
            ).first()
            if has_version_table is None:
                current_revision = None
            else:
                current_rows = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
                if len(current_rows) > 1:
                    raise ValueError("protected upgrade does not support multiple Alembic heads")
                current_revision = current_rows[0] if current_rows else None
    finally:
        engine.dispose()

    while target_revision is not None:
        if target_revision.revision == current_revision:
            return
        parents = target_revision.down_revision
        if parents is None:
            break
        if isinstance(parents, (tuple, list)):
            raise TypeError("protected upgrade does not support branched Alembic histories")
        target_revision = scripts.get_revision(parents)
    if current_revision is not None:
        raise ValueError(f"refusing non-forward Alembic target: {revision}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sqlite_url(database: Path) -> str:
    """Render a path-safe URL and escape ConfigParser interpolation markers."""

    return URL.create("sqlite", database=str(database)).render_as_string(hide_password=False).replace("%", "%%")


def main() -> None:
    """CLI entry point; the database path is mandatory to prevent default-target use."""

    parser = argparse.ArgumentParser(description="Safely upgrade an explicit SQLite database")
    parser.add_argument("database", type=Path, help="existing SQLite database file")
    parser.add_argument("--revision", default="head", help="Alembic forward revision (default: head)")
    args = parser.parse_args()
    result = upgrade_sqlite(args.database, args.revision)
    print(f"Upgraded {result.database} to {result.revision}; backup: {result.backup} sha256={result.backup_sha256}")


if __name__ == "__main__":
    main()
