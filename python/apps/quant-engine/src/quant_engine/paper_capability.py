"""Service-owned, same-user capability delivery; no credential discovery or persistence."""

import asyncio
import ipaddress
import json
import os
import socket
import stat
from pathlib import Path
from urllib.parse import urlsplit

from .paper_config import Capability

FRAME_LIMIT = 1024
HANDSHAKE_SECONDS = 0.5
ACTIVE_LIMIT = 4


def _frame(session_id: str, origin: str, capability: str | None = None) -> bytes:
    fields: dict[str, str | int] = {
        "version": 1,
        "environment": "internal_paper",
        "session_id": session_id,
        "origin": origin,
    }
    if capability is not None:
        fields["capability"] = capability
    return (json.dumps(fields, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")


def _origin(value: str) -> str:
    try:
        parsed = urlsplit(value)
        address = ipaddress.ip_address(parsed.hostname or "")
        port = parsed.port
    except ValueError:
        raise ValueError("private_capability_unavailable") from None
    host = f"[{address}]" if address.version == 6 else str(address)
    if not address.is_loopback or port is None or not 1 <= port <= 65535 or value != f"http://{host}:{port}":
        raise ValueError("private_capability_unavailable")
    return value


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_uid, info.st_mode


def _directories(path: Path, *, create: bool) -> tuple[tuple[Path, os.stat_result], ...]:
    """Only the dedicated final directory may be created; no parent is repaired."""
    chain: list[tuple[Path, os.stat_result]] = []
    for directory in reversed((path.parent, *path.parent.parents)):
        try:
            info = directory.lstat()
        except FileNotFoundError:
            if not create or directory != path.parent:
                raise ValueError("private_capability_unavailable") from None
            directory.mkdir(mode=0o700)
            info = directory.lstat()
        mode = stat.S_IMODE(info.st_mode)
        temporary = str(directory) in {"/private/tmp", "/tmp"} and info.st_uid == 0 and bool(mode & stat.S_ISVTX)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, os.getuid()}:
            raise ValueError("private_capability_unavailable")
        if mode & 0o022 and not temporary:
            raise ValueError("private_capability_unavailable")
        if directory == path.parent and (info.st_uid != os.getuid() or mode != 0o700):
            raise ValueError("private_capability_unavailable")
        chain.append((directory, info))
    return tuple(chain)


class PaperCapabilityBroker:
    """Publish one process-private principal after admission and HTTP ownership exist.

    The protocol, private path policy, connection budget and inode-aware cleanup
    are hidden here. Callers own only explicit startup and final shutdown.
    """

    def __init__(self, path: str | Path, capability: Capability, origin: str) -> None:
        raw = str(path)
        if os.name != "posix" or not raw.startswith("/") or len(os.fsencode(raw)) > 100:
            raise ValueError("private_capability_unavailable")
        if raw != os.path.normpath(raw) or raw.startswith("//") or "\x00" in raw or raw.endswith("/"):
            raise ValueError("private_capability_unavailable")
        self._path = Path(raw)
        self._request = _frame(capability.session_id, _origin(origin))
        self._response = _frame(capability.session_id, origin, capability.token.decode("ascii"))
        if len(self._response) > FRAME_LIMIT:
            raise ValueError("private_capability_unavailable")
        self._server: asyncio.Server | None = None
        self._chain: tuple[tuple[Path, os.stat_result], ...] = ()
        self._inode: tuple[int, int, int, int] | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._writers: set[asyncio.StreamWriter] = set()
        self._closing = False
        self._rejected = self._deadlines = self._closed = 0

    @property
    def diagnostics(self) -> dict[str, int]:
        """Nonsecret resource counters for bounded-lifecycle verification."""
        return {
            "active": len(self._tasks),
            "rejected": self._rejected,
            "deadlines": self._deadlines,
            "closed": self._closed,
        }

    async def open(self) -> None:
        if self._closing or self._server is not None:
            raise ValueError("private_capability_unavailable")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._chain = _directories(self._path, create=True)
            if os.path.lexists(self._path):
                raise ValueError("private_capability_unavailable")
            listener.bind(str(self._path))
            info = self._path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError("private_capability_unavailable")
            self._inode = _identity(info)
            self._path.chmod(0o600, follow_symlinks=False)
            self._inode = _identity(self._path.lstat())
            self._verify_path()
            listener.listen(ACTIVE_LIMIT)
            listener.setblocking(False)
            self._server = await asyncio.start_unix_server(self._accept, sock=listener, limit=FRAME_LIMIT)
        except BaseException:
            listener.close()
            self._unlink_owned()
            raise

    def _verify_path(self) -> None:
        chain = _directories(self._path, create=False)
        if tuple((path, _identity(info)) for path, info in chain) != tuple(
            (path, _identity(info)) for path, info in self._chain
        ):
            raise ValueError("private_capability_unavailable")
        info = self._path.lstat()
        if (
            not stat.S_ISSOCK(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or _identity(info) != self._inode
        ):
            raise ValueError("private_capability_unavailable")

    def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        # Refuse before task creation: a semaphore would permit an unbounded queue.
        if self._closing or len(self._tasks) >= ACTIVE_LIMIT:
            self._rejected += 1
            writer.close()
            return
        deadline = asyncio.get_running_loop().time() + HANDSHAKE_SECONDS
        self._writers.add(writer)
        task = asyncio.create_task(self._serve(reader, writer, deadline))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, deadline: float) -> None:
        try:
            async with asyncio.timeout_at(deadline):
                request = bytearray()
                while chunk := await reader.read(FRAME_LIMIT + 1 - len(request)):
                    request.extend(chunk)
                    if len(request) > FRAME_LIMIT:
                        raise ValueError("private_capability_unavailable")
                # Exact canonical bytes also reject duplicate keys, extras and trailing frames.
                if bytes(request) != self._request:
                    raise ValueError("private_capability_unavailable")
                self._verify_path()
                writer.write(self._response)
                await writer.drain()
        except TimeoutError:
            self._deadlines += 1
        except (OSError, ValueError):
            self._rejected += 1
        finally:
            writer.close()
            try:
                async with asyncio.timeout(HANDSHAKE_SECONDS):
                    await writer.wait_closed()
            except (TimeoutError, OSError):
                pass
            self._writers.discard(writer)
            self._closed += 1

    def _unlink_owned(self) -> None:
        try:
            info = self._path.lstat()
            if (
                self._inode is not None
                and self._inode[:2] == (info.st_dev, info.st_ino)
                and stat.S_ISSOCK(info.st_mode)
                and info.st_uid == os.getuid()
            ):
                self._path.unlink()
        except FileNotFoundError:
            pass

    async def close(self) -> None:
        """Refuse new handshakes, cancel owned work, and remove only our socket inode."""
        self._closing = True
        try:
            if self._server is not None:
                self._server.close()
                await self._server.wait_closed()
            tasks = tuple(self._tasks)
            for task in tasks:
                task.cancel()
            for writer in tuple(self._writers):
                writer.close()
            if tasks:
                async with asyncio.timeout(HANDSHAKE_SECONDS * 2):
                    await asyncio.gather(*tasks, return_exceptions=True)
                # Some event loops defer done callbacks beyond gather completion.
                self._tasks.difference_update(tasks)
        finally:
            self._unlink_owned()
