"""Durable, redacted account evidence for native execution sessions.

This module only stores server-validated projections. It does not parse venue
credentials, call an exchange, or decide whether an order is safe to submit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from quant_data.commands import EmergencyState, Environment, LedgerConflict, identifier
from quant_data.models import AccountSession, ReconciliationSnapshot
from quant_data.models import EmergencyState as EmergencyStateRow
from quant_data.reconciliation_events import (
    NativeEventEvidence,
    persist_native_events,
    resolve_native_events,
)

_MAX_JSON_BYTES = 1024 * 1024
_MAX_RECONCILIATION_AGE_NS = 30_000_000_000
_MAX_FUTURE_SKEW_NS = 5_000_000_000
_FORBIDDEN_KEY_PARTS = (
    "apikey",
    "apisecret",
    "secret",
    "token",
    "password",
    "authorization",
    "signature",
    "privatekey",
)


def _json(value: object, name: str) -> str:
    """Serialize bounded JSON while rejecting credentials and non-JSON values."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
        raise ValueError(f"{name} evidence exceeds bounded size")
    return encoded


def _reject_secret_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(char for char in key.lower() if char.isalnum()) if isinstance(key, str) else ""
            if not normalized or any(part in normalized for part in _FORBIDDEN_KEY_PARTS):
                raise ValueError("credential-like reconciliation field is not allowed")
            _reject_secret_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_secret_keys(child)


@dataclass(frozen=True)
class ReconciliationEvidence:
    """One complete or protected join of private account reports."""

    session_id: str
    revision: int
    wallet: object
    positions: object
    orders: object
    executions: object
    complete: bool
    observed_at_ns: int
    generation: int = 0
    protected_reason: str | None = None
    native_events: tuple[NativeEventEvidence, ...] = ()

    def __post_init__(self) -> None:
        identifier(self.session_id, "session_id")
        if type(self.revision) is not int or self.revision <= 0:
            raise ValueError("reconciliation revision must be positive")
        if type(self.complete) is not bool or type(self.observed_at_ns) is not int or self.observed_at_ns < 0:
            raise ValueError("invalid reconciliation metadata")
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("invalid reconciliation generation")
        if self.complete and self.protected_reason is not None:
            raise ValueError("complete evidence cannot carry a protected reason")
        if self.protected_reason is not None:
            identifier(self.protected_reason, "protected_reason")
        if not isinstance(self.native_events, tuple) or any(
            not isinstance(event, NativeEventEvidence) for event in self.native_events
        ):
            raise TypeError("native event evidence must be a typed tuple")
        if not isinstance(self.wallet, dict) or not isinstance(self.positions, (list, tuple)):
            raise TypeError("wallet and position evidence must be structured reports")
        if not isinstance(self.orders, (list, tuple)) or not isinstance(self.executions, (list, tuple)):
            raise TypeError("order and execution evidence must be report arrays")
        for name, value in (
            ("wallet", self.wallet),
            ("positions", self.positions),
            ("orders", self.orders),
            ("executions", self.executions),
        ):
            _reject_secret_keys(value)
            _json(value, name)

    def encoded(self) -> tuple[str, str, str, str, str]:
        payloads: tuple[str, str, str, str] = (
            _json(self.wallet, "wallet"),
            _json(self.positions, "positions"),
            _json(self.orders, "orders"),
            _json(self.executions, "executions"),
        )
        metadata = _json(
            {
                "complete": self.complete,
                "generation": self.generation,
                "native_events": [
                    event.canonical() for event in sorted(self.native_events, key=_native_event_sort_key)
                ],
                "observed_at_ns": self.observed_at_ns,
                "protected_reason": self.protected_reason,
            },
            "reconciliation metadata",
        )
        digest = hashlib.sha256("|".join((*payloads, metadata)).encode("utf-8")).hexdigest()
        return payloads[0], payloads[1], payloads[2], payloads[3], digest


@dataclass(frozen=True)
class ReconciliationRecord:
    session_id: str
    generation: int
    revision: int
    evidence_digest: str
    wallet: object
    positions: object
    orders: object
    executions: object
    complete: bool
    protected_reason: str | None
    observed_at_ns: int


@dataclass(frozen=True)
class AccountSessionRecord:
    """Credential-free account session projection; never exposes an ORM entity."""

    session_id: str
    environment: str
    account_ref: str
    expected_uid: str
    category: str
    generation: int
    status: str
    protected: bool
    protection_reason: str | None
    reconciliation_revision: int
    config_fingerprint: str


