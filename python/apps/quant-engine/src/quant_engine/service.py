"""Compose ingestion and bounded latest state behind a supervised worker."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import replace

from .market_data import BybitMarketDataAdapter, Connector, MarketDataHealth, TickerEvent
from .runtime import EngineRuntime
from .supervisor import EngineSupervisor


class MarketWorker:
    """Drain one adapter into one latest event per subscribed symbol.

    Consumer termination invalidates the whole worker so supervision restarts
    both ingestion and consumption rather than silently filling the queue.
    """

    def __init__(self, adapter: BybitMarketDataAdapter) -> None:
        self._adapter = adapter
        self._consumer: asyncio.Task[None] | None = None
        self._symbols: frozenset[str] = frozenset()
        self._latest: dict[str, TickerEvent] = {}
        self._closing = False

    async def start(self, symbols: Sequence[str]) -> None:
        self._symbols = frozenset(symbols)
        self._closing = False
        await self._adapter.start(symbols)
        self._consumer = asyncio.create_task(self._consume(), name="quant-engine-market-consumer")

    async def close(self) -> None:
        self._closing = True
        consumer = self._consumer
        try:
            if consumer is not None:
                consumer.cancel()
                await asyncio.gather(consumer, return_exceptions=True)
        finally:
            await self._adapter.close()
            self._latest.clear()

    def health(self) -> MarketDataHealth:
        health = self._adapter.health()
        consumer = self._consumer
        if not self._closing and (
            (consumer is not None and consumer.done()) or health.state in {"closed", "stopped", "failed"}
        ):
            return replace(health, state="failed")
        return health

    def latest(self, symbol: str) -> TickerEvent | None:
        return self._latest.get(symbol)

    async def _consume(self) -> None:
        while True:
            event = await self._adapter.next_event()
            if event.symbol in self._symbols:
                self._latest[event.symbol] = event


class EngineService:
    """Own supervised ingestion generations; HTTP only observes current facts."""

    def __init__(
        self,
        symbols: Sequence[str],
        *,
        connector: Connector | None = None,
        max_restarts: int = 3,
        poll_interval: float = 0.1,
    ) -> None:
        self.symbols = tuple(sorted({symbol.strip().upper() for symbol in symbols}))
        self.worker: MarketWorker | None = None
        self._connector = connector
        self.supervisor = EngineSupervisor(
            symbols=self.symbols,
            factory=self._new_worker,
            max_restarts=max_restarts,
            poll_interval=poll_interval,
        )

    def _new_worker(self) -> tuple[MarketWorker, EngineRuntime]:
        adapter = (
            BybitMarketDataAdapter() if self._connector is None else BybitMarketDataAdapter(connector=self._connector)
        )
        self.worker = MarketWorker(adapter)
        return self.worker, EngineRuntime()

    async def start(self) -> None:
        await self.supervisor.start()

    async def close(self) -> None:
        await self.supervisor.close()

    def latest(self, symbol: str) -> TickerEvent | None:
        return self.worker.latest(symbol) if self.worker is not None else None
