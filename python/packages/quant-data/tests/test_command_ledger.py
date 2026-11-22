"""Ledger contract tests on named, isolated pytest SQLite targets; no exchange IO."""

import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from threading import Barrier

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from alembic import command
from quant_data.commands import (
    CommandState as S,
)
from quant_data.commands import (
    Environment,
    InvalidTransition,
    LedgerConflict,
    OrderCommand,
    OrderType,
    RiskCode,
    Side,
)
from quant_data.ledger import CommandLedger
from quant_data.migrations import upgrade_sqlite
from quant_data.reconciliation_store import ReconciliationEvidence, ReconciliationStore

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "command-ledger-test.sqlite"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "head")
    with create_engine(f"sqlite:///{path}").connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0007_native_execution_state"
        )
        assert {"execution_commands", "command_events", "market_snapshot_projections"} <= set(
            inspect(connection).get_table_names()
        )
    return path


def ledger(path: Path) -> CommandLedger:
    return CommandLedger(sessionmaker(create_engine(f"sqlite:///{path}", connect_args={"timeout": 10})))


def native_ready(path: Path) -> tuple[CommandLedger, ReconciliationStore]:
    engine = create_engine(f"sqlite:///{path}", connect_args={"timeout": 10})
    sessions = sessionmaker(engine)
    reconciliation = ReconciliationStore(sessions)
    reconciliation.open_session("native-session", "account-fixture", "b" * 64, expected_uid="uid-1")
    reconciliation.record(
        ReconciliationEvidence("native-session", 1, {"total_equity": "1000"}, [], [], [], True, 1, generation=0)
    )
    reconciliation.activate("native-session", 0, 1, 2)
    return CommandLedger(sessions), reconciliation


def native_admit(store: CommandLedger, request_id: str = "native-request") -> str:
    row = store.admit_native(
        replace(intent(), request_id=request_id),
        "native-session",
        0,
        1,
        True,
        RiskCode.APPROVED,
        policy_fingerprint="c" * 64,
        context_fingerprint="d" * 64,
        evaluated_at_ns=10,
        expires_at_ns=100,
        reservation_price=Decimal(100),
    )
    assert row.state == S.READY
    return row.id


def intent() -> OrderCommand:
    return OrderCommand(
        Environment.TESTNET,
        "account-fixture",
        "request-1",
        "BTCUSDT",
        Side.BUY,
        OrderType.LIMIT,
        Decimal("1.00"),
        Decimal("100.00"),
    )


def dispatched(store: CommandLedger, request: str = "request-1") -> str:
    row = store.admit(replace(intent(), request_id=request))
    store.decide_risk(row.id, True, RiskCode.APPROVED)
    won, result = store.claim_dispatch(row.id)
    assert won and result.state == S.DISPATCHING
    return row.id


def test_admission_idempotent_scope_conflict_and_reopen(database: Path) -> None:
    store = ledger(database)
    original = store.admit(intent())
    equal = store.admit(replace(intent(), quantity=Decimal(1), limit_price=Decimal(100)))
    assert equal == original
    assert ledger(database).admit(intent()) == original
    for change in ({"quantity": Decimal(2)}, {"side": Side.SELL}, {"reduce_only": True}):
        with pytest.raises(LedgerConflict):
            store.admit(replace(intent(), **change))
    for change in ({"account_ref": "another-account"}, {"environment": Environment.DEMO}):
        other = store.admit(replace(intent(), **change))
        assert other.id != original.id
        assert other.native_client_order_id != original.native_client_order_id
    assert len(store.events(original.id)) == 1
    assert len(original.native_client_order_id) <= 36


def test_separate_session_concurrent_admission_and_dispatch(database: Path) -> None:
    barrier = Barrier(6)

    def admit(_: int) -> str:
        store = ledger(database)  # independent Engine, Session factory and connections
        barrier.wait()
        return store.admit(intent()).id

    with ThreadPoolExecutor(6) as pool:
        ids = list(pool.map(admit, range(6)))
    assert len(set(ids)) == 1
    store = ledger(database)
    store.decide_risk(ids[0], True, RiskCode.APPROVED)
    dispatch_barrier = Barrier(6)

    def claim(_: int) -> bool:
        separate = ledger(database)
        dispatch_barrier.wait()
        return separate.claim_dispatch(ids[0])[0]

    with ThreadPoolExecutor(6) as pool:
        winners = list(pool.map(claim, range(6)))
    assert sum(winners) == 1
    assert [event.state for event in store.events(ids[0])] == [S.ADMITTED, S.READY, S.DISPATCHING]


