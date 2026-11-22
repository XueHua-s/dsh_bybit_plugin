"""Fail-closed metadata registry; registered strategies are never executed here."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import replace
from enum import Enum
from typing import NoReturn
from urllib.parse import urlsplit

from quant_strategies.metadata import (
    ConfigField,
    ConfigKind,
    ConfigValue,
    LifecycleStatus,
    Market,
    StrategyMetadata,
    StrategyRecord,
    ValidationStatus,
)


class RegistryErrorCode(str, Enum):
    INVALID_METADATA = "invalid_metadata"
    INVALID_CONFIGURATION = "invalid_configuration"
    DUPLICATE_VERSION = "duplicate_version"
    NOT_FOUND = "not_found"
    INVALID_TRANSITION = "invalid_transition"


class RegistryValidationError(ValueError):
    """Stable failure code without echoing caller-controlled values."""

    def __init__(self, code: RegistryErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_STRATEGY_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
_COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_INSTRUMENT = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{1,31}$")
_TIMEFRAME = re.compile(r"^[1-9]\d{0,4}[smhdw]$")
_LICENSE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$")
_MAX_METADATA_ITEMS = 128
_CANDIDATE_VALIDATION_STATUSES = frozenset(
    {
        ValidationStatus.BACKTEST_PASSED,
        ValidationStatus.OOS_PASSED,
        ValidationStatus.WALK_FORWARD_PASSED,
        ValidationStatus.PAPER_PASSED,
    }
)


class StrategyRegistry:
    """Own one in-memory definition per strategy version; never imports strategy code."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], StrategyRecord] = {}

    def register(
        self,
        metadata: StrategyMetadata,
        configuration: Mapping[str, ConfigValue],
    ) -> StrategyRecord:
        _validate_metadata(metadata)
        normalized_config = _validate_configuration(metadata.configuration_schema, configuration)
        key = (metadata.strategy_id, metadata.version)
        if key in self._records:
            raise RegistryValidationError(RegistryErrorCode.DUPLICATE_VERSION)
        record = StrategyRecord(metadata=metadata, configuration=normalized_config)
        self._records[key] = record
        return record

    def get(self, strategy_id: str, version: str) -> StrategyRecord:
        record = self._records.get((strategy_id, version))
        if record is None:
            raise RegistryValidationError(RegistryErrorCode.NOT_FOUND)
        return record

    def transition(
        self,
        strategy_id: str,
        version: str,
        target: LifecycleStatus,
        *,
        approval_ref: str | None = None,
    ) -> StrategyRecord:
        key = (strategy_id, version)
        current = self._records.get(key)
        if current is None:
            raise RegistryValidationError(RegistryErrorCode.NOT_FOUND)
        if not _transition_allowed(current.metadata, target, approval_ref):
            raise RegistryValidationError(RegistryErrorCode.INVALID_TRANSITION)
        next_approval_ref = approval_ref if target is LifecycleStatus.APPROVED else current.metadata.approval_ref
        metadata = replace(current.metadata, current_status=target, approval_ref=next_approval_ref)
        _validate_metadata(metadata)
        updated = replace(current, metadata=metadata)
        self._records[key] = updated
        return updated


