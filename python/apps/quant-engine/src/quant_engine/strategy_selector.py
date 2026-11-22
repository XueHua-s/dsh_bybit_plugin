"""Validated, account-free strategy choice for one already selected market."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from quant_strategies import MarketSnapshot, Signal, evaluate
from quant_strategies.metadata import LifecycleStatus, ValidationStatus

from .strategy_registry import RegistryErrorCode, RegistryValidationError, StrategyRecord, StrategyRegistry

MAX_EVALUATION_AGE_MS = 30 * 24 * 60 * 60 * 1000
MIN_OOS_SAMPLE_COUNT = 30


class Regime(StrEnum):
    """Small, explainable regime vocabulary used by the selector."""

    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RegimeEvidence:
    """Bounded evidence; values are descriptive and never account state."""

    regime: Regime
    trend_score: float | None
    volatility: float | None
    sample_size: int


@dataclass(frozen=True, slots=True)
class SelectionCandidate:
    """Caller-supplied evaluation inputs with auditable age and source metadata."""

    strategy_id: str
    version: str
    oos_score: float
    confidence: float
    expected_cost_bps: float
    evaluation_ref: str
    evaluated_at_ms: int
    out_of_sample_samples: int
    supported_regimes: tuple[Regime, ...]

    def __post_init__(self) -> None:
        if (
            type(self.strategy_id) is not str
            or not self.strategy_id
            or type(self.version) is not str
            or not self.version
        ):
            raise ValueError("invalid_strategy_reference")
        if (
            type(self.oos_score) not in {int, float}
            or not math.isfinite(self.oos_score)
            or not -100.0 <= self.oos_score <= 100.0
        ):
            raise ValueError("invalid_oos_score")
        if (
            type(self.confidence) not in {int, float}
            or not math.isfinite(self.confidence)
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise ValueError("invalid_confidence")
        if (
            type(self.expected_cost_bps) not in {int, float}
            or not math.isfinite(self.expected_cost_bps)
            or not 0.0 <= self.expected_cost_bps <= 10_000.0
        ):
            raise ValueError("invalid_expected_cost")
        if (
            type(self.evaluation_ref) is not str
            or not self.evaluation_ref.strip()
            or len(self.evaluation_ref) > 256
            or any(ord(character) < 32 for character in self.evaluation_ref)
            or type(self.evaluated_at_ms) is not int
            or self.evaluated_at_ms <= 0
            or type(self.out_of_sample_samples) is not int
            or not MIN_OOS_SAMPLE_COUNT <= self.out_of_sample_samples <= 1_000_000
        ):
            raise ValueError("invalid_evaluation_provenance")
        if (
            type(self.supported_regimes) is not tuple
            or not self.supported_regimes
            or any(type(item) is not Regime or item is Regime.UNKNOWN for item in self.supported_regimes)
            or len(set(self.supported_regimes)) != len(self.supported_regimes)
        ):
            raise ValueError("invalid_supported_regimes")


@dataclass(frozen=True, slots=True)
class SelectionState:
    """Persistable selector memory; it does not authorize an execution."""

    strategy_id: str
    version: str
    selected_at_ms: int
    score: float

    def __post_init__(self) -> None:
        if not self.strategy_id or not self.version or type(self.selected_at_ms) is not int or self.selected_at_ms <= 0:
            raise ValueError("invalid_selection_state")
        if type(self.score) not in {int, float} or not math.isfinite(self.score) or not -100.0 <= self.score <= 100.0:
            raise ValueError("invalid_selection_state")


SelectionKind = Literal["selected", "retained", "abstain"]


@dataclass(frozen=True, slots=True)
class SelectionDecision:
    """The selector's explicit result, including an abstention reason."""

    kind: SelectionKind
    regime: RegimeEvidence
    strategy_id: str | None
    version: str | None
    signal: Signal | None
    score: float | None
    evaluation_ref: str | None
    evaluated_at_ms: int | None
    reason: str
    confidence: float | None = None


def detect_regime(snapshot: MarketSnapshot, *, trend_window: int = 20, volatility_window: int = 20) -> RegimeEvidence:
    """Classify a close series without looking at account or dashboard state."""

    if type(trend_window) is not int or type(volatility_window) is not int or trend_window < 2 or volatility_window < 2:
        raise ValueError("invalid_regime_window")
    closes = tuple(bar.close for bar in snapshot.bars)
    required = max(trend_window, volatility_window) + 1
    if len(closes) < required:
        return RegimeEvidence(Regime.UNKNOWN, None, None, len(closes) - 1)
    returns = tuple(closes[index] / closes[index - 1] - 1.0 for index in range(1, len(closes)))
    trend = returns[-trend_window:]
    volatility_sample = returns[-volatility_window:]
    total_movement = sum(abs(item) for item in trend)
    trend_score = sum(trend) / (total_movement + 1e-12)
    average = sum(volatility_sample) / len(volatility_sample)
    volatility = math.sqrt(sum((item - average) ** 2 for item in volatility_sample) / len(volatility_sample))
    if not all(math.isfinite(item) for item in (trend_score, volatility)):
        return RegimeEvidence(Regime.UNKNOWN, None, None, len(returns))
    if volatility >= 0.03:
        regime = Regime.VOLATILE
    elif trend_score >= 0.25:
        regime = Regime.TREND_UP
    elif trend_score <= -0.25:
        regime = Regime.TREND_DOWN
    else:
        regime = Regime.RANGE
    return RegimeEvidence(regime, trend_score, volatility, len(returns))


