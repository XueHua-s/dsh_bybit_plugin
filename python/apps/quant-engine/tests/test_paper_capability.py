"""Real Unix peers prove canonical EOF framing, private paths and bounded ownership."""

import asyncio
import json
import os
import socket
import stat
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from quant_engine.paper_capability import PaperCapabilityBroker
from quant_engine.paper_config import Capability

SESSION = "paper-test"
ORIGIN = "http://127.0.0.1:8766"
REQUEST = b'{"version":1,"environment":"internal_paper","session_id":"paper-test","origin":"http://127.0.0.1:8766"}\n'


def principal() -> Capability:
    return Capability(b"synthetic-broker-capability-00001", SESSION)


@pytest.fixture
def private_path() -> Iterator[Path]:
    temporary = Path("/private/tmp") if Path("/private/tmp").exists() else Path("/tmp")
    with tempfile.TemporaryDirectory(prefix="bqp-", dir=temporary.resolve()) as directory:
        yield Path(directory) / "private" / "paper.sock"


async def exchange(path: Path, frames: tuple[bytes, ...], *, eof: bool = True, delay: float = 0) -> bytes:
    reader, writer = await asyncio.open_unix_connection(path)
    try:
        for frame in frames:
            writer.write(frame)
            await writer.drain()
            if delay:
                await asyncio.sleep(delay)
        if eof:
            writer.write_eof()
        return await asyncio.wait_for(reader.read(), 2)
    finally:
        writer.close()
        await writer.wait_closed()


def require_response(frame: bytes) -> None:
    # Fixed exceptions avoid pytest rendering a failed expression's token-bearing operands.
    expected = REQUEST[:-2] + b',"capability":"' + principal().token + b'"}\n'
    if frame != expected:
        raise AssertionError("canonical_response_failed")


def require_empty(frame: bytes) -> None:
    if frame:
        raise AssertionError("broker_disclosed_response")


