"""Deterministic target allocation and non-reversing transition planning."""

from __future__ import annotations

from collections.abc import Iterable
from math import fsum

from .models import (
    PortfolioPlan,
    PortfolioPolicy,
    PositionExposure,
    TargetProposal,
    Transition,
    TransitionStep,
)

MAX_PORTFOLIO_SYMBOLS = 100
GROSS_SCALE_EPSILON = 1e-12


def plan_targets(
    proposals: Iterable[TargetProposal],
    current: Iterable[PositionExposure],
    policy: PortfolioPolicy,
) -> PortfolioPlan:
    """Build bounded targets while keeping proposal, account and execution concerns separate.

    A missing proposal holds an existing position. Low-confidence or expired proposals
    abstain. Aggregate scaling preserves relative direction, and a sign reversal is
    represented as a reduce-to-zero step followed by a second increase step that the
    execution authority must independently revalidate.
    """

    current_by_symbol = _unique_positions(current)
    proposal_by_symbol, abstained = _validated_proposals(proposals, policy)
    explicit: dict[str, float] = {}
    for symbol, proposal in proposal_by_symbol.items():
        if symbol not in abstained and proposal.target_exposure is not None:
            explicit[symbol] = max(
                -policy.max_single_exposure,
                min(policy.max_single_exposure, proposal.target_exposure),
            )

    held = {symbol: position.exposure for symbol, position in current_by_symbol.items() if symbol not in explicit}
    held_gross = fsum(abs(value) for value in held.values())
    allocation_capacity = max(0.0, policy.max_gross_exposure - held_gross)
    proposed_gross = fsum(abs(value) for value in explicit.values())
    gross_scale = min(1.0, allocation_capacity / proposed_gross) if proposed_gross > 0 else 1.0
    if gross_scale < 1.0:
        # Keep floating-point summation from crossing a hard exposure ceiling.
        gross_scale *= 1.0 - GROSS_SCALE_EPSILON
    targets = {**held, **{symbol: value * gross_scale for symbol, value in explicit.items()}}
    # The turnover ceiling limits this plan's total target movement. Interpolating
    # from current to capped targets preserves the gross cap when the current book
    # is already within policy, and prevents a sudden multi-symbol rebalance.
    raw_turnover = fsum(
        abs(value - current_by_symbol.get(symbol, PositionExposure(symbol, 0.0)).exposure)
        for symbol, value in targets.items()
    )
    turnover_scale = min(1.0, policy.max_turnover / raw_turnover) if raw_turnover > 0 else 1.0
    if turnover_scale < 1.0:
        targets = {
            symbol: current_by_symbol.get(symbol, PositionExposure(symbol, 0.0)).exposure
            + (target - current_by_symbol.get(symbol, PositionExposure(symbol, 0.0)).exposure) * turnover_scale
            for symbol, target in targets.items()
        }
    planned_targets = dict(targets)
    target_records = tuple(
        PositionExposure(symbol, planned_targets[symbol])
        for symbol in sorted(planned_targets)
        if abs(planned_targets[symbol]) > 1e-12
    )
    transitions: list[Transition] = []
    turnover = 0.0
    warnings: list[str] = []
    if held_gross > policy.max_gross_exposure:
        warnings.append("current_unproposed_exposure_exceeds_gross_limit; new exposure is blocked")
    planned_gross = fsum(abs(value) for value in targets.values())
    if planned_gross > policy.max_gross_exposure:
        warnings.append("planned_exposure_remains_above_gross_limit")
    warnings.extend(
        f"{symbol}: planned exposure remains above single-position limit"
        for symbol, exposure in targets.items()
        if abs(exposure) > policy.max_single_exposure
    )
    if gross_scale < 1.0:
        warnings.append("proposed_exposure_scaled_to_gross_limit")
    if turnover_scale < 1.0:
        warnings.append("target_changes_scaled_to_turnover_limit")
    symbols = sorted(set(current_by_symbol) | set(planned_targets) | set(proposal_by_symbol))
    for symbol in symbols:
        current_exposure = current_by_symbol.get(symbol, PositionExposure(symbol, 0.0)).exposure
        target_exposure = planned_targets.get(symbol, current_exposure)
        delta = target_exposure - current_exposure
        turnover += abs(delta)
        proposal = proposal_by_symbol.get(symbol)
        if abs(delta) <= 1e-12:
            transitions.append(
                Transition(
                    symbol,
                    current_exposure,
                    target_exposure,
                    _proposal_target(proposal),
                    (TransitionStep(target_exposure, 0.0, "hold"),),
                    "abstain" if symbol in abstained else "hold",
                    _strategy_id(proposal),
                    _evidence(proposal),
                )
            )
            continue
        if current_exposure * target_exposure < 0:
            transitions.append(
                Transition(
                    symbol,
                    current_exposure,
                    target_exposure,
                    _proposal_target(proposal),
                    (
                        TransitionStep(0.0, -current_exposure, "reduce"),
                        TransitionStep(target_exposure, target_exposure, "increase"),
                    ),
                    "reverse_requires_recheck",
                    _strategy_id(proposal),
                    _evidence(proposal),
                )
            )
            warnings.append(f"{symbol}: reversal requires independent risk recheck between phases")
        else:
            phase = "increase" if abs(target_exposure) > abs(current_exposure) else "reduce"
            transitions.append(
                Transition(
                    symbol,
                    current_exposure,
                    target_exposure,
                    _proposal_target(proposal),
                    (TransitionStep(target_exposure, delta, phase),),
                    "rebalance",
                    _strategy_id(proposal),
                    _evidence(proposal),
                )
            )
    return PortfolioPlan(
        target_records,
        tuple(transitions),
        fsum(abs(record.exposure) for record in target_records),
        round(turnover, 12),
        tuple(sorted(abstained)),
        tuple(warnings),
    )


def _unique_positions(values: Iterable[PositionExposure]) -> dict[str, PositionExposure]:
    result: dict[str, PositionExposure] = {}
    for value in values:
        if type(value) is not PositionExposure:
            raise ValueError("invalid_current_position")
        if len(result) >= MAX_PORTFOLIO_SYMBOLS:
            raise ValueError("portfolio_symbol_limit_exceeded")
        if value.symbol in result:
            raise ValueError("duplicate_current_symbol")
        result[value.symbol] = value
    return result


def _validated_proposals(
    values: Iterable[TargetProposal], policy: PortfolioPolicy
) -> tuple[dict[str, TargetProposal], set[str]]:
    result: dict[str, TargetProposal] = {}
    abstained: set[str] = set()
    for proposal in values:
        if type(proposal) is not TargetProposal:
            raise ValueError("invalid_target_proposal")
        if len(result) >= MAX_PORTFOLIO_SYMBOLS:
            raise ValueError("portfolio_symbol_limit_exceeded")
        if proposal.symbol in result:
            raise ValueError("duplicate_target_symbol")
        if proposal.expires_at_ms <= policy.now_ms or proposal.confidence < policy.minimum_confidence:
            abstained.add(proposal.symbol)
            result[proposal.symbol] = proposal
            continue
        result[proposal.symbol] = proposal
    return result, abstained


def _strategy_id(proposal: TargetProposal | None) -> str | None:
    return None if proposal is None else proposal.strategy_id


def _evidence(proposal: TargetProposal | None) -> str | None:
    return None if proposal is None else proposal.evidence_ref


def _proposal_target(proposal: TargetProposal | None) -> float | None:
    return None if proposal is None else proposal.target_exposure
