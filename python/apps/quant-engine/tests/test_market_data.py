import asyncio
import json

import pytest
from quant_engine.market_data import BybitMarketDataAdapter, WebSocketConnection


class FakeSocket:
    def __init__(self, frames: list[str], *, disconnect_first: bool = False) -> None:
        self.frames = iter(frames)
        self.disconnect_first = disconnect_first
        self.sent: list[str] = []
        self.closed = False

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def recv(self) -> str:
        if self.disconnect_first:
            self.disconnect_first = False
            raise ConnectionError("test disconnect")
        try:
            return next(self.frames)
        except StopIteration:
            await asyncio.Future()
            raise AssertionError("unreachable")

    async def close(self) -> None:
        self.closed = True


def _frame(symbol: str = "BTCUSDT", price: str = "64000.1") -> str:
    return json.dumps(
        {
            "topic": f"tickers.{symbol}",
            "ts": 1730000000000,
            "data": [{"symbol": symbol, "lastPrice": price, "bid1Price": "64000", "ask1Price": "64001"}],
        }
    )


def _object_frame() -> str:
    return json.dumps(
        {
            "topic": "tickers.ETHUSDT",
            "ts": 1730000001000,
            "data": {"symbol": "ETHUSDT", "lastPrice": "3000"},
        }
    )


def _invalid_frame(**updates: object) -> str:
    frame = json.loads(_frame())
    frame.update(updates)
    return json.dumps(frame)


def test_subscribes_parses_and_closes_public_testnet_socket() -> None:
    async def scenario() -> None:
        socket = FakeSocket(["{bad", _frame()])
        urls: list[str] = []

        async def connect(url: str) -> WebSocketConnection:
            urls.append(url)
            return socket

        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["btcusdt"])
        event = await asyncio.wait_for(adapter.next_event(), timeout=1)
        await adapter.close()

        assert urls == [BybitMarketDataAdapter.TESTNET_URL]
        assert json.loads(socket.sent[0]) == {"op": "subscribe", "args": ["tickers.BTCUSDT"]}
        assert (event.symbol, event.last_price, event.bid_price, event.ask_price) == (
            "BTCUSDT",
            64000.1,
            64000.0,
            64001.0,
        )
        health = adapter.health()
        assert health.state == "closed"
        assert (health.received, health.parsed, health.discarded) == (2, 1, 1)
        assert socket.closed

        object_event = BybitMarketDataAdapter._parse(_object_frame())
        assert object_event is not None
        assert (object_event.symbol, object_event.last_price) == ("ETHUSDT", 3000.0)

    asyncio.run(scenario())


def test_bounded_queue_applies_backpressure_and_tracks_depth() -> None:
    async def scenario() -> None:
        socket = FakeSocket([_frame(), _frame(price="64002")])

        async def connect(_: str) -> WebSocketConnection:
            return socket

        adapter = BybitMarketDataAdapter(connector=connect, queue_size=1)
        await adapter.start(["BTCUSDT"])
        for _ in range(100):
            if adapter.health().queue_depth == 1:
                break
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert adapter.health().queue_depth == 1
        assert adapter.health().parsed == 1
        assert (await adapter.next_event()).last_price == 64000.1
        next_event = await asyncio.wait_for(adapter.next_event(), timeout=1)
        assert next_event.last_price == 64002.0
        await adapter.close()

    asyncio.run(scenario())


def test_invalid_frames_are_discarded_without_stopping_worker() -> None:
    async def scenario() -> None:
        invalid_frames = [
            _invalid_frame(topic="tickers."),
            _invalid_frame(data=[{"symbol": "", "lastPrice": "1"}]),
            _invalid_frame(ts=float("nan")),
            _invalid_frame(ts=float("inf")),
            _invalid_frame(ts=10**400),
            _invalid_frame(ts=1730000000000.5),
            _invalid_frame(data=[{"symbol": "BTCUSDT", "lastPrice": "nan"}]),
            _invalid_frame(data=[{"symbol": "BTCUSDT", "bid1Price": "-inf"}]),
            _invalid_frame(data=[{"symbol": "BTCUSDT", "lastPrice": 10**400}]),
        ]
        socket = FakeSocket([*invalid_frames, _frame()])

        async def connect(_: str) -> WebSocketConnection:
            return socket

        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["BTCUSDT"])
        event = await asyncio.wait_for(adapter.next_event(), timeout=1)
        health = adapter.health()
        await adapter.close()

        assert event.symbol == "BTCUSDT"
        assert health.received == len(invalid_frames) + 1
        assert health.parsed == 1
        assert health.discarded == len(invalid_frames)
        assert socket.closed

    asyncio.run(scenario())


