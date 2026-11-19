"""Ticker schema validation, independent of transport lifecycle."""

import json

import pytest
from quant_engine.market_data import BybitMarketDataAdapter


def _frame(data: dict[str, object]) -> str:
    return json.dumps({"topic": "tickers.BTCUSDT", "ts": 1730000000000, "data": data})


@pytest.mark.parametrize("symbol", ["ETHUSDT", "btcusdt", "", True, 123, None])
def test_payload_symbol_must_match_topic(symbol: object) -> None:
    assert BybitMarketDataAdapter._parse(_frame({"symbol": symbol, "lastPrice": "100"})) is None


@pytest.mark.parametrize("key", ["lastPrice", "bid1Price", "ask1Price"])
@pytest.mark.parametrize("price", [True, False, 0, -3, "0", "-3", "nan", "inf", {}, [], None])
def test_supplied_prices_must_be_positive_finite_numbers(key: str, price: object) -> None:
    assert BybitMarketDataAdapter._parse(_frame({"symbol": "BTCUSDT", key: price})) is None


@pytest.mark.parametrize(
    "data",
    [
        {"symbol": "BTCUSDT", "lastPrice": "100"},
        {"bid1Price": "99"},
        {"symbol": "BTCUSDT", "ask1Price": 101},
        {"symbol": "BTCUSDT"},
    ],
)
def test_partial_delta_fields_keep_valid_topic_identity(data: dict[str, object]) -> None:
    event = BybitMarketDataAdapter._parse(_frame(data))
    assert event is not None
    assert event.symbol == "BTCUSDT"
    assert event.last_price == (100.0 if "lastPrice" in data else None)
    assert event.bid_price == (99.0 if "bid1Price" in data else None)
    assert event.ask_price == (101.0 if "ask1Price" in data else None)


@pytest.mark.parametrize(
    "timestamp", [10**400, 253402300800000, 253402300800000.0, float("inf"), float("nan"), 0, -1, True, 1.5]
)
def test_untrusted_timestamps_are_bounded_integral_epoch_milliseconds(timestamp: object) -> None:
    frame = json.loads(_frame({"lastPrice": "100"}))
    frame["ts"] = timestamp
    assert BybitMarketDataAdapter._parse(json.dumps(frame)) is None


@pytest.mark.parametrize("timestamp", [1, 1730000000000, 1730000000000.0, 253402300799999])
def test_timestamp_schema_bound_is_deterministic_without_wall_clock_dependency(timestamp: float) -> None:
    frame = json.loads(_frame({"lastPrice": "100"}))
    frame["ts"] = timestamp
    event = BybitMarketDataAdapter._parse(json.dumps(frame))
    assert event is not None
    assert event.event_time_ms == int(timestamp)
