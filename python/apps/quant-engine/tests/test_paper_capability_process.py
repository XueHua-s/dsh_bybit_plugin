"""Actual opt-in CLI broker, exclusive HTTP ownership and independent native shutdown."""

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
from test_admission import config_at
from test_paper_process import PaperChildren


@pytest.fixture
def private_path() -> Iterator[Path]:
    temporary = Path("/private/tmp") if Path("/private/tmp").exists() else Path("/tmp")
    with tempfile.TemporaryDirectory(prefix="bqp-", dir=temporary.resolve()) as directory:
        yield Path(directory) / "private" / "paper.sock"


def process_environment() -> dict[str, str]:
    """Allowlist synthetic child settings; no inherited credentials or dotenv input."""
    return {
        "PATH": os.path.dirname(sys.executable) + os.pathsep + "/usr/bin:/bin",
        "LANG": "C.UTF-8",
    }


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def arguments(database: Path, session: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "quant_engine.paper_bootstrap",
        "--database",
        str(database),
        "--session",
        session,
        "--port",
        str(port),
    ]


def fetch_capability(path: Path, session: str, origin: str) -> str:
    fields = {"version": 1, "environment": "internal_paper", "session_id": session, "origin": origin}
    frame = (json.dumps(fields, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
    with socket.socket(socket.AF_UNIX) as peer:
        peer.settimeout(1)
        peer.connect(str(path))
        peer.sendall(frame)
        peer.shutdown(socket.SHUT_WR)
        response = bytearray()
        while chunk := peer.recv(1025 - len(response)):
            response.extend(chunk)
            if len(response) > 1024:
                raise AssertionError("broker_response_limit")
    if not response:
        raise ValueError("broker_refused")
    data = json.loads(response)
    token = data.pop("capability", None)
    if data != fields or not isinstance(token, str) or not 32 <= len(token) <= 128:
        raise AssertionError("broker_response_scope")
    return token


def no_disclosure(output: bytes, token: str) -> bool:
    return token.encode() not in output


def require_silent_startup_failure(completed: subprocess.CompletedProcess[bytes]) -> None:
    # Uvicorn's public Server.startup exits STARTUP_FAILURE(3) on lifespan failure.
    if completed.returncode != 3 or completed.stdout or completed.stderr:
        raise AssertionError("paper_startup_failure_contract")


@contextmanager
def running(
    database: Path, session: str, path: Path, *, fd_mode: bool = False
) -> Iterator[tuple[subprocess.Popen[bytes], str, dict[str, str]]]:
    port = free_port()
    origin = f"http://127.0.0.1:{port}"
    argv = arguments(database, session, port)
    read_fd = None
    if fd_mode:
        read_fd, write_fd = os.pipe()
        token = "synthetic-old-fd-capability-000001"
        os.write(write_fd, token.encode())
        os.close(write_fd)
        argv += ["--capability-fd", str(read_fd)]
    else:
        token = ""
        argv += ["--capability-socket", str(path)]
    process = subprocess.Popen(
        argv,
        pass_fds=() if read_fd is None else (read_fd,),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=process_environment(),
    )
    if read_fd is not None:
        os.close(read_fd)
    try:
        deadline = time.monotonic() + 12
        while True:
            if process.poll() is not None or time.monotonic() > deadline:
                raise AssertionError("paper_broker_process_not_ready")
            try:
                if not token:
                    token = fetch_capability(path, session, origin)
                headers = {"Authorization": "Bearer " + token}
                response = httpx.get(origin + "/api/v1/trading/status", headers=headers, timeout=0.5)
                if response.status_code == 200:
                    break
            except (OSError, ValueError, httpx.TransportError):
                pass
            time.sleep(0.03)
        yield process, origin, headers
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=12)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=3)
            raise AssertionError("paper_broker_shutdown_deadline") from None
        if token and not no_disclosure(stdout + stderr, token):
            raise AssertionError("private_capability_disclosed")


def assert_listener_closed(origin: str) -> None:
    port = int(origin.rsplit(":", 1)[1])
    with socket.socket() as peer:
        peer.settimeout(0.5)
        assert peer.connect_ex(("127.0.0.1", port)) != 0


