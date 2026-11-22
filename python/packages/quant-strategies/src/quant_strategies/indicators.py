"""Validated rolling indicators used by the built-in strategy families."""

from __future__ import annotations

from math import sqrt
from statistics import mean


def _window(values: tuple[float, ...], period: int) -> tuple[float, ...] | None:
    if period < 1 or len(values) < period:
        return None
    return values[-period:]


def sma(values: tuple[float, ...], period: int) -> float | None:
    window = _window(values, period)
    return None if window is None else mean(window)


def ema(values: tuple[float, ...], period: int) -> float | None:
    if period < 1 or len(values) < period:
        return None
    value = mean(values[:period])
    alpha = 2.0 / (period + 1.0)
    for item in values[period:]:
        value = alpha * item + (1.0 - alpha) * value
    return value


def stddev(values: tuple[float, ...], period: int) -> float | None:
    window = _window(values, period)
    if window is None:
        return None
    average = mean(window)
    return sqrt(mean((item - average) ** 2 for item in window))


def rsi(values: tuple[float, ...], period: int) -> float | None:
    if period < 1 or len(values) <= period:
        return None
    gains = [max(values[index] - values[index - 1], 0.0) for index in range(1, period + 1)]
    losses = [max(values[index - 1] - values[index], 0.0) for index in range(1, period + 1)]
    average_gain = mean(gains)
    average_loss = mean(losses)
    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        average_gain = (average_gain * (period - 1) + max(change, 0.0)) / period
        average_loss = (average_loss * (period - 1) + max(-change, 0.0)) / period
    return 100.0 if average_loss == 0 else 100.0 - 100.0 / (1.0 + average_gain / average_loss)


def atr(highs: tuple[float, ...], lows: tuple[float, ...], closes: tuple[float, ...], period: int) -> float | None:
    if period < 1 or len(closes) <= period:
        return None
    true_ranges = [highs[0] - lows[0]]
    true_ranges.extend(
        max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1]))
        for index in range(1, len(closes))
    )
    value = mean(true_ranges[1 : period + 1])
    for item in true_ranges[period + 1 :]:
        value = (value * (period - 1) + item) / period
    return value


def donchian(highs: tuple[float, ...], lows: tuple[float, ...], period: int) -> tuple[float, float] | None:
    if period < 1 or len(highs) <= period:
        return None
    return max(highs[-period - 1 : -1]), min(lows[-period - 1 : -1])


def adx(
    highs: tuple[float, ...], lows: tuple[float, ...], closes: tuple[float, ...], period: int
) -> tuple[float, float, float] | None:
    if period < 1 or len(closes) < period * 2 + 1:
        return None
    true_ranges: list[float] = []
    plus: list[float] = []
    minus: list[float] = []
    for index in range(1, len(closes)):
        up = highs[index] - highs[index - 1]
        down = lows[index - 1] - lows[index]
        plus.append(up if up > down and up > 0 else 0.0)
        minus.append(down if down > up and down > 0 else 0.0)
        true_ranges.append(
            max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1]))
        )
    atr_value, plus_value, minus_value = sum(true_ranges[:period]), sum(plus[:period]), sum(minus[:period])
    dx: list[float] = []
    plus_di = minus_di = 0.0
    for index in range(period, len(true_ranges)):
        if index > period:
            atr_value = atr_value - atr_value / period + true_ranges[index]
            plus_value = plus_value - plus_value / period + plus[index]
            minus_value = minus_value - minus_value / period + minus[index]
        plus_di = 100.0 * plus_value / atr_value if atr_value else 0.0
        minus_di = 100.0 * minus_value / atr_value if atr_value else 0.0
        denominator = plus_di + minus_di
        dx.append(100.0 * abs(plus_di - minus_di) / denominator if denominator else 0.0)
    if len(dx) < period:
        return None
    adx_value = mean(dx[:period])
    for item in dx[period:]:
        adx_value = (adx_value * (period - 1) + item) / period
    return adx_value, plus_di, minus_di