def test_golden_split_eof_permissions_and_cleanup(private_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    async def scenario() -> None:
        broker = PaperCapabilityBroker(private_path, principal(), ORIGIN)
        await broker.open()
        try:
            assert stat.S_IMODE(private_path.parent.stat().st_mode) == 0o700
            assert stat.S_IMODE(private_path.stat().st_mode) == 0o600
            require_response(await exchange(private_path, (REQUEST,)))
            require_response(await exchange(private_path, (REQUEST[:25], REQUEST[25:]), delay=0.03))
            reader, writer = await asyncio.open_unix_connection(private_path)
            writer.write(REQUEST)
            await writer.drain()
            # A complete LF frame cannot disclose anything before request EOF.
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(reader.read(1), 0.03)
            writer.write_eof()
            require_response(await reader.read())
            writer.close()
            await writer.wait_closed()
        finally:
            await broker.close()
        assert not private_path.exists()
        assert private_path.parent.is_dir()
        assert broker.diagnostics["active"] == 0
        with pytest.raises(ValueError, match="^private_capability_unavailable$"):
            await broker.open()

    asyncio.run(scenario())
    output = capsys.readouterr()
    assert not output.out and not output.err


@pytest.mark.parametrize(
    "frame",
    [
        REQUEST[:-1],
        REQUEST + REQUEST,
        REQUEST.replace(b'"version":1', b'"version":1,"version":1'),
        REQUEST.replace(b'"version":1', b'"version":true'),
        REQUEST.replace(b'"version":1', b'"version":2'),
        REQUEST.replace(b"paper-test", b"another-session"),
        REQUEST.replace(b"internal_paper", b"testnet"),
        REQUEST.replace(b"127.0.0.1:8766", b"127.0.0.1:8767"),
        REQUEST.replace(b'{"version":1,', b'{"extra":1,"version":1,'),
        REQUEST.replace(b":1,", b": 1,"),
        REQUEST[:-1] + b"\r\n",
        b"\xff\n",
        b"x" * 1025,
    ],
)
def test_invalid_request_has_no_disclosure(private_path: Path, frame: bytes) -> None:
    async def scenario() -> None:
        broker = PaperCapabilityBroker(private_path, principal(), ORIGIN)
        await broker.open()
        try:
            require_empty(await exchange(private_path, (frame,)))
        finally:
            await broker.close()

    asyncio.run(scenario())


def test_delayed_trailing_frame_and_missing_eof_are_rejected(private_path: Path) -> None:
    async def scenario() -> None:
        broker = PaperCapabilityBroker(private_path, principal(), ORIGIN)
        await broker.open()
        try:
            require_empty(await exchange(private_path, (REQUEST, b"{}\n"), delay=0.03))
            started = time.monotonic()
            require_empty(await exchange(private_path, (REQUEST,), eof=False))
            assert 0.4 <= time.monotonic() - started < 1
            assert broker.diagnostics["deadlines"] == 1
        finally:
            await broker.close()

    asyncio.run(scenario())


def test_four_active_refuses_before_task_and_close_cancels(private_path: Path) -> None:
    async def scenario() -> None:
        broker = PaperCapabilityBroker(private_path, principal(), ORIGIN)
        await broker.open()
        peers: list[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = []
        try:
            for _ in range(4):
                peers.append(await asyncio.open_unix_connection(private_path))
            await asyncio.sleep(0.02)
            assert broker.diagnostics["active"] == 4
            reader, writer = await asyncio.open_unix_connection(private_path)
            require_empty(await asyncio.wait_for(reader.read(), 0.2))
            writer.close()
            await writer.wait_closed()
            assert broker.diagnostics["active"] == 4
            assert broker.diagnostics["rejected"] == 1
            started = time.monotonic()
            await broker.close()
            assert time.monotonic() - started < 0.5
            assert broker.diagnostics["active"] == 0
            for reader, _writer in peers:
                require_empty(await reader.read())
        finally:
            await broker.close()
            for _reader, writer in peers:
                writer.close()
                await writer.wait_closed()

    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["file", "fifo", "socket", "link"])
def test_never_unlinks_existing_path(private_path: Path, kind: str) -> None:
    async def scenario() -> None:
        private_path.parent.mkdir(mode=0o700)
        listener = None
        if kind == "file":
            private_path.write_text("operator-data")
        elif kind == "fifo":
            os.mkfifo(private_path)
        elif kind == "link":
            private_path.symlink_to(private_path.parent / "missing")
        else:
            listener = socket.socket(socket.AF_UNIX)
            listener.bind(str(private_path))
        before = private_path.lstat().st_ino
        broker = PaperCapabilityBroker(private_path, principal(), ORIGIN)
        try:
            with pytest.raises(ValueError, match="^private_capability_unavailable$"):
                await broker.open()
            await broker.close()
            assert private_path.lstat().st_ino == before
        finally:
            if listener:
                listener.close()

    asyncio.run(scenario())


def test_unsafe_directory_symlink_and_replacement_cleanup(private_path: Path) -> None:
    async def scenario() -> None:
        private_path.parent.mkdir(mode=0o755)
        broker = PaperCapabilityBroker(private_path, principal(), ORIGIN)
        with pytest.raises(ValueError):
            await broker.open()
        assert stat.S_IMODE(private_path.parent.stat().st_mode) == 0o755
        private_path.parent.chmod(0o700)
        link = private_path.parent.parent / "link"
        link.symlink_to(private_path.parent, target_is_directory=True)
        with pytest.raises(ValueError):
            await PaperCapabilityBroker(link / "paper.sock", principal(), ORIGIN).open()
        await broker.open()
        displaced = private_path.with_name("displaced.sock")
        private_path.rename(displaced)
        private_path.write_text("replacement")
        await broker.close()
        assert private_path.read_text() == "replacement"
        assert displaced.exists()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "path", ["relative.sock", "/tmp//a.sock", "/tmp/./a.sock", "/tmp/a/../b.sock", "/tmp/a/", "/" + "a" * 100]
)
def test_invalid_path_is_fixed_error(path: str) -> None:
    with pytest.raises(ValueError, match="^private_capability_unavailable$"):
        PaperCapabilityBroker(path, principal(), ORIGIN)


def test_replaced_permissions_and_scope_never_disclose(private_path: Path) -> None:
    async def scenario() -> None:
        broker = PaperCapabilityBroker(private_path, principal(), ORIGIN)
        await broker.open()
        try:
            private_path.chmod(0o666)
            require_empty(await exchange(private_path, (REQUEST,)))
            private_path.chmod(0o600)
        finally:
            await broker.close()
        assert not private_path.exists()
        for origin in ["http://localhost:8766", "http://127.0.0.1:8766/", "https://127.0.0.1:8766"]:
            with pytest.raises(ValueError, match="^private_capability_unavailable$"):
                PaperCapabilityBroker(private_path, principal(), origin)

    asyncio.run(scenario())


def test_canonical_ascii_escape_is_the_same_protocol(private_path: Path) -> None:
    async def scenario() -> None:
        capability = Capability(principal().token, "paper-\u00e9")
        broker = PaperCapabilityBroker(private_path, capability, ORIGIN)
        await broker.open()
        try:
            request = REQUEST.replace(b"paper-test", b"paper-\\u00e9")
            response = await exchange(private_path, (request,))
            data = json.loads(response)
            assert data["session_id"] == "paper-\u00e9"
            if b"\\u00e9" not in response:
                raise AssertionError("canonical_ascii_escape_missing")
            require_empty(await exchange(private_path, (request.replace(b"\\u00e9", "\u00e9".encode()),)))
        finally:
            await broker.close()

    asyncio.run(scenario())
