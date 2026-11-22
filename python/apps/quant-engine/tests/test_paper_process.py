"""Independent HTTP process, private capability pipe, SIGTERM and crash protection."""

import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx
import psutil
import pytest
from test_admission import config_at, proposal


def _state(process: psutil.Process) -> str:
    # Process.is_running compares the captured PID/create-time identity, not just PID existence.
    if not process.is_running():
        return "exited_or_reused"
    try:
        return process.status()
    except psutil.NoSuchProcess:
        return "exited_or_reused"


def _describe(processes: tuple[psutil.Process, ...]) -> list[tuple[int, float, str]]:
    return [(process.pid, process.create_time(), _state(process)) for process in processes]


def _wait_inactive(processes: tuple[psutil.Process, ...], role: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        active = tuple(
            process for process in processes if _state(process) not in {"exited_or_reused", psutil.STATUS_ZOMBIE}
        )
        if not active:
            return
        assert time.monotonic() < deadline, f"{role}_shutdown_deadline: {_describe(active)}"
        time.sleep(0.01)


@dataclass(frozen=True)
class PaperChildren:
    """Observe native reaping separately from the stdlib tracker's asynchronous exit."""

    native: tuple[psutil.Process, ...]
    trackers: tuple[psutil.Process, ...]

    @classmethod
    def capture(cls, owner_pid: int) -> "PaperChildren":
        native, trackers = [], []
        for child in psutil.Process(owner_pid).children(recursive=True):
            arguments = child.cmdline()
            # server() starts an unflagged interpreter; data argv must never relax native reaping.
            is_tracker = (
                len(arguments) == 3
                and arguments[:2] == [sys.executable, "-c"]
                and re.fullmatch(r"from multiprocessing\.resource_tracker import main;main\([0-9]+\)", arguments[2])
                is not None
            )
            (trackers if is_tracker else native).append(child)
        assert native, "native_child_not_observed"
        assert trackers, "resource_tracker_not_observed"
        return cls(tuple(native), tuple(trackers))

    def assert_native_reaped(self) -> None:
        """Service stop joins its worker; an unreaped native zombie must fail."""
        remaining = tuple(process for process in self.native if process.is_running())
        assert not remaining, f"native_not_reaped: {_describe(remaining)}"

    def assert_shutdown(self, *, graceful: bool) -> None:
        if graceful:
            self.assert_native_reaped()
        else:
            # A killed owner cannot reap its orphan; the watchdog must still end execution.
            _wait_inactive(self.native, "native", 8)
        # CPython deliberately does not wait for this process; EOF cleanup may outlive the owner.
        _wait_inactive(self.trackers, "resource_tracker", 3)


@contextmanager
def server(
    database: Path, session: str, *, authenticated: bool = True
) -> Iterator[tuple[subprocess.Popen[bytes], str, dict[str, str]]]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    read_fd, write_fd = os.pipe()
    capability = b"synthetic-process-capability-0001"
    os.write(write_fd, capability)
    os.close(write_fd)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "quant_engine.paper_bootstrap",
            "--database",
            str(database),
            "--session",
            session,
            "--capability-fd",
            str(read_fd),
            "--port",
            str(port),
        ],
        pass_fds=(read_fd,),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.close(read_fd)
    headers = {"Authorization": "Bearer " + capability.decode()} if authenticated else {}
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 12
        while True:
            try:
                response = httpx.get(url + "/api/v1/trading/status", headers=headers, timeout=0.5)
                assert response.status_code in {200, 401}
                break
            except httpx.TransportError:
                if process.poll() is not None or time.monotonic() > deadline:
                    raise AssertionError("paper_process_not_ready") from None
                time.sleep(0.05)
        yield process, url, headers
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
                raise AssertionError("paper_process_shutdown_deadline") from None


@pytest.mark.parametrize("pause_tracker", [False, True])
def test_process_private_auth_http_independent_lifetime_and_sigterm(tmp_path: Path, pause_tracker: bool) -> None:
    config = config_at(tmp_path)
    with server(config.database, config.session_id) as (process, url, headers):
        unauth = httpx.get(url + "/api/v1/trading/status", timeout=2)
        assert unauth.status_code == 401
        session = {"environment": "internal_paper", "session_id": config.session_id}
        started = httpx.post(url + "/api/v1/trading/start", headers=headers, json=session, timeout=8)
        assert started.status_code == 200
        assert started.json()["ready"]
        children = PaperChildren.capture(process.pid)
        # Each httpx call closes its own client; native worker remains owned by service.
        submitted = httpx.post(
            url + "/api/v1/trading/commands", headers=headers, json=proposal().model_dump(), timeout=5
        )
        assert submitted.status_code == 202
        receipt = submitted.json()
        deadline = time.monotonic() + 8
        while True:
            response = httpx.get(url + "/api/v1/trading/commands/by-request/req-1", headers=headers, timeout=3)
            assert response.status_code == 200
            if response.json()["state"] == "filled":
                break
            assert time.monotonic() < deadline
            time.sleep(0.05)
        assert response.json()["command_id"] == receipt["command_id"]
        status = httpx.get(url + "/api/v1/trading/status", headers=headers, timeout=2)
        assert status.json()["native_process_alive"]
        try:
            if pause_tracker:
                for tracker in children.trackers:
                    tracker.send_signal(signal.SIGSTOP)
                deadline = time.monotonic() + 2
                while any(_state(tracker) != psutil.STATUS_STOPPED for tracker in children.trackers):
                    assert time.monotonic() < deadline, "resource_tracker_not_paused"
                    time.sleep(0.01)
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=12)
            assert process.returncode in {0, -signal.SIGTERM}
            children.assert_native_reaped()
            if pause_tracker:
                assert all(_state(tracker) == psutil.STATUS_STOPPED for tracker in children.trackers)
        finally:
            if pause_tracker:
                for tracker in children.trackers:
                    try:
                        tracker.send_signal(signal.SIGCONT)
                    except psutil.NoSuchProcess:
                        pass
        children.assert_shutdown(graceful=True)
    with server(config.database, config.session_id) as (_process, url, headers):
        response = httpx.get(url + "/api/v1/trading/status", headers=headers, timeout=2)
        assert response.json()["state"] == "protected"
        refused = httpx.post(url + "/api/v1/trading/start", headers=headers, json=session, timeout=2)
        assert refused.status_code == 503


