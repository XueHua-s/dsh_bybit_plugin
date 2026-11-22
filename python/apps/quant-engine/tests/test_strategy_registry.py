from dataclasses import replace

import pytest
from quant_engine.strategy_registry import (
    ConfigField,
    LifecycleStatus,
    Market,
    RegistryErrorCode,
    RegistryValidationError,
    StrategyMetadata,
    StrategyRegistry,
    ValidationStatus,
)


def metadata(**changes: object) -> StrategyMetadata:
    values: dict[str, object] = {
        "strategy_id": "ema_cross",
        "name": "EMA Crossover",
        "version": "1.0.0",
        "source_repository": "https://example.test/quant/ema-cross",
        "source_commit": "a" * 40,
        "license": "MIT",
        "supported_markets": (Market.LINEAR,),
        "supported_instruments": ("BTCUSDT",),
        "timeframes": ("5m", "1h"),
        "required_features": ("close", "ema_fast", "ema_slow"),
        "warmup_period": 200,
        "configuration_schema": (
            ConfigField("fast_period", "integer", minimum=2, maximum=100),
            ConfigField("slow_period", "integer", minimum=3, maximum=500),
            ConfigField("confirm", "boolean", required=False),
            ConfigField("mode", "enum", choices=("trend", "flat"), required=False),
        ),
        "entry_conditions": ("fast EMA crosses above slow EMA",),
        "exit_conditions": ("fast EMA crosses below slow EMA",),
        "target_exposure": "bounded signed portfolio weight in [-1, 1]",
        "risk_constraints": ("independent engine risk approval required",),
        "backtest_metrics": (("sharpe", 0.7), ("max_drawdown", 0.2)),
        "validation_status": ValidationStatus.NOT_STARTED,
        "current_status": LifecycleStatus.RESEARCH,
        "approval_ref": None,
    }
    values.update(changes)
    return StrategyMetadata(**values)  # type: ignore[arg-type]


def valid_config() -> dict[str, int | bool | str]:
    return {"fast_period": 12, "slow_period": 50, "confirm": True, "mode": "trend"}


def test_register_valid_definition_as_immutable_sorted_snapshot() -> None:
    registry = StrategyRegistry()
    config = valid_config()

    record = registry.register(metadata(), config)
    config["fast_period"] = 99

    assert record.configuration == (("confirm", True), ("fast_period", 12), ("mode", "trend"), ("slow_period", 50))
    assert registry.get("ema_cross", "1.0.0") == record


@pytest.mark.parametrize(
    "field,value",
    [
        ("strategy_id", "Bad ID"),
        ("name", "  "),
        ("version", "latest"),
        ("source_repository", "file:///tmp/untrusted"),
        ("source_repository", "https://user:password@example.test/repo"),
        ("source_repository", "https://[::1"),
        ("source_commit", "not-a-commit"),
        ("license", ""),
        ("supported_markets", ()),
        ("supported_markets", ("linear",)),
        ("supported_instruments", ("*",)),
        ("timeframes", ("0m",)),
        ("required_features", ("bad feature",)),
        ("warmup_period", True),
        ("warmup_period", 0),
        ("entry_conditions", ()),
        ("exit_conditions", ("",)),
        ("target_exposure", ""),
        ("risk_constraints", ()),
        ("backtest_metrics", (("sharpe", float("nan")),)),
        ("supported_instruments", tuple(f"X{index:03d}" for index in range(129))),
        ("configuration_schema", tuple(ConfigField(f"param_{index}", "integer") for index in range(129))),
        ("entry_conditions", tuple(f"rule {index}" for index in range(129))),
        ("backtest_metrics", tuple((f"metric_{index}", 1.0) for index in range(129))),
        ("current_status", LifecycleStatus.CANDIDATE),
        ("validation_status", "paper_passed"),
        ("current_status", "approved"),
    ],
)
def test_register_rejects_invalid_metadata(field: str, value: object) -> None:
    registry = StrategyRegistry()

    with pytest.raises(RegistryValidationError) as error:
        registry.register(metadata(**{field: value}), valid_config())

    assert error.value.code is RegistryErrorCode.INVALID_METADATA
    assert str(error.value) == RegistryErrorCode.INVALID_METADATA.value


