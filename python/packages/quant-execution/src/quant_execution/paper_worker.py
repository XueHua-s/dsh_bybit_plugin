"""Spawn target and bounded private IPC. Never accept external pickle/callback inputs."""

import asyncio
import os
import threading
from dataclasses import dataclass
from multiprocessing import parent_process
from multiprocessing.queues import Queue
from queue import Empty, Full
from typing import Literal

from nautilus_trader.live.node import TradingNode

from .paper_models import PaperDepth, PaperEvent, PaperFixture, PaperOrder, PaperSnapshot
from .paper_native import NativePaper


@dataclass(frozen=True)
class Request:
    sequence: int
    action: Literal["submit", "cancel", "feed", "snapshot", "protect", "stop"]
    value: PaperOrder | PaperDepth | str | None = None


@dataclass(frozen=True)
class Response:
    sequence: int
    snapshot: PaperSnapshot | None
    error: str | None = None


async def _serve(
    fixture: PaperFixture | tuple[PaperFixture, ...],
    commands: Queue,
    replies: Queue,
    events: Queue,
    nodes: list[TradingNode],
) -> None:
    protected = False
    event_stream_complete = True

    def emit(event: PaperEvent) -> None:
        nonlocal protected, event_stream_complete
        try:
            events.put_nowait(event)
        except Full:
            protected = True
            event_stream_complete = False

    parent = parent_process()

    def check_parent() -> None:
        if parent is not None and not parent.is_alive():
            raise RuntimeError("paper_service_owner_lost")

    check_parent()
    native = NativePaper(fixture, emit, nodes.append)
    run_task = asyncio.create_task(native.node.run_async())
    try:
        for _ in range(500):
            check_parent()
            if native.node.is_running() and native.strategy.is_running:
                break
            if run_task.done():
                raise RuntimeError("native_start_failed")
            await asyncio.sleep(0.005)
        else:
            raise RuntimeError("native_start_timeout")
        for item in native.fixtures:
            native.feed(item.initial_depth, initial=True, symbol=item.instrument.symbol)
        await asyncio.sleep(0.01)

        def snapshot() -> PaperSnapshot:
            total, free, position, orders = native.account()
            unrealized, realized = native.pnl()
            return PaperSnapshot(
                status="protected" if protected else "running",
                account_id="SIM-001",
                balance_total=total,
                balance_free=free,
                position_quantity=position,
                open_order_ids=orders,
                process_alive=True,
                process_id=os.getpid(),
                loop_closed=False,
                node_instance_id=str(native.node.kernel.instance_id),
                market_timestamp_ns=max(item.timestamp_ns for item in native.depth_by_symbol.values()),
                bid=native.depth_by_symbol[native.fixture.instrument.symbol].bid,
                ask=native.depth_by_symbol[native.fixture.instrument.symbol].ask,
                bid_size=native.depth_by_symbol[native.fixture.instrument.symbol].bid_size,
                ask_size=native.depth_by_symbol[native.fixture.instrument.symbol].ask_size,
                failure_reason=None if event_stream_complete else "native_event_queue_full",
                event_stream_complete=event_stream_complete,
                equity=total + unrealized,
                available_equity=min(free, free + unrealized),
                unrealized_pnl=unrealized,
                realized_pnl=realized,
                snapshot_timestamp_ns=native.node.kernel.clock.timestamp_ns(),
                instruments=native.instrument_snapshots(),
            )

        replies.put_nowait(Response(0, snapshot()))
        while True:
            check_parent()
            if run_task.done():
                raise RuntimeError("native_owner_ended")
            try:
                request = commands.get_nowait()
            except Empty:
                await asyncio.sleep(0.005)
                continue
            try:
                if not isinstance(request, Request):
                    raise TypeError("invalid_private_request")
                if request.action == "stop":
                    replies.put_nowait(Response(request.sequence, snapshot()))
                    break
                if request.action == "protect":
                    protected = True
                elif request.action == "submit":
                    if protected:
                        raise RuntimeError("paper_protected")
                    if not isinstance(request.value, PaperOrder):
                        raise ValueError("invalid_private_order")
                    native.submit(request.value)
                elif request.action == "cancel":
                    if not isinstance(request.value, str):
                        raise ValueError("invalid_private_cancel")
                    native.cancel(request.value)
                elif request.action == "feed":
                    if not isinstance(request.value, PaperDepth):
                        raise ValueError("invalid_private_depth")
                    native.feed(request.value, symbol=request.value.symbol)
                await asyncio.sleep(0.01)
                replies.put_nowait(Response(request.sequence, snapshot()))
            except ValueError as exc:
                replies.put_nowait(Response(request.sequence, snapshot(), str(exc)))
            except Exception:  # noqa: BLE001 - native boundary must freeze every unexpected fault
                protected = True
                replies.put_nowait(Response(request.sequence, snapshot(), "native_dispatch_failed"))
    finally:
        await native.node.stop_async()
        await asyncio.wait_for(run_task, 2.0)


def worker_main(fixture: PaperFixture, commands: Queue, replies: Queue, events: Queue) -> None:
    """Main thread of a spawned child; official node owns only this child's signals."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    nodes: list[TradingNode] = []
    clean = False
    main_task = loop.create_task(_serve(fixture, commands, replies, events, nodes))
    watcher_stop = threading.Event()
    owner_lost = threading.Event()
    parent = parent_process()

    def watch_owner() -> None:
        # This thread remains responsive even if the native event loop blocks.
        while not watcher_stop.wait(0.05):
            if parent is not None and not parent.is_alive():
                owner_lost.set()
                try:
                    loop.call_soon_threadsafe(main_task.cancel)
                except RuntimeError:
                    pass
                if not watcher_stop.wait(2.0):
                    os._exit(70)  # only this orphan child; never signal other processes
                return

    watcher = threading.Thread(target=watch_owner, name="paper-owner-watch", daemon=True)
    watcher.start()
    try:
        loop.run_until_complete(main_task)
        clean = True
    except BaseException:  # noqa: BLE001 - child must always report failure and dispose owned resources
        try:
            replies.put_nowait(Response(-1, None, "native_worker_failed"))
        except Full:
            pass
    finally:
        for node in nodes:
            node.dispose()
        if not loop.is_closed():
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
        if owner_lost.is_set():
            replies.cancel_join_thread()
        if clean and not owner_lost.is_set():
            events.close()
            events.join_thread()
        else:
            events.cancel_join_thread()
        try:
            replies.put_nowait(Response(-2, None, None if clean else "native_cleanup_failed"))
        except Full:
            pass
        watcher_stop.set()
        watcher.join(0.2)
