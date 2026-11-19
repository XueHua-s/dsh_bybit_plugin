"""Bounded synchronous facade for one continuous native internal-paper session.

The service owns this object independently of client and Tool lifetimes. Timeout or
worker loss freezes submissions; this facade never retries an ambiguous command.
"""

import multiprocessing
import threading
from dataclasses import replace
from decimal import Decimal
from multiprocessing.process import BaseProcess
from queue import Empty, Full
from time import monotonic
from typing import Literal

from .paper_models import PaperDepth, PaperEvent, PaperFixture, PaperOrder, PaperSnapshot
from .paper_worker import Request, Response, worker_main


class PaperRuntime:
    def __init__(
        self,
        fixture: PaperFixture,
        *,
        queue_capacity: int = 128,
        event_capacity: int = 4096,
        timeout_seconds: float = 5.0,
    ) -> None:
        if not 1 <= queue_capacity <= 10000 or not 1 <= event_capacity <= 100000:
            raise ValueError("invalid_queue_capacity")
        if not 0 < timeout_seconds <= 30:
            raise ValueError("invalid_timeout")
        self._fixture = fixture
        self._timeout = timeout_seconds
        ctx = multiprocessing.get_context("spawn")
        self._commands = ctx.Queue(maxsize=queue_capacity)
        self._replies = ctx.Queue(maxsize=queue_capacity)
        self._events = ctx.Queue(maxsize=event_capacity)
        self._process: BaseProcess = ctx.Process(
            target=worker_main,
            args=(fixture, self._commands, self._replies, self._events),
            name="quant-paper-native",
            daemon=True,
        )
        self._lock = threading.RLock()
        self._sequence = 0
        self._status = "created"
        self._closed = False
        self._loop_closed = False
        self._failure_reason: str | None = None
        self._event_stream_complete = True
        self._last: PaperSnapshot | None = None
        self._pending_events: list[PaperEvent] = []

    def _receive(self, sequence: int) -> PaperSnapshot:
        deadline = monotonic() + self._timeout
        while monotonic() < deadline:
            try:
                response = self._replies.get(timeout=min(0.05, max(0.001, deadline - monotonic())))
            except Empty:
                if self._process.exitcode is not None:
                    break
                continue
            if not isinstance(response, Response) or response.sequence != sequence:
                self._status = "failed"
                self._failure_reason = "native_response_uncertain"
                self._event_stream_complete = False
                raise RuntimeError("native_response_uncertain")
            if response.snapshot is not None:
                self._last = response.snapshot
            if response.error is not None:
                if response.error.startswith(("invalid_", "duplicate_", "unknown_", "crossed_", "nonmonotonic_")):
                    raise ValueError(response.error)
                self._status = "protected"
                self._failure_reason = response.error
                self._event_stream_complete = False
                raise RuntimeError(response.error)
            assert response.snapshot is not None
            if response.snapshot.status == "protected":
                self._status = "protected"
            return response.snapshot
        self._status = "failed"
        self._failure_reason = "native_response_timeout_or_worker_lost"
        self._event_stream_complete = False
        raise RuntimeError("native_response_timeout_or_worker_lost")

    def start(self) -> PaperSnapshot:
        """Start once; old native sessions are never reconstructed from empty reports."""
        with self._lock:
            if self._status != "created":
                raise RuntimeError("paper_already_started")
            self._status = "starting"
            self._process.start()
            try:
                self._receive(0)
                self._status = "running"
                return self._view()
            except BaseException:
                self._status = "failed"
                self._reap(force=True)
                raise

    def _request(
        self,
        action: Literal["submit", "cancel", "feed", "snapshot", "protect", "stop"],
        value: PaperOrder | PaperDepth | str | None = None,
    ) -> None:
        if self._closed or self._status not in ("running", "protected"):
            raise RuntimeError("paper_not_running")
        if action == "submit" and self._status != "running":
            raise RuntimeError("paper_protected")
        self._sequence += 1
        try:
            self._commands.put_nowait(Request(self._sequence, action, value))
        except Full:
            self._status = "protected"
            raise RuntimeError("native_command_queue_full") from None
        self._receive(self._sequence)

    def submit(self, order: PaperOrder) -> None:
        """Dispatch exactly the supplied ledger identity once; no new-ID retry."""
        with self._lock:
            self._request("submit", order)

    def cancel(self, client_order_id: str) -> None:
        with self._lock:
            self._request("cancel", client_order_id)

    def feed(self, depth: PaperDepth) -> None:
        """Provide a complete explicit later synthetic snapshot, never auto-replenish."""
        with self._lock:
            self._request("feed", depth)

    def protect(self) -> None:
        with self._lock:
            if self._status == "running":
                self._status = "protected"
                self._request("protect")

    def _drain_events(self) -> list[PaperEvent]:
        result: list[PaperEvent] = []
        while True:
            try:
                event = self._events.get_nowait()
            except Empty:
                break
            if not isinstance(event, PaperEvent):
                self._status = "protected"
                raise TypeError("invalid_native_event")
            result.append(event)
        return result

    def read_events(self) -> tuple[PaperEvent, ...]:
        """Consume native evidence, including pending events retained across clean stop."""
        with self._lock:
            result = self._pending_events
            self._pending_events = []
            if not self._closed:
                result.extend(self._drain_events())
            return tuple(result)

    def _view(self) -> PaperSnapshot:
        if self._last is None:
            d = self._fixture.initial_depth
            self._last = PaperSnapshot(
                self._status,
                "SIM-001",
                Decimal(0),
                Decimal(0),
                Decimal(0),
                (),
                False,
                self._process.pid,
                self._closed,
                "",
                d.timestamp_ns,
                d.bid,
                d.ask,
                d.bid_size,
                d.ask_size,
            )
        return replace(
            self._last,
            status=self._status,
            process_alive=self._process.is_alive(),
            process_id=self._process.pid,
            loop_closed=self._loop_closed,
            failure_reason=self._failure_reason or self._last.failure_reason,
            event_stream_complete=self._event_stream_complete and self._last.event_stream_complete,
        )

    def snapshot(self) -> PaperSnapshot:
        with self._lock:
            if self._status in ("running", "protected"):
                self._request("snapshot")
            return self._view()

    def _reap(self, *, force: bool) -> bool:
        if self._process.pid is not None:
            if force and self._process.is_alive():
                self._process.terminate()
            deadline = monotonic() + self._timeout
            while self._process.is_alive() and monotonic() < deadline:
                self._pending_events.extend(self._drain_events())
                self._process.join(0.01)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(self._timeout)
            self._pending_events.extend(self._drain_events())
        clean = False
        while True:
            try:
                reply = self._replies.get_nowait()
            except Empty:
                break
            if isinstance(reply, Response) and reply.sequence == -2 and reply.error is None:
                clean = True
        for queue in (self._commands, self._replies, self._events):
            queue.cancel_join_thread()
            queue.close()
        self._closed = True
        self._loop_closed = clean and self._process.exitcode == 0 and not self._process.is_alive()
        return self._loop_closed

    def stop(self) -> PaperSnapshot:
        """Freeze dispatch and verify cleanup handshake plus actual child join."""
        with self._lock:
            if self._closed:
                return self._view()
            clean = False
            if self._status in ("running", "protected"):
                try:
                    self._request("stop")
                    self._status = "stopping"
                    clean = self._reap(force=False)
                except Exception:  # noqa: BLE001 - cleanup must reap child after any transport failure
                    self._status = "failed"
                    self._reap(force=True)
            else:
                clean = self._status == "created"
                self._reap(force=True)
            stream_complete = self._event_stream_complete and (self._last is None or self._last.event_stream_complete)
            self._status = "stopped" if clean and stream_complete else "failed"
            return self._view()
