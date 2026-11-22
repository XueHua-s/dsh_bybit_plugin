from decimal import Decimal as D
from time import sleep, time_ns

import pytest
from quant_execution.models import InstrumentSpec
from quant_execution.paper_models import PaperDepth, PaperFixture, PaperOrder
from quant_execution.paper_runtime import PaperRuntime


def fixture():
    return PaperFixture(
        InstrumentSpec("ETHUSDT", "ETH", D("0.10"), D("0.001"), D("0.001"), D(100), D(5)),
        PaperDepth(D("2000.00"), D("2000.10"), D("0.010"), D("0.010"), time_ns()),
        D(1000000),
    )


def test_multi_instrument_runtime_routes_orders_and_positions_by_symbol():
    alpha = PaperFixture(
        InstrumentSpec("ALPHA-PERP", "ALPHA", D("0.1"), D("0.01"), D("0.01"), D(100), D(1)),
        PaperDepth(D("10.0"), D("10.1"), D("1.00"), D("1.00"), time_ns(), "ALPHA-PERP"),
        D(100000),
    )
    beta = PaperFixture(
        InstrumentSpec("BETA.PERP", "BETA", D("0.01"), D("0.001"), D("0.001"), D(100), D(1)),
        PaperDepth(D("20.00"), D("20.01"), D("2.000"), D("2.000"), time_ns(), "BETA.PERP"),
        D(100000),
    )
    runtime = PaperRuntime((alpha, beta))
    try:
        started = runtime.start()
        assert {item.symbol for item in started.instruments} == {"ALPHA-PERP", "BETA.PERP"}
        runtime.submit(PaperOrder("alpha-order", "BUY", D("0.50"), D("10.1"), "ALPHA-PERP"))
        runtime.submit(PaperOrder("beta-order", "SELL", D("0.250"), D("20.00"), "BETA.PERP"))
        snapshot = runtime.snapshot()
        by_symbol = {item.symbol: item for item in snapshot.instruments}
        assert by_symbol["ALPHA-PERP"].position_quantity == D("0.50")
        assert by_symbol["BETA.PERP"].position_quantity == D("-0.250")
        assert {event.client_order_id for event in runtime.read_events() if event.status == "FILLED"} == {
            "alpha-order",
            "beta-order",
        }
        with pytest.raises(ValueError, match="unknown_order_symbol"):
            runtime.submit(PaperOrder("unknown", "BUY", D("0.1"), D("10.1"), "GAMMA_1"))
    finally:
        assert runtime.stop().status == "stopped"


def test_real_native_continuous_session():
    runtime = PaperRuntime(fixture())
    try:
        first = runtime.start()
        runtime.submit(PaperOrder("ledger-one", "BUY", D("0.006"), D("2000.10")))
        sleep(0.05)
        filled = runtime.read_events()
        assert any(e.status == "FILLED" and e.client_order_id == "ledger-one" for e in filled)
        assert any(e.event_type == "OrderAccepted" for e in filled)
        snapshot = runtime.snapshot()
        assert snapshot.position_quantity == D("0.006")
        assert snapshot.balance_total < first.balance_total
        runtime.submit(PaperOrder("ledger-two", "BUY", D("0.008"), D("2000.10")))
        sleep(0.05)
        partial = runtime.read_events()
        assert sum((e.last_fill_quantity or D(0) for e in partial), D(0)) == D("0.004")
        assert partial[-1].status == "PARTIALLY_FILLED"
        assert runtime.snapshot().position_quantity == D("0.010")
        runtime.feed(PaperDepth(D("1999.90"), D("2000.00"), D("0.010"), D("0.010"), time_ns()))
        sleep(0.05)
        later = runtime.read_events()
        assert any(e.status == "FILLED" and e.client_order_id == "ledger-two" for e in later)
        assert runtime.snapshot().node_instance_id == first.node_instance_id
        assert runtime.snapshot().position_quantity == D("0.014")
        runtime.submit(PaperOrder("ledger-rest", "BUY", D("0.006"), D("1900.00")))
        sleep(0.05)
        assert "ledger-rest" in runtime.snapshot().open_order_ids
        runtime.cancel("ledger-rest")
        sleep(0.05)
        assert any(e.status == "CANCELED" for e in runtime.read_events())
        with pytest.raises(ValueError, match="duplicate"):
            runtime.submit(PaperOrder("ledger-one", "BUY", D("0.006"), D("2000.10")))
    finally:
        stopped = runtime.stop()
    assert stopped.status == "stopped"
    assert not stopped.process_alive and stopped.loop_closed


