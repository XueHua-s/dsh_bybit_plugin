"""Immutable synthetic session inputs and native execution evidence; never authorization."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from .models import InstrumentSpec


@dataclass(frozen=True)
class PaperDepth:
    bid: Decimal
    ask: Decimal
    bid_size: Decimal
    ask_size: Decimal
    timestamp_ns: int


@dataclass(frozen=True)
class PaperFixture:
    instrument: InstrumentSpec
    initial_depth: PaperDepth
    starting_balance: Decimal


@dataclass(frozen=True)
class PaperOrder:
    client_order_id: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    limit_price: Decimal | None = None


@dataclass(frozen=True)
class PaperEvent:
    event_id: str
    client_order_id: str
    event_type: str
    status: str
    cumulative_filled_quantity: Decimal
    last_fill_quantity: Decimal | None
    last_fill_price: Decimal | None
    trade_id: str | None
    account_id: str | None
    position_id: str | None
    commission: Decimal | None
    currency: str | None
    timestamp_ns: int


@dataclass(frozen=True)
class PaperSnapshot:
    status: str
    account_id: str
    balance_total: Decimal
    balance_free: Decimal
    position_quantity: Decimal
    open_order_ids: tuple[str, ...]
    process_alive: bool
    process_id: int | None
    loop_closed: bool
    node_instance_id: str
    market_timestamp_ns: int
    bid: Decimal
    ask: Decimal
    bid_size: Decimal
    ask_size: Decimal
    failure_reason: str | None = None
    event_stream_complete: bool = True
    equity: Decimal = Decimal(0)
    unrealized_pnl: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    snapshot_timestamp_ns: int = 0
    available_equity: Decimal = Decimal(0)