def test_risk_rejection_audited_and_cannot_dispatch(database: Path) -> None:
    store = ledger(database)
    row = store.admit(intent())
    rejected = store.decide_risk(row.id, False, RiskCode.BALANCE)
    assert rejected.state == S.RISK_REJECTED
    assert store.decide_risk(row.id, False, RiskCode.BALANCE) == rejected
    assert not store.claim_dispatch(row.id)[0]
    assert ledger(database).events(row.id)[-1].decision_code == RiskCode.BALANCE
    with pytest.raises(LedgerConflict):
        store.decide_risk(row.id, True, RiskCode.APPROVED)
    with pytest.raises(ValueError):
        store.decide_risk(row.id, True, RiskCode.ACCOUNT)


def test_native_admission_requires_complete_active_reconciliation_and_reserves(database: Path) -> None:
    store, _ = native_ready(database)
    command_id = native_admit(store)
    with create_engine(f"sqlite:///{database}").connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM execution_reservations WHERE command_id=:id"), {"id": command_id}
            ).scalar_one()
            == 1
        )
    assert store.claim_native_dispatch(command_id, "native-session", 0, 1, 99)[0]


def test_native_admission_rejects_protected_and_incomplete_account(database: Path) -> None:
    engine = create_engine(f"sqlite:///{database}", connect_args={"timeout": 10})
    reconciliation = ReconciliationStore(sessionmaker(engine))
    reconciliation.open_session("native-session", "account-fixture", "b" * 64, expected_uid="uid-1")
    reconciliation.record(
        ReconciliationEvidence(
            "native-session",
            1,
            {"total_equity": "1000"},
            [],
            [],
            [],
            False,
            1,
            generation=0,
            protected_reason="missing_orders_page",
        )
    )
    with pytest.raises(InvalidTransition, match="protected"):
        native_admit(ledger(database))


def test_native_rejected_risk_has_no_reservation(database: Path) -> None:
    store, _ = native_ready(database)
    row = store.admit_native(
        replace(intent(), request_id="rejected-native"),
        "native-session",
        0,
        1,
        False,
        RiskCode.BALANCE,
        policy_fingerprint="c" * 64,
        context_fingerprint="d" * 64,
        evaluated_at_ns=10,
        expires_at_ns=100,
        reservation_price=Decimal(100),
    )
    assert row.state == S.RISK_REJECTED
    with create_engine(f"sqlite:///{database}").connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM execution_reservations")).scalar_one() == 0
    assert not store.claim_native_dispatch(row.id, "native-session", 0, 1, 99)[0]


@pytest.mark.parametrize("change", ["generation", "revision", "expiry", "emergency"])
def test_native_dispatch_rechecks_generation_revision_expiry_and_emergency(database: Path, change: str) -> None:
    store, reconciliation = native_ready(database)
    command_id = native_admit(store, request_id=f"stale-{change}")
    if change == "generation":
        reconciliation.begin_generation("native-session", 0)
        args = ("native-session", 0, 1, 99)
    elif change == "revision":
        reconciliation.record(
            ReconciliationEvidence("native-session", 2, {"total_equity": "1000"}, [], [], [], True, 3, generation=0)
        )
        reconciliation.activate("native-session", 0, 2, 4)
        args = ("native-session", 0, 1, 99)
    elif change == "expiry":
        args = ("native-session", 0, 1, 100)
    else:
        reconciliation.protect("native-session", "operator_stop")
        args = ("native-session", 0, 1, 99)
    assert not store.claim_native_dispatch(command_id, *args)[0]


