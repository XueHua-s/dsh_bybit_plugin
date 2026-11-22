from decimal import Decimal

import pytest
from quant_engine.paper_order_mapper import map_exposure_delta
from quant_execution.models import InstrumentSpec
from quant_execution.paper_models import PaperDepth


def _spec() -> InstrumentSpec:
    return InstrumentSpec("ALPHA", "AAA", Decimal("0.1"), Decimal("0.01"), Decimal("0.01"), Decimal(100), Decimal(1))


def _depth(stamp: int = 100) -> PaperDepth:
    return PaperDepth(Decimal(10), Decimal("10.1"), Decimal(10), Decimal(10), stamp)


def test_mapper_uses_side_quote_and_rounds_down() -> None:
    mapped = map_exposure_delta(
        request_id="req-1",
        symbol="ALPHA",
        delta_exposure=Decimal("0.251"),
        equity=Decimal(100),
        instrument=_spec(),
        depth=_depth(),
        now_ns=101,
        max_age_ns=10,
    )
    assert mapped is not None
    assert mapped.intent.side == "BUY"
    assert mapped.intent.quantity == Decimal("2.48")
    assert mapped.intent.price_limit == Decimal("10.1")


def test_mapper_rejects_stale_or_insufficient_depth() -> None:
    with pytest.raises(ValueError, match="stale_fixture_quote"):
        map_exposure_delta(
            request_id="req-1",
            symbol="ALPHA",
            delta_exposure=Decimal("0.2"),
            equity=Decimal(100),
            instrument=_spec(),
            depth=_depth(1),
            now_ns=100,
            max_age_ns=10,
        )
    assert (
        map_exposure_delta(
            request_id="req-1",
            symbol="ALPHA",
            delta_exposure=Decimal("0.9"),
            equity=Decimal(100),
            instrument=_spec(),
            depth=PaperDepth(Decimal(10), Decimal("10.1"), Decimal(5), Decimal(5), 100),
            now_ns=101,
            max_age_ns=10,
        )
        is None
    )
