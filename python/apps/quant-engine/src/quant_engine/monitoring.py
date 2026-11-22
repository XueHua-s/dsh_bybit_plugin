"""Measured process and market-readiness facts, without invented execution data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import psutil
from pydantic import BaseModel, ConfigDict

from .market_data import TickerEvent
from .service import EngineService


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProcessMetrics(ContractModel):
    rss_bytes: int
    cpu_user_seconds: float
    cpu_system_seconds: float


class MarketHealth(ContractModel):
    state: str
    queue_depth: int
    received: int
    parsed: int
    discarded: int
    reconnects: int
    last_event_at: str | None
    freshness_seconds: dict[str, float | None]
    exchange_lag_seconds: dict[str, float | None]


class ExecutionMetrics(ContractModel):
    status: Literal["unknown"] = "unknown"
    order_latency_ms: float | None = None
    order_rejection_rate: float | None = None
    reconciliation: Literal["unknown"] = "unknown"


class HealthResponse(ContractModel):
    status: Literal["ready", "degraded", "unavailable"]
    ready: bool
    environment: Literal["testnet"] = "testnet"
    supervisor_state: str
    restart_count: int
    max_restarts: int
    last_error: str | None
    process: ProcessMetrics
    market: MarketHealth | None
    execution: ExecutionMetrics


class HealthMonitor:
    """Readiness requires a connected feed and fresh data for every symbol."""

    def __init__(self, service: EngineService, stale_after: float) -> None:
        self._service = service
        self._stale_after = stale_after
        self._process = psutil.Process()

    def age(self, received_at: str) -> float:
        return max(0, (datetime.now(UTC) - datetime.fromisoformat(received_at)).total_seconds())

    def exchange_lag(self, event_time_ms: int) -> float:
        return datetime.now(UTC).timestamp() - event_time_ms / 1000

    def is_fresh(self, event: TickerEvent | None) -> bool:
        """One freshness policy for readiness and market queries, including clock skew."""
        return (
            event is not None
            and self.age(event.received_at) <= self._stale_after
            and -5 <= self.exchange_lag(event.event_time_ms) <= self._stale_after
        )

    def snapshot(self) -> HealthResponse:
        supervisor = self._service.supervisor.snapshot()
        market = supervisor.market_data
        freshness = {
            symbol: self.age(event.received_at) if (event := self._service.latest(symbol)) is not None else None
            for symbol in self._service.symbols
        }
        exchange_lags = {
            symbol: self.exchange_lag(event.event_time_ms) if (event := self._service.latest(symbol)) else None
            for symbol in self._service.symbols
        }
        ready = (
            supervisor.state == "running"
            and market is not None
            and market.state == "connected"
            and all(self.is_fresh(self._service.latest(symbol)) for symbol in self._service.symbols)
        )
        cpu = self._process.cpu_times()
        return HealthResponse(
            status="ready" if ready else "degraded" if supervisor.state in {"running", "restarting"} else "unavailable",
            ready=ready,
            supervisor_state=supervisor.state,
            restart_count=supervisor.restart_count,
            max_restarts=supervisor.max_restarts,
            last_error=supervisor.last_error,
            process=ProcessMetrics(
                rss_bytes=self._process.memory_info().rss, cpu_user_seconds=cpu.user, cpu_system_seconds=cpu.system
            ),
            market=None
            if market is None
            else MarketHealth(
                state=market.state,
                queue_depth=market.queue_depth,
                received=market.received,
                parsed=market.parsed,
                discarded=market.discarded,
                reconnects=market.reconnects,
                last_event_at=market.last_event_at,
                freshness_seconds=freshness,
                exchange_lag_seconds=exchange_lags,
            ),
            execution=ExecutionMetrics(),
        )
