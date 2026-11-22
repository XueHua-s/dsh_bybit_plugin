from datetime import UTC, datetime, timedelta

import pytest
from quant_strategies import Bar, MarketSnapshot
from quant_strategies.alpha158 import QLIB_SOURCE, factors


def test_alpha158_subset_is_reproducible_and_normalized() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    market = MarketSnapshot(
        tuple(Bar(start + timedelta(days=i), 10 + i, 11 + i, 9 + i, 10 + i, 100 + i) for i in range(8))
    )
    result = factors(market, 5)
    assert result == factors(market, 5)
    assert QLIB_SOURCE.endswith("54355232463878d2eebb91fe0ee5fa7fa1f5976c")
    assert [name for name, _ in result or ()] == ["ROC5", "MA5", "STD5", "RSV5", "SUMP5"]
    values = dict(result or ())
    assert values["ROC5"] == 12 / 17
    assert values["MA5"] < 1
    assert values["STD5"] > 0
    assert 0 <= values["RSV5"] <= 1
    assert values["SUMP5"] == pytest.approx(1.0)
