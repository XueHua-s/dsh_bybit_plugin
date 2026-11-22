"""Offline integration through the real adapter, consumer, supervisor and ASGI lifespan."""

import argparse
import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from quant_engine.api import create_app
from quant_engine.bootstrap import loopback_host
from quant_engine.market_data import WebSocketConnection
from quant_engine.service import EngineService, MarketWorker


class Socket:
    def __init__(self) -> None:
        self.frames: asyncio.Queue[str] = asyncio.Queue()
        self.closed = False
        self.subscriptions: list[str] = []

    async def send(self, data: str) -> None:
        self.subscriptions.append(data)

    async def recv(self) -> str:
        return await self.frames.get()

    async def close(self) -> None:
        self.closed = True

    def ticker(self, *, timestamp: int | None = None) -> None:
        self.frames.put_nowait(
            json.dumps(
                {
                    "topic": "tickers.BTCUSDT",
                    "ts": timestamp if timestamp is not None else int(datetime.now(UTC).timestamp() * 1000),
                    "data": {"symbol": "BTCUSDT", "lastPrice": "50000", "bid1Price": "49999", "ask1Price": "50001"},
                }
            )
        )


async def eventually(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(2):
        while not condition():
            await asyncio.sleep(0.001)


def test_lifespan_drains_real_adapter_and_reports_status() -> None:
    async def scenario() -> None:
        socket = Socket()

        async def connect(url: str) -> WebSocketConnection:
            assert url == "wss://stream-testnet.bybit.com/v5/public/linear"
            return socket

        engine = EngineService(("BTCUSDT",), connector=connect, poll_interval=0.001)
        app = create_app(("BTCUSDT",), service=engine)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            empty = await client.get("/api/v1/health")
            assert empty.status_code == 503
            assert empty.json()["status"] == "degraded"
            assert (await client.get("/api/v1/market/BTCUSDT")).status_code == 503
            assert (await client.get("/api/v1/market/ETHUSDT")).status_code == 404
            for _ in range(600):
                socket.ticker()
            await eventually(
                lambda: (
                    engine.latest("BTCUSDT") is not None
                    and (market := engine.supervisor.snapshot().market_data) is not None
                    and market.parsed == 600
                    and market.queue_depth == 0
                )
            )
            health = await client.get("/api/v1/health")
            assert health.status_code == 200
            facts = health.json()
            assert facts["ready"] is True
            assert facts["market"]["queue_depth"] == 0
            assert facts["market"]["parsed"] == 600
            assert facts["process"]["rss_bytes"] > 0
            assert facts["process"]["cpu_user_seconds"] >= 0
            assert facts["execution"]["order_latency_ms"] is None
            assert facts["execution"]["order_rejection_rate"] is None
            assert facts["execution"]["reconciliation"] == "unknown"
            ticker = await client.get("/api/v1/market/BTCUSDT")
            assert ticker.status_code == 200
            assert ticker.json()["last_price"] == 50000
            assert socket.subscriptions
            socket.frames.put_nowait(
                json.dumps(
                    {
                        "topic": "tickers.BTCUSDT",
                        "ts": int(datetime.now(UTC).timestamp() * 1000),
                        "type": "delta",
                        "data": {"symbol": "BTCUSDT", "bid1Price": "49998"},
                    }
                )
            )
            await eventually(lambda: (event := engine.latest("BTCUSDT")) is not None and event.bid_price == 49998)
            partial = (await client.get("/api/v1/market/BTCUSDT")).json()
            assert partial["partial"] is False
            assert partial["last_price"] == 50000
            provenance = await client.get("/api/v1/market/BTCUSDT/provenance")
            assert provenance.status_code == 503
        assert socket.closed
        assert engine.latest("BTCUSDT") is None
        assert engine.supervisor.snapshot().state == "stopped"
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]

    asyncio.run(scenario())