def _validate_metadata(metadata: StrategyMetadata) -> None:
    if not isinstance(metadata, StrategyMetadata):
        _invalid_metadata()
    _require_text(metadata.strategy_id, _STRATEGY_ID)
    _require_text(metadata.name, None, maximum=128)
    _require_text(metadata.version, _VERSION)
    _validate_repository(metadata.source_repository)
    if metadata.source_commit is None:
        if urlsplit(metadata.source_repository).scheme != "internal":
            _invalid_metadata()
    else:
        _require_text(metadata.source_commit, _COMMIT)
    _require_text(metadata.license, _LICENSE)
    markets = metadata.supported_markets
    if (
        type(markets) is not tuple
        or not markets
        or any(type(item) is not Market for item in markets)
        or len(set(markets)) != len(markets)
    ):
        _invalid_metadata()
    _validate_text_collection(metadata.supported_instruments, _INSTRUMENT)
    _validate_text_collection(metadata.timeframes, _TIMEFRAME)
    _validate_text_collection(metadata.required_features, _IDENTIFIER)
    if type(metadata.warmup_period) is not int or not 1 <= metadata.warmup_period <= 100_000:
        _invalid_metadata()
    _validate_schema(metadata.configuration_schema)
    _validate_descriptions(metadata.entry_conditions)
    _validate_descriptions(metadata.exit_conditions)
    _require_text(metadata.target_exposure, None, maximum=512)
    _validate_descriptions(metadata.risk_constraints)
    _validate_metrics(metadata.backtest_metrics)
    if type(metadata.validation_status) is not ValidationStatus or type(metadata.current_status) is not LifecycleStatus:
        _invalid_metadata()
    if metadata.approval_ref is not None:
        _require_text(metadata.approval_ref, None, maximum=128)
    if (
        metadata.current_status is LifecycleStatus.CANDIDATE
        and metadata.validation_status not in _CANDIDATE_VALIDATION_STATUSES
    ):
        _invalid_metadata()
    if metadata.current_status in {LifecycleStatus.APPROVED, LifecycleStatus.DISABLED} and (
        metadata.validation_status is not ValidationStatus.PAPER_PASSED or metadata.approval_ref is None
    ):
        _invalid_metadata()


def _validate_repository(value: str) -> None:
    if type(value) is not str or len(value) > 512:
        _invalid_metadata()
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError:
        _invalid_metadata()
    if parsed.scheme == "internal":
        if not parsed.netloc or parsed.query or parsed.fragment:
            _invalid_metadata()
        return
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        _invalid_metadata()


def _validate_schema(schema: tuple[ConfigField, ...]) -> None:
    if type(schema) is not tuple or len(schema) > _MAX_METADATA_ITEMS:
        _invalid_metadata()
    names: set[str] = set()
    for field in schema:
        if type(field) is not ConfigField:
            _invalid_metadata()
        _require_text(field.name, _IDENTIFIER)
        kinds = {"integer", "number", "boolean", "string", "enum"}
        if field.name in names or type(field.kind) is not str or field.kind not in kinds:
            _invalid_metadata()
        names.add(field.name)
        if type(field.required) is not bool or type(field.min_length) is not int or type(field.max_length) is not int:
            _invalid_metadata()
        if field.min_length < 0 or not field.min_length <= field.max_length <= 4096:
            _invalid_metadata()
        if field.kind in {"integer", "number"}:
            for bound in (field.minimum, field.maximum):
                if bound is not None and (
                    type(bound) not in {int, float} or (type(bound) is float and not math.isfinite(bound))
                ):
                    _invalid_metadata()
            if field.minimum is not None and field.maximum is not None and field.minimum > field.maximum:
                _invalid_metadata()
            if field.choices:
                _invalid_metadata()
        elif field.minimum is not None or field.maximum is not None:
            _invalid_metadata()
        if type(field.choices) is not tuple or any(type(choice) is not str or not choice for choice in field.choices):
            _invalid_metadata()
        if len(set(field.choices)) != len(field.choices):
            _invalid_metadata()
        if field.kind == "enum" and not field.choices:
            _invalid_metadata()
        if field.kind != "enum" and field.choices:
            _invalid_metadata()


def _validate_configuration(
    schema: tuple[ConfigField, ...],
    configuration: Mapping[str, ConfigValue],
) -> tuple[tuple[str, ConfigValue], ...]:
    if not isinstance(configuration, Mapping):
        _invalid_configuration()
    fields = {field.name: field for field in schema}
    if any(type(key) is not str or key not in fields for key in configuration):
        _invalid_configuration()
    for name, field in fields.items():
        if name not in configuration:
            if field.required:
                _invalid_configuration()
            continue
        if not _matches_kind(configuration[name], field.kind):
            _invalid_configuration()
        value = configuration[name]
        if field.kind in {"integer", "number"}:
            if type(value) is int:
                numeric_value = value
                if value.bit_length() > 63:
                    _invalid_configuration()
            elif type(value) is float:
                numeric_value = value
                if not math.isfinite(value):
                    _invalid_configuration()
            else:
                _invalid_configuration()
            if field.minimum is not None and numeric_value < field.minimum:
                _invalid_configuration()
            if field.maximum is not None and numeric_value > field.maximum:
                _invalid_configuration()
        elif field.kind in {"string", "enum"}:
            if type(value) is not str:
                _invalid_configuration()
            if len(value) < field.min_length or len(value) > field.max_length:
                _invalid_configuration()
            if field.kind == "enum" and value not in field.choices:
                _invalid_configuration()
    return tuple(sorted(configuration.items()))


