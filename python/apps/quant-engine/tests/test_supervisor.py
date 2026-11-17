import asyncio
from collections.abc import Sequence

import pytest
from quant_engine import EngineSupervisor
from quant_engine.market_data import MarketDataHealth
from quant_engine.runtime import RuntimeSnapshot


class FakeRuntime:
    def __init__(self) -> None:
        self.running = False
        self.stop_calls = 0

    def start(self) -> RuntimeSnapshot:
        self.running = True
        return self.snapshot()

    def stop(self) -> RuntimeSnapshot:
        self.running = False
        self.stop_calls += 1
        return self.snapshot()

    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(self.running, None, None, 0, 0, 2, False, None)


class FakeAdapter:
    def __init__(self) -> None:
        self.state = "idle"
        self.start_calls = 0
        self.close_calls = 0

    async def start(self, symbols: Sequence[str]) -> None:
        assert symbols == ("BTCUSDT",)
        self.start_calls += 1
        self.state = "connected"

    async def close(self) -> None:
        self.close_calls += 1
        self.state = "closed"

    def health(self) -> MarketDataHealth:
        return MarketDataHealth(self.state, 0, 0, 0, 0, 0, None)


class BlockingAdapter(FakeAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.close_started = asyncio.Event()
        self.release_close = asyncio.Event()

    async def close(self) -> None:
        self.close_started.set()
        await self.release_close.wait()
        await super().close()


def test_restarts_once_after_worker_stops() -> None:
    created: list[tuple[FakeAdapter, FakeRuntime]] = []

    def factory() -> tuple[FakeAdapter, FakeRuntime]:
        pair = (FakeAdapter(), FakeRuntime())
        created.append(pair)
        return pair

    supervisor = EngineSupervisor(symbols=("btcusdt",), factory=factory, max_restarts=1, poll_interval=0.001)

    async def scenario() -> None:
        await supervisor.start()
        created[0][0].state = "stopped"
        await asyncio.sleep(0.01)
        snapshot = supervisor.snapshot()
        assert snapshot.state == "running"
        assert snapshot.restart_count == 1
        assert len(created) == 2
        await supervisor.close()
        assert supervisor.snapshot().state == "stopped"

    asyncio.run(scenario())


def test_restart_budget_exhaustion_is_failed() -> None:
    created: list[tuple[FakeAdapter, FakeRuntime]] = []

    def factory() -> tuple[FakeAdapter, FakeRuntime]:
        pair = (FakeAdapter(), FakeRuntime())
        created.append(pair)
        return pair

    supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=factory, max_restarts=0, poll_interval=0.001)

    async def scenario() -> None:
        await supervisor.start()
        created[0][0].state = "failed"
        await asyncio.sleep(0.01)
        snapshot = supervisor.snapshot()
        assert snapshot.state == "failed"
        assert snapshot.restart_count == 0
        assert snapshot.last_error == "market-data worker state: failed"
        assert created[0][0].close_calls == 1
        assert created[0][1].stop_calls == 1
        await supervisor.close()

    asyncio.run(scenario())


def test_close_racing_restart_waits_for_cancellation_safe_cleanup() -> None:
    adapter = BlockingAdapter()
    runtime = FakeRuntime()
    supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=lambda: (adapter, runtime), poll_interval=0.001)

    async def scenario() -> None:
        await supervisor.start()
        adapter.state = "failed"
        await adapter.close_started.wait()
        close_task = asyncio.create_task(supervisor.close())
        await asyncio.sleep(0)
        adapter.release_close.set()
        snapshot = await close_task
        assert snapshot.state == "stopped"
        assert adapter.close_calls == 1
        assert runtime.stop_calls == 1
        assert supervisor.snapshot().runtime is None

    asyncio.run(scenario())


def test_unexpected_restart_factory_error_is_terminal() -> None:
    adapter = FakeAdapter()
    runtime = FakeRuntime()
    calls = 0

    def factory() -> tuple[FakeAdapter, FakeRuntime]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return adapter, runtime
        raise LookupError("factory broke")

    supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=factory, max_restarts=1, poll_interval=0.001)

    async def scenario() -> None:
        await supervisor.start()
        adapter.state = "failed"
        await asyncio.sleep(0.01)
        snapshot = supervisor.snapshot()
        assert snapshot.state == "failed"
        assert snapshot.last_error == "restart failed: LookupError"
        assert adapter.close_calls == 1
        assert runtime.stop_calls == 1
        await supervisor.close()

    asyncio.run(scenario())


