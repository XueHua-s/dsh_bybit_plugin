"""Public Testnet market observations persist without becoming stale live state."""

import asyncio
import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx
from quant_data.market_store import MarketSnapshotRecord, MarketSnapshotStore
from quant_data.migrations import upgrade_sqlite
from quant_engine.api import create_app
from quant_engine.market_data import WebSocketConnection
from quant_engine.service import EngineService


class Socket:
    def __init__(self) -> None:
        self.frames: asyncio.Queue[str] = asyncio.Queue()
        self.closed = False

    async def send(self, data: str) -> None:
        assert json.loads(data) == {"op": "subscribe", "args": ["tickers.BTCUSDT"]}

    async def recv(self) -> str:
        return await self.frames.get()

    async def close(self) -> None:
        self.closed = True

    def snapshot(self) -> None:
        self.frames.put_nowait(
            json.dumps(
                {
                    "topic": "tickers.BTCUSDT",
                    "ts": int(datetime.now(UTC).timestamp() * 1000),
                    "type": "snapshot",
                    "data": {
                        "symbol": "BTCUSDT",
                        "lastPrice": "64000.1234567890123456789",
                        "bid1Price": "64000.1",
                        "ask1Price": "64000.2",
                    },
                }
            )
        )

    def delta(self) -> None:
        self.frames.put_nowait(
            json.dumps(
                {
                    "topic": "tickers.BTCUSDT",
                    "ts": int(datetime.now(UTC).timestamp() * 1000),
                    "type": "delta",
                    "data": {"symbol": "BTCUSDT", "bid1Price": "63999.9"},
                }
            )
        )


class FailingStore:
    def upsert(self, record: MarketSnapshotRecord) -> None:
        del record
        raise OSError("private storage detail")

    def latest(self, environment: str, symbol: str) -> MarketSnapshotRecord | None:
        del environment, symbol
        return None

    def close(self) -> None:
        pass


async def eventually(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(2):
        while not condition():
            await asyncio.sleep(0.001)


def test_provenance_distinguishes_persisted_history_from_current_stream(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = tmp_path / "market.sqlite"
        with sqlite3.connect(database) as connection:
            connection.execute("PRAGMA user_version=0")
        upgrade_sqlite(database)
        store = MarketSnapshotStore.sqlite(database)
        store.upsert(
            MarketSnapshotRecord(
                environment="testnet",
                symbol="BTCUSDT",
                last_price=Decimal("63000.25"),
                bid_price=None,
                ask_price=None,
                event_time_ms=1_790_000_000_000,
                received_at="2026-11-18T00:00:00+00:00",
                source="bybit-v5-public-linear-tickers",
            )
        )
        socket = Socket()

        async def connect(_url: str) -> WebSocketConnection:
            return socket

        engine = EngineService(("BTCUSDT",), connector=connect, market_store=store)
        app = create_app(("BTCUSDT",), service=engine)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            historical = await client.get("/api/v1/market/BTCUSDT/provenance")
            assert historical.status_code == 200
            assert historical.json()["historical_only"] is True
            assert historical.json()["live_observation"] is False
            assert (await client.get("/api/v1/market/BTCUSDT")).status_code == 503

            socket.snapshot()
            await eventually(lambda: engine.latest("BTCUSDT") is not None)
            socket.delta()
            await eventually(
                lambda: (event := engine.latest("BTCUSDT")) is not None and event.bid_price == Decimal("63999.9")
            )
            await eventually(
                lambda: (row := store.latest("testnet", "BTCUSDT")) is not None and row.bid_price == Decimal("63999.9")
            )
            current = await client.get("/api/v1/market/BTCUSDT/provenance")
            assert current.status_code == 200
            assert current.json()["live_observation"] is True
            assert current.json()["historical_only"] is False
            market = await client.get("/api/v1/market/BTCUSDT")
            assert market.status_code == 200
            assert market.json()["last_price"] == 64000.12345678901
            assert market.json()["bid_price"] == 63999.9
            assert market.json()["partial"] is False
        assert socket.closed

    asyncio.run(scenario())


def test_store_failure_never_publishes_market_ready(tmp_path: Path) -> None:
    async def scenario() -> None:
        socket = Socket()

        async def connect(_url: str) -> WebSocketConnection:
            return socket

        engine = EngineService(("BTCUSDT",), connector=connect, market_store=FailingStore(), max_restarts=0)
        app = create_app(("BTCUSDT",), service=engine)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            socket.snapshot()
            await eventually(lambda: engine.supervisor.snapshot().state == "failed")
            assert engine.latest("BTCUSDT") is None
            health = await client.get("/api/v1/health")
            assert health.status_code == 503
            assert "private storage detail" not in health.text
            assert (await client.get("/api/v1/market/BTCUSDT")).status_code == 503
        assert socket.closed

    asyncio.run(scenario())
