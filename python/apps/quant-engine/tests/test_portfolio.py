from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from quant_engine.portfolio import selection_to_proposal
from quant_engine.strategy_registry import StrategyRegistry
from quant_engine.strategy_selector import (
    Regime,
    SelectionCandidate,
    SelectionDecision,
    SelectionState,
    select_strategy,
)
from quant_strategies import Bar, MarketSnapshot
from quant_strategies.families import DEFAULT_CONFIGS, STRATEGY_METADATA
from quant_strategies.metadata import LifecycleStatus, ValidationStatus


def _snapshot() -> MarketSnapshot:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = tuple(100.0 + index for index in range(80))
    return MarketSnapshot(
        tuple(
            Bar(start + timedelta(minutes=index), close, close + 1, close - 1, close, 10.0)
            for index, close in enumerate(closes)
        )
    )


def _registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    metadata = STRATEGY_METADATA[0]
    registry.register(
        replace(
            metadata,
            validation_status=ValidationStatus.PAPER_PASSED,
            current_status=LifecycleStatus.APPROVED,
            approval_ref="review-sma-cross",
        ),
        DEFAULT_CONFIGS[metadata.strategy_id],
    )
    return registry


def _decision(*, previous: SelectionState | None = None) -> SelectionDecision:
    candidate = SelectionCandidate(
        "sma_cross",
        "0.1.0",
        0.7,
        0.8,
        2.0,
        "evaluation://sma_cross/0.1.0",
        100_000,
        64,
        (Regime.TREND_UP,),
    )
    return select_strategy(_snapshot(), (candidate,), _registry(), 100_000, previous=previous)


def test_selected_strategy_becomes_provenanced_target_proposal() -> None:
    decision = _decision()
    proposal = selection_to_proposal("BTCUSDT", decision)
    assert proposal is not None
    assert proposal.symbol == "BTCUSDT"
    assert proposal.strategy_id == "sma_cross"
    assert proposal.confidence == 0.8
    assert proposal.evidence_ref == "evaluation://sma_cross/0.1.0"
    assert proposal.expires_at_ms == 100_000 + 30 * 24 * 60 * 60 * 1000
    assert decision.signal is not None
    assert proposal.target_exposure == decision.signal.target_exposure


def test_retained_strategy_remains_eligible_for_portfolio_planning() -> None:
    previous = SelectionState("sma_cross", "0.1.0", 99_999, 0.7)
    decision = _decision(previous=previous)
    assert decision.kind == "retained"
    assert selection_to_proposal("BTCUSDT", decision) is not None


def test_selector_abstention_creates_no_target_proposal() -> None:
    decision = select_strategy(_snapshot(), (), _registry(), 100_000)
    assert decision.kind == "abstain"
    assert selection_to_proposal("BTCUSDT", decision) is None


def test_incomplete_selected_decision_fails_closed() -> None:
    decision = _decision()
    with pytest.raises(ValueError, match="incomplete_selection_decision"):
        selection_to_proposal("BTCUSDT", replace(decision, signal=None))
