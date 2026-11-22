"""Strict validation for internal synthetic-paper cycle messages."""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_OPAQUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_SYMBOL = re.compile(r"^[A-Z0-9]+(?:[-._][A-Z0-9]+)*$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class InstrumentRules(StrictModel):
    base_currency: str
    price_increment: str
    size_increment: str
    min_quantity: str
    max_quantity: str
    min_notional: str

    @field_validator("base_currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        if re.fullmatch(r"[A-Z0-9]{1,16}", value) is None:
            raise ValueError("invalid_fixture_currency")
        return value

    @field_validator("price_increment", "size_increment", "min_quantity", "max_quantity", "min_notional")
    @classmethod
    def positive_decimal(cls, value: str) -> str:
        try:
            number = Decimal(value)
        except InvalidOperation:
            raise ValueError("invalid_fixture_decimal") from None
        if not number.is_finite() or number <= 0:
            raise ValueError("invalid_fixture_decimal")
        return value


class FixtureBar(StrictModel):
    """Canonical synthetic OHLCV bar; timestamps are UTC Unix nanoseconds."""

    timestamp_ns: int = Field(gt=0)
    open: str
    high: str
    low: str
    close: str
    volume: str

    @field_validator("open", "high", "low", "close")
    @classmethod
    def positive_price(cls, value: str) -> str:
        try:
            number = Decimal(value)
        except InvalidOperation:
            raise ValueError("invalid_fixture_bar_price") from None
        if not number.is_finite() or number <= 0:
            raise ValueError("invalid_fixture_bar_price")
        return value

    @field_validator("volume")
    @classmethod
    def nonnegative_volume(cls, value: str) -> str:
        try:
            number = Decimal(value)
        except InvalidOperation:
            raise ValueError("invalid_fixture_bar_volume") from None
        if not number.is_finite() or number < 0:
            raise ValueError("invalid_fixture_bar_volume")
        return value

    @model_validator(mode="after")
    def valid_ohlc(self) -> FixtureBar:
        if Decimal(self.high) < max(Decimal(self.open), Decimal(self.close)):
            raise ValueError("invalid_fixture_bar_ohlc")
        if Decimal(self.low) > min(Decimal(self.open), Decimal(self.close)):
            raise ValueError("invalid_fixture_bar_ohlc")
        return self


class SelectorEvidence(StrictModel):
    """Fixture-owned, synthetic-only evidence exposed for local selection."""

    strategy_id: str
    version: str
    approval_ref: str
    current_status: Literal["approved"]
    validation_status: Literal["paper_passed"]
    oos_score: float
    confidence: float
    expected_cost_bps: float
    evaluation_ref: str
    evaluated_at_ns: int = Field(gt=0)
    expires_at_ns: int = Field(gt=0)
    out_of_sample_samples: int = Field(ge=30, le=1_000_000)
    supported_regimes: tuple[str, ...] = Field(min_length=1, max_length=16)
    ready_signal: bool
    provenance: Literal["synthetic_fixture_only"]
    evidence_digest: str

    @field_validator("evidence_digest")
    @classmethod
    def valid_evidence_digest(cls, value: str) -> str:
        if _DIGEST.fullmatch(value) is None:
            raise ValueError("invalid_evidence_digest")
        return value

    @field_validator("strategy_id")
    @classmethod
    def valid_evidence_strategy(cls, value: str) -> str:
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", value) is None:
            raise ValueError("invalid_evidence_strategy")
        return value

    @model_validator(mode="after")
    def valid_evidence_window(self) -> SelectorEvidence:
        if self.expires_at_ns <= self.evaluated_at_ns:
            raise ValueError("invalid_evidence_window")
        if not -100 <= self.oos_score <= 100:
            raise ValueError("invalid_evidence_score")
        if not 0 <= self.confidence <= 1 or not 0 <= self.expected_cost_bps <= 10_000:
            raise ValueError("invalid_evidence_score")
        if len(set(self.supported_regimes)) != len(self.supported_regimes):
            raise ValueError("duplicate_evidence_regime")
        if any(regime not in {"trend_up", "trend_down", "range", "volatile"} for regime in self.supported_regimes):
            raise ValueError("invalid_evidence_regime")
        payload = self.model_dump(mode="json", exclude={"evidence_digest"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        if hashlib.sha256(encoded).hexdigest() != self.evidence_digest:
            raise ValueError("evidence_digest_mismatch")
        return self


class Candidate(StrictModel):
    symbol: str
    snapshot_id: str
    observed_at_ns: int = Field(gt=0)
    expires_at_ns: int = Field(gt=0)
    bid: str
    ask: str
    bid_size: str
    ask_size: str
    rules: InstrumentRules
    bars: tuple[FixtureBar, ...] = Field(min_length=1, max_length=32)
    selector_evidence: tuple[SelectorEvidence, ...] = Field(min_length=1, max_length=32)

    @field_validator("symbol")
    @classmethod
    def valid_symbol(cls, value: str) -> str:
        if _SYMBOL.fullmatch(value) is None or len(value) > 40:
            raise ValueError("invalid_candidate_symbol")
        return value

    @field_validator("snapshot_id")
    @classmethod
    def valid_snapshot_id(cls, value: str) -> str:
        if _OPAQUE.fullmatch(value) is None:
            raise ValueError("invalid_snapshot_id")
        return value

    @field_validator("bid", "ask", "bid_size", "ask_size")
    @classmethod
    def positive_quote(cls, value: str) -> str:
        try:
            number = Decimal(value)
        except InvalidOperation:
            raise ValueError("invalid_fixture_quote") from None
        if not number.is_finite() or number <= 0:
            raise ValueError("invalid_fixture_quote")
        return value

    @model_validator(mode="after")
    def valid_quote_window(self) -> Candidate:
        if self.expires_at_ns <= self.observed_at_ns or Decimal(self.bid) > Decimal(self.ask):
            raise ValueError("invalid_fixture_quote_window")
        timestamps = [bar.timestamp_ns for bar in self.bars]
        if timestamps != sorted(set(timestamps)) or timestamps[-1] > self.observed_at_ns:
            raise ValueError("invalid_fixture_bar_window")
        return self


class CorrelationPair(StrictModel):
    first_symbol: str
    second_symbol: str
    coefficient: str

    @model_validator(mode="after")
    def canonical_pair_value(self) -> CorrelationPair:
        if any(_SYMBOL.fullmatch(item) is None or len(item) > 40 for item in (self.first_symbol, self.second_symbol)):
            raise ValueError("invalid_fixture_correlation_pair")
        if self.first_symbol >= self.second_symbol:
            raise ValueError("invalid_fixture_correlation_pair")
        try:
            value = Decimal(self.coefficient)
        except InvalidOperation:
            raise ValueError("invalid_fixture_correlation_value") from None
        if not value.is_finite() or not Decimal(-1) <= value <= Decimal(1):
            raise ValueError("invalid_fixture_correlation_range")
        return self


class FixtureSnapshot(StrictModel):
    schema_version: Literal["1"]
    fixture_id: str
    bundle_digest: str
    observed_at_ns: int = Field(gt=0)
    expires_at_ns: int = Field(gt=0)
    candidates: tuple[Candidate, ...] = Field(min_length=1, max_length=128)
    correlations: tuple[CorrelationPair, ...] = Field(max_length=8128)

    @field_validator("fixture_id")
    @classmethod
    def valid_fixture_id(cls, value: str) -> str:
        if _OPAQUE.fullmatch(value) is None:
            raise ValueError("invalid_fixture_id")
        return value

    @field_validator("bundle_digest")
    @classmethod
    def valid_digest(cls, value: str) -> str:
        if _DIGEST.fullmatch(value) is None:
            raise ValueError("invalid_bundle_digest")
        return value

    @model_validator(mode="after")
    def unique_candidates(self) -> FixtureSnapshot:
        symbols = [candidate.symbol for candidate in self.candidates]
        if len(set(symbols)) != len(symbols):
            raise ValueError("duplicate_candidate_symbol")
        if self.expires_at_ns <= self.observed_at_ns:
            raise ValueError("invalid_fixture_snapshot_window")
        if any(
            candidate.observed_at_ns < self.observed_at_ns or candidate.expires_at_ns > self.expires_at_ns
            for candidate in self.candidates
        ):
            raise ValueError("candidate_outside_snapshot_window")
        symbols = sorted(symbols)
        expected = {(first, second) for index, first in enumerate(symbols) for second in symbols[index + 1 :]}
        actual = [(item.first_symbol, item.second_symbol) for item in self.correlations]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError("fixture_correlation_pair_coverage")
        return self


class DecisionTrack(StrictModel):
    decision_id: str
    symbol: str
    strategy_id: str
    strategy_version: str
    action: Literal["long", "short", "flat", "abstain"]
    target_exposure: float | None
    evidence_digest: str

    @field_validator("decision_id", "strategy_id", "strategy_version")
    @classmethod
    def valid_opaque(cls, value: str) -> str:
        if _OPAQUE.fullmatch(value) is None:
            raise ValueError("invalid_decision_identity")
        return value

    @field_validator("symbol")
    @classmethod
    def valid_decision_symbol(cls, value: str) -> str:
        if _SYMBOL.fullmatch(value) is None or len(value) > 40:
            raise ValueError("invalid_decision_symbol")
        return value

    @field_validator("evidence_digest")
    @classmethod
    def valid_evidence_digest(cls, value: str) -> str:
        if _DIGEST.fullmatch(value) is None:
            raise ValueError("invalid_evidence_digest")
        return value

    @field_validator("target_exposure", mode="before")
    @classmethod
    def finite_exposure(cls, value: object) -> object:
        if value is not None and type(value) not in (int, float):
            raise ValueError("invalid_target_exposure")
        if isinstance(value, (int, float)) and abs(value) > 1:
            raise ValueError("invalid_target_exposure")
        return value

    @model_validator(mode="after")
    def action_exposure(self) -> DecisionTrack:
        if (self.action == "abstain") != (self.target_exposure is None):
            raise ValueError("action_target_exposure_mismatch")
        if self.action == "long" and self.target_exposure is not None and self.target_exposure <= 0:
            raise ValueError("action_target_exposure_mismatch")
        if self.action == "short" and self.target_exposure is not None and self.target_exposure >= 0:
            raise ValueError("action_target_exposure_mismatch")
        if self.action == "flat" and self.target_exposure != 0:
            raise ValueError("action_target_exposure_mismatch")
        return self


class DecisionRequest(StrictModel):
    schema_version: Literal["1"]
    environment: Literal["internal_paper"]
    request_id: str
    payload_digest: str
    session_id: str
    fixture_id: str
    bundle_digest: str
    cycle_id: str
    universe_digest: str
    expires_at_ns: int = Field(gt=0)
    decision: DecisionTrack

    @field_validator("request_id", "session_id", "fixture_id", "cycle_id")
    @classmethod
    def valid_identity(cls, value: str) -> str:
        if _OPAQUE.fullmatch(value) is None:
            raise ValueError("invalid_request_identity")
        return value

    @field_validator("payload_digest", "bundle_digest", "universe_digest")
    @classmethod
    def valid_request_digest(cls, value: str) -> str:
        if _DIGEST.fullmatch(value) is None:
            raise ValueError("invalid_request_digest")
        return value

    def computed_payload_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"payload_digest"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()

    def validate_payload_digest(self) -> None:
        if self.payload_digest != self.computed_payload_digest():
            raise ValueError("payload_digest_mismatch")


class CycleReceipt(StrictModel):
    schema_version: Literal["1"]
    request_id: str
    payload_digest: str
    decision_id: str
    status: Literal[
        "abstained",
        "claimed",
        "rejected",
        "selected",
        "risk_rejected",
        "admitted",
        "accepted",
        "partially_filled",
        "filled",
        "protected",
        "unknown",
    ]
    reason: str | None
    command_id: str | None
    native_client_order_id: str | None
