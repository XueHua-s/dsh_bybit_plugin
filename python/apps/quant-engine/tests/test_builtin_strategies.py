from quant_engine.builtin_strategies import register_builtin_strategies
from quant_engine.strategy_registry import StrategyRegistry
from quant_strategies.metadata import LifecycleStatus, StrategyMetadata, ValidationStatus


def test_builtins_register_as_research_only_with_no_fabricated_commit() -> None:
    registry = StrategyRegistry()
    records = register_builtin_strategies(registry)

    assert len(records) == 11
    assert all(isinstance(record.metadata, StrategyMetadata) for record in records)
    assert all(record.metadata.current_status is LifecycleStatus.RESEARCH for record in records)
    assert all(record.metadata.validation_status is ValidationStatus.NOT_STARTED for record in records)
    assert all(record.metadata.source_commit is None for record in records)
    assert all(registry.get(record.metadata.strategy_id, record.metadata.version) == record for record in records)
