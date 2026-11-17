"""Immutable offline plan and native execution evidence; never exchange authorization."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class InstrumentSpec:
    """Explicit fixture rules, not asserted to be current exchange instrument metadata."""

    symbol: str
    base_currency: str
    price_increment: Decimal
    size_increment: Decimal
    min_quantity: Decimal
    max_quantity: Decimal
    min_notional: Decimal
    maker_fee: Decimal = Decimal("0.0002")
    taker_fee: Decimal = Decimal("0.0006")


@dataclass(frozen=True)
class Quote:
    bid: Decimal
    ask: Decimal
    size: Decimal
    timestamp_ns: int


@dataclass(frozen=True)
class OrderIntent:
    """A request key is admitted once per finite run; None price means market order."""

    request_id: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    limit_price: Decimal | None = None


@dataclass(frozen=True)
class NativeOrderResult:
    request_id: str
    client_order_id: str
    status: str
    filled_quantity: Decimal
    events: tuple[str, ...]
    fill_quantities: tuple[Decimal, ...]


@dataclass(frozen=True)
class SimulationResult:
    """Evidence is read from native cached orders after the run; disposal is guaranteed."""

    orders: tuple[NativeOrderResult, ...]
    disposed: bool
    strategy_stopped: bool
    open_orders: int
