"""Adapt validated strategy selections to account-free portfolio proposals."""

from __future__ import annotations

from typing import cast

from quant_portfolio import TargetProposal
from quant_strategies import Signal

from .strategy_selector import MAX_EVALUATION_AGE_MS, SelectionDecision


def selection_to_proposal(symbol: str, decision: SelectionDecision) -> TargetProposal | None:
    """Create a bounded target proposal, or preserve an explicit selector abstention.

    This adapter carries only a strategy signal and its evaluation provenance. It
    accepts no account or exchange state and cannot create an order.
    """

    if type(decision) is not SelectionDecision:
        raise ValueError("invalid_selection_decision")
    if decision.kind == "abstain":
        return None
    if decision.kind not in {"selected", "retained"}:
        raise ValueError("invalid_selection_decision")
    confidence = decision.confidence
    if (
        type(decision.strategy_id) is not str
        or not decision.strategy_id
        or type(decision.version) is not str
        or not decision.version
        or type(decision.signal) is not Signal
        or not decision.signal.ready
        or decision.signal.strategy_id != decision.strategy_id
        or type(confidence) not in {int, float}
        or type(decision.evaluation_ref) is not str
        or type(decision.evaluated_at_ms) is not int
        or decision.evaluated_at_ms <= 0
    ):
        raise ValueError("incomplete_selection_decision")
    return TargetProposal(
        symbol=symbol,
        strategy_id=decision.strategy_id,
        strategy_version=decision.version,
        target_exposure=decision.signal.target_exposure,
        confidence=cast(float, confidence),
        evidence_ref=decision.evaluation_ref,
        expires_at_ms=decision.evaluated_at_ms + MAX_EVALUATION_AGE_MS,
    )
