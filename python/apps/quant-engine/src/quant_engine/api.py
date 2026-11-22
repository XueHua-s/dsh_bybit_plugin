"""Versioned read-only FastAPI boundary; constructing the app performs no I/O."""

from __future__ import annotations

import math
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator, model_validator
from quant_strategies import Bar, Market, MarketSnapshot

from .monitoring import ContractModel, HealthMonitor, HealthResponse
from .service import EngineService
from .strategy_evidence import evaluate_strategy_families

SUPPORTED_EVIDENCE_INTERVALS = frozenset({"1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"})
MAX_RESEARCH_BODY_BYTES = 262_144


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


class MarketProvenanceResponse(ContractModel):
    environment: Literal["testnet"] = "testnet"
    symbol: str
    last_price: float | None
    bid_price: float | None
    ask_price: float | None
    event_time_ms: int
    received_at: str
    source: str
    live_observation: bool
    historical_only: bool


class ErrorResponse(ContractModel):
    detail: str


class StrategyEvidenceBarRequest(ContractModel):
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @field_validator("timestamp_ms", mode="before")
    @classmethod
    def strict_timestamp(cls, value: object) -> int:
        if type(value) is not int or not 0 <= value <= 32503680000000:
            raise ValueError("invalid_bar_timestamp")
        return value

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def strict_number(cls, value: object) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError("invalid_bar_value")
        return float(value)

    @model_validator(mode="after")
    def valid_ohlcv(self) -> StrategyEvidenceBarRequest:
        if min(self.open, self.high, self.low, self.close) <= 0 or self.volume < 0:
            raise ValueError("invalid_bar_range")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("invalid_bar_ohlc")
        return self


class StrategyEvidenceRequest(ContractModel):
    symbol: str
    market: Literal["spot", "linear"]
    interval: str
    bars: tuple[StrategyEvidenceBarRequest, ...] = Field(max_length=1000)
    funding_rate: float | None = None

    @field_validator("symbol")
    @classmethod
    def valid_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if re.fullmatch(r"[A-Z0-9]{2,32}", normalized) is None:
            raise ValueError("invalid_symbol")
        return normalized

    @field_validator("interval")
    @classmethod
    def valid_interval(cls, value: str) -> str:
        if value not in SUPPORTED_EVIDENCE_INTERVALS:
            raise ValueError("unsupported_interval")
        return value

    @field_validator("funding_rate", mode="before")
    @classmethod
    def strict_funding(cls, value: object) -> float | None:
        if value is None:
            return None
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or abs(value) > 0.1
        ):
            raise ValueError("invalid_funding_rate")
        return float(value)

    @model_validator(mode="after")
    def ordered_bars(self) -> StrategyEvidenceRequest:
        if any(left.timestamp_ms >= right.timestamp_ms for left, right in zip(self.bars, self.bars[1:])):
            raise ValueError("unordered_market_snapshot")
        if self.market == "spot" and self.funding_rate is not None:
            raise ValueError("spot_market_has_no_funding_rate")
        return self


class StrategyEvidenceResult(ContractModel):
    strategy_id: str
    name: str
    version: str
    source_repository: str
    source_commit: str | None
    license: str
    lifecycle_status: str
    validation_status: str
    supported_markets: tuple[str, ...]
    ready: bool
    research_target_exposure: float | None
    reason: str
    features: tuple[tuple[str, float], ...]
    research_only: Literal[True] = True
    deployment_eligible: Literal[False] = False