def test_reconnect_uses_injected_jitter_and_records_health() -> None:
    async def scenario() -> None:
        sockets = [FakeSocket([], disconnect_first=True), FakeSocket([_frame()])]
        delays: list[float] = []
        attempts = 0

        async def connect(_: str) -> WebSocketConnection:
            nonlocal attempts
            socket = sockets[attempts]
            attempts += 1
            return socket

        async def sleep(delay: float) -> None:
            delays.append(delay)

        adapter = BybitMarketDataAdapter(connector=connect, jitter=lambda: 0.5, sleeper=sleep)
        await adapter.start(["BTCUSDT"])
        event = await asyncio.wait_for(adapter.next_event(), timeout=1)
        await adapter.close()

        assert event.symbol == "BTCUSDT"
        assert delays == [0.5]
        assert adapter.health().reconnects == 1

    asyncio.run(scenario())


class LifecycleSocket(FakeSocket):
    def __init__(self, *, fail_at: str | None = None) -> None:
        super().__init__([])
        self.fail_at = fail_at
        self.close_calls = 0
        self.reading = asyncio.Event()
        self.closing = asyncio.Event()
        self.release_close = asyncio.Event()

    async def send(self, data: str) -> None:
        if self.fail_at == "send":
            raise ValueError("untrusted transport payload")
        await super().send(data)

    async def recv(self) -> str:
        self.reading.set()
        if self.fail_at in ("recv", "recv_slow_close"):
            raise ValueError("untrusted transport payload")
        if self.fail_at == "disconnect":
            raise ConnectionError("untrusted transport payload")
        return await super().recv()

    async def close(self) -> None:
        self.close_calls += 1
        self.closing.set()
        if self.fail_at == "close":
            raise ValueError("untrusted transport payload")
        if self.fail_at in ("slow_close", "recv_slow_close"):
            await self.release_close.wait()
        await super().close()


async def _wait_for_state(adapter: BybitMarketDataAdapter, state: str) -> None:
    async with asyncio.timeout(1):
        while adapter.health().state != state:
            await asyncio.sleep(0)


def test_unexpected_transport_failures_publish_safe_failed_health_and_close_socket() -> None:
    async def scenario(fail_at: str) -> None:
        socket = LifecycleSocket(fail_at=fail_at)
        unobserved: list[object] = []
        asyncio.get_running_loop().set_exception_handler(lambda _loop, context: unobserved.append(context))

        async def connect(_: str) -> WebSocketConnection:
            if fail_at == "connect":
                raise ValueError("untrusted transport payload")
            return socket

        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["BTCUSDT"])
        await _wait_for_state(adapter, "failed")
        assert adapter._task is not None and adapter._task.done()
        assert adapter._task.exception() is None
        assert "untrusted" not in repr(adapter.health())
        assert socket.close_calls == (0 if fail_at == "connect" else 1)
        await adapter.close()
        assert adapter.health().state == "closed"
        assert unobserved == []

    for fail_at in ("connect", "send", "recv"):
        asyncio.run(scenario(fail_at))


def test_reconnect_closes_old_socket_before_backoff_and_next_connect() -> None:
    async def scenario() -> None:
        old_socket = LifecycleSocket(fail_at="disconnect")
        new_socket = LifecycleSocket()
        attempts = 0

        async def connect(_: str) -> WebSocketConnection:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return old_socket
            assert old_socket.closed and old_socket.close_calls == 1
            return new_socket

        async def sleep(_: float) -> None:
            assert old_socket.closed and old_socket.close_calls == 1

        adapter = BybitMarketDataAdapter(connector=connect, sleeper=sleep)
        await adapter.start(["BTCUSDT"])
        await asyncio.wait_for(new_socket.reading.wait(), 1)
        await adapter.close()
        assert attempts == 2
        assert adapter.health().reconnects == 1
        assert new_socket.close_calls == 1

    asyncio.run(scenario())


def test_backoff_failures_are_terminal_after_socket_cleanup() -> None:
    async def scenario(fail_at: str) -> None:
        socket = LifecycleSocket(fail_at="disconnect")

        async def connect(_: str) -> WebSocketConnection:
            return socket

        def jitter() -> float:
            if fail_at == "jitter":
                raise ValueError("untrusted jitter payload")
            return 0.5

        async def sleep(_: float) -> None:
            raise ValueError("untrusted sleep payload")

        adapter = BybitMarketDataAdapter(connector=connect, jitter=jitter, sleeper=sleep)
        await adapter.start(["BTCUSDT"])
        await _wait_for_state(adapter, "failed")
        assert socket.closed and socket.close_calls == 1
        assert adapter.health().reconnects == 1
        await adapter.close()

    for fail_at in ("jitter", "sleep"):
        asyncio.run(scenario(fail_at))


def test_close_failure_still_stops_reader_and_reconnect_worker() -> None:
    async def scenario(explicit_close: bool) -> None:
        socket = LifecycleSocket(fail_at="close")
        attempts = 0

        async def connect(_: str) -> WebSocketConnection:
            nonlocal attempts
            attempts += 1
            return socket

        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["BTCUSDT"])
        await asyncio.wait_for(socket.reading.wait(), 1)
        if explicit_close:
            await asyncio.wait_for(adapter.close(), 1)
        else:
            assert adapter._task is not None
            adapter._task.cancel()
            await _wait_for_state(adapter, "failed")
            await adapter.close()
        assert adapter.health().state == "closed"
        assert socket.close_calls == 1
        assert attempts == 1
        assert adapter._task is None

    for explicit_close in (True, False):
        asyncio.run(scenario(explicit_close))


