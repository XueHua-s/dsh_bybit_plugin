from quant_strategies.indicators import adx, atr, donchian, ema, rsi, sma, stddev


def test_rolling_indicators_are_deterministic() -> None:
    closes = (1.0, 2.0, 3.0, 4.0, 5.0)
    highs = (2.0, 3.0, 4.0, 5.0, 6.0)
    lows = (0.5, 1.5, 2.5, 3.5, 4.5)
    assert sma(closes, 3) == 4.0
    assert ema(closes, 3) == 4.0
    deviation = stddev(closes, 3)
    assert deviation is not None and deviation > 0
    assert rsi(closes, 2) == 100.0
    assert atr(highs, lows, closes, 2) == 2.0
    assert donchian(highs, lows, 3) == (5.0, 1.5)
    strength, plus_di, minus_di = adx(highs, lows, closes, 2) or (0.0, 0.0, 0.0)
    assert strength == 100.0
    assert plus_di > minus_di == 0.0


def test_indicators_report_insufficient_history() -> None:
    assert sma((1.0, 2.0), 3) is None
    assert ema((1.0, 2.0), 3) is None
    assert stddev((1.0, 2.0), 3) is None
    assert rsi((1.0, 2.0), 2) is None
