import asyncio
import json

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
