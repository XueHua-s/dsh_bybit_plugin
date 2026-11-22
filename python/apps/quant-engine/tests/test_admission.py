"""Isolated migrated SQLite and real native/evaluator paper admission evidence."""

import asyncio
import sqlite3
from contextlib import closing
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from time import time_ns

import pytest
from quant_data.commands import CommandState
from quant_data.migrations import upgrade_sqlite
from quant_engine.paper_admission import PaperAdmission, PaperUnavailable
from quant_engine.paper_api_models import SubmitRequest
from quant_engine.paper_config import synthetic_config
from quant_engine.paper_context import risk_context
from quant_execution.models import InstrumentSpec
from quant_execution.paper_models import PaperDepth, PaperFixture
from quant_risk.evaluator import evaluate
from quant_risk.models import Correlation, OrderIntent


def config_at(tmp_path: Path):
    database = tmp_path / "paper.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA user_version=0")
    upgrade_sqlite(database)
    return synthetic_config(database, "session-fixture")


def proposal(request_id: str = "req-1", *, symbol: str = "BTCUSDT", **values: str) -> SubmitRequest:
    return SubmitRequest(
        environment="internal_paper",
        session_id="session-fixture",
        request_id=request_id,
        symbol=symbol,
        side="buy",
        order_type="limit",
        quantity=values.get("quantity", "0.001"),
        limit_price=values.get("limit_price", "50000"),
    )


async def settled(service: PaperAdmission, command_id: str):
    async with asyncio.timeout(8):
        while True:
            result = await service.get(command_id)
            if result.state in {CommandState.FILLED, CommandState.RISK_REJECTED, CommandState.REJECTED}:
                return result
            await asyncio.sleep(0.02)


def test_two_symbol_admission_uses_matching_fixture_quotes_and_positions(tmp_path: Path) -> None:
    async def scenario() -> None:
        config = config_at(tmp_path)
        alpha = PaperFixture(
            InstrumentSpec(
                "ALPHA-PERP", "ALPHA", Decimal("0.001"), Decimal("0.1"), Decimal("0.1"), Decimal(100), Decimal(5)
            ),
            PaperDepth(
                Decimal("10.000"), Decimal("10.001"), Decimal("5.000"), Decimal("5.000"), time_ns(), "ALPHA-PERP"
            ),
            Decimal(10000),
        )
        beta = PaperFixture(
            InstrumentSpec(
                "BETA.PERP", "BETA", Decimal("0.001"), Decimal("0.01"), Decimal("0.01"), Decimal(100), Decimal(5)
            ),
            PaperDepth(
                Decimal("100.000"), Decimal("100.001"), Decimal("5.000"), Decimal("5.000"), time_ns(), "BETA.PERP"
            ),
            Decimal(10000),
        )
        pair = Correlation("ALPHA-PERP", "BETA.PERP", Decimal(1))
        config = replace(config, fixture=(alpha, beta), correlations=(pair,))
        service = PaperAdmission(config)
        await service.open()
        try:
            assert (await service.start()).ready
            assert service._store is not None and service._runtime is not None
            durable = service._store.snapshot(config.session_id, service._owner)
            native = service._runtime.snapshot()
            intent = OrderIntent("alpha-probe", "ALPHA-PERP", "BUY", Decimal("0.5"), Decimal("10.001"), Decimal(1))
            context = risk_context(
                config,
                durable,
                native,
                intent,
                time_ns() // 1_000_000,
                Decimal(0),
                Decimal(0),
                config.fixtures[0].starting_balance,
            )
            decision = evaluate(intent, context, config.policy)
            assert decision.approved, decision.reasons
            first = await service.submit(
                proposal("alpha-request", symbol="ALPHA-PERP", quantity="0.5", limit_price="10.001")
            )
            assert (await settled(service, first.id)).state == CommandState.FILLED
            second = await service.submit(
                proposal("beta-request", symbol="BETA.PERP", quantity="0.1", limit_price="100.001")
            )
            second_final = await settled(service, second.id)
            assert second_final.state == CommandState.FILLED
            native = service._runtime.snapshot()
            by_symbol = {item.symbol: item for item in native.instruments}
            assert by_symbol["ALPHA-PERP"].position_quantity == Decimal("0.5")
            assert by_symbol["BETA.PERP"].position_quantity == Decimal("0.1")
            durable = service._store.snapshot(config.session_id, service._owner)
            assert {item.symbol: item.quantity for item in durable.positions} == {
                "ALPHA-PERP": Decimal("0.5"),
                "BETA.PERP": Decimal("0.1"),
            }
        finally:
            await service.close()

        beta_dir = tmp_path / "beta-only"
        beta_dir.mkdir()
        beta_config = replace(config_at(beta_dir), fixture=(alpha, beta), correlations=(pair,))
        beta_service = PaperAdmission(beta_config)
        await beta_service.open()
        try:
            assert (await beta_service.start()).ready
            assert beta_service._runtime is not None
            order = await beta_service.submit(
                proposal("beta-only-request", symbol="BETA.PERP", quantity="0.1", limit_price="100.001")
            )
            assert (await settled(beta_service, order.id)).state == CommandState.FILLED
            native = beta_service._runtime.snapshot()
            assert next(item for item in native.instruments if item.symbol == "BETA.PERP").position_quantity == Decimal(
                "0.1"
            )
        finally:
            await beta_service.close()

    asyncio.run(scenario())


