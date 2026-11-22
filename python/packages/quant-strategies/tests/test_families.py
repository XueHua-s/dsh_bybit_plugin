from datetime import UTC, datetime, timedelta

import pytest
from quant_strategies import STRATEGIES, Bar, MarketSnapshot, evaluate
from quant_strategies.families import STRATEGY_METADATA


def snapshot(count: int = 80, funding_rate: float | None = None) -> MarketSnapshot:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(
        Bar(start + timedelta(minutes=index), 100 + index, 101 + index, 99 + index, 100 + index, 10)
        for index in range(count)
    )
    return MarketSnapshot(bars, funding_rate)


def test_catalog_has_metadata_and_all_outputs_are_bounded() -> None:
    market = snapshot(funding_rate=0.0005)
    assert tuple(item.strategy_id for item in STRATEGY_METADATA) == STRATEGIES
    for strategy_id in STRATEGIES:
        signal = evaluate(strategy_id, market)
        assert signal.strategy_id == strategy_id
        assert -1 <= signal.target_exposure <= 1
        assert signal.ready


def test_warmup_is_explicit_and_has_no_exposure() -> None:
    signal = evaluate("ema_cross", snapshot(5))
    assert signal.ready is False
    assert signal.target_exposure == 0


@pytest.mark.parametrize("strategy_id", STRATEGIES)
def test_unknown_config_and_nonfinite_values_fail_closed(strategy_id: str) -> None:
    with pytest.raises(ValueError, match="invalid_strategy_config"):
        evaluate(strategy_id, snapshot(), {"unexpected": 1})
    with pytest.raises(ValueError, match="invalid_strategy_config"):
        evaluate(strategy_id, snapshot(), {"max_exposure": float("nan")})


def test_funding_strategy_needs_funding_evidence() -> None:
    signal = evaluate("funding_carry", snapshot())
    assert signal.ready is False
    assert signal.target_exposure == 0


def test_funding_direction_and_exposure_cap_are_explicit() -> None:
    assert evaluate("funding_carry", snapshot(funding_rate=0.0005)).target_exposure == -1
    assert evaluate("funding_carry", snapshot(funding_rate=-0.0005)).target_exposure == 1
    assert evaluate("ema_cross", snapshot(), {"max_exposure": 0.25}).target_exposure == 0.25


def test_snapshot_rejects_unordered_or_invalid_bars() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bar = Bar(start, 1, 2, 1, 2, 0)
    with pytest.raises(ValueError, match="unordered_market_snapshot"):
        MarketSnapshot((bar, bar))
    with pytest.raises(ValueError, match="invalid_bar_ohlc"):
        Bar(start, 3, 2, 1, 2, 1)
