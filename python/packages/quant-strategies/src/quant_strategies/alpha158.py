"""Small, independently implemented Alpha158 factor subset attributed to Qlib."""

from __future__ import annotations

from .indicators import sma, stddev
from .models import MarketSnapshot

QLIB_SOURCE = "https://github.com/microsoft/qlib@54355232463878d2eebb91fe0ee5fa7fa1f5976c"


def factors(snapshot: MarketSnapshot, period: int = 5) -> tuple[tuple[str, float], ...] | None:
    """Return ROC, MA, STD, RSV and SUMP analogues without importing Qlib."""
    if period < 1 or len(snapshot.bars) <= period:
        return None
    closes = tuple(bar.close for bar in snapshot.bars)
    highs = tuple(bar.high for bar in snapshot.bars)
    lows = tuple(bar.low for bar in snapshot.bars)
    average, deviation = sma(closes, period), stddev(closes, period)
    if average is None or deviation is None:
        return None
    prior, high, low = closes[-period - 1], max(highs[-period:]), min(lows[-period:])
    changes = [closes[index] - closes[index - 1] for index in range(len(closes) - period, len(closes))]
    total_movement = sum(abs(change) for change in changes)
    return (
        (f"ROC{period}", prior / closes[-1]),
        (f"MA{period}", average / closes[-1]),
        (f"STD{period}", deviation / closes[-1]),
        (f"RSV{period}", (closes[-1] - low) / (high - low + 1e-12)),
        (f"SUMP{period}", sum(max(change, 0.0) for change in changes) / (total_movement + 1e-12)),
    )