def test_consumer_failure_exhausts_restart_budget_and_closes_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failed_consumer(_self: MarketWorker) -> None:
        raise ValueError("injected consumer fault")

    monkeypatch.setattr(MarketWorker, "_consume", failed_consumer)

    async def scenario() -> None:
        sockets: list[Socket] = []

        async def connect(_url: str) -> WebSocketConnection:
            socket = Socket()
            sockets.append(socket)
            return socket

        engine = EngineService(("BTCUSDT",), connector=connect, max_restarts=1, poll_interval=0.001)
        app = create_app(("BTCUSDT",), service=engine)
        async with app.router.lifespan_context(app):
            await eventually(lambda: engine.supervisor.snapshot().state == "failed")
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                health = await client.get("/api/v1/health")
                assert health.status_code == 503
                assert health.json()["status"] == "unavailable"
                assert health.json()["restart_count"] == 1
                assert health.json()["last_error"] is not None
                assert (await client.get("/api/v1/market/BTCUSDT")).status_code == 503
            assert len(sockets) == 2
            assert all(socket.closed for socket in sockets)
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]

    asyncio.run(scenario())


def test_stale_data_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    # Timestamp is injected at the adapter boundary, not a fabricated HTTP response.
    import quant_engine.market_data as adapter_module

    class OldClock(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return datetime.now(UTC) - timedelta(minutes=5)

    monkeypatch.setattr(adapter_module, "datetime", OldClock)

    async def scenario() -> None:
        socket = Socket()

        async def connect(_url: str) -> WebSocketConnection:
            return socket

        engine = EngineService(("BTCUSDT",), connector=connect)
        app = create_app(("BTCUSDT",), service=engine, stale_after=1)
        async with app.router.lifespan_context(app):
            socket.ticker()
            await eventually(lambda: engine.latest("BTCUSDT") is not None)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                assert (await client.get("/api/v1/market/BTCUSDT")).status_code == 503
                assert (await client.get("/api/v1/health")).json()["ready"] is False

    asyncio.run(scenario())


def test_offline_schema_and_config_guard() -> None:
    app = create_app(("BTCUSDT",))
    schema = app.openapi()
    assert set(schema["paths"]) == {
        "/api/v1/health",
        "/api/v1/market/{symbol}",
        "/api/v1/market/{symbol}/provenance",
        "/api/v1/research/strategy-evidence",
    }
    assert "HealthResponse" in schema["components"]["schemas"]
    assert loopback_host("127.0.0.1") == "127.0.0.1"
    assert loopback_host("::1") == "::1"
    for host in ("0.0.0.0", "example.com", "192.168.1.2"):
        with pytest.raises(argparse.ArgumentTypeError):
            loopback_host(host)
    for symbols in ((), ("",), ("BTC/USDT",)):
        with pytest.raises(ValueError):
            create_app(symbols)
    for stale_after in (0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            create_app(("BTCUSDT",), stale_after=stale_after)


@pytest.mark.parametrize("offset", [-300, 300])
def test_exchange_timestamp_age_rejected(offset: int) -> None:
    async def scenario() -> None:
        socket = Socket()

        async def connect(_url: str) -> WebSocketConnection:
            return socket

        engine = EngineService(("BTCUSDT",), connector=connect)
        app = create_app(("BTCUSDT",), service=engine)
        async with app.router.lifespan_context(app):
            socket.ticker(timestamp=int((datetime.now(UTC).timestamp() + offset) * 1000))
            await eventually(lambda: engine.latest("BTCUSDT") is not None)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                assert (await client.get("/api/v1/health")).status_code == 503
                assert (await client.get("/api/v1/market/BTCUSDT")).status_code == 503

    asyncio.run(scenario())


def test_extreme_exchange_timestamp_discarded_before_http() -> None:
    async def scenario() -> None:
        socket = Socket()

        async def connect(_url: str) -> WebSocketConnection:
            return socket

        engine = EngineService(("BTCUSDT",), connector=connect)
        app = create_app(("BTCUSDT",), service=engine)
        async with app.router.lifespan_context(app):
            socket.ticker(timestamp=10**400)
            await eventually(
                lambda: (market := engine.supervisor.snapshot().market_data) is not None and market.discarded == 1
            )
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                assert (await client.get("/api/v1/health")).status_code == 503
                assert (await client.get("/api/v1/market/BTCUSDT")).status_code == 503
            assert engine.latest("BTCUSDT") is None

    asyncio.run(scenario())
