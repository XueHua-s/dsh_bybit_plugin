"""Transactional local command ledger, with no exchange IO or automatic retry of dispatch."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from quant_data.commands import (
    AuditRecord,
    CommandRecord,
    CommandState,
    Environment,
    InvalidTransition,
    LedgerConflict,
    OrderCommand,
    OrderType,
    RiskCode,
    Side,
    canonical,
    decimal_text,
    fingerprint,
    identifier,
)
from quant_data.models import CommandEvent, ExecutionCommand

S = CommandState
_OBSERVATIONS = {S.ACCEPTED, S.PARTIALLY_FILLED, S.FILLED, S.CANCELLED, S.REJECTED, S.RECONCILIATION_REQUIRED}
_ALLOWED = {
    S.DISPATCHING: _OBSERVATIONS,
    S.ACCEPTED: _OBSERVATIONS - {S.ACCEPTED},
    S.PARTIALLY_FILLED: {S.PARTIALLY_FILLED, S.FILLED, S.CANCELLED, S.RECONCILIATION_REQUIRED},
    S.RECONCILIATION_REQUIRED: _OBSERVATIONS - {S.RECONCILIATION_REQUIRED},
}


class CommandLedger:
    """Own one transaction per call; never keep it open while contacting an executor.

    A ready row is a recorded caller decision, NOT live authorization: future
    execution must revalidate risk expiry/account state and reserve capacity.
    Recovery must run with dispatchers quiescent. It cannot fence external IO.
    """

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def admit(self, command: OrderCommand) -> CommandRecord:
        """Persist identity before sending; identical scoped retries reuse it forever."""
        payload = command.canonical()
        digest = fingerprint(payload)
        with self._sessions() as session:
            try:
                with session.begin():
                    existing = session.scalar(
                        select(ExecutionCommand).where(
                            ExecutionCommand.environment == command.environment.value,
                            ExecutionCommand.account_ref == command.account_ref,
                            ExecutionCommand.request_id == command.request_id,
                        )
                    )
                    if existing is not None:
                        return _same_command(existing, digest)
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
                        command_json=payload,
                        fingerprint=digest,
                        native_client_order_id="q" + fingerprint(scope)[:32],
                        state=S.ADMITTED.value,
                        cumulative_filled="0",
                        version=0,
                    )
                    session.add(row)
                    session.flush()
                    session.add(_event(row, "internal:admitted", fingerprint("admitted"), None))
                    return _record(row)
            except IntegrityError:
                # The scope constraint arbitrates independent sessions; the loser
                # reads the committed winner instead of manufacturing a new ID.
                session.rollback()
                existing = session.scalar(
                    select(ExecutionCommand).where(
                        ExecutionCommand.environment == command.environment.value,
                        ExecutionCommand.account_ref == command.account_ref,
                        ExecutionCommand.request_id == command.request_id,
                    )
                )
                if existing is None:
                    raise
                return _same_command(existing, digest)

    def get(self, command_id: str) -> CommandRecord:
        with self._sessions() as session:
            return _record(_required(session, command_id))

    def events(self, command_id: str) -> tuple[AuditRecord, ...]:
        with self._sessions() as session:
            _required(session, command_id)
            return tuple(
                AuditRecord(
                    row.event_id,
                    S(row.state),
                    Decimal(row.cumulative_filled),
                    None if row.decision_code is None else RiskCode(row.decision_code),
                    row.version,
                )
                for row in session.scalars(
                    select(CommandEvent).where(CommandEvent.command_id == command_id).order_by(CommandEvent.version)
                )
            )

    def decide_risk(self, command_id: str, allowed: bool, decision_code: RiskCode) -> CommandRecord:
        """Record an external deterministic risk decision; no risk checks are performed here."""
        if not isinstance(allowed, bool) or not isinstance(decision_code, RiskCode):
            raise TypeError("typed risk decision required")
        if allowed != (decision_code == RiskCode.APPROVED):
            raise ValueError("risk code contradicts allowed flag")
        return self._transition(
            command_id,
            "internal:risk",
            S.READY if allowed else S.RISK_REJECTED,
            Decimal(0),
            decision_code,
            {S.ADMITTED},
        )

    def claim_dispatch(self, command_id: str) -> tuple[bool, CommandRecord]:
        """Exactly one caller wins ready -> dispatching; losers MUST NOT submit."""
        try:
            result = self._transition(
                command_id, "internal:dispatch", S.DISPATCHING, Decimal(0), None, {S.READY}, replay=False
            )
            return True, result
        except InvalidTransition:
            return False, self.get(command_id)

    def observe(self, command_id: str, event_id: str, state: S, cumulative_filled: Decimal) -> CommandRecord:
        """Apply a reconciled execution report, deduplicated within this command.

        Late fills after terminal cancel/reject raise InvalidTransition; callers
        MUST escalate reconciliation, never treat rejection as evidence of flat.
        No order/trade accounting or exchange report ordering is inferred here.
        """
        identifier(event_id, "event_id")
        if event_id.startswith("internal:"):
            raise ValueError("reserved event ID namespace")
        if not isinstance(state, S) or state not in _OBSERVATIONS:
            raise ValueError("unsupported execution observation")
        decimal_text(cumulative_filled)
        return self._transition(command_id, event_id, state, cumulative_filled, None, None)

    def recover_inflight(self) -> tuple[CommandRecord, ...]:
        """Mark interrupted dispatch unknown, without exchange calls or resubmission."""
        with self._sessions() as session:
            ids = tuple(session.scalars(select(ExecutionCommand.id).where(ExecutionCommand.state == S.DISPATCHING)))
        recovered: list[CommandRecord] = []
        for command_id in ids:
            try:
                recovered.append(
                    self._transition(
                        command_id, "internal:recovery", S.RECONCILIATION_REQUIRED, Decimal(0), None, {S.DISPATCHING}
                    )
                )
            except InvalidTransition:
                # A concurrent observation/recovery won. Never overwrite its state.
                continue
        return tuple(recovered)

    def _transition(
        self,
        command_id: str,
        event_id: str,
        state: S,
        filled: Decimal,
        code: RiskCode | None,
        allowed: set[S] | None,
        replay: bool = True,
    ) -> CommandRecord:
        try:
            return self._transition_once(command_id, event_id, state, filled, code, allowed, replay)
        except InvalidTransition:
            # A concurrent duplicate may have committed after our initial event read.
            # Read in a fresh transaction; never retry the state change or dispatch.
            if replay:
                with self._sessions() as session:
                    previous = session.scalar(
                        select(CommandEvent).where(
                            CommandEvent.command_id == command_id, CommandEvent.event_id == event_id
                        )
                    )
                    if previous is not None:
                        digest = fingerprint(
                            canonical(
                                {
                                    "state": state.value,
                                    "filled": decimal_text(filled),
                                    "risk_code": None if code is None else code.value,
                                }
                            )
                        )
                        if previous.fingerprint != digest:
                            raise LedgerConflict("event ID reused with different payload") from None
                        return _record(_required(session, command_id))
            raise

    def _transition_once(
        self,
        command_id: str,
        event_id: str,
        state: S,
        filled: Decimal,
        code: RiskCode | None,
        allowed: set[S] | None,
        replay: bool = True,
    ) -> CommandRecord:
        with self._sessions.begin() as session:
            return _transition_in_session(session, command_id, event_id, state, filled, code, allowed, replay)


def _transition_in_session(
    session: Session,
    command_id: str,
    event_id: str,
    state: S,
    filled: Decimal,
    code: RiskCode | None,
    allowed: set[S] | None,
    replay: bool = True,
) -> CommandRecord:
    digest = fingerprint(
        canonical(
            {
                "state": state.value,
                "filled": decimal_text(filled),
                "risk_code": None if code is None else code.value,
            }
        )
    )
    row = _required(session, command_id)
    previous = session.scalar(
        select(CommandEvent).where(CommandEvent.command_id == command_id, CommandEvent.event_id == event_id)
    )
    if previous is not None:
        if not replay:
            raise InvalidTransition("dispatch was already claimed; reconciliation may be required")
        if previous.fingerprint != digest:
            raise LedgerConflict("event ID reused with different payload")
        return _record(row)
    before = S(row.state)
    if (allowed is not None and before not in allowed) or (
        allowed is None and state not in _ALLOWED.get(before, set())
    ):
        raise InvalidTransition(f"forbidden transition {before.value} -> {state.value}; reconcile late reports")
    command = _record(row).command
    if filled < Decimal(row.cumulative_filled) or filled > command.quantity:
        raise InvalidTransition("cumulative fill must not decrease or exceed order quantity")
    if state == S.FILLED and filled != command.quantity:
        raise InvalidTransition("filled state requires complete quantity")
    if state == S.PARTIALLY_FILLED and not Decimal(0) < filled < command.quantity:
        raise InvalidTransition("partial fill must be between zero and order quantity")
    if state in {S.ACCEPTED, S.REJECTED} and filled != 0:
        raise InvalidTransition("accepted/rejected cannot claim a fill")
    version = row.version + 1
    result = session.execute(
        update(ExecutionCommand)
        .where(
            ExecutionCommand.id == command_id,
            ExecutionCommand.version == row.version,
            ExecutionCommand.state == row.state,
        )
        .values(state=state.value, cumulative_filled=decimal_text(filled), version=version)
        .returning(ExecutionCommand.id),
        execution_options={"synchronize_session": False},
    )
    if result.scalar_one_or_none() is None:
        raise InvalidTransition("concurrent transition won; reread state before continuing")
    session.refresh(row)
    session.add(_event(row, event_id, digest, code))
    session.flush()
    return _record(row)


def _required(session: Session, command_id: str) -> ExecutionCommand:
    row = session.get(ExecutionCommand, command_id)
    if row is None:
        raise KeyError("unknown command")
    return row


def _same_command(row: ExecutionCommand, digest: str) -> CommandRecord:
    if row.fingerprint != digest:
        raise LedgerConflict("request ID reused with different command payload")
    return _record(row)


def _record(row: ExecutionCommand) -> CommandRecord:
    payload: object = json.loads(row.command_json)
    if not isinstance(payload, dict):
        raise TypeError("corrupt stored command")

    def field(name: str) -> str:
        value: object = payload.get(name)
        if not isinstance(value, str):
            raise TypeError("corrupt stored command field")
        return value

    reduce_only: object = payload.get("reduce_only")
    if not isinstance(reduce_only, bool):
        raise TypeError("corrupt stored command boolean")
    command = OrderCommand(
        Environment(field("environment")),
        field("account_ref"),
        field("request_id"),
        field("symbol"),
        Side(field("side")),
        OrderType(field("order_type")),
        Decimal(field("quantity")),
        None if payload.get("limit_price") is None else Decimal(field("limit_price")),
        reduce_only,
    )
    if fingerprint(command.canonical()) != row.fingerprint:
        raise ValueError("stored command fingerprint mismatch")
    return CommandRecord(
        row.id,
        command,
        row.fingerprint,
        row.native_client_order_id,
        S(row.state),
        Decimal(row.cumulative_filled),
        row.version,
    )


def _event(row: ExecutionCommand, event_id: str, digest: str, code: RiskCode | None) -> CommandEvent:
    return CommandEvent(
        command_id=row.id,
        event_id=event_id,
        fingerprint=digest,
        state=row.state,
        cumulative_filled=row.cumulative_filled,
        decision_code=None if code is None else code.value,
        version=row.version,
    )
