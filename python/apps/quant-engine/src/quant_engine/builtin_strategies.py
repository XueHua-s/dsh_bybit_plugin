"""Register immutable built-in strategy metadata without enabling execution."""

from __future__ import annotations

from quant_strategies.families import DEFAULT_CONFIGS, STRATEGY_METADATA

from .strategy_registry import StrategyRecord, StrategyRegistry


def register_builtin_strategies(registry: StrategyRegistry) -> tuple[StrategyRecord, ...]:
    """Add built-ins as unvalidated research records to the supplied registry."""
    return tuple(registry.register(metadata, DEFAULT_CONFIGS[metadata.strategy_id]) for metadata in STRATEGY_METADATA)