def test_stop_retains_undrained_native_events():
    runtime = PaperRuntime(fixture())
    runtime.start()
    runtime.submit(PaperOrder("retain", "BUY", D("0.006"), D("2000.10")))
    stopped = runtime.stop()
    assert stopped.status == "stopped"
    events = runtime.read_events()
    assert any(e.status == "FILLED" and e.client_order_id == "retain" for e in events)
    assert runtime.read_events() == ()


def test_overflow_protects_and_cannot_claim_complete_stop():
    runtime = PaperRuntime(fixture(), event_capacity=1)
    runtime.start()
    runtime.submit(PaperOrder("overflow", "BUY", D("0.006"), D("2000.10")))
    snapshot = runtime.snapshot()
    assert snapshot.status == "protected"
    assert not snapshot.event_stream_complete
    assert snapshot.failure_reason == "native_event_queue_full"
    with pytest.raises(RuntimeError, match="protected"):
        runtime.submit(PaperOrder("blocked", "BUY", D("0.006"), D("2000.10")))
    stopped = runtime.stop()
    assert stopped.status == "failed" and stopped.loop_closed
    assert not stopped.process_alive


def test_invalid_fixture_and_unexpected_worker_death_are_reaped():
    from dataclasses import replace

    bad = PaperRuntime(replace(fixture(), starting_balance=D(-1)))
    with pytest.raises(RuntimeError):
        bad.start()
    assert bad.stop().status == "failed"
    assert not bad.snapshot().process_alive
    runtime = PaperRuntime(fixture())
    runtime.start()
    runtime._process.kill()
    runtime._process.join(2)
    with pytest.raises(RuntimeError):
        runtime.snapshot()
    stopped = runtime.stop()
    assert stopped.status == "failed" and not stopped.process_alive
    assert not stopped.loop_closed


def test_explicit_protect_rejects_later_submit_and_stop_is_idempotent():
    runtime = PaperRuntime(fixture())
    runtime.start()
    runtime.protect()
    with pytest.raises(RuntimeError, match="protected"):
        runtime.submit(PaperOrder("blocked", "BUY", D("0.006"), D("2000.10")))
    assert runtime.stop().status == "stopped"
    assert runtime.stop().status == "stopped"


def test_native_market_fill_and_fixture_precision_normalization():
    from dataclasses import replace

    config = fixture()
    config = replace(config, initial_depth=replace(config.initial_depth, bid=D("1999.9"), ask=D(2000)))
    runtime = PaperRuntime(config)
    try:
        runtime.start()
        runtime.submit(PaperOrder("market-exact-id", "BUY", D("0.006")))
        events = runtime.read_events()
        fills = [e for e in events if e.last_fill_quantity is not None]
        assert len(fills) == 1
        fill = fills[0]
        assert fill.client_order_id == "market-exact-id"
        assert fill.event_id and fill.trade_id and fill.position_id
        assert fill.cumulative_filled_quantity == D("0.006")
        assert fill.last_fill_price == D(2000)
        assert fill.commission is not None and fill.commission > 0
        assert fill.currency == "USDT" and fill.account_id == "SIM-001"
    finally:
        assert runtime.stop().status == "stopped"


def test_forced_deadline_never_claims_clean_loop_or_complete_events():
    import os
    import signal
    from time import monotonic

    runtime = PaperRuntime(fixture())
    runtime.start()
    assert runtime._process.pid is not None
    os.kill(runtime._process.pid, signal.SIGSTOP)
    runtime._timeout = 0.1
    before = monotonic()
    stopped = runtime.stop()
    assert monotonic() - before < 2
    assert stopped.status == "failed" and not stopped.process_alive
    assert not stopped.loop_closed and not stopped.event_stream_complete
    assert stopped.failure_reason == "native_response_timeout_or_worker_lost"


def test_invalid_depth_and_order_leave_native_session_unchanged():
    from dataclasses import replace

    runtime = PaperRuntime(fixture())
    try:
        initial = runtime.start()
        with pytest.raises(ValueError, match="invalid_order"):
            runtime.submit(PaperOrder("invalid", "BUY", D("0.0001"), D("2000.10")))
        with pytest.raises(ValueError, match="nonmonotonic"):
            runtime.feed(replace(fixture().initial_depth, timestamp_ns=initial.market_timestamp_ns))
        assert runtime.read_events() == ()
        assert runtime.snapshot().position_quantity == 0
        assert runtime.snapshot().balance_total == initial.balance_total
    finally:
        assert runtime.stop().status == "stopped"


