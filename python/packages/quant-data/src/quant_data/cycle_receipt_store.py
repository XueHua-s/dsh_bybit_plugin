"""Append-only durable AI cycle receipts, independent of order commands."""

from __future__ import annotations

import time
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .admission_contracts import digest
from .admission_store import owned, transaction
from .commands import Environment, LedgerConflict, identifier
from .models import AiPaperCycleEvent, AiPaperCycleReceipt

_TERMINAL = frozenset({"abstained", "rejected", "risk_rejected", "filled", "protected", "unknown"})
_TRANSITIONS = {
    ("received", "claimed"),
    ("received", "selected"),
    ("received", "abstained"),
    ("received", "rejected"),
    ("received", "protected"),
    ("received", "unknown"),
    ("claimed", "selected"),
    ("claimed", "abstained"),
    ("claimed", "rejected"),
    ("claimed", "risk_rejected"),
    ("claimed", "protected"),
    ("claimed", "unknown"),
    ("selected", "admitted"),
    ("selected", "risk_rejected"),
    ("selected", "rejected"),
    ("selected", "abstained"),
    ("selected", "protected"),
    ("selected", "unknown"),
    ("admitted", "accepted"),
    ("admitted", "partially_filled"),
    ("admitted", "filled"),
    ("admitted", "protected"),
    ("admitted", "unknown"),
    ("accepted", "partially_filled"),
    ("accepted", "filled"),
    ("accepted", "protected"),
    ("accepted", "unknown"),
    ("partially_filled", "partially_filled"),
    ("partially_filled", "filled"),
    ("partially_filled", "protected"),
    ("partially_filled", "unknown"),
}
_STATUSES = _TERMINAL | frozenset({"claimed", "selected", "admitted", "accepted", "partially_filled"})


