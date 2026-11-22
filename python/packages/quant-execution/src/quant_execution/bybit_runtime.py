"""Protected owner process for a future native Bybit execution session.

The parent facade never touches a Nautilus loop, cache, config or credential.
One spawned child owns the node from construction through disposal.  This is
deliberately a lifecycle boundary: the default project still supplies no live
factory, and no method in this module creates an exchange client by itself.
"""

from __future__ import annotations

import multiprocessing
import threading
from dataclasses import dataclass, replace
from multiprocessing.process import BaseProcess
from queue import Empty, Full
from time import monotonic, time_ns
from typing import Literal, Protocol

RuntimeState = Literal["created", "starting", "running", "protected", "stopping", "stopped", "failed"]


@dataclass(frozen=True)
class RuntimeHealth:
    """Sanitized lifecycle evidence; never carries config, URLs or exceptions."""

    state: RuntimeState
    session_id: str
    generation: int
    heartbeat_ns: int
    websocket_ready: bool
    reconciliation_revision: int
    pending_commands: int
    pending_events: int
    owner_alive: bool
    reason: str | None = None


class NodeController(Protocol):
    """The only object allowed to touch a native node, inside the owner process."""

    def start(self) -> None: ...

    def submit(self, order: object) -> None: ...

    def protect(self, reason: str) -> None: ...

    def stop(self) -> None: ...

    def dispose(self) -> None: ...


class NodeFactory(Protocol):
    """A trusted, top-level factory; it is invoked only in the child process."""

    def __call__(self) -> NodeController: ...


@dataclass(frozen=True)
class _Command:
    sequence: int
    action: Literal["submit", "protect", "stop"]
    payload: object | None = None


@dataclass(frozen=True)
class _Reply:
    sequence: int
    state: Literal["running", "protected", "stopped", "failed"]
    heartbeat_ns: int
    reason: str | None = None


def _safe_reply(replies: object, reply: _Reply) -> None:
    """Best-effort fixed-shape reporting; never serialize an exception."""

    try:
        replies.put_nowait(reply)  # type: ignore[attr-defined]
    except (Full, OSError, ValueError):
        pass


def _owner_main(factory: NodeFactory, commands: object, replies: object) -> None:
    """Run on the child main thread, where Nautilus may register signals."""

    node: NodeController | None = None
    clean = False
    try:
        node = factory()
        node.start()
        _safe_reply(replies, _Reply(0, "running", time_ns()))
        while True:
            try:
                command = commands.get()  # type: ignore[attr-defined]
            except (EOFError, OSError):
                _safe_reply(replies, _Reply(-1, "failed", time_ns(), "owner_channel_closed"))
                return
            if not isinstance(command, _Command):
                _safe_reply(replies, _Reply(-1, "failed", time_ns(), "invalid_owner_command"))
                return
            try:
                if command.action == "submit":
                    node.submit(command.payload)
                    _safe_reply(replies, _Reply(command.sequence, "running", time_ns()))
                elif command.action == "protect":
                    if not isinstance(command.payload, str) or not command.payload:
                        raise ValueError("invalid_protection_reason")
                    node.protect(command.payload)
                    _safe_reply(replies, _Reply(command.sequence, "protected", time_ns(), command.payload))
                else:
                    node.stop()
                    node.dispose()
                    clean = True
                    _safe_reply(replies, _Reply(command.sequence, "stopped", time_ns()))
                    return
            except ValueError as exc:
                # Only stable local validation codes cross the process boundary.
                reason = str(exc) if str(exc).startswith("invalid_") else "node_command_rejected"
                _safe_reply(replies, _Reply(command.sequence, "protected", time_ns(), reason))
            except Exception:  # noqa: BLE001 - owner must report a fixed failure code
                _safe_reply(replies, _Reply(command.sequence, "failed", time_ns(), "node_command_failed"))
                return
    except Exception:  # noqa: BLE001 - owner must report a fixed failure code
        _safe_reply(replies, _Reply(0, "failed", time_ns(), "node_start_failed"))
    finally:
        if node is not None and not clean:
            try:
                node.stop()
            except Exception:  # noqa: BLE001,S110 - cleanup cannot leak an owner process
                pass
            try:
                node.dispose()
            except Exception:  # noqa: BLE001,S110 - cleanup cannot leak an owner process
                pass


