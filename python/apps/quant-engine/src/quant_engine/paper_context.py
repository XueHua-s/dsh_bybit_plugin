"""Conservative valuation of explicit synthetic native state for the real risk evaluator."""

from decimal import Decimal

from quant_data.admission_contracts import SessionSnapshot
from quant_execution.paper_models import PaperSnapshot
from quant_risk.models import AccountSnapshot, Exposure, MarketSnapshot, OrderIntent, RiskContext

from .paper_config import PaperConfig


def risk_context(
    config: PaperConfig,
    durable: SessionSnapshot,
    native: PaperSnapshot,
    intent: OrderIntent,
    now_ms: int,
    consumed_bid: Decimal,
    consumed_ask: Decimal,
    peak_equity: Decimal,
) -> RiskContext:
    """Use durable positions/reservations, delivered fixture depth and native account truth.

    Every position is charged gross at the larger quote. Unknown native/durable position
    divergence is reconciled by the caller before this function can authorize submission.
    Finite depth is depleted cumulatively and is never refreshed by a request.
    """
    spec = config.fixture.instrument
    mark = max(native.bid, native.ask)
    durable_equity = durable.balance + sum(
        (
            item.quantity * ((native.bid if item.quantity > 0 else native.ask) - item.average_entry_price)
            for item in durable.positions
        ),
        Decimal(0),
    )
    equity = min(durable_equity, native.equity)
    positions = tuple(
        Exposure(f"position:{item.symbol}", item.symbol, abs(item.quantity) * mark, Decimal(1), Decimal(1), now_ms)
        for item in durable.positions
        if item.quantity
    )
    reservations = tuple(
        Exposure(
            item.command_id,
            item.symbol,
            item.remaining_quantity * max(item.price, mark),
            Decimal(1),
            Decimal(1),
            now_ms,
        )
        for item in durable.reservations
    )
    executable = native.ask if intent.side == "BUY" else native.bid
    depth = max(
        Decimal(0), (native.ask_size - consumed_ask) if intent.side == "BUY" else (native.bid_size - consumed_bid)
    )
    market = MarketSnapshot(
        spec.symbol,
        intent,
        native.market_timestamp_ns // 1_000_000,
        native.bid,
        native.ask,
        executable,
        depth * executable,
        Decimal(0),
        Decimal(1),
        spec.size_increment,
        spec.price_increment,
        spec.min_quantity,
        spec.max_quantity,
        spec.min_notional,
    )
    account = AccountSnapshot(
        native.account_id,
        "internal_paper",
        native.snapshot_timestamp_ns // 1_000_000,
        equity,
        min(durable_equity, native.available_equity),
        config.fixture.starting_balance,
        max(Decimal(0), config.fixture.starting_balance - equity),
        max(peak_equity, equity),
        True,
        True,
        not durable.protected,
    )
    return RiskContext(
        str(durable.generation),
        now_ms,
        now_ms,
        now_ms,
        (durable.last_admitted_at_ns or 0) // 1_000_000,
        account,
        market,
        positions,
        reservations,
        (),
        durable.protected,
    )
