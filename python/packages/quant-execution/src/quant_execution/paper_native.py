"""Private native owner: pinned worker-safe node construction, strategy and evidence."""

import asyncio
from collections.abc import Callable
from decimal import Decimal

from nautilus_trader.adapters.sandbox.config import SandboxExecutionClientConfig
from nautilus_trader.config import LiveExecEngineConfig, LoggingConfig, StrategyConfig, TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import BookOrder, OrderBookDelta, OrderBookDeltas, QuoteTick
from nautilus_trader.model.enums import BookAction, OrderSide
from nautilus_trader.model.events import OrderEvent, OrderFilled
from nautilus_trader.model.identifiers import AccountId, ClientOrderId, TraderId, Venue
from nautilus_trader.trading.strategy import Strategy

from .fixtures import make_instrument
from .paper_models import PaperDepth, PaperEvent, PaperFixture, PaperOrder
from .paper_sandbox import SandboxLiveExecClientFactory


class _PaperStrategy(Strategy):
    def __init__(self, emit: Callable[[PaperEvent], None]) -> None:
        super().__init__(StrategyConfig(use_uuid_client_order_ids=True))
        self.emit = emit

    def on_order_event(self, event: OrderEvent) -> None:
        order = self.cache.order(event.client_order_id)
        fill = event if isinstance(event, OrderFilled) else None
        self.emit(
            PaperEvent(
                event_id=str(event.id),
                client_order_id=str(event.client_order_id),
                event_type=type(event).__name__,
                status=order.status.name if order else "INITIALIZED",
                cumulative_filled_quantity=order.filled_qty.as_decimal() if order else Decimal(0),
                last_fill_quantity=fill.last_qty.as_decimal() if fill else None,
                last_fill_price=fill.last_px.as_decimal() if fill else None,
                trade_id=str(fill.trade_id) if fill else None,
                account_id=str(event.account_id) if hasattr(event, "account_id") else None,
                position_id=str(fill.position_id) if fill and fill.position_id else None,
                commission=fill.commission.as_decimal() if fill else None,
                currency=str(fill.commission.currency) if fill else None,
                timestamp_ns=event.ts_event,
            )
        )


