"""Lifecycle state with an optional durable checkpoint."""

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

CHECKPOINT_VERSION = 2


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """Immutable health facts suitable for a status endpoint."""

    running: bool
    started_at: str | None
    stopped_at: str | None
    queue_depth: int
    reconnects: int
    checkpoint_version: int
    recovered: bool
    checkpoint_error: str | None


class EngineRuntime:
    """Own lifecycle state and persist restart-safe health counters."""

    def __init__(self, checkpoint_path: Path | None = None) -> None:
        self._checkpoint_path = checkpoint_path
        self._running = False
        self._started_at: str | None = None
        self._stopped_at: str | None = None
        self._queue_depth = 0
        self._reconnects = 0
        self._recovered = False
        self._checkpoint_error: str | None = None

    def start(self) -> RuntimeSnapshot:
        if not self._running:
            recovered = self._restore_checkpoint()
            self._running = True
            self._started_at = _now()
            self._stopped_at = None
            self._recovered = recovered
        return self.snapshot()

    def stop(self) -> RuntimeSnapshot:
        if not self._running:
            return self.snapshot()
        self._running = False
        self._stopped_at = _now()
        snapshot = self.snapshot()
        if self._checkpoint_path is not None:
            self._write_checkpoint(snapshot)
        return snapshot

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
            checkpoint_version=CHECKPOINT_VERSION,
            recovered=self._recovered,
            checkpoint_error=self._checkpoint_error,
        )

    def _restore_checkpoint(self) -> bool:
        path = self._checkpoint_path
        self._queue_depth = 0
        if path is None or not path.exists():
            self._checkpoint_error = None
            return False
        try:
            with path.open(encoding="utf-8") as stream:
                payload = json.load(stream)
            self._apply_checkpoint(payload)
            self._checkpoint_error = None
        except (OSError, ValueError, TypeError, KeyError) as error:
            self._queue_depth = 0
            self._reconnects = 0
            self._stopped_at = None
            self._checkpoint_error = f"invalid checkpoint: {type(error).__name__}"
            return False
        return True

    def _apply_checkpoint(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise TypeError("invalid checkpoint payload")
        version = payload.get("version")
        if type(version) is not int or version not in (1, CHECKPOINT_VERSION):
            raise ValueError("unsupported checkpoint version")
        required_fields = {"version", "reconnects"}
        if version == 1:
            required_fields.update(("running", "started_at", "stopped_at", "queue_depth"))
        if not required_fields.issubset(payload):
            raise ValueError("incomplete checkpoint")
        reconnects = payload.get("reconnects")
        if type(reconnects) is not int or reconnects < 0:
            raise ValueError("invalid reconnect count")
        if version == 1:
            if payload.get("running") is not False:
                raise ValueError("invalid running state")
            for field in ("started_at", "stopped_at"):
                value = payload.get(field)
                _validate_timestamp(value, field)
            queue_depth = payload.get("queue_depth")
            if type(queue_depth) is not int or queue_depth < 0:
                raise ValueError("invalid legacy queue depth")
        self._queue_depth = 0
        self._reconnects = reconnects
        self._stopped_at = None

    def _write_checkpoint(self, snapshot: RuntimeSnapshot) -> None:
        path = self._checkpoint_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": CHECKPOINT_VERSION,
            "reconnects": snapshot.reconnects,
        }
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, separators=(",", ":"), sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, path)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_timestamp(value: object, field: str) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(f"invalid {field.replace('_', ' ')}")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"invalid {field.replace('_', ' ')}") from error
    if timestamp.utcoffset() is None:
        raise ValueError(f"invalid {field.replace('_', ' ')}")