def _matches_kind(value: ConfigValue, kind: ConfigKind) -> bool:
    if kind == "integer":
        return type(value) is int
    if kind == "number":
        return type(value) in {int, float}
    if kind == "boolean":
        return type(value) is bool
    if kind in {"string", "enum"}:
        return type(value) is str
    return False


def _validate_metrics(metrics: tuple[tuple[str, float], ...]) -> None:
    if type(metrics) is not tuple or len(metrics) > _MAX_METADATA_ITEMS:
        _invalid_metadata()
    names: set[str] = set()
    for item in metrics:
        if type(item) is not tuple or len(item) != 2:
            _invalid_metadata()
        name, value = item
        _require_text(name, _IDENTIFIER)
        if name in names or type(value) not in {int, float}:
            _invalid_metadata()
        if (type(value) is float and not math.isfinite(value)) or (type(value) is int and value.bit_length() > 63):
            _invalid_metadata()
        names.add(name)


def _validate_descriptions(values: tuple[str, ...]) -> None:
    if type(values) is not tuple or not values or len(values) > _MAX_METADATA_ITEMS:
        _invalid_metadata()
    if any(type(value) is not str or not value.strip() or len(value) > 512 for value in values):
        _invalid_metadata()


def _validate_text_collection(values: tuple[str, ...], pattern: re.Pattern[str]) -> None:
    if type(values) is not tuple or not values or len(values) > _MAX_METADATA_ITEMS:
        _invalid_metadata()
    if any(type(value) is not str or not pattern.fullmatch(value) for value in values):
        _invalid_metadata()
    if len(set(values)) != len(values):
        _invalid_metadata()


def _require_text(value: str, pattern: re.Pattern[str] | None, *, maximum: int = 512) -> None:
    if type(value) is not str or not value.strip() or len(value) > maximum:
        _invalid_metadata()
    if pattern is not None and not pattern.fullmatch(value):
        _invalid_metadata()


def _transition_allowed(
    metadata: StrategyMetadata,
    target: LifecycleStatus,
    approval_ref: str | None,
) -> bool:
    current = metadata.current_status
    allowed = {
        LifecycleStatus.RESEARCH: {LifecycleStatus.CANDIDATE, LifecycleStatus.REJECTED, LifecycleStatus.RETIRED},
        LifecycleStatus.CANDIDATE: {
            LifecycleStatus.RESEARCH,
            LifecycleStatus.APPROVED,
            LifecycleStatus.REJECTED,
            LifecycleStatus.RETIRED,
        },
        LifecycleStatus.APPROVED: {LifecycleStatus.DISABLED, LifecycleStatus.RETIRED},
        LifecycleStatus.DISABLED: {LifecycleStatus.APPROVED, LifecycleStatus.RETIRED},
        LifecycleStatus.REJECTED: {LifecycleStatus.RETIRED},
        LifecycleStatus.RETIRED: set(),
    }
    if type(target) is not LifecycleStatus or target not in allowed[current]:
        return False
    if target is LifecycleStatus.CANDIDATE:
        return metadata.validation_status in _CANDIDATE_VALIDATION_STATUSES
    if target is LifecycleStatus.APPROVED:
        return (
            metadata.validation_status is ValidationStatus.PAPER_PASSED
            and type(approval_ref) is str
            and bool(approval_ref.strip())
            and len(approval_ref) <= 128
        )
    return approval_ref is None


def _invalid_metadata() -> NoReturn:
    raise RegistryValidationError(RegistryErrorCode.INVALID_METADATA)


def _invalid_configuration() -> NoReturn:
    raise RegistryValidationError(RegistryErrorCode.INVALID_CONFIGURATION)