class CycleReceiptStore:
    """Own cycle header/event transactions; command binding remains AdmissionStore-owned."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def begin(
        self,
        session_id: str,
        owner_id: str,
        request_id: str,
        payload_digest: str,
        decision_id: str,
        fixture_digest: str,
        *,
        claim_owner: str,
        claim_deadline_ns: int,
    ) -> tuple[dict[str, object], bool]:
        identifier(request_id, "request_id")
        identifier(decision_id, "decision_id")
        identifier(claim_owner, "claim_owner")
        if type(claim_deadline_ns) is not int or claim_deadline_ns <= time.time_ns():
            raise ValueError("invalid_cycle_claim")
        digest(payload_digest)
        digest(fixture_digest)
        with transaction(self._sessions) as session:
            paper = owned(session, session_id, owner_id)
            row = session.scalar(
                select(AiPaperCycleReceipt).where(
                    AiPaperCycleReceipt.environment == Environment.INTERNAL_PAPER.value,
                    AiPaperCycleReceipt.account_ref == paper.account_ref,
                    AiPaperCycleReceipt.request_id == request_id,
                )
            )
            if row is not None:
                if (row.payload_digest, row.decision_id, row.fixture_digest) != (
                    payload_digest,
                    decision_id,
                    fixture_digest,
                ):
                    raise LedgerConflict("AI cycle request payload conflict")
                projection = self._projection(session, row)
                claim_deadline = projection.get("claim_deadline_ns")
                if (
                    projection["status"]
                    in {"received", "claimed", "selected", "admitted", "accepted", "partially_filled"}
                    and type(claim_deadline) is int
                    and claim_deadline <= time.time_ns()
                ):
                    latest = session.scalar(
                        select(AiPaperCycleEvent)
                        .where(AiPaperCycleEvent.receipt_id == row.id)
                        .order_by(AiPaperCycleEvent.sequence.desc())
                        .limit(1)
                    )
                    assert latest is not None
                    session.add(
                        AiPaperCycleEvent(
                            receipt_id=row.id,
                            event_id=str(uuid4()),
                            sequence=latest.sequence + 1,
                            status="protected",
                            reason="claim_lease_expired",
                        )
                    )
                    session.flush()
                    projection = self._projection(session, row)
                return projection, False
            row = AiPaperCycleReceipt(
                environment=Environment.INTERNAL_PAPER.value,
                account_ref=paper.account_ref,
                request_id=request_id,
                payload_digest=payload_digest,
                decision_id=decision_id,
                fixture_digest=fixture_digest,
            )
            session.add(row)
            session.flush()
            session.add(
                AiPaperCycleEvent(
                    receipt_id=row.id,
                    event_id=str(uuid4()),
                    sequence=0,
                    status="claimed",
                    claim_owner=claim_owner,
                    generation=paper.generation,
                    claim_deadline_ns=claim_deadline_ns,
                )
            )
            session.flush()
            return self._projection(session, row), True

    def get(self, session_id: str, owner_id: str, request_id: str) -> dict[str, object]:
        identifier(request_id, "request_id")
        with self._sessions() as session:
            paper = owned(session, session_id, owner_id)
            row = session.scalar(
                select(AiPaperCycleReceipt).where(
                    AiPaperCycleReceipt.environment == Environment.INTERNAL_PAPER.value,
                    AiPaperCycleReceipt.account_ref == paper.account_ref,
                    AiPaperCycleReceipt.request_id == request_id,
                )
            )
            if row is None:
                raise KeyError(request_id)
            return self._projection(session, row)

    def protect_inflight(self, session_id: str, owner_id: str) -> int:
        """Fence every unfinished cycle after process restart; never infer replay safety."""
        inflight = {"received", "claimed", "selected", "admitted", "accepted", "partially_filled"}
        with transaction(self._sessions) as session:
            paper = owned(session, session_id, owner_id)
            rows = session.scalars(
                select(AiPaperCycleReceipt).where(
                    AiPaperCycleReceipt.environment == Environment.INTERNAL_PAPER.value,
                    AiPaperCycleReceipt.account_ref == paper.account_ref,
                )
            ).all()
            protected = 0
            for row in rows:
                latest = session.scalar(
                    select(AiPaperCycleEvent)
                    .where(AiPaperCycleEvent.receipt_id == row.id)
                    .order_by(AiPaperCycleEvent.sequence.desc())
                    .limit(1)
                )
                if latest is None or latest.status not in inflight:
                    continue
                session.add(
                    AiPaperCycleEvent(
                        receipt_id=row.id,
                        event_id=str(uuid4()),
                        sequence=latest.sequence + 1,
                        status="protected",
                        reason="restart_requires_reconciliation",
                    )
                )
                protected += 1
            session.flush()
            return protected

    def append(
        self,
        session_id: str,
        owner_id: str,
        request_id: str,
        status: str,
        *,
        reason: str | None = None,
        strategy_digest: str | None = None,
        evidence_digest: str | None = None,
        client_order_id: str | None = None,
        command_id: str | None = None,
        generation: int | None = None,
        claim_owner: str | None = None,
        claim_deadline_ns: int | None = None,
    ) -> dict[str, object]:
        if status not in _STATUSES:
            raise ValueError("invalid_cycle_status")
        if reason is not None:
            identifier(reason, "cycle reason")
        for value in (strategy_digest, evidence_digest):
            if value is not None:
                digest(value)
        if client_order_id is not None:
            identifier(client_order_id, "client_order_id")
        if command_id is not None:
            identifier(command_id, "command_id")
        if status in {"admitted", "accepted", "partially_filled", "filled"} and command_id is None:
            raise ValueError("command_required_for_admitted_cycle")
        with transaction(self._sessions) as session:
            paper = owned(session, session_id, owner_id)
            row = session.scalar(
                select(AiPaperCycleReceipt).where(
                    AiPaperCycleReceipt.environment == Environment.INTERNAL_PAPER.value,
                    AiPaperCycleReceipt.account_ref == paper.account_ref,
                    AiPaperCycleReceipt.request_id == request_id,
                )
            )
            if row is None:
                raise KeyError(request_id)
            latest = session.scalar(
                select(AiPaperCycleEvent)
                .where(AiPaperCycleEvent.receipt_id == row.id)
                .order_by(AiPaperCycleEvent.sequence.desc())
                .limit(1)
            )
            if latest is None or latest.status in _TERMINAL or (latest.status, status) not in _TRANSITIONS:
                raise LedgerConflict("invalid AI cycle event transition")
            session.add(
                AiPaperCycleEvent(
                    receipt_id=row.id,
                    event_id=str(uuid4()),
                    sequence=latest.sequence + 1,
                    status=status,
                    reason=reason,
                    strategy_digest=strategy_digest,
                    evidence_digest=evidence_digest,
                    client_order_id=client_order_id,
                    command_id=command_id,
                    generation=generation,
                    claim_owner=claim_owner,
                    claim_deadline_ns=claim_deadline_ns,
                )
            )
            session.flush()
            return self._projection(session, row)

    @staticmethod
    def _projection(session: Session, row: AiPaperCycleReceipt) -> dict[str, object]:
        events = session.scalars(
            select(AiPaperCycleEvent).where(AiPaperCycleEvent.receipt_id == row.id).order_by(AiPaperCycleEvent.sequence)
        )
        history = [
            {
                "sequence": e.sequence,
                "status": e.status,
                "reason": e.reason,
                "command_id": e.command_id,
                "client_order_id": e.client_order_id,
                "generation": e.generation,
                "claim_owner": e.claim_owner,
                "claim_deadline_ns": e.claim_deadline_ns,
            }
            for e in events
        ]
        latest = history[-1] if history else {"status": "unknown", "reason": None}
        claim = next((event for event in history if event["status"] == "claimed"), {})
        return {
            "request_id": row.request_id,
            "payload_digest": row.payload_digest,
            "decision_id": row.decision_id,
            "fixture_digest": row.fixture_digest,
            "status": latest["status"],
            "reason": latest["reason"],
            "command_id": latest.get("command_id"),
            "native_client_order_id": latest.get("client_order_id"),
            "claim_owner": claim.get("claim_owner"),
            "claim_deadline_ns": claim.get("claim_deadline_ns"),
            "events": history,
        }
