"""Generation-bound Testnet admission and dispatch claims, with no venue IO."""

from __future__ import annotations

import re
from collections.abc import Callable
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from quant_data.commands import (
    CommandRecord,
    CommandState,
    EmergencyState,
    Environment,
    InvalidTransition,
    LedgerConflict,
    OrderCommand,
    RiskCode,
    canonical,
    decimal_text,
    fingerprint,
    identifier,
)
from quant_data.ledger import _record, _same_command, _transition_in_session
from quant_data.models import (
    AccountSession,
    ExecutionCommand,
    ExecutionReservation,
    NativeAdmissionDecision,
)
from quant_data.models import (
    EmergencyState as EmergencyStateRow,
)
from quant_data.reconciliation_store import ReconciliationStore


def admit_native(
    sessions: sessionmaker[Session],
    command: OrderCommand,
    session_id: str,
    expected_generation: int,
    reconciliation_revision: int,
    allowed: bool,
    decision_code: RiskCode,
    *,
    policy_fingerprint: str,
    context_fingerprint: str,
    evaluated_at_ns: int,
    expires_at_ns: int,
    reservation_price: Decimal,
) -> CommandRecord:
    if command.environment is not Environment.TESTNET:
        raise ValueError("native admission requires Testnet")
    identifier(session_id, "session_id")
    _nonnegative(expected_generation, "expected_generation")
    _nonnegative(reconciliation_revision, "reconciliation_revision")
    _fingerprint(policy_fingerprint, "policy_fingerprint")
    _fingerprint(context_fingerprint, "context_fingerprint")
    if type(allowed) is not bool or not isinstance(decision_code, RiskCode):
        raise TypeError("typed native risk decision required")
    if allowed != (decision_code is RiskCode.APPROVED):
        raise ValueError("risk code contradicts allowed flag")
    if type(evaluated_at_ns) is not int or type(expires_at_ns) is not int or expires_at_ns <= evaluated_at_ns:
        raise ValueError("risk decision expiry must follow evaluation")
    decimal_text(reservation_price)
    if reservation_price <= 0:
        raise ValueError("native reservation price must be positive")

    payload = command.canonical()
    digest = fingerprint(payload)
    try:
        with sessions.begin() as session:
            existing = _existing_native(
                session, command, digest, session_id, expected_generation, reconciliation_revision
            )
            if existing is not None:
                return existing
            _native_account(session, session_id, command.account_ref, expected_generation)
            _native_reconciliation(session, session_id, expected_generation, reconciliation_revision, evaluated_at_ns)
            _native_emergency(session, session_id, expected_generation)
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
                state=CommandState.ADMITTED.value,
                cumulative_filled="0",
                version=0,
            )
            session.add(row)
            session.flush()
            session.add(
                NativeAdmissionDecision(
                    command_id=row.id,
                    session_id=session_id,
                    allowed=int(allowed),
                    decision_code=decision_code.value,
                    policy_fingerprint=policy_fingerprint,
                    context_fingerprint=context_fingerprint,
                    account_generation=expected_generation,
                    reconciliation_revision=reconciliation_revision,
                    evaluated_at_ns=evaluated_at_ns,
                    expires_at_ns=expires_at_ns,
                    reservation_price=decimal_text(reservation_price),
                )
            )
            if allowed:
                session.add(
                    ExecutionReservation(
                        command_id=row.id,
                        session_id=session_id,
                        account_generation=expected_generation,
                        reconciliation_revision=reconciliation_revision,
                        symbol=command.symbol,
                        side=command.side.value,
                        remaining_quantity=decimal_text(command.quantity),
                        reserved_notional=decimal_text(command.quantity * reservation_price),
                        reserved_at_ns=evaluated_at_ns,
                    )
                )
            return _transition_in_session(
                session,
                row.id,
                "internal:risk",
                CommandState.READY if allowed else CommandState.RISK_REJECTED,
                Decimal(0),
                decision_code,
                {CommandState.ADMITTED},
            )
    except IntegrityError:
        with sessions() as session:
            existing = _existing_native(
                session, command, digest, session_id, expected_generation, reconciliation_revision
            )
            if existing is None:
                raise
            return existing


