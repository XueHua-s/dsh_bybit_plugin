"""Native report evidence and conservative transactional paper accounting."""

from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from sqlalchemy.orm import Session

from quant_data.admission_contracts import AccountingModel, NativeObservation, timestamp
from quant_data.admission_models import (
    NativeEvent,
    PaperPosition,
    PaperSession,
    ProtectionEvent,
    Reservation,
    RiskDecision,
)
from quant_data.commands import CommandRecord, InvalidTransition, Side, canonical, decimal_text, fingerprint
from quant_data.commands import CommandState as S
from quant_data.ledger import _record, _required, _transition_in_session


def observe(session: Session, paper: PaperSession, observation: NativeObservation) -> CommandRecord:
    with localcontext() as arithmetic:
        # Contracts permit 31 integer and 18 fractional places. All additions,
        # subtraction and signed projections must remain independent of caller
        # Decimal settings, including hostile low precision/trap contexts.
        arithmetic.prec = 100
        arithmetic.rounding = ROUND_HALF_EVEN
        arithmetic.Emax, arithmetic.Emin = 999, -999
        for signal in arithmetic.traps:
            arithmetic.traps[signal] = False
        return _observe(session, paper, observation)


def _observe(session: Session, paper: PaperSession, observation: NativeObservation) -> CommandRecord:
    decision = session.get(RiskDecision, observation.command_id)
    if decision is None or decision.session_id != paper.id:
        raise ValueError("native command/session scope mismatch")
    row = _required(session, observation.command_id)
    record = _record(row)
    payload = canonical(
        {
            "command_id": observation.command_id,
            "state": observation.state.value,
            "filled": decimal_text(observation.cumulative_filled),
            "notional": decimal_text(observation.cumulative_notional),
            "fee": decimal_text(observation.cumulative_fee),
            "time_ns": str(observation.occurred_at_ns),
        }
    )
    digest = fingerprint(payload)
    prior = session.get(NativeEvent, (paper.id, observation.event_id))
    if prior is not None:
        if prior.fingerprint != digest:
            protect_record(session, paper, "native_event_conflict")
            # Keep the original identity immutable; retain a bounded derived
            # conflict identity so the attempted structured facts survive too.
            conflict_id = "conflict:" + fingerprint(observation.event_id + digest)
            if session.get(NativeEvent, (paper.id, conflict_id)) is None:
                session.add(_evidence(paper.id, conflict_id, observation, digest, False))
        return record
    reservation = session.get(Reservation, observation.command_id)
    try:
        if reservation is None:
            raise InvalidTransition("native event lacks admitted reservation")
        if observation.occurred_at_ns < reservation.last_event_ns:
            raise InvalidTransition("out of order native event")
        if observation.cumulative_notional < Decimal(
            reservation.cumulative_notional
        ) or observation.cumulative_fee < Decimal(reservation.cumulative_fee):
            raise InvalidTransition("cumulative accounting regressed")
        delta_quantity = observation.cumulative_filled - record.cumulative_filled
        delta_notional = observation.cumulative_notional - Decimal(reservation.cumulative_notional)
        delta_fee = observation.cumulative_fee - Decimal(reservation.cumulative_fee)
        if delta_quantity == 0 and delta_notional != 0 or delta_quantity > 0 and delta_notional <= 0:
            raise InvalidTransition("fill accounting inconsistent")
        # Savepoint ensures malformed evidence can be retained/protect the
        # session without committing a partially advanced ledger or projection.
        with session.begin_nested():
            result = _transition_in_session(
                session, row.id, observation.event_id, observation.state, observation.cumulative_filled, None, None
            )
            position = session.get(PaperPosition, (paper.id, record.command.symbol))
            if position is None:
                position = PaperPosition(
                    session_id=paper.id, symbol=record.command.symbol, quantity="0", average_entry_price="0"
                )
                session.add(position)
            sign = Decimal(1) if record.command.side is Side.BUY else Decimal(-1)
            _project_fill(paper, position, sign, delta_quantity, delta_notional, delta_fee)
            reservation.remaining_quantity = decimal_text(
                Decimal(0)
                if observation.state in {S.FILLED, S.CANCELLED, S.REJECTED}
                else record.command.quantity - observation.cumulative_filled
            )
            reservation.cumulative_notional = decimal_text(observation.cumulative_notional)
            reservation.cumulative_fee = decimal_text(observation.cumulative_fee)
            reservation.last_event_ns = observation.occurred_at_ns
            if observation.state is S.RECONCILIATION_REQUIRED:
                protect_record(session, paper, "native_reconciliation_required")
            session.flush()
        applied = True
    except InvalidTransition:
        protect_record(session, paper, "native_report_requires_reconciliation")
        result, applied = _record(_required(session, observation.command_id)), False
    session.add(_evidence(paper.id, observation.event_id, observation, digest, applied))
    paper.generation += 1
    session.flush()
    return result


