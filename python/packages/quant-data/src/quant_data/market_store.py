"""Durable latest-market projection with an intentionally small interface."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session, sessionmaker

from .migrations import revision_is_at_least
from .models import MarketSnapshotProjection


@dataclass(frozen=True, slots=True)
class MarketSnapshotRecord:
    """Canonical persisted observation; it is not a freshness assertion."""

    environment: str
    symbol: str
    last_price: Decimal | None
    bid_price: Decimal | None
    ask_price: Decimal | None
    event_time_ms: int
    received_at: str
    source: str


class MarketSnapshotRepository(Protocol):
    """Store one current public observation per environment and symbol."""

    def upsert(self, record: MarketSnapshotRecord) -> None: ...

    def latest(self, environment: str, symbol: str) -> MarketSnapshotRecord | None: ...

    def close(self) -> None: ...


def _price_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError("market snapshot price is invalid")
    rendered = format(value, "f")
    if len(rendered) > 128:
        raise ValueError("market snapshot price is too large")
    return rendered


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise RuntimeError("stored market price is invalid") from error
    if not parsed.is_finite() or parsed <= 0:
        raise RuntimeError("stored market price is invalid")
    return parsed


class MarketSnapshotStore:
    """Own ORM details for one explicit, already-migrated SQLite database."""

    def __init__(self, sessions: sessionmaker[Session], *, engine: Engine | None = None) -> None:
        self._sessions = sessions
        self._engine = engine

    @classmethod
    def sqlite(cls, database: Path) -> MarketSnapshotStore:
        """Open an existing SQLite database; never create or migrate it."""
        target = database.expanduser().resolve()
        if not target.is_file():
            raise FileNotFoundError(f"market database does not exist: {target}")
        engine = create_engine(URL.create("sqlite", database=str(target)))
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            migrated = revision_is_at_least(connection, "0005_market_snapshot_projection")
        if "market_snapshot_projections" not in tables or not migrated:
            engine.dispose()
            raise RuntimeError("market database must be migrated to 0005_market_snapshot_projection")
        return cls(sessionmaker(engine, expire_on_commit=False), engine=engine)

    def upsert(self, record: MarketSnapshotRecord) -> None:
        """Atomically replace one environment/symbol projection."""
        self._validate(record)
        with self._sessions.begin() as session:
            row = session.scalar(
                select(MarketSnapshotProjection).where(
                    MarketSnapshotProjection.environment == record.environment,
                    MarketSnapshotProjection.symbol == record.symbol,
                )
            )
            values = {
                "last_price": _price_text(record.last_price),
                "bid_price": _price_text(record.bid_price),
                "ask_price": _price_text(record.ask_price),
                "event_time_ms": record.event_time_ms,
                "received_at": record.received_at,
                "source": record.source,
            }
            if row is None:
                session.add(MarketSnapshotProjection(environment=record.environment, symbol=record.symbol, **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)

    def latest(self, environment: str, symbol: str) -> MarketSnapshotRecord | None:
        with self._sessions() as session:
            row = session.scalar(
                select(MarketSnapshotProjection).where(
                    MarketSnapshotProjection.environment == environment,
                    MarketSnapshotProjection.symbol == symbol,
                )
            )
            if row is None:
                return None
            return MarketSnapshotRecord(
                environment=row.environment,
                symbol=row.symbol,
                last_price=_decimal(row.last_price),
                bid_price=_decimal(row.bid_price),
                ask_price=_decimal(row.ask_price),
                event_time_ms=row.event_time_ms,
                received_at=row.received_at,
                source=row.source,
            )

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

    @staticmethod
    def _validate(record: MarketSnapshotRecord) -> None:
        if record.environment != "testnet":
            raise ValueError("market snapshot environment must be testnet")
        if not record.symbol or len(record.symbol) > 32:
            raise ValueError("market snapshot symbol is invalid")
        if (
            type(record.event_time_ms) is not int
            or record.event_time_ms <= 0
            or not record.received_at
            or len(record.received_at) > 64
            or not record.source
            or len(record.source) > 128
        ):
            raise ValueError("market snapshot provenance is incomplete")
        for price in (record.last_price, record.bid_price, record.ask_price):
            _price_text(price)