def test_concurrent_cancelled_close_keeps_cleanup_and_prevents_start_race() -> None:
    async def scenario() -> None:
        socket = LifecycleSocket(fail_at="slow_close")

        async def connect(_: str) -> WebSocketConnection:
            return socket

        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["BTCUSDT"])
        await asyncio.wait_for(socket.reading.wait(), 1)
        first = asyncio.create_task(adapter.close())
        await asyncio.wait_for(socket.closing.wait(), 1)
        second = asyncio.create_task(adapter.close())
        first.cancel()
        await asyncio.gather(first, return_exceptions=True)
        try:
            await adapter.start(["BTCUSDT"])
        except RuntimeError as error:
            assert str(error) == "adapter is closing"
        else:
            raise AssertionError("start raced with incomplete cleanup")
        socket.release_close.set()
        await asyncio.wait_for(second, 1)
        await adapter.close()
        assert socket.close_calls == 1
        assert adapter.health().state == "closed"
        assert adapter._task is None

    asyncio.run(scenario())


def test_cancellation_during_queue_backpressure_closes_socket_once() -> None:
    async def scenario() -> None:
        socket = FakeSocket([_frame(), _frame(), _frame()])

        async def connect(_: str) -> WebSocketConnection:
            return socket

        adapter = BybitMarketDataAdapter(connector=connect, queue_size=1)
        await adapter.start(["BTCUSDT"])
        async with asyncio.timeout(1):
            while adapter.health().received != 2:
                await asyncio.sleep(0)
        await asyncio.wait_for(adapter.close(), 1)
        assert socket.closed
        assert adapter.health().queue_depth == 1
        assert adapter.health().parsed == 1
        assert adapter._task is None

    asyncio.run(scenario())


def test_explicit_close_during_terminal_cleanup_waits_without_interrupting_socket_close() -> None:
    async def scenario() -> None:
        socket = LifecycleSocket(fail_at="recv_slow_close")

        async def connect(_: str) -> WebSocketConnection:
            return socket

        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["BTCUSDT"])
        await asyncio.wait_for(socket.closing.wait(), 1)
        close = asyncio.create_task(adapter.close())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not close.done()
        socket.release_close.set()
        await asyncio.wait_for(close, 1)
        assert socket.closed and socket.close_calls == 1
        assert adapter.health().state == "closed"

    asyncio.run(scenario())


def test_slow_socket_close_is_bounded_and_shutdown_worker_finishes() -> None:
    async def scenario() -> None:
        socket = LifecycleSocket(fail_at="slow_close")

        async def connect(_: str) -> WebSocketConnection:
            return socket

        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["BTCUSDT"])
        await asyncio.wait_for(socket.reading.wait(), 1)
        await asyncio.wait_for(adapter.close(), 6)
        assert socket.close_calls == 1
        assert adapter._task is None
        assert adapter.health().state == "closed"

    asyncio.run(scenario())


def test_failed_adapter_can_restart_with_a_fresh_transport() -> None:
    async def scenario() -> None:
        failed = LifecycleSocket(fail_at="recv")
        replacement = LifecycleSocket()
        sockets = iter([failed, replacement])

        async def connect(_: str) -> WebSocketConnection:
            return next(sockets)

        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["BTCUSDT"])
        await _wait_for_state(adapter, "failed")
        await adapter.start(["ETHUSDT"])
        await asyncio.wait_for(replacement.reading.wait(), 1)
        assert adapter.health().state == "connected"
        await adapter.close()
        assert failed.close_calls == replacement.close_calls == 1

    asyncio.run(scenario())


def test_unexpected_parser_failure_is_terminal_and_closes_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        socket = FakeSocket([_frame()])

        async def connect(_: str) -> WebSocketConnection:
            return socket

        def fail_parse(_: str | bytes) -> None:
            raise ValueError("untrusted parser payload")

        monkeypatch.setattr(BybitMarketDataAdapter, "_parse", staticmethod(fail_parse))
        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["BTCUSDT"])
        await _wait_for_state(adapter, "failed")
        assert socket.closed
        assert adapter._task is not None and adapter._task.exception() is None
        await adapter.close()

    asyncio.run(scenario())


def test_repeated_worker_cancellation_cannot_interrupt_socket_cleanup() -> None:
    async def scenario() -> None:
        socket = LifecycleSocket(fail_at="slow_close")

        async def connect(_: str) -> WebSocketConnection:
            return socket

        adapter = BybitMarketDataAdapter(connector=connect)
        await adapter.start(["BTCUSDT"])
        await asyncio.wait_for(socket.reading.wait(), 1)
        close = asyncio.create_task(adapter.close())
        await asyncio.wait_for(socket.closing.wait(), 1)
        assert adapter._task is not None
        for _ in range(3):
            adapter._task.cancel()
            await asyncio.sleep(0)
        assert not close.done()
        socket.release_close.set()
        await asyncio.wait_for(close, 1)
        assert socket.closed and socket.close_calls == 1

    asyncio.run(scenario())
