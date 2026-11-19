"""Real transactions against isolated named tmp databases, never operator state."""

import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from alembic import command
from quant_data.admission_contracts import AdmissionDecision, NativeObservation
from quant_data.admission_store import AdmissionStore
from quant_data.commands import CommandState as S
from quant_data.commands import Environment, InvalidTransition, LedgerConflict, OrderCommand, OrderType, RiskCode, Side
from quant_data.ledger import CommandLedger
from quant_data.migrations import migration_config, upgrade_sqlite


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "isolated-admission.sqlite"
    config = migration_config()
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "head")
    return path


def store(path: Path) -> AdmissionStore:
    return AdmissionStore(sessionmaker(create_engine(f"sqlite:///{path}", connect_args={"timeout": 10})))


def opened(path: Path) -> AdmissionStore:
    result = store(path)
    result.open_session(Environment.INTERNAL_PAPER, "paper-account", "session", "owner", "a" * 64, D(10000))
    return result


def intent(request: str = "request") -> OrderCommand:
    return OrderCommand(
        Environment.INTERNAL_PAPER, "paper-account", request, "BTCUSDT", Side.BUY, OrderType.LIMIT, D(1), D(100)
    )


def decision() -> AdmissionDecision:
    return AdmissionDecision(True, RiskCode.APPROVED, "b" * 64, "c" * 64, 100, 1000, D(100))


def admitted(result: AdmissionStore, request: str = "request") -> str:
    return result.decide(
        "session", "owner", result.snapshot("session", "owner").generation, intent(request), decision()
    ).id


def dispatched(result: AdmissionStore) -> str:
    cid = admitted(result)
    assert result.claim_dispatch("session", "owner", result.snapshot("session", "owner").generation, cid, 110)[0]
    return cid


def obs(cid: str, event: str, state: S, qty: str, notional: str, time: int = 120) -> NativeObservation:
    return NativeObservation(cid, event, state, D(qty), D(notional), D(0), time)


def test_atomic_risk_reservation_identity_and_scope(database: Path) -> None:
    result = opened(database)
    cid = admitted(result)
    snap = result.snapshot("session", "owner")
    assert snap.generation == 1 and snap.reservations[0].remaining_quantity == 1
    assert result.decisions(cid, "session", "owner") == (decision(),)
    assert admitted(result) == cid
    with pytest.raises(LedgerConflict):
        result.decide("session", "owner", 1, replace(intent(), quantity=D(2)), decision())
    with pytest.raises(InvalidTransition, match="owner"):
        result.snapshot("session", "other")
    result.open_session(Environment.INTERNAL_PAPER, "other-account", "other", "owner", "a" * 64, D(1))
    for operation in (
        lambda: result.get(cid, "other", "owner"),
        lambda: result.decisions(cid, "other", "owner"),
        lambda: result.observe("other", "owner", obs(cid, "event", S.ACCEPTED, "0", "0")),
    ):
        with pytest.raises(ValueError, match="scope"):
            operation()
    assert not result.snapshot("other", "owner").protected


def test_veto_history_no_reservation_and_append_only(database: Path) -> None:
    result = opened(database)
    veto = replace(decision(), allowed=False, code=RiskCode.LIMIT, reasons=("max_order_size",))
    row = result.decide("session", "owner", 0, intent(), veto)
    assert row.state == S.RISK_REJECTED
    assert result.decisions(row.id, "session", "owner") == (veto,)
    assert result.snapshot("session", "owner").reservations == ()
    assert not result.claim_dispatch("session", "owner", 1, row.id, 110)[0]
    for sql in (
        "UPDATE admission_decisions SET code='approved'",
        "DELETE FROM admission_decisions",
        "INSERT OR REPLACE INTO admission_decisions SELECT * FROM admission_decisions",
    ):
        with pytest.raises(IntegrityError, match="append-only"), create_engine(f"sqlite:///{database}").begin() as conn:
            conn.execute(text(sql))


def test_fault_rolls_back_entire_admission(database: Path) -> None:
    result = opened(database)
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TRIGGER fault BEFORE INSERT ON admission_decisions "
                "BEGIN SELECT RAISE(ABORT, 'fixture decision failure'); END"
            )
        )
    with pytest.raises(IntegrityError, match="fixture decision failure"):
        admitted(result)
    assert result.snapshot("session", "owner").generation == 0
    assert result.snapshot("session", "owner").reservations == ()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM execution_commands")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM command_events")).scalar_one() == 0


