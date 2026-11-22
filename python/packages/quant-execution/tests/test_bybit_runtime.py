"""Credential-free lifecycle tests for the protected native owner facade."""

from __future__ import annotations

import pytest
from quant_execution.bybit_runtime import BybitRuntime, NodeController


class FakeNode:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def submit(self, order: object) -> None:
        if not isinstance(order, dict) or order.get("client_order_id") != "ledger-1":
            raise ValueError("invalid_order")

    def protect(self, reason: str) -> None:
        if not reason:
            raise ValueError("invalid_protection_reason")

    def stop(self) -> None:
        self.stopped = True

    def dispose(self) -> None:
        if not self.stopped:
            raise RuntimeError("dispose_before_stop")


class FakeFactory:
    def __call__(self) -> NodeController:
        return FakeNode()


class FailingFactory:
    def __call__(self) -> NodeController:
        raise RuntimeError("secret-canary-in-exception")


def test_owner_process_lifecycle_and_protection() -> None:
    runtime = BybitRuntime(FakeFactory(), session_id="session", generation=4)
    try:
        assert runtime.start().state == "running"
        assert runtime.submit({"client_order_id": "ledger-1"}).state == "running"
        protected = runtime.protect("reconciliation_required")
        assert protected.state == "protected"
        with pytest.raises(RuntimeError, match="runtime_protected"):
            runtime.submit({"client_order_id": "ledger-1"})
    finally:
        stopped = runtime.stop()
    assert stopped.state == "stopped"
    assert not stopped.owner_alive
    assert stopped.reason == "reconciliation_required"
    assert runtime.stop().state == "stopped"


def test_invalid_order_is_fixed_code_and_does_not_retry() -> None:
    runtime = BybitRuntime(FakeFactory(), session_id="session", generation=0)
    try:
        runtime.start()
        with pytest.raises(RuntimeError, match="invalid_order"):
            runtime.submit({"client_order_id": "wrong"})
        assert runtime.health().state == "protected"
        assert runtime.health().reason == "invalid_order"
    finally:
        runtime.stop()


def test_start_failure_is_redacted_and_stops_cleanly() -> None:
    runtime = BybitRuntime(FailingFactory(), session_id="session", generation=0)
    with pytest.raises(RuntimeError, match="node_start_failed") as error:
        runtime.start()
    assert "secret-canary" not in str(error.value)
    health = runtime.health()
    assert health.state == "failed"
    assert health.reason == "node_start_failed"
    assert runtime.stop().state == "failed"


def test_constructor_rejects_unbounded_runtime_configuration() -> None:
    with pytest.raises(ValueError, match="queue"):
        BybitRuntime(FakeFactory(), session_id="session", generation=0, queue_capacity=0)
    with pytest.raises(ValueError, match="timeout"):
        BybitRuntime(FakeFactory(), session_id="session", generation=0, timeout_seconds=31)
