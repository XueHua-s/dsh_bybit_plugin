"""Offline tests for the server-owned Testnet order mapping boundary."""

from __future__ import annotations

from decimal import Decimal

import pytest
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId, StrategyId, Symbol, TraderId, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Currency, Money, Price, Quantity
from quant_data.commands import (
    CommandRecord,
    CommandState,
    Environment,
    OrderCommand,
    OrderType,
    Side,
    canonical,
    fingerprint,
)
from quant_execution.bybit_order_mapper import map_testnet_order


def _instrument(symbol: str = "BTCUSDT") -> CryptoPerpetual:
    return CryptoPerpetual(
        instrument_id=InstrumentId(Symbol(symbol), Venue("BYBIT")),
        raw_symbol=Symbol(symbol),
        base_currency=Currency.from_str("BTC"),
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=1,
        size_precision=3,
        price_increment=Price.from_str("0.1"),
        size_increment=Quantity.from_str("0.001"),
        min_quantity=Quantity.from_str("0.001"),
        max_quantity=Quantity.from_str("100"),
        min_notional=Money.from_str("5 USDT"),
        margin_init=Decimal(1),
        margin_maint=Decimal("0.5"),
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.0006"),
        ts_event=0,
        ts_init=0,
    )


def _command(
    order_type: OrderType = OrderType.LIMIT,
    environment: Environment = Environment.TESTNET,
    quantity: Decimal = Decimal("0.010"),
    limit_price: Decimal | None = None,
    reduce_only: bool = False,
) -> OrderCommand:
    return OrderCommand(
        environment=environment,
        account_ref="account-fixture",
        request_id="request-fixture",
        symbol="BTCUSDT",
        side=Side.BUY,
        order_type=order_type,
        quantity=quantity,
        limit_price=(Decimal("60000.0") if limit_price is None else limit_price)
        if order_type is OrderType.LIMIT
        else None,
        reduce_only=reduce_only,
    )


def _record(command: OrderCommand, client_id: str | None = None) -> CommandRecord:
    scope = canonical(
        {
            "environment": command.environment.value,
            "account_ref": command.account_ref,
            "request_id": command.request_id,
        }
    )
    allocated_id = "q" + fingerprint(scope)[:32] if client_id is None else client_id
    return CommandRecord(
        "command-fixture",
        command,
        fingerprint(command.canonical()),
        allocated_id,
        CommandState.READY,
        Decimal(0),
        0,
    )


def test_maps_limit_with_stable_id_and_reduce_only() -> None:
    record = _record(_command(reduce_only=True))
    order = map_testnet_order(
        record,
        _instrument(),
        TraderId("TRADER-001"),
        StrategyId("STRATEGY-001"),
        init_id=UUID4.from_str("00000000-0000-4000-8000-000000000001"),
        ts_init_ns=123,
    )
    assert order.client_order_id.value == record.native_client_order_id
    assert order.instrument_id.value == "BTCUSDT.BYBIT"
    assert order.side is OrderSide.BUY
    assert order.quantity.as_decimal() == Decimal("0.010")
    assert order.price.as_decimal() == Decimal("60000.0")
    assert order.is_reduce_only
    assert order.ts_init == 123


def test_maps_market_without_price() -> None:
    record = _record(_command(OrderType.MARKET))
    order = map_testnet_order(
        record,
        _instrument(),
        TraderId("TRADER-001"),
        StrategyId("STRATEGY-001"),
        ts_init_ns=1,
    )
    assert order.order_type.name == "MARKET"
    assert not order.has_price


def test_rejects_non_ready_command_record() -> None:
    command = _command()
    record = CommandRecord(
        "command-fixture",
        command,
        fingerprint(command.canonical()),
        _record(command).native_client_order_id,
        CommandState.ADMITTED,
        Decimal(0),
        0,
    )
    with pytest.raises(ValueError, match="risk-approved"):
        map_testnet_order(record, _instrument(), TraderId("TRADER-001"), StrategyId("STRATEGY-001"), ts_init_ns=1)


@pytest.mark.parametrize(
    "record, instrument, message",
    (
        (_record(_command(environment=Environment.DEMO)), _instrument(), "Testnet"),
        (_record(_command()), _instrument("ETHUSDT"), "catalog"),
        (_record(_command(), "not-ledger-id"), _instrument(), "client order ID"),
        (
            _record(_command(quantity=Decimal("0.0105"))),
            _instrument(),
            "increment",
        ),
        (
            _record(_command(limit_price=Decimal("60000.05"))),
            _instrument(),
            "increment",
        ),
    ),
)
def test_rejects_untrusted_or_inexact_inputs(
    record: CommandRecord,
    instrument: CryptoPerpetual,
    message: str,
) -> None:
    with pytest.raises((ValueError, TypeError), match=message):
        map_testnet_order(
            record,
            instrument,
            TraderId("TRADER-001"),
            StrategyId("STRATEGY-001"),
            ts_init_ns=1,
        )


def test_rejects_tampered_command_fingerprint() -> None:
    command = _command()
    record = CommandRecord(
        "command-fixture", command, "0" * 64, _record(command).native_client_order_id, CommandState.READY, Decimal(0), 0
    )
    with pytest.raises(ValueError, match="fingerprint"):
        map_testnet_order(record, _instrument(), TraderId("TRADER-001"), StrategyId("STRATEGY-001"), ts_init_ns=1)


def test_rejects_non_bybit_catalog_instrument() -> None:
    instrument = _instrument()
    sim = CryptoPerpetual(
        instrument_id=InstrumentId(Symbol("BTCUSDT"), Venue("SIM")),
        raw_symbol=instrument.raw_symbol,
        base_currency=instrument.base_currency,
        quote_currency=instrument.quote_currency,
        settlement_currency=instrument.settlement_currency,
        is_inverse=instrument.is_inverse,
        price_precision=instrument.price_precision,
        size_precision=instrument.size_precision,
        price_increment=instrument.price_increment,
        size_increment=instrument.size_increment,
        min_quantity=instrument.min_quantity,
        max_quantity=instrument.max_quantity,
        min_notional=instrument.min_notional,
        margin_init=instrument.margin_init,
        margin_maint=instrument.margin_maint,
        maker_fee=instrument.maker_fee,
        taker_fee=instrument.taker_fee,
        ts_event=0,
        ts_init=0,
    )
    with pytest.raises(ValueError, match="Bybit"):
        map_testnet_order(_record(_command()), sim, TraderId("TRADER-001"), StrategyId("STRATEGY-001"), ts_init_ns=1)
