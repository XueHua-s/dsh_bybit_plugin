"""Construct native instruments and finite quote streams from explicit offline metadata."""

from decimal import Decimal

from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import BookOrder, OrderBookDelta, OrderBookDeltas, QuoteTick
from nautilus_trader.model.enums import BookAction, OrderSide
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Currency, Money, Price, Quantity

from .models import InstrumentSpec, Quote


def make_instrument(spec: InstrumentSpec) -> CryptoPerpetual:
    for value in (spec.price_increment, spec.size_increment, spec.min_quantity, spec.max_quantity, spec.min_notional):
        if not value.is_finite() or value <= 0:
            raise ValueError("instrument rules must be finite and positive")
    if spec.min_quantity > spec.max_quantity:
        raise ValueError("invalid instrument quantity range")
    if not spec.symbol or not spec.symbol.isalnum():
        raise ValueError("fixture symbol must be alphanumeric")
    for fee in (spec.maker_fee, spec.taker_fee):
        if not fee.is_finite() or fee < 0:
            raise ValueError("fixture fee must be finite and nonnegative")
    return CryptoPerpetual(
        instrument_id=InstrumentId(Symbol(spec.symbol), Venue("SIM")),
        raw_symbol=Symbol(spec.symbol),
        base_currency=Currency.from_str(spec.base_currency),
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=max(0, -int(spec.price_increment.as_tuple().exponent)),
        size_precision=max(0, -int(spec.size_increment.as_tuple().exponent)),
        price_increment=Price.from_str(str(spec.price_increment)),
        size_increment=Quantity.from_str(str(spec.size_increment)),
        min_quantity=Quantity.from_str(str(spec.min_quantity)),
        max_quantity=Quantity.from_str(str(spec.max_quantity)),
        min_notional=Money(spec.min_notional, USDT),
        margin_init=Decimal(1),
        margin_maint=Decimal("0.5"),
        maker_fee=spec.maker_fee,
        taker_fee=spec.taker_fee,
        ts_event=0,
        ts_init=0,
    )


def make_quotes(instrument: CryptoPerpetual, quotes: tuple[Quote, ...]) -> list[QuoteTick]:
    if len(quotes) < 3:
        raise ValueError("at least three quotes required for submission and confirmed cancellation")
    previous = 0
    result: list[QuoteTick] = []
    for quote in quotes:
        if quote.timestamp_ns <= previous:
            raise ValueError("quote timestamps must strictly increase from a positive epoch")
        previous = quote.timestamp_ns
        for value in (quote.bid, quote.ask, quote.size):
            if not value.is_finite() or value <= 0:
                raise ValueError("quotes must be finite and positive")
        if quote.ask < quote.bid:
            raise ValueError("crossed quote")
        if quote.bid % instrument.price_increment.as_decimal() or quote.ask % instrument.price_increment.as_decimal():
            raise ValueError("quote price does not match instrument increment")
        if quote.size % instrument.size_increment.as_decimal():
            raise ValueError("quote size does not match instrument increment")
        result.append(
            QuoteTick(
                instrument_id=instrument.id,
                bid_price=Price.from_str(str(quote.bid)),
                ask_price=Price.from_str(str(quote.ask)),
                bid_size=Quantity.from_str(str(quote.size)),
                ask_size=Quantity.from_str(str(quote.size)),
                ts_event=quote.timestamp_ns,
                ts_init=quote.timestamp_ns,
            )
        )
    return result


def initial_book(instrument: CryptoPerpetual, quote: Quote) -> OrderBookDeltas:
    """One finite L2 snapshot, without synthetic replenishment of consumed liquidity."""
    timestamp = quote.timestamp_ns - 1
    deltas = [OrderBookDelta.clear(instrument.id, 0, timestamp, timestamp)]
    for side, price in ((OrderSide.BUY, quote.bid), (OrderSide.SELL, quote.ask)):
        order = BookOrder(side, Price.from_str(str(price)), Quantity.from_str(str(quote.size)), 0)
        deltas.append(OrderBookDelta(instrument.id, BookAction.ADD, order, 0, 0, timestamp, timestamp))
    return OrderBookDeltas(instrument.id, deltas)