def select_strategy(
    snapshot: MarketSnapshot,
    candidates: tuple[SelectionCandidate, ...],
    registry: StrategyRegistry,
    now_ms: int,
    *,
    previous: SelectionState | None = None,
    cooldown_ms: int = 15 * 60_000,
    hysteresis: float = 0.05,
) -> SelectionDecision:
    """Choose one validated strategy, or abstain, with deterministic hysteresis."""

    if type(now_ms) is not int or now_ms <= 0 or type(cooldown_ms) is not int or cooldown_ms < 0:
        raise ValueError("invalid_selection_clock")
    if type(candidates) is not tuple or type(registry) is not StrategyRegistry:
        raise ValueError("invalid_selection_inputs")
    if type(hysteresis) not in {int, float} or not math.isfinite(hysteresis) or hysteresis < 0.0:
        raise ValueError("invalid_hysteresis")
    evidence = detect_regime(snapshot)
    if evidence.regime is Regime.UNKNOWN:
        return _abstain(evidence, "insufficient_regime_evidence")
    scored: list[tuple[float, StrategyRecord, Signal, SelectionCandidate]] = []
    stale_evidence = False
    for candidate in candidates:
        try:
            record = registry.get(candidate.strategy_id, candidate.version)
        except RegistryValidationError as error:
            if error.code is RegistryErrorCode.NOT_FOUND:
                continue
            raise
        metadata = record.metadata
        if (
            metadata.current_status is not LifecycleStatus.APPROVED
            or metadata.validation_status is not ValidationStatus.PAPER_PASSED
            or not metadata.approval_ref
            or evidence.regime not in candidate.supported_regimes
        ):
            continue
        if candidate.evaluated_at_ms > now_ms or now_ms - candidate.evaluated_at_ms > MAX_EVALUATION_AGE_MS:
            stale_evidence = True
            continue
        try:
            signal = evaluate(metadata.strategy_id, snapshot, dict(record.configuration))
        except (TypeError, ValueError):
            continue
        if not signal.ready:
            continue
        score = candidate.oos_score + (0.1 * candidate.confidence) - (candidate.expected_cost_bps / 10_000.0)
        scored.append((score, record, signal, candidate))
    if not scored:
        return _abstain(evidence, "stale_evaluation_evidence" if stale_evidence else "no_validated_strategy")
    scored.sort(key=lambda item: (-item[0], item[1].metadata.strategy_id, item[1].metadata.version))
    scored = [item for item in scored if item[0] > 0.0]
    if not scored:
        return _abstain(evidence, "score_below_minimum")
    winner_score, winner_record, winner_signal, winner_candidate = scored[0]
    prior = (
        next(
            (
                (score, record, signal, candidate)
                for score, record, signal, candidate in scored
                if (
                    record.metadata.strategy_id,
                    record.metadata.version,
                )
                == (previous.strategy_id, previous.version)
            ),
            None,
        )
        if previous is not None
        else None
    )
    if prior is not None and previous is not None:
        elapsed = now_ms - previous.selected_at_ms
        if elapsed < 0:
            return _abstain(evidence, "selection_clock_reversed")
        if elapsed < cooldown_ms or winner_score <= prior[0] + hysteresis:
            prior_candidate = prior[3]
            return SelectionDecision(
                "retained",
                evidence,
                previous.strategy_id,
                previous.version,
                prior[2],
                prior[0],
                prior_candidate.evaluation_ref,
                prior_candidate.evaluated_at_ms,
                "cooldown_or_hysteresis",
                prior_candidate.confidence,
            )
    return SelectionDecision(
        "selected",
        evidence,
        winner_record.metadata.strategy_id,
        winner_record.metadata.version,
        winner_signal,
        winner_score,
        winner_candidate.evaluation_ref,
        winner_candidate.evaluated_at_ms,
        "highest_validated_score",
        winner_candidate.confidence,
    )


def _abstain(evidence: RegimeEvidence, reason: str) -> SelectionDecision:
    return SelectionDecision("abstain", evidence, None, None, None, None, None, None, reason)
