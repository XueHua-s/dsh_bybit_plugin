"""Immutable portfolio planning contracts with bounded, signed exposures."""

import re
from dataclasses import dataclass
from math import isfinite
from typing import Literal, cast


def _finite(value: object) -> bool:
    if type(value) not in {int, float}:
        return False
    return isfinite(cast(int | float, value))


def _valid_symbol(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[A-Z0-9]+(?:[-._][A-Z0-9]+)*", value) is not None and len(value) <= 40


@dataclass(frozen=True, slots=True)
class PositionExposure:
    """Existing signed exposure as a fraction of reconciled account equity."""

    symbol: str
    exposure: float

    def __post_init__(self) -> None:
        if not _valid_symbol(self.symbol):
            raise ValueError("invalid_position_symbol")
        if not _finite(self.exposure) or abs(float(self.exposure)) > 1.0:
            raise ValueError("invalid_position_exposure")


@dataclass(frozen=True, slots=True)
class TargetProposal:
    """Validated strategy output; ``None`` means hold the current position."""

    symbol: str
    strategy_id: str
    strategy_version: str
    target_exposure: float | None
    confidence: float
    evidence_ref: str
    expires_at_ms: int

    def __post_init__(self) -> None:
        if (
            not _valid_symbol(self.symbol)
            or type(self.strategy_id) is not str
            or not self.strategy_id
            or type(self.strategy_version) is not str
            or not self.strategy_version
        ):
            raise ValueError("invalid_target_reference")
        if self.target_exposure is not None and (
            not _finite(self.target_exposure) or abs(float(self.target_exposure)) > 1.0
        ):
            raise ValueError("invalid_target_exposure")
        if not _finite(self.confidence) or not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("invalid_target_confidence")
        if (
            type(self.evidence_ref) is not str
            or not self.evidence_ref.strip()
            or len(self.evidence_ref) > 256
            or any(ord(character) < 32 for character in self.evidence_ref)
            or type(self.expires_at_ms) is not int
            or self.expires_at_ms <= 0
        ):
            raise ValueError("invalid_target_evidence")


@dataclass(frozen=True, slots=True)
class PortfolioPolicy:
    """Operator-owned ceilings; these limits do not replace account risk checks."""

    max_gross_exposure: float = 1.0
    max_single_exposure: float = 0.5
    minimum_confidence: float = 0.5
    max_turnover: float = 0.5
    now_ms: int = 0

    def __post_init__(self) -> None:
        if (
            not _finite(self.max_gross_exposure)
            or not 0.0 < float(self.max_gross_exposure) <= 1.0
            or not _finite(self.max_single_exposure)
            or not 0.0 < float(self.max_single_exposure) <= 1.0
            or not _finite(self.minimum_confidence)
            or not 0.0 <= float(self.minimum_confidence) <= 1.0
            or not _finite(self.max_turnover)
            or not 0.0 <= float(self.max_turnover) <= 2.0
            or type(self.now_ms) is not int
            or self.now_ms <= 0
        ):
            raise ValueError("invalid_portfolio_policy")
        if self.max_single_exposure > self.max_gross_exposure:
            raise ValueError("single_exposure_exceeds_gross_limit")


TransitionReason = Literal["rebalance", "reverse_requires_recheck", "hold", "abstain"]


@dataclass(frozen=True, slots=True)
class TransitionStep:
    """One deterministic exposure change; execution must revalidate it."""

    target_exposure: float
    delta_exposure: float
    phase: Literal["reduce", "increase", "hold"]


@dataclass(frozen=True, slots=True)
class Transition:
    symbol: str
    current_exposure: float
    target_exposure: float
    proposal_target_exposure: float | None
    steps: tuple[TransitionStep, ...]
    reason: TransitionReason
    strategy_id: str | None
    evidence_ref: str | None


@dataclass(frozen=True, slots=True)
class PortfolioPlan:
    """Auditable target map and safe transition sequence, never an order."""

    targets: tuple[PositionExposure, ...]
    transitions: tuple[Transition, ...]
    gross_exposure: float
    turnover: float
    abstained_symbols: tuple[str, ...]
    warnings: tuple[str, ...]
