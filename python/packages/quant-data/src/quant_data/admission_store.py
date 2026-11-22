"""Transactional paper admission authority. No external execution or blind retries."""

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from quant_data.admission_contracts import (
    AccountingModel,
    AdmissionDecision,
    NativeObservation,
    PositionSnapshot,
    ReservationSnapshot,
    SessionSnapshot,
    digest,
    timestamp,
)
from quant_data.admission_models import PaperPosition, PaperSession, Reservation, RiskDecision
from quant_data.commands import (
    CommandRecord,
    Environment,
    InvalidTransition,
    LedgerConflict,
    OrderCommand,
    RiskCode,
    Side,
    canonical,
    decimal_text,
    fingerprint,
    identifier,
)
from quant_data.commands import (
    CommandState as S,
)
from quant_data.ledger import _event, _record, _required, _same_command, _transition_in_session
from quant_data.models import ExecutionCommand


@contextmanager
def transaction(sessions: sessionmaker[Session]) -> Iterator[Session]:
    """SQLite serializes read/check/write across processes before reading context.

    Other SQL databases are not supported by this bounded single-host paper slice.
    Engine process lifetime locking remains mandatory: DB locks cannot fence IO.
    """
    with sessions() as session:
        if session.get_bind().dialect.name != "sqlite":
            raise ValueError("paper admission requires SQLite")
        try:
            session.execute(text("BEGIN IMMEDIATE"))
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise


def owned(session: Session, session_id: str, owner_id: str, generation: int | None = None) -> PaperSession:
    row = session.get(PaperSession, session_id)
    if row is None:
        raise KeyError("unknown paper session")
    if row.owner_id != owner_id:
        raise InvalidTransition("paper session owner lost")
    if generation is not None and row.generation != generation:
        raise InvalidTransition("stale context generation")
    return row


def snapshot_row(session: Session, row: PaperSession) -> SessionSnapshot:
    positions = tuple(
        PositionSnapshot(p.symbol, Decimal(p.quantity), Decimal(p.average_entry_price))
        for p in session.scalars(
            select(PaperPosition).where(PaperPosition.session_id == row.id).order_by(PaperPosition.symbol)
        )
    )
    reservations = tuple(
        ReservationSnapshot(r.command_id, r.symbol, Side(r.side), Decimal(r.remaining_quantity), Decimal(r.price))
        for r in session.scalars(
            select(Reservation).where(Reservation.session_id == row.id).order_by(Reservation.command_id)
        )
        if Decimal(r.remaining_quantity) > 0
    )
    return SessionSnapshot(
        row.id,
        row.account_ref,
        row.owner_id,
        row.generation,
        bool(row.protected),
        row.protection_reason,
        Decimal(row.balance),
        positions,
        reservations,
        row.last_admitted_at_ns,
        AccountingModel(row.accounting_model),
        Decimal(row.realized_pnl),
        Decimal(row.cumulative_fee),
    )


