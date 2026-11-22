"""Authenticated fixture snapshot route remains loopback paper-only."""

import hashlib
import json
import sqlite3
import time
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from quant_engine.ai_paper_contracts import CycleReceipt, DecisionRequest
from quant_engine.paper_admission import PaperAdmission
from quant_engine.paper_api import create_paper_app
from quant_engine.paper_config import Capability, config_for_bundle
from quant_engine.strategy_selector import Regime
from quant_engine.synthetic_fixture_registry import (
    PaperFixtureBundle,
    SyntheticBar,
    SyntheticFixtureRegistry,
    SyntheticSelectionEvidence,
)
from quant_execution.models import InstrumentSpec
from quant_execution.paper_models import PaperDepth, PaperFixture
from test_admission import config_at

_DIGEST = "a" * 64


def _cycle_request(session_id: str, fixture_id: str, bundle_digest: str, expires_at_ns: int) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": "1",
        "environment": "internal_paper",
        "request_id": "request-1",
        "payload_digest": _DIGEST,
        "session_id": session_id,
        "fixture_id": fixture_id,
        "bundle_digest": bundle_digest,
        "cycle_id": "cycle-1",
        "universe_digest": bundle_digest,
        "expires_at_ns": expires_at_ns,
        "decision": {
            "decision_id": "decision-1",
            "symbol": "ALPHA",
            "strategy_id": "strategy-1",
            "strategy_version": "1",
            "action": "long",
            "target_exposure": 0.25,
            "evidence_digest": _DIGEST,
        },
    }
    body["payload_digest"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in body.items() if key != "payload_digest"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return body


def _evidence(stamp: int) -> SyntheticSelectionEvidence:
    return SyntheticSelectionEvidence(
        "sma_cross",
        "0.1.0",
        "fixture-approval:sma-cross",
        1.0,
        0.8,
        2.0,
        "fixture-evidence:sma-cross",
        stamp - 20_000_000_000,
        stamp + 50_000_000_000,
        64,
        (Regime.TREND_UP, Regime.TREND_DOWN, Regime.RANGE, Regime.VOLATILE),
        True,
    )


def test_fixture_snapshot_requires_capability_and_returns_registry_digest(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    stamp = time.time_ns()
    fixture = PaperFixture(
        InstrumentSpec("ALPHA", "AAA", Decimal("0.1"), Decimal("0.01"), Decimal("0.01"), Decimal(100), Decimal(1)),
        PaperDepth(Decimal(10), Decimal("10.1"), Decimal(2), Decimal(3), stamp),
        Decimal(10000),
    )
    bars = tuple(
        SyntheticBar(stamp, Decimal(10), Decimal("10.1"), Decimal("9.9"), Decimal(10), Decimal(1))
        for stamp in range(stamp - 30_000_000_000, stamp, 1_000_000_000)
    )
    registry = SyntheticFixtureRegistry(
        (PaperFixtureBundle("bundle-a", (fixture,), {"ALPHA": bars}, {"ALPHA": (_evidence(stamp),)}, ()),)
    )
    capability = Capability(b"synthetic-test-capability-fixture", config.session_id)
    headers = {"Authorization": f"Bearer {capability.token.decode()}"}
    with TestClient(create_paper_app(config, capability, fixture_registry=registry)) as client:
        assert client.get("/api/v1/trading/fixtures/bundle-a").status_code == 401
        response = client.get("/api/v1/trading/fixtures/bundle-a", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["fixture_id"] == "bundle-a"
        assert body["bundle_digest"] == registry.resolve("bundle-a").digest
        assert body["candidates"][0]["symbol"] == "ALPHA"
        assert client.get("/api/v1/trading/fixtures/missing", headers=headers).status_code == 404


def test_paper_app_binds_one_bundle_to_the_native_session(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    stamp = time.time_ns()

    def bundle(fixture_id: str, symbol: str) -> PaperFixtureBundle:
        fixture = PaperFixture(
            InstrumentSpec(
                symbol, symbol[:3], Decimal("0.1"), Decimal("0.01"), Decimal("0.01"), Decimal(100), Decimal(1)
            ),
            PaperDepth(Decimal(10), Decimal("10.1"), Decimal(2), Decimal(3), stamp),
            Decimal(10000),
        )
        bars = tuple(
            SyntheticBar(bar_stamp, Decimal(10), Decimal("10.1"), Decimal("9.9"), Decimal(10), Decimal(1))
            for bar_stamp in range(stamp - 20_000_000_000, stamp, 1_000_000_000)
        )
        return PaperFixtureBundle(fixture_id, (fixture,), {symbol: bars}, {symbol: (_evidence(stamp),)}, ())

    alpha = bundle("bundle-a", "ALPHA")
    beta = bundle("bundle-b", "BETA")
    capability = Capability(b"synthetic-test-capability-binding", config.session_id)
    registry_a = SyntheticFixtureRegistry((alpha,))
    bound_config = config_for_bundle(config, alpha)
    with pytest.raises(ValueError, match="paper_session_requires_single_fixture_bundle"):
        create_paper_app(config, capability, fixture_registry=SyntheticFixtureRegistry((alpha, beta)))
    with pytest.raises(ValueError, match="paper_service_fixture_mismatch"):
        create_paper_app(config, capability, service=PaperAdmission(config), fixture_registry=registry_a)
    # Native admission receives exactly the fixtures from the same registered bundle.
    app = create_paper_app(bound_config, capability, fixture_registry=registry_a)
    assert app


def test_ai_cycle_route_requires_control_and_binds_fixture_before_handler(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    stamp = time.time_ns()
    fixture = PaperFixture(
        InstrumentSpec("ALPHA", "AAA", Decimal("0.1"), Decimal("0.01"), Decimal("0.01"), Decimal(100), Decimal(1)),
        PaperDepth(Decimal(10), Decimal("10.1"), Decimal(2), Decimal(3), stamp),
        Decimal(10000),
    )
    bars = tuple(
        SyntheticBar(stamp, Decimal(10), Decimal("10.1"), Decimal("9.9"), Decimal(10), Decimal(1))
        for stamp in range(stamp - 20_000_000_000, stamp, 1_000_000_000)
    )
    registry = SyntheticFixtureRegistry(
        (PaperFixtureBundle("bundle-a", (fixture,), {"ALPHA": bars}, {"ALPHA": (_evidence(stamp),)}, ()),)
    )
    capability = Capability(b"synthetic-test-capability-cycle1", config.session_id)
    seen: list[DecisionRequest] = []
    receipts: dict[str, CycleReceipt] = {}

    async def handle(request: DecisionRequest) -> CycleReceipt:
        seen.append(request)
        receipt = CycleReceipt(
            schema_version="1",
            request_id=request.request_id,
            payload_digest=request.payload_digest,
            decision_id=request.decision.decision_id,
            status="admitted",
            reason=None,
            command_id="command-1",
            native_client_order_id="native-1",
        )
        receipts[request.request_id] = receipt
        return receipt

    async def lookup(request_id: str) -> CycleReceipt:
        return receipts[request_id]

    headers = {"Authorization": f"Bearer {capability.token.decode()}"}
    app = create_paper_app(
        config, capability, fixture_registry=registry, test_only=True, ai_cycle_handler=handle, ai_cycle_lookup=lookup
    )
    try:
        create_paper_app(config, capability, fixture_registry=registry, ai_cycle_handler=handle)
    except ValueError as error:
        assert str(error) == "paper_cycle_overrides_are_test_only"
    else:
        raise AssertionError("injected cycle handlers must be explicitly test-only")
    with TestClient(app) as client:
        body = _cycle_request(
            config.session_id, "bundle-a", registry.resolve("bundle-a").digest, stamp + 50_000_000_000
        )
        assert client.post("/api/v1/trading/ai-cycles", json=body).status_code == 401
        response = client.post("/api/v1/trading/ai-cycles", json=body, headers=headers)
        assert response.status_code == 202
        assert response.json()["status"] == "admitted"
        assert len(seen) == 1
        assert client.get("/api/v1/trading/ai-cycles/by-request/request-1", headers=headers).status_code == 200

        bad = {**body, "bundle_digest": "b" * 64}
        assert client.post("/api/v1/trading/ai-cycles", json=bad, headers=headers).status_code == 422
        decision = cast(dict[str, object], body["decision"])
        off_universe = {**body, "decision": {**decision, "symbol": "BETA"}}
        off_universe["payload_digest"] = hashlib.sha256(
            json.dumps(
                {key: value for key, value in off_universe.items() if key != "payload_digest"},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        assert client.post("/api/v1/trading/ai-cycles", json=off_universe, headers=headers).status_code == 422
        assert len(seen) == 1

    schema = app.openapi()
    assert "/api/v1/trading/fixtures/{fixture_id}" in schema["paths"]
    assert "/api/v1/trading/ai-cycles" in schema["paths"]
    assert "/api/v1/trading/ai-cycles/by-request/{request_id}" in schema["paths"]


def test_default_cycle_service_persists_receipt_across_app_restart(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    stamp = time.time_ns()
    fixture = PaperFixture(
        InstrumentSpec("ALPHA", "AAA", Decimal("0.1"), Decimal("0.01"), Decimal("0.01"), Decimal(100), Decimal(1)),
        PaperDepth(Decimal(10), Decimal("10.1"), Decimal(2), Decimal(3), stamp),
        Decimal(10000),
    )
    bars = tuple(
        SyntheticBar(stamp, Decimal(10), Decimal("10.1"), Decimal("9.9"), Decimal(10), Decimal(1))
        for stamp in range(stamp - 30_000_000_000, stamp, 1_000_000_000)
    )
    registry = SyntheticFixtureRegistry(
        (
            PaperFixtureBundle(
                "bundle-a",
                (fixture,),
                {"ALPHA": bars},
                {"ALPHA": (_evidence(stamp),)},
                (),
            ),
        )
    )
    capability = Capability(b"synthetic-test-capability-cycle2", config.session_id)
    headers = {"Authorization": f"Bearer {capability.token.decode()}"}
    body = _cycle_request(config.session_id, "bundle-a", registry.resolve("bundle-a").digest, stamp + 50_000_000_000)
    decision = cast(dict[str, object], body["decision"])
    decision = {**decision, "action": "abstain", "target_exposure": None}
    body["decision"] = decision
    body["payload_digest"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in body.items() if key != "payload_digest"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    with TestClient(create_paper_app(config, capability, fixture_registry=registry)) as client:
        posted = client.post("/api/v1/trading/ai-cycles", json=body, headers=headers)
        assert posted.status_code == 202, posted.text
        assert posted.json()["status"] == "abstained"
        assert posted.json()["reason"] == "ai_abstained"

    # A new app instance reopens the same tmp_path SQLite journal and queries its receipt.
    with TestClient(create_paper_app(config, capability, fixture_registry=registry)) as restarted:
        restored = restarted.get("/api/v1/trading/ai-cycles/by-request/request-1", headers=headers)
        assert restored.status_code == 200, restored.text
        assert restored.json() == posted.json()

        mismatch = _cycle_request(
            config.session_id, "bundle-a", registry.resolve("bundle-a").digest, stamp + 50_000_000_000
        )
        mismatch["request_id"] = "request-reject"
        mismatch_decision = cast(dict[str, object], mismatch["decision"])
        mismatch["decision"] = {**mismatch_decision, "decision_id": "decision-reject"}
        mismatch["payload_digest"] = hashlib.sha256(
            json.dumps(
                {key: value for key, value in mismatch.items() if key != "payload_digest"},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        rejected = restarted.post("/api/v1/trading/ai-cycles", json=mismatch, headers=headers)
        assert rejected.status_code == 202, rejected.text
        assert rejected.json()["status"] == "rejected"
        assert rejected.json()["reason"] == "selector_identity_mismatch"


def test_default_cycle_records_stale_fixture_and_replays_receipt_after_expiry(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    now = time.time_ns()
    stamp = now - 120_000_000_000
    fixture = PaperFixture(
        InstrumentSpec("ALPHA", "AAA", Decimal("0.1"), Decimal("0.01"), Decimal("0.01"), Decimal(100), Decimal(1)),
        PaperDepth(Decimal(10), Decimal("10.1"), Decimal(2), Decimal(3), stamp),
        Decimal(10000),
    )
    bars = tuple(
        SyntheticBar(bar_stamp, Decimal(10), Decimal("10.1"), Decimal("9.9"), Decimal(10), Decimal(1))
        for bar_stamp in range(stamp - 20_000_000_000, stamp, 1_000_000_000)
    )
    registry = SyntheticFixtureRegistry(
        (
            PaperFixtureBundle(
                "bundle-stale",
                (fixture,),
                {"ALPHA": bars},
                {"ALPHA": (_evidence(stamp),)},
                (),
            ),
        )
    )
    capability = Capability(b"synthetic-test-capability-stale-001", config.session_id)
    headers = {"Authorization": f"Bearer {capability.token.decode()}"}
    body = _cycle_request(config.session_id, "bundle-stale", registry.only_bundle.digest, now + 30_000_000_000)
    abstain = cast(dict[str, object], body["decision"])
    body["decision"] = {**abstain, "action": "abstain", "target_exposure": None}
    body["payload_digest"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in body.items() if key != "payload_digest"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    with TestClient(create_paper_app(config, capability, fixture_registry=registry)) as client:
        first = client.post("/api/v1/trading/ai-cycles", json=body, headers=headers)
        assert first.status_code == 202, first.text
        assert first.json()["status"] == "rejected"
        assert first.json()["reason"] == "stale_fixture_bars"
        replay = client.post("/api/v1/trading/ai-cycles", json=body, headers=headers)
        assert replay.status_code == 202, replay.text
        assert replay.json() == first.json()


@pytest.mark.parametrize(
    ("fixture_id", "symbol", "base", "bid", "ask", "expected_status"),
    [
        ("bundle-a", "ALPHA", "AAA", "10", "10.001", "filled"),
        ("bundle-a", "ALPHA", "AAA", "10", "10.1", "risk_rejected"),
        ("bundle-b", "BETA-PERP", "BETA", "100", "100.001", "filled"),
    ],
    ids=["bundle-a-filled", "bundle-a-risk-veto", "bundle-b-native-symbol"],
)
def test_default_cycle_binds_registry_bundle_to_native_session_and_risk(
    tmp_path: Path, fixture_id: str, symbol: str, base: str, bid: str, ask: str, expected_status: str
) -> None:
    config = config_at(tmp_path)
    stamp = time.time_ns()
    fixture = PaperFixture(
        InstrumentSpec(symbol, base, Decimal("0.001"), Decimal("0.1"), Decimal("0.1"), Decimal(1000), Decimal(1)),
        # The default policy permits at most 0.1% relative spread. The cases
        # cover a compliant and vetoed ALPHA quote plus a different bundle B symbol.
        PaperDepth(Decimal(bid), Decimal(ask), Decimal(1000), Decimal(1000), stamp),
        Decimal(10000),
    )
    bars = tuple(
        SyntheticBar(ts, Decimal(index + 50), Decimal(index + 52), Decimal(index + 49), Decimal(index + 51), Decimal(1))
        for index, ts in enumerate(range(stamp - 32_000_000_000, stamp, 1_000_000_000))
    )
    evidence = _evidence(stamp)
    registry = SyntheticFixtureRegistry(
        (PaperFixtureBundle(fixture_id, (fixture,), {symbol: bars}, {symbol: (evidence,)}, ()),)
    )
    capability = Capability(b"synthetic-test-capability-risk-001", config.session_id)
    headers = {"Authorization": f"Bearer {capability.token.decode()}"}
    bundle = registry.only_bundle
    body = _cycle_request(config.session_id, fixture_id, bundle.digest, stamp + 50_000_000_000)
    body.update(
        request_id="request-risk",
        universe_digest=bundle.digest,
        decision={
            "decision_id": "decision-risk",
            "symbol": symbol,
            "strategy_id": "sma_cross",
            "strategy_version": "0.1.0",
            "action": "long",
            "target_exposure": 0.01,
            "evidence_digest": evidence.evidence_digest,
        },
    )
    body["payload_digest"] = hashlib.sha256(
        json.dumps(
            {k: v for k, v in body.items() if k != "payload_digest"}, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    with TestClient(create_paper_app(config, capability, fixture_registry=registry)) as client:
        assert (
            client.post(
                "/api/v1/trading/start",
                json={"environment": "internal_paper", "session_id": config.session_id},
                headers=headers,
            ).status_code
            == 200
        )
        result = client.post("/api/v1/trading/ai-cycles", json=body, headers=headers).json()
        assert result["status"] == expected_status
        assert result["command_id"]
        replay = client.post("/api/v1/trading/ai-cycles", json=body, headers=headers)
        assert replay.status_code == 202
        assert replay.json() == result
        decision_payload = cast(dict[str, object], body["decision"])
        changed = {**body, "decision": {**decision_payload, "target_exposure": 0.02}}
        changed["payload_digest"] = hashlib.sha256(
            json.dumps(
                {key: value for key, value in changed.items() if key != "payload_digest"},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        assert client.post("/api/v1/trading/ai-cycles", json=changed, headers=headers).status_code == 409
        with sqlite3.connect(config.database) as connection:
            command_json = connection.execute(
                "SELECT command_json FROM execution_commands WHERE id=?", (result["command_id"],)
            ).fetchone()[0]
            assert json.loads(command_json)["symbol"] == symbol
            command_count = connection.execute(
                "SELECT count(*) FROM execution_commands WHERE request_id='request-risk'"
            ).fetchone()[0]
            assert command_count == 1
            reasons = connection.execute(
                "SELECT reasons_json FROM admission_decisions WHERE command_id=?", (result["command_id"],)
            ).fetchone()[0]
        if expected_status == "risk_rejected":
            assert '"spread_limit"' in reasons
        else:
            assert reasons == "[]"
