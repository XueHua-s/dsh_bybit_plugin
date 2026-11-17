"""Secret-free command contracts; canonical forms are owned by this boundary."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Environment(StrEnum):
    BACKTEST = "backtest"
    INTERNAL_PAPER = "internal_paper"
    DEMO = "demo"
    TESTNET = "testnet"


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class CommandState(StrEnum):
    ADMITTED = "admitted"
    READY = "ready"
    RISK_REJECTED = "risk_rejected"
    DISPATCHING = "dispatching"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class RiskCode(StrEnum):
    APPROVED = "approved"
    ACCOUNT = "account"
    BALANCE = "balance"
    INSTRUMENT = "instrument"
    LIMIT = "limit"
    STALE_DATA = "stale_data"
    EMERGENCY_STOP = "emergency_stop"


def identifier(value: str, name: str) -> str:
    """Accept bounded opaque references, never raw credentials or untrusted prose."""
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value) is None:
        raise ValueError(f"invalid {name}")
    return value


def decimal_text(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0 or value > Decimal("1e30"):
        raise ValueError("quantity/price must be a finite nonnegative Decimal <= 1e30")
    # Avoid context-dependent Decimal.normalize rounding and unbounded fractional payloads.
    if value == 0:
        return "0"
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int) or exponent < -18:
        raise ValueError("quantity/price supports at most 18 fractional places")
    return format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")


def canonical(fields: dict[str, str | bool | None]) -> str:
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class OrderCommand:
    """A single immutable submit intention; account_ref is an internal non-secret alias."""

    environment: Environment
    account_ref: str
    request_id: str
    symbol: str
    side: Side
    order_type: OrderType
    quantity: Decimal
    limit_price: Decimal | None = None
    reduce_only: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.environment, Environment) or not isinstance(self.side, Side):
            raise TypeError("typed environment and side required")
        if not isinstance(self.order_type, OrderType) or not isinstance(self.reduce_only, bool):
            raise TypeError("typed order type and boolean reduce_only required")
        for name in ("account_ref", "request_id", "symbol"):
            identifier(getattr(self, name), name)
        decimal_text(self.quantity)
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type == OrderType.LIMIT:
            if self.limit_price is not None:
                decimal_text(self.limit_price)
            if self.limit_price is None or self.limit_price <= 0:
                raise ValueError("limit orders require a positive price")
        elif self.limit_price is not None:
            raise ValueError("market orders cannot contain a limit price")

    def canonical(self) -> str:
        return canonical(
            {
                "schema": "order-command-v1",
                "environment": self.environment.value,
                "account_ref": self.account_ref,
                "request_id": self.request_id,
                "symbol": self.symbol,
                "side": self.side.value,
                "order_type": self.order_type.value,
                "quantity": decimal_text(self.quantity),
                "limit_price": None if self.limit_price is None else decimal_text(self.limit_price),
                "reduce_only": self.reduce_only,
            }
        )


@dataclass(frozen=True)
class CommandRecord:
    id: str
    command: OrderCommand
    fingerprint: str
    native_client_order_id: str
    state: CommandState
    cumulative_filled: Decimal
    version: int


@dataclass(frozen=True)
class AuditRecord:
    event_id: str
    state: CommandState
    cumulative_filled: Decimal
    decision_code: RiskCode | None
    version: int


class LedgerConflict(ValueError):
    """An idempotency key was reused for a different immutable payload."""


class InvalidTransition(ValueError):
    """State changed concurrently or the requested transition is forbidden."""
