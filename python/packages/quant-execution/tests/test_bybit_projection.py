"""Strict projections reject unknown or incomplete remote evidence."""

from decimal import Decimal

import pytest
from quant_execution.bybit_projection import (
    AccountKeyEvidence,
    InstrumentEvidence,
    ProjectionError,
    ReportCoverage,
    WalletEvidence,
)


def test_projects_only_allowlisted_account_evidence() -> None:
    evidence = AccountKeyEvidence.parse(
        {
            "user_id": "107209442",
            "parent_uid": "100000001",
            "is_master": False,
            "read_only": False,
            "unified": True,
            "expires_at_ms": 2_000_000_000_000,
            "ip_bindings": ["203.0.113.4"],
            "permissions": ["read", "linear_trade"],
        }
    )
    assert evidence.user_id == "107209442"
    assert evidence.parent_uid == "100000001"
    assert evidence.permissions == frozenset({"read", "linear_trade"})


@pytest.mark.parametrize(
    "change",
    [
        {"api_key": "secret"},
        {"user_id": None},
        {"read_only": 1},
        {"permissions": ["read", "read"]},
        {"expires_at_ms": True},
    ],
)
def test_rejects_unknown_or_wrongly_typed_account_fields(change: dict[str, object]) -> None:
    raw: dict[str, object] = {
        "user_id": "107209442",
        "is_master": False,
        "read_only": False,
        "unified": True,
        "expires_at_ms": 2_000_000_000_000,
        "ip_bindings": ["203.0.113.4"],
        "permissions": ["read", "linear_trade"],
    }
    raw.update(change)
    with pytest.raises(ProjectionError):
        AccountKeyEvidence.parse(raw)


@pytest.mark.parametrize("binding", ["0.0.0.0", "203.0.113.4/24", "not-an-ip"])
def test_ip_binding_must_be_a_specific_address(binding: str) -> None:
    with pytest.raises(ProjectionError):
        AccountKeyEvidence.parse(
            {
                "user_id": "81234567",
                "is_master": False,
                "read_only": False,
                "unified": True,
                "expires_at_ms": 2_000_000_000_000,
                "ip_bindings": [binding],
                "permissions": ["read", "linear_trade"],
            }
        )


def test_wallet_keeps_zero_funds_as_observed_data() -> None:
    wallet = WalletEvidence.parse(
        {
            "observed_at_ms": 1_800_000_000_000,
            "account_type": "UNIFIED",
            "total_equity_usdt": "0",
            "available_margin_usdt": "0",
        }
    )
    assert wallet.total_equity_usdt == Decimal(0)
    assert wallet.available_margin_usdt == Decimal(0)


@pytest.mark.parametrize("value", [True, -1, "NaN", "Infinity", "1e40", 1.2])
def test_wallet_rejects_untrusted_nonfinite_negative_or_float_values(value: object) -> None:
    with pytest.raises(ProjectionError):
        WalletEvidence.parse(
            {
                "symbol": "BTCUSDT",
                "observed_at_ms": 1_800_000_000_000,
                "account_type": "UNIFIED",
                "total_equity_usdt": value,
                "available_margin_usdt": "0",
            }
        )


def test_instrument_and_reports_require_expected_identity_and_complete_flags() -> None:
    instrument = InstrumentEvidence.parse(
        {
            "symbol": "BTCUSDT",
            "observed_at_ms": 1_800_000_000_000,
            "tick_size": "0.1",
            "quantity_step": "0.001",
            "minimum_quantity": "0.001",
            "minimum_notional_usdt": "5",
        },
        "BTCUSDT",
    )
    assert instrument.quantity_step == Decimal("0.001")
    with pytest.raises(ProjectionError, match="instrument_mismatch"):
        InstrumentEvidence.parse(
            {
                "symbol": "ETHUSDT",
                "observed_at_ms": 1_800_000_000_000,
                "tick_size": "0.1",
                "quantity_step": "0.001",
                "minimum_quantity": "0.001",
                "minimum_notional_usdt": "5",
            },
            "BTCUSDT",
        )
    coverage = ReportCoverage.parse(
        {
            "symbol": "BTCUSDT",
            "observed_at_ms": 1_800_000_000_000,
            "orders_complete": True,
            "positions_complete": True,
            "executions_complete": True,
            "pagination_complete": True,
            "skipped_symbols": [],
        },
        "BTCUSDT",
    )
    assert coverage.pagination_complete
    with pytest.raises(ProjectionError):
        ReportCoverage.parse(
            {
                "symbol": "BTCUSDT",
                "observed_at_ms": 1_800_000_000_000,
                "orders_complete": True,
                "positions_complete": True,
                "executions_complete": True,
                "pagination_complete": True,
                "skipped_symbols": [],
                "raw_payload": {},
            },
            "BTCUSDT",
        )
