"""Real app boundary authorization, session scope and value-redacted validation."""

from pathlib import Path

from fastapi.testclient import TestClient
from quant_engine.paper_api import create_paper_app
from quant_engine.paper_config import Capability
from test_admission import config_at


def test_auth_scope_strict_redacted_and_bounds(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    capability = Capability(b"synthetic-test-capability-00000001", config.session_id)
    headers = {"Authorization": "Bearer " + capability.token.decode()}
    app = create_paper_app(config, capability)
    with TestClient(app) as client:
        assert client.get("/api/v1/trading/status").status_code == 401
        assert (
            client.get("/api/v1/trading/status", headers={**headers, "Origin": "https://example.test"}).status_code
            == 403
        )
        assert client.get("/api/v1/trading/status/", headers=headers).status_code == 404
        payload = {"environment": "internal_paper", "session_id": config.session_id}
        assert (
            client.post("/api/v1/trading/start", json={**payload, "session_id": "wrong"}, headers=headers).status_code
            == 403
        )
        for bad in ({**payload, "cash": "SYNTHETIC-INPUT-MARKER"}, {**payload, "environment": "mainnet"}):
            response = client.post("/api/v1/trading/start", json=bad, headers=headers)
            assert response.status_code == 422
            assert response.json() == {"detail": "invalid_request"}
            assert "SYNTHETIC-INPUT-MARKER" not in response.text
        assert client.post("/api/v1/trading/start", content=b"x" * 4097, headers=headers).status_code == 413
        assert client.get("/api/v1/trading/commands/unknown", headers=headers).status_code == 404
        assert client.get("/api/v1/trading/status", headers=headers).json()["state"] == "idle"
    schema = app.openapi()
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert all(method.get("security") for item in schema["paths"].values() for method in item.values())


def test_observer_cannot_start(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    capability = Capability(b"synthetic-test-capability-00000002", config.session_id, frozenset({"observe"}))
    with TestClient(create_paper_app(config, capability)) as client:
        headers = {"Authorization": "Bearer " + capability.token.decode()}
        response = client.post(
            "/api/v1/trading/start",
            headers=headers,
            json={"environment": "internal_paper", "session_id": config.session_id},
        )
        assert response.status_code == 403
        assert client.get("/api/v1/trading/status", headers=headers).json()["state"] == "idle"
