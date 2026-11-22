"""Deterministic, credential-free reconciliation projection for Bybit reports.

The Nautilus Bybit adapter owns transport and private-stream lifecycle.  This
module deliberately accepts only already parsed, secret-free report envelopes.
It joins REST order/fill/position/wallet snapshots with explicitly supplied
private event evidence, preserves unknown or incomplete state as protected,
and writes one immutable revision through the data store. REST rows remain
snapshot evidence and are never relabelled as private events.
It never creates a Nautilus node, resolves credentials, retries a venue call, or
infers that an empty report means a flat account.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from time import time_ns
from typing import Final

from quant_data.reconciliation_events import NativeEventEvidence
from quant_data.reconciliation_store import (
    ReconciliationEvidence,
    ReconciliationRecord,
    ReconciliationStore,
)


class ReconciliationError(ValueError):
    """A report cannot be safely projected; the code is safe to expose."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


_MAX_AGE_NS: Final = 30_000_000_000
_MAX_FUTURE_SKEW_NS: Final = 5_000_000_000
_MAX_DECIMAL: Final = Decimal("1e30")
_ORDER_RANK: Final = {
    "NEW": 10,
    "ACCEPTED": 10,
    "PARTIALLY_FILLED": 20,
    "FILLED": 30,
    "CANCELED": 30,
    "CANCELLED": 30,
    "REJECTED": 30,
    "EXPIRED": 30,
}
_SIDES: Final = frozenset({"BUY", "SELL", "BOTH"})
_ORDER_KEYS: Final = frozenset(
    {
        "event_id",
        "client_order_id",
        "venue_order_id",
        "symbol",
        "side",
        "status",
        "quantity",
        "filled_quantity",
        "timestamp_ns",
        "reason",
    }
)
_EXECUTION_KEYS: Final = frozenset(
    {
        "event_id",
        "trade_id",
        "client_order_id",
        "venue_order_id",
        "symbol",
        "side",
        "quantity",
        "price",
        "timestamp_ns",
    }
)
_POSITION_KEYS: Final = frozenset({"event_id", "symbol", "side", "quantity", "average_entry_price", "timestamp_ns"})
_WALLET_KEYS: Final = frozenset({"account_type", "total_equity_usdt", "available_margin_usdt", "observed_at_ns"})


