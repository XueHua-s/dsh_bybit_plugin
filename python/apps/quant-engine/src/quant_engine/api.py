"""Versioned read-only FastAPI boundary; constructing the app performs no I/O."""

from __future__ import annotations

import math
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Response

from .monitoring import ContractModel, HealthMonitor, HealthResponse
from .service import EngineService


class MarketResponse(ContractModel):
    environment: Literal["testnet"] = "testnet"
    symbol: str
    last_price: float | None
    bid_price: float | None
    ask_price: float | None
    event_time_ms: int
    received_at: str
    partial: bool
    exchange_lag_seconds: float
    age_seconds: float


class ErrorResponse(ContractModel):
    detail: str


def validate_symbols(symbols: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(sorted({symbol.strip().upper() for symbol in symbols}))
    if not normalized or len(normalized) > 100 or any(re.fullmatch(r"[A-Z0-9]{2,32}", s) is None for s in normalized):
        raise ValueError("configure 1 to 100 explicit alphanumeric symbols (2 to 32 characters)")
    return normalized


def create_app(symbols: tuple[str, ...], *, service: EngineService | None = None, stale_after: float = 30.0) -> FastAPI:
    """Create a local observation API whose lifespan owns exactly one service."""
    symbols = validate_symbols(symbols)
    if not math.isfinite(stale_after) or stale_after <= 0:
        raise ValueError("stale_after must be finite and positive")
    engine = service or EngineService(symbols)
    if engine.symbols != symbols:
        raise ValueError("service symbols must match configured symbols")
    monitor = HealthMonitor(engine, stale_after)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            await engine.start()
            yield
        finally:
            await engine.close()

    app = FastAPI(title="Bybit Quant Engine", version="0.1.0", lifespan=lifespan)

    @app.get("/api/v1/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
    async def health(response: Response) -> HealthResponse:
        snapshot = monitor.snapshot()
        response.status_code = 200 if snapshot.ready else 503
        return snapshot

    @app.get(
        "/api/v1/market/{symbol}",
        response_model=MarketResponse,
        responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def market(symbol: str) -> MarketResponse:
        normalized = symbol.upper()
        if normalized not in symbols:
            raise HTTPException(404, "symbol is not configured")
        event = engine.latest(normalized)
        snapshot = engine.supervisor.snapshot()
        if event is None or snapshot.state != "running" or snapshot.market_data is None:
            raise HTTPException(503, "market data is unavailable")
        age = monitor.age(event.received_at)
        lag = monitor.exchange_lag(event.event_time_ms)
        if snapshot.market_data.state != "connected" or not monitor.is_fresh(event):
            raise HTTPException(503, "market data is stale or disconnected")
        return MarketResponse(
            symbol=event.symbol,
            last_price=event.last_price,
            bid_price=event.bid_price,
            ask_price=event.ask_price,
            event_time_ms=event.event_time_ms,
            received_at=event.received_at,
            age_seconds=age,
            exchange_lag_seconds=lag,
            partial=any(price is None for price in (event.last_price, event.bid_price, event.ask_price)),
        )

    return app