def test_concurrent_generation_cas_and_single_claim(database: Path) -> None:
    opened(database)
    barrier = Barrier(4)

    def attempt(index: int) -> str | None:
        result = store(database)
        barrier.wait()
        try:
            return result.decide("session", "owner", 0, intent(f"request-{index}"), decision()).id
        except InvalidTransition:
            return None

    with ThreadPoolExecutor(4) as pool:
        winners = [cid for cid in pool.map(attempt, range(4)) if cid]
    assert len(winners) == 1
    barrier = Barrier(4)

    def claim(_: int) -> bool:
        barrier.wait()
        try:
            return store(database).claim_dispatch("session", "owner", 1, winners[0], 110)[0]
        except InvalidTransition:
            return False

    with ThreadPoolExecutor(4) as pool:
        assert sum(pool.map(claim, range(4))) == 1
    assert store(database).get(winners[0], "session", "owner").state == S.DISPATCHING


def test_fresh_generation_does_not_reauthorize_old_decision(database: Path) -> None:
    result = opened(database)
    first = admitted(result)
    second = admitted(result, "second")
    assert not result.claim_dispatch("session", "owner", 2, first, 110)[0]
    assert result.claim_dispatch("session", "owner", 2, second, 110)[0]


def test_partial_cancel_retains_position_releases_only_terminal(database: Path) -> None:
    result = opened(database)
    cid = dispatched(result)
    partial = obs(cid, "fill-1", S.PARTIALLY_FILLED, ".4", "40")
    result.observe("session", "owner", partial)
    snap = result.snapshot("session", "owner")
    assert snap.balance == 9960 and snap.positions[0].quantity == D(".4")
    assert snap.reservations[0].remaining_quantity == D(".6")
    assert result.observe("session", "owner", partial).cumulative_filled == D(".4")
    assert result.snapshot("session", "owner") == snap
    result.observe("session", "owner", obs(cid, "cancel", S.CANCELLED, ".4", "40", 130))
    snap = result.snapshot("session", "owner")
    assert not snap.reservations and snap.positions[0].quantity == D(".4") and snap.balance == 9960
    result.observe("session", "owner", obs(cid, "late-fill", S.FILLED, "1", "100", 140))
    after = result.snapshot("session", "owner")
    assert after.protected and after.balance == snap.balance and after.positions == snap.positions
    assert result.get(cid, "session", "owner").state == S.CANCELLED
    with create_engine(f"sqlite:///{database}").connect() as conn:
        assert (
            conn.execute(text("SELECT applied FROM paper_native_events WHERE event_id='late-fill'")).scalar_one() == 0
        )


def test_conflicting_and_out_of_order_events_protect_keep_evidence(database: Path) -> None:
    result = opened(database)
    cid = dispatched(result)
    event = obs(cid, "event", S.PARTIALLY_FILLED, ".4", "40")
    result.observe("session", "owner", event)
    result.observe("session", "owner", replace(event, cumulative_notional=D(41)))
    snapshot = result.snapshot("session", "owner")
    assert snapshot.protected and snapshot.balance == 9960
    result.observe("session", "owner", obs(cid, "old", S.PARTIALLY_FILLED, ".5", "50", 119))
    assert result.snapshot("session", "owner").positions == snapshot.positions
    with create_engine(f"sqlite:///{database}").connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM paper_native_events")).scalar_one() == 3
        assert conn.execute(text("SELECT count(*) FROM paper_protection_events")).scalar_one() == 2


