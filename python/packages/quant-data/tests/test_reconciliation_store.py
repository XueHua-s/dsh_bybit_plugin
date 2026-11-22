"""Exercise native account persistence on isolated SQLite/Alembic databases."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from alembic import command
from quant_data.commands import EmergencyState, LedgerConflict
from quant_data.migrations import upgrade_sqlite
from quant_data.models import EmergencyState as EmergencyStateRow
from quant_data.reconciliation_events import NativeEventEvidence
from quant_data.reconciliation_store import ReconciliationEvidence, ReconciliationStore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINGERPRINT = "a" * 64


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "execution.sqlite"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "head")
    return path


def store(path: Path) -> tuple[ReconciliationStore, Engine]:
    engine = create_engine(f"sqlite:///{path}")
    return ReconciliationStore(sessionmaker(engine)), engine


def opened(path: Path) -> tuple[ReconciliationStore, Engine]:
    result, engine = store(path)
    session = result.open_session("test-session", "account-alias", FINGERPRINT, expected_uid="uid-42")
    assert session.environment == "testnet"
    assert session.category == "linear"
    assert session.generation == 0 and session.protected
    assert session.status == EmergencyState.PROTECTED.value
    return result, engine


def evidence(
    revision: int,
    *,
    generation: int = 0,
    complete: bool = True,
    reason: str | None = None,
    observed_at_ns: int | None = None,
    orders: list[dict[str, str]] | None = None,
    native_events: tuple[NativeEventEvidence, ...] = (),
) -> ReconciliationEvidence:
    return ReconciliationEvidence(
        session_id="test-session",
        revision=revision,
        wallet={"account_type": "UNIFIED", "total_equity": "1000"},
        positions=[],
        orders=[] if orders is None else orders,
        executions=[],
        complete=complete,
        protected_reason=reason,
        observed_at_ns=revision if observed_at_ns is None else observed_at_ns,
        generation=generation,
        native_events=native_events,
    )


def native_event(
    event_id: str,
    *,
    state: str = "ACCEPTED",
    payload: dict[str, str] | None = None,
) -> NativeEventEvidence:
    return NativeEventEvidence(
        event_id=event_id,
        event_type="order",
        state=state,
        occurred_at_ns=10,
        payload={"state": state} if payload is None else payload,
        client_order_id=f"client-{event_id}",
        venue_order_id=f"venue-{event_id}",
    )


def test_account_identity_is_scoped_and_immutable(database: Path) -> None:
    result, engine = opened(database)
    try:
        same = result.open_session("test-session", "account-alias", FINGERPRINT, expected_uid="uid-42")
        assert same.session_id == "test-session"
        with pytest.raises(LedgerConflict, match="configuration mismatch"):
            result.open_session("test-session", "account-alias", FINGERPRINT, expected_uid="other-uid")
        with pytest.raises(LedgerConflict, match="another generation"):
            result.open_session("second-session", "account-alias", FINGERPRINT, expected_uid="uid-42")
        with pytest.raises(ValueError, match="only Testnet Linear"):
            result.open_session("spot-session", "spot-account", FINGERPRINT, expected_uid="uid-42", category="spot")
    finally:
        engine.dispose()


def test_restart_increments_generation_and_keeps_account_protected(database: Path) -> None:
    result, engine = opened(database)
    try:
        restarted = result.begin_generation("test-session", expected_generation=0)
        assert restarted.generation == 1
        assert restarted.protected
        assert restarted.protection_reason == "generation_requires_reconciliation"
        assert restarted.status == EmergencyState.PROTECTED.value
        with pytest.raises(LedgerConflict, match="stale account generation"):
            result.begin_generation("test-session", expected_generation=0)
        assert result.account_session("test-session").generation == 1
        with pytest.raises(LedgerConflict, match="stale reconciliation generation"):
            result.record(evidence(1, generation=0))
        assert result.record(evidence(1, generation=1)).generation == 1
    finally:
        engine.dispose()


def test_reconciliation_revisions_are_contiguous_and_idempotent(database: Path) -> None:
    result, engine = opened(database)
    try:
        first = result.record(evidence(1))
        assert result.record(evidence(1)) == first
        assert result.latest("test-session") == first
        assert first.complete and first.evidence_digest
        assert result.account_session("test-session").protected
        with pytest.raises(ValueError, match="contiguous"):
            result.record(evidence(3))
        with pytest.raises(LedgerConflict, match="different evidence"):
            result.record(evidence(1, orders=[{"symbol": "ETHUSDT", "status": "New"}]))
    finally:
        engine.dispose()


def test_incomplete_reconciliation_fences_account_and_complete_snapshot_does_not_unlock(database: Path) -> None:
    result, engine = opened(database)
    try:
        result.record(evidence(1, complete=False, reason="orders_page_missing"))
        incomplete = result.account_session("test-session")
        assert incomplete.protected and incomplete.protection_reason == "orders_page_missing"
        assert incomplete.status == EmergencyState.PROTECTED.value
        with sessionmaker(engine)() as session:
            emergency = session.get(EmergencyStateRow, "test-session")
            assert emergency is not None and emergency.state == EmergencyState.PROTECTED.value
        result.record(evidence(2))
        complete = result.account_session("test-session")
        assert complete.protected
        assert complete.protection_reason == "orders_page_missing"
        assert complete.reconciliation_revision == 2
    finally:
        engine.dispose()


def test_native_event_duplicate_is_inserted_once_and_replays_canonically(database: Path) -> None:
    result, engine = opened(database)
    try:
        event = native_event("evt-1")
        first = result.record(evidence(1, native_events=(event, event)))
        replay = result.record(evidence(1, native_events=(event,)))
        assert replay == first and first.complete
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM native_execution_events")).scalar_one() == 1
            assert connection.execute(text("SELECT applied FROM native_execution_events")).scalar_one() == 0

        second = result.record(evidence(2, native_events=(event,)))
        assert second.complete
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM native_execution_events")).scalar_one() == 1
    finally:
        engine.dispose()


def test_conflicting_native_event_batch_is_protected_and_replay_is_idempotent(database: Path) -> None:
    result, engine = opened(database)
    try:
        accepted = native_event("duplicate", state="ACCEPTED")
        filled = native_event("duplicate", state="FILLED")
        unrelated = native_event("unrelated")
        first = result.record(evidence(1, native_events=(accepted, filled, unrelated)))
        replay = result.record(evidence(1, native_events=(unrelated, filled, accepted)))
        assert replay == first
        assert not first.complete and first.protected_reason == "native_event_conflict"
        assert result.account_session("test-session").protected
        with engine.connect() as connection:
            event_ids = connection.execute(text("SELECT event_id FROM native_execution_events")).scalars().all()
            assert event_ids == ["unrelated"]
            assert connection.execute(text("SELECT applied FROM native_execution_events")).scalar_one() == 0
    finally:
        engine.dispose()


def test_native_event_batch_is_bounded_before_persistence(database: Path) -> None:
    result, engine = opened(database)
    try:
        events = tuple(native_event(f"event-{index}", payload={"data": "x" * 60_000}) for index in range(18))
        with pytest.raises(ValueError, match="native event batch exceeds bounded size"):
            result.record(evidence(1, native_events=events))
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM native_execution_events")).scalar_one() == 0
    finally:
        engine.dispose()


def test_existing_native_event_conflict_protects_a_running_account(database: Path) -> None:
    result, engine = opened(database)
    try:
        original = native_event("evt-1", state="ACCEPTED")
        result.record(evidence(1, observed_at_ns=1_000_000_000, native_events=(original,)))
        result.activate("test-session", 0, 1, 1_000_000_001)
        conflict = result.record(
            evidence(
                2,
                observed_at_ns=1_000_000_002,
                native_events=(native_event("evt-1", state="FILLED"),),
            )
        )
        assert not conflict.complete and conflict.protected_reason == "native_event_conflict"
        account = result.account_session("test-session")
        assert account.protected and account.status == EmergencyState.PROTECTED.value
        with sessionmaker(engine)() as session:
            emergency = session.get(EmergencyStateRow, "test-session")
            assert emergency is not None
            assert emergency.state == EmergencyState.PROTECTED.value
            assert emergency.reason == "native_event_conflict"
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("observed_at_ns", "activated_at_ns"),
    (
        (1_000_000_000, 31_000_000_001),  # older than the 30-second freshness window
        (10_000_000_001, 5_000_000_000),  # more than five seconds in the future
    ),
)
def test_activation_rejects_stale_or_future_reconciliation(
    database: Path, observed_at_ns: int, activated_at_ns: int
) -> None:
    result, engine = opened(database)
    try:
        result.record(evidence(1, observed_at_ns=observed_at_ns))
        with pytest.raises(ValueError, match="stale or future-dated"):
            result.activate("test-session", 0, 1, activated_at_ns)
        account = result.account_session("test-session")
        assert account.protected and account.status == EmergencyState.PROTECTED.value
    finally:
        engine.dispose()


def test_protect_synchronizes_durable_emergency_state(database: Path) -> None:
    result, engine = opened(database)
    try:
        result.record(evidence(1, observed_at_ns=10))
        result.activate("test-session", 0, 1, 11)

        result.protect("test-session", "operator_stop")

        with sessionmaker(engine)() as session:
            emergency = session.get(EmergencyStateRow, "test-session")
            assert emergency is not None
            assert emergency.state == EmergencyState.PROTECTED.value
            assert emergency.generation == 0
            assert emergency.reason == "operator_stop"
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "payload",
    (
        {"apiKey": "must-not-persist"},
        {"wallet": [{"access_token": "must-not-persist"}]},
        {"nested": {"private-key": "must-not-persist"}},
    ),
)
def test_reconciliation_rejects_credential_like_fields(payload: object) -> None:
    with pytest.raises(ValueError, match="credential-like"):
        ReconciliationEvidence(
            "test-session",
            1,
            payload,
            [],
            [],
            [],
            True,
            1,  # type: ignore[arg-type]
        )


def test_snapshot_rows_are_append_only_at_database_boundary(database: Path) -> None:
    result, engine = opened(database)
    try:
        result.record(evidence(1))
        with pytest.raises(IntegrityError, match="append-only"), engine.begin() as connection:
            connection.execute(text("UPDATE reconciliation_snapshots SET complete=0"))
        with pytest.raises(IntegrityError, match="append-only"), engine.begin() as connection:
            connection.execute(text("DELETE FROM reconciliation_snapshots"))
        with pytest.raises(IntegrityError, match="append-only"), engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT OR REPLACE INTO reconciliation_snapshots "
                    "(id, session_id, generation, revision, evidence_digest, wallet_json, positions_json, orders_json, "
                    "executions_json, complete, observed_at_ns) "
                    "VALUES (1, 'test-session', 0, 1, 'x', '{}', '[]', '[]', '[]', 1, 1)"
                )
            )
    finally:
        engine.dispose()


def test_migration_0007_keeps_existing_audit_rows_and_verified_backup(tmp_path: Path) -> None:
    database = tmp_path / "upgrade.sqlite"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "0006_ai_paper_decision_binding")
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO trade_events "
            "(event_type, environment, symbol, payload_json, created_at) "
            "VALUES ('risk_decision', 'testnet', 'ETHUSDT', '{\"allowed\":false}', '2026-01-01 00:00:00')"
        )
    engine.dispose()

    upgraded = upgrade_sqlite(database)
    restored = tmp_path / "restored.sqlite"
    shutil.copyfile(upgraded.backup, restored)
    with create_engine(f"sqlite:///{database}").connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0007_native_execution_state"
        )
        assert connection.execute(text("SELECT count(*) FROM account_sessions")).scalar_one() == 0
    with create_engine(f"sqlite:///{restored}").connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0006_ai_paper_decision_binding"
        )
        assert connection.execute(text("SELECT count(*) FROM trade_events")).scalar_one() == 1


def test_migration_refuses_downgrade_after_native_evidence(database: Path) -> None:
    result, engine = opened(database)
    try:
        result.record(evidence(1))
        downgrade_config = Config(str(PROJECT_ROOT / "alembic.ini"))
        downgrade_config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
        with pytest.raises(RuntimeError, match="contains user data"):
            command.downgrade(downgrade_config, "0006_ai_paper_decision_binding")
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "payload", ({"apiKey": "secret"}, {"access_token": "secret"}, {"nested": {"private-key": "secret"}})
)
def test_native_event_rejects_credential_like_fields(payload: object) -> None:
    with pytest.raises(ValueError, match="credential-like"):
        native_event("unsafe", payload=payload)  # type: ignore[arg-type]
