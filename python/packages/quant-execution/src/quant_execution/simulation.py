"""Native finite simulation. No live client, credentials or production executor exists here."""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig, StrategyConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, BookType, OmsType, OrderSide
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.model.orders import Order
from nautilus_trader.trading.strategy import Strategy

from .fixtures import initial_book, make_instrument, make_quotes
from .models import InstrumentSpec, NativeOrderResult, OrderIntent, Quote, SimulationResult


def _admit(instrument: CryptoPerpetual, quotes: tuple[Quote, ...], intents: tuple[OrderIntent, ...]) -> None:
    seen: set[str] = set()
    for intent in intents:
        if not intent.request_id.strip() or intent.request_id in seen:
            raise ValueError("empty or duplicate request ID")
        seen.add(intent.request_id)
        if intent.side not in ("BUY", "SELL"):
            raise ValueError("invalid side")
        quantity = intent.quantity
        if not quantity.is_finite() or quantity <= 0:
            raise ValueError("quantity must be finite and positive")
        if quantity % instrument.size_increment.as_decimal():
            raise ValueError("quantity does not match instrument increment")
        if instrument.min_quantity is not None and quantity < instrument.min_quantity.as_decimal():
            raise ValueError("quantity below minimum")
        if instrument.max_quantity is not None and quantity > instrument.max_quantity.as_decimal():
            raise ValueError("quantity above maximum")
        price = intent.limit_price
        if price is not None and (
            not price.is_finite() or price <= 0 or price % instrument.price_increment.as_decimal()
        ):
            raise ValueError("invalid limit price increment")
        # Conservative reference for a finite fixture admission, not a live price guarantee.
        reference = price if price is not None else min(quotes[0].bid, quotes[0].ask)
        if instrument.min_notional is not None and quantity * reference < instrument.min_notional.as_decimal():
            raise ValueError("order below minimum notional")


class _PlanStrategy(Strategy):
    """Own all native order creation and callback sequencing inside one private boundary."""

    def __init__(self, instrument: CryptoPerpetual, intents: tuple[OrderIntent, ...]) -> None:
        super().__init__(StrategyConfig(use_uuid_client_order_ids=True))
        self.instrument = instrument
        self.intents = intents
        self.native_orders: list[tuple[str, Order]] = []
        self.tick_count = 0
        self.stopped = False

    def on_start(self) -> None:
        self.subscribe_quote_ticks(self.instrument.id)

    def on_quote_tick(self, tick: QuoteTick) -> None:
        self.tick_count += 1
        if self.tick_count == 1:
            for intent in self.intents:
                side = OrderSide.BUY if intent.side == "BUY" else OrderSide.SELL
                quantity = Quantity.from_str(str(intent.quantity))
                if intent.limit_price is None:
                    order = self.order_factory.market(self.instrument.id, side, quantity)
                else:
                    order = self.order_factory.limit(
                        self.instrument.id,
                        side,
                        quantity,
                        Price.from_str(str(intent.limit_price)),
                    )
                self.native_orders.append((intent.request_id, order))
                self.submit_order(order)
        elif self.tick_count == 2:
            self.cancel_all_orders(self.instrument.id)

    def on_stop(self) -> None:
        self.unsubscribe_quote_ticks(self.instrument.id)
        self.stopped = True


def run_simulation(
    instrument: InstrumentSpec,
    quotes: tuple[Quote, ...],
    intents: tuple[OrderIntent, ...],
    *,
    environment: str = "backtest",
) -> SimulationResult:
    """Execute only a finite offline native backtest; every other environment fails closed.

    The fixed synthetic cash balance is deliberately fixture-only. This function does not
    grant Testnet/Mainnet authorization, validate portfolio risk or recover exchange state.
    """
    if environment != "backtest":
        raise ValueError("only offline backtest is supported")
    native_instrument = make_instrument(instrument)
    ticks = make_quotes(native_instrument, quotes)
    if any((q.bid, q.ask, q.size) != (quotes[0].bid, quotes[0].ask, quotes[0].size) for q in quotes):
        raise ValueError("single snapshot fixture requires stationary quote callbacks")
    _admit(native_instrument, quotes, intents)
    strategy = _PlanStrategy(native_instrument, intents)
    engine = BacktestEngine(
        BacktestEngineConfig(
            trader_id=TraderId("OFFLINE-001"),
            logging=LoggingConfig(bypass_logging=True),
            run_analysis=False,
        )
    )
    try:
        engine.add_venue(
            venue=Venue("SIM"),
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            base_currency=USDT,
            starting_balances=[Money(Decimal(1000000), USDT)],
            default_leverage=Decimal(1),
            book_type=BookType.L2_MBP,
            liquidity_consumption=True,
        )
        engine.add_instrument(native_instrument)
        engine.add_data([initial_book(native_instrument, quotes[0])])
        engine.add_data(ticks)
        engine.add_strategy(strategy)
        engine.run()
        orders = tuple(
            NativeOrderResult(
                request_id=request_id,
                client_order_id=str(order.client_order_id),
                status=order.status.name,
                filled_quantity=order.filled_qty.as_decimal(),
                events=tuple(type(event).__name__ for event in order.events),
                fill_quantities=tuple(
                    event.last_qty.as_decimal() for event in order.events if isinstance(event, OrderFilled)
                ),
            )
            for request_id, order in strategy.native_orders
        )
        open_orders = len(engine.cache.orders_open())
    finally:
        engine.dispose()
    return SimulationResult(orders, engine.trader.is_disposed and strategy.is_disposed, strategy.stopped, open_orders)
