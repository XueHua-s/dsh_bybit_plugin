from dataclasses import replace
from datetime import UTC, datetime, timedelta

from quant_engine.strategy_registry import StrategyRegistry
from quant_engine.strategy_selector import (
    Regime,
    SelectionCandidate,
    SelectionState,
    detect_regime,
    select_strategy,
)
from quant_strategies import Bar, MarketSnapshot
from quant_strategies.families import DEFAULT_CONFIGS, STRATEGY_METADATA
from quant_strategies.metadata import LifecycleStatus, ValidationStatus


def snapshot(count: int = 80, *, volatile: bool = False) -> MarketSnapshot:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = tuple(100.0 + index if not volatile else 100.0 * (1.08 if index % 2 else 0.92) for index in range(count))
    return MarketSnapshot(
        tuple(
            Bar(start + timedelta(minutes=index), close, close + 1, close - 1, close, 10.0)
            for index, close in enumerate(closes)
        )
    )


def approved_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    for metadata in STRATEGY_METADATA[:2]:
        registry.register(
            replace(
                metadata,
                validation_status=ValidationStatus.PAPER_PASSED,
                current_status=LifecycleStatus.APPROVED,
                approval_ref=f"review-{metadata.strategy_id}",
            ),
            DEFAULT_CONFIGS[metadata.strategy_id],
        )
    return registry


def candidate(
    strategy_id: str,
    score: float,
    *,
    regimes: tuple[Regime, ...] = (Regime.TREND_UP,),
    evaluated_at_ms: int = 100_000,
    out_of_sample_samples: int = 64,
) -> SelectionCandidate:
    return SelectionCandidate(
        strategy_id,
        "0.1.0",
        score,
        0.8,
        2.0,
        f"evaluation://{strategy_id}/0.1.0",
        evaluated_at_ms,
        out_of_sample_samples,
        regimes,
    )


def test_regime_detector_is_bounded_and_fail_closed() -> None:
    up = detect_regime(snapshot())
    assert up.regime is Regime.TREND_UP
    assert up.trend_score is not None and 0.0 < up.trend_score <= 1.0
    assert detect_regime(snapshot(10)).regime is Regime.UNKNOWN
    assert detect_regime(snapshot(80, volatile=True)).regime is Regime.VOLATILE


def test_selector_requires_approved_paper_validated_records() -> None:
    registry = StrategyRegistry()
    metadata = STRATEGY_METADATA[0]
    registry.register(metadata, DEFAULT_CONFIGS[metadata.strategy_id])
    result = select_strategy(snapshot(), (candidate(metadata.strategy_id, 1.0),), registry, 100_000)
    assert result.kind == "abstain"
    assert result.reason == "no_validated_strategy"


def test_selector_scores_candidates_and_retains_with_hysteresis() -> None:
    registry = approved_registry()
    first = select_strategy(
        snapshot(),
        (candidate("sma_cross", 0.7), candidate("ema_cross", 0.6)),
        registry,
        100_000,
    )
    assert first.kind == "selected"
    assert first.strategy_id == "sma_cross"
    assert first.evaluation_ref == "evaluation://sma_cross/0.1.0"
    assert first.signal is not None and first.signal.ready
    state = SelectionState(first.strategy_id or "", first.version or "", 100_000, first.score or 0.0)
    retained = select_strategy(
        snapshot(),
        (candidate("sma_cross", 0.7), candidate("ema_cross", 0.72)),
        registry,
        100_001,
        previous=state,
    )
    assert retained.kind == "retained"
    assert retained.strategy_id == "sma_cross"
    switched = select_strategy(
        snapshot(),
        (candidate("sma_cross", 0.7), candidate("ema_cross", 0.9)),
        registry,
        100_000 + 15 * 60_000 + 1,
        previous=state,
    )
    assert switched.kind == "selected"
    assert switched.strategy_id == "ema_cross"


def test_selector_filters_regime_and_negative_scores() -> None:
    registry = approved_registry()
    result = select_strategy(
        snapshot(),
        (candidate("sma_cross", 0.5, regimes=(Regime.RANGE,)), candidate("ema_cross", -1.0)),
        registry,
        100_000,
    )
    assert result.kind == "abstain"
    assert result.reason == "score_below_minimum"


def test_selector_rejects_stale_future_and_small_oos_evidence() -> None:
    registry = approved_registry()
    now_ms = 1_800_000_000_000
    stale = candidate("sma_cross", 1.0, evaluated_at_ms=now_ms - 31 * 24 * 60 * 60 * 1000)
    result = select_strategy(snapshot(), (stale,), registry, now_ms)
    assert result.kind == "abstain"
    assert result.reason == "stale_evaluation_evidence"
    future = candidate("sma_cross", 1.0, evaluated_at_ms=now_ms + 1)
    assert select_strategy(snapshot(), (future,), registry, now_ms).reason == "stale_evaluation_evidence"

    try:
        candidate("sma_cross", 1.0, out_of_sample_samples=29)
    except ValueError as error:
        assert str(error) == "invalid_evaluation_provenance"
    else:
        raise AssertionError("small OOS samples must be rejected")