def test_actual_broker_native_sigterm_and_protected_restart(tmp_path: Path, private_path: Path) -> None:
    config = config_at(tmp_path)
    with running(config.database, config.session_id, private_path) as (process, origin, headers):
        assert httpx.get(origin + "/api/v1/trading/status", timeout=2).status_code == 401
        with pytest.raises(ValueError, match="^broker_refused$"):
            fetch_capability(private_path, "wrong-session", origin)
        with pytest.raises(ValueError, match="^broker_refused$"):
            fetch_capability(private_path, config.session_id, "http://127.0.0.1:1")
        session = {"environment": "internal_paper", "session_id": config.session_id}
        started = httpx.post(origin + "/api/v1/trading/start", headers=headers, json=session, timeout=8)
        assert started.status_code == 200
        assert started.json()["native_process_alive"]
        children = PaperChildren.capture(process.pid)
        # Closing provisioning/HTTP peers does not own the service or native process.
        assert process.poll() is None
        assert httpx.get(origin + "/api/v1/trading/status", headers=headers, timeout=2).json()["native_process_alive"]
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=12)
        assert process.returncode in {0, -signal.SIGTERM}
        children.assert_shutdown(graceful=True)
        assert not private_path.exists()
        assert_listener_closed(origin)
    with running(config.database, config.session_id, private_path) as (_process, origin, headers):
        state = httpx.get(origin + "/api/v1/trading/status", headers=headers, timeout=2).json()
        assert state["state"] == "protected"
        assert not state["native_process_alive"]
        refused = httpx.post(origin + "/api/v1/trading/start", headers=headers, json=session, timeout=2)
        assert refused.status_code == 503
    assert not private_path.exists()


def test_old_fifo_mode_remains_independent(tmp_path: Path, private_path: Path) -> None:
    config = config_at(tmp_path)
    with running(config.database, config.session_id, private_path, fd_mode=True) as (process, origin, headers):
        assert not private_path.exists()
        status = httpx.get(origin + "/api/v1/trading/status", headers=headers, timeout=2)
        assert status.json()["state"] == "idle"
        session = {"environment": "internal_paper", "session_id": config.session_id}
        assert httpx.post(origin + "/api/v1/trading/start", headers=headers, json=session, timeout=8).status_code == 200
        children = PaperChildren.capture(process.pid)
        assert httpx.post(origin + "/api/v1/trading/stop", headers=headers, json=session, timeout=8).status_code == 200
        children.assert_native_reaped()
    children.assert_shutdown(graceful=True)
    assert_listener_closed(origin)


def test_http_port_conflict_precedes_broker_and_database(private_path: Path) -> None:
    database = private_path.parent.parent / "never-opened.sqlite"
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        port = occupied.getsockname()[1]
        completed = subprocess.run(
            arguments(database, "paper-test", port) + ["--capability-socket", str(private_path)],
            capture_output=True,
            check=False,
            env=process_environment(),
            timeout=5,
        )
        assert completed.returncode == 2
        assert b"private_capability_or_paper_configuration_unavailable" in completed.stderr
        assert not private_path.exists()
        assert not private_path.parent.exists()
        assert not database.exists()


def test_admission_failure_never_publishes_or_migrates(private_path: Path) -> None:
    database = private_path.parent.parent / "unmigrated.sqlite"
    database.touch()
    port = free_port()
    completed = subprocess.run(
        arguments(database, "paper-test", port) + ["--capability-socket", str(private_path)],
        capture_output=True,
        check=False,
        env=process_environment(),
        timeout=5,
    )
    require_silent_startup_failure(completed)
    assert not private_path.exists()
    assert not private_path.parent.exists()
    assert database.stat().st_size == 0
    assert_listener_closed(f"http://127.0.0.1:{port}")


def test_existing_socket_startup_refusal_preserves_operator_inode(tmp_path: Path, private_path: Path) -> None:
    config = config_at(tmp_path)
    private_path.parent.mkdir(mode=0o700)
    private_path.write_text("operator-file")
    inode = private_path.stat().st_ino
    port = free_port()
    completed = subprocess.run(
        arguments(config.database, config.session_id, port) + ["--capability-socket", str(private_path)],
        capture_output=True,
        check=False,
        env=process_environment(),
        timeout=5,
    )
    require_silent_startup_failure(completed)
    assert private_path.stat().st_ino == inode
    assert private_path.read_text() == "operator-file"
    assert_listener_closed(f"http://127.0.0.1:{port}")


@pytest.mark.parametrize("extra", [[], ["--capability-fd", "3", "--capability-socket", "/private/tmp/x/s"]])
def test_cli_requires_exactly_one_explicit_provisioning_mode(extra: list[str]) -> None:
    completed = subprocess.run(
        arguments(Path("/nonexistent/test-only.sqlite"), "paper-test", 8766) + extra,
        capture_output=True,
        check=False,
        env=process_environment(),
        timeout=5,
    )
    assert completed.returncode == 2