def claim_native_dispatch(
    sessions: sessionmaker[Session],
    get_command: Callable[[str], CommandRecord],
    command_id: str,
    session_id: str,
    expected_generation: int,
    reconciliation_revision: int,
    now_ns: int,
) -> tuple[bool, CommandRecord]:
    identifier(session_id, "session_id")
    _nonnegative(expected_generation, "expected_generation")
    _nonnegative(reconciliation_revision, "reconciliation_revision")
    _nonnegative(now_ns, "now_ns")
    try:
        with sessions.begin() as session:
            row = session.get(ExecutionCommand, command_id)
            if row is None:
                raise KeyError("unknown command")
            if row.environment != Environment.TESTNET.value:
                raise InvalidTransition("native dispatch requires Testnet")
            _native_account(session, session_id, row.account_ref, expected_generation)
            _native_reconciliation(session, session_id, expected_generation, reconciliation_revision, now_ns)
            _native_emergency(session, session_id, expected_generation)
            decision = session.get(NativeAdmissionDecision, command_id)
            if decision is None or not decision.allowed or decision.session_id != session_id:
                raise InvalidTransition("native risk admission is absent or rejected")
            if (
                decision.account_generation != expected_generation
                or decision.reconciliation_revision != reconciliation_revision
            ):
                raise InvalidTransition("native risk context is stale")
            if now_ns >= decision.expires_at_ns:
                raise InvalidTransition("native risk decision expired")
            result = _transition_in_session(
                session,
                command_id,
                "internal:native-dispatch",
                CommandState.DISPATCHING,
                Decimal(0),
                None,
                {CommandState.READY},
                replay=False,
            )
            return True, result
    except InvalidTransition:
        return False, get_command(command_id)


def _existing_native(
    session: Session,
    command: OrderCommand,
    digest: str,
    session_id: str,
    expected_generation: int,
    reconciliation_revision: int,
) -> CommandRecord | None:
    row = session.scalar(
        select(ExecutionCommand).where(
            ExecutionCommand.environment == command.environment.value,
            ExecutionCommand.account_ref == command.account_ref,
            ExecutionCommand.request_id == command.request_id,
        )
    )
    if row is None:
        return None
    _same_command(row, digest)
    decision = session.get(NativeAdmissionDecision, row.id)
    if decision is None or (
        decision.session_id != session_id
        or decision.account_generation != expected_generation
        or decision.reconciliation_revision != reconciliation_revision
    ):
        raise LedgerConflict("native admission binding conflict")
    return _record(row)


def _native_account(session: Session, session_id: str, account_ref: str, generation: int) -> AccountSession:
    account = session.get(AccountSession, session_id)
    if account is None or account.environment != Environment.TESTNET.value or account.account_ref != account_ref:
        raise InvalidTransition("native account binding is unknown")
    if account.generation != generation:
        raise InvalidTransition("native account generation is stale")
    if account.protected or account.status != EmergencyState.RUNNING.value:
        raise InvalidTransition("native account is protected")
    return account


def _native_reconciliation(
    session: Session,
    session_id: str,
    generation: int,
    revision: int,
    now_ns: int,
) -> None:
    account = session.get(AccountSession, session_id)
    if account is None or account.generation != generation or account.reconciliation_revision != revision:
        raise InvalidTransition("native reconciliation revision is stale")
    try:
        ReconciliationStore.require_current_snapshot(session, session_id, generation, revision, now_ns)
    except ValueError:
        raise InvalidTransition("native reconciliation is incomplete or stale")


def _native_emergency(session: Session, session_id: str, generation: int) -> None:
    emergency = session.get(EmergencyStateRow, session_id)
    if emergency is None or emergency.generation != generation or emergency.state != EmergencyState.RUNNING.value:
        raise InvalidTransition("native emergency fence is not running")


def _nonnegative(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _fingerprint(value: str, name: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"invalid {name}")
