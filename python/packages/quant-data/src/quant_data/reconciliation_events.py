"""Validate, deduplicate and persist credential-free native event evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from quant_data.commands import identifier
from quant_data.models import NativeExecutionEvent

_MAX_EVENT_BYTES = 1024 * 1024
_MAX_EVENTS_PER_BATCH = 10_000
_MAX_EVENT_BATCH_BYTES = 1024 * 1024
_FORBIDDEN = ("apikey", "apisecret", "secret", "token", "password", "authorization", "signature", "privatekey")


def _json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    if len(payload.encode("utf-8")) > _MAX_EVENT_BYTES:
        raise ValueError("native event evidence exceeds bounded size")
    return payload


def _reject_secrets(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(char for char in key.lower() if char.isalnum()) if isinstance(key, str) else ""
            if not normalized or any(part in normalized for part in _FORBIDDEN):
                raise ValueError("credential-like reconciliation field is not allowed")
            _reject_secrets(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_secrets(child)


@dataclass(frozen=True)
class NativeEventEvidence:
    event_id: str
    event_type: str
    state: str
    occurred_at_ns: int
    payload: object
    client_order_id: str | None = None
    venue_order_id: str | None = None
    _payload_json: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        identifier(self.event_id, "event_id")
        identifier(self.event_type, "event_type")
        identifier(self.state, "event state")
        if self.event_type not in {"order", "execution"}:
            raise ValueError("unsupported native event type")
        if type(self.occurred_at_ns) is not int or self.occurred_at_ns < 0:
            raise ValueError("invalid native event timestamp")
        for value, name in ((self.client_order_id, "client_order_id"), (self.venue_order_id, "venue_order_id")):
            if value is not None:
                identifier(value, name)
        if self.client_order_id is not None and len(self.client_order_id) > 36:
            raise ValueError("client order ID is too long")
        _reject_secrets(self.payload)
        object.__setattr__(self, "_payload_json", _json(self.payload))

    def canonical(self) -> dict[str, object]:
        return {
            "client_order_id": self.client_order_id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at_ns": self.occurred_at_ns,
            "payload": json.loads(self._payload_json),
            "state": self.state,
            "venue_order_id": self.venue_order_id,
        }


@dataclass(frozen=True)
class NativeEventResolution:
    snapshot_events: tuple[NativeEventEvidence, ...]
    insertable_events: tuple[NativeEventEvidence, ...]
    conflict: bool


def resolve_native_events(
    session: Session, session_id: str, events: tuple[NativeEventEvidence, ...]
) -> NativeEventResolution:
    if len(events) > _MAX_EVENTS_PER_BATCH:
        raise ValueError("native event batch exceeds bounded size")
    grouped: dict[str, dict[str, NativeEventEvidence]] = {}
    batch_bytes = 0
    for event in events:
        payload = _json(event.canonical())
        batch_bytes += len(payload.encode("utf-8"))
        if batch_bytes > _MAX_EVENT_BATCH_BYTES:
            raise ValueError("native event batch exceeds bounded size")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        grouped.setdefault(event.event_id, {})[digest] = event
    conflicting_ids = {event_id for event_id, values in grouped.items() if len(values) > 1}
    insertable: list[NativeEventEvidence] = []
    conflict = bool(conflicting_ids)
    for event_id, values in sorted(grouped.items()):
        if event_id in conflicting_ids:
            continue
        digest, event = next(iter(values.items()))
        existing = session.scalar(
            select(NativeExecutionEvent).where(
                NativeExecutionEvent.session_id == session_id,
                NativeExecutionEvent.event_id == event_id,
            )
        )
        if existing is None:
            insertable.append(event)
        elif existing.payload_digest != digest:
            conflict = True
    snapshot = tuple(event for _, values in sorted(grouped.items()) for _, event in sorted(values.items()))
    return NativeEventResolution(snapshot, tuple(insertable), conflict)


def persist_native_events(session: Session, session_id: str, events: tuple[NativeEventEvidence, ...]) -> None:
    for event in events:
        payload = _json(event.canonical())
        session.add(
            NativeExecutionEvent(
                session_id=session_id,
                event_id=event.event_id,
                command_id=None,
                client_order_id=event.client_order_id,
                venue_order_id=event.venue_order_id,
                event_type=event.event_type,
                state=event.state,
                payload_digest=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                payload_json=payload,
                occurred_at_ns=event.occurred_at_ns,
                applied=0,
            )
        )