def protect_record(session: Session, paper: PaperSession, reason: str) -> None:
    paper.protected = 1
    if paper.protection_reason is None:
        paper.protection_reason = reason
    paper.generation += 1
    session.add(ProtectionEvent(session_id=paper.id, generation=paper.generation, reason=reason))


def _evidence(
    session_id: str, event_id: str, observation: NativeObservation, digest: str, applied: bool
) -> NativeEvent:
    return NativeEvent(
        session_id=session_id,
        event_id=event_id,
        command_id=observation.command_id,
        fingerprint=digest,
        state=observation.state.value,
        cumulative_filled=decimal_text(observation.cumulative_filled),
        cumulative_notional=decimal_text(observation.cumulative_notional),
        cumulative_fee=decimal_text(observation.cumulative_fee),
        occurred_at_ns=observation.occurred_at_ns,
        applied=int(applied),
    )


def record_native(
    session: Session, paper: PaperSession, command_id: str, event_id: str, event_type: str, occurred_at_ns: int
) -> CommandRecord:
    """Retain native identity for events that do not advance ledger lifecycle."""
    from quant_data.commands import identifier

    allowed = {
        "OrderInitialized",
        "OrderSubmitted",
        "OrderPendingUpdate",
        "OrderPendingCancel",
        "OrderUpdated",
        "OrderTriggered",
        "OrderCancelRejected",
        "OrderModifyRejected",
    }
    identifier(event_id, "event_id")
    if event_id.startswith("internal:") or event_type not in allowed:
        raise ValueError("unsupported native audit event")
    timestamp(occurred_at_ns)
    decision = session.get(RiskDecision, command_id)
    if decision is None or decision.session_id != paper.id:
        raise ValueError("native command/session scope mismatch")
    record = _record(_required(session, command_id))
    digest = fingerprint(
        canonical({"command_id": command_id, "event_type": event_type, "time_ns": str(occurred_at_ns)})
    )
    prior = session.get(NativeEvent, (paper.id, event_id))
    if prior is not None and prior.fingerprint == digest:
        return record
    if prior is not None:
        protect_record(session, paper, "native_event_conflict")
        event_id = "conflict:" + fingerprint(event_id + digest)
        if session.get(NativeEvent, (paper.id, event_id)) is not None:
            return record
    session.add(
        NativeEvent(
            session_id=paper.id,
            event_id=event_id,
            command_id=command_id,
            fingerprint=digest,
            state=event_type,
            cumulative_filled=decimal_text(record.cumulative_filled),
            cumulative_notional="0",
            cumulative_fee="0",
            occurred_at_ns=occurred_at_ns,
            applied=0,
        )
    )
    session.flush()
    return record


def _project_fill(
    paper: PaperSession, position: PaperPosition, sign: Decimal, quantity: Decimal, notional: Decimal, fee: Decimal
) -> None:
    """Own explicit spot versus linear-perpetual economics under fixed arithmetic.

    Perpetual notional changes exposure, not wallet cash. Only realized PnL and
    native commissions affect collateral; marked unrealized PnL belongs to the
    engine's trusted/native market account snapshot comparison.
    """
    before = Decimal(position.quantity)
    delta = sign * quantity
    after = before + delta
    average = Decimal(position.average_entry_price)
    realized = Decimal(0)
    if quantity:
        price = notional / quantity
        if before == 0 or before * delta > 0:
            average = (abs(before) * average + notional) / abs(after)
        else:
            closed = min(abs(before), quantity)
            realized = closed * (price - average) * (Decimal(1) if before > 0 else Decimal(-1))
            if after == 0:
                average = Decimal(0)
            elif before * after < 0:
                average = price
    if paper.accounting_model == AccountingModel.LINEAR_PERPETUAL.value:
        paper.balance = format(Decimal(paper.balance) + realized - fee, "f")
        paper.realized_pnl = format(Decimal(paper.realized_pnl) + realized, "f")
    elif paper.accounting_model == AccountingModel.SPOT.value:
        paper.balance = format(Decimal(paper.balance) - sign * notional - fee, "f")
    else:
        raise InvalidTransition("unsupported stored accounting model")
    paper.cumulative_fee = format(Decimal(paper.cumulative_fee) + fee, "f")
    position.quantity = format(after, "f")
    position.average_entry_price = format(average, "f")