def test_crash_preserves_session_and_never_auto_restarts(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    with server(config.database, config.session_id) as (process, url, headers):
        # No native child started here; crash is a durable ownership/session boundary.
        before = httpx.get(url + "/api/v1/trading/status", headers=headers, timeout=2)
        assert before.json()["state"] == "idle"
        process.kill()
        process.wait(timeout=3)
    with server(config.database, config.session_id) as (_process, url, headers):
        after = httpx.get(url + "/api/v1/trading/status", headers=headers, timeout=2)
        assert after.json()["state"] == "protected"
        assert not after.json()["native_process_alive"]


def test_crash_after_dispatch_preserves_order_and_reaps_orphan(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    with server(config.database, config.session_id) as (process, url, headers):
        session = {"environment": "internal_paper", "session_id": config.session_id}
        started = httpx.post(url + "/api/v1/trading/start", headers=headers, json=session, timeout=8)
        assert started.status_code == 200
        # Crossing LIMIT dispatch leaves filled/nonflat or uncertain state across crash;
        # neither state authorizes replay into an empty Sandbox.
        resting = proposal("crash-order").model_dump()
        submitted = httpx.post(url + "/api/v1/trading/commands", headers=headers, json=resting, timeout=5)
        assert submitted.status_code == 202
        command_id = submitted.json()["command_id"]
        children = PaperChildren.capture(process.pid)
        process.kill()
        process.wait(timeout=3)
        children.assert_shutdown(graceful=False)
    with server(config.database, config.session_id) as (_process, url, headers):
        status = httpx.get(url + "/api/v1/trading/status", headers=headers, timeout=2)
        assert status.json()["state"] == "protected"
        record = httpx.get(url + "/api/v1/trading/commands/" + command_id, headers=headers, timeout=2)
        assert record.status_code == 200
        assert record.json()["command_id"] == command_id
        assert not status.json()["native_process_alive"]


def test_bootstrap_exposes_authenticated_fixture_and_durable_ai_cycle(tmp_path: Path) -> None:
    """The deployed CLI provisions its trusted fixture registry and receipt API."""
    config = config_at(tmp_path)
    with server(config.database, config.session_id) as (_process, url, headers):
        snapshot = httpx.get(url + "/api/v1/trading/fixtures/builtin-synthetic", headers=headers, timeout=3)
        assert snapshot.status_code == 200, snapshot.text
        fixture = snapshot.json()
        assert fixture["fixture_id"] == "builtin-synthetic"
        assert [item["symbol"] for item in fixture["candidates"]] == ["BTCUSDT"]
        candidate = fixture["candidates"][0]
        evidence = candidate["selector_evidence"][0]
        session = {"environment": "internal_paper", "session_id": config.session_id}
        started = httpx.post(url + "/api/v1/trading/start", headers=headers, json=session, timeout=10)
        assert started.status_code == 200, started.text
        assert started.json()["ready"] is True
        body: dict[str, object] = {
            "schema_version": "1",
            "environment": "internal_paper",
            "request_id": "process-cycle-order",
            "session_id": config.session_id,
            "fixture_id": fixture["fixture_id"],
            "bundle_digest": fixture["bundle_digest"],
            "cycle_id": "process-cycle",
            "universe_digest": fixture["bundle_digest"],
            "expires_at_ns": fixture["expires_at_ns"],
            "decision": {
                "decision_id": "process-decision-order",
                "symbol": candidate["symbol"],
                "strategy_id": evidence["strategy_id"],
                "strategy_version": evidence["version"],
                "action": "long",
                "target_exposure": 0.01,
                "evidence_digest": evidence["evidence_digest"],
            },
        }
        body["payload_digest"] = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        ).hexdigest()
        posted = httpx.post(url + "/api/v1/trading/ai-cycles", headers=headers, json=body, timeout=5)
        assert posted.status_code == 202, posted.text
        receipt = posted.json()
        assert receipt["request_id"] == body["request_id"]
        assert receipt["payload_digest"] == body["payload_digest"]
        deadline = time.monotonic() + 8
        while receipt["status"] not in {"filled", "risk_rejected", "rejected", "protected", "unknown"}:
            assert time.monotonic() < deadline, "ai_cycle_terminal_deadline"
            time.sleep(0.05)
            refreshed = httpx.get(
                url + "/api/v1/trading/ai-cycles/by-request/" + str(body["request_id"]),
                headers=headers,
                timeout=3,
            )
            assert refreshed.status_code == 200, refreshed.text
            receipt = refreshed.json()
        assert receipt["status"] == "filled", receipt
        assert isinstance(receipt["command_id"], str)
        assert isinstance(receipt["native_client_order_id"], str)
        recovered = httpx.get(
            url + "/api/v1/trading/ai-cycles/by-request/" + str(body["request_id"]), headers=headers, timeout=3
        )
        assert recovered.status_code == 200, recovered.text
        assert recovered.json() == receipt
        unauthenticated = httpx.get(url + "/api/v1/trading/fixtures/builtin-synthetic", timeout=3)
        assert unauthenticated.status_code == 401