class AdmissionStore:
    """Own account context CAS, immutable decisions and matching-ledger atomicity.

    Caller owns deterministic risk and a process lifetime account lock. Never use
    a wire-provided allowed flag. Opening an existing session always protects it:
    durable projections do not reconstruct native matching-engine state.
    """

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def open_session(
        self,
        environment: Environment,
        account_ref: str,
        session_id: str,
        owner_id: str,
        config_fingerprint: str,
        starting_balance: Decimal,
        accounting_model: AccountingModel = AccountingModel.SPOT,
    ) -> SessionSnapshot:
        if environment is not Environment.INTERNAL_PAPER:
            raise ValueError("explicit internal_paper required")
        for name, value in (("account_ref", account_ref), ("session_id", session_id), ("owner_id", owner_id)):
            identifier(value, name)
        if not isinstance(accounting_model, AccountingModel):
            raise TypeError("typed paper accounting model required")
        digest(config_fingerprint)
        decimal_text(starting_balance)
        if starting_balance <= 0:
            raise ValueError("positive synthetic starting balance required")
        with transaction(self._sessions) as session:
            row = session.get(PaperSession, session_id)
            if row is None:
                if session.scalar(select(PaperSession).where(PaperSession.account_ref == account_ref)) is not None:
                    raise LedgerConflict("paper account already belongs to another session")
                row = PaperSession(
                    id=session_id,
                    account_ref=account_ref,
                    owner_id=owner_id,
                    config_fingerprint=config_fingerprint,
                    generation=0,
                    protected=0,
                    protection_reason=None,
                    balance=decimal_text(starting_balance),
                    accounting_model=accounting_model.value,
                    realized_pnl="0",
                    cumulative_fee="0",
                )
                session.add(row)
                session.flush()
            else:
                if (
                    row.account_ref != account_ref
                    or row.config_fingerprint != config_fingerprint
                    or row.accounting_model != accounting_model.value
                ):
                    raise LedgerConflict("paper session configuration mismatch")
                row.owner_id = owner_id
                from quant_data.admission_events import protect_record

                protect_record(session, row, "restart_requires_reconciliation")
            return snapshot_row(session, row)

    def snapshot(self, session_id: str, owner_id: str) -> SessionSnapshot:
        with self._sessions() as session:
            return snapshot_row(session, owned(session, session_id, owner_id))

    def get(self, command_id: str, session_id: str, owner_id: str) -> CommandRecord:
        with self._sessions() as session:
            owned(session, session_id, owner_id)
            _scope(session, command_id, session_id)
            return _record(_required(session, command_id))

    def get_by_request(self, request_id: str, session_id: str, owner_id: str) -> CommandRecord:
        identifier(request_id, "request_id")
        with self._sessions() as session:
            paper = owned(session, session_id, owner_id)
            row = session.scalar(
                select(ExecutionCommand).where(
                    ExecutionCommand.environment == Environment.INTERNAL_PAPER.value,
                    ExecutionCommand.account_ref == paper.account_ref,
                    ExecutionCommand.request_id == request_id,
                )
            )
            if row is None:
                raise KeyError("unknown paper request")
            _scope(session, row.id, session_id)
            return _record(row)

    def record_native(
        self, session_id: str, owner_id: str, command_id: str, event_id: str, event_type: str, occurred_at_ns: int
    ) -> CommandRecord:
        from quant_data.admission_events import record_native

        with transaction(self._sessions) as session:
            return record_native(
                session, owned(session, session_id, owner_id), command_id, event_id, event_type, occurred_at_ns
            )

    def protect(self, session_id: str, owner_id: str, reason: str) -> SessionSnapshot:
        identifier(reason, "protection reason")
        with transaction(self._sessions) as session:
            row = owned(session, session_id, owner_id)
            from quant_data.admission_events import protect_record

            protect_record(session, row, reason)
            return snapshot_row(session, row)

    def decide(
        self,
        session_id: str,
        owner_id: str,
        expected_generation: int,
        command: OrderCommand,
        decision: AdmissionDecision,
        *,
        decision_request_digest: str | None = None,
        decision_id: str | None = None,
        fixture_digest: str | None = None,
    ) -> CommandRecord:
        if not isinstance(decision, AdmissionDecision):
            raise TypeError("typed server decision required")
        binding = (decision_request_digest, decision_id, fixture_digest)
        if any(value is not None for value in binding) and (
            any(type(value) is not str or not value for value in binding)
            or re.fullmatch(r"[a-f0-9]{64}", decision_request_digest or "") is None
            or re.fullmatch(r"[a-f0-9]{64}", fixture_digest or "") is None
        ):
            raise ValueError("invalid_decision_binding")
        if decision_id is not None:
            identifier(decision_id, "decision_id")
        with transaction(self._sessions) as session:
            paper = owned(session, session_id, owner_id)
            if command.environment is not Environment.INTERNAL_PAPER or command.account_ref != paper.account_ref:
                raise ValueError("command/session scope mismatch")
            existing = session.scalar(
                select(ExecutionCommand).where(
                    ExecutionCommand.environment == command.environment.value,
                    ExecutionCommand.account_ref == command.account_ref,
                    ExecutionCommand.request_id == command.request_id,
                )
            )
            if existing is not None:
                prior = session.get(RiskDecision, existing.id)
                if prior is None or prior.session_id != session_id:
                    raise LedgerConflict("command not owned by this admission session")
                if decision_request_digest is not None:
                    binding_row = session.execute(
                        text(
                            "SELECT request_digest, decision_id, fixture_digest, command_id "
                            "FROM ai_paper_decision_bindings WHERE environment=:environment "
                            "AND account_ref=:account_ref AND request_id=:request_id"
                        ),
                        {
                            "environment": command.environment.value,
                            "account_ref": command.account_ref,
                            "request_id": command.request_id,
                        },
                    ).first()
                    if binding_row is None or tuple(binding_row) != (
                        decision_request_digest,
                        decision_id,
                        fixture_digest,
                        existing.id,
                    ):
                        raise LedgerConflict("decision request binding conflict")
                return _same_command(existing, fingerprint(command.canonical()))
            owned(session, session_id, owner_id, expected_generation)
            if paper.protected:
                raise InvalidTransition("paper session protected")
            if paper.last_admitted_at_ns is not None and decision.evaluated_at_ns < paper.last_admitted_at_ns:
                raise InvalidTransition("risk decision precedes latest context")
            payload = command.canonical()
            scope = canonical(
                {
                    "environment": command.environment.value,
                    "account_ref": command.account_ref,
                    "request_id": command.request_id,
                }
            )
            row = ExecutionCommand(
                id=str(uuid4()),
                environment=command.environment.value,
                account_ref=command.account_ref,
                request_id=command.request_id,
                fingerprint=fingerprint(payload),
                command_json=payload,
                native_client_order_id="q" + fingerprint(scope)[:32],
                state=S.ADMITTED.value,
                cumulative_filled="0",
                version=0,
            )
            session.add(row)
            session.flush()
            session.add(_event(row, "internal:admitted", fingerprint("admitted"), None))
            session.add(
                RiskDecision(
                    command_id=row.id,
                    session_id=session_id,
                    allowed=int(decision.allowed),
                    code=decision.code.value,
                    policy_fingerprint=decision.policy_fingerprint,
                    context_fingerprint=decision.context_fingerprint,
                    reasons_json=json.dumps(decision.reasons),
                    context_generation=paper.generation,
                    evaluated_at_ns=decision.evaluated_at_ns,
                    expires_at_ns=decision.expires_at_ns,
                    reservation_price=decimal_text(decision.reservation_price),
                )
            )
            if decision.allowed:
                session.add(
                    Reservation(
                        command_id=row.id,
                        session_id=session_id,
                        symbol=command.symbol,
                        side=command.side.value,
                        remaining_quantity=decimal_text(command.quantity),
                        price=decimal_text(decision.reservation_price),
                        cumulative_notional="0",
                        cumulative_fee="0",
                        last_event_ns=0,
                    )
                )
                paper.last_admitted_at_ns = decision.evaluated_at_ns
            paper.generation += 1
            record = _transition_in_session(
                session,
                row.id,
                "internal:risk",
                S.READY if decision.allowed else S.RISK_REJECTED,
                Decimal(0),
                decision.code,
                {S.ADMITTED},
            )
            if decision_request_digest is not None and decision_id is not None and fixture_digest is not None:
                receipt = {
                    "schema_version": "1",
                    "request_id": command.request_id,
                    "payload_digest": decision_request_digest,
                    "decision_id": decision_id,
                    "status": "admitted" if decision.allowed else "risk_rejected",
                    "reason": None if decision.allowed else "risk_rejected",
                    "command_id": record.id,
                    "native_client_order_id": record.native_client_order_id,
                }
                session.execute(
                    text(
                        "INSERT INTO ai_paper_decision_bindings "
                        "(environment, account_ref, request_id, request_digest, decision_id, fixture_digest, "
                        "command_id, native_client_order_id, receipt_json) "
                        "VALUES (:environment, :account_ref, :request_id, :request_digest, :decision_id, "
                        ":fixture_digest, :command_id, :native_client_order_id, :receipt_json)"
                    ),
                    {
                        "environment": command.environment.value,
                        "account_ref": command.account_ref,
                        "request_id": command.request_id,
                        "request_digest": decision_request_digest,
                        "decision_id": decision_id,
                        "fixture_digest": fixture_digest,
                        "command_id": record.id,
                        "native_client_order_id": record.native_client_order_id,
                        "receipt_json": json.dumps(receipt, sort_keys=True, separators=(",", ":")),
                    },
                )
            return record

    def get_decision_receipt(self, request_id: str, session_id: str, owner_id: str) -> dict[str, object]:
        identifier(request_id, "request_id")
        with transaction(self._sessions) as session:
            paper = owned(session, session_id, owner_id)
            row = session.execute(
                text(
                    "SELECT receipt_json FROM ai_paper_decision_bindings WHERE environment=:environment "
                    "AND account_ref=:account_ref AND request_id=:request_id"
                ),
                {
                    "environment": Environment.INTERNAL_PAPER.value,
                    "account_ref": paper.account_ref,
                    "request_id": request_id,
                },
            ).first()
            if row is None or not isinstance(row[0], str):
                raise KeyError(request_id)
            payload = json.loads(row[0])
            if not isinstance(payload, dict):
                raise LedgerConflict("invalid durable decision receipt")
            return payload

    def claim_dispatch(
        self, session_id: str, owner_id: str, expected_generation: int, command_id: str, now_ns: int
    ) -> tuple[bool, CommandRecord]:
        timestamp(now_ns)
        with transaction(self._sessions) as session:
            paper = owned(session, session_id, owner_id, expected_generation)
            decision = session.get(RiskDecision, command_id)
            if decision is None or decision.session_id != session_id:
                raise ValueError("command/session scope mismatch")
            row = _required(session, command_id)
            if paper.protected or row.state != S.READY.value:
                return False, _record(row)
            if paper.generation != decision.context_generation + 1:
                return False, _record(row)
            if not decision.evaluated_at_ns <= now_ns < decision.expires_at_ns:
                from quant_data.admission_events import protect_record

                protect_record(session, paper, "decision_expired")
                return False, _record(row)
            paper.generation += 1
            return True, _transition_in_session(
                session, command_id, "internal:dispatch", S.DISPATCHING, Decimal(0), None, {S.READY}, replay=False
            )

    def decisions(self, command_id: str, session_id: str, owner_id: str) -> tuple[AdmissionDecision, ...]:
        with self._sessions() as session:
            owned(session, session_id, owner_id)
            row = _scope(session, command_id, session_id)
            return (
                AdmissionDecision(
                    bool(row.allowed),
                    RiskCode(row.code),
                    row.policy_fingerprint,
                    row.context_fingerprint,
                    row.evaluated_at_ns,
                    row.expires_at_ns,
                    Decimal(row.reservation_price),
                    tuple(json.loads(row.reasons_json)),
                ),
            )

    def observe(self, session_id: str, owner_id: str, observation: NativeObservation) -> CommandRecord:
        from quant_data.admission_events import observe

        with transaction(self._sessions) as session:
            return observe(session, owned(session, session_id, owner_id), observation)


def _scope(session: Session, command_id: str, session_id: str) -> RiskDecision:
    row = session.get(RiskDecision, command_id)
    if row is None or row.session_id != session_id:
        raise ValueError("command/session scope mismatch")
    return row
