"""Immutable input and output contracts for deterministic strategy evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite


@dataclass(frozen=True, slots=True)
class Bar:
    """One oldest-first OHLCV bar with finite positive prices and nonnegative volume."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.timestamp, datetime)
            or self.timestamp.tzinfo is None
            or self.timestamp.utcoffset() is None
        ):
            raise ValueError("invalid_bar_timestamp")
        values = (self.open, self.high, self.low, self.close, self.volume)
        if any(type(value) not in {int, float} or not isfinite(value) for value in values):
            raise ValueError("invalid_bar_value")
        if min(self.open, self.high, self.low, self.close) <= 0 or self.volume < 0:
            raise ValueError("invalid_bar_range")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("invalid_bar_ohlc")


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """Bounded market window and optional funding rate; no account state is accepted."""

    bars: tuple[Bar, ...]
    funding_rate: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.bars, tuple) or not 1 <= len(self.bars) <= 4096:
            raise ValueError("empty_market_snapshot")
        if any(not isinstance(bar, Bar) for bar in self.bars):
            raise ValueError("invalid_market_snapshot")
        if any(left.timestamp >= right.timestamp for left, right in zip(self.bars, self.bars[1:])):
            raise ValueError("unordered_market_snapshot")
        if self.funding_rate is not None and (
            type(self.funding_rate) not in {int, float}
            or not isfinite(self.funding_rate)
            or abs(self.funding_rate) > 0.1
        ):
            raise ValueError("invalid_funding_rate")


@dataclass(frozen=True, slots=True)
class Signal:
    """Strategy result; target exposure is a bounded signed weight, never an order."""

    strategy_id: str
    target_exposure: float
    ready: bool
    reason: str
    features: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.target_exposure) not in {int, float}
            or not isfinite(self.target_exposure)
            or not -1.0 <= self.target_exposure <= 1.0
        ):
            raise ValueError("invalid_target_exposure")
        if not self.strategy_id or not self.reason:
            raise ValueError("invalid_signal_metadata")
        if not isinstance(self.features, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) not in {int, float}
            or not isfinite(item[1])
            for item in self.features
        ):
            raise ValueError("invalid_signal_feature")