class StrategyEvidenceResponse(ContractModel):
    symbol: str
    market: Literal["spot", "linear"]
    interval: str
    snapshot_status: Literal["fresh", "stale", "empty"]
    snapshot_age_ms: int | None
    newest_timestamp_ms: int | None
    strategy_count: int
    research_only: Literal[True] = True
    deployment_eligible: Literal[False] = False
    strategies: tuple[StrategyEvidenceResult, ...]


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

    # Bound the actual ASGI bytes, including chunked requests, before Pydantic
    # decodes the untrusted snapshot.  The evidence route is read-only, but a
    # bounded body keeps CPU and memory work predictable for every caller.
    @app.middleware("http")
    async def bounded_request_body(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method != "POST" or request.url.path != "/api/v1/research/strategy-evidence":
            return await call_next(request)
        lengths = request.headers.getlist("content-length")
        if len(lengths) > 1 or (
            lengths and (len(lengths[0]) > 6 or not lengths[0].isdigit() or int(lengths[0]) > MAX_RESEARCH_BODY_BYTES)
        ):
            return JSONResponse({"detail": "request_too_large_or_invalid"}, status_code=413)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_RESEARCH_BODY_BYTES:
                return JSONResponse({"detail": "request_too_large_or_invalid"}, status_code=413)
        request._body = bytes(body)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": "invalid_request"}, status_code=422)

    @app.exception_handler(ValueError)
    async def invalid_value(_request: Request, _error: ValueError) -> JSONResponse:
        return JSONResponse({"detail": "invalid_request"}, status_code=422)

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
            last_price=None if event.last_price is None else float(event.last_price),
            bid_price=None if event.bid_price is None else float(event.bid_price),
            ask_price=None if event.ask_price is None else float(event.ask_price),
            event_time_ms=event.event_time_ms,
            received_at=event.received_at,
            age_seconds=age,
            exchange_lag_seconds=lag,
            partial=any(price is None for price in (event.last_price, event.bid_price, event.ask_price)),
        )

    @app.get(
        "/api/v1/market/{symbol}/provenance",
        response_model=MarketProvenanceResponse,
        responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def market_provenance(symbol: str) -> MarketProvenanceResponse:
        normalized = symbol.upper()
        if normalized not in symbols:
            raise HTTPException(404, "symbol is not configured")
        try:
            record = await engine.persisted_latest(normalized)
        except RuntimeError as error:
            raise HTTPException(503, "market provenance storage is unavailable") from error
        if record is None:
            raise HTTPException(404, "no persisted market observation")
        current = engine.latest(normalized)
        health = engine.supervisor.snapshot()
        live = (
            current is not None
            and current.received_at == record.received_at
            and health.state == "running"
            and health.market_data is not None
            and health.market_data.state == "connected"
            and monitor.is_fresh(current)
        )
        return MarketProvenanceResponse(
            symbol=record.symbol,
            last_price=None if record.last_price is None else float(record.last_price),
            bid_price=None if record.bid_price is None else float(record.bid_price),
            ask_price=None if record.ask_price is None else float(record.ask_price),
            event_time_ms=record.event_time_ms,
            received_at=record.received_at,
            source=record.source,
            live_observation=live,
            historical_only=not live,
        )

    @app.post(
        "/api/v1/research/strategy-evidence",
        response_model=StrategyEvidenceResponse,
        responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def strategy_evidence(request: StrategyEvidenceRequest) -> StrategyEvidenceResponse:
        """Evaluate deterministic strategy families as explicitly research-only evidence."""
        bars = tuple(
            Bar(
                timestamp=datetime.fromtimestamp(bar.timestamp_ms / 1000, UTC),
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
            )
            for bar in request.bars
        )
        snapshot = None if not bars else MarketSnapshot(bars=bars, funding_rate=request.funding_rate)
        newest_timestamp_ms = request.bars[-1].timestamp_ms if request.bars else None
        snapshot_status, snapshot_age_ms = _snapshot_status(newest_timestamp_ms, request.interval)
        market = Market.SPOT if request.market == "spot" else Market.LINEAR
        results = evaluate_strategy_families(snapshot, market, stale=snapshot_status == "stale")
        return StrategyEvidenceResponse(
            symbol=request.symbol,
            market=request.market,
            interval=request.interval,
            snapshot_status=snapshot_status,
            snapshot_age_ms=snapshot_age_ms,
            newest_timestamp_ms=newest_timestamp_ms,
            strategy_count=len(results),
            strategies=tuple(
                StrategyEvidenceResult(
                    strategy_id=item.strategy_id,
                    name=item.name,
                    version=item.version,
                    source_repository=item.source_repository,
                    source_commit=item.source_commit,
                    license=item.license,
                    lifecycle_status=item.lifecycle_status,
                    validation_status=item.validation_status,
                    supported_markets=item.supported_markets,
                    ready=item.ready,
                    research_target_exposure=item.research_target_exposure,
                    reason=item.reason,
                    features=item.features,
                )
                for item in results
            ),
        )

    return app


def _snapshot_status(
    newest_timestamp_ms: int | None, interval: str
) -> tuple[Literal["fresh", "stale", "empty"], int | None]:
    if newest_timestamp_ms is None:
        return "empty", None
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    age_ms = now_ms - newest_timestamp_ms
    interval_ms = (
        int(interval) * 60_000
        if interval.isdigit()
        else {
            "D": 86_400_000,
            "W": 604_800_000,
            "M": 2_592_000_000,
        }[interval]
    )
    status = "fresh" if -5_000 <= age_ms <= 2 * interval_ms else "stale"
    return status, max(0, age_ms)
