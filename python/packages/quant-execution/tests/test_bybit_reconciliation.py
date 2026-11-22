"""Offline reconciliation projection tests; no Bybit transport is used."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from quant_data.reconciliation_events import NativeEventEvidence
from quant_data.reconciliation_store import ReconciliationStore
from quant_execution.bybit_reconciliation import (
    BybitReconciliationBatch,
    BybitReconciliationProjector,
    ReconciliationError,
)
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2] / "quant-data"


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "execution.sqlite"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "head")
    return path


def opened(path: Path) -> tuple[ReconciliationStore, Engine]:
    engine = create_engine(f"sqlite:///{path}")
    store = ReconciliationStore(sessionmaker(engine))
    store.open_session("session", "account", "a" * 64, expected_uid="uid")
    return store, engine


def batch(**overrides: object) -> BybitReconciliationBatch:
    values: dict[str, object] = {
        "session_id": "session",
        "generation": 0,
        "revision": 1,
        "observed_at_ns": 1_000_000_000,
        "wallet": {
            "account_type": "UNIFIED",
            "total_equity_usdt": "1000",
            "available_margin_usdt": "900",
            "observed_at_ns": 1_000_000_000,
        },
        "positions": [],
        "orders": [],
        "executions": [],
        "expected_client_order_ids": (),
        "expected_venue_order_ids": (),
    }
    values.update(overrides)
    return BybitReconciliationBatch(**values)  # type: ignore[arg-type]


def order(
    *, status: str = "New", client_order_id: str | None = "client-1", filled_quantity: str = "0"
) -> dict[str, object]:
    return {
        "event_id": "order-event-1",
        "client_order_id": client_order_id,
        "venue_order_id": "venue-1",
        "symbol": "BTCUSDT",
        "side": "Buy",
        "status": status,
        "quantity": "1",
        "filled_quantity": filled_quantity,
        "timestamp_ns": 1_000_000_000,
        "reason": None,
    }


def execution(quantity: str) -> dict[str, object]:
    return {
        "event_id": "execution-event-1",
        "trade_id": "trade-1",
        "client_order_id": "client-1",
        "venue_order_id": "venue-1",
        "symbol": "BTCUSDT",
        "side": "Buy",
        "quantity": quantity,
        "price": "60000",
        "timestamp_ns": 1_000_000_000,
    }


def private_event() -> NativeEventEvidence:
    return NativeEventEvidence(
        event_id="private-1",
        event_type="order",
        state="ACCEPTED",
        occurred_at_ns=1_000_000_000,
        payload={"source": "private-stream", "status": "Accepted"},
        client_order_id="client-1",
        venue_order_id="venue-1",
    )


def test_rest_orders_and_executions_are_not_mislabelled_as_private_events(database: Path) -> None:
    store, engine = opened(database)
    try:
        result = BybitReconciliationProjector(store).project(
            batch(
                orders=[order(status="PartiallyFilled", filled_quantity="0.5")],
                executions=[execution("0.5")],
                expected_client_order_ids=("client-1",),
            ),
            now_ns=1_000_000_001,
        )
        assert result.complete
        assert result.orders == [
            {
                "event_id": "order-event-1",
                "client_order_id": "client-1",
                "venue_order_id": "venue-1",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "status": "PARTIALLY_FILLED",
                "quantity": "1",
                "filled_quantity": "0.5",
                "timestamp_ns": 1_000_000_000,
                "reason": None,
            }
        ]
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM native_execution_events")).scalar_one() == 0
    finally:
        engine.dispose()


def test_only_explicit_private_events_enter_native_event_ledger(database: Path) -> None:
    store, engine = opened(database)
    try:
        BybitReconciliationProjector(store).project(
            batch(
                private_events=(private_event(),),
                expected_client_order_ids=("client-1",),
                expected_venue_order_ids=("venue-1",),
            ),
            now_ns=1_000_000_001,
        )
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM native_execution_events")).scalar_one() == 1
            assert (
                connection.execute(text("SELECT payload_json FROM native_execution_events"))
                .scalar_one()
                .find("private-stream")
                >= 0
            )
    finally:
        engine.dispose()


def test_projector_protects_complete_fill_with_mismatched_execution_quantity(database: Path) -> None:
    store, engine = opened(database)
    try:
        result = BybitReconciliationProjector(store).project(
            batch(
                orders=[order(status="Filled", filled_quantity="1")],
                expected_client_order_ids=("client-1",),
            ),
            now_ns=1_000_000_001,
        )
        assert not result.complete
        assert result.protected_reason == "execution_fill_mismatch"
    finally:
        engine.dispose()


def test_projector_protects_unknown_order_identity(database: Path) -> None:
    store, engine = opened(database)
    try:
        result = BybitReconciliationProjector(store).project(
            batch(orders=[order(client_order_id=None)]),
            now_ns=1_000_000_001,
        )
        assert not result.complete
        assert result.protected_reason == "unknown_order_identity"
    finally:
        engine.dispose()


def test_projector_protects_unlinked_private_event_identity(database: Path) -> None:
    store, engine = opened(database)
    try:
        result = BybitReconciliationProjector(store).project(
            batch(private_events=(private_event(),)),
            now_ns=1_000_000_001,
        )
        assert not result.complete
        assert result.protected_reason == "unknown_private_event_identity"
    finally:
        engine.dispose()


def test_batch_rejects_string_identity_collection() -> None:
    with pytest.raises(ReconciliationError, match="identity_invalid"):
        batch(expected_client_order_ids="client-1")