@pytest.mark.parametrize(
    "configuration",
    [
        {"fast_period": 12},  # missing required slow_period
        {"fast_period": 12, "slow_period": 50, "unknown": 1},
        {"fast_period": True, "slow_period": 50},  # bool is not an integer config value
        {"fast_period": 12, "slow_period": 2},  # below minimum
        {"fast_period": 12, "slow_period": 501},  # above maximum
        {"fast_period": 12, "slow_period": 50, "mode": "live"},  # unknown enum
        {"fast_period": 12, "slow_period": 50, "confirm": 1},  # bool is not an integer
        {"fast_period": 12, "slow_period": 50, "confirm": None},
        {"fast_period": 12, "slow_period": 50, "nested": {"x": 1}},
    ],
)
def test_register_rejects_invalid_or_unbounded_configuration(configuration: object) -> None:
    with pytest.raises(RegistryValidationError) as error:
        StrategyRegistry().register(metadata(), configuration)  # type: ignore[arg-type]

    assert error.value.code is RegistryErrorCode.INVALID_CONFIGURATION


def test_register_rejects_duplicate_version_without_replacing_original() -> None:
    registry = StrategyRegistry()
    original = registry.register(metadata(), valid_config())

    with pytest.raises(RegistryValidationError) as error:
        registry.register(metadata(name="Different name"), valid_config())

    assert error.value.code is RegistryErrorCode.DUPLICATE_VERSION
    assert registry.get("ema_cross", "1.0.0") == original


def test_internal_source_may_omit_commit_without_fabricating_provenance() -> None:
    internal = metadata(source_repository="internal://bybit-quant", source_commit=None)
    assert StrategyRegistry().register(internal, valid_config()).metadata.source_commit is None

    with pytest.raises(RegistryValidationError) as error:
        StrategyRegistry().register(metadata(source_commit=None), valid_config())
    assert error.value.code is RegistryErrorCode.INVALID_METADATA


def test_candidate_and_approval_require_completed_validation_and_reference() -> None:
    registry = StrategyRegistry()
    registry.register(metadata(validation_status=ValidationStatus.NOT_STARTED), valid_config())

    with pytest.raises(RegistryValidationError) as candidate_error:
        registry.transition("ema_cross", "1.0.0", LifecycleStatus.CANDIDATE)

    assert candidate_error.value.code is RegistryErrorCode.INVALID_TRANSITION
    candidate_ready = StrategyRegistry()
    candidate_ready.register(metadata(validation_status=ValidationStatus.BACKTEST_PASSED), valid_config())
    candidate = candidate_ready.transition("ema_cross", "1.0.0", LifecycleStatus.CANDIDATE)
    assert candidate.metadata.current_status is LifecycleStatus.CANDIDATE

    paper_ready = replace(
        candidate.metadata,
        validation_status=ValidationStatus.PAPER_PASSED,
    )
    approved_registry = StrategyRegistry()
    approved_registry.register(paper_ready, valid_config())
    with pytest.raises(RegistryValidationError) as approval_error:
        approved_registry.transition("ema_cross", "1.0.0", LifecycleStatus.APPROVED)
    assert approval_error.value.code is RegistryErrorCode.INVALID_TRANSITION

    approved = approved_registry.transition(
        "ema_cross", "1.0.0", LifecycleStatus.APPROVED, approval_ref="review-2026-0001"
    )
    assert approved.metadata.current_status is LifecycleStatus.APPROVED
    assert approved.metadata.approval_ref == "review-2026-0001"


@pytest.mark.parametrize("status", [LifecycleStatus.APPROVED, LifecycleStatus.DISABLED])
def test_approved_and_disabled_status_require_approval_provenance(status: LifecycleStatus) -> None:
    with pytest.raises(RegistryValidationError) as error:
        StrategyRegistry().register(
            metadata(current_status=status, validation_status=ValidationStatus.PAPER_PASSED),
            valid_config(),
        )

    assert error.value.code is RegistryErrorCode.INVALID_METADATA


def test_transitions_are_bounded_and_failed_attempts_leave_state_unchanged() -> None:
    registry = StrategyRegistry()
    registry.register(
        metadata(
            validation_status=ValidationStatus.PAPER_PASSED,
            current_status=LifecycleStatus.APPROVED,
            approval_ref="review-2026-0001",
        ),
        valid_config(),
    )

    with pytest.raises(RegistryValidationError) as error:
        registry.transition("ema_cross", "1.0.0", LifecycleStatus.RESEARCH)
    assert error.value.code is RegistryErrorCode.INVALID_TRANSITION
    assert registry.get("ema_cross", "1.0.0").metadata.current_status is LifecycleStatus.APPROVED

    disabled = registry.transition("ema_cross", "1.0.0", LifecycleStatus.DISABLED)
    assert disabled.metadata.current_status is LifecycleStatus.DISABLED
    retired = registry.transition("ema_cross", "1.0.0", LifecycleStatus.RETIRED)
    assert retired.metadata.current_status is LifecycleStatus.RETIRED
    with pytest.raises(RegistryValidationError) as terminal_error:
        registry.transition("ema_cross", "1.0.0", LifecycleStatus.RESEARCH)
    assert terminal_error.value.code is RegistryErrorCode.INVALID_TRANSITION