def test_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        EngineSupervisor(symbols=())
    with pytest.raises(ValueError):
        EngineSupervisor(symbols=("BTCUSDT",), max_restarts=-1)
    with pytest.raises(ValueError):
        EngineSupervisor(symbols=("BTCUSDT",), poll_interval=0)


class BlockingStartAdapter(FakeAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.start_entered = asyncio.Event()
        self.release_start = asyncio.Event()

    async def start(self, symbols: Sequence[str]) -> None:
        self.start_entered.set()
        await self.release_start.wait()
        await super().start(symbols)


def test_close_wins_against_in_flight_and_queued_starts() -> None:
    async def scenario() -> None:
        adapter = BlockingStartAdapter()
        runtime = FakeRuntime()
        created = 0

        def factory() -> tuple[FakeAdapter, FakeRuntime]:
            nonlocal created
            created += 1
            return adapter, runtime

        supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=factory)
        start_task = asyncio.create_task(supervisor.start())
        await adapter.start_entered.wait()
        queued_start = asyncio.create_task(supervisor.start())
        await asyncio.sleep(0)
        close_task = asyncio.create_task(supervisor.close())
        await asyncio.sleep(0)
        late_start = asyncio.create_task(supervisor.start())
        await asyncio.sleep(0)
        assert not close_task.done()
        adapter.release_start.set()
        results = await asyncio.gather(start_task, queued_start, late_start, close_task)
        assert all(result.state == "stopped" for result in results)
        assert created == 1
        assert adapter.start_calls == 1
        assert adapter.close_calls == runtime.stop_calls == 1
        assert not runtime.running
        assert supervisor.snapshot().runtime is None
        assert supervisor.snapshot().market_data is None
        assert not [task for task in asyncio.all_tasks() if task.get_name() == "quant-engine-supervisor"]

    asyncio.run(scenario())


def test_concurrent_starts_share_one_worker_and_monitor() -> None:
    async def scenario() -> None:
        adapter = BlockingStartAdapter()
        runtime = FakeRuntime()
        created = 0

        def factory() -> tuple[FakeAdapter, FakeRuntime]:
            nonlocal created
            created += 1
            return adapter, runtime

        supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=factory)
        first = asyncio.create_task(supervisor.start())
        await adapter.start_entered.wait()
        second = asyncio.create_task(supervisor.start())
        await asyncio.sleep(0)
        assert not second.done()
        adapter.release_start.set()
        results = await asyncio.gather(first, second)
        assert all(result.state == "running" for result in results)
        assert created == adapter.start_calls == 1
        assert len([task for task in asyncio.all_tasks() if task.get_name() == "quant-engine-supervisor"]) == 1
        await supervisor.close()
        assert adapter.close_calls == runtime.stop_calls == 1

    asyncio.run(scenario())


def test_explicit_start_after_completed_close_can_reopen() -> None:
    async def scenario() -> None:
        adapter = FakeAdapter()
        runtime = FakeRuntime()
        supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=lambda: (adapter, runtime))
        await supervisor.start()
        await supervisor.close()
        assert (await supervisor.start()).state == "running"
        assert adapter.start_calls == 2
        await supervisor.close()
        assert adapter.close_calls == runtime.stop_calls == 2

    asyncio.run(scenario())


def test_cancelled_close_waits_for_cleanup() -> None:
    async def scenario() -> None:
        adapter = BlockingAdapter()
        runtime = FakeRuntime()
        supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=lambda: (adapter, runtime))
        await supervisor.start()
        close_task = asyncio.create_task(supervisor.close())
        await adapter.close_started.wait()
        close_task.cancel()
        await asyncio.sleep(0)
        assert not close_task.done()
        adapter.release_close.set()
        with pytest.raises(asyncio.CancelledError):
            await close_task
        assert supervisor.snapshot().state == "stopped"
        assert adapter.close_calls == runtime.stop_calls == 1

    asyncio.run(scenario())


