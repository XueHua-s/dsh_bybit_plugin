"""Single-source registry for explicitly injected offline synthetic market bundles."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

from quant_execution.paper_models import PaperFixture

from .strategy_selector import Regime, SelectionCandidate

if TYPE_CHECKING:
    from .paper_config import PaperConfig

_SYMBOL = re.compile(r"^[A-Z0-9]+(?:[-._][A-Z0-9]+)*$")
_FIXTURE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_MAX_BARS_PER_SYMBOL = 32


def _decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("non_finite_fixture_decimal")
    return format(value, "f")


@dataclass(frozen=True, slots=True)
class SyntheticBar:
    """One validated, synthetic OHLCV observation, oldest first."""

    timestamp_ns: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        values = (self.open, self.high, self.low, self.close, self.volume)
        if type(self.timestamp_ns) is not int or self.timestamp_ns <= 0:
            raise ValueError("invalid_fixture_bar_timestamp")
        if any(not value.is_finite() for value in values):
            raise ValueError("invalid_fixture_bar_value")
        if min(self.open, self.high, self.low, self.close) <= 0 or self.volume < 0:
            raise ValueError("invalid_fixture_bar_range")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("invalid_fixture_bar_ohlc")


@dataclass(frozen=True, slots=True)
class SyntheticSelectionEvidence:
    """Deterministic fixture-owned selector evidence, never live provenance."""

    strategy_id: str
    version: str
    approval_ref: str
    oos_score: float
    confidence: float
    expected_cost_bps: float
    evaluation_ref: str
    evaluated_at_ns: int
    expires_at_ns: int
    out_of_sample_samples: int
    supported_regimes: tuple[Regime, ...]
    ready_signal: bool

    def __post_init__(self) -> None:
        import math

        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", self.strategy_id):
            raise ValueError("invalid_fixture_evidence_strategy")
        if not re.fullmatch(
            r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?", self.version
        ):
            raise ValueError("invalid_fixture_evidence_version")
        if not self.approval_ref.startswith("fixture-approval:") or len(self.approval_ref) > 128:
            raise ValueError("invalid_fixture_evidence_approval")
        if not self.evaluation_ref.startswith("fixture-evidence:") or len(self.evaluation_ref) > 128:
            raise ValueError("invalid_fixture_evidence_reference")
        scores = (self.oos_score, self.confidence, self.expected_cost_bps)
        if any(type(value) not in {int, float} or not math.isfinite(value) for value in scores):
            raise ValueError("invalid_fixture_evidence_score")
        if (
            not -100 <= self.oos_score <= 100
            or not 0 <= self.confidence <= 1
            or not 0 <= self.expected_cost_bps <= 10_000
        ):
            raise ValueError("invalid_fixture_evidence_score")
        if (
            type(self.evaluated_at_ns) is not int
            or type(self.expires_at_ns) is not int
            or self.evaluated_at_ns <= 0
            or self.expires_at_ns <= self.evaluated_at_ns
            or type(self.out_of_sample_samples) is not int
            or not 30 <= self.out_of_sample_samples <= 1_000_000
            or type(self.ready_signal) is not bool
            or type(self.supported_regimes) is not tuple
            or not self.supported_regimes
            or any(type(item) is not Regime or item is Regime.UNKNOWN for item in self.supported_regimes)
            or len(set(self.supported_regimes)) != len(self.supported_regimes)
        ):
            raise ValueError("invalid_fixture_evidence_window")

    @property
    def evidence_digest(self) -> str:
        payload = self.payload(include_digest=False)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        return hashlib.sha256(raw).hexdigest()

    def payload(self, *, include_digest: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "strategy_id": self.strategy_id,
            "version": self.version,
            "approval_ref": self.approval_ref,
            "current_status": "approved",
            "validation_status": "paper_passed",
            "oos_score": float(self.oos_score),
            "confidence": float(self.confidence),
            "expected_cost_bps": float(self.expected_cost_bps),
            "evaluation_ref": self.evaluation_ref,
            "evaluated_at_ns": self.evaluated_at_ns,
            "expires_at_ns": self.expires_at_ns,
            "out_of_sample_samples": self.out_of_sample_samples,
            "supported_regimes": [item.value for item in self.supported_regimes],
            "ready_signal": self.ready_signal,
            "provenance": "synthetic_fixture_only",
        }
        if include_digest:
            payload["evidence_digest"] = self.evidence_digest
        return payload

    def candidate(self) -> SelectionCandidate:
        return SelectionCandidate(
            self.strategy_id,
            self.version,
            self.oos_score,
            self.confidence,
            self.expected_cost_bps,
            f"{self.evaluation_ref}:{self.evidence_digest}",
            self.evaluated_at_ns // 1_000_000,
            self.out_of_sample_samples,
            self.supported_regimes,
        )


@dataclass(frozen=True, slots=True)
class SyntheticCorrelation:
    """One canonical unordered pairwise correlation assumption for offline risk."""

    first_symbol: str
    second_symbol: str
    coefficient: Decimal

    def __post_init__(self) -> None:
        if (
            type(self.first_symbol) is not str
            or type(self.second_symbol) is not str
            or not _SYMBOL.fullmatch(self.first_symbol)
            or not _SYMBOL.fullmatch(self.second_symbol)
            or self.first_symbol >= self.second_symbol
        ):
            raise ValueError("invalid_fixture_correlation_pair")
        if type(self.coefficient) is not Decimal or not self.coefficient.is_finite():
            raise ValueError("invalid_fixture_correlation_value")
        if not Decimal(-1) <= self.coefficient <= Decimal(1):
            raise ValueError("invalid_fixture_correlation_range")

    def payload(self) -> dict[str, str]:
        return {
            "first_symbol": self.first_symbol,
            "second_symbol": self.second_symbol,
            "coefficient": _decimal(self.coefficient),
        }


def _fixture_payload(fixture: PaperFixture) -> dict[str, object]:
    spec = fixture.instrument
    depth = fixture.initial_depth
    return {
        "symbol": spec.symbol,
        "base_currency": spec.base_currency,
        "price_increment": _decimal(spec.price_increment),
        "size_increment": _decimal(spec.size_increment),
        "min_quantity": _decimal(spec.min_quantity),
        "max_quantity": _decimal(spec.max_quantity),
        "min_notional": _decimal(spec.min_notional),
        "maker_fee": _decimal(spec.maker_fee),
        "taker_fee": _decimal(spec.taker_fee),
        "bid": _decimal(depth.bid),
        "ask": _decimal(depth.ask),
        "bid_size": _decimal(depth.bid_size),
        "ask_size": _decimal(depth.ask_size),
        "timestamp_ns": depth.timestamp_ns,
        "starting_balance": _decimal(fixture.starting_balance),
    }


@dataclass(frozen=True)
class PaperFixtureBundle:
    """Immutable set of arbitrary test instruments sharing one synthetic account."""

    fixture_id: str
    fixtures: tuple[PaperFixture, ...]
    bars_by_symbol: Mapping[str, tuple[SyntheticBar, ...]]
    evidence_by_symbol: Mapping[str, tuple[SyntheticSelectionEvidence, ...]]
    correlations: tuple[SyntheticCorrelation, ...] = ()

    def __post_init__(self) -> None:
        if not _FIXTURE_ID.fullmatch(self.fixture_id):
            raise ValueError("invalid_fixture_id")
        if not self.fixtures or len(self.fixtures) > 128:
            raise ValueError("invalid_fixture_count")
        symbols = [fixture.instrument.symbol for fixture in self.fixtures]
        if any(not _SYMBOL.fullmatch(symbol) or len(symbol) > 40 for symbol in symbols):
            raise ValueError("invalid_fixture_symbol")
        if len(set(symbols)) != len(symbols):
            raise ValueError("duplicate_fixture_symbol")
        expected_pairs = {
            (first, second) for index, first in enumerate(sorted(symbols)) for second in sorted(symbols)[index + 1 :]
        }
        pairs = [(item.first_symbol, item.second_symbol) for item in self.correlations]
        if (
            any(type(item) is not SyntheticCorrelation for item in self.correlations)
            or len(pairs) != len(set(pairs))
            or set(pairs) != expected_pairs
        ):
            raise ValueError("fixture_correlation_pair_coverage")
        if set(self.bars_by_symbol) != set(symbols):
            raise ValueError("fixture_bars_symbol_mismatch")
        if set(self.evidence_by_symbol) != set(symbols):
            raise ValueError("fixture_evidence_symbol_mismatch")
        for evidence_set in self.evidence_by_symbol.values():
            if (
                not evidence_set
                or len(evidence_set) > 32
                or any(type(item) is not SyntheticSelectionEvidence for item in evidence_set)
                or len({item.strategy_id for item in evidence_set}) != len(evidence_set)
            ):
                raise ValueError("invalid_fixture_evidence_set")
        for symbol, bars in self.bars_by_symbol.items():
            if not 1 <= len(bars) <= _MAX_BARS_PER_SYMBOL:
                raise ValueError("invalid_fixture_bar_count")
            timestamps = [bar.timestamp_ns for bar in bars]
            if timestamps != sorted(set(timestamps)):
                raise ValueError("unordered_fixture_bars")
            fixture = next(item for item in self.fixtures if item.instrument.symbol == symbol)
            if timestamps[-1] > fixture.initial_depth.timestamp_ns:
                raise ValueError("fixture_bars_after_quote")
        balances = {fixture.starting_balance for fixture in self.fixtures}
        if len(balances) != 1 or any(not balance.is_finite() or balance <= 0 for balance in balances):
            raise ValueError("inconsistent_fixture_account")
        for fixture in self.fixtures:
            spec = fixture.instrument
            if any(
                not value.is_finite() or value <= 0
                for value in (
                    spec.price_increment,
                    spec.size_increment,
                    spec.min_quantity,
                    spec.max_quantity,
                    spec.min_notional,
                )
            ):
                raise ValueError("invalid_fixture_rules")
            depth = fixture.initial_depth
            if (
                depth.timestamp_ns <= 0
                or not all(
                    value.is_finite() and value > 0 for value in (depth.bid, depth.ask, depth.bid_size, depth.ask_size)
                )
                or depth.bid > depth.ask
            ):
                raise ValueError("invalid_fixture_depth")
        object.__setattr__(self, "fixtures", tuple(sorted(self.fixtures, key=lambda item: item.instrument.symbol)))
        object.__setattr__(
            self,
            "correlations",
            tuple(sorted(self.correlations, key=lambda item: (item.first_symbol, item.second_symbol))),
        )
        object.__setattr__(
            self, "bars_by_symbol", MappingProxyType({key: tuple(value) for key, value in self.bars_by_symbol.items()})
        )
        object.__setattr__(
            self,
            "evidence_by_symbol",
            MappingProxyType({key: tuple(value) for key, value in self.evidence_by_symbol.items()}),
        )

    @property
    def by_symbol(self) -> Mapping[str, PaperFixture]:
        return MappingProxyType({item.instrument.symbol: item for item in self.fixtures})

    @property
    def digest(self) -> str:
        payload = {
            "fixture_id": self.fixture_id,
            "fixtures": [_fixture_payload(item) for item in self.fixtures],
            "bars": {
                symbol: [
                    {
                        "timestamp_ns": bar.timestamp_ns,
                        "open": _decimal(bar.open),
                        "high": _decimal(bar.high),
                        "low": _decimal(bar.low),
                        "close": _decimal(bar.close),
                        "volume": _decimal(bar.volume),
                    }
                    for bar in self.bars_by_symbol[symbol]
                ]
                for symbol in sorted(self.bars_by_symbol)
            },
            "selector_evidence": {
                symbol: [item.payload() for item in self.evidence_by_symbol[symbol]]
                for symbol in sorted(self.evidence_by_symbol)
            },
            "correlations": [item.payload() for item in self.correlations],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()

    @property
    def observed_at_ns(self) -> int:
        return min(item.initial_depth.timestamp_ns for item in self.fixtures)

    def resolve(self, symbol: str) -> PaperFixture:
        try:
            return self.by_symbol[symbol]
        except KeyError:
            raise ValueError("unsupported_fixture_symbol") from None

    def snapshot(self, *, now_ns: int, ttl_ns: int) -> dict[str, object]:
        if now_ns < self.observed_at_ns or ttl_ns <= 0:
            raise ValueError("invalid_fixture_snapshot_clock")
        candidates = []
        for fixture in self.fixtures:
            bars = self.bars_by_symbol[fixture.instrument.symbol]
            evidence = self.evidence_by_symbol[fixture.instrument.symbol]
            if bars[-1].timestamp_ns > now_ns or now_ns - bars[-1].timestamp_ns > ttl_ns:
                raise ValueError("stale_fixture_bars")
            if any(item.evaluated_at_ns > now_ns or item.expires_at_ns <= now_ns for item in evidence):
                raise ValueError("stale_fixture_evidence")
            item = _fixture_payload(fixture)
            candidates.append(
                {
                    "symbol": item["symbol"],
                    "snapshot_id": f"{self.fixture_id}:{item['symbol']}:{item['timestamp_ns']}",
                    "observed_at_ns": item["timestamp_ns"],
                    "expires_at_ns": cast(int, item["timestamp_ns"]) + ttl_ns,
                    "bid": item["bid"],
                    "ask": item["ask"],
                    "bid_size": item["bid_size"],
                    "ask_size": item["ask_size"],
                    "rules": {
                        key: item[key]
                        for key in (
                            "base_currency",
                            "price_increment",
                            "size_increment",
                            "min_quantity",
                            "max_quantity",
                            "min_notional",
                        )
                    },
                    "bars": [
                        {
                            "timestamp_ns": bar.timestamp_ns,
                            "open": _decimal(bar.open),
                            "high": _decimal(bar.high),
                            "low": _decimal(bar.low),
                            "close": _decimal(bar.close),
                            "volume": _decimal(bar.volume),
                        }
                        for bar in bars
                    ],
                    "selector_evidence": [
                        item.payload() for item in self.evidence_by_symbol[fixture.instrument.symbol]
                    ],
                }
            )
        if any(now_ns >= int(candidate["expires_at_ns"]) for candidate in candidates):
            raise ValueError("stale_fixture_bundle")
        return {
            "schema_version": "1",
            "fixture_id": self.fixture_id,
            "bundle_digest": self.digest,
            "observed_at_ns": self.observed_at_ns,
            "expires_at_ns": min(int(candidate["expires_at_ns"]) for candidate in candidates),
            "candidates": candidates,
            "correlations": [item.payload() for item in self.correlations],
        }


class SyntheticFixtureRegistry:
    """Resolve snapshots and instruments only from immutable in-process injection."""

    def __init__(self, bundles: tuple[PaperFixtureBundle, ...]) -> None:
        if not bundles or len(bundles) > 16:
            raise ValueError("invalid_fixture_registry")
        by_id = {bundle.fixture_id: bundle for bundle in bundles}
        if len(by_id) != len(bundles):
            raise ValueError("duplicate_fixture_id")
        self._bundles = MappingProxyType(by_id)

    @property
    def only_bundle(self) -> PaperFixtureBundle:
        """Return the sole bundle allowed to back one native paper session."""
        if len(self._bundles) != 1:
            raise ValueError("paper_session_requires_single_fixture_bundle")
        return next(iter(self._bundles.values()))

    def resolve(self, fixture_id: str, bundle_digest: str | None = None) -> PaperFixtureBundle:
        bundle = self._bundles.get(fixture_id)
        if bundle is None or (bundle_digest is not None and bundle.digest != bundle_digest):
            raise ValueError("fixture_identity_mismatch")
        return bundle

    def snapshot(self, fixture_id: str, *, now_ns: int, ttl_ns: int) -> dict[str, object]:
        return self.resolve(fixture_id).snapshot(now_ns=now_ns, ttl_ns=ttl_ns)


def builtin_synthetic_fixture_registry(config: PaperConfig) -> SyntheticFixtureRegistry:
    """Build the one trusted fixture bundle used by the paper service.

    The bundle is deliberately derived from the already-created ``synthetic_config``
    fixture.  It does not read a file, call a network, or accept strategy/market
    data from a caller.  The public API still requires an explicit ``PaperConfig``
    so tests and launchers cannot accidentally provision an exchange fixture.
    """

    from .paper_config import PaperConfig

    if type(config) is not PaperConfig or config.policy.environment != "internal_paper":
        raise ValueError("builtin_fixture_requires_internal_paper")
    fixtures = config.fixtures
    if len(fixtures) != 1 or fixtures[0].instrument.symbol != "BTCUSDT":
        raise ValueError("builtin_fixture_requires_canonical_instrument")
    fixture = fixtures[0]
    stamp = fixture.initial_depth.timestamp_ns
    if stamp <= 32_000_000_000:
        raise ValueError("builtin_fixture_timestamp_unavailable")

    bars: list[SyntheticBar] = []
    for index in range(32):
        timestamp_ns = stamp - (31 - index) * 1_000_000_000
        close = Decimal(49900) + Decimal(index * 5)
        bars.append(
            SyntheticBar(
                timestamp_ns,
                close - Decimal(1),
                close + Decimal(2),
                close - Decimal(2),
                close,
                Decimal(10),
            )
        )
    evidence = SyntheticSelectionEvidence(
        "sma_cross",
        "0.1.0",
        "fixture-approval:builtin-synthetic",
        1.0,
        0.8,
        2.0,
        "fixture-evidence:builtin-synthetic",
        stamp - 1_000_000_000,
        stamp + 60_000_000_000,
        64,
        (Regime.TREND_UP, Regime.TREND_DOWN, Regime.RANGE, Regime.VOLATILE),
        True,
    )
    bundle = PaperFixtureBundle(
        "builtin-synthetic",
        (fixture,),
        {fixture.instrument.symbol: tuple(bars)},
        {fixture.instrument.symbol: (evidence,)},
        (),
    )
    return SyntheticFixtureRegistry((bundle,))
