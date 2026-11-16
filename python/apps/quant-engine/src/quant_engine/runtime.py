"""Small lifecycle core; transport and exchange adapters live outside this module."""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """Immutable health facts suitable for a status endpoint."""

    running: bool
    started_at: str | None
    stopped_at: str | None
    queue_depth: int
    reconnects: int


class EngineRuntime:
    """Owns lifecycle state and leaves long-running work to explicit services."""

    def __init__(self) -> None:
        self._running = False
        self._started_at: str | None = None
        self._stopped_at: str | None = None
        self._queue_depth = 0
        self._reconnects = 0

    def start(self) -> RuntimeSnapshot:
        if not self._running:
            self._running = True
            self._started_at = _now()
            self._stopped_at = None
        return self.snapshot()

    def stop(self) -> RuntimeSnapshot:
        if self._running:
            self._running = False
            self._stopped_at = _now()
        return self.snapshot()

    def set_queue_depth(self, depth: int) -> None:
        self._queue_depth = max(0, depth)

    def record_reconnect(self) -> None:
        self._reconnects += 1

    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            running=self._running,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            queue_depth=self._queue_depth,
            reconnects=self._reconnects,
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()
