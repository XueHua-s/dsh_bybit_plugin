# Constructor adaptation based on NautilusTrader 1.231.0
# Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
# SPDX-License-Identifier: LGPL-3.0-only
# Source: nautilus_trader/adapters/sandbox/execution.py at 27a8e54e7ac3c57d6cbf8891f0283dfbaee97317
# Distributed under the GNU Lesser General Public License version 3.0.
# https://www.gnu.org/licenses/lgpl-3.0.html

"""Pinned 1.231.0 Sandbox constructor adaptation for finite native L2 consumption.

Upstream Sandbox omits the native liquidity_consumption argument. Initialize only
one exchange/account, retaining inherited Sandbox connect/data/command methods.
"""

import asyncio

from nautilus_trader.adapters.sandbox.config import SandboxExecutionClientConfig
from nautilus_trader.adapters.sandbox.execution import SandboxExecutionClient
from nautilus_trader.backtest.engine import SimulatedExchange
from nautilus_trader.backtest.execution_client import BacktestExecClient
from nautilus_trader.backtest.models import FillModel, LatencyModel, MakerTakerFeeModel
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus, TestClock
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.config import LiveExecClientConfig
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.live.factories import LiveExecClientFactory
from nautilus_trader.model.enums import AccountType, BookType, OmsType
from nautilus_trader.model.identifiers import AccountId, ClientId, Venue
from nautilus_trader.model.objects import Currency, Money
from nautilus_trader.portfolio.base import PortfolioFacade


class _FiniteSandbox(SandboxExecutionClient):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        portfolio: PortfolioFacade,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        config: SandboxExecutionClientConfig,
    ) -> None:
        expected = SandboxExecutionClientConfig(
            venue="SIM",
            starting_balances=config.starting_balances,
            base_currency="USDT",
            book_type="L2_MBP",
        )
        if config != expected:
            raise ValueError("unsupported_finite_sandbox_config")
        self.test_clock = TestClock()
        LiveExecutionClient.__init__(
            self,
            loop=loop,
            client_id=ClientId("SIM"),
            venue=Venue("SIM"),
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            base_currency=Currency.from_str("USDT"),
            instrument_provider=InstrumentProvider(),
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            config=None,
        )
        self._set_account_id(AccountId("SIM-001"))
        self.exchange = SimulatedExchange(
            venue=Venue("SIM"),
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            starting_balances=[Money.from_str(b) for b in config.starting_balances],
            base_currency=Currency.from_str("USDT"),
            default_leverage=config.default_leverage,
            leverages={},
            modules=[],
            portfolio=portfolio,
            msgbus=msgbus,
            cache=cache,
            clock=self.test_clock,
            fill_model=FillModel(),
            fee_model=MakerTakerFeeModel(),
            latency_model=LatencyModel(0),
            book_type=BookType.L2_MBP,
            use_message_queue=False,
            liquidity_consumption=True,
        )
        self._client = BacktestExecClient(exchange=self.exchange, msgbus=msgbus, cache=cache, clock=self.test_clock)
        self.exchange.register_client(self._client)
        self.exchange.initialize_account()


class SandboxLiveExecClientFactory(LiveExecClientFactory):
    @staticmethod
    def create(
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: LiveExecClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        *,
        portfolio: PortfolioFacade | None = None,
    ) -> SandboxExecutionClient:
        if not isinstance(config, SandboxExecutionClientConfig) or portfolio is None or name != "SIM":
            raise ValueError("unsupported_finite_sandbox_factory")
        return _FiniteSandbox(loop, portfolio, msgbus, cache, clock, config)