def test_failed_initial_start_reports_terminal_error() -> None:
    def factory() -> tuple[FakeAdapter, FakeRuntime]:
        raise LookupError("factory broke")

    async def scenario() -> None:
        supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=factory)
        with pytest.raises(LookupError):
            await supervisor.start()
        snapshot = supervisor.snapshot()
        assert snapshot.state == "failed"
        assert snapshot.last_error == "start failed: LookupError"
        assert snapshot.runtime is None

    asyncio.run(scenario())


@pytest.mark.parametrize("during_restart", [False, True])
def test_cleanup_failure_reports_failed_state(during_restart: bool) -> None:
    class FailingCloseAdapter(FakeAdapter):
        async def close(self) -> None:
            await super().close()
            raise OSError("close failed")

    async def scenario() -> None:
        adapter = FailingCloseAdapter()
        runtime = FakeRuntime()
        supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=lambda: (adapter, runtime), poll_interval=0.001)
        await supervisor.start()
        if during_restart:
            adapter.state = "failed"
            monitor = supervisor._monitor
            assert monitor is not None
            await asyncio.wait_for(monitor, timeout=1)
            assert supervisor.snapshot().last_error == "restart failed: OSError"
        else:
            with pytest.raises(OSError):
                await supervisor.close()
            assert supervisor.snapshot().last_error == "close failed: OSError"
        assert supervisor.snapshot().state == "failed"
        assert supervisor.snapshot().runtime is None
        assert adapter.close_calls == runtime.stop_calls == 1
        await supervisor.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("failure_source", ["sleeper", "health"])
def test_monitor_exception_closes_worker_and_reports_terminal_failure(failure_source: str) -> None:
    async def scenario() -> None:
        poll_entered = asyncio.Event()
        release_poll = asyncio.Event()

        async def poll(_: float) -> None:
            poll_entered.set()
            await release_poll.wait()
            if failure_source == "sleeper":
                raise OSError("private details must not appear in status")

        class FailingHealthAdapter(FakeAdapter):
            def health(self) -> MarketDataHealth:
                if failure_source == "health" and release_poll.is_set():
                    raise OSError("private details must not appear in status")
                return super().health()

        adapter = FailingHealthAdapter()
        runtime = FakeRuntime()
        supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=lambda: (adapter, runtime), sleeper=poll)
        await supervisor.start()
        await poll_entered.wait()
        release_poll.set()
        monitor = supervisor._monitor
        assert monitor is not None
        await asyncio.wait_for(monitor, timeout=1)
        snapshot = supervisor.snapshot()
        assert snapshot.state == "failed"
        assert snapshot.last_error == "monitor failed: OSError"
        assert snapshot.market_data is None
        assert snapshot.runtime is None
        assert adapter.close_calls == runtime.stop_calls == 1
        assert not runtime.running
        await supervisor.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("during_restart", [False, True])
def test_repeated_cancellation_cannot_interrupt_worker_cleanup(during_restart: bool) -> None:
    async def scenario() -> None:
        adapter = BlockingAdapter()
        runtime = FakeRuntime()
        supervisor = EngineSupervisor(symbols=("BTCUSDT",), factory=lambda: (adapter, runtime), poll_interval=0.001)
        await supervisor.start()
        if during_restart:
            adapter.state = "failed"
            await adapter.close_started.wait()
        closing = asyncio.create_task(supervisor.close())
        await adapter.close_started.wait()
        await asyncio.sleep(0)  # Ensure close has published intent before cancelling its caller.
        for _ in range(3):
            closing.cancel()
            await asyncio.sleep(0)
        assert not closing.done()
        assert adapter.close_calls == runtime.stop_calls == 0
        assert runtime.running
        assert supervisor.snapshot().runtime is not None
        assert supervisor.snapshot().market_data is not None
        adapter.release_close.set()
        with pytest.raises(asyncio.CancelledError):
            await closing
        assert adapter.close_calls == runtime.stop_calls == 1
        assert not runtime.running
        assert supervisor.snapshot().state == "stopped"
        assert supervisor.snapshot().runtime is None
        assert supervisor.snapshot().market_data is None
        await supervisor.close()
        assert adapter.close_calls == runtime.stop_calls == 1

    asyncio.run(scenario())
