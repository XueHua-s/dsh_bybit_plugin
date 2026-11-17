"""One serialized, durable authority over a synthetic account and native paper OMS."""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import threading
import time
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from quant_data.admission_contracts import AccountingModel, AdmissionDecision, NativeObservation, SessionSnapshot
from quant_data.admission_store import AdmissionStore
from quant_data.commands import (
    CommandRecord,
    CommandState,
    Environment,
    LedgerConflict,
    OrderCommand,
    OrderType,
    RiskCode,
    Side,
)
from quant_data.ledger import CommandLedger
from quant_execution.paper_models import PaperOrder
from quant_execution.paper_runtime import PaperRuntime
from quant_risk.evaluator import evaluate
from quant_risk.models import OrderIntent
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from .paper_api_models import PaperStatus, SubmitRequest
from .paper_config import PaperConfig
from .paper_context import risk_context


class PaperUnavailable(RuntimeError):
    """Fixed safe boundary error; original exceptions never enter HTTP responses."""


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, default=str, sort_keys=True).encode()).hexdigest()


class PaperAdmission:
    """Hide ownership, risk generations, reservation and event persistence behind proposals.

    A threading lock serializes background native ingestion, all admissions and lifecycle.
    The bounded async entrance limits pending requests; HTTP lifetime never owns an order.
    Restart always protects a previous session, because native Sandbox cannot replay it.
    """

    def __init__(self, config: PaperConfig) -> None:
        self.config = config
        self._owner = str(uuid4())
        self._lock = threading.RLock()
        self._file: int | None = None
        self._state = "idle"
        self._store: AdmissionStore | None = None
        self._ledger: CommandLedger | None = None
        self._runtime: PaperRuntime | None = None
        self._snapshot: SessionSnapshot | None = None
        self._poll: asyncio.Task[None] | None = None
        self._pending = 0
        self._ids: dict[str, str] = {}
        self._totals: dict[str, tuple[Decimal, Decimal]] = {}
        self._peak_equity = config.fixture.starting_balance
        self._consumed_bid = Decimal(0)
        self._consumed_ask = Decimal(0)

    async def open(self) -> None:
        await asyncio.to_thread(self._open)
        self._poll = asyncio.create_task(self._ingest_loop(), name="paper-native-ingestion")

    def _open(self) -> None:
        import os

        path = self.config.database.resolve()
        if not path.is_file() or path.is_symlink():
            raise PaperUnavailable("pre_migrated_isolated_database_required")
        fd = os.open(Path(str(path) + ".paper.lock"), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
            with engine.connect() as connection:
                if connection.scalar(text("select version_num from alembic_version")) != "0004_admission_state":
                    raise PaperUnavailable("paper_schema_required")
            sessions = sessionmaker(engine, expire_on_commit=False)
            self._store = AdmissionStore(sessions)
            self._ledger = CommandLedger(sessions)
            self._snapshot = self._store.open_session(
                Environment.INTERNAL_PAPER,
                self.config.session_id,
                self.config.session_id,
                self._owner,
                _digest({"policy": asdict(self.config.policy), "accounting": "linear_perpetual"}),
                self.config.fixture.starting_balance,
                AccountingModel.LINEAR_PERPETUAL,
            )
            self._file = fd
            self._state = "protected" if self._snapshot.protected else "idle"
        except Exception:  # noqa: BLE001 - fail closed at native/persistence boundary
            os.close(fd)
            raise PaperUnavailable("paper_database_or_ownership_unavailable") from None

    async def start(self) -> PaperStatus:
        return await asyncio.to_thread(self._start)

    def _start(self) -> PaperStatus:
        with self._lock:
            if self._state == "running":
                return self._status()
            if self._state != "idle":
                raise PaperUnavailable("explicit_new_session_required")
            try:
                self._runtime = PaperRuntime(self.config.fixture)
                native = self._runtime.start()
                if native.account_id != self.config.policy.account_id or not native.process_alive:
                    raise PaperUnavailable("native_account_unavailable")
                self._state = "running"
            except Exception:  # noqa: BLE001 - fail closed at native/persistence boundary
                self._protect("native_start_failed")
                raise PaperUnavailable("native_start_failed") from None
            return self._status()

    async def submit(self, request: SubmitRequest) -> CommandRecord:
        if self._pending >= self.config.queue_capacity:
            raise PaperUnavailable("admission_queue_full")
        self._pending += 1
        job = asyncio.create_task(asyncio.to_thread(self._submit_guarded, request))
        try:
            return await asyncio.shield(job)
        finally:
            if job.done():
                self._pending -= 1
            else:

                def completed(task: asyncio.Task[CommandRecord]) -> None:
                    self._pending -= 1
                    if not task.cancelled():
                        task.exception()  # Caller disconnect cannot orphan an unobserved failure.

                job.add_done_callback(completed)

    def _submit_guarded(self, request: SubmitRequest) -> CommandRecord:
        with self._lock:
            try:
                return self._submit(request)
            except LedgerConflict:
                raise
            except Exception:  # noqa: BLE001 - native/persistence uncertainty freezes before releasing writer
                self._protect("admission_or_dispatch_failed")
                raise PaperUnavailable("admission_or_dispatch_failed") from None

    def _submit(self, request: SubmitRequest) -> CommandRecord:
        with self._lock:
            store, ledger, runtime = self._required()
            self._drain()
            if self._state != "running":
                raise PaperUnavailable("paper_not_running")
            command = OrderCommand(
                Environment.INTERNAL_PAPER,
                self.config.session_id,
                request.request_id,
                request.symbol,
                Side(request.side),
                OrderType.LIMIT,
                Decimal(request.quantity),
                Decimal(request.limit_price),
            )
            now = time.time_ns()
            durable = store.snapshot(self.config.session_id, self._owner)
            native = runtime.snapshot()
            now = time.time_ns()
            self._peak_equity = max(self._peak_equity, native.equity)
            position = sum((item.quantity for item in durable.positions), Decimal(0))
            if (
                not native.process_alive
                or native.status != "running"
                or not native.event_stream_complete
                or native.failure_reason is not None
                or position != native.position_quantity
                or abs(durable.balance - native.balance_total) > Decimal("0.00000001")
                or abs(durable.realized_pnl - durable.cumulative_fee - native.realized_pnl) > Decimal("0.00000001")
            ):
                self._protect("native_reconciliation_required")
                raise PaperUnavailable("native_reconciliation_required")
            intent = OrderIntent(
                request.request_id,
                request.symbol,
                "BUY" if request.side == "buy" else "SELL",
                command.quantity,
                Decimal(request.limit_price),
                Decimal(1),
            )
            context = risk_context(
                self.config,
                durable,
                native,
                intent,
                now // 1_000_000,
                self._consumed_bid,
                self._consumed_ask,
                self._peak_equity,
            )
            decision = evaluate(intent, context, self.config.policy)
            plan = decision.approved_plan
            expires = now + 1 if plan is None else plan.expires_at_ms * 1_000_000
            evidence = AdmissionDecision(
                decision.approved,
                RiskCode.APPROVED if decision.approved else RiskCode.LIMIT,
                _digest(asdict(self.config.policy)),
                _digest(asdict(context)),
                now,
                expires,
                max(native.ask, Decimal(request.limit_price)),
                decision.reasons,
            )
            try:
                record = store.decide(self.config.session_id, self._owner, durable.generation, command, evidence)
                if record.state != CommandState.READY:
                    return record
                current = store.snapshot(self.config.session_id, self._owner)
                if current.generation != durable.generation + 1 or time.time_ns() > expires:
                    self._protect("risk_context_expired")
                    raise PaperUnavailable("risk_context_expired")
                claimed, record = store.claim_dispatch(
                    self.config.session_id, self._owner, current.generation, record.id, time.time_ns()
                )
                if not claimed and store.snapshot(self.config.session_id, self._owner).protected:
                    self._protect("dispatch_authority_protected")
                    raise PaperUnavailable("dispatch_authority_protected")
                if claimed:
                    self._ids[record.native_client_order_id] = record.id
                    runtime.submit(
                        PaperOrder(record.native_client_order_id, intent.side, command.quantity, command.limit_price)
                    )
                self._drain()
                return ledger.get(record.id)
            except LedgerConflict:
                raise
            except Exception:  # noqa: BLE001 - fail closed at native/persistence boundary
                self._protect("admission_or_dispatch_failed")
                raise PaperUnavailable("admission_or_dispatch_failed") from None

    def _required(self) -> tuple[AdmissionStore, CommandLedger, PaperRuntime]:
        if self._store is None or self._ledger is None or self._runtime is None:
            raise PaperUnavailable("paper_not_running")
        return self._store, self._ledger, self._runtime

    def _drain(self) -> None:
        store, ledger, runtime = self._required()
        for event in runtime.read_events():
            command_id = self._ids.get(event.client_order_id)
            if command_id is None:
                self._protect("unknown_native_event")
                raise PaperUnavailable("unknown_native_event")
            # Native initialization/submission are not venue acceptance. Lifecycle events
            # are projected only when they carry an authoritative state supported by ledger.
            states = {
                "ACCEPTED": CommandState.ACCEPTED,
                "PARTIALLY_FILLED": CommandState.PARTIALLY_FILLED,
                "FILLED": CommandState.FILLED,
                "CANCELED": CommandState.CANCELLED,
                "CANCELLED": CommandState.CANCELLED,
                "REJECTED": CommandState.REJECTED,
                "DENIED": CommandState.REJECTED,
            }
            state = (
                states.get(event.status)
                if event.event_type
                in {"OrderAccepted", "OrderFilled", "OrderCanceled", "OrderRejected", "OrderDenied", "OrderExpired"}
                else None
            )
            if state is None:
                store.record_native(
                    self.config.session_id,
                    self._owner,
                    command_id,
                    event.event_id,
                    event.event_type,
                    event.timestamp_ns,
                )
                continue
            notional, fee = self._totals.get(command_id, (Decimal(0), Decimal(0)))
            if event.last_fill_quantity:
                notional += event.last_fill_quantity * (event.last_fill_price or Decimal(0))
                fee += event.commission or Decimal(0)
                command = ledger.get(command_id).command
                if command.side == Side.BUY:
                    self._consumed_ask += event.last_fill_quantity
                else:
                    self._consumed_bid += event.last_fill_quantity
            self._totals[command_id] = (notional, fee)
            store.observe(
                self.config.session_id,
                self._owner,
                NativeObservation(
                    command_id,
                    event.event_id,
                    state,
                    event.cumulative_filled_quantity,
                    notional,
                    fee,
                    event.timestamp_ns,
                ),
            )

    async def _ingest_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(0.01)
                await asyncio.to_thread(self._ingest)
        except asyncio.CancelledError:
            return

    def _ingest(self) -> None:
        with self._lock:
            if self._runtime is None or self._state not in {"running", "stopping"}:
                return
            try:
                self._drain()
                native = self._runtime.snapshot()
                self._peak_equity = max(self._peak_equity, native.equity)
                if (
                    not native.process_alive
                    or native.status != "running"
                    or not native.event_stream_complete
                    or native.failure_reason is not None
                ):
                    self._protect("native_worker_stopped")
            except Exception:  # noqa: BLE001 - fail closed at native/persistence boundary
                self._protect("native_event_persistence_failed")

    def _protect(self, reason: str) -> None:
        self._state = "protected"
        if self._runtime is not None:
            try:
                self._runtime.protect()
            except Exception:  # noqa: BLE001 - persist protection even if native IPC failed
                self._state = "protected"
        if self._store is not None:
            try:
                self._snapshot = self._store.protect(self.config.session_id, self._owner, reason)
            except Exception:  # noqa: BLE001 - fail closed at native/persistence boundary
                self._state = "protected"  # Durability unavailable; memory remains frozen.

    async def get(self, command_id: str) -> CommandRecord:
        def lookup() -> CommandRecord:
            with self._lock:
                if self._ledger is None:
                    raise PaperUnavailable("database_unavailable")
                if self._store is None:
                    raise PaperUnavailable("database_unavailable")
                try:
                    result = self._store.get(command_id, self.config.session_id, self._owner)
                except ValueError:
                    raise KeyError("unknown_command") from None
                except SQLAlchemyError:
                    self._protect("command_read_failed")
                    raise PaperUnavailable("command_read_failed") from None
                if result.command.account_ref != self.config.session_id:
                    raise KeyError("unknown_command")
                return result

        return await asyncio.to_thread(lookup)

    async def get_by_request(self, request_id: str) -> CommandRecord:
        def lookup() -> CommandRecord:
            with self._lock:
                if self._store is None:
                    raise PaperUnavailable("database_unavailable")
                try:
                    return self._store.get_by_request(request_id, self.config.session_id, self._owner)
                except SQLAlchemyError:
                    self._protect("command_read_failed")
                    raise PaperUnavailable("command_read_failed") from None

        return await asyncio.to_thread(lookup)

    async def status(self) -> PaperStatus:
        return await asyncio.to_thread(self._locked_status)

    def _locked_status(self) -> PaperStatus:
        with self._lock:
            return self._status()

    def _status(self) -> PaperStatus:
        if self._store is not None:
            try:
                self._snapshot = self._store.snapshot(self.config.session_id, self._owner)
            except Exception:  # noqa: BLE001 - fixed error after freezing on failed observation
                self._protect("status_persistence_failed")
                raise PaperUnavailable("status_unavailable") from None
        if self._snapshot is not None and self._snapshot.protected and self._state not in {"protected", "stopped"}:
            self._protect("durable_session_protected")
        try:
            native = None if self._runtime is None else self._runtime.snapshot()
        except Exception:  # noqa: BLE001 - native status uncertainty is protected and redacted
            self._protect("native_status_unavailable")
            raise PaperUnavailable("native_status_unavailable") from None
        return PaperStatus(
            session_id=self.config.session_id,
            state=self._state,  # type: ignore[arg-type]
            ready=(
                self._state == "running"
                and self._snapshot is not None
                and not self._snapshot.protected
                and native is not None
                and native.process_alive
                and native.status == "running"
                and native.event_stream_complete
                and native.failure_reason is None
                and time.time_ns() - native.market_timestamp_ns <= self.config.policy.snapshot_ttl_ms * 1_000_000
            ),
            native_process_alive=native is not None and native.process_alive,
            generation=0 if self._snapshot is None else self._snapshot.generation,
            pending_reservations=0 if self._snapshot is None else len(self._snapshot.reservations),
        )

    async def stop(self) -> PaperStatus:
        return await asyncio.to_thread(self._stop)

    def _stop(self) -> PaperStatus:
        with self._lock:
            if self._state == "stopped":
                return self._status()
            self._state = "stopping"
            failed = False
            if self._runtime is not None:
                try:
                    self._runtime.protect()
                    for order_id in self._runtime.snapshot().open_order_ids:
                        self._runtime.cancel(order_id)
                    self._drain()
                except Exception:  # noqa: BLE001 - shutdown must still reap native after cancellation/event failure
                    failed = True
                finally:
                    try:
                        native = self._runtime.stop()
                        self._drain()
                        failed = (
                            failed or native.process_alive or not native.loop_closed or not native.event_stream_complete
                        )
                    except Exception:  # noqa: BLE001 - failed native disposal stays protected
                        failed = True
            self._protect("native_stop_incomplete" if failed else "session_stopped_requires_new_session")
            if not failed:
                self._state = "stopped"
            return self._status()

    async def close(self) -> None:
        import os

        try:
            if self._poll is not None:
                self._poll.cancel()
                await self._poll
            await self.stop()
        finally:
            if self._file is not None:
                os.close(self._file)
                self._file = None