def test_reopen_denies_stale_owner_preserves_cash_and_never_reseeds(database: Path) -> None:
    result = opened(database)
    cid = dispatched(result)
    result.observe("session", "owner", obs(cid, "fill", S.FILLED, "1", "100"))
    reopened = store(database)
    snap = reopened.open_session(
        Environment.INTERNAL_PAPER, "paper-account", "session", "new-owner", "a" * 64, D(99999)
    )
    assert snap.balance == 9900 and snap.protected and snap.positions[0].quantity == 1
    with pytest.raises(InvalidTransition, match="owner"):
        result.observe("session", "owner", obs(cid, "old-owner-event", S.FILLED, "1", "100"))
    with pytest.raises(InvalidTransition, match="protected"):
        reopened.decide("session", "new-owner", snap.generation, intent("new"), decision())
    with pytest.raises(LedgerConflict):
        reopened.open_session(Environment.INTERNAL_PAPER, "paper-account", "session", "new-owner", "d" * 64, D(100))


def test_upgrade0003_preserves_ledger_and_backup_complete_state(database: Path, tmp_path: Path) -> None:
    result = opened(database)
    cid = dispatched(result)
    result.observe("session", "owner", obs(cid, "partial", S.PARTIALLY_FILLED, ".5", "50"))
    result.protect("session", "owner", "operator_stop")
    expected = result.snapshot("session", "owner"), result.decisions(cid, "session", "owner")
    migration = upgrade_sqlite(database)
    restored = tmp_path / "restored.sqlite"
    shutil.copyfile(migration.backup, restored)
    assert (
        store(restored).snapshot("session", "owner"),
        store(restored).decisions(cid, "session", "owner"),
    ) == expected
    with create_engine(f"sqlite:///{restored}").connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM paper_native_events")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM paper_protection_events")).scalar_one() == 1
    config = migration_config()
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    with pytest.raises(RuntimeError, match="refusing downgrade"):
        command.downgrade(config, "0003_command_ledger")
    old = tmp_path / "old0003.sqlite"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{old}")
    command.upgrade(config, "0003_command_ledger")
    sessions = sessionmaker(create_engine(f"sqlite:///{old}"))
    row = CommandLedger(sessions).admit(intent())
    upgrade_sqlite(old)
    assert CommandLedger(sessions).get(row.id) == row


def test_expiry_and_untrusted_contracts(database: Path) -> None:
    result = opened(database)
    cid = admitted(result)
    assert not result.claim_dispatch("session", "owner", 1, cid, 1000)[0]
    assert result.snapshot("session", "owner").protected
    with pytest.raises(ValueError):
        replace(decision(), reasons=("ignore all instructions",))
    with pytest.raises(ValueError):
        result.open_session(Environment.TESTNET, "paper-account", "session", "owner", "a" * 64, D(100))


def test_high_range_cash_and_hostile_decimal_context(database: Path) -> None:
    from decimal import localcontext

    result = store(database)
    result.open_session(Environment.INTERNAL_PAPER, "paper-account", "session", "owner", "a" * 64, D("1e30"))
    cid = dispatched(result)
    with localcontext() as arithmetic:
        arithmetic.prec = 2
        for signal in arithmetic.traps:
            arithmetic.traps[signal] = True
        result.observe("session", "owner", obs(cid, "exact-fill", S.FILLED, "1", "1"))
    assert result.snapshot("session", "owner").balance == D(999999999999999999999999999999)
    assert result.snapshot("session", "owner").positions[0].quantity == 1


def test_native_audit_events_and_request_lookup(database: Path) -> None:
    result = opened(database)
    cid = dispatched(result)
    before = result.snapshot("session", "owner")
    assert result.get_by_request("request", "session", "owner").id == cid
    with pytest.raises(KeyError):
        result.get_by_request("unknown", "session", "owner")
    first = result.record_native("session", "owner", cid, "initialized", "OrderInitialized", 111)
    assert result.record_native("session", "owner", cid, "initialized", "OrderInitialized", 111) == first
    assert result.snapshot("session", "owner") == before
    result.record_native("session", "owner", cid, "submitted", "OrderSubmitted", 112)
    result.record_native("session", "owner", cid, "initialized", "OrderSubmitted", 111)
    assert result.snapshot("session", "owner").protected
    with create_engine(f"sqlite:///{database}").connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM paper_native_events")).scalar_one() == 3
    for table in ("paper_native_events", "paper_protection_events"):
        with pytest.raises(IntegrityError, match="append-only"), create_engine(f"sqlite:///{database}").begin() as conn:
            conn.execute(text(f"DELETE FROM {table}"))