def test_native_admission_idempotency_conflict_and_single_claim(database: Path) -> None:
    store, _ = native_ready(database)
    command_id = native_admit(store)
    assert native_admit(store) == command_id
    with pytest.raises(LedgerConflict):
        store.admit_native(
            replace(intent(), request_id="native-request", quantity=Decimal(2)),
            "native-session",
            0,
            1,
            True,
            RiskCode.APPROVED,
            policy_fingerprint="c" * 64,
            context_fingerprint="d" * 64,
            evaluated_at_ns=10,
            expires_at_ns=100,
            reservation_price=Decimal(100),
        )
    barrier = Barrier(6)

    def claim(_: int) -> bool:
        separate = ledger(database)
        barrier.wait()
        return separate.claim_native_dispatch(command_id, "native-session", 0, 1, 99)[0]

    with ThreadPoolExecutor(6) as pool:
        assert sum(pool.map(claim, range(6))) == 1


def test_native_idempotent_replay_returns_receipt_while_protected(database: Path) -> None:
    store, reconciliation = native_ready(database)
    command_id = native_admit(store)
    reconciliation.protect("native-session", "operator_stop")
    assert native_admit(store) == command_id
    assert not store.claim_native_dispatch(command_id, "native-session", 0, 1, 99)[0]


def test_native_dispatch_fails_closed_when_emergency_projection_is_missing(database: Path) -> None:
    store, _ = native_ready(database)
    command_id = native_admit(store)
    with create_engine(f"sqlite:///{database}").begin() as connection:
        connection.execute(text("DELETE FROM emergency_states WHERE session_id='native-session'"))

    assert not store.claim_native_dispatch(command_id, "native-session", 0, 1, 99)[0]


def test_partial_fill_event_idempotency_and_terminal_guards(database: Path) -> None:
    store = ledger(database)
    cid = dispatched(store)
    store.observe(cid, "venue-accepted", S.ACCEPTED, Decimal(0))
    partial = store.observe(cid, "venue-fill-1", S.PARTIALLY_FILLED, Decimal("0.4"))
    assert store.observe(cid, "venue-fill-1", S.PARTIALLY_FILLED, Decimal("0.40")) == partial
    with pytest.raises(LedgerConflict):
        store.observe(cid, "venue-fill-1", S.PARTIALLY_FILLED, Decimal("0.5"))
    for state, quantity in (
        (S.ACCEPTED, "0"),
        (S.CANCELLED, "0.2"),
        (S.FILLED, "0.9"),
        (S.PARTIALLY_FILLED, "1"),
        (S.FILLED, "1.1"),
    ):
        with pytest.raises(InvalidTransition):
            store.observe(cid, "invalid", state, Decimal(quantity))
    complete = store.observe(cid, "venue-fill-2", S.FILLED, Decimal(1))
    assert complete.cumulative_filled == Decimal(1)
    assert store.observe(cid, "venue-fill-1", S.PARTIALLY_FILLED, Decimal("0.4")) == complete
    with pytest.raises(InvalidTransition):
        store.observe(cid, "late-accepted", S.ACCEPTED, Decimal(0))
    assert len(store.events(cid)) == 6


def test_cancel_preserves_partial_fill_and_late_fill_requires_reconciliation(database: Path) -> None:
    store = ledger(database)
    cid = dispatched(store)
    store.observe(cid, "fill", S.PARTIALLY_FILLED, Decimal("0.4"))
    cancelled = store.observe(cid, "cancel", S.CANCELLED, Decimal("0.4"))
    assert cancelled.cumulative_filled == Decimal("0.4")
    with pytest.raises(InvalidTransition, match="reconcile late reports"):
        store.observe(cid, "late-fill", S.FILLED, Decimal(1))
    assert store.get(cid) == cancelled  # NOT evidence of a flat account
    other = dispatched(store, "other")
    assert store.observe(other, "cancel", S.CANCELLED, Decimal(0)).state == S.CANCELLED


def test_recovery_never_resubmits_and_external_resolution_required(database: Path) -> None:
    store = ledger(database)
    cid = dispatched(store)
    identity = store.get(cid).native_client_order_id
    restarted = ledger(database)
    assert restarted.recover_inflight()[0].state == S.RECONCILIATION_REQUIRED
    assert restarted.recover_inflight() == ()
    assert not restarted.claim_dispatch(cid)[0]
    assert restarted.admit(intent()).native_client_order_id == identity
    assert restarted.observe(cid, "reconciled-fill", S.FILLED, Decimal(1)).state == S.FILLED