class NativePaper:
    """All methods are owner-loop only; no native object crosses the facade."""

    def __init__(
        self,
        fixture: PaperFixture,
        emit: Callable[[PaperEvent], None],
        own_node: Callable[[TradingNode], None],
    ) -> None:
        self.fixture = fixture
        self.instrument = make_instrument(fixture.instrument)
        if not fixture.starting_balance.is_finite() or fixture.starting_balance <= 0:
            raise ValueError("invalid_fixture_cash")
        self.depth = fixture.initial_depth
        self.validate_depth(self.depth, 0)
        self.node = TradingNode(
            TradingNodeConfig(
                trader_id=TraderId("PAPER-001"),
                logging=LoggingConfig(log_level="ERROR", use_pyo3=False),
                exec_engine=LiveExecEngineConfig(reconciliation=False, inflight_check_interval_ms=0),
                exec_clients={
                    "SIM": SandboxExecutionClientConfig(
                        venue="SIM",
                        starting_balances=[f"{fixture.starting_balance} USDT"],
                        base_currency="USDT",
                        book_type="L2_MBP",
                    )
                },
                timeout_connection=1.0,
                timeout_reconciliation=1.0,
                timeout_portfolio=1.0,
                timeout_disconnection=1.0,
                timeout_post_stop=0.01,
                timeout_shutdown=1.0,
            ),
            loop=asyncio.get_running_loop(),
        )
        own_node(self.node)
        self.strategy = _PaperStrategy(emit)
        self.node.cache.add_instrument(self.instrument)
        self.node.trader.add_strategy(self.strategy)
        self.node.add_exec_client_factory("SIM", SandboxLiveExecClientFactory)
        self.node.build()
        self.seen: set[str] = set()

    def validate_depth(self, depth: PaperDepth, previous: int) -> None:
        if isinstance(depth.timestamp_ns, bool) or not isinstance(depth.timestamp_ns, int):
            raise TypeError("invalid_depth_timestamp")
        if depth.timestamp_ns <= previous:
            raise ValueError("nonmonotonic_depth")
        for value, increment in (
            (depth.bid, self.instrument.price_increment.as_decimal()),
            (depth.ask, self.instrument.price_increment.as_decimal()),
            (depth.bid_size, self.instrument.size_increment.as_decimal()),
            (depth.ask_size, self.instrument.size_increment.as_decimal()),
        ):
            if not value.is_finite() or value <= 0 or value % increment:
                raise ValueError("invalid_depth_increment")
        if depth.bid > depth.ask:
            raise ValueError("crossed_depth")

    def feed(self, depth: PaperDepth, *, initial: bool = False) -> None:
        self.validate_depth(depth, 0 if initial else self.depth.timestamp_ns)
        ts = depth.timestamp_ns
        deltas = [OrderBookDelta.clear(self.instrument.id, 0, ts, ts)]
        for side, price, size in (
            (OrderSide.BUY, depth.bid, depth.bid_size),
            (OrderSide.SELL, depth.ask, depth.ask_size),
        ):
            deltas.append(
                OrderBookDelta(
                    self.instrument.id,
                    BookAction.ADD,
                    BookOrder(side, self.instrument.make_price(price), self.instrument.make_qty(size), 0),
                    0,
                    0,
                    ts,
                    ts,
                )
            )
        # Native Sandbox subscription receives native data, including later updates.
        self.node.kernel.msgbus.publish(
            f"data.book.SIM.{self.instrument.id.symbol}",
            OrderBookDeltas(self.instrument.id, deltas),
        )
        self.node.kernel.data_engine.process(
            QuoteTick(
                self.instrument.id,
                self.instrument.make_price(depth.bid),
                self.instrument.make_price(depth.ask),
                self.instrument.make_qty(depth.bid_size),
                self.instrument.make_qty(depth.ask_size),
                ts,
                ts,
            )
        )
        self.depth = depth

    def submit(self, intent: PaperOrder) -> None:
        if not intent.client_order_id or len(intent.client_order_id) > 128:
            raise ValueError("invalid_client_order_id")
        if intent.client_order_id in self.seen:
            raise ValueError("duplicate_client_order_id")
        if intent.side not in ("BUY", "SELL"):
            raise ValueError("invalid_side")
        qty = intent.quantity
        spec = self.fixture.instrument
        if not qty.is_finite() or qty < spec.min_quantity or qty > spec.max_quantity or qty % spec.size_increment:
            raise ValueError("invalid_order_quantity")
        price = intent.limit_price
        if price is not None and (not price.is_finite() or price <= 0 or price % spec.price_increment):
            raise ValueError("invalid_order_price")
        if qty * (price if price is not None else self.depth.bid) < spec.min_notional:
            raise ValueError("invalid_order_notional")
        side = OrderSide.BUY if intent.side == "BUY" else OrderSide.SELL
        kwargs = {"client_order_id": ClientOrderId(intent.client_order_id)}
        if price is None:
            order = self.strategy.order_factory.market(
                self.instrument.id, side, self.instrument.make_qty(qty), **kwargs
            )
        else:
            order = self.strategy.order_factory.limit(
                self.instrument.id,
                side,
                self.instrument.make_qty(qty),
                self.instrument.make_price(price),
                **kwargs,
            )
        self.seen.add(intent.client_order_id)
        self.strategy.submit_order(order)

    def cancel(self, client_order_id: str) -> None:
        order = self.node.cache.order(ClientOrderId(client_order_id))
        if order is None:
            raise ValueError("unknown_client_order_id")
        self.strategy.cancel_order(order)

    def account(self) -> tuple[Decimal, Decimal, Decimal, tuple[str, ...]]:
        account = self.node.cache.account_for_venue(Venue("SIM"))
        if account is None:
            raise RuntimeError("missing_native_account")
        return (
            account.balance_total(USDT).as_decimal(),
            account.balance_free(USDT).as_decimal(),
            sum((p.signed_decimal_qty() for p in self.node.cache.positions_open()), Decimal(0)),
            tuple(str(o.client_order_id) for o in self.node.cache.orders_open()),
        )

    def pnl(self) -> tuple[Decimal, Decimal]:
        """Native fresh mark-to-liquidation PnL, not inferred spot cash movements."""
        account_id = AccountId("SIM-001")
        unrealized = self.node.portfolio.unrealized_pnl(self.instrument.id, account_id=account_id)
        realized = self.node.portfolio.realized_pnl(self.instrument.id, account_id=account_id)
        if unrealized is None or realized is None:
            raise RuntimeError("native_valuation_unavailable")
        return unrealized.as_decimal(), realized.as_decimal()