class BybitRuntime:
    """Bounded, fail-closed facade for one account-owner process.

    The facade allocates no order identity and performs no retry.  A timeout,
    queue overflow, owner death or ambiguous reply protects the session and
    requires reconciliation before any caller can submit again.
    """

    def __init__(
        self,
        factory: NodeFactory,
        *,
        session_id: str,
        generation: int,
        reconciliation_revision: int = 0,
        queue_capacity: int = 128,
        timeout_seconds: float = 5.0,
    ) -> None:
        if not session_id or not isinstance(session_id, str):
            raise ValueError("invalid_session_id")
        if type(generation) is not int or generation < 0:
            raise ValueError("invalid_generation")
        if type(reconciliation_revision) is not int or reconciliation_revision < 0:
            raise ValueError("invalid_reconciliation_revision")
        if not 1 <= queue_capacity <= 10_000:
            raise ValueError("invalid_queue_capacity")
        if not 0 < timeout_seconds <= 30:
            raise ValueError("invalid_timeout")
        ctx = multiprocessing.get_context("spawn")
        self._commands = ctx.Queue(maxsize=queue_capacity)
        self._replies = ctx.Queue(maxsize=queue_capacity)
        self._process: BaseProcess = ctx.Process(
            target=_owner_main,
            args=(factory, self._commands, self._replies),
            name="bybit-native-owner",
            daemon=True,
        )
        self._timeout = timeout_seconds
        self._lock = threading.RLock()
        self._sequence = 0
        self._closed = False
        self._health = RuntimeHealth("created", session_id, generation, 0, False, reconciliation_revision, 0, 0, False)

    def _fail(self, reason: str) -> None:
        self._health = replace(self._health, state="failed", reason=reason, owner_alive=self._process.is_alive())

    def _receive(self, sequence: int) -> _Reply:
        deadline = monotonic() + self._timeout
        while monotonic() < deadline:
            try:
                reply = self._replies.get(timeout=min(0.05, max(0.001, deadline - monotonic())))
            except Empty:
                if not self._process.is_alive():
                    self._fail("owner_died")
                    raise RuntimeError("owner_died") from None
                continue
            if not isinstance(reply, _Reply) or reply.sequence != sequence:
                self._fail("owner_reply_uncertain")
                raise RuntimeError("owner_reply_uncertain")
            if reply.state == "failed":
                self._fail(reply.reason or "owner_failed")
                raise RuntimeError(self._health.reason or "owner_failed")
            self._health = replace(
                self._health,
                state=reply.state,
                heartbeat_ns=reply.heartbeat_ns,
                reason=reply.reason if reply.reason is not None else self._health.reason,
                owner_alive=self._process.is_alive(),
            )
            return reply
        self._fail("owner_timeout")
        raise RuntimeError("owner_timeout")

    def start(self) -> RuntimeHealth:
        with self._lock:
            if self._health.state != "created":
                raise RuntimeError("runtime_already_started")
            self._health = replace(self._health, state="starting")
            self._process.start()
            try:
                self._receive(0)
            except BaseException:
                self.stop()
                raise
            return self.health()

    def _send(self, action: Literal["submit", "protect", "stop"], payload: object | None = None) -> _Reply:
        self._sequence += 1
        command = _Command(self._sequence, action, payload)
        try:
            self._commands.put_nowait(command)
        except Full:
            self._fail("owner_command_queue_full")
            raise RuntimeError("owner_command_queue_full") from None
        return self._receive(self._sequence)

    def submit(self, order: object) -> RuntimeHealth:
        with self._lock:
            if self._health.state != "running":
                raise RuntimeError("runtime_protected")
            reply = self._send("submit", order)
            if reply.state != "running":
                raise RuntimeError(reply.reason or "runtime_protected")
            return self.health()

    def protect(self, reason: str) -> RuntimeHealth:
        with self._lock:
            if not isinstance(reason, str) or not reason:
                raise ValueError("invalid_protection_reason")
            if self._health.state in ("created", "stopped", "failed"):
                return self.health()
            self._health = replace(self._health, state="protected", reason=reason)
            try:
                self._send("protect", reason)
            except RuntimeError:
                self._fail("owner_protect_failed")
            return self.health()

    def health(self) -> RuntimeHealth:
        with self._lock:
            return replace(self._health, owner_alive=self._process.is_alive())

    def stop(self) -> RuntimeHealth:
        with self._lock:
            if self._closed:
                return self.health()
            prior = self._health.state
            if prior in ("running", "protected", "starting") and self._process.is_alive():
                self._health = replace(self._health, state="stopping")
                try:
                    self._send("stop")
                except RuntimeError:
                    self._fail(self._health.reason or "owner_stop_failed")
            if self._process.is_alive():
                self._process.join(self._timeout)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(self._timeout)
                self._fail("owner_stop_timeout")
            elif self._health.state == "stopping" or prior == "created":
                self._health = replace(self._health, state="stopped", owner_alive=False)
            self._closed = True
            self._commands.close()
            self._replies.close()
            self._commands.join_thread()
            self._replies.join_thread()
            return self.health()


__all__ = ["BybitRuntime", "NodeController", "NodeFactory", "RuntimeHealth", "RuntimeState"]