def test_append_only_and_downgrade_guard_and_backup_roundtrip(database: Path, tmp_path: Path) -> None:
    store = ledger(database)
    cid = dispatched(store)
    store.observe(cid, "fill", S.PARTIALLY_FILLED, Decimal("0.2"))
    before = store.get(cid), store.events(cid)
    engine = create_engine(f"sqlite:///{database}")
    for statement in ("UPDATE command_events SET state='filled'", "DELETE FROM command_events"):
        with pytest.raises(IntegrityError, match="append-only"), engine.begin() as connection:
            connection.execute(text(statement))
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    with pytest.raises(RuntimeError, match="refusing downgrade"):
        command.downgrade(config, "0002_strategy_config")
    engine.dispose()
    result = upgrade_sqlite(database)  # isolated fixture only; head->head yields verified backup
    restore = tmp_path / "command-ledger-restored-test.sqlite"
    shutil.copyfile(result.backup, restore)
    restored = ledger(restore)
    assert (restored.get(cid), restored.events(cid)) == before
    assert restored.admit(intent()).native_client_order_id == before[0].native_client_order_id
    assert restored.recover_inflight() == ()


@pytest.mark.parametrize("quantity", [Decimal("NaN"), Decimal("Infinity"), Decimal(-1), Decimal(0), Decimal("1e-19")])
def test_hostile_quantity_rejected(quantity: Decimal) -> None:
    with pytest.raises(ValueError):
        replace(intent(), quantity=quantity)


def test_no_arbitrary_payload_mainnet_or_reserved_events(database: Path) -> None:
    with pytest.raises(ValueError):
        Environment("mainnet")
    with pytest.raises(ValueError):
        replace(intent(), account_ref="untrusted\ntext")
    with pytest.raises(ValueError):
        replace(intent(), order_type=OrderType.MARKET)
    store = ledger(database)
    cid = dispatched(store)
    with pytest.raises(ValueError):
        store.observe(cid, "internal:dispatch", S.FILLED, Decimal(1))


@pytest.mark.parametrize("price", [Decimal("-0"), Decimal(0), Decimal("0E+1000000000")])
def test_zero_limit_price_rejected(price: Decimal) -> None:
    with pytest.raises(ValueError):
        replace(intent(), limit_price=price)


def test_zero_canonical_and_audit_replace_cannot_overwrite(database: Path) -> None:
    from quant_data.commands import decimal_text

    assert decimal_text(Decimal("-0")) == "0"
    assert decimal_text(Decimal("0E+1000000000")) == "0"
    store = ledger(database)
    cid = dispatched(store)
    before = store.events(cid)
    with pytest.raises(IntegrityError, match="append-only"), create_engine(f"sqlite:///{database}").begin() as conn:
        conn.execute(
            text(
                "INSERT OR REPLACE INTO command_events "
                "SELECT id, command_id, event_id, fingerprint, 'filled', cumulative_filled, "
                "decision_code, version, created_at FROM command_events WHERE command_id=:cid"
            ),
            {"cid": cid},
        )
    assert store.events(cid) == before


def test_concurrent_same_observation_is_idempotent(database: Path) -> None:
    store = ledger(database)
    cid = dispatched(store)
    barrier = Barrier(6)

    def observe(_: int) -> str:
        separate = ledger(database)
        barrier.wait()
        return separate.observe(cid, "shared-fill", S.PARTIALLY_FILLED, Decimal("0.4")).id

    with ThreadPoolExecutor(6) as pool:
        assert set(pool.map(observe, range(6))) == {cid}
    assert len(store.events(cid)) == 4


def test_audit_insert_failure_rolls_back_state_and_version(database: Path) -> None:
    store = ledger(database)
    cid = dispatched(store)
    before = store.get(cid), store.events(cid)
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER fixture_reject_event BEFORE INSERT ON command_events "
                "WHEN NEW.event_id='fault-injection' "
                "BEGIN SELECT RAISE(ABORT, 'fixture audit failure'); END"
            )
        )
    with pytest.raises(IntegrityError, match="fixture audit failure"):
        store.observe(cid, "fault-injection", S.FILLED, Decimal(1))
    assert (store.get(cid), store.events(cid)) == before
