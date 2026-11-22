"""Read-only strategy evidence contract and bounded-input tests."""

from __future__ import annotations

import asyncio
import json
import math
from datetime import UTC, datetime

import httpx
import pytest
from quant_engine.api import MAX_RESEARCH_BODY_BYTES, create_app
from quant_engine.strategy_evidence import evaluate_strategy_families
from quant_strategies import Bar, Market, MarketSnapshot


def bars(count: int, *, newest_timestamp_ms: int | None = None) -> list[dict[str, int | float]]:
    newest = newest_timestamp_ms or int(datetime.now(UTC).timestamp() * 1000) - 60_000
    return [
        {
            "timestamp_ms": newest - ((count - index - 1) * 3_600_000),
            "open": 100 + index * 0.3,
            "high": 101 + index * 0.3,
            "low": 99 + index * 0.3,
            "close": 100 + index * 0.3,
            "volume": 1000 + index,
        }
        for index in range(count)
    ]


def request_body(*, market: str = "linear", count: int = 80) -> dict[str, object]:
    return {"symbol": "btcusdt", "market": market, "interval": "60", "bars": bars(count)}


def post(body: object, *, content: bytes | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        app = create_app(("BTCUSDT",))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            if content is not None:
                return await client.post("/api/v1/research/strategy-evidence", content=content)
            return await client.post("/api/v1/research/strategy-evidence", json=body)

    return asyncio.run(send())


def test_evaluator_keeps_all_builtin_families_unapproved() -> None:
    values = bars(80)
    snapshot = MarketSnapshot(
        bars=tuple(
            Bar(
                timestamp=datetime.fromtimestamp(int(item["timestamp_ms"]) / 1000, UTC),
                open=float(item["open"]),
                high=float(item["high"]),
                low=float(item["low"]),
                close=float(item["close"]),
                volume=float(item["volume"]),
            )
            for item in values
        ),
    )
    evidence = evaluate_strategy_families(snapshot, Market.LINEAR)
    assert len(evidence) == 11
    assert all(item.lifecycle_status == "research" for item in evidence)
    assert all(item.validation_status == "not_started" for item in evidence)
    assert all(item.deployment_eligible is False and item.research_only is True for item in evidence)
    assert any(item.ready for item in evidence)


@pytest.mark.parametrize(
    "snapshot_status,reason,body",
    [
        ("empty", "empty_snapshot", request_body(count=0)),
        (
            "stale",
            "stale_snapshot",
            {
                **request_body(count=1),
                "bars": bars(1, newest_timestamp_ms=int(datetime.now(UTC).timestamp() * 1000) - 3 * 86_400_000),
            },
        ),
    ],
)
def test_empty_or_stale_windows_are_explicit_not_ready(
    snapshot_status: str, reason: str, body: dict[str, object]
) -> None:
    response = post(body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_status"] == snapshot_status
    assert payload["deployment_eligible"] is False
    assert all(not item["ready"] and item["reason"] == reason for item in payload["strategies"])
    assert all(item["research_target_exposure"] is None for item in payload["strategies"])


def test_fresh_linear_snapshot_returns_research_only_evidence() -> None:
    body = request_body()
    newest = body["bars"][-1]["timestamp_ms"]  # type: ignore[index]
    response = post(body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTCUSDT"
    assert payload["market"] == "linear"
    assert payload["snapshot_status"] == "fresh"
    assert payload["newest_timestamp_ms"] == newest
    assert payload["strategy_count"] == 11
    assert payload["research_only"] is True
    assert payload["deployment_eligible"] is False
    assert all(item["deployment_eligible"] is False for item in payload["strategies"])
    assert {item["strategy_id"] for item in payload["strategies"]} >= {"sma_cross", "funding_carry"}


def test_spot_snapshot_rejects_funding_rate_and_spot_family_is_unsupported() -> None:
    invalid = {**request_body(market="spot"), "funding_rate": 0.0001}
    assert post(invalid).status_code == 422
    valid = post(request_body(market="spot"))
    assert valid.status_code == 200
    funding = next(item for item in valid.json()["strategies"] if item["strategy_id"] == "funding_carry")
    assert funding["ready"] is False
    assert funding["reason"] == "unsupported_market"
    assert funding["deployment_eligible"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        lambda body: {**body, "bars": [*body["bars"], body["bars"][-1]]},
        lambda body: {**body, "bars": [body["bars"][1], body["bars"][0], *body["bars"][2:]]},
        lambda body: {**body, "extra": True},
        lambda body: {**body, "market": "inverse"},
        lambda body: {**body, "interval": "2"},
        lambda body: {**body, "bars": bars(1001)},
        lambda body: {**body, "bars": [{**body["bars"][0], "close": float("nan")}]},
    ],
)
def test_invalid_reordered_or_overlong_inputs_fail_closed(mutate) -> None:  # type: ignore[no-untyped-def]
    body = mutate(request_body())
    close = body["bars"][0]["close"]  # type: ignore[index]
    response = (
        post(None, content=json.dumps(body, allow_nan=True).encode())
        if isinstance(close, float) and not math.isfinite(close)
        else post(body)
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_request"}


def test_actual_request_body_is_bounded_before_json_parsing() -> None:
    response = post(None, content=b" " * (MAX_RESEARCH_BODY_BYTES + 1))
    assert response.status_code == 413
    assert response.json() == {"detail": "request_too_large_or_invalid"}


def test_evidence_contract_path_is_in_openapi() -> None:
    schema = create_app(("BTCUSDT",)).openapi()
    operation = schema["paths"]["/api/v1/research/strategy-evidence"]["post"]
    assert operation["responses"]["413"]["content"]["application/json"]["schema"]["$ref"].endswith("ErrorResponse")
    assert "StrategyEvidenceRequest" in schema["components"]["schemas"]
    assert "StrategyEvidenceResponse" in schema["components"]["schemas"]