class ReconciliationStore:
    """Own append-only evidence revisions and the account protection fence."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def open_session(
        self,
        session_id: str,
        account_ref: str,
        config_fingerprint: str,
        *,
        expected_uid: str,
        category: str = "linear",
    ) -> AccountSessionRecord:
        identifier(session_id, "session_id")
        identifier(account_ref, "account_ref")
        identifier(expected_uid, "expected_uid")
        identifier(category, "category")
        if category != "linear":
            raise ValueError("only Testnet Linear accounts are supported")
        if len(config_fingerprint) != 64 or any(char not in "0123456789abcdef" for char in config_fingerprint):
            raise ValueError("invalid config fingerprint")
        with self._sessions.begin() as session:
            row = session.get(AccountSession, session_id)
            if row is None:
                scoped = session.scalar(
                    select(AccountSession).where(
                        AccountSession.environment == Environment.TESTNET.value,
                        AccountSession.account_ref == account_ref,
                    )
                )
                if scoped is not None:
                    raise LedgerConflict("account session already belongs to another generation")
                row = AccountSession(
                    id=session_id,
                    environment=Environment.TESTNET.value,
                    account_ref=account_ref,
                    expected_uid=expected_uid,
                    category=category,
                    generation=0,
                    status=EmergencyState.PROTECTED.value,
                    protected=1,
                    protection_reason="initial_reconciliation_required",
                    reconciliation_revision=0,
                    config_fingerprint=config_fingerprint,
                )
                session.add(row)
                session.flush()
            elif (
                row.config_fingerprint != config_fingerprint
                or row.account_ref != account_ref
                or row.expected_uid != expected_uid
                or row.category != category
            ):
                raise LedgerConflict("account session configuration mismatch")
            return _session_record(row)

    def begin_generation(self, session_id: str, expected_generation: int) -> AccountSessionRecord:
        """Fence stale owners before restart and require fresh account reconciliation."""
        identifier(session_id, "session_id")
        if type(expected_generation) is not int or expected_generation < 0:
            raise ValueError("invalid expected account generation")
        with self._sessions.begin() as session:
            row = session.get(AccountSession, session_id)
            if row is None:
                raise KeyError("unknown account session")
            if row.generation != expected_generation:
                raise LedgerConflict("stale account generation")
            row.generation += 1
            row.status = EmergencyState.PROTECTED.value
            row.protected = 1
            row.protection_reason = "generation_requires_reconciliation"
            session.flush()
            return _session_record(row)

    def account_session(self, session_id: str) -> AccountSessionRecord:
        identifier(session_id, "session_id")
        with self._sessions() as session:
            row = session.get(AccountSession, session_id)
            if row is None:
                raise KeyError("unknown account session")
            return _session_record(row)

    def record(self, evidence: ReconciliationEvidence) -> ReconciliationRecord:
        with self._sessions.begin() as session:
            account = session.get(AccountSession, evidence.session_id)
            if account is None:
                raise KeyError("unknown account session")
            if evidence.generation != account.generation:
                raise LedgerConflict("stale reconciliation generation")
            resolution = resolve_native_events(session, evidence.session_id, evidence.native_events)
            if resolution.conflict:
                effective = replace(
                    evidence,
                    complete=False,
                    protected_reason="native_event_conflict",
                    native_events=resolution.snapshot_events,
                )
            else:
                effective = replace(evidence, native_events=resolution.snapshot_events)
            wallet, positions, orders, executions, digest = effective.encoded()
            if evidence.revision <= account.reconciliation_revision:
                prior = session.scalar(
                    select(ReconciliationSnapshot).where(
                        ReconciliationSnapshot.session_id == evidence.session_id,
                        ReconciliationSnapshot.revision == evidence.revision,
                    )
                )
                if prior is None or prior.evidence_digest != digest:
                    raise LedgerConflict("reconciliation revision already has different evidence")
                return _record(prior)
            if evidence.revision != account.reconciliation_revision + 1:
                raise ValueError("reconciliation revisions must be contiguous")
            row = ReconciliationSnapshot(
                session_id=evidence.session_id,
                generation=evidence.generation,
                revision=evidence.revision,
                evidence_digest=digest,
                wallet_json=wallet,
                positions_json=positions,
                orders_json=orders,
                executions_json=executions,
                complete=int(effective.complete),
                protected_reason=effective.protected_reason,
                observed_at_ns=effective.observed_at_ns,
            )
            session.add(row)
            persist_native_events(session, evidence.session_id, resolution.insertable_events)
            account.reconciliation_revision = evidence.revision
            if not effective.complete:
                account.protected = 1
                account.protection_reason = effective.protected_reason or "incomplete_reconciliation"
                account.status = EmergencyState.PROTECTED.value
                emergency = session.get(EmergencyStateRow, evidence.session_id)
                if emergency is None:
                    session.add(
                        EmergencyStateRow(
                            session_id=evidence.session_id,
                            state=EmergencyState.PROTECTED.value,
                            generation=account.generation,
                            reason=account.protection_reason,
                            command_id=None,
                            updated_at_ns=evidence.observed_at_ns,
                        )
                    )
                else:
                    emergency.state = EmergencyState.PROTECTED.value
                    emergency.generation = account.generation
                    emergency.reason = account.protection_reason
                    emergency.updated_at_ns = evidence.observed_at_ns
            session.flush()
            return _record(row)

    @staticmethod
    def require_current_snapshot(
        session: Session,
        session_id: str,
        generation: int,
        revision: int,
        now_ns: int,
    ) -> ReconciliationSnapshot:
        """Return only the exact, complete, fresh evidence bound to this generation.

        Callers use this inside their transaction so an activation or dispatch
        claim cannot rely on a complete snapshot from a previous account state.
        """
        if type(now_ns) is not int or now_ns < 0:
            raise ValueError("invalid reconciliation clock")
        snapshot = session.scalar(
            select(ReconciliationSnapshot).where(
                ReconciliationSnapshot.session_id == session_id,
                ReconciliationSnapshot.generation == generation,
                ReconciliationSnapshot.revision == revision,
            )
        )
        if snapshot is None or not snapshot.complete:
            raise ValueError("complete reconciliation is required")
        age_ns = now_ns - snapshot.observed_at_ns
        if age_ns < -_MAX_FUTURE_SKEW_NS or age_ns > _MAX_RECONCILIATION_AGE_NS:
            raise ValueError("reconciliation snapshot is stale or future-dated")
        return snapshot

    def latest(self, session_id: str) -> ReconciliationRecord:
        identifier(session_id, "session_id")
        with self._sessions() as session:
            row = session.scalar(
                select(ReconciliationSnapshot)
                .where(ReconciliationSnapshot.session_id == session_id)
                .order_by(ReconciliationSnapshot.revision.desc())
            )
            if row is None:
                raise KeyError("no reconciliation evidence")
            return _record(row)

    def activate(
        self, session_id: str, expected_generation: int, revision: int, activated_at_ns: int
    ) -> AccountSessionRecord:
        """Explicitly clear the protection fence after a complete joined snapshot."""
        identifier(session_id, "session_id")
        if type(expected_generation) is not int or expected_generation < 0:
            raise ValueError("invalid expected account generation")
        if type(revision) is not int or revision <= 0:
            raise ValueError("invalid reconciliation revision")
        if type(activated_at_ns) is not int or activated_at_ns < 0:
            raise ValueError("invalid activation clock")
        with self._sessions.begin() as session:
            account = session.get(AccountSession, session_id)
            if account is None:
                raise KeyError("unknown account session")
            if account.generation != expected_generation or account.reconciliation_revision != revision:
                raise LedgerConflict("stale account reconciliation binding")
            self.require_current_snapshot(
                session,
                session_id,
                expected_generation,
                revision,
                activated_at_ns,
            )
            account.protected = 0
            account.protection_reason = None
            account.status = EmergencyState.RUNNING.value
            session.merge(
                EmergencyStateRow(
                    session_id=session_id,
                    state=EmergencyState.RUNNING.value,
                    generation=expected_generation,
                    reason=None,
                    command_id=None,
                    updated_at_ns=activated_at_ns,
                )
            )
            session.flush()
            return _session_record(account)

    def protect(self, session_id: str, reason: str) -> None:
        identifier(session_id, "session_id")
        identifier(reason, "protection reason")
        with self._sessions.begin() as session:
            row = session.get(AccountSession, session_id)
            if row is None:
                raise KeyError("unknown account session")
            row.protected = 1
            row.protection_reason = reason
            row.status = EmergencyState.PROTECTED.value
            emergency = session.get(EmergencyStateRow, session_id)
            if emergency is not None:
                emergency.state = EmergencyState.PROTECTED.value
                emergency.generation = row.generation
                emergency.reason = reason


def _record(row: ReconciliationSnapshot) -> ReconciliationRecord:
    return ReconciliationRecord(
        row.session_id,
        row.generation,
        row.revision,
        row.evidence_digest,
        json.loads(row.wallet_json),
        json.loads(row.positions_json),
        json.loads(row.orders_json),
        json.loads(row.executions_json),
        bool(row.complete),
        row.protected_reason,
        row.observed_at_ns,
    )


def _native_event_sort_key(event: NativeEventEvidence) -> tuple[str, str]:
    return event.event_id, event.event_type


def _session_record(row: AccountSession) -> AccountSessionRecord:
    if row.expected_uid is None:
        raise ValueError("account session is missing its expected UID")
    return AccountSessionRecord(
        row.id,
        row.environment,
        row.account_ref,
        row.expected_uid,
        row.category,
        row.generation,
        row.status,
        bool(row.protected),
        row.protection_reason,
        row.reconciliation_revision,
        row.config_fingerprint,
    )
