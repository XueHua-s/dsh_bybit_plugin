from dataclasses import replace
from decimal import Decimal as D

import pytest
from quant_execution import InstrumentSpec, OrderIntent, Quote, run_simulation


@pytest.fixture
def instrument():
    return InstrumentSpec("ETHUSDT", "ETH", D("0.10"), D("0.001"), D("0.001"), D(100), D(5))


@pytest.fixture
def quotes():
    return tuple(Quote(D("2000.00"), D("2000.10"), D("100.000"), (i + 1) * 1_000_000_000) for i in range(3))


def test_native_market_fill_and_limit_cancel(instrument, quotes):
    result = run_simulation(
        instrument,
        quotes,
        (
            OrderIntent("market", "BUY", D("0.010")),
            OrderIntent("resting", "BUY", D("0.010"), D("1900.00")),
        ),
    )
    filled, canceled = result.orders
    assert filled.status == "FILLED"
    assert filled.filled_quantity == D("0.010")
    assert "OrderFilled" in filled.events
    assert "OrderAccepted" in canceled.events
    assert "OrderCanceled" in canceled.events
    assert canceled.status == "CANCELED"
    assert canceled.filled_quantity == 0
    assert len({o.client_order_id for o in result.orders}) == 2
    assert result.disposed and result.strategy_stopped and result.open_orders == 0


def test_duplicate_request_rejected_before_native_submission(instrument, quotes):
    intent = OrderIntent("duplicate", "BUY", D("0.010"))
    with pytest.raises(ValueError, match="duplicate"):
        run_simulation(instrument, quotes, (intent, intent))


@pytest.mark.parametrize("environment", ["mainnet", "testnet", "demo", "internal-paper", "", "BACKTEST"])
def test_environment_fence(instrument, quotes, environment):
    with pytest.raises(ValueError, match="offline"):
        run_simulation(instrument, quotes, (), environment=environment)


@pytest.mark.parametrize("quantity", ["0", "NaN", "Infinity", "0.0001", "100.001", "0.001"])
def test_size_and_notional_guards(instrument, quotes, quantity):
    with pytest.raises(ValueError):
        run_simulation(instrument, quotes, (OrderIntent("invalid", "BUY", D(quantity)),))


def test_limit_price_precision_guard(instrument, quotes):
    with pytest.raises(ValueError, match="price"):
        run_simulation(instrument, quotes, (OrderIntent("bad-price", "BUY", D("0.010"), D("1900.01")),))


def test_user_selected_fixture_symbol(instrument, quotes):
    btc = replace(instrument, symbol="BTCUSDT", base_currency="BTC")
    result = run_simulation(btc, quotes, (OrderIntent("btc", "BUY", D("0.010")),))
    assert result.orders[0].status == "FILLED"


def test_bad_fixture_fails_closed(instrument, quotes):
    with pytest.raises(ValueError, match="timestamp"):
        run_simulation(instrument, (quotes[0], quotes[0], quotes[2]), ())


def test_native_partial_fill_then_confirmed_cancel(instrument, quotes):
    limited = tuple(replace(q, size=D("0.004")) for q in quotes)
    result = run_simulation(instrument, limited, (OrderIntent("partial", "BUY", D("0.010"), D("2000.10")),))
    order = result.orders[0]
    assert order.status == "CANCELED"
    assert order.filled_quantity == D("0.004")
    assert order.fill_quantities == (D("0.004"),)
    assert order.events.index("OrderAccepted") < order.events.index("OrderFilled")
    assert order.events.index("OrderFilled") < order.events.index("OrderCanceled")
    assert result.open_orders == 0 and result.disposed


def test_native_client_ids_unique_across_runs(instrument, quotes):
    intent = OrderIntent("same-run-local-request", "BUY", D("0.010"))
    first = run_simulation(instrument, quotes, (intent,))
    second = run_simulation(instrument, quotes, (intent,))
    assert first.orders[0].client_order_id != second.orders[0].client_order_id


def test_cleanup_even_if_native_run_raises(instrument, quotes, monkeypatch):
    from quant_execution import simulation

    original = simulation.BacktestEngine
    instances = []

    class InterruptedEngine(original):
        def __init__(self, config):
            super().__init__(config)
            instances.append(self)

        def run(self):
            raise RuntimeError("controlled run failure")

    monkeypatch.setattr(simulation, "BacktestEngine", InterruptedEngine)
    with pytest.raises(RuntimeError, match="controlled run failure"):
        run_simulation(instrument, quotes, (OrderIntent("cleanup", "BUY", D("0.010")),))
    assert len(instances) == 1
    assert instances[0].trader.is_disposed


def test_nonstationary_single_snapshot_fixture_rejected(instrument, quotes):
    changed = (quotes[0], replace(quotes[1], ask=D("2000.20")), quotes[2])
    with pytest.raises(ValueError, match="stationary"):
        run_simulation(instrument, changed, ())