@dataclass(frozen=True)
class BybitReconciliationBatch:
    """A single server-owned join of canonical REST and private reports.

    The booleans are explicit because the upstream adapter can return an empty
    list after a transport/API error.  Callers must set the corresponding flag
    false in that case; an empty list with all flags true means a verified empty
    report, not an implicit account reset.
    """

    session_id: str
    generation: int
    revision: int
    observed_at_ns: int
    wallet: Mapping[str, object]
    positions: Sequence[Mapping[str, object]]
    orders: Sequence[Mapping[str, object]]
    executions: Sequence[Mapping[str, object]]
    orders_complete: bool = True
    positions_complete: bool = True
    executions_complete: bool = True
    pagination_complete: bool = True
    private_stream_healthy: bool = True
    expected_client_order_ids: Collection[str] = field(default_factory=tuple)
    expected_venue_order_ids: Collection[str] = field(default_factory=tuple)
    private_events: tuple[NativeEventEvidence, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ReconciliationError("session_invalid")
        if type(self.generation) is not int or self.generation < 0:
            raise ReconciliationError("generation_invalid")
        if type(self.revision) is not int or self.revision <= 0:
            raise ReconciliationError("revision_invalid")
        if type(self.observed_at_ns) is not int or self.observed_at_ns < 0:
            raise ReconciliationError("timestamp_invalid")
        for name in (
            "orders_complete",
            "positions_complete",
            "executions_complete",
            "pagination_complete",
            "private_stream_healthy",
        ):
            if type(getattr(self, name)) is not bool:
                raise ReconciliationError("coverage_invalid")
        if not isinstance(self.wallet, Mapping) or not all(
            isinstance(row, Mapping) for row in (*self.positions, *self.orders, *self.executions)
        ):
            raise ReconciliationError("report_schema_invalid")
        for values in (self.expected_client_order_ids, self.expected_venue_order_ids):
            if (
                isinstance(values, (str, bytes))
                or not isinstance(values, Collection)
                or any(not isinstance(item, str) or not item for item in values)
            ):
                raise ReconciliationError("identity_invalid")
            if len(values) > 10_000:
                raise ReconciliationError("identity_limit")
        if type(self.private_events) is not tuple or any(
            not isinstance(event, NativeEventEvidence) for event in self.private_events
        ):
            raise ReconciliationError("private_event_schema_invalid")


class BybitReconciliationProjector:
    """Validate one batch and append its redacted evidence revision."""

    def __init__(self, store: ReconciliationStore, *, clock_ns: Callable[[], int] | None = None) -> None:
        self._store = store
        self._clock_ns = clock_ns or time_ns

    def project(self, batch: BybitReconciliationBatch, *, now_ns: int | None = None) -> ReconciliationRecord:
        evidence = self.normalize(batch, now_ns=self._clock_ns() if now_ns is None else now_ns)
        return self._store.record(evidence)

    @classmethod
    def normalize(cls, batch: BybitReconciliationBatch, *, now_ns: int) -> ReconciliationEvidence:
        if type(now_ns) is not int or now_ns < 0:
            raise ReconciliationError("timestamp_invalid")
        age = now_ns - batch.observed_at_ns
        reasons: set[str] = set()
        if age < -_MAX_FUTURE_SKEW_NS or age > _MAX_AGE_NS:
            reasons.add("snapshot_stale_or_future")
        if not batch.orders_complete:
            reasons.add("orders_incomplete")
        if not batch.positions_complete:
            reasons.add("positions_incomplete")
        if not batch.executions_complete:
            reasons.add("executions_incomplete")
        if not batch.pagination_complete:
            reasons.add("pagination_incomplete")
        if not batch.private_stream_healthy:
            reasons.add("private_stream_unhealthy")

        wallet = _wallet(batch.wallet, batch.observed_at_ns)
        positions = _positions(batch.positions, batch.observed_at_ns)
        orders, order_reasons = _orders(batch.orders, batch.observed_at_ns)
        executions, execution_reasons = _executions(batch.executions, batch.observed_at_ns)
        reasons.update(order_reasons)
        reasons.update(execution_reasons)
        reasons.update(
            _check_order_progression(
                orders,
                executions,
                require_complete=batch.executions_complete and batch.pagination_complete,
            )
        )
        reasons.update(_check_known_ids(orders, batch.expected_client_order_ids, batch.expected_venue_order_ids))
        reasons.update(
            _check_private_event_ids(
                batch.private_events,
                orders,
                executions,
                batch.expected_client_order_ids,
                batch.expected_venue_order_ids,
            )
        )
        if any(item["client_order_id"] is None and item["venue_order_id"] is None for item in orders):
            reasons.add("unknown_order_identity")
        protected = tuple(sorted(reasons))
        return ReconciliationEvidence(
            session_id=batch.session_id,
            revision=batch.revision,
            wallet=wallet,
            positions=positions,
            orders=orders,
            executions=executions,
            complete=not protected,
            protected_reason=protected[0] if protected else None,
            observed_at_ns=batch.observed_at_ns,
            generation=batch.generation,
            native_events=batch.private_events,
        )


def _mapping(value: object, keys: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value) or not frozenset(value) <= keys:
        raise ReconciliationError("report_schema_invalid")
    return value


def _text(value: object, *, allow_none: bool = False, code: str = "report_field_invalid") -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise ReconciliationError(code)
    if any(ord(char) < 0x20 or char in "\r\n" for char in value):
        raise ReconciliationError(code)
    return value


def _number(value: object, *, positive: bool = False) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ReconciliationError("numeric_field_invalid")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ReconciliationError("numeric_field_invalid") from None
    if not parsed.is_finite() or parsed < 0 or parsed > _MAX_DECIMAL or (positive and parsed <= 0):
        raise ReconciliationError("numeric_field_invalid")
    text = format(parsed, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _timestamp(value: object, observed_at_ns: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReconciliationError("timestamp_invalid")
    if value > observed_at_ns + _MAX_FUTURE_SKEW_NS:
        raise ReconciliationError("timestamp_invalid")
    return value


def _side(value: object) -> str:
    text = _text(value)
    assert text is not None
    side = text.upper()
    if side not in _SIDES:
        raise ReconciliationError("side_invalid")
    return side


def _wallet(raw: Mapping[str, object], observed_at_ns: int) -> dict[str, str | int]:
    row = _mapping(raw, _WALLET_KEYS)
    account_type = _text(row.get("account_type"))
    if account_type != "UNIFIED":
        raise ReconciliationError("account_type_unsupported")
    observed = row.get("observed_at_ns")
    return {
        "account_type": account_type,
        "total_equity_usdt": _number(row.get("total_equity_usdt")),
        "available_margin_usdt": _number(row.get("available_margin_usdt")),
        "observed_at_ns": _timestamp(observed, observed_at_ns),
    }


def _positions(raw: Sequence[Mapping[str, object]], observed_at_ns: int) -> list[dict[str, str | int | None]]:
    result: list[dict[str, str | int | None]] = []
    for item in raw:
        row = _mapping(item, _POSITION_KEYS)
        symbol = _text(row.get("symbol"))
        side = _side(row.get("side"))
        timestamp = _timestamp(row.get("timestamp_ns"), observed_at_ns)
        event_id = _text(row.get("event_id"), allow_none=True) or f"position:{symbol}:{side}"
        assert symbol is not None and event_id is not None
        result.append(
            {
                "event_id": event_id,
                "symbol": symbol,
                "side": side,
                "quantity": _number(row.get("quantity")),
                "average_entry_price": _number(row.get("average_entry_price")),
                "timestamp_ns": timestamp,
            }
        )
    return sorted(result, key=_order_sort_key)


def _orders(
    raw: Sequence[Mapping[str, object]], observed_at_ns: int
) -> tuple[list[dict[str, str | int | None]], set[str]]:
    result: list[dict[str, str | int | None]] = []
    reasons: set[str] = set()
    for item in raw:
        row = _mapping(item, _ORDER_KEYS)
        status = _text(row.get("status"))
        assert status is not None
        normalized_status = _normalize_status(status)
        if normalized_status not in _ORDER_RANK:
            normalized_status = "UNKNOWN"
            reasons.add("order_status_unknown")
        result.append(
            {
                "event_id": _text(row.get("event_id")),
                "client_order_id": _text(row.get("client_order_id"), allow_none=True),
                "venue_order_id": _text(row.get("venue_order_id"), allow_none=True),
                "symbol": _text(row.get("symbol")),
                "side": _side(row.get("side")),
                "status": normalized_status,
                "quantity": _number(row.get("quantity"), positive=True),
                "filled_quantity": _number(row.get("filled_quantity")),
                "timestamp_ns": _timestamp(row.get("timestamp_ns"), observed_at_ns),
                "reason": _text(row.get("reason"), allow_none=True),
            }
        )
    unique, dedupe_reasons = _deduplicate(result, "event_id")
    reasons.update(dedupe_reasons)
    return sorted(unique, key=_order_sort_key), reasons


def _executions(
    raw: Sequence[Mapping[str, object]], observed_at_ns: int
) -> tuple[list[dict[str, str | int | None]], set[str]]:
    result: list[dict[str, str | int | None]] = []
    for item in raw:
        row = _mapping(item, _EXECUTION_KEYS)
        result.append(
            {
                "event_id": _text(row.get("event_id")),
                "trade_id": _text(row.get("trade_id"), allow_none=True),
                "client_order_id": _text(row.get("client_order_id"), allow_none=True),
                "venue_order_id": _text(row.get("venue_order_id"), allow_none=True),
                "symbol": _text(row.get("symbol")),
                "side": _side(row.get("side")),
                "quantity": _number(row.get("quantity"), positive=True),
                "price": _number(row.get("price"), positive=True),
                "timestamp_ns": _timestamp(row.get("timestamp_ns"), observed_at_ns),
            }
        )
    unique, reasons = _deduplicate(result, "event_id")
    return sorted(unique, key=_order_sort_key), reasons


def _deduplicate(
    rows: Sequence[dict[str, str | int | None]], field: str
) -> tuple[list[dict[str, str | int | None]], set[str]]:
    seen: dict[str, Mapping[str, object]] = {}
    unique: list[dict[str, str | int | None]] = []
    reasons: set[str] = set()
    for row in rows:
        value = row[field]
        assert isinstance(value, str)
        prior = seen.get(value)
        if prior is not None:
            if dict(prior) != dict(row):
                reasons.add("event_conflict")
            continue
        seen[value] = row
        unique.append(row)
    return unique, reasons


def _order_sort_key(row: Mapping[str, object]) -> tuple[int, str]:
    timestamp = row["timestamp_ns"]
    event_id = row["event_id"]
    if not isinstance(timestamp, int) or not isinstance(event_id, str):
        raise ReconciliationError("report_schema_invalid")
    return timestamp, event_id


def _int_field(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ReconciliationError("report_schema_invalid")
    return value


def _normalize_status(status: str) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", status)
    return re.sub(r"[\s-]+", "_", separated).upper()


def _check_order_progression(
    orders: Sequence[Mapping[str, object]],
    executions: Sequence[Mapping[str, object]],
    *,
    require_complete: bool,
) -> set[str]:
    reasons: set[str] = set()
    prior: dict[tuple[object, object, object], tuple[int, Decimal]] = {}
    for row in orders:
        key = (row["client_order_id"], row["venue_order_id"], row["symbol"])
        status = str(row["status"])
        if status not in _ORDER_RANK:
            reasons.add("order_status_unknown")
            continue
        filled = Decimal(str(row["filled_quantity"]))
        old = prior.get(key)
        if old is not None and (_ORDER_RANK[status] < old[0] or filled < old[1]):
            reasons.add("order_progression_invalid")
        prior[key] = (_ORDER_RANK[status], max(filled, old[1] if old else Decimal(0)))
        if filled > Decimal(str(row["quantity"])):
            reasons.add("fill_overrun")

    filled_by_order: dict[tuple[object, object], Decimal] = {}
    for row in executions:
        key = (row["client_order_id"], row["venue_order_id"])
        filled_by_order[key] = filled_by_order.get(key, Decimal(0)) + Decimal(str(row["quantity"]))
    for row in orders:
        key = (row["client_order_id"], row["venue_order_id"])
        execution_qty = filled_by_order.get(key, Decimal(0))
        if execution_qty > Decimal(str(row["quantity"])):
            reasons.add("fill_overrun")
        if execution_qty > Decimal(str(row["filled_quantity"])):
            reasons.add("execution_exceeds_order_cumulative")
        if require_complete and execution_qty != Decimal(str(row["filled_quantity"])):
            reasons.add("execution_fill_mismatch")
    return reasons


def _check_known_ids(
    orders: Sequence[Mapping[str, object]], expected_clients: Collection[str], expected_venues: Collection[str]
) -> set[str]:
    reasons: set[str] = set()
    for row in orders:
        client = row["client_order_id"]
        venue = row["venue_order_id"]
        client_known = isinstance(client, str) and client in expected_clients
        venue_known = isinstance(venue, str) and venue in expected_venues
        if not client_known and not venue_known:
            reasons.add("unknown_order_identity")
    return reasons


def _check_private_event_ids(
    events: Sequence[NativeEventEvidence],
    orders: Sequence[Mapping[str, object]],
    executions: Sequence[Mapping[str, object]],
    expected_clients: Collection[str],
    expected_venues: Collection[str],
) -> set[str]:
    known_clients = set(expected_clients)
    known_venues = set(expected_venues)
    for row in (*orders, *executions):
        client = row.get("client_order_id")
        venue = row.get("venue_order_id")
        if isinstance(client, str):
            known_clients.add(client)
        if isinstance(venue, str):
            known_venues.add(venue)

    reasons: set[str] = set()
    for event in events:
        if event.client_order_id is None and event.venue_order_id is None:
            reasons.add("unknown_private_event_identity")
            continue
        if event.client_order_id is not None and event.client_order_id not in known_clients:
            reasons.add("unknown_private_event_identity")
        if event.venue_order_id is not None and event.venue_order_id not in known_venues:
            reasons.add("unknown_private_event_identity")
    return reasons


def reconcile_bybit_reports(
    store: ReconciliationStore,
    batch: BybitReconciliationBatch,
    *,
    now_ns: int | None = None,
) -> ReconciliationRecord:
    """Functional facade used by session code and deterministic tests."""

    return BybitReconciliationProjector(store).project(batch, now_ns=now_ns)


__all__ = [
    "BybitReconciliationBatch",
    "BybitReconciliationProjector",
    "ReconciliationError",
    "reconcile_bybit_reports",
]
