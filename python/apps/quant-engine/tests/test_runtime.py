import json

from quant_engine import EngineRuntime


def test_runtime_starts_and_stops_cleanly() -> None:
    runtime = EngineRuntime()
    assert runtime.snapshot().running is False
    started = runtime.start()
    assert started.running is True
    assert started.started_at is not None
    stopped = runtime.stop()
    assert stopped.running is False
    assert stopped.stopped_at is not None


def test_runtime_clamps_queue_and_counts_reconnects() -> None:
    runtime = EngineRuntime()
    runtime.set_queue_depth(-3)
    runtime.record_reconnect()
    runtime.record_reconnect()
    snapshot = runtime.snapshot()
    assert snapshot.queue_depth == 0
    assert snapshot.reconnects == 2


def test_runtime_restores_health_counters_after_restart(tmp_path) -> None:
    checkpoint = tmp_path / "runtime.json"
    first = EngineRuntime(checkpoint)
    first.start()
    first.set_queue_depth(7)
    first.record_reconnect()
    first.record_reconnect()
    first.stop()
    saved = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert saved["version"] == 2
    assert "queue_depth" not in saved
    assert "started_at" not in saved
    assert "stopped_at" not in saved
    assert saved == {"version": 2, "reconnects": 2}

    restarted = EngineRuntime(checkpoint)
    snapshot = restarted.start()

    assert snapshot.running is True
    assert snapshot.queue_depth == 0
    assert snapshot.reconnects == 2
    assert snapshot.started_at is not None
    assert snapshot.started_at != first.snapshot().started_at
    assert snapshot.stopped_at is None
    assert snapshot.recovered is True
    assert snapshot.checkpoint_error is None


def test_runtime_rejects_corrupted_checkpoint_and_fails_closed(tmp_path) -> None:
    checkpoint = tmp_path / "runtime.json"
    checkpoint.write_text("{not-json", encoding="utf-8")

    runtime = EngineRuntime(checkpoint)
    snapshot = runtime.start()

    assert snapshot.running is True
    assert snapshot.queue_depth == 0
    assert snapshot.reconnects == 0
    assert snapshot.recovered is False
    assert snapshot.checkpoint_error == "invalid checkpoint: JSONDecodeError"


def test_runtime_rejects_schema_tampering(tmp_path) -> None:
    checkpoint = tmp_path / "runtime.json"
    checkpoint.write_text(
        json.dumps(
            {
                "version": 2,
                "reconnects": True,
            }
        ),
        encoding="utf-8",
    )

    snapshot = EngineRuntime(checkpoint).start()

    assert snapshot.recovered is False
    assert snapshot.queue_depth == 0
    assert snapshot.reconnects == 0
    assert snapshot.checkpoint_error == "invalid checkpoint: ValueError"


def test_runtime_rejects_boolean_checkpoint_version(tmp_path) -> None:
    checkpoint = tmp_path / "runtime.json"
    checkpoint.write_text(
        json.dumps(
            {
                "version": True,
                "running": False,
                "started_at": None,
                "stopped_at": None,
                "reconnects": 0,
            }
        ),
        encoding="utf-8",
    )

    snapshot = EngineRuntime(checkpoint).start()

    assert snapshot.recovered is False
    assert snapshot.reconnects == 0
    assert snapshot.checkpoint_error == "invalid checkpoint: ValueError"


def test_runtime_rejects_missing_checkpoint_fields(tmp_path) -> None:
    checkpoint = tmp_path / "runtime.json"
    checkpoint.write_text(
        json.dumps({"version": 2}),
        encoding="utf-8",
    )

    snapshot = EngineRuntime(checkpoint).start()

    assert snapshot.recovered is False
    assert snapshot.reconnects == 0
    assert snapshot.checkpoint_error == "invalid checkpoint: ValueError"


def test_runtime_reads_legacy_checkpoint_without_restoring_queue_depth(tmp_path) -> None:
    checkpoint = tmp_path / "runtime.json"
    checkpoint.write_text(
        json.dumps(
            {
                "version": 1,
                "running": False,
                "started_at": "2000-01-01T00:00:00+00:00",
                "stopped_at": "2000-01-01T00:01:00+00:00",
                "queue_depth": 9,
                "reconnects": 3,
            }
        ),
        encoding="utf-8",
    )

    snapshot = EngineRuntime(checkpoint).start()

    assert snapshot.recovered is True
    assert snapshot.queue_depth == 0
    assert snapshot.reconnects == 3
    assert snapshot.started_at is not None
    assert snapshot.started_at != "2000-01-01T00:00:00+00:00"
    assert snapshot.stopped_at is None
