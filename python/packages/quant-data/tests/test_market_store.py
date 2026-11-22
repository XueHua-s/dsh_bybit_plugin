"""Market snapshot persistence keeps exact values and explicit migration boundaries."""

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from alembic import command
from quant_data.market_store import MarketSnapshotRecord, MarketSnapshotStore
from quant_data.migrations import migration_config, upgrade_sqlite


def record(
    *,
    symbol: str = "BTCUSDT",
    last_price: Decimal | None = Decimal("64000.1234567890123456789"),
    received_at: str = "2026-11-19T10:00:00+00:00",
) -> MarketSnapshotRecord:
    return MarketSnapshotRecord(
        environment="testnet",
        symbol=symbol,
        last_price=last_price,
        bid_price=Decimal("64000.1"),
        ask_price=Decimal("64000.2"),
        event_time_ms=1_790_000_000_000,
        received_at=received_at,
        source="bybit-v5-public-linear-tickers",
    )


def migrated_database(path: Path) -> Path:
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=0")
    upgrade_sqlite(path)
    return path


def test_sqlite_store_roundtrips_decimal_and_upserts_one_symbol(tmp_path: Path) -> None:
    database = migrated_database(tmp_path / "market.sqlite")
    store = MarketSnapshotStore.sqlite(database)
    first = record()
    store.upsert(first)
    store.upsert(record(last_price=Decimal("64001.000000000000000001"), received_at="later"))

    result = store.latest("testnet", "BTCUSDT")
    assert result == record(last_price=Decimal("64001.000000000000000001"), received_at="later")
    with create_engine(f"sqlite:///{database}").connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM market_snapshot_projections")).scalar_one() == 1
    store.close()


def test_snapshot_store_requires_a_database_at_least_revision_0005(tmp_path: Path) -> None:
    database = tmp_path / "old.sqlite"
    database.touch()
    config = migration_config()
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "0004_admission_state")

    with pytest.raises(RuntimeError, match="must be migrated to 0005"):
        MarketSnapshotStore.sqlite(database)


def test_snapshot_store_rejects_missing_files_and_non_testnet_records(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        MarketSnapshotStore.sqlite(tmp_path / "missing.sqlite")

    store = MarketSnapshotStore.sqlite(migrated_database(tmp_path / "market.sqlite"))
    with pytest.raises(ValueError, match="environment must be testnet"):
        store.upsert(
            MarketSnapshotRecord(
                environment="mainnet",
                symbol="BTCUSDT",
                last_price=Decimal(1),
                bid_price=None,
                ask_price=None,
                event_time_ms=1,
                received_at="now",
                source="fixture",
            )
        )
    store.close()