def test_real_native_lifetime_idempotency_and_restart_protection(tmp_path: Path) -> None:
    async def scenario() -> None:
        config = config_at(tmp_path)
        service = PaperAdmission(config)
        await service.open()
        try:
            assert (await service.start()).ready
            one = await service.submit(proposal())
            final = await settled(service, one.id)
            assert final.state == CommandState.FILLED
            same = await service.submit(proposal())
            assert same.id == one.id
            assert same.native_client_order_id == one.native_client_order_id
            second = await service.submit(proposal("req-2"))
            assert (await settled(service, second.id)).state == CommandState.FILLED
            assert (await service.status()).native_process_alive
            competing = PaperAdmission(config)
            with pytest.raises(PaperUnavailable):
                await competing.open()
        finally:
            await service.close()
        assert not (await service.status()).native_process_alive
        restart = PaperAdmission(config)
        await restart.open()
        try:
            assert (await restart.status()).state == "protected"
            with pytest.raises(PaperUnavailable):
                await restart.start()
        finally:
            await restart.close()

    asyncio.run(scenario())


def test_actual_risk_rejects_and_concurrent_reservations(tmp_path: Path) -> None:
    async def scenario() -> None:
        config = config_at(tmp_path)
        config = replace(config, policy=replace(config.policy, max_account_exposure=Decimal(50)))
        service = PaperAdmission(config)
        await service.open()
        try:
            await service.start()
            results = await asyncio.gather(service.submit(proposal("one")), service.submit(proposal("two")))
            assert sum(item.state == CommandState.RISK_REJECTED for item in results) >= 1
            large = await service.submit(proposal("large", quantity="0.1"))
            assert large.state == CommandState.RISK_REJECTED
        finally:
            await service.close()

    asyncio.run(scenario())


def test_stale_synthetic_context_never_refreshes(tmp_path: Path) -> None:
    async def scenario() -> None:
        config = config_at(tmp_path)
        fixture = config.fixtures[0]
        depth = replace(fixture.initial_depth, timestamp_ns=1_000_000_000)
        config = replace(config, fixture=(replace(fixture, initial_depth=depth),))
        service = PaperAdmission(config)
        await service.open()
        try:
            await service.start()
            assert (await service.submit(proposal())).state == CommandState.RISK_REJECTED
        finally:
            await service.close()

    asyncio.run(scenario())


def test_perpetual_open_notional_is_not_daily_loss_and_fees_reconcile(tmp_path: Path) -> None:
    async def scenario() -> None:
        service = PaperAdmission(config_at(tmp_path))
        await service.open()
        try:
            await service.start()
            record = await service.submit(proposal("open-500", quantity="0.01"))
            assert (await settled(service, record.id)).state == CommandState.FILLED
            assert service._store is not None and service._runtime is not None
            durable = service._store.snapshot(service.config.session_id, service._owner)
            native = service._runtime.snapshot()
            assert durable.balance == native.balance_total
            assert durable.balance > Decimal(9999)  # Opening 500USDT is not 500USDT loss.
            assert durable.realized_pnl - durable.cumulative_fee == native.realized_pnl
            assert native.unrealized_pnl == Decimal("-0.001")  # Explicit synthetic spread.
            assert native.equity == native.balance_total + native.unrealized_pnl
            follow = await service.submit(proposal("after-open"))
            assert (await settled(service, follow.id)).state == CommandState.FILLED
        finally:
            await service.close()

    asyncio.run(scenario())