def test_native_derivative_valuation_not_spot_notional_cash():
    runtime = PaperRuntime(fixture())
    try:
        initial = runtime.start()
        runtime.submit(PaperOrder("long", "BUY", D("0.006"), D("2000.10")))
        filled = runtime.read_events()
        fee = sum((e.commission or D(0) for e in filled), D(0))
        opened = runtime.snapshot()
        assert opened.balance_total == initial.balance_total - fee
        assert opened.realized_pnl == -fee
        assert opened.unrealized_pnl == D("-0.00060000")
        assert opened.equity == opened.balance_total + opened.unrealized_pnl
        assert opened.balance_free < opened.balance_total
        assert opened.available_equity == opened.balance_free + opened.unrealized_pnl
        runtime.feed(PaperDepth(D("2100.00"), D("2100.10"), D("0.020"), D("0.020"), time_ns()))
        marked = runtime.snapshot()
        assert marked.unrealized_pnl == D("0.59940000")
        assert marked.equity == marked.balance_total + marked.unrealized_pnl
        assert marked.available_equity == marked.balance_free
        assert marked.snapshot_timestamp_ns >= marked.market_timestamp_ns
        runtime.submit(PaperOrder("close", "SELL", D("0.006"), D("2100.00")))
        closed = runtime.snapshot()
        assert closed.position_quantity == 0
        assert closed.unrealized_pnl == 0
        assert closed.realized_pnl > 0
        assert closed.balance_total == initial.balance_total + closed.realized_pnl
        runtime.submit(PaperOrder("short", "SELL", D("0.004"), D("2100.00")))
        runtime.feed(PaperDepth(D("2200.00"), D("2200.10"), D("0.020"), D("0.020"), time_ns()))
        short = runtime.snapshot()
        assert short.position_quantity == D("-0.004")
        assert short.unrealized_pnl == D("-0.40040000")
        assert short.equity == short.balance_total + short.unrealized_pnl
        assert short.available_equity == short.balance_free + short.unrealized_pnl
    finally:
        assert runtime.stop().status == "stopped"


@pytest.mark.parametrize("block_native", [False, True])
def test_service_sigkill_does_not_orphan_native_worker(tmp_path, block_native):
    import os
    import subprocess
    import sys
    from time import monotonic

    script = tmp_path / "paper_owner.py"
    pid_file = tmp_path / "native.pid"
    script.write_text("""
from decimal import Decimal as D
from pathlib import Path
from time import sleep, time_ns
import sys
from quant_execution.models import InstrumentSpec
from quant_execution.paper_models import PaperFixture, PaperDepth, PaperOrder
from quant_execution.paper_runtime import PaperRuntime
from quant_execution.paper_native import NativePaper
original_account = NativePaper.account
calls = 0
def account(self):
    global calls
    calls += 1
    if sys.argv[2] == "block" and calls >= 2:
        Path(sys.argv[1] + ".blocked").write_text("blocked")
        sleep(60)
    return original_account(self)
NativePaper.account = account
if __name__ == "__main__":
    spec = InstrumentSpec("ETHUSDT", "ETH", D("0.10"), D("0.001"), D("0.001"), D(100), D(5))
    fixture = PaperFixture(spec, PaperDepth(D(2000), D("2000.1"), D("0.01"), D("0.01"), time_ns()), D(10000))
    runtime = PaperRuntime(fixture)
    state = runtime.start()
    Path(sys.argv[1]).write_text(str(state.process_id))
    runtime.submit(PaperOrder("before-parent-crash", "BUY", D("0.006"), D("2000.1")))
    sleep(60)
""")
    service = subprocess.Popen([sys.executable, str(script), str(pid_file), "block" if block_native else "normal"])
    child_pid = None
    try:
        deadline = monotonic() + 10
        while not pid_file.exists() and monotonic() < deadline and service.poll() is None:
            sleep(0.02)
        assert pid_file.exists()
        child_pid = int(pid_file.read_text())
        if block_native:
            blocked_file = pid_file.with_name(pid_file.name + ".blocked")
            while not blocked_file.exists() and monotonic() < deadline:
                sleep(0.02)
            assert blocked_file.exists()
        else:
            sleep(0.1)
        service.kill()
        service.wait(2)
        deadline = monotonic() + 5
        while monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            sleep(0.05)
        else:
            pytest.fail("native child survived killed service owner")
    finally:
        if service.poll() is None:
            service.kill()
            service.wait(2)
        if child_pid is not None:
            try:
                os.kill(child_pid, 9)
            except ProcessLookupError:
                pass
