"""Exercise the published Alembic revision against an isolated temporary database."""

import hashlib
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL

from alembic import command
from quant_data.migrations import upgrade_sqlite

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_upgrade_preserves_strategy_trade_and_audit_rows_and_backups(tmp_path: Path) -> None:
    database = tmp_path / "migration-test.sqlite"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")

    command.upgrade(config, "0001_initial")
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO strategy_versions "
                "(id, strategy_id, version, validation_status, metadata_json, created_at) "
                "VALUES (1, 'mean-reversion', 'v1', 'validated', :metadata, '2026-01-01 00:00:00')"
            ),
            {"metadata": '{"window":20}'},
        )
        connection.execute(
            text(
                "INSERT INTO trade_events "
                "(id, event_type, environment, symbol, payload_json, created_at) "
                "VALUES (1, 'trade_filled', 'testnet', 'BTCUSDT', :payload, '2026-01-01 00:00:00')"
            ),
            {"payload": '{"qty":0.01}'},
        )
        connection.execute(
            text(
                "INSERT INTO trade_events "
                "(id, event_type, environment, symbol, payload_json, created_at) "
                "VALUES (2, 'risk_decision', 'testnet', 'BTCUSDT', :payload, '2026-01-01 00:00:00')"
            ),
            {"payload": '{"allowed":true}'},
        )
    engine.dispose()

    result = upgrade_sqlite(database)
    assert result.database == database.resolve()
    assert result.backup.is_file()
    assert hashlib.sha256(result.backup.read_bytes()).hexdigest() == result.backup_sha256
    backup_engine = create_engine(f"sqlite:///{result.backup}")
    with backup_engine.connect() as connection:
        assert connection.execute(text("PRAGMA integrity_check")).scalar_one() == "ok"
        assert connection.execute(text("SELECT count(*) FROM trade_events")).scalar_one() == 2
    backup_engine.dispose()

    upgraded = create_engine(f"sqlite:///{database}")
    with upgraded.connect() as connection:
        assert (
            connection.execute(text("SELECT strategy_config_json FROM strategy_versions WHERE id=1")).scalar_one()
            == '{"window":20}'
        )
        assert (
            connection.execute(text("SELECT count(*) FROM trade_events WHERE event_type='trade_filled'")).scalar_one()
            == 1
        )
        assert (
            connection.execute(text("SELECT count(*) FROM trade_events WHERE event_type='risk_decision'")).scalar_one()
            == 1
        )
    inspector = inspect(upgraded)
    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "strategy_versions",
        "trade_events",
        "execution_commands",
        "command_events",
        "paper_sessions",
        "admission_decisions",
        "paper_reservations",
        "paper_positions",
        "paper_native_events",
        "paper_protection_events",
    }
    assert {"event_type", "environment", "payload_json"} <= {
        column["name"] for column in inspector.get_columns("trade_events")
    }
    upgraded.dispose()

    downgrade_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    downgrade_config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    with pytest.raises(RuntimeError, match="refusing downgrade: .* contains user data"):
        command.downgrade(downgrade_config, "base")
    with pytest.raises(ValueError, match="refusing non-forward Alembic target"):
        upgrade_sqlite(database, "0001_initial")
    preserved = create_engine(f"sqlite:///{database}")
    with preserved.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM trade_events")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM strategy_versions")).scalar_one() == 1
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002_strategy_config"
        )
        assert "strategy_config_json" in {
            column["name"] for column in inspect(connection).get_columns("strategy_versions")
        }
    preserved.dispose()


def test_failed_migration_leaves_original_database_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "failed-migration.sqlite"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "0001_initial")
    before = database.read_bytes()

    real_upgrade = command.upgrade

    def fail_after_upgrade(config: Config, revision: str) -> None:
        real_upgrade(config, revision)
        raise RuntimeError("simulated post-migration failure")

    monkeypatch.setattr("quant_data.migrations.command.upgrade", fail_after_upgrade)
    with pytest.raises(RuntimeError, match="simulated post-migration failure"):
        upgrade_sqlite(database)

    assert database.read_bytes() == before
    backups = list(tmp_path.glob("failed-migration.sqlite.pre-migration-*.sqlite"))
    assert len(backups) == 1
    backup_engine = create_engine(f"sqlite:///{backups[0]}")
    with backup_engine.connect() as connection:
        assert connection.execute(text("PRAGMA integrity_check")).scalar_one() == "ok"
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial"
    backup_engine.dispose()


@pytest.mark.parametrize("sidecar", ("-journal", "-wal", "-shm"))
def test_migration_refuses_sqlite_sidecars(tmp_path: Path, sidecar: str) -> None:
    database = tmp_path / "sidecar.sqlite"
    database.touch()
    Path(f"{database}{sidecar}").touch()

    with pytest.raises(RuntimeError, match="journal/WAL/SHM sidecars"):
        upgrade_sqlite(database)


def test_migration_refuses_active_sqlite_writer(tmp_path: Path) -> None:
    database = tmp_path / "locked.sqlite"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "0001_initial")
    writer = sqlite3.connect(database)
    try:
        writer.execute("BEGIN IMMEDIATE")
        with pytest.raises(RuntimeError, match="active SQLite client prevents migration"):
            upgrade_sqlite(database)
    finally:
        writer.rollback()
        writer.close()


def test_migration_refuses_wal_mode_without_mutating_it(tmp_path: Path) -> None:
    database = tmp_path / "wal.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE state (id INTEGER PRIMARY KEY)")
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"

    with pytest.raises(RuntimeError, match="requires SQLite DELETE journal mode"):
        upgrade_sqlite(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_migration_detects_source_change_before_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "raced.sqlite"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "0001_initial")
    real_upgrade = command.upgrade

    def change_source_after_candidate_upgrade(config: Config, revision: str) -> None:
        real_upgrade(config, revision)
        with database.open("ab") as source:
            source.write(b"outside-lock-change")

    monkeypatch.setattr("quant_data.migrations.command.upgrade", change_source_after_candidate_upgrade)
    with pytest.raises(RuntimeError, match="database changed during migration"):
        upgrade_sqlite(database)
    assert database.read_bytes().endswith(b"outside-lock-change")
    assert len(list(tmp_path.glob("raced.sqlite.pre-migration-*.sqlite"))) == 1


def test_migration_preserves_special_characters_in_database_path(tmp_path: Path) -> None:
    ordinary = tmp_path / "initial.sqlite"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", URL.create("sqlite", database=str(ordinary)).render_as_string())
    command.upgrade(config, "0001_initial")
    database = tmp_path / "db?name#with space.sqlite"
    ordinary.rename(database)

    result = upgrade_sqlite(database)

    assert result.database == database.resolve()
    engine = create_engine(URL.create("sqlite", database=str(database)))
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0004_admission_state"
        )
    engine.dispose()


def test_current_head_metadata_matches_published_migrations(tmp_path: Path) -> None:
    """A real Alembic comparison must discover every model and no schema drift."""
    database = tmp_path / "metadata-consistency-test.sqlite"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "head")
    command.check(config)
    engine = create_engine(f"sqlite:///{database}")
    try:
        inspector = inspect(engine)
        assert {
            "name": "ix_trade_events_created_at",
            "column_names": ["created_at"],
            "unique": 0,
            "dialect_options": {},
        } in inspector.get_indexes("trade_events")
        assert {"name": None, "column_names": ["strategy_id", "version"]} in inspector.get_unique_constraints(
            "strategy_versions"
        )
    finally:
        engine.dispose()
