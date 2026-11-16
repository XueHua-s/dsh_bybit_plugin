from quant_engine import EngineRuntime


def test_runtime_starts_and_stops_cleanly() -> None:
    runtime = EngineRuntime()
    assert runtime.snapshot().running is False
    started = runtime.start()
    assert started.running is True
    assert started.started_at is not None
    stopped = runtime.stop()
    assert stopped.running is False
    assert stopped.stopped_at is not None


def test_runtime_clamps_queue_and_counts_reconnects() -> None:
    runtime = EngineRuntime()
    runtime.set_queue_depth(-3)
    runtime.record_reconnect()
    runtime.record_reconnect()
    snapshot = runtime.snapshot()
    assert snapshot.queue_depth == 0
    assert snapshot.reconnects == 2