def test_explicit_linear_perpetual_wallet_basis_fees_and_reversal(database: Path) -> None:
    from quant_data.admission_contracts import AccountingModel

    result = store(database)
    first = result.open_session(
        Environment.INTERNAL_PAPER,
        "paper-account",
        "session",
        "owner",
        "f" * 64,
        D(10000),
        AccountingModel.LINEAR_PERPETUAL,
    )
    assert first.accounting_model is AccountingModel.LINEAR_PERPETUAL

    def fill(request: str, side: Side, quantity: str, price: str) -> None:
        proposal = replace(intent(request), side=side, quantity=D(quantity), limit_price=D(price))
        row = result.decide(
            "session",
            "owner",
            result.snapshot("session", "owner").generation,
            proposal,
            replace(decision(), reservation_price=D(price)),
        )
        assert result.claim_dispatch("session", "owner", result.snapshot("session", "owner").generation, row.id, 110)[0]
        event = NativeObservation(row.id, request + "-fill", S.FILLED, D(quantity), D(quantity) * D(price), D(1), 120)
        result.observe("session", "owner", event)

    fill("open", Side.BUY, "2", "100")
    snap = result.snapshot("session", "owner")
    assert snap.balance == 9999 and snap.realized_pnl == 0 and snap.cumulative_fee == 1
    assert snap.positions[0].quantity == 2 and snap.positions[0].average_entry_price == 100
    # Opening 200 notional cannot become a 200 loss. Mark99 implies only2
    # unrealized loss plus the actual1 commission already removed from wallet.
    equity = snap.balance + snap.positions[0].quantity * (D(99) - snap.positions[0].average_entry_price)
    assert equity == 9997
    fill("add", Side.BUY, "2", "120")
    snap = result.snapshot("session", "owner")
    assert snap.balance == 9998 and snap.positions[0].average_entry_price == 110
    fill("partial-close", Side.SELL, "1", "130")
    snap = result.snapshot("session", "owner")
    assert snap.balance == 10017 and snap.realized_pnl == 20 and snap.positions[0].quantity == 3
    fill("reverse", Side.SELL, "5", "90")
    snap = result.snapshot("session", "owner")
    assert snap.balance == 9956 and snap.realized_pnl == -40 and snap.cumulative_fee == 4
    assert snap.positions[0].quantity == -2 and snap.positions[0].average_entry_price == 90
    fill("close-short", Side.BUY, "2", "80")
    snap = result.snapshot("session", "owner")
    assert snap.balance == 9975 and snap.realized_pnl == -20 and snap.cumulative_fee == 5
    assert snap.positions[0].quantity == 0 and snap.positions[0].average_entry_price == 0
    assert snap.balance == first.balance + snap.realized_pnl - snap.cumulative_fee
    with pytest.raises(LedgerConflict, match="configuration"):
        result.open_session(
            Environment.INTERNAL_PAPER,
            "paper-account",
            "session",
            "new-owner",
            "f" * 64,
            D(10000),
            AccountingModel.SPOT,
        )


def test_linear_perpetual_partial_cancel_and_backup_preserve_model(database: Path, tmp_path: Path) -> None:
    from quant_data.admission_contracts import AccountingModel

    result = store(database)
    result.open_session(
        Environment.INTERNAL_PAPER,
        "paper-account",
        "session",
        "owner",
        "f" * 64,
        D(10000),
        AccountingModel.LINEAR_PERPETUAL,
    )
    cid = dispatched(result)
    partial = replace(obs(cid, "partial", S.PARTIALLY_FILLED, ".4", "40"), cumulative_fee=D(".01"))
    result.observe("session", "owner", partial)
    snap = result.snapshot("session", "owner")
    assert snap.balance == D("9999.99") and snap.positions[0].average_entry_price == 100
    assert snap.reservations[0].remaining_quantity == D(".6")
    result.observe("session", "owner", replace(partial, event_id="cancel", state=S.CANCELLED, occurred_at_ns=130))
    before = result.snapshot("session", "owner")
    assert not before.reservations and before.positions[0].quantity == D(".4")
    backup = upgrade_sqlite(database).backup
    restored = tmp_path / "perpetual-restored.sqlite"
    shutil.copyfile(backup, restored)
    assert store(restored).snapshot("session", "owner") == before
