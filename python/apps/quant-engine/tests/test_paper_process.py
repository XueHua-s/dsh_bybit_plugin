"""Independent HTTP process, private capability pipe, SIGTERM and crash protection."""

import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx
import psutil
from test_admission import config_at, proposal


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


def test_process_private_auth_http_independent_lifetime_and_sigterm(tmp_path: Path) -> None:
    config = config_at(tmp_path)
    child_pids: list[int] = []
    with server(config.database, config.session_id) as (process, url, headers):
        unauth = httpx.get(url + "/api/v1/trading/status", timeout=2)
        assert unauth.status_code == 401
        session = {"environment": "internal_paper", "session_id": config.session_id}
        started = httpx.post(url + "/api/v1/trading/start", headers=headers, json=session, timeout=8)
        assert started.status_code == 200
        assert started.json()["ready"]
        child_pids = [child.pid for child in psutil.Process(process.pid).children(recursive=True)]
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
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=12)
        assert process.returncode in {0, -signal.SIGTERM}
    assert child_pids
    assert not [pid for pid in child_pids if psutil.pid_exists(pid)]
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
    child_pids: list[int] = []
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
        child_pids = [
            child.pid
            for child in psutil.Process(process.pid).children(recursive=True)
            if "resource_tracker" not in " ".join(child.cmdline())
        ]
        process.kill()
        process.wait(timeout=3)
        deadline = time.monotonic() + 8
        while any(
            psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE for pid in child_pids
        ):
            assert time.monotonic() < deadline
            time.sleep(0.05)
    assert child_pids
    with server(config.database, config.session_id) as (_process, url, headers):
        status = httpx.get(url + "/api/v1/trading/status", headers=headers, timeout=2)
        assert status.json()["state"] == "protected"
        record = httpx.get(url + "/api/v1/trading/commands/" + command_id, headers=headers, timeout=2)
        assert record.status_code == 200
        assert record.json()["command_id"] == command_id
        assert not status.json()["native_process_alive"]
