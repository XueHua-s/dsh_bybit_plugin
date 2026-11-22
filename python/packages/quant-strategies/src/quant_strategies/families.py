"""Built-in target-exposure strategies with a single fail-closed evaluator."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Final

from .alpha158 import factors
from .indicators import adx, atr, donchian, ema, rsi, sma, stddev
from .metadata import ConfigField, LifecycleStatus, Market, StrategyMetadata, ValidationStatus
from .models import MarketSnapshot, Signal

DEFAULT_CONFIGS: Final[dict[str, dict[str, int | float]]] = {
    "sma_cross": {"fast": 10, "slow": 30, "max_exposure": 1.0},
    "ema_cross": {"fast": 10, "slow": 30, "max_exposure": 1.0},
    "donchian_breakout": {"period": 20, "max_exposure": 1.0},
    "adx_trend": {"period": 14, "threshold": 20.0, "max_exposure": 1.0},
    "ts_momentum": {"period": 20, "max_exposure": 1.0},
    "bollinger_reversion": {"period": 20, "entry_z": 2.0, "max_exposure": 1.0},
    "zscore_reversion": {"period": 20, "entry_z": 1.5, "max_exposure": 1.0},
    "rsi_reversion": {"period": 14, "entry_low": 30.0, "entry_high": 70.0, "max_exposure": 1.0},
    "atr_breakout": {"period": 14, "multiplier": 1.0, "max_exposure": 1.0},
    "funding_carry": {"threshold": 0.0001, "max_exposure": 1.0},
    "alpha158_subset": {"period": 5, "max_exposure": 1.0},
}

_BOUNDS: Final[dict[str, tuple[int | float, int | float]]] = {
    "fast": (2, 100),
    "slow": (3, 500),
    "period": (2, 500),
    "threshold": (0.00001, 60.0),
    "entry_z": (0.5, 5.0),
    "entry_low": (5.0, 45.0),
    "entry_high": (55.0, 95.0),
    "multiplier": (0.25, 5.0),
    "max_exposure": (0.0, 1.0),
}


def _metadata(strategy_id: str) -> StrategyMetadata:
    config = DEFAULT_CONFIGS[strategy_id]
    schema_fields = []
    for name, value in config.items():
        minimum, maximum = _BOUNDS[name]
        if strategy_id == "funding_carry" and name == "threshold":
            maximum = 0.1
        schema_fields.append(
            ConfigField(name, "integer" if type(value) is int else "number", minimum=minimum, maximum=maximum)
        )
    schema = tuple(schema_fields)
    return StrategyMetadata(
        strategy_id,
        strategy_id.replace("_", " ").title(),
        "0.1.0",
        "internal://bybit-quant",
        None,
        "MIT",
        (Market.LINEAR,) if strategy_id == "funding_carry" else (Market.SPOT, Market.LINEAR),
        ("ALL",),
        ("1m", "5m", "15m", "1h", "4h", "1d"),
        ("close", "high", "low"),
        30,
        schema,
        ("deterministic rule emits a signed target exposure",),
        ("rule returns target exposure to zero or changes direction",),
        "signed portfolio weight bounded by max_exposure in [-1, 1]",
        ("independent account-aware risk approval required",),
        (),
        ValidationStatus.NOT_STARTED,
        LifecycleStatus.RESEARCH,
    )


STRATEGY_METADATA: Final[tuple[StrategyMetadata, ...]] = tuple(_metadata(key) for key in DEFAULT_CONFIGS)
STRATEGIES: Final[tuple[str, ...]] = tuple(DEFAULT_CONFIGS)


def evaluate(strategy_id: str, snapshot: MarketSnapshot, config: Mapping[str, object] | None = None) -> Signal:
    """Evaluate one strategy and return only a bounded signed target exposure."""
    if strategy_id not in DEFAULT_CONFIGS:
        raise ValueError("unknown_strategy")
    settings = _normalize_config(strategy_id, {} if config is None else config)
    closes, highs, lows = (
        tuple(b.close for b in snapshot.bars),
        tuple(b.high for b in snapshot.bars),
        tuple(b.low for b in snapshot.bars),
    )
    cap = float(settings["max_exposure"])
    period = int(settings.get("period", 20))
    if strategy_id in {"sma_cross", "ema_cross"}:
        fast, slow = int(settings["fast"]), int(settings["slow"])
        average = sma if strategy_id == "sma_cross" else ema
        fast_value, slow_value = average(closes, fast), average(closes, slow)
        if fast_value is None or slow_value is None:
            return _not_ready(strategy_id, slow)
        return _signal(
            strategy_id,
            _sign(fast_value - slow_value),
            "trend_cross",
            cap,
            (("fast", fast_value), ("slow", slow_value)),
        )
    if strategy_id == "donchian_breakout":
        channel = donchian(highs, lows, period)
        if channel is None:
            return _not_ready(strategy_id, period + 1)
        exposure = 1.0 if closes[-1] > channel[0] else -1.0 if closes[-1] < channel[1] else 0.0
        return _signal(strategy_id, exposure, "channel_breakout", cap)
    if strategy_id == "adx_trend":
        state = adx(highs, lows, closes, period)
        if state is None:
            return _not_ready(strategy_id, period * 2 + 1)
        strength, plus, minus = state
        exposure = _sign(plus - minus) if strength >= float(settings["threshold"]) else 0.0
        return _signal(strategy_id, exposure, "adx_filter", cap, (("adx", strength),))
    if strategy_id == "ts_momentum":
        if len(closes) <= period:
            return _not_ready(strategy_id, period + 1)
        return _signal(strategy_id, _sign(closes[-1] / closes[-period - 1] - 1.0), "time_series_momentum", cap)
    if strategy_id in {"bollinger_reversion", "zscore_reversion"}:
        average, deviation = sma(closes, period), stddev(closes, period)
        if average is None or deviation is None or deviation == 0:
            return _not_ready(strategy_id, period)
        zscore = (closes[-1] - average) / deviation
        exposure = 0.0 if abs(zscore) < float(settings["entry_z"]) else -_sign(zscore)
        return _signal(strategy_id, exposure, strategy_id, cap, (("zscore", zscore),))
    if strategy_id == "rsi_reversion":
        value = rsi(closes, period)
        if value is None:
            return _not_ready(strategy_id, period + 1)
        exposure = (
            1.0 if value <= float(settings["entry_low"]) else -1.0 if value >= float(settings["entry_high"]) else 0.0
        )
        return _signal(strategy_id, exposure, "rsi_reversion", cap, (("rsi", value),))
    if strategy_id == "atr_breakout":
        value = atr(highs, lows, closes, period)
        if value is None:
            return _not_ready(strategy_id, period + 1)
        move = closes[-1] - closes[-2]
        return _signal(
            strategy_id,
            _sign(move) if abs(move) > value * float(settings["multiplier"]) else 0.0,
            "atr_breakout",
            cap,
            (("atr", value),),
        )
    if strategy_id == "funding_carry":
        rate = snapshot.funding_rate
        if rate is None:
            return _not_ready(strategy_id, 1)
        exposure = -_sign(rate) if abs(rate) >= float(settings["threshold"]) else 0.0
        return _signal(strategy_id, exposure, "funding_carry", cap, (("funding_rate", rate),))
    result = factors(snapshot, period)
    if result is None:
        return _not_ready(strategy_id, period + 1)
    return _signal(strategy_id, _clip((1.0 - result[0][1] + result[3][1] - 0.5) / 2.0), "alpha158_subset", cap, result)


def _normalize_config(strategy_id: str, supplied: Mapping[str, object]) -> dict[str, int | float]:
    if not isinstance(supplied, Mapping):
        raise TypeError("invalid_strategy_config")
    normalized = dict(DEFAULT_CONFIGS[strategy_id])
    for name, value in supplied.items():
        if type(name) is not str or name not in normalized:
            raise ValueError("invalid_strategy_config")
        if type(value) is int or type(value) is float:
            normalized[name] = value
        else:
            raise ValueError("invalid_strategy_config")
    for name, value in normalized.items():
        minimum, maximum = _BOUNDS[name]
        if type(value) not in {int, float} or not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError("invalid_strategy_config")
    if strategy_id in {"sma_cross", "ema_cross"} and normalized["fast"] >= normalized["slow"]:
        raise ValueError("invalid_strategy_config")
    if strategy_id == "funding_carry" and normalized["threshold"] > 0.1:
        raise ValueError("invalid_strategy_config")
    if strategy_id == "rsi_reversion" and normalized["entry_low"] >= normalized["entry_high"]:
        raise ValueError("invalid_strategy_config")
    return normalized


def _signal(
    strategy_id: str, exposure: float, reason: str, cap: float, features: tuple[tuple[str, float], ...] = ()
) -> Signal:
    return Signal(strategy_id, _clip(exposure) * cap, True, reason, features)


def _not_ready(strategy_id: str, warmup: int) -> Signal:
    return Signal(strategy_id, 0.0, False, f"warmup_{warmup}")


def _clip(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _sign(value: float) -> float:
    return 1.0 if value > 0 else -1.0 if value < 0 else 0.0
