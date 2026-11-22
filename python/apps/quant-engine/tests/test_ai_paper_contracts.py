import hashlib
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError
from quant_engine.ai_paper_contracts import (
    Candidate,
    CorrelationPair,
    DecisionRequest,
    DecisionTrack,
    FixtureBar,
    FixtureSnapshot,
    InstrumentRules,
    SelectorEvidence,
)

_DIGEST = "a" * 64


def _rules() -> InstrumentRules:
    return InstrumentRules(
        base_currency="AAA",
        price_increment="0.1",
        size_increment="0.01",
        min_quantity="0.01",
        max_quantity="10",
        min_notional="1",
    )


def _candidate(symbol: str = "ALPHA") -> Candidate:
    return Candidate(
        symbol=symbol,
        snapshot_id=f"fixture:{symbol}:100",
        observed_at_ns=100,
        expires_at_ns=200,
        bid="10",
        ask="10.1",
        bid_size="2",
        ask_size="3",
        rules=_rules(),
        bars=tuple(
            FixtureBar(timestamp_ns=stamp, open="10", high="10.1", low="9.9", close="10", volume="1")
            for stamp in range(80, 101)
        ),
        selector_evidence=(_evidence(),),
    )


def _evidence() -> SelectorEvidence:
    fields: dict[str, object] = {
        "strategy_id": "sma_cross",
        "version": "0.1.0",
        "approval_ref": "fixture-approval:sma",
        "current_status": "approved",
        "validation_status": "paper_passed",
        "oos_score": 1.0,
        "confidence": 0.8,
        "expected_cost_bps": 2.0,
        "evaluation_ref": "fixture-evidence:sma",
        "evaluated_at_ns": 100,
        "expires_at_ns": 200,
        "out_of_sample_samples": 64,
        "supported_regimes": ("trend_up", "trend_down", "range", "volatile"),
        "ready_signal": True,
        "provenance": "synthetic_fixture_only",
    }
    encoded = json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return SelectorEvidence.model_validate({**fields, "evidence_digest": hashlib.sha256(encoded).hexdigest()})


def test_fixture_contract_rejects_extra_fields_duplicate_symbols_and_invalid_quote() -> None:
    with pytest.raises(ValidationError):
        Candidate.model_validate({**_candidate().model_dump(), "exchange_url": "https://example.invalid"})
    with pytest.raises(ValidationError, match="duplicate_candidate_symbol"):
        FixtureSnapshot(
            schema_version="1",
            fixture_id="bundle-a",
            bundle_digest=_DIGEST,
            observed_at_ns=100,
            expires_at_ns=200,
            candidates=(_candidate(), _candidate()),
            correlations=(),
        )
    with pytest.raises(ValidationError):
        Candidate(**{**_candidate().model_dump(), "bid": "NaN"})


def test_snapshot_requires_complete_canonical_pairwise_correlation_matrix() -> None:
    candidates = (_candidate("ALPHA-PERP"), _candidate("BETA.PERP"))
    with pytest.raises(ValidationError, match="fixture_correlation_pair_coverage"):
        FixtureSnapshot(
            schema_version="1",
            fixture_id="bundle-a",
            bundle_digest=_DIGEST,
            observed_at_ns=100,
            expires_at_ns=200,
            candidates=candidates,
            correlations=(),
        )
    with pytest.raises(ValidationError, match="invalid_fixture_correlation_pair"):
        CorrelationPair(first_symbol="BETA.PERP", second_symbol="ALPHA-PERP", coefficient="1")
    with pytest.raises(ValidationError, match="invalid_fixture_correlation_range"):
        CorrelationPair(first_symbol="ALPHA-PERP", second_symbol="BETA.PERP", coefficient="1.1")
    snapshot = FixtureSnapshot(
        schema_version="1",
        fixture_id="bundle-a",
        bundle_digest=_DIGEST,
        observed_at_ns=100,
        expires_at_ns=200,
        candidates=candidates,
        correlations=(CorrelationPair(first_symbol="ALPHA-PERP", second_symbol="BETA.PERP", coefficient="1"),),
    )
    assert len(snapshot.correlations) == 1


def test_decision_action_exposure_and_unknown_fields_fail_closed() -> None:
    with pytest.raises(ValidationError, match="action_target_exposure_mismatch"):
        DecisionTrack(
            decision_id="decision-1",
            symbol="ALPHA",
            strategy_id="mean-reversion",
            strategy_version="1",
            action="long",
            target_exposure=-0.2,
            evidence_digest=_DIGEST,
        )
    with pytest.raises(ValidationError):
        DecisionTrack.model_validate(
            {
                "decision_id": "decision-1",
                "symbol": "ALPHA",
                "strategy_id": "s1",
                "strategy_version": "1",
                "action": "abstain",
                "target_exposure": None,
                "evidence_digest": _DIGEST,
                "limit_price": "10",
            }
        )


def test_request_digest_binds_fixture_decision_and_environment() -> None:
    decision = DecisionTrack(
        decision_id="decision-1",
        symbol="ALPHA",
        strategy_id="mean-reversion",
        strategy_version="1",
        action="long",
        target_exposure=0.25,
        evidence_digest=_DIGEST,
    )
    values = {
        "schema_version": "1",
        "environment": "internal_paper",
        "request_id": "request-1",
        "payload_digest": _DIGEST,
        "session_id": "session-1",
        "fixture_id": "bundle-a",
        "bundle_digest": _DIGEST,
        "cycle_id": "cycle-1",
        "universe_digest": _DIGEST,
        "expires_at_ns": 200,
        "decision": decision,
    }
    initial = DecisionRequest(**values)
    request = initial.model_copy(update={"payload_digest": initial.computed_payload_digest()})
    request.validate_payload_digest()
    changed = request.model_copy(update={"decision": decision.model_copy(update={"target_exposure": 0.5})})
    with pytest.raises(ValueError, match="payload_digest_mismatch"):
        changed.validate_payload_digest()
    with pytest.raises(ValidationError):
        DecisionRequest(**{**values, "environment": "testnet"})


def test_candidate_amounts_are_decimal_safe_and_exposure_is_bounded() -> None:
    assert Decimal(_candidate().bid) * Decimal(_candidate().bid_size) == Decimal(20)
    with pytest.raises(ValidationError):
        DecisionTrack(
            decision_id="decision-1",
            symbol="ALPHA",
            strategy_id="strategy-1",
            strategy_version="1",
            action="long",
            target_exposure=1.01,
            evidence_digest=_DIGEST,
        )


def test_candidate_rejects_missing_unordered_or_invalid_synthetic_bars() -> None:
    payload = _candidate().model_dump()
    payload.pop("bars")
    with pytest.raises(ValidationError):
        Candidate.model_validate(payload)
    payload = _candidate().model_dump()
    payload["bars"] = tuple(reversed(payload["bars"]))
    with pytest.raises(ValidationError, match="invalid_fixture_bar_window"):
        Candidate.model_validate(payload)
    with pytest.raises(ValidationError, match="invalid_fixture_bar_ohlc"):
        FixtureBar(timestamp_ns=100, open="10", high="9", low="10", close="10", volume="1")


def test_fixture_selector_evidence_digest_and_expiry_are_enforced() -> None:
    with pytest.raises(ValidationError, match="evidence_digest_mismatch"):
        SelectorEvidence(**{**_evidence().model_dump(), "confidence": 0.9})
    with pytest.raises(ValidationError, match="invalid_evidence_window"):
        SelectorEvidence(**{**_evidence().model_dump(), "expires_at_ns": 100})
