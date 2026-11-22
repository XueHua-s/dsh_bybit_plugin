"""Offline Testnet session/admission contract; no provider or venue IO."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

from alembic import command
from alembic.config import Config
from quant_data.commands import CommandState, Environment, OrderCommand, OrderType, Side
from quant_data.ledger import CommandLedger
from quant_data.reconciliation_store import ReconciliationEvidence
from quant_engine.admission import NativeAdmission, NativeProposal, RiskContextSource
from quant_engine.bybit_profiles import TrustedBybitProfile
from quant_engine.bybit_session import BybitSession, BybitSessionUnavailable
from quant_execution.bybit_preflight import ProfileBinding
from quant_risk.models import AccountSnapshot, MarketSnapshot, OrderIntent, RiskContext, RiskPolicy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[3] / "packages" / "quant-data"


class _Provider:
    def get_api_key_evidence(self, profile: ProfileBinding, timeout_seconds: float) -> dict[str, object]:
        return {
            "user_id": profile.expected_uid,
            "parent_uid": None,
            "is_master": False,
            "read_only": False,
            "unified": True,
            "expires_at_ms": 200_000,
            "ip_bindings": ["192.0.2.1"],
            "permissions": ["read", "linear_trade"],
        }

    def get_wallet_evidence(
        self, profile: ProfileBinding, account_type: str, timeout_seconds: float
    ) -> dict[str, object]:
        return {
            "observed_at_ms": 99_999,
            "account_type": "UNIFIED",
            "total_equity_usdt": "1000",
            "available_margin_usdt": "900",
        }

    def get_linear_instrument_evidence(
        self, profile: ProfileBinding, symbol: str, timeout_seconds: float
    ) -> dict[str, object]:
        return {
            "symbol": symbol,
            "observed_at_ms": 99_999,
            "tick_size": "1",
            "quantity_step": "1",
            "minimum_quantity": "1",
            "minimum_notional_usdt": "5",
        }

    def get_initial_report_coverage(
        self, profile: ProfileBinding, symbol: str, timeout_seconds: float
    ) -> dict[str, object]:
        return {
            "symbol": symbol,
            "observed_at_ms": 99_999,
            "orders_complete": True,
            "positions_complete": True,
            "executions_complete": True,
            "pagination_complete": True,
            "skipped_symbols": [],
        }


def _policy() -> RiskPolicy:
    return RiskPolicy(
        "account-fixture",
        "testnet",
        Decimal(500),
        Decimal(1000),
        Decimal(5),
        Decimal(3000),
        Decimal("0.1"),
        Decimal("0.2"),
        10,
        Decimal("0.02"),
        Decimal("0.02"),
        Decimal("0.5"),
        Decimal("0.01"),
        Decimal("0.1"),
        Decimal(1),
        Decimal("0.8"),
        Decimal(2),
        Decimal("0.001"),
        0,
        5000,
    )


def test_ai_proposal_is_risk_checked_and_claimed_without_venue_io(tmp_path: Path) -> None:
    database = tmp_path / "native.sqlite"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "head")
    sessions = sessionmaker(create_engine(f"sqlite:///{database}"))
    account = BybitSession(
        sessions,
        session_id="native-session",
        account_ref="account-fixture",
        profile=TrustedBybitProfile("profile", "81234567"),
        config_fingerprint="a" * 64,
    )
    assert account.open().protected
    account.record_reconciliation(
        ReconciliationEvidence("native-session", 1, {"equity": "1000"}, [], [], [], True, 100_000_000, generation=0)
    )
    assert not account.activate(1, 100_000_001).ready
    assert account.preflight(_Provider(), "BTCUSDT", 100_000).order_submission_allowed is False

    @dataclass(frozen=True)
    class Source:
        def context_for(self, command: OrderCommand) -> RiskContext:
            intent = OrderIntent(
                command.request_id,
                command.symbol,
                "BUY",
                command.quantity,
                command.limit_price or Decimal(0),
                Decimal(1),
            )
            snapshot = 100_000
            market = MarketSnapshot(
                command.symbol,
                intent,
                snapshot,
                Decimal(99),
                Decimal(100),
                Decimal(100),
                Decimal(10000),
                Decimal("0.001"),
                Decimal("0.5"),
                Decimal("0.1"),
                Decimal(1),
                Decimal("0.1"),
                Decimal(100),
                Decimal(5),
            )
            return RiskContext(
                "native-session:0:1",
                snapshot,
                snapshot,
                snapshot,
                snapshot - 1_000,
                AccountSnapshot(
                    "account-fixture",
                    "testnet",
                    snapshot,
                    Decimal(1000),
                    Decimal(900),
                    Decimal(1000),
                    Decimal(0),
                    Decimal(1000),
                    True,
                    True,
                    True,
                ),
                market,
                (),
                (),
                (),
                False,
            )

    admission = NativeAdmission(account, CommandLedger(sessions))
    receipt = admission.admit_proposal(
        NativeProposal("request-1", "BTCUSDT", "buy", Decimal(1), Decimal(101)),
        Source(),
        _policy(),
        now_ns=100_000_000,
    )
    assert receipt.claim is not None
    assert receipt.command.state is CommandState.DISPATCHING
    assert receipt.claim.native_client_order_id == receipt.command.native_client_order_id


def test_environment_and_account_are_server_bound(tmp_path: Path) -> None:
    database = tmp_path / "native.sqlite"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "head")
    sessions = sessionmaker(create_engine(f"sqlite:///{database}"))
    account = BybitSession(
        sessions,
        session_id="native-session",
        account_ref="account-fixture",
        profile=TrustedBybitProfile("profile", "81234567"),
        config_fingerprint="a" * 64,
    )
    account.open()
    try:
        NativeAdmission(account, CommandLedger(sessions)).admit(
            OrderCommand(
                Environment.INTERNAL_PAPER,
                "account-fixture",
                "request",
                "BTCUSDT",
                Side.BUY,
                OrderType.LIMIT,
                Decimal(1),
                Decimal(100),
            ),
            cast(RiskContextSource, object()),
            _policy(),
            now_ns=1,
        )
    except BybitSessionUnavailable as error:
        assert "testnet_session_not_ready" in str(error)
    else:
        raise AssertionError("protected session accepted an AI proposal")
