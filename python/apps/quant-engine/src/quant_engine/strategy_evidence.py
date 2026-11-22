"""Bounded read-only strategy-family evidence; never creates an intent or order."""

from __future__ import annotations

from dataclasses import dataclass

from quant_strategies import MarketSnapshot, Signal, evaluate
from quant_strategies.families import DEFAULT_CONFIGS, STRATEGY_METADATA
from quant_strategies.metadata import Market, StrategyMetadata


@dataclass(frozen=True, slots=True)
class StrategyFamilyEvidence:
    strategy_id: str
    name: str
    version: str
    source_repository: str
    source_commit: str | None
    license: str
    lifecycle_status: str
    validation_status: str
    supported_markets: tuple[str, ...]
    ready: bool
    research_target_exposure: float | None
    reason: str
    features: tuple[tuple[str, float], ...]
    research_only: bool = True
    deployment_eligible: bool = False


def evaluate_strategy_families(
    snapshot: MarketSnapshot | None,
    market: Market,
    *,
    stale: bool = False,
) -> tuple[StrategyFamilyEvidence, ...]:
    """Evaluate built-in defaults for context, preserving their unvalidated status."""
    if snapshot is not None and type(snapshot) is not MarketSnapshot or type(market) is not Market:
        raise ValueError("invalid_strategy_evidence_input")

    results: list[StrategyFamilyEvidence] = []
    for metadata in STRATEGY_METADATA:
        signal = _evaluate_one(metadata, snapshot, market, stale=stale)
        results.append(_evidence(metadata, signal))
    return tuple(results)


def _evaluate_one(
    metadata: StrategyMetadata, snapshot: MarketSnapshot | None, market: Market, *, stale: bool
) -> Signal:
    if market not in metadata.supported_markets:
        return Signal(metadata.strategy_id, 0.0, False, "unsupported_market")
    if snapshot is None:
        return Signal(metadata.strategy_id, 0.0, False, "empty_snapshot")
    if stale:
        return Signal(metadata.strategy_id, 0.0, False, "stale_snapshot")
    return evaluate(metadata.strategy_id, snapshot, DEFAULT_CONFIGS[metadata.strategy_id])


def _evidence(metadata: StrategyMetadata, signal: Signal) -> StrategyFamilyEvidence:
    # The current family catalog is intentionally research-only. Even if its
    # metadata changes, this endpoint is not an approval or deployment gate.
    validation = metadata.validation_status
    lifecycle = metadata.current_status
    # This bridge is deliberately a research boundary.  Promotion is owned by
    # the registry/review workflow and can never be inferred from this endpoint.
    deployment_eligible = False
    return StrategyFamilyEvidence(
        strategy_id=metadata.strategy_id,
        name=metadata.name,
        version=metadata.version,
        source_repository=metadata.source_repository,
        source_commit=metadata.source_commit,
        license=metadata.license,
        lifecycle_status=lifecycle.value,
        validation_status=validation.value,
        supported_markets=tuple(item.value for item in metadata.supported_markets),
        ready=signal.ready,
        research_target_exposure=signal.target_exposure if signal.ready else None,
        reason=signal.reason,
        features=signal.features,
        research_only=True,
        deployment_eligible=deployment_eligible,
    )
