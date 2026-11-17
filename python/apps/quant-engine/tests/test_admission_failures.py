"""Native account authority cannot escape durable reservation and failure protection."""

import asyncio
from pathlib import Path

import pytest
from quant_engine.paper_admission import PaperAdmission, PaperUnavailable
from test_admission import config_at, proposal


def test_claim_failure_protects_without_native_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        service = PaperAdmission(config_at(tmp_path))
        await service.open()
        try:
            await service.start()
            assert service._store is not None and service._runtime is not None
            calls: list[object] = []
            monkeypatch.setattr(service._runtime, "submit", calls.append)

            def failed_claim(*_args: object) -> None:
                raise RuntimeError("synthetic_persistence_failure")

            monkeypatch.setattr(service._store, "claim_dispatch", failed_claim)
            with pytest.raises(PaperUnavailable):
                await service.submit(proposal())
            assert not calls
            status = await service.status()
            assert status.state == "protected"
            assert status.pending_reservations == 1
        finally:
            await service.close()

    asyncio.run(scenario())


def test_native_protect_failure_still_persists_and_reaps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        service = PaperAdmission(config_at(tmp_path))
        await service.open()
        await service.start()
        assert service._runtime is not None

        def fail() -> None:
            raise RuntimeError("synthetic_native_ipc_failure")

        monkeypatch.setattr(service._runtime, "protect", fail)
        service._protect("synthetic_protect_test")
        status = await service.status()
        assert status.state == "protected"
        await service.close()
        assert not (await service.status()).native_process_alive

    asyncio.run(scenario())


def test_initial_drain_persistence_failure_protects_before_next_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        service = PaperAdmission(config_at(tmp_path))
        await service.open()
        try:
            await service.start()
            assert service._runtime is not None
            dispatched: list[object] = []
            monkeypatch.setattr(service._runtime, "submit", dispatched.append)

            def fail() -> None:
                raise RuntimeError("synthetic_event_commit_failure")

            monkeypatch.setattr(service, "_drain", fail)
            with pytest.raises(PaperUnavailable):
                await service.submit(proposal())
            assert not dispatched
            assert (await service.status()).state == "protected"
        finally:
            await service.close()

    asyncio.run(scenario())


def test_expired_claim_durable_protection_freezes_native_and_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        service = PaperAdmission(config_at(tmp_path))
        await service.open()
        try:
            await service.start()
            assert service._store is not None and service._runtime is not None
            original = service._store.claim_dispatch
            dispatched: list[object] = []
            monkeypatch.setattr(service._runtime, "submit", dispatched.append)

            def expired(session_id: str, owner_id: str, generation: int, command_id: str, now_ns: int):
                return original(session_id, owner_id, generation, command_id, now_ns + 60_000_000_001)

            monkeypatch.setattr(service._store, "claim_dispatch", expired)
            with pytest.raises(PaperUnavailable):
                await service.submit(proposal())
            assert not dispatched
            status = await service.status()
            assert status.state == "protected"
            assert not status.ready
        finally:
            await service.close()

    asyncio.run(scenario())
