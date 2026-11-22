"""Map an admitted Testnet Linear command to one Nautilus native order.

The mapper is deliberately a narrow boundary.  It accepts an instrument that
was resolved by the server-side catalog and an order ID allocated by the
durable command ledger.  It never rounds caller values, accepts venue IDs, or
performs exchange IO.
"""

from __future__ import annotations

import re
from decimal import Decimal

from nautilus_trader.core.uuid import UUID4
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import ClientOrderId, StrategyId, TraderId
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.orders import LimitOrder, MarketOrder
from quant_data.commands import CommandRecord, CommandState, Environment, OrderCommand, OrderType, Side, fingerprint

_LEDGER_ORDER_ID = re.compile(r"q[0-9a-f]{32}\Z")
_BYBIT_VENUE = "BYBIT"


def _exact_quantity(instrument: CryptoPerpetual, value: Decimal) -> Quantity:
    """Convert a quantity only when the instrument conversion is lossless."""

    if value <= 0 or not value.is_finite():
        raise ValueError("quantity must be finite and positive")
    increment = instrument.size_increment.as_decimal()
    if value % increment:
        raise ValueError("quantity does not match the instrument increment")
    if instrument.min_quantity is not None and value < instrument.min_quantity.as_decimal():
        raise ValueError("quantity is below the instrument minimum")
    if instrument.max_quantity is not None and value > instrument.max_quantity.as_decimal():
        raise ValueError("quantity is above the instrument maximum")
    try:
        quantity = instrument.make_qty(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("quantity is outside the instrument precision") from exc
    if quantity.as_decimal() != value:
        raise ValueError("quantity would be rounded by the instrument")
    return quantity


def _exact_price(instrument: CryptoPerpetual, value: Decimal) -> Price:
    """Convert a limit price only when the instrument conversion is lossless."""

    if value <= 0 or not value.is_finite():
        raise ValueError("limit price must be finite and positive")
    if value % instrument.price_increment.as_decimal():
        raise ValueError("limit price does not match the instrument increment")
    if instrument.min_price is not None and value < instrument.min_price.as_decimal():
        raise ValueError("limit price is below the instrument minimum")
    if instrument.max_price is not None and value > instrument.max_price.as_decimal():
        raise ValueError("limit price is above the instrument maximum")
    try:
        price = instrument.make_price(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("limit price is outside the instrument precision") from exc
    if price.as_decimal() != value:
        raise ValueError("limit price would be rounded by the instrument")
    return price


def map_testnet_order(
    record: CommandRecord,
    instrument: CryptoPerpetual,
    trader_id: TraderId,
    strategy_id: StrategyId,
    *,
    init_id: UUID4 | None = None,
    ts_init_ns: int,
) -> MarketOrder | LimitOrder:
    """Build one native Bybit Linear order from a ledger-approved record.

    The record carries the exact command and deterministic client ID allocated
    by the command ledger.  The instrument and runtime IDs are explicit so a
    UI symbol or caller-supplied venue cannot become execution authority.
    """

    if not isinstance(record, CommandRecord) or record.state is not CommandState.READY:
        raise ValueError("a risk-approved ledger record is required")
    command = record.command
    if record.fingerprint != fingerprint(command.canonical()):
        raise ValueError("ledger command fingerprint is invalid")
    if not isinstance(command, OrderCommand) or command.environment is not Environment.TESTNET:
        raise ValueError("only Testnet commands can be mapped")
    if not isinstance(instrument, CryptoPerpetual) or instrument.venue.value != _BYBIT_VENUE:
        raise ValueError("a Bybit instrument is required")
    if str(instrument.symbol) != command.symbol:
        raise ValueError("command symbol does not match the catalog instrument")
    if not isinstance(trader_id, TraderId) or not isinstance(strategy_id, StrategyId):
        raise TypeError("native trader and strategy IDs are required")
    if (
        not isinstance(record.native_client_order_id, str)
        or _LEDGER_ORDER_ID.fullmatch(record.native_client_order_id) is None
    ):
        raise ValueError("native client order ID is invalid")
    if isinstance(ts_init_ns, bool) or not isinstance(ts_init_ns, int) or ts_init_ns <= 0:
        raise ValueError("ts_init_ns must be a positive integer")

    side = OrderSide.BUY if command.side is Side.BUY else OrderSide.SELL
    quantity = _exact_quantity(instrument, command.quantity)
    client_order_id = ClientOrderId(record.native_client_order_id)
    event_id = init_id if init_id is not None else UUID4()

    if command.order_type is OrderType.MARKET:
        return MarketOrder(
            trader_id=trader_id,
            strategy_id=strategy_id,
            instrument_id=instrument.id,
            client_order_id=client_order_id,
            order_side=side,
            quantity=quantity,
            init_id=event_id,
            ts_init=ts_init_ns,
            time_in_force=TimeInForce.GTC,
            reduce_only=command.reduce_only,
        )

    if command.order_type is not OrderType.LIMIT or command.limit_price is None:
        raise ValueError("unsupported order type")
    price = _exact_price(instrument, command.limit_price)
    return LimitOrder(
        trader_id=trader_id,
        strategy_id=strategy_id,
        instrument_id=instrument.id,
        client_order_id=client_order_id,
        order_side=side,
        quantity=quantity,
        price=price,
        init_id=event_id,
        ts_init=ts_init_ns,
        time_in_force=TimeInForce.GTC,
        reduce_only=command.reduce_only,
    )


__all__ = ["map_testnet_order"]
