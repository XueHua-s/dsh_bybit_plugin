"""Typed, public Bybit Testnet market-data transport.

The adapter owns Bybit's wire format and reconnect policy.  Consumers receive
validated ticker events and a small health snapshot, so exchange protocol
details do not leak into strategy or risk code.
"""

from __future__ import annotations

import asyncio
import json
import math
import random
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast

import websockets.asyncio.client


class WebSocketConnection(Protocol):
    async def send(self, data: str) -> None: ...

    async def recv(self) -> str | bytes: ...

    async def close(self) -> None: ...


Connector = Callable[[str], Awaitable[WebSocketConnection]]
Sleeper = Callable[[float], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class TickerEvent:
    """A validated linear ticker update from the public V5 stream."""

    symbol: str
    last_price: float | None
    bid_price: float | None
    ask_price: float | None
    event_time_ms: int
    received_at: str


@dataclass(frozen=True, slots=True)
class MarketDataHealth:
    state: str
    queue_depth: int
    received: int
    parsed: int
    discarded: int
    reconnects: int
    last_event_at: str | None


def _connect(url: str) -> Awaitable[WebSocketConnection]:
    return cast(Awaitable[WebSocketConnection], websockets.asyncio.client.connect(url))


class BybitMarketDataAdapter:
    """Subscribe to public Testnet tickers with bounded, graceful lifecycle."""

    TESTNET_URL = "wss://stream-testnet.bybit.com/v5/public/linear"

    def __init__(
        self,
        *,
        connector: Connector = _connect,
        queue_size: int = 256,
        max_backoff: float = 30.0,
        jitter: Callable[[], float] = random.random,
        sleeper: Sleeper = asyncio.sleep,
    ) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be positive")
        if max_backoff <= 0:
            raise ValueError("max_backoff must be positive")
        self._connector = connector
        self._events: asyncio.Queue[TickerEvent] = asyncio.Queue(maxsize=queue_size)
        self._max_backoff = max_backoff
        self._jitter = jitter
        self._sleep = sleeper
        self._task: asyncio.Task[None] | None = None
        self._socket: WebSocketConnection | None = None
        self._closed = False
        self._state = "idle"
        self._received = 0
        self._parsed = 0
        self._discarded = 0
        self._reconnects = 0
        self._last_event_at: str | None = None

    async def start(self, symbols: Sequence[str]) -> None:
        """Start the background subscription; symbols must be non-empty."""
        if not symbols:
            raise ValueError("at least one symbol is required")
        if self._task is not None and not self._task.done():
            raise RuntimeError("adapter is already running")
        normalized = tuple(sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()}))
        if not normalized:
            raise ValueError("symbols must contain non-empty values")
        self._closed = False
        self._task = asyncio.create_task(self._run(normalized), name="bybit-market-data")

    async def next_event(self) -> TickerEvent:
        """Wait for the next validated ticker event."""
        return await self._events.get()

    async def close(self) -> None:
        """Stop reads, close the socket, and wait for the worker to exit."""
        self._closed = True
        self._state = "closing"
        socket = self._socket
        if socket is not None:
            await socket.close()
        task = self._task
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._task = None
        self._socket = None
        self._state = "closed"

    def health(self) -> MarketDataHealth:
        return MarketDataHealth(
            state=self._state,
            queue_depth=self._events.qsize(),
            received=self._received,
            parsed=self._parsed,
            discarded=self._discarded,
            reconnects=self._reconnects,
            last_event_at=self._last_event_at,
        )

    async def _run(self, symbols: tuple[str, ...]) -> None:
        topics = [f"tickers.{symbol}" for symbol in symbols]
        backoff = 0.5
        while not self._closed:
            try:
                self._state = "connecting"
                self._socket = await self._connector(self.TESTNET_URL)
                self._state = "connected"
                await self._socket.send(json.dumps({"op": "subscribe", "args": topics}))
                backoff = 0.5
                while not self._closed:
                    raw = await self._socket.recv()
                    self._received += 1
                    event = self._parse(raw)
                    if event is None:
                        self._discarded += 1
                        continue
                    await self._events.put(event)
                    self._parsed += 1
                    self._last_event_at = event.received_at
            except asyncio.CancelledError:
                raise
            except (ConnectionError, OSError, RuntimeError, websockets.exceptions.WebSocketException):
                if self._closed:
                    break
                self._state = "reconnecting"
                self._reconnects += 1
                delay = min(backoff, self._max_backoff) * (0.5 + self._jitter())
                await self._sleep(delay)
                backoff = min(backoff * 2, self._max_backoff)
            finally:
                self._socket = None
        self._state = "closed" if self._closed else "stopped"

    @staticmethod
    def _parse(raw: str | bytes) -> TickerEvent | None:
        try:
            decoded = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(decoded, dict) or not isinstance(decoded.get("topic"), str):
            return None
        topic = decoded["topic"]
        if not topic.startswith("tickers."):
            return None
        topic_symbol = topic.removeprefix("tickers.").strip()
        if not topic_symbol:
            return None
        payload = decoded.get("data")
        if isinstance(payload, dict):
            item = cast(Mapping[str, object], payload)
        elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
            item = cast(Mapping[str, object], payload[0])
        else:
            return None
        symbol = item.get("symbol")
        if symbol is None:
            symbol = topic_symbol
        elif not isinstance(symbol, str) or not symbol.strip():
            return None
        else:
            symbol = symbol.strip()
        event_time = decoded.get("ts")
        if (
            isinstance(event_time, bool)
            or not isinstance(event_time, (int, float))
            or event_time <= 0
            or (isinstance(event_time, float) and (not math.isfinite(event_time) or not event_time.is_integer()))
        ):
            return None

        def number(key: str) -> float | None:
            value = item.get(key)
            if value is None:
                return None
            try:
                parsed = float(value) if isinstance(value, (int, float, str)) else None
            except (OverflowError, ValueError):
                return None
            return parsed if parsed is None or math.isfinite(parsed) else None

        prices = tuple(number(key) for key in ("lastPrice", "bid1Price", "ask1Price"))
        for key, price in zip(("lastPrice", "bid1Price", "ask1Price"), prices, strict=True):
            if item.get(key) is not None and price is None:
                return None

        return TickerEvent(
            symbol=symbol,
            last_price=prices[0],
            bid_price=prices[1],
            ask_price=prices[2],
            event_time_ms=int(event_time),
            received_at=datetime.now(UTC).isoformat(),
        )
