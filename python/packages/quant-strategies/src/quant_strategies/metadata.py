"""Shared immutable strategy metadata and bounded configuration contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Market(str, Enum):
    SPOT = "spot"
    LINEAR = "linear"
    INVERSE = "inverse"
    OPTIONS = "options"


class ValidationStatus(str, Enum):
    NOT_STARTED = "not_started"
    BACKTEST_PASSED = "backtest_passed"
    OOS_PASSED = "oos_passed"
    WALK_FORWARD_PASSED = "walk_forward_passed"
    PAPER_PASSED = "paper_passed"
    FAILED = "failed"


class LifecycleStatus(str, Enum):
    RESEARCH = "research"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    DISABLED = "disabled"
    RETIRED = "retired"
    REJECTED = "rejected"


ConfigValue = str | int | float | bool
ConfigKind = Literal["integer", "number", "boolean", "string", "enum"]


@dataclass(frozen=True, slots=True)
class ConfigField:
    """One bounded scalar setting; nested objects and implicit defaults are unsupported."""

    name: str
    kind: ConfigKind
    required: bool = True
    minimum: int | float | None = None
    maximum: int | float | None = None
    choices: tuple[str, ...] = ()
    min_length: int = 0
    max_length: int = 256


@dataclass(frozen=True, slots=True)
class StrategyMetadata:
    """Complete descriptive strategy metadata; fields never grant execution authority."""

    strategy_id: str
    name: str
    version: str
    source_repository: str
    source_commit: str | None
    license: str
    supported_markets: tuple[Market, ...]
    supported_instruments: tuple[str, ...]
    timeframes: tuple[str, ...]
    required_features: tuple[str, ...]
    warmup_period: int
    configuration_schema: tuple[ConfigField, ...]
    entry_conditions: tuple[str, ...]
    exit_conditions: tuple[str, ...]
    target_exposure: str
    risk_constraints: tuple[str, ...]
    backtest_metrics: tuple[tuple[str, float], ...]
    validation_status: ValidationStatus
    current_status: LifecycleStatus
    approval_ref: str | None = None


@dataclass(frozen=True, slots=True)
class StrategyRecord:
    """Immutable metadata/config snapshot retained by the process-local registry."""

    metadata: StrategyMetadata
    configuration: tuple[tuple[str, ConfigValue], ...]
