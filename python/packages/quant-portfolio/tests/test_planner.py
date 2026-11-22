import math

from quant_portfolio import PortfolioPolicy, PositionExposure, TargetProposal, plan_targets


def proposal(symbol: str, target: float | None, *, confidence: float = 0.9, expires: int = 2_000) -> TargetProposal:
    return TargetProposal(symbol, "sma_cross", "0.1.0", target, confidence, f"eval://{symbol}", expires)


def test_scales_gross_exposure_and_preserves_unmentioned_positions() -> None:
    plan = plan_targets(
        (proposal("BTCUSDT", 0.8), proposal("ETHUSDT", 0.6)),
        (PositionExposure("SOLUSDT", 0.2),),
        PortfolioPolicy(max_gross_exposure=1.0, max_single_exposure=0.8, max_turnover=2.0, now_ms=1),
    )
    assert plan.gross_exposure <= 1.0
    assert plan.gross_exposure > 0.999999999
    assert {item.symbol: item.exposure for item in plan.targets}["SOLUSDT"] == 0.2
    assert plan.turnover > 0


def test_reversal_is_two_phase_and_warns_for_independent_recheck() -> None:
    plan = plan_targets(
        (proposal("BTCUSDT", -0.4),),
        (PositionExposure("BTCUSDT", 0.3),),
        PortfolioPolicy(max_turnover=1.0, now_ms=1),
    )
    transition = plan.transitions[0]
    assert transition.reason == "reverse_requires_recheck"
    assert [step.phase for step in transition.steps] == ["reduce", "increase"]
    assert transition.steps[0].target_exposure == 0.0
    assert transition.steps[1].target_exposure == -0.4
    assert plan.warnings == ("BTCUSDT: reversal requires independent risk recheck between phases",)


def test_explicit_zero_target_flattens_and_is_not_confused_with_abstention() -> None:
    plan = plan_targets(
        (proposal("BTCUSDT", 0.0),),
        (PositionExposure("BTCUSDT", 0.3),),
        PortfolioPolicy(now_ms=1),
    )
    assert plan.targets == ()
    assert plan.transitions[0].target_exposure == 0.0
    assert plan.transitions[0].reason == "rebalance"
    assert plan.transitions[0].steps[0].phase == "reduce"


def test_expired_or_low_confidence_proposals_abstain_without_flattening() -> None:
    plan = plan_targets(
        (proposal("BTCUSDT", -0.4, confidence=0.2, expires=1),),
        (PositionExposure("BTCUSDT", 0.3),),
        PortfolioPolicy(now_ms=1),
    )
    assert plan.abstained_symbols == ("BTCUSDT",)
    assert plan.targets == (PositionExposure("BTCUSDT", 0.3),)
    assert plan.transitions[0].reason == "abstain"


def test_valid_none_target_is_audited_as_hold() -> None:
    plan = plan_targets(
        (proposal("BTCUSDT", None),),
        (),
        PortfolioPolicy(now_ms=1),
    )
    assert len(plan.transitions) == 1
    assert plan.transitions[0].reason == "hold"
    assert plan.transitions[0].strategy_id == "sma_cross"


def test_turnover_limit_scales_the_requested_change() -> None:
    plan = plan_targets(
        (proposal("BTCUSDT", 0.8),),
        (PositionExposure("BTCUSDT", 0.2),),
        PortfolioPolicy(max_single_exposure=0.8, max_turnover=0.1, now_ms=1),
    )
    assert plan.turnover <= 0.1
    assert abs(plan.targets[0].exposure - 0.3) < 1e-12
    assert "target_changes_scaled_to_turnover_limit" in plan.warnings


def test_gross_scaling_never_changes_unproposed_positions() -> None:
    plan = plan_targets(
        (proposal("BTCUSDT", 0.8),),
        (PositionExposure("ETHUSDT", 0.4),),
        PortfolioPolicy(max_gross_exposure=0.6, max_single_exposure=0.6, max_turnover=2.0, now_ms=1),
    )
    targets = {item.symbol: item.exposure for item in plan.targets}
    assert targets["ETHUSDT"] == 0.4
    assert abs(targets["BTCUSDT"] - 0.2) < 1e-12
    assert plan.gross_exposure <= 0.6


def test_turnover_cap_reports_existing_exposure_that_still_exceeds_limits() -> None:
    plan = plan_targets(
        (proposal("BTCUSDT", 0.0),),
        (PositionExposure("BTCUSDT", 0.8),),
        PortfolioPolicy(max_gross_exposure=0.5, max_single_exposure=0.5, max_turnover=0.1, now_ms=1),
    )
    assert len(plan.targets) == 1
    assert math.isclose(plan.targets[0].exposure, 0.7, abs_tol=1e-12)
    assert "planned_exposure_remains_above_gross_limit" in plan.warnings
    assert "BTCUSDT: planned exposure remains above single-position limit" in plan.warnings


def test_duplicate_symbols_fail_closed() -> None:
    policy = PortfolioPolicy(now_ms=1)
    try:
        plan_targets((proposal("BTCUSDT", 0.1), proposal("BTCUSDT", 0.2)), (), policy)
    except ValueError as error:
        assert str(error) == "duplicate_target_symbol"
    else:
        raise AssertionError("duplicate targets must be rejected")


def test_bad_symbols_and_oversized_universe_fail_closed() -> None:
    try:
        PositionExposure("btc-usdt", 0.1)
    except ValueError as error:
        assert str(error) == "invalid_position_symbol"
    else:
        raise AssertionError("symbols must already be canonical")

    policy = PortfolioPolicy(now_ms=1)
    oversized = tuple(PositionExposure(f"S{index}", 0.0) for index in range(101))
    try:
        plan_targets((), oversized, policy)
    except ValueError as error:
        assert str(error) == "portfolio_symbol_limit_exceeded"
    else:
        raise AssertionError("unbounded input must be rejected")
