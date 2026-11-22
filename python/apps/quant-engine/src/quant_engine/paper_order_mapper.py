"""Map a portfolio exposure delta to one bounded synthetic order intent."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from quant_execution.models import InstrumentSpec
from quant_execution.paper_models import PaperDepth
from quant_risk.models import OrderIntent


@dataclass(frozen=True, slots=True)
class MappedOrder:
    """Order intent plus the trusted synthetic quote used to derive it."""

    intent: OrderIntent
    notional: Decimal
    executable_price: Decimal


def map_exposure_delta(
    *,
    request_id: str,
    symbol: str,
    delta_exposure: Decimal,
    equity: Decimal,
    instrument: InstrumentSpec,
    depth: PaperDepth,
    now_ns: int,
    max_age_ns: int,
) -> MappedOrder | None:
    """Create a limit intent from trusted fixture state, or return ``None`` for no-op.

    Prices and depth are exclusively supplied by the injected fixture.  Quantity is
    rounded down to the instrument step and checked against minimums, finite depth,
    and available equity before an intent is returned.
    """

    if type(delta_exposure) is not Decimal or type(equity) is not Decimal:
        raise ValueError("decimal_mapper_inputs_required")
    if not delta_exposure or equity <= 0 or now_ns <= 0 or max_age_ns <= 0:
        return None
    if depth.timestamp_ns <= 0 or now_ns < depth.timestamp_ns or now_ns - depth.timestamp_ns > max_age_ns:
        raise ValueError("stale_fixture_quote")
    if depth.bid <= 0 or depth.ask <= 0 or depth.bid > depth.ask:
        raise ValueError("invalid_fixture_quote")
    side = "BUY" if delta_exposure > 0 else "SELL"
    price = depth.ask if side == "BUY" else depth.bid
    available_size = depth.ask_size if side == "BUY" else depth.bid_size
    raw_quantity = (abs(delta_exposure) * equity) / price
    units = (raw_quantity / instrument.size_increment).to_integral_value(rounding=ROUND_DOWN)
    quantity = units * instrument.size_increment
    if quantity < instrument.min_quantity or quantity > instrument.max_quantity or quantity > available_size:
        return None
    notional = quantity * price
    if notional < instrument.min_notional or notional > equity:
        return None
    return MappedOrder(OrderIntent(request_id, symbol, side, quantity, price, Decimal(1)), notional, price)
