"""Bounded lifecycle supervision for one in-process engine worker."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from .market_data import BybitMarketDataAdapter, MarketDataHealth
from .runtime import EngineRuntime, RuntimeSnapshot

SupervisorState = Literal["idle", "running", "restarting", "stopped", "failed"]


class MarketDataWorker(Protocol):
    async def start(self, symbols: Sequence[str]) -> None: ...

    async def close(self) -> None: ...

    def health(self) -> MarketDataHealth: ...


class RuntimeWorker(Protocol):
    def start(self) -> RuntimeSnapshot: ...

    def stop(self) -> RuntimeSnapshot: ...

    def snapshot(self) -> RuntimeSnapshot: ...


WorkerFactory = Callable[[], tuple[MarketDataWorker, RuntimeWorker]]


async def _await_cleanup[T](task: asyncio.Task[T]) -> T:
    """Defer all caller cancellations until owned cleanup has actually finished."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    result = task.result()
    if cancelled:
        raise asyncio.CancelledError
    return result


@dataclass(frozen=True, slots=True)
class SupervisorSnapshot:
    """Typed status facts for a local worker lifecycle endpoint."""

    state: SupervisorState
    restart_count: int
    max_restarts: int
    last_error: str | None
    runtime: RuntimeSnapshot | None
    market_data: MarketDataHealth | None


class EngineSupervisor:
    """Keep one adapter/runtime pair alive with a finite restart budget.

    This supervises an in-process async worker only. It does not supervise
    operating-system processes or recover orders and exchange/account state.
    """

    def __init__(
        self,
        *,
        symbols: Sequence[str],
        factory: WorkerFactory | None = None,
        max_restarts: int = 3,
        poll_interval: float = 0.1,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        normalized = tuple(sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()}))
        if not normalized:
            raise ValueError("symbols must contain a non-empty value")
        if max_restarts < 0:
            raise ValueError("max_restarts must be non-negative")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self._symbols = normalized
        self._factory = factory or (lambda: (BybitMarketDataAdapter(), EngineRuntime()))
        self._max_restarts = max_restarts
        self._poll_interval = poll_interval
        self._sleep = sleeper
        self._adapter: MarketDataWorker | None = None
        self._runtime: RuntimeWorker | None = None
        self._monitor: asyncio.Task[None] | None = None
        self._closing = False
        self._close_requests = 0
        self._shutdown_generation = 0
        self._state: SupervisorState = "idle"
        self._restart_count = 0
        self._last_error: str | None = None
        self._transition_lock = asyncio.Lock()

    async def start(self) -> SupervisorSnapshot:
        """Start once; a close requested during this call takes precedence."""
        generation = self._shutdown_generation
        async with self._transition_lock:
            if self._close_requests or generation != self._shutdown_generation:
                return self.snapshot()
            if self._state == "running":
                return self.snapshot()
            self._closing = False
            self._restart_count = 0
            self._last_error = None
            try:
                await self._start_worker()
                if self._closing:
                    await self._close_worker()
                    self._state = "stopped"
                    return self.snapshot()
            except asyncio.CancelledError:
                self._state = "stopped"
                raise
            except Exception as error:
                self._last_error = f"start failed: {type(error).__name__}"
                self._state = "failed"
                raise
            self._state = "running"
            self._monitor = asyncio.create_task(self._watch(), name="quant-engine-supervisor")
            return self.snapshot()

    async def close(self) -> SupervisorSnapshot:
        """Finish shutdown even if the caller is cancelled; later starts may reopen."""
        # Publish shutdown intent before waiting for an in-flight start/restart.
        self._closing = True
        self._shutdown_generation += 1
        self._close_requests += 1
        cleanup = asyncio.create_task(self._close(), name="quant-engine-supervisor-close")
        try:
            return await _await_cleanup(cleanup)
        finally:
            self._close_requests -= 1

    async def _close(self) -> SupervisorSnapshot:
        monitor = self._monitor
        self._monitor = None
        if monitor is not None:
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)
        async with self._transition_lock:
            try:
                await self._close_worker()
            except Exception as error:
                self._last_error = f"close failed: {type(error).__name__}"
                self._state = "failed"
                raise
            self._state = "stopped"
            return self.snapshot()

    def snapshot(self) -> SupervisorSnapshot:
        runtime = self._runtime.snapshot() if self._runtime is not None else None
        market_data = self._adapter.health() if self._adapter is not None else None
        return SupervisorSnapshot(
            state=self._state,
            restart_count=self._restart_count,
            max_restarts=self._max_restarts,
            last_error=self._last_error,
            runtime=runtime,
            market_data=market_data,
        )

    async def _watch(self) -> None:
        try:
            while not self._closing:
                await self._sleep(self._poll_interval)
                if self._closing or self._adapter is None:
                    return
                health = self._adapter.health()
                if health.state not in {"stopped", "failed"}:
                    continue
                await self._restart_or_fail(f"market-data worker state: {health.state}")
                if self._state == "failed":
                    return
        except Exception as error:  # noqa: BLE001 - never leave a live worker without its monitor
            async with self._transition_lock:
                self._last_error = f"monitor failed: {type(error).__name__}"
                self._state = "failed"
                try:
                    await self._close_worker()
                except Exception as cleanup_error:  # noqa: BLE001 - retain both type-only diagnostics
                    self._last_error += f"; cleanup failed: {type(cleanup_error).__name__}"

    async def _restart_or_fail(self, reason: str) -> None:
        async with self._transition_lock:
            if self._closing:
                return
            self._last_error = reason
            try:
                if self._restart_count >= self._max_restarts:
                    await self._close_worker()
                    self._state = "failed"
                    return
                self._state = "restarting"
                await self._close_worker()
                if self._closing:
                    return
                self._restart_count += 1
                await self._start_worker()
                if self._closing:
                    await self._close_worker()
                    return
            except asyncio.CancelledError:
                raise
            except Exception as error:  # noqa: BLE001 - worker failures become terminal status
                self._last_error = f"restart failed: {type(error).__name__}"
                self._state = "failed"
                return
            self._state = "running"

    async def _start_worker(self) -> None:
        adapter, runtime = self._factory()
        self._adapter = adapter
        self._runtime = runtime
        try:
            runtime.start()
            await adapter.start(self._symbols)
        except BaseException:
            await self._close_worker()
            raise

    async def _close_worker(self) -> None:
        cleanup = asyncio.create_task(self._close_worker_impl(), name="quant-engine-worker-close")
        await _await_cleanup(cleanup)

    async def _close_worker_impl(self) -> None:
        adapter = self._adapter
        runtime = self._runtime
        try:
            if adapter is not None:
                await adapter.close()
        finally:
            try:
                if runtime is not None:
                    runtime.stop()
            finally:
                self._adapter = None
                self._runtime = None
