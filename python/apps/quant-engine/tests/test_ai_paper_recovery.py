"""Exercise the cycle-binding migration only against offline tmp_path SQLite."""

import socket
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

_ROOT = Path(__file__).resolve().parents[3] / "packages" / "quant-data"


def _config(database: Path) -> Config:
    resolved = database.resolve()
    config = Config(str(_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{resolved}")
    return config


def test_decision_binding_migration_isolated_downgrade_guard_and_restore(tmp_path: Path, monkeypatch) -> None:
    database = (tmp_path / "synthetic-paper.sqlite").resolve()
    assert database.is_relative_to(tmp_path.resolve())

    def deny_network(*_args, **_kwargs):
        raise AssertionError("network access is forbidden in paper migration tests")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket.socket, "connect", deny_network)
    config = _config(database)
    command.upgrade(config, "0005_market_snapshot_projection")
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO execution_commands "
                    "(id, environment, account_ref, request_id, fingerprint, command_json, "
                    "native_client_order_id, state, cumulative_filled, version) "
                    "VALUES ('cmd-1', 'internal_paper', 'SIM-001', 'req-1', 'fp', '{}', "
                    "'native-1', 'ready', '0', 0)"
                )
            )
        command.upgrade(config, "0006_ai_paper_decision_binding")
        assert "ai_paper_decision_bindings" in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT request_id FROM execution_commands")).scalar_one() == "req-1"
        command.downgrade(config, "0005_market_snapshot_projection")
        assert "ai_paper_decision_bindings" not in inspect(engine).get_table_names()
        command.upgrade(config, "0006_ai_paper_decision_binding")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO ai_paper_decision_bindings "
                    "(environment, account_ref, request_id, request_digest, decision_id, fixture_digest, "
                    "command_id, native_client_order_id, receipt_json) VALUES "
                    "('internal_paper', 'SIM-001', 'req-1', 'a', 'd', 'b', 'cmd-1', 'native-1', '{}')"
                )
            )
        with pytest.raises(RuntimeError, match="decision bindings contain durable paper receipts"):
            command.downgrade(config, "0005_market_snapshot_projection")
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM ai_paper_decision_bindings WHERE request_id='req-1'"))
            connection.execute(text("DELETE FROM execution_commands WHERE id='cmd-1'"))
        command.downgrade(config, "0005_market_snapshot_projection")
        assert "ai_paper_decision_bindings" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_cycle_binding_receipt_replay_and_conflicting_payload(tmp_path: Path) -> None:
    from decimal import Decimal

    from quant_data.admission_contracts import AccountingModel, AdmissionDecision
    from quant_data.admission_store import AdmissionStore
    from quant_data.commands import Environment, LedgerConflict, OrderCommand, OrderType, RiskCode, Side
    from sqlalchemy.orm import sessionmaker

    database = (tmp_path / "cycle-binding.sqlite").resolve()
    assert database.is_relative_to(tmp_path.resolve())
    command.upgrade(_config(database), "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        store = AdmissionStore(sessionmaker(engine, expire_on_commit=False))
        snapshot = store.open_session(
            Environment.INTERNAL_PAPER,
            "SIM-001",
            "session-1",
            "owner-1",
            "a" * 64,
            Decimal(1000),
            AccountingModel.LINEAR_PERPETUAL,
        )
        intent = OrderCommand(
            Environment.INTERNAL_PAPER,
            "SIM-001",
            "request-1",
            "ALPHA-PERP",
            Side.BUY,
            OrderType.LIMIT,
            Decimal(1),
            Decimal(10),
        )
        decision = AdmissionDecision(
            True,
            RiskCode.APPROVED,
            "b" * 64,
            "c" * 64,
            100,
            1000,
            Decimal(10),
            (),
        )
        binding = {"decision_request_digest": "d" * 64, "decision_id": "decision-1", "fixture_digest": "e" * 64}
        first = store.decide("session-1", "owner-1", snapshot.generation, intent, decision, **binding)
        receipt = store.get_decision_receipt("request-1", "session-1", "owner-1")
        assert receipt["command_id"] == first.id
        assert receipt["native_client_order_id"] == first.native_client_order_id
        replay = store.decide("session-1", "owner-1", snapshot.generation, intent, decision, **binding)
        assert replay.id == first.id
        with pytest.raises(LedgerConflict, match="decision request binding conflict"):
            store.decide(
                "session-1",
                "owner-1",
                snapshot.generation,
                intent,
                decision,
                decision_request_digest="f" * 64,
                decision_id="decision-1",
                fixture_digest="e" * 64,
            )
    finally:
        engine.dispose()


def test_append_only_cycle_receipt_replays_terminal_no_order_state(tmp_path: Path) -> None:
    from decimal import Decimal

    from quant_data.admission_contracts import AccountingModel
    from quant_data.admission_store import AdmissionStore
    from quant_data.commands import Environment, LedgerConflict
    from quant_data.cycle_receipt_store import CycleReceiptStore
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker

    database = (tmp_path / "cycle-receipt.sqlite").resolve()
    assert database.is_relative_to(tmp_path.resolve())
    command.upgrade(_config(database), "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        sessions = sessionmaker(engine, expire_on_commit=False)
        admission = AdmissionStore(sessions)
        admission.open_session(
            Environment.INTERNAL_PAPER,
            "SIM-001",
            "session-r",
            "owner-r",
            "a" * 64,
            Decimal(1000),
            AccountingModel.LINEAR_PERPETUAL,
        )
        store = CycleReceiptStore(sessions)
        receipt, created = store.begin(
            "session-r",
            "owner-r",
            "request-r",
            "b" * 64,
            "decision-r",
            "c" * 64,
            claim_owner="worker-r",
            claim_deadline_ns=time.time_ns() + 60_000_000_000,
        )
        assert created and receipt["status"] == "claimed"
        selected = store.append("session-r", "owner-r", "request-r", "selected", strategy_digest="d" * 64)
        terminal = store.append("session-r", "owner-r", "request-r", "abstained", reason="selector_abstained")
        replay, created = store.begin(
            "session-r",
            "owner-r",
            "request-r",
            "b" * 64,
            "decision-r",
            "c" * 64,
            claim_owner="worker-r",
            claim_deadline_ns=time.time_ns() + 60_000_000_000,
        )
        assert not created and replay == terminal and selected["status"] == "selected"
        events = terminal["events"]
        assert isinstance(events, list)
        assert all(isinstance(event, dict) for event in events)
        assert [event["sequence"] for event in events] == [0, 1, 2]
        assert store.get("session-r", "owner-r", "request-r") == terminal
        with pytest.raises(LedgerConflict, match="payload conflict"):
            store.begin(
                "session-r",
                "owner-r",
                "request-r",
                "e" * 64,
                "decision-r",
                "c" * 64,
                claim_owner="worker-r",
                claim_deadline_ns=time.time_ns() + 60_000_000_000,
            )
        with engine.begin() as connection:
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(text("UPDATE ai_paper_cycle_events SET status='unknown' WHERE receipt_id=1"))
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(text("DELETE FROM ai_paper_cycle_events WHERE receipt_id=1"))
    finally:
        engine.dispose()


def test_concurrent_cycle_begin_creates_one_claim_owner(tmp_path: Path) -> None:
    from decimal import Decimal

    from quant_data.admission_contracts import AccountingModel
    from quant_data.admission_store import AdmissionStore
    from quant_data.commands import Environment
    from quant_data.cycle_receipt_store import CycleReceiptStore
    from sqlalchemy.orm import sessionmaker

    database = (tmp_path / "cycle-claim-race.sqlite").resolve()
    assert database.is_relative_to(tmp_path.resolve())
    command.upgrade(_config(database), "head")
    engine = create_engine(f"sqlite:///{database}", connect_args={"check_same_thread": False})
    try:
        sessions = sessionmaker(engine, expire_on_commit=False)
        admission = AdmissionStore(sessions)
        admission.open_session(
            Environment.INTERNAL_PAPER,
            "SIM-001",
            "session-race",
            "owner-race",
            "a" * 64,
            Decimal(1000),
            AccountingModel.LINEAR_PERPETUAL,
        )
        deadline = time.time_ns() + 60_000_000_000

        def start(worker: str):
            return CycleReceiptStore(sessions).begin(
                "session-race",
                "owner-race",
                "request-race",
                "b" * 64,
                "decision-race",
                "c" * 64,
                claim_owner=worker,
                claim_deadline_ns=deadline,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = tuple(pool.map(start, ("worker-one", "worker-two")))
        assert sorted((first[1], second[1])) == [False, True]
        assert first[0]["status"] == second[0]["status"] == "claimed"
        assert first[0]["claim_owner"] == second[0]["claim_owner"]
        assert first[0]["claim_owner"] in {"worker-one", "worker-two"}
        events = first[0]["events"]
        assert isinstance(events, list)
        assert len(events) == 1
    finally:
        engine.dispose()
